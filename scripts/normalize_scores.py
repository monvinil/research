#!/usr/bin/env python3
"""
normalize_scores.py — Batch normalization, GG→EC replacement, category enforcement, deduplication.

Reads:  data/verified/v3-3_unified_models_2026-02-11.json
Writes: data/verified/v3-4_normalized_2026-02-11.json

Steps:
  1. Batch normalization (calibrate cross-batch scoring inconsistency)
  2. GG → EC axis replacement (Geographic Grade → External Context)
  3. Hard-enforce category thresholds (multi-category assignment)
  4. Deduplicate models (name similarity + architecture+sector overlap)
  5. Recompute composite scores and re-rank
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/Users/mv/Documents/research")
INPUT_PATH = BASE / "data" / "verified" / "v3-3_unified_models_2026-02-11.json"
OUTPUT_PATH = BASE / "data" / "verified" / "v3-4_normalized_2026-02-11.json"

# ---------------------------------------------------------------------------
# Batch calibration adjustments
# ---------------------------------------------------------------------------
BATCH_ADJUSTMENTS = {
    "v3-2_cycle": {"SN": -1.5, "FA": -1.5, "TG": -2.5},
    "new_macro_45": {"SN": -0.5, "FA": -0.3, "TG": -0.5},
    "top_40_deep": {},
    "expansion_123": {},
    "mid_41to112": {},
}

# ---------------------------------------------------------------------------
# Fear friction gap by 2-digit NAICS prefix (from rate_expansion.py)
# ---------------------------------------------------------------------------
FEAR_FRICTION = {
    "52": 1, "31": 1, "32": 1, "33": 1,
    "56": 2, "54": 3, "62": 3, "81": 2,
    "53": 2, "72": 1, "48": 2, "49": 2,
    "42": 1, "44": 1, "45": 1,
    "61": 3, "71": 2, "51": 2,
    "23": 2, "22": 2, "21": 2,
    "92": 3, "11": 1, "55": 2, "91": 3,
}

# Sectors considered fear-friction-relevant (gap > 3 means gap >= 4 in integer,
# but the spec says "> 3" so gap values of 4+ qualify).
# From the data: the only sectors with gap=3 are 54, 62, 61, 92, 91.
# None have gap > 3 in the table above. However, the key_v3_context text
# mentions "fear_friction_gap=5" for legal (54) and "fear_friction_gap=3"
# for healthcare (62). We use key_v3_context parsing as a fallback.
FEAR_NAICS_PREFIXES = set()
for prefix, gap_val in FEAR_FRICTION.items():
    if gap_val > 3:
        FEAR_NAICS_PREFIXES.add(prefix)


def clamp(value, lo=1.0, hi=10.0):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, float(value)))


def get_naics_prefix2(sector_naics):
    """Extract the 2-digit NAICS prefix from sector_naics field."""
    if not sector_naics:
        return ""
    # Handle ranges like "31-33"
    cleaned = str(sector_naics).strip()
    # Take first 2 digits
    digits = re.match(r"(\d{2})", cleaned)
    return digits.group(1) if digits else ""


def levenshtein_distance(s1, s2):
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Insertion, deletion, substitution
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def names_are_similar(name1, name2):
    """Check if two model names are duplicates per spec.

    Duplicate if:
      - Levenshtein distance < 15% of the longer name's length, OR
      - One name fully contains the other
    """
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    # Containment check
    if n1 in n2 or n2 in n1:
        return True

    # Levenshtein check: distance < 15% of the longer name
    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return True
    threshold = 0.15 * max_len
    dist = levenshtein_distance(n1, n2)
    return dist < threshold


def parse_fear_friction_gap_from_context(key_v3_context):
    """Try to extract fear_friction_gap=N from key_v3_context text."""
    if not key_v3_context:
        return None
    match = re.search(r"fear_friction_gap\s*=\s*(\d+)", key_v3_context)
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Step 1: Batch normalization
# ---------------------------------------------------------------------------
def apply_batch_normalization(model):
    """Apply batch-specific score adjustments to a model's scores."""
    batch = model.get("source_batch", "")
    adjustments = BATCH_ADJUSTMENTS.get(batch, {})
    scores = dict(model["scores"])  # copy

    for axis, delta in adjustments.items():
        if axis in scores:
            scores[axis] = clamp(scores[axis] + delta)

    model["scores"] = scores
    return model


