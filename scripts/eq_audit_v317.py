#!/usr/bin/env python3
"""
EQ Audit v3-17: Evidence Quality re-grading for all 608 models.

Applies explicit grading criteria (EQ 1-10) based on actual model content,
replacing the batch-assigned EQ=2 values with data-driven grades.

Rules:
- EQ=0 models: upgrade to whatever the criteria say
- EQ=2 models: upgrade if criteria say higher
- EQ > 2 models: only upgrade, NEVER downgrade (preserve manual grades)

Confidence tier updates:
- EQ >= 6 AND composite >= 70 -> HIGH (if not already)
- EQ >= 4 AND EQ < 6 -> MODERATE (if currently LOW)
- Never downgrade existing HIGH models
"""

import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

# -- Configuration ----------------------------------------------------------

DATA_FILE = Path("/Users/mv/Documents/research/data/verified/v3-12_normalized_2026-02-12.json")
BACKUP_FILE = DATA_FILE.parent / "v3-12_normalized_2026-02-12.pre-eq-audit.backup.json"

DEEP_DIVE_PREFIXES = (
    "MC-V37", "MC-V38", "MC-V39", "MC-V310",
    "MC-V312", "MC-V313", "MC-V314", "MC-V315",
)


# -- Helper functions -------------------------------------------------------

def has_numbers_or_stats(text):
    """Check if text contains specific numbers, dollar amounts, percentages, or stats."""
    if not text:
        return False
    text = str(text)
    patterns = [
        r'\$[\d.,]+[BMKbmk]?',        # Dollar amounts: $3M, $14-16M, $50K
        r'\d+[%]',                      # Percentages: 21%, 43%
        r'\d+\.\d+[BMKx]',             # Decimal with suffix: 1.5B, 21.5x
        r'\d{1,3}[BMK]\b',             # Numbers with suffix: 3M, 250K, 65B
        r'\b\d{4,}\b',                 # 4+ digit numbers: 21000, 250000
        r'\b\d+,\d{3}',               # Comma-separated numbers: 21,000
        r'\d+[\-\u2013]\d+[BMK%]',    # Ranges: 14-16M, 5-10%
        r'\b\d+x\b',                   # Multipliers: 3x, 500x
    ]
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False


def has_specific_claims(text):
    """Check if text contains specific testable claims (numbers + context)."""
    if not text:
        return False
    text = str(text)
    if not has_numbers_or_stats(text):
        return False
    if len(text) < 50:
        return False
    return True


def is_deep_dive_model(model_id):
    """Check if model ID matches deep dive patterns."""
    return model_id.startswith(DEEP_DIVE_PREFIXES)


def has_populated_deep_dive_evidence(model):
    """Check if deep_dive_evidence is meaningfully populated."""
    dde = model.get("deep_dive_evidence", "")
    if isinstance(dde, dict):
        return any(bool(v) for v in dde.values())
    return bool(dde) and len(str(dde).strip()) > 20


def has_testable_falsification(model):
    """Check if falsification_criteria contains specific testable claims."""
    fc = model.get("falsification_criteria", [])
    if not fc:
        return False
    if isinstance(fc, list):
        for criterion in fc:
            if has_numbers_or_stats(str(criterion)):
                return True
            c = str(criterion).lower()
            if any(kw in c for kw in ["within", "by 20", "exceeds", "falls below",
                                       "more than", "less than", "reaches"]):
                return True
    return False


def compute_eq_grade(model):
    """
    Compute EQ grade from 1-10 based on model content.
    Checks from highest to lowest, returns the MAX grade the model qualifies for.
    """
    mid = model.get("id", "")

    # EQ=10: Validated against external live data (none currently) -- reserved

    # EQ=9: deep_dive_evidence + falsification with specific testable claims
    if has_populated_deep_dive_evidence(model) and has_testable_falsification(model):
        dde = str(model.get("deep_dive_evidence", ""))
        if has_numbers_or_stats(dde):
            return 9

    # EQ=8: deep_dive_evidence field populated (full sourced evidence)
    if has_populated_deep_dive_evidence(model):
        return 8

    # EQ=7: Deep dive model with evidence containing specific numbers
    if is_deep_dive_model(mid):
        evidence_text = " ".join(filter(None, [
            str(model.get("one_liner", "")),
            str(model.get("macro_source", "")),
            str(model.get("key_v3_context", "")),
        ]))
        if has_numbers_or_stats(evidence_text):
            return 7

    # EQ=6: Deep dive model (by ID pattern)
    if is_deep_dive_model(mid):
        return 6

    # EQ=5: Sector-specific data (4+ digit NAICS + Polanyi data)
    naics = str(model.get("sector_naics", ""))
    naics_clean = naics.replace("-", "")
    has_4digit_naics = len(naics_clean) >= 4 and naics_clean.isdigit()
    has_polanyi = bool(model.get("polanyi"))
    if has_4digit_naics and has_polanyi:
        return 5

    # EQ=4: Secondary validation (architecture + 2+ forces)
    has_arch = bool(model.get("architecture"))
    forces = model.get("forces_v3", []) or []
    has_2_forces = len(forces) >= 2
    if has_arch and has_2_forces:
        return 4

    # EQ=3: Rationale with data citation (numbers in one_liner/evidence)
    evidence_text = " ".join(filter(None, [
        str(model.get("one_liner", "")),
        str(model.get("macro_source", "")),
        str(model.get("key_v3_context", "")),
    ]))
    if has_specific_claims(evidence_text):
        return 3

    # EQ=2: Basic rationale but no external data citation
    has_rationale = bool(model.get("one_liner")) or bool(model.get("key_v3_context"))
    if has_rationale:
        return 2

    # EQ=1: Only name and category, no rationale
    return 1


