#!/usr/bin/env python3
"""
Merge v3-12 'Coverage Expansion' deep dive models into existing inventory.

v3-12 adds models from 4 previously uncovered sectors:
  1. Accommodation & Food Services (NAICS 72) — 16.5M workers
  2. Transportation & Warehousing (NAICS 48-49) — 6.7M workers
  3. Construction (NAICS 23) — 8.0M workers
  4. Admin/Support/Waste Management (NAICS 56) — 9.4M workers

These 4 sectors represent ~50M workers (30% of US employment) that had
minimal coverage (43 models across all 4, zero deep dives).

Input:
  - v3-10_normalized_2026-02-12.json (454 models with VCR from v3-11)
  - v3-12_accommodation_food_deep_dive_2026-02-12.json
  - v3-12_transportation_deep_dive_2026-02-12.json
  - v3-12_construction_deep_dive_2026-02-12.json
  - v3-12_admin_support_deep_dive_2026-02-12.json

Output:
  - v3-12_normalized_2026-02-12.json  (full inventory with new models)

VCR scoring is NOT done here — run scripts/vcr_scoring.py separately after merge.
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

EXISTING_FILE = BASE / "v3-10_normalized_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-12_normalized_2026-02-12.json"

DEEP_DIVE_FILES = [
    BASE / "v3-12_accommodation_food_deep_dive_2026-02-12.json",
    BASE / "v3-12_transportation_deep_dive_2026-02-12.json",
    BASE / "v3-12_construction_deep_dive_2026-02-12.json",
    BASE / "v3-12_admin_support_deep_dive_2026-02-12.json",
]

WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}
CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}


def calc_composite(scores):
    return round(sum(scores[axis] * WEIGHTS[axis] for axis in WEIGHTS) / 10, 2)


def calc_opp_composite(cla_scores):
    return round(sum(cla_scores[axis] * CLA_WEIGHTS[axis] for axis in CLA_WEIGHTS) / 10, 2)


def classify_opportunity(opp):
    if opp >= 75: return "WIDE_OPEN"
    elif opp >= 60: return "ACCESSIBLE"
    elif opp >= 45: return "CONTESTED"
    elif opp >= 30: return "FORTIFIED"
    else: return "LOCKED"


def enforce_category(composite, scores):
    cats = []
    if composite >= 80 and scores.get("SN", 0) >= 9:
        cats.append("STRUCTURAL_WINNER")
    if composite >= 70 and scores.get("FA", 0) >= 7:
        cats.append("FORCE_RIDER")
    if scores.get("TG", 0) >= 8 and scores.get("SN", 0) >= 6:
        cats.append("TIMING_ARBITRAGE")
    if scores.get("CE", 0) >= 8 and scores.get("SN", 0) >= 6:
        cats.append("CAPITAL_MOAT")
    if not cats:
        if composite >= 60:
            cats = ["CONDITIONAL"]
        else:
            cats = ["PARKED"]
    return cats


def extract_scores(card):
    """Extract 5-axis scores from various card formats."""
    scores_raw = card.get("scores", {})
    scores = {}

    # Map both short and long axis names
    name_map = {
        "SN": "SN", "structural_necessity": "SN", "Structural Necessity": "SN",
        "FA": "FA", "force_alignment": "FA", "Force Alignment": "FA",
        "EC": "EC", "external_context": "EC", "External Context": "EC",
        "TG": "TG", "timing_growth": "TG", "Timing/Growth": "TG",
        "CE": "CE", "capital_efficiency": "CE", "Capital Efficiency": "CE",
    }

    for raw_key, val in scores_raw.items():
        mapped = name_map.get(raw_key, raw_key)
        if mapped in WEIGHTS:
            scores[mapped] = float(val) if isinstance(val, (int, float)) else 5.0

    # Ensure all axes present
    for axis in WEIGHTS:
        if axis not in scores:
            print(f"    WARNING: Missing {axis} for {card.get('id', '?')}, defaulting to 5.0")
            scores[axis] = 5.0

    return scores


def extract_cla(card):
    """Extract CLA from competitive_landscape_assessment or cla field."""
    # Try cla field first
    cla_raw = card.get("cla", {})
    if not cla_raw:
        cla_raw = card.get("competitive_landscape_assessment", {})

    cla_scores = {}
    if isinstance(cla_raw, dict):
        for key in ("MO", "MA", "VD", "DV"):
            if key in cla_raw:
                cla_scores[key] = float(cla_raw[key])
            elif key.lower() in cla_raw:
                cla_scores[key] = float(cla_raw[key.lower()])

        # Check nested scores dict
        inner_scores = cla_raw.get("scores", {})
        for key in ("MO", "MA", "VD", "DV"):
            if key not in cla_scores and key in inner_scores:
                cla_scores[key] = float(inner_scores[key])

    if all(k in cla_scores for k in CLA_WEIGHTS):
        opp_comp = calc_opp_composite(cla_scores)
        return {
            "scores": cla_scores,
            "composite": opp_comp,
            "category": classify_opportunity(opp_comp),
            "rationale": cla_raw.get("rationale", "From v3-12 deep dive"),
        }
    else:
        print(f"    WARNING: Incomplete CLA for {card.get('id', '?')}, using defaults")
        default_scores = {"MO": 5, "MA": 5, "VD": 5, "DV": 5}
        return {
            "scores": default_scores,
            "composite": 50.0,
            "category": "CONTESTED",
            "rationale": "Default — CLA scores incomplete in deep dive",
        }


def normalize_card(card, source_batch):
    """Convert a deep dive model card into normalized inventory format."""
    scores = extract_scores(card)
    recalc = calc_composite(scores)
    cla = extract_cla(card)
    cats = enforce_category(recalc, scores)

    # Preserve special categories if stated
    stated_cats = card.get("category", [])
    if isinstance(stated_cats, str):
        stated_cats = [stated_cats]
    for c in stated_cats:
        if c in ("FEAR_ECONOMY", "EMERGING_CATEGORY") and c not in cats:
            cats.append(c)

    # Get forces from various formats
    forces = card.get("forces_v3", card.get("forces", []))

    model = {
        "id": card.get("id", "UNKNOWN"),
        "name": card.get("name", "Unknown"),
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": forces,
        "scores": scores,
        "composite": recalc,
        "composite_stated": card.get("composite"),
        "category": cats,
        "one_liner": card.get("one_liner"),
        "key_v3_context": None,
        "source_batch": source_batch,
        "macro_source": card.get("macro_source"),
        "rank": None,
        "primary_category": cats[0] if cats else "PARKED",
        "new_in_v36": True,
        "cla": cla,
        "deep_dive_evidence": card.get("deep_dive_evidence"),
        "falsification_criteria": card.get("falsification_criteria"),
        "vcr_evidence": card.get("vcr_evidence"),
    }
    return model


def extract_model_cards(data):
    """Extract model cards from deep dive JSON — handles various nesting patterns."""
    # Direct model_cards key
    cards = data.get("model_cards", [])
    if cards:
        return cards

    # Nested in section dict (manufacturing/micro-firm pattern)
    for key, val in data.items():
        if isinstance(val, dict):
            if "model_cards" in val:
                return val["model_cards"]

    # Try other common keys
    for key in ("models", "cards"):
        if key in data and isinstance(data[key], list):
            return data[key]

    return []


def main():
    print("=" * 70)
    print("MERGE v3-12 'Coverage Expansion': 4 sector deep dives into 454-model base")
    print("=" * 70)
    print()

    # Load existing inventory
    print("Loading existing inventory...")
    with open(EXISTING_FILE) as f:
        existing_data = json.load(f)
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models")

    existing_ids = {m["id"] for m in existing_models}

    # Load deep dive files
    all_new_cards = []
    file_counts = {}

    for dd_file in DEEP_DIVE_FILES:
        if not dd_file.exists():
            print(f"\n  SKIP: {dd_file.name} not found")
            continue

        print(f"\nLoading {dd_file.name}...")
        with open(dd_file) as f:
            data = json.load(f)

        cards = extract_model_cards(data)
        source_batch = f"v3-12_{data.get('sector_naics', 'unknown')}"
        sector_name = data.get("sector", dd_file.stem)

        print(f"  Found {len(cards)} model cards for {sector_name}")
        file_counts[sector_name] = len(cards)

        for card in cards:
            card["_source_batch"] = source_batch

        all_new_cards.extend(cards)

    print(f"\nTotal new cards to merge: {len(all_new_cards)}")

    # Check for ID collisions
    new_ids = set()
    collisions = []
    for card in all_new_cards:
        cid = card.get("id", "?")
        if cid in existing_ids:
            collisions.append(cid)
        if cid in new_ids:
            collisions.append(f"{cid} (duplicate)")
        new_ids.add(cid)

    if collisions:
        print(f"  WARNING: {len(collisions)} collision(s): {collisions[:10]}")
        all_new_cards = [c for c in all_new_cards if c.get("id") not in existing_ids]

    # Normalize all new cards
    print("\nNormalizing new model cards...")
    new_models = []
    for card in all_new_cards:
        model = normalize_card(card, card.get("_source_batch", "v3-12"))
        new_models.append(model)
        opp_info = f"OPP={model['cla']['composite']:.1f} {model['cla']['category']}"
        print(f"  {model['id']:<25s} {model['composite']:5.2f} {model['primary_category']:<18s} "
              f"{opp_info:<25s} {model['name'][:40]}")

    # Merge
    all_models = existing_models + new_models
    print(f"\nTotal models after merge: {len(all_models)}")

    # Sort by composite descending (Transformation Rank)
    all_models.sort(key=lambda m: (-m["composite"], m["id"]))
    for i, m in enumerate(all_models, 1):
        m["rank"] = i

    # Sort by OPP composite for Opportunity Rank
    models_by_opp = sorted(all_models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(models_by_opp, 1):
        m["opportunity_rank"] = i

    # Re-sort by transformation rank
    all_models.sort(key=lambda m: m["rank"])

    # Compute stats
    composites = [m["composite"] for m in all_models]
    composite_stats = {
        "max": max(composites),
        "min": min(composites),
        "mean": round(statistics.mean(composites), 2),
        "median": round(statistics.median(composites), 2),
    }

    opp_composites = [m.get("cla", {}).get("composite", 0) for m in all_models]
    opp_stats = {
        "max": max(opp_composites),
        "min": min(opp_composites),
        "mean": round(statistics.mean(opp_composites), 2),
        "median": round(statistics.median(opp_composites), 2),
    }

    primary_cat_dist = Counter(
        m.get("primary_category", m["category"][0] if isinstance(m["category"], list) and m["category"] else "PARKED")
        for m in all_models
    )
    opp_cat_dist = Counter(m.get("cla", {}).get("category", "?") for m in all_models)
    source_counts = Counter(m.get("source_batch", "unknown") for m in all_models)

    comp_dist = {
        "above_80": sum(1 for c in composites if c >= 80),
        "70_to_80": sum(1 for c in composites if 70 <= c < 80),
        "60_to_70": sum(1 for c in composites if 60 <= c < 70),
        "50_to_60": sum(1 for c in composites if 50 <= c < 60),
        "below_50": sum(1 for c in composites if c < 50),
    }

    opp_dist = {
        "above_75": sum(1 for c in opp_composites if c >= 75),
        "60_to_75": sum(1 for c in opp_composites if 60 <= c < 75),
        "45_to_60": sum(1 for c in opp_composites if 45 <= c < 60),
        "30_to_45": sum(1 for c in opp_composites if 30 <= c < 45),
        "below_30": sum(1 for c in opp_composites if c < 30),
    }

    # Sub-model and decomposition stats preserved from v3-10
    sub_model_count = sum(1 for m in all_models if m.get("parent_id"))
    decomposed_parent_count = sum(1 for m in all_models if m.get("decomposed"))

    # Build output
    output = {
        "cycle": "v3-12",
        "date": "2026-02-12",
        "engine_version": "3.12",
        "description": (
            f"v3-12 'Coverage Expansion': {len(existing_models)} existing + "
            f"{len(new_models)} new models from 4 sector deep dives "
            f"(Accommodation/Food, Transportation, Construction, Admin/Support). "
            f"Covers 50M+ additional workers (30% of US employment). "
            f"VCR v2 fundamental scoring with independent capture/velocity analysis. "
            f"All {len(all_models)} models ranked on Transformation, Opportunity, and VC ROI."
        ),
        "rating_system": existing_data.get("rating_system", {}),
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_models_v312": len(new_models),
            "new_model_sources": file_counts,
            "sub_models": sub_model_count,
            "decomposed_parents": decomposed_parent_count,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "opportunity_stats": opp_stats,
            "opportunity_distribution": opp_dist,
            "opportunity_category_distribution": dict(sorted(opp_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "granularity_framework": existing_data.get("granularity_framework",
            existing_data.get("summary", {}).get("granularity_framework")),
        "models": all_models,
    }

    # Write output
    print(f"\nWriting {len(all_models)} models to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print()
    print("=" * 70)
    print(f"MERGE COMPLETE — v3-12 'Coverage Expansion'")
    print("=" * 70)
    print(f"  Total models: {len(all_models)}")
    print(f"  Existing:     {len(existing_models)}")
    print(f"  New (v3-12):  {len(new_models)}")
    print()

    for sector, count in file_counts.items():
        print(f"    {sector}: {count} models")
    print()

    print(f"  Transformation: max={composite_stats['max']}, mean={composite_stats['mean']:.2f}")
    print(f"  Opportunity:    max={opp_stats['max']}, mean={opp_stats['mean']:.2f}")
    print()

    print("  Opportunity Category Distribution:")
    for cat in ["WIDE_OPEN", "ACCESSIBLE", "CONTESTED", "FORTIFIED", "LOCKED"]:
        print(f"    {cat:<15s}: {opp_cat_dist.get(cat, 0)}")
    print()

    print(f"  Source Batches:")
    for batch, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"    {batch:<35s}: {count}")
    print()

    # Show new models ranked by composite
    print("  New Models by Transformation Rank:")
    new_sorted = sorted(new_models, key=lambda m: -m["composite"])
    for m in new_sorted:
        opp_c = m.get("cla", {}).get("composite", 0)
        print(f"    T#{m['rank']:3d}  O#{m.get('opportunity_rank', 0):3d}  "
              f"TC={m['composite']:5.1f}  OC={opp_c:5.1f}  "
              f"{m.get('cla',{}).get('category','?'):<12s}  "
              f"{m['id']:<25s}  {m['name'][:40]}")
    print()
    print(f"  Output: {OUTPUT_FILE}")
    print(f"\n  NEXT STEP: Run python3 scripts/vcr_scoring.py to add VCR scores to new models")


if __name__ == "__main__":
    main()