# ---------------------------------------------------------------------------
# Step 2: GG → EC replacement
# ---------------------------------------------------------------------------
def compute_ec(model):
    """Replace GG with EC (External Context) score.

    EC measures how much international context materially changes
    the model's viability vs. US-only assessment.
    """
    scores = model["scores"]
    gg_baseline = float(scores.get("GG", 5.0))
    ec = gg_baseline

    architecture = (model.get("architecture") or "").lower().strip()
    forces = model.get("forces_v3", []) or []
    sector_naics = str(model.get("sector_naics", ""))
    prefix2 = get_naics_prefix2(sector_naics)
    macro_source = (model.get("macro_source") or "").lower()

    # Architecture overrides
    if architecture in ("acquire_and_modernize", "rollup_consolidation"):
        ec = 5.0  # US-physical, international irrelevant

    # Force-based modifiers
    if "F3" in forces:
        ec += 1.5  # geopolitics directly relevant

    # Sector-based modifiers
    if prefix2 in ("31", "32", "33"):
        ec += 1.0  # manufacturing — supply chain / nearshoring

    if prefix2 in ("52", "54"):
        ec += 0.5  # financial/compliance — EU AI Act contagion

    if prefix2 == "62":
        ec += 0.5  # healthcare — Japan aging leading indicator

    if "defense" in macro_source:
        ec += 2.0  # inherently international

    if prefix2 in ("21", "22"):
        ec += 1.0  # energy — geopolitical dynamics

    # Architecture-based modifiers (non-override)
    if architecture == "regulatory_moat_builder":
        ec += 1.0  # EU AI Act opportunity

    if architecture in ("platform_infrastructure", "data_compounding"):
        ec += 0.5  # portable globally

    # Force-based demographic modifier
    if "F2" in forces:
        ec += 0.5  # Japan/India as leading indicators

    ec = clamp(ec)

    # Remove GG, set EC
    new_scores = {}
    for k, v in scores.items():
        if k != "GG":
            new_scores[k] = v
    new_scores["EC"] = round(ec, 2)
    model["scores"] = new_scores

    return model


# ---------------------------------------------------------------------------
# Step 3: Recompute composite
# ---------------------------------------------------------------------------
def compute_composite(scores):
    """Compute composite = (SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10"""
    sn = float(scores.get("SN", 0))
    fa = float(scores.get("FA", 0))
    ec = float(scores.get("EC", 0))
    tg = float(scores.get("TG", 0))
    ce = float(scores.get("CE", 0))
    return round((sn * 25 + fa * 25 + ec * 20 + tg * 15 + ce * 15) / 10, 2)