def update_confidence_tier(model):
    """
    Update confidence tier based on new EQ.
    - EQ >= 6 AND composite >= 70 -> HIGH (if not already)
    - EQ >= 4 AND EQ < 6 -> MODERATE (if currently LOW)
    - Never downgrade existing HIGH
    """
    current = model.get("confidence_tier", "LOW")
    eq = model.get("evidence_quality", 0)
    composite = model.get("composite", 0)

    if current == "HIGH":
        return "HIGH"

    if eq >= 6 and composite >= 70:
        return "HIGH"

    if 4 <= eq < 6 and current == "LOW":
        return "MODERATE"

    return current


# -- Main -------------------------------------------------------------------

def main():
    print("=" * 78)
    print("EQ AUDIT v3-17 -- Evidence Quality Re-Grading")
    print("=" * 78)
    print()

    # Step 0: Create backup FIRST (before any modification)
    shutil.copy2(DATA_FILE, BACKUP_FILE)
    print("Backup created: {}".format(BACKUP_FILE.name))

    # Load data
    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data["models"]
    total = len(models)
    print("Loaded {} models from {}".format(total, DATA_FILE.name))
    print()

    # -- PART 1: Audit EQ=0 models -----------------------------------------
    print("-" * 78)
    print("PART 1: EQ=0 MODELS AUDIT")
    print("-" * 78)
    eq0_models = [m for m in models if m.get("evidence_quality", 0) == 0]
    print()
    print("Found {} models with EQ=0:".format(len(eq0_models)))
    print()
    header = "{:<22} {:<45} {:<20} {:>6} {:<10}".format(
        "ID", "Name", "Category", "Comp", "Tier")
    print(header)
    print("{} {} {} {} {}".format("-"*22, "-"*45, "-"*20, "-"*6, "-"*10))
    for m in eq0_models:
        print("{:<22} {:<45} {:<20} {:>6.1f} {:<10}".format(
            m["id"], m["name"][:44], m.get("primary_category", ""),
            m.get("composite", 0), m.get("confidence_tier", "")))

    # -- PART 2: Compute new EQ grades --------------------------------------
    print()
    print("-" * 78)
    print("PART 2: APPLYING EQ GRADING CRITERIA")
    print("-" * 78)
    print()

    # Snapshot before state
    before_eq = {m["id"]: m.get("evidence_quality", 0) for m in models}
    before_tier = {m["id"]: m.get("confidence_tier", "LOW") for m in models}

    # Grade each model
    changes = []
    for model in models:
        mid = model["id"]
        old_eq = model.get("evidence_quality", 0)
        computed_eq = compute_eq_grade(model)

        # Upgrade rules:
        #   EQ=0 -> upgrade to computed
        #   EQ=2 (batch-assigned) -> upgrade if computed > 2
        #   All others -> only upgrade, never downgrade
        final_eq = max(old_eq, computed_eq)

        if final_eq != old_eq:
            changes.append({
                "id": mid,
                "name": model["name"],
                "old_eq": old_eq,
                "new_eq": final_eq,
                "delta": final_eq - old_eq,
            })

        model["evidence_quality"] = final_eq

    print("Grading complete. {} models evaluated.".format(total))

    # -- PART 3: Migration Report -------------------------------------------
    print()
    print("-" * 78)
    print("PART 3: EQ MIGRATION REPORT")
    print("-" * 78)
    print()

    print("Models changed: {} / {} ({:.1f}%)".format(
        len(changes), total, 100.0 * len(changes) / total))
    print()

    # Distribution before vs after
    before_dist = Counter(before_eq.values())
    after_dist = Counter(m["evidence_quality"] for m in models)

    print("{:>4}  {:>8}  {:>8}  {:>8}".format("EQ", "Before", "After", "Delta"))
    print("{}  {}  {}  {}".format("-"*4, "-"*8, "-"*8, "-"*8))
    for eq in range(0, 11):
        b = before_dist.get(eq, 0)
        a = after_dist.get(eq, 0)
        d = a - b
        if d > 0:
            delta_str = "+{}".format(d)
        elif d < 0:
            delta_str = str(d)
        else:
            delta_str = "---"
        print("{:>4}  {:>8}  {:>8}  {:>8}".format(eq, b, a, delta_str))

    # Mean EQ before vs after, by confidence tier (using ORIGINAL tiers)
    print()
    print("Mean EQ by confidence tier (before -> after):")
    print()
    tiers_ordered = ["HIGH", "MODERATE", "LOW"]
    for tier in tiers_ordered:
        tier_models = [m for m in models if before_tier[m["id"]] == tier]
        if not tier_models:
            continue
        mean_before = sum(before_eq[m["id"]] for m in tier_models) / len(tier_models)
        mean_after = sum(m["evidence_quality"] for m in tier_models) / len(tier_models)
        print("  {:<10}: {:.2f} -> {:.2f}  (+{:.2f}, n={})".format(
            tier, mean_before, mean_after, mean_after - mean_before, len(tier_models)))

    # All changes sorted by delta descending
    changes_sorted = sorted(changes, key=lambda x: (-x["delta"], x["id"]))

    # Show top changes
    print()
    print("All EQ changes by size:")
    delta_groups = defaultdict(list)
    for c in changes_sorted:
        delta_groups[c["delta"]].append(c)
    for delta in sorted(delta_groups.keys(), reverse=True):
        items = delta_groups[delta]
        print()
        print("  Delta +{}: {} models".format(delta, len(items)))

    # Biggest EQ jumps (3+ points)
    big_jumps = [c for c in changes_sorted if c["delta"] >= 3]
    print()
    if big_jumps:
        print("Biggest EQ jumps (delta >= 3): {} models".format(len(big_jumps)))
        print()
        print("{:<36} {:<42} {:>4} {:>4} {:>6}".format(
            "ID", "Name", "Old", "New", "Delta"))
        print("{} {} {} {} {}".format("-"*36, "-"*42, "-"*4, "-"*4, "-"*6))
        for c in big_jumps:
            print("{:<36} {:<42} {:>4} {:>4} {:>6}".format(
                c["id"][:35], c["name"][:41], c["old_eq"], c["new_eq"],
                "+{}".format(c["delta"])))
    else:
        print("No models with EQ jump >= 3.")

    # -- PART 4: Confidence Tier Updates ------------------------------------
    print()
    print("-" * 78)
    print("PART 4: CONFIDENCE TIER MIGRATION")
    print("-" * 78)
    print()

    tier_changes = []
    for model in models:
        mid = model["id"]
        old_tier = before_tier[mid]
        new_tier = update_confidence_tier(model)

        if new_tier != old_tier:
            tier_changes.append({
                "id": mid,
                "name": model["name"],
                "old_tier": old_tier,
                "new_tier": new_tier,
                "eq": model["evidence_quality"],
                "composite": model.get("composite", 0),
            })

        model["confidence_tier"] = new_tier

    # Tier distribution before vs after
    before_tier_dist = Counter(before_tier.values())
    after_tier_dist = Counter(m["confidence_tier"] for m in models)

    print("{:<12}  {:>8}  {:>8}  {:>8}".format("Tier", "Before", "After", "Delta"))
    print("{}  {}  {}  {}".format("-"*12, "-"*8, "-"*8, "-"*8))
    for tier in tiers_ordered:
        b = before_tier_dist.get(tier, 0)
        a = after_tier_dist.get(tier, 0)
        d = a - b
        if d > 0:
            delta_str = "+{}".format(d)
        elif d < 0:
            delta_str = str(d)
        else:
            delta_str = "---"
        print("{:<12}  {:>8}  {:>8}  {:>8}".format(tier, b, a, delta_str))

    print()
    print("Tier changes: {} models".format(len(tier_changes)))
    if tier_changes:
        print()
        transitions = defaultdict(list)
        for tc in tier_changes:
            key = "{} -> {}".format(tc["old_tier"], tc["new_tier"])
            transitions[key].append(tc)

        for transition in sorted(transitions.keys()):
            items = transitions[transition]
            print("  {}: {} models".format(transition, len(items)))
            for tc in items[:15]:
                print("    {:<32} {:<38} EQ={} comp={:.1f}".format(
                    tc["id"][:31], tc["name"][:37], tc["eq"], tc["composite"]))
            if len(items) > 15:
                print("    ... and {} more".format(len(items) - 15))

    # -- PART 5: Save -------------------------------------------------------
    print()
    print("-" * 78)
    print("PART 5: SAVING")
    print("-" * 78)
    print()

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("Updated data saved to: {}".format(DATA_FILE.name))
    print("Backup at: {}".format(BACKUP_FILE.name))

    # -- Final summary ------------------------------------------------------
    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    mean_before_all = sum(before_eq.values()) / total
    mean_after_all = sum(m["evidence_quality"] for m in models) / total
    print("  Total models:        {}".format(total))
    print("  EQ changes:          {} ({:.1f}%)".format(
        len(changes), 100.0 * len(changes) / total))
    print("  Tier changes:        {}".format(len(tier_changes)))
    print("  Mean EQ:             {:.2f} -> {:.2f}".format(
        mean_before_all, mean_after_all))
    print("  EQ=0 remaining:      {}".format(
        sum(1 for m in models if m["evidence_quality"] == 0)))
    print("  EQ=2 remaining:      {}".format(
        sum(1 for m in models if m["evidence_quality"] == 2)))
    print()


if __name__ == "__main__":
    main()
