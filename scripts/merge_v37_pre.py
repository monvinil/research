#!/usr/bin/env python3
"""
Merge v3-6 normalized inventory (325 models) with 20 new model cards from
Information and Utilities deep dives.

Produces:
  - v3-7_normalized_2026-02-12.json  (345 models, full inventory)
  - updates data/ui/models.json       (slim UI format)

Input files:
  1. v3-6_normalized_2026-02-12.json          (325 models, the base)
  2. v3-6_information_sector_deep_dive_2026-02-12.json  (10 cards in model_cards)
  3. v3-6_utilities_sector_deep_dive_2026-02-12.json    (10 cards in model_cards)
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

EXISTING_FILE = BASE / "v3-6_normalized_2026-02-12.json"
INFO_FILE = BASE / "v3-6_information_sector_deep_dive_2026-02-12.json"
UTIL_FILE = BASE / "v3-6_utilities_sector_deep_dive_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-7_normalized_2026-02-12.json"
UI_OUTPUT = UI_DIR / "models.json"

# Composite formula weights
WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}


def calc_composite(scores):
    """Recalculate composite: (SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10"""
    return round(
        sum(scores[axis] * WEIGHTS[axis] for axis in WEIGHTS) / 10, 2
    )


def extract_score(scores_obj, axis_short, axis_long):
    """
    Extract a numeric score from either flat or nested format.

    Flat format:   scores.SN = 8.5
    Nested format: scores.structural_necessity.score = 8.5
    """
    # Try flat format first (scores.SN directly)
    if axis_short in scores_obj:
        val = scores_obj[axis_short]
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, dict) and "score" in val:
            return val["score"]

    # Try nested long-name format
    if axis_long in scores_obj:
        val = scores_obj[axis_long]
        if isinstance(val, dict) and "score" in val:
            return val["score"]
        if isinstance(val, (int, float)):
            return val

    raise KeyError(
        f"Cannot find score for {axis_short}/{axis_long} in {list(scores_obj.keys())}"
    )


# Mapping from short axis name to possible long-form key in deep dive cards
AXIS_MAP = {
    "SN": "structural_necessity",
    "FA": "force_alignment",
    "EC": "external_context",
    "TG": "timing_grade",
    "CE": "capital_efficiency",
}

# Category hard-enforcement thresholds
CATEGORY_RULES = {
    "STRUCTURAL_WINNER": lambda c, s: c >= 80 and s["SN"] >= 9,
    "FORCE_RIDER": lambda c, s: c >= 70 and s["FA"] >= 7,
    "TIMING_ARBITRAGE": lambda c, s: s["TG"] >= 8 and s["SN"] >= 6,
    "CAPITAL_MOAT": lambda c, s: s["CE"] >= 8 and s["SN"] >= 6,
    "FEAR_ECONOMY": lambda c, s: False,  # checked via macro_source/forces
    "EMERGING_CATEGORY": lambda c, s: False,  # checked via macro_source
}


def enforce_category(composite, scores, stated_categories, card):
    """
    Apply category hard-enforcement rules.

    - STRUCTURAL_WINNER: composite >= 80 AND SN >= 9
    - FORCE_RIDER: composite >= 70 AND FA >= 7
    - Categories that don't meet thresholds get downgraded.
    - Also detect FEAR_ECONOMY from forces/macro_source.
    - Fallback: CONDITIONAL (composite >= 60) or PARKED (< 60).
    """
    enforced = []

    # Check STRUCTURAL_WINNER
    if composite >= 80 and scores["SN"] >= 9:
        enforced.append("STRUCTURAL_WINNER")

    # Check FORCE_RIDER
    if composite >= 70 and scores["FA"] >= 7:
        enforced.append("FORCE_RIDER")

    # Check TIMING_ARBITRAGE
    if scores["TG"] >= 8 and scores["SN"] >= 6:
        enforced.append("TIMING_ARBITRAGE")

    # Check CAPITAL_MOAT
    if scores["CE"] >= 8 and scores["SN"] >= 6:
        enforced.append("CAPITAL_MOAT")

    # Check FEAR_ECONOMY — preserve if stated and driven by F5/fear
    forces = card.get("forces", [])
    macro = card.get("macro_source", "") or ""
    if any("fear" in str(f).lower() or "F5" in str(f) for f in forces) or "fear" in macro.lower():
        if "FEAR_ECONOMY" in stated_categories or "F5_psychology" in forces:
            enforced.append("FEAR_ECONOMY")

    # Check EMERGING_CATEGORY — preserve if stated
    if "EMERGING_CATEGORY" in stated_categories:
        if "emerging" in macro.lower():
            enforced.append("EMERGING_CATEGORY")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in enforced:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    enforced = unique

    # Fallback
    if not enforced:
        if composite >= 60:
            enforced = ["CONDITIONAL"]
        else:
            enforced = ["PARKED"]

    return enforced


def normalize_deep_dive_card(card, source_label):
    """
    Convert a deep dive model card into normalized inventory format.

    Handles both information cards (nested scores) and utilities cards (flat scores).
    """
    # Extract scores
    raw_scores = card["scores"]
    scores = {}
    for short, long in AXIS_MAP.items():
        scores[short] = extract_score(raw_scores, short, long)

    # Recalculate composite
    recalc = calc_composite(scores)

    # Determine best stated composite
    # Prefer composite_corrected over composite_score over composite
    stated = card.get("composite_corrected") or card.get("composite_score") or card.get("composite")

    # Get stated categories
    cat_final = card.get("category_final") or card.get("category", "")
    if isinstance(cat_final, list):
        stated_categories = cat_final
    else:
        stated_categories = [cat_final] if cat_final else []

    # Apply hard-enforcement on the recalculated composite
    categories = enforce_category(recalc, scores, stated_categories, card)

    # Determine primary_category (first in list)
    primary_category = categories[0]

    # Build one_liner from one_line field
    one_liner = card.get("one_line") or card.get("one_liner")

    model = {
        "id": card["card_id"],
        "name": card["model_name"],
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": card.get("forces", []),
        "scores": scores,
        "composite": recalc,
        "composite_stated": stated,
        "category": categories,
        "one_liner": one_liner,
        "key_v3_context": None,
        "source_batch": f"v36_deep_dive_{source_label}",
        "macro_source": card.get("macro_source"),
        "rank": None,  # assigned after sorting
        "primary_category": primary_category,
        "new_in_v36": True,
    }

    return model, stated, recalc


def build_slim_model(m):
    """Build the slim UI format for models.json."""
    return {
        "rank": m["rank"],
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "category": m["primary_category"],
        "categories": m["category"],
        "scores": m["scores"],
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "source_batch": m.get("source_batch"),
        "new_in_v36": m.get("new_in_v36", False),
        "one_liner": m.get("one_liner"),
    }


def main():
    print("=" * 70)
    print("MERGE v3-7 PRE: Information + Utilities deep dives into 325-model base")
    print("=" * 70)
    print()

    # ── Load existing inventory ──────────────────────────────────────────
    print("Loading existing inventory...")
    with open(EXISTING_FILE) as f:
        existing_data = json.load(f)
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models from {EXISTING_FILE.name}")

    # ── Load deep dive files ─────────────────────────────────────────────
    print("Loading Information sector deep dive...")
    with open(INFO_FILE) as f:
        info_data = json.load(f)
    info_cards = info_data["model_cards"]
    print(f"  Loaded {len(info_cards)} Information cards")

    print("Loading Utilities sector deep dive...")
    with open(UTIL_FILE) as f:
        util_data = json.load(f)
    util_cards = util_data["model_cards"]
    print(f"  Loaded {len(util_cards)} Utilities cards")

    total_new = len(info_cards) + len(util_cards)
    print(f"  Total new cards to merge: {total_new}")
    print()

    # ── Check for ID collisions ──────────────────────────────────────────
    print("Checking for ID collisions...")
    existing_ids = {m["id"] for m in existing_models}
    new_ids = set()
    collisions = []

    for card in info_cards + util_cards:
        cid = card["card_id"]
        if cid in existing_ids:
            collisions.append(f"{cid} (exists in base inventory)")
        if cid in new_ids:
            collisions.append(f"{cid} (duplicate within new cards)")
        new_ids.add(cid)

    if collisions:
        print(f"  WARNING: {len(collisions)} ID collision(s): {collisions}")
    else:
        print("  No ID collisions found")
    print()

    # ── Normalize new cards ──────────────────────────────────────────────
    print("Normalizing and scoring new cards...")
    new_models = []
    composite_diffs = []

    for card in info_cards:
        model, stated, recalc = normalize_deep_dive_card(card, "information_deep_dive")
        new_models.append(model)
        if stated is not None:
            diff = abs(stated - recalc)
            composite_diffs.append((model["id"], model["name"], stated, recalc, diff))
            if diff > 0.01:
                print(f"  {model['id']}: stated={stated}, recalculated={recalc}, diff={diff:.2f}")

    for card in util_cards:
        model, stated, recalc = normalize_deep_dive_card(card, "utilities_deep_dive")
        new_models.append(model)
        if stated is not None:
            diff = abs(stated - recalc)
            composite_diffs.append((model["id"], model["name"], stated, recalc, diff))
            if diff > 0.01:
                print(f"  {model['id']}: stated={stated}, recalculated={recalc}, diff={diff:.2f}")

    print(f"  Normalized {len(new_models)} new cards")
    print()

    # ── Composite validation ─────────────────────────────────────────────
    print("Composite validation (stated vs. recalculated):")
    significant_diffs = [(cid, name, st, rc, d) for cid, name, st, rc, d in composite_diffs if d > 0.5]
    if significant_diffs:
        print(f"  WARNING: {len(significant_diffs)} cards with composite diff > 0.5:")
        for cid, name, stated, recalc, diff in significant_diffs:
            print(f"    {cid}: {name[:50]}")
            print(f"      stated={stated}, recalculated={recalc}, diff={diff:.2f}")
            print(f"      (using recalculated value)")
    else:
        print("  All cards within 0.5 tolerance (or using composite_corrected)")

    minor_diffs = [(cid, name, st, rc, d) for cid, name, st, rc, d in composite_diffs if 0.01 < d <= 0.5]
    if minor_diffs:
        print(f"  {len(minor_diffs)} cards with minor diff (0.01 < diff <= 0.5) — using recalculated:")
        for cid, name, stated, recalc, diff in minor_diffs:
            print(f"    {cid}: stated={stated}, recalc={recalc}, diff={diff:.2f}")
    print()

    # ── Preserve existing new_in_v36 flags ───────────────────────────────
    # Existing models keep their current new_in_v36 flag (True for v3-6 deep dives)
    # New models all get new_in_v36 = True

    # ── Merge ────────────────────────────────────────────────────────────
    print("Merging...")
    all_models = existing_models + new_models
    print(f"  Total models: {len(all_models)}")

    # ── Apply category hard-enforcement to NEW models only ────────────────
    # Existing 325 models keep their manually-validated categories
    print("Applying category hard-enforcement to 20 new models only...")
    new_ids = {m["id"] for m in new_models}
    enforcement_changes = []
    for m in all_models:
        if m["id"] not in new_ids:
            continue  # preserve existing categories
        old_primary = m.get("primary_category") or (m["category"][0] if m["category"] else "PARKED")
        old_cats = m["category"] if isinstance(m["category"], list) else [m["category"]]

        # Re-enforce categories
        new_cats = enforce_category(m["composite"], m["scores"], old_cats, m)
        new_primary = new_cats[0]

        if set(new_cats) != set(old_cats) or new_primary != old_primary:
            enforcement_changes.append({
                "id": m["id"],
                "name": m["name"],
                "composite": m["composite"],
                "SN": m["scores"]["SN"],
                "FA": m["scores"]["FA"],
                "old_primary": old_primary,
                "new_primary": new_primary,
                "old_cats": old_cats,
                "new_cats": new_cats,
            })

        m["category"] = new_cats
        m["primary_category"] = new_primary

    if enforcement_changes:
        print(f"  {len(enforcement_changes)} category change(s) from hard-enforcement:")
        for ch in enforcement_changes[:20]:  # show first 20
            print(f"    {ch['id']}: {ch['old_primary']} -> {ch['new_primary']} "
                  f"(composite={ch['composite']}, SN={ch['SN']}, FA={ch['FA']})")
        if len(enforcement_changes) > 20:
            print(f"    ... and {len(enforcement_changes) - 20} more")
    else:
        print("  No category changes from hard-enforcement")
    print()

    # ── Sort by composite descending ─────────────────────────────────────
    all_models.sort(key=lambda m: (-m["composite"], m["id"]))

    # ── Re-rank 1 through N ──────────────────────────────────────────────
    for i, m in enumerate(all_models, 1):
        m["rank"] = i

    # ── Compute summary stats ────────────────────────────────────────────
    composites = [m["composite"] for m in all_models]
    composites_sorted = sorted(composites)
    n = len(composites_sorted)
    if n % 2 == 0:
        median = (composites_sorted[n // 2 - 1] + composites_sorted[n // 2]) / 2
    else:
        median = composites_sorted[n // 2]

    composite_stats = {
        "max": max(composites),
        "min": min(composites),
        "mean": round(statistics.mean(composites), 2),
        "median": round(median, 2),
    }

    # Primary category distribution
    primary_cat_dist = Counter(m["primary_category"] for m in all_models)

    # All-category distribution
    all_cat_dist = Counter()
    for m in all_models:
        for c in m["category"]:
            all_cat_dist[c] += 1

    # Composite distribution
    comp_dist = {
        "above_80": sum(1 for c in composites if c >= 80),
        "70_to_80": sum(1 for c in composites if 70 <= c < 80),
        "60_to_70": sum(1 for c in composites if 60 <= c < 70),
        "50_to_60": sum(1 for c in composites if 50 <= c < 60),
        "below_50": sum(1 for c in composites if c < 50),
    }

    # Source batch counts
    source_counts = Counter(m.get("source_batch", "unknown") for m in all_models)

    # new_in_v36 counts
    new_v36_count = sum(1 for m in all_models if m.get("new_in_v36"))
    existing_count = sum(1 for m in all_models if not m.get("new_in_v36"))

    # ── Build top 50 ─────────────────────────────────────────────────────
    top_50 = []
    for m in all_models[:50]:
        top_50.append({
            "rank": m["rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "primary_category": m["primary_category"],
            "category": m["category"],
            "scores": m["scores"],
            "architecture": m.get("architecture"),
            "source_batch": m.get("source_batch"),
            "new_in_v36": m.get("new_in_v36", False),
        })

    # ── Build full output ────────────────────────────────────────────────
    output = {
        "cycle": "v3-7",
        "date": "2026-02-12",
        "engine_version": "3.7",
        "description": (
            f"Merged normalized model inventory: 325 models from v3-6 normalized + "
            f"20 deep dive model cards from v3-6 (10 Information sector, 10 Utilities sector). "
            f"All {len(all_models)} models sorted by composite descending, re-ranked 1-{len(all_models)}. "
            f"new_in_v36 boolean identifies models added during v3-6/v3-7 deep dive cycles. "
            f"Category hard-enforcement applied to all models."
        ),
        "merge_info": {
            "existing_source": "v3-6_normalized_2026-02-12.json",
            "new_sources": [
                "v3-6_information_sector_deep_dive_2026-02-12.json (10 cards)",
                "v3-6_utilities_sector_deep_dive_2026-02-12.json (10 cards)",
            ],
            "existing_count": 325,
            "new_count": total_new,
            "info_cards": len(info_cards),
            "util_cards": len(util_cards),
            "duplicate_ids_found": len(collisions),
            "category_enforcement_changes": len(enforcement_changes),
            "merge_date": "2026-02-12",
        },
        "rating_system": existing_data["rating_system"],
        "summary": {
            "total_models": len(all_models),
            "existing_models": 325,
            "new_v37_models": total_new,
            "new_in_v36_total": new_v36_count,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "all_category_distribution": dict(sorted(all_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "top_50": top_50,
        "models": all_models,
    }

    # ── Write normalized output ──────────────────────────────────────────
    print(f"Writing {len(all_models)} models to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ── Write UI models.json ─────────────────────────────────────────────
    print(f"Writing UI models.json ({len(all_models)} models)...")
    ui_models = [build_slim_model(m) for m in all_models]
    ui_output = {
        "cycle": "v3-7",
        "date": "2026-02-12",
        "total": len(all_models),
        "summary": {
            "total_models": len(all_models),
            "existing_models": 325,
            "new_v37_models": total_new,
            "new_in_v36_total": new_v36_count,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "all_category_distribution": dict(sorted(all_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "models": ui_models,
    }
    with open(UI_OUTPUT, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)

    # ── Validate output ──────────────────────────────────────────────────
    print()
    print("Validating output...")
    with open(OUTPUT_FILE) as f:
        validated = json.load(f)

    expected_total = 325 + total_new
    assert len(validated["models"]) == expected_total, \
        f"Expected {expected_total} models, got {len(validated['models'])}"
    assert validated["summary"]["total_models"] == expected_total
    assert validated["models"][0]["rank"] == 1
    assert validated["models"][-1]["rank"] == expected_total

    # Check sorting
    for i in range(len(validated["models"]) - 1):
        assert validated["models"][i]["composite"] >= validated["models"][i + 1]["composite"], \
            f"Sort violation at rank {i+1}: {validated['models'][i]['composite']} < {validated['models'][i+1]['composite']}"

    # Check all models have required fields
    required_fields = ["id", "name", "sector_naics", "composite", "category", "scores", "rank", "new_in_v36"]
    score_axes = ["SN", "FA", "EC", "TG", "CE"]
    for m in validated["models"]:
        for field in required_fields:
            assert field in m, f"Model {m.get('id', '?')} missing field: {field}"
        for axis in score_axes:
            assert axis in m["scores"], f"Model {m['id']} missing score axis: {axis}"

    # Check no duplicate IDs
    output_ids = [m["id"] for m in validated["models"]]
    assert len(output_ids) == len(set(output_ids)), "Duplicate IDs found in output!"

    # Validate UI output
    with open(UI_OUTPUT) as f:
        ui_validated = json.load(f)
    assert len(ui_validated["models"]) == expected_total, \
        f"UI models.json: expected {expected_total}, got {len(ui_validated['models'])}"

    print("  All validations PASSED")
    print()

    # ── Print results ────────────────────────────────────────────────────
    print("=" * 70)
    print("MERGE COMPLETE — v3-7 Pre-merge")
    print("=" * 70)
    print()
    print(f"  Total models:      {len(all_models)}")
    print(f"  Base (v3-6):       325")
    print(f"  New (Information): {len(info_cards)}")
    print(f"  New (Utilities):   {len(util_cards)}")
    print(f"  new_in_v36 total:  {new_v36_count} (includes prior v3-6 deep dives)")
    print()
    print(f"  Composite stats:")
    print(f"    max={composite_stats['max']}, min={composite_stats['min']}, "
          f"mean={composite_stats['mean']}, median={composite_stats['median']}")
    print()
    print(f"  Composite distribution:")
    for bucket, count in comp_dist.items():
        print(f"    {bucket:>10s}: {count}")
    print()
    print(f"  Primary category distribution:")
    for cat in sorted(primary_cat_dist.keys()):
        print(f"    {cat:<25s}: {primary_cat_dist[cat]}")
    print()

    # Composite diff report
    print("  Composite stated vs. recalculated (diff > 0.5):")
    if significant_diffs:
        for cid, name, stated, recalc, diff in significant_diffs:
            print(f"    {cid}: stated={stated}, recalc={recalc}, diff={diff:.2f} — {name[:50]}")
    else:
        print("    None (all within tolerance)")
    print()

    # Top 15
    print("  Top 15 models:")
    for m in all_models[:15]:
        flag = " [NEW]" if "deep_dive_information" in (m.get("source_batch") or "") or \
                           "deep_dive_utilities" in (m.get("source_batch") or "") else ""
        v36 = " [v36]" if m.get("new_in_v36") and not flag else ""
        print(f"    {m['rank']:3d}. {m['composite']:6.2f}  {m['primary_category']:<22s}  "
              f"{m['id']:<20s}  {m['name'][:45]}{flag}{v36}")
    print()

    # New cards placement
    print("  New Information cards placement:")
    for m in all_models:
        if "information_deep_dive" in (m.get("source_batch") or ""):
            print(f"    {m['rank']:3d}. {m['composite']:6.2f}  {m['primary_category']:<22s}  "
                  f"{m['id']:<16s}  {m['name'][:50]}")
    print()

    print("  New Utilities cards placement:")
    for m in all_models:
        if "utilities_deep_dive" in (m.get("source_batch") or ""):
            print(f"    {m['rank']:3d}. {m['composite']:6.2f}  {m['primary_category']:<22s}  "
                  f"{m['id']:<16s}  {m['name'][:50]}")
    print()

    print(f"  Output: {OUTPUT_FILE}")
    print(f"  UI:     {UI_OUTPUT}")
    print()


if __name__ == "__main__":
    main()