# ---------------------------------------------------------------------------
# Step 4: Category assignment (hard enforcement, multi-category)
# ---------------------------------------------------------------------------
def assign_categories(model):
    """Assign ALL matching categories in priority order.

    Returns (categories_list, primary_category).
    """
    scores = model["scores"]
    composite = model["composite"]
    sn = float(scores.get("SN", 0))
    fa = float(scores.get("FA", 0))
    ec = float(scores.get("EC", 0))
    tg = float(scores.get("TG", 0))
    ce = float(scores.get("CE", 0))

    forces = model.get("forces_v3", []) or []
    sector_naics = str(model.get("sector_naics", ""))
    prefix2 = get_naics_prefix2(sector_naics)
    macro_source = (model.get("macro_source") or "").lower()
    key_v3_context = model.get("key_v3_context") or ""

    categories = []

    # 1. STRUCTURAL_WINNER: SN >= 8.0 AND FA >= 8.0
    if sn >= 8.0 and fa >= 8.0:
        categories.append("STRUCTURAL_WINNER")

    # 2. FORCE_RIDER: FA >= 7.0 (and not already STRUCTURAL_WINNER for primary,
    #    but we assign all that match, so just check FA)
    if fa >= 7.0 and "STRUCTURAL_WINNER" not in categories:
        categories.append("FORCE_RIDER")

    # 3. GEOGRAPHIC_PLAY: removed (no equivalent category)

    # 4. TIMING_ARBITRAGE: TG >= 8.0 AND SN >= 6.0
    if tg >= 8.0 and sn >= 6.0:
        categories.append("TIMING_ARBITRAGE")

    # 5. CAPITAL_MOAT: CE >= 8.0 AND SN >= 6.0
    if ce >= 8.0 and sn >= 6.0:
        categories.append("CAPITAL_MOAT")

    # 6. FEAR_ECONOMY: macro_source contains "fear" OR sector in fear_friction
    #    sectors with gap > 3
    is_fear = False
    if "fear" in macro_source:
        is_fear = True
    if not is_fear and prefix2 in FEAR_NAICS_PREFIXES:
        is_fear = True
    # Also check key_v3_context for explicit fear_friction_gap > 3
    if not is_fear:
        gap = parse_fear_friction_gap_from_context(key_v3_context)
        if gap is not None and gap > 3:
            is_fear = True
    if is_fear:
        categories.append("FEAR_ECONOMY")

    # 7. EMERGING_CATEGORY: no standard NAICS or macro_source contains "emerging"
    is_emerging = False
    if "emerging" in macro_source:
        is_emerging = True
    if not is_emerging:
        naics_lower = sector_naics.lower()
        if "n/a" in naics_lower or "emerging" in naics_lower or not prefix2:
            is_emerging = True
    if is_emerging:
        categories.append("EMERGING_CATEGORY")

    # 8. CONDITIONAL: composite >= 60 (fallback)
    if not categories and composite >= 60:
        categories.append("CONDITIONAL")

    # 9. PARKED: composite < 60
    if not categories and composite < 60:
        categories.append("PARKED")

    # If we have real categories but composite < 60, still add PARKED as secondary
    # Actually, per spec: PARKED is "composite < 60" and CONDITIONAL is "composite >= 60 (fallback)"
    # These are fallbacks only when no other category matches.
    # But a model CAN have e.g. FORCE_RIDER + TIMING_ARBITRAGE.

    primary = categories[0] if categories else "PARKED"
    return categories, primary


# ---------------------------------------------------------------------------
# Step 5: Deduplication
# ---------------------------------------------------------------------------
def deduplicate_models(models):
    """Identify and merge duplicate models.

    Duplicates: same architecture AND same 2-digit NAICS, AND
    (Levenshtein distance < 15% of name length, or one name contains other).

    Keep highest composite; add variants field.
    """
    # Build groups: key = (architecture, naics_prefix2)
    # Then within each group, find name-similar clusters
    from collections import defaultdict

    groups = defaultdict(list)
    for model in models:
        arch = (model.get("architecture") or "").lower().strip()
        prefix2 = get_naics_prefix2(model.get("sector_naics", ""))
        key = (arch, prefix2)
        groups[key].append(model)

    kept = []
    total_merged = 0

    for key, group in groups.items():
        arch, prefix2 = key

        # Skip groups where architecture is empty (can't meaningfully dedup)
        # or prefix is empty — only dedup when both are non-empty
        if not arch or not prefix2:
            kept.extend(group)
            continue

        # Find clusters of name-similar models
        used = [False] * len(group)
        clusters = []

        for i in range(len(group)):
            if used[i]:
                continue
            cluster = [i]
            used[i] = True
            for j in range(i + 1, len(group)):
                if used[j]:
                    continue
                if names_are_similar(group[i]["name"], group[j]["name"]):
                    cluster.append(j)
                    used[j] = True
            clusters.append(cluster)

        for cluster in clusters:
            if len(cluster) == 1:
                kept.append(group[cluster[0]])
            else:
                # Pick highest composite
                cluster_models = [group[idx] for idx in cluster]
                cluster_models.sort(key=lambda m: m["composite"], reverse=True)
                winner = cluster_models[0]
                variant_ids = [m["id"] for m in cluster_models[1:]]
                winner["variants"] = variant_ids
                winner["variant_count"] = len(cluster_models)
                kept.append(winner)
                total_merged += len(variant_ids)

    return kept, total_merged


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    # Load input
    print(f"Reading: {INPUT_PATH}")
    if not INPUT_PATH.exists():
        print(f"ERROR: Input file not found: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(INPUT_PATH, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    models = data.get("models", [])
    if not models:
        print("ERROR: No 'models' array found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(models)} models")

    # Track batch counts for reporting
    batch_counts = {}
    for m in models:
        b = m.get("source_batch", "unknown")
        batch_counts[b] = batch_counts.get(b, 0) + 1
    print(f"Batch distribution: {json.dumps(batch_counts, indent=2)}")

    # -----------------------------------------------------------------------
    # Step 1: Batch normalization
    # -----------------------------------------------------------------------
    print("\n--- Step 1: Batch Normalization ---")
    adjustments_applied = {b: 0 for b in BATCH_ADJUSTMENTS}
    for m in models:
        batch = m.get("source_batch", "")
        if batch in BATCH_ADJUSTMENTS and BATCH_ADJUSTMENTS[batch]:
            adjustments_applied[batch] += 1
        apply_batch_normalization(m)

    for batch, adj in BATCH_ADJUSTMENTS.items():
        if adj:
            count = adjustments_applied.get(batch, 0)
            print(f"  {batch}: adjusted {count} models — {adj}")
        else:
            print(f"  {batch}: no adjustment (reference batch)")

    # -----------------------------------------------------------------------
    # Step 2: GG → EC replacement
    # -----------------------------------------------------------------------
    print("\n--- Step 2: GG -> EC Replacement ---")
    ec_values = []
    for m in models:
        old_gg = m["scores"].get("GG", 5.0)
        compute_ec(m)
        new_ec = m["scores"]["EC"]
        ec_values.append(new_ec)

    print(f"  EC stats: min={min(ec_values):.2f}, max={max(ec_values):.2f}, "
          f"mean={sum(ec_values)/len(ec_values):.2f}")

    # -----------------------------------------------------------------------
    # Step 3: Recompute composite
    # -----------------------------------------------------------------------
    print("\n--- Step 3: Recompute Composite ---")
    old_composites = [m["composite"] for m in models]
    for m in models:
        m["composite"] = compute_composite(m["scores"])
    new_composites = [m["composite"] for m in models]

    delta_composites = [new - old for new, old in zip(new_composites, old_composites)]
    print(f"  Composite change: min={min(delta_composites):.2f}, "
          f"max={max(delta_composites):.2f}, "
          f"mean={sum(delta_composites)/len(delta_composites):.2f}")

    # -----------------------------------------------------------------------
    # Step 4: Category assignment (hard enforcement)
    # -----------------------------------------------------------------------
    print("\n--- Step 4: Category Hard Enforcement ---")
    old_categories = {}
    for m in models:
        old_cat = m.get("category", "PARKED")
        old_categories[old_cat] = old_categories.get(old_cat, 0) + 1

    category_changes = 0
    for m in models:
        old_cat = m.get("category", "PARKED")
        categories, primary = assign_categories(m)
        m["category"] = categories
        m["primary_category"] = primary
        if primary != old_cat:
            category_changes += 1

    new_primary_dist = {}
    new_all_dist = {}
    for m in models:
        p = m["primary_category"]
        new_primary_dist[p] = new_primary_dist.get(p, 0) + 1
        for c in m["category"]:
            new_all_dist[c] = new_all_dist.get(c, 0) + 1

    print(f"  Category changes (primary): {category_changes} / {len(models)}")
    print(f"  Old category distribution: {json.dumps(old_categories, indent=4)}")
    print(f"  New primary category distribution: {json.dumps(new_primary_dist, indent=4)}")
    print(f"  New all-category distribution (models can be in multiple): {json.dumps(new_all_dist, indent=4)}")

    # -----------------------------------------------------------------------
    # Step 5: Deduplication
    # -----------------------------------------------------------------------
    print("\n--- Step 5: Deduplication ---")
    models_before = len(models)
    models, total_merged = deduplicate_models(models)
    models_after = len(models)
    print(f"  Before: {models_before} models")
    print(f"  After:  {models_after} models")
    print(f"  Merged: {total_merged} duplicate variants into existing models")

    # List dedup winners
    deduped = [m for m in models if m.get("variant_count", 0) > 1]
    if deduped:
        print(f"  Deduplicated groups ({len(deduped)}):")
        for m in sorted(deduped, key=lambda x: x["composite"], reverse=True):
            print(f"    {m['id']} \"{m['name']}\" — kept (composite {m['composite']:.2f}), "
                  f"merged {m['variant_count'] - 1} variant(s): {m['variants']}")

    # -----------------------------------------------------------------------
    # Step 6: Re-rank by composite descending
    # -----------------------------------------------------------------------
    print("\n--- Step 6: Re-rank ---")
    models.sort(key=lambda m: m["composite"], reverse=True)
    for i, m in enumerate(models):
        m["rank"] = i + 1

    # -----------------------------------------------------------------------
    # Build output
    # -----------------------------------------------------------------------
    # Update rating_system
    rating_system = {
        "axes": {
            "SN": {
                "name": "Structural Necessity",
                "weight": 0.25,
                "description": "Must this business exist given structural forces?"
            },
            "FA": {
                "name": "Force Alignment",
                "weight": 0.25,
                "description": "How many F1-F6 forces drive it, weighted by velocity?"
            },
            "EC": {
                "name": "External Context",
                "weight": 0.2,
                "description": "How much does international context materially change viability vs. US-only assessment?"
            },
            "TG": {
                "name": "Timing Grade",
                "weight": 0.15,
                "description": "Perez-aware entry window + crash resilience"
            },
            "CE": {
                "name": "Capital Efficiency",
                "weight": 0.15,
                "description": "Revenue-per-dollar, time-to-cashflow, crash survivability"
            }
        },
        "composite_formula": "(SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10",
        "categories": {
            "STRUCTURAL_WINNER": "SN >= 8.0 AND FA >= 8.0 — must-exist business with multi-force convergence",
            "FORCE_RIDER": "FA >= 7.0 — rides 3+ converging macro forces (and not STRUCTURAL_WINNER)",
            "TIMING_ARBITRAGE": "TG >= 8.0 AND SN >= 6.0 — narrow entry window",
            "CAPITAL_MOAT": "CE >= 8.0 AND SN >= 6.0 — cash-flow positive within 6 months",
            "FEAR_ECONOMY": "Arises from fear friction: macro_source contains 'fear' or sector fear_friction_gap > 3",
            "EMERGING_CATEGORY": "Doesn't map to existing NAICS or macro_source contains 'emerging'",
            "CONDITIONAL": "Composite >= 60 but no other category matched (fallback)",
            "PARKED": "Composite < 60 (fallback)"
        },
        "notes": [
            "Models can have MULTIPLE categories assigned as a list",
            "primary_category is the first matched in priority order",
            "GEOGRAPHIC_PLAY removed — replaced by EC axis, no equivalent category",
            "Batch normalization applied: v3-2_cycle (SN -1.5, FA -1.5, TG -2.5), new_macro_45 (SN -0.5, FA -0.3, TG -0.5)"
        ]
    }

    # Compute summary stats
    composites = [m["composite"] for m in models]
    summary = {
        "total_models": len(models),
        "deduplicated_from": models_before,
        "variants_merged": total_merged,
        "batch_normalization_applied": True,
        "gg_replaced_with_ec": True,
        "composite_stats": {
            "max": round(max(composites), 2),
            "min": round(min(composites), 2),
            "mean": round(sum(composites) / len(composites), 2),
            "median": round(sorted(composites)[len(composites) // 2], 2)
        },
        "composite_distribution": {
            "above_80": sum(1 for c in composites if c >= 80),
            "70_to_80": sum(1 for c in composites if 70 <= c < 80),
            "60_to_70": sum(1 for c in composites if 60 <= c < 70),
            "50_to_60": sum(1 for c in composites if 50 <= c < 60),
            "below_50": sum(1 for c in composites if c < 50),
        },
        "primary_category_distribution": new_primary_dist,
        "all_category_distribution": new_all_dist,
        "source_batch_counts": batch_counts,
    }

    # Build top_50 for the output (mirrors input format)
    top_50 = []
    for m in models[:50]:
        entry = {
            "rank": m["rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "primary_category": m["primary_category"],
            "category": m["category"],
            "scores": m["scores"],
            "architecture": m.get("architecture", ""),
            "source_batch": m.get("source_batch", ""),
        }
        if m.get("variants"):
            entry["variants"] = m["variants"]
            entry["variant_count"] = m["variant_count"]
        top_50.append(entry)

    # Build output data
    output = {
        "cycle": "v3-4",
        "date": "2026-02-11",
        "engine_version": "3.4",
        "description": (
            f"Normalized model inventory: batch normalization applied, "
            f"GG replaced with EC (External Context), categories hard-enforced "
            f"with multi-category assignment, deduplicated. "
            f"{len(models)} models after dedup (from {models_before})."
        ),
        "rating_system": rating_system,
        "summary": summary,
        "top_50": top_50,
        "models": models,
    }

    # Write output
    print(f"\nWriting: {OUTPUT_PATH}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    file_size = OUTPUT_PATH.stat().st_size
    print(f"Written: {file_size:,} bytes")

    # -----------------------------------------------------------------------
    # Final summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("NORMALIZATION COMPLETE")
    print("=" * 70)
    print(f"  Input:  {INPUT_PATH.name} ({models_before} models)")
    print(f"  Output: {OUTPUT_PATH.name} ({len(models)} models)")
    print(f"  Deduplication: {total_merged} variants merged into {len(deduped)} groups")
    print(f"\n  Composite stats (post-normalization):")
    print(f"    Max:    {summary['composite_stats']['max']}")
    print(f"    Min:    {summary['composite_stats']['min']}")
    print(f"    Mean:   {summary['composite_stats']['mean']}")
    print(f"    Median: {summary['composite_stats']['median']}")
    print(f"\n  Composite distribution:")
    for bucket, count in summary["composite_distribution"].items():
        print(f"    {bucket}: {count}")
    print(f"\n  Primary category distribution:")
    for cat in ["STRUCTURAL_WINNER", "FORCE_RIDER", "TIMING_ARBITRAGE",
                "CAPITAL_MOAT", "FEAR_ECONOMY", "EMERGING_CATEGORY",
                "CONDITIONAL", "PARKED"]:
        count = new_primary_dist.get(cat, 0)
        print(f"    {cat}: {count}")
    print(f"\n  All-category distribution (multi-assignment):")
    for cat in sorted(new_all_dist.keys()):
        print(f"    {cat}: {new_all_dist[cat]}")

    # Show top 10
    print(f"\n  Top 10 models (post-normalization):")
    for m in models[:10]:
        cats = ", ".join(m["category"])
        print(f"    #{m['rank']:3d}  {m['composite']:6.2f}  [{cats}]  {m['name']}")
        print(f"           SN={m['scores']['SN']:.1f}  FA={m['scores']['FA']:.1f}  "
              f"EC={m['scores']['EC']:.1f}  TG={m['scores']['TG']:.1f}  "
              f"CE={m['scores']['CE']:.1f}  [{m.get('source_batch', '')}]")

    # Show biggest movers (composite delta)
    print(f"\n  Biggest composite changes (sample):")
    # We need to compare against original composites. Rebuild mapping by ID.
    # Re-read original for comparison
    with open(INPUT_PATH, "r") as f:
        orig_data = json.load(f)
    orig_by_id = {m["id"]: m["composite"] for m in orig_data.get("models", [])}

    deltas = []
    for m in models:
        old_c = orig_by_id.get(m["id"])
        if old_c is not None:
            delta = m["composite"] - old_c
            deltas.append((m["id"], m["name"], old_c, m["composite"], delta))

    deltas.sort(key=lambda x: x[4])
    print("    Biggest drops:")
    for mid, name, old_c, new_c, delta in deltas[:5]:
        print(f"      {mid}: {old_c:.2f} -> {new_c:.2f} ({delta:+.2f})  {name}")
    print("    Biggest gains:")
    for mid, name, old_c, new_c, delta in deltas[-5:]:
        print(f"      {mid}: {old_c:.2f} -> {new_c:.2f} ({delta:+.2f})  {name}")


if __name__ == "__main__":
    main()
