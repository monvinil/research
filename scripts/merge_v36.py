#!/usr/bin/env python3
"""
Merge v3-4 normalized inventory (293 models) with v3-6 scored deep dive cards (32 models).
Produces v3-6_normalized_2026-02-12.json with 325 models, sorted by composite descending, re-ranked 1-325.
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
EXISTING_FILE = BASE / "v3-4_normalized_2026-02-11.json"
NEW_FILE = BASE / "v3-6_scored_deep_dive_cards_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-6_normalized_2026-02-12.json"


def load_existing():
    with open(EXISTING_FILE) as f:
        data = json.load(f)
    return data


def load_new():
    with open(NEW_FILE) as f:
        data = json.load(f)
    return data


def normalize_new_card(card):
    """Convert a scored deep dive card to the same field structure as existing models."""
    # Extract flat scores from the nested {score, justification} format
    scores = {}
    for axis in ["SN", "FA", "EC", "TG", "CE"]:
        score_data = card["scores"][axis]
        if isinstance(score_data, dict):
            scores[axis] = score_data["score"]
        else:
            scores[axis] = score_data

    # Category: the deep dive file has a single string; existing models have a list
    category_str = card["category"]
    # Parse category_rationale to find secondary categories
    categories = [category_str]
    rationale = card.get("category_rationale", "")
    # Look for "Also qualifies as X" or "Also X" patterns
    secondary_keywords = [
        "STRUCTURAL_WINNER", "FORCE_RIDER", "TIMING_ARBITRAGE",
        "CAPITAL_MOAT", "FEAR_ECONOMY", "EMERGING_CATEGORY"
    ]
    for kw in secondary_keywords:
        if kw != category_str and kw in rationale and "qualifies" in rationale.lower():
            # Only add if the rationale indicates actual qualification
            if f"qualifies as {kw}" in rationale or f"Also {kw}" in rationale:
                categories.append(kw)

    # Determine primary_category
    primary_category = categories[0]

    model = {
        "id": card["card_id"],
        "name": card["model_name"],
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card["sector_naics"],
        "sector_name": None,  # Not available in deep dive cards
        "architecture": card.get("architecture"),
        "forces_v3": [],  # Will be inferred from scores if possible
        "scores": scores,
        "composite": card["composite"],
        "category": categories,
        "one_liner": None,
        "key_v3_context": None,
        "source_batch": f"v36_deep_dive_{card.get('source_file', 'unknown')}",
        "macro_source": card.get("source_file"),
        "rank": None,  # Will be assigned after sorting
        "primary_category": primary_category,
        "new_in_v36": True,
        # Preserve extra deep-dive data
        "qcew_data_used": card.get("qcew_data_used"),
        "category_rationale": card.get("category_rationale"),
    }

    return model


def main():
    print("Loading existing inventory...")
    existing_data = load_existing()
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models")

    print("Loading new deep dive cards...")
    new_data = load_new()
    new_cards = new_data["scored_cards"]
    print(f"  Loaded {len(new_cards)} new cards")

    # Check for duplicate IDs
    existing_ids = {m["id"] for m in existing_models}
    new_ids = set()
    duplicates = []
    for card in new_cards:
        cid = card["card_id"]
        if cid in existing_ids:
            duplicates.append(cid)
        if cid in new_ids:
            duplicates.append(f"{cid} (duplicate within new cards)")
        new_ids.add(cid)

    if duplicates:
        print(f"  WARNING: Found {len(duplicates)} duplicate IDs: {duplicates}")
    else:
        print("  No duplicate IDs found between existing and new cards")

    # Mark existing models with new_in_v36 = False
    for m in existing_models:
        m["new_in_v36"] = False

    # Normalize new cards
    print("Normalizing new cards...")
    new_models = [normalize_new_card(card) for card in new_cards]

    # Merge
    all_models = existing_models + new_models
    print(f"  Total models before sort: {len(all_models)}")

    # Sort by composite descending
    all_models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Re-rank 1 through 325
    for i, m in enumerate(all_models, 1):
        m["rank"] = i

    # Compute stats
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

    # Category distribution (primary)
    primary_cats = Counter(m["primary_category"] for m in all_models if "primary_category" in m and m["primary_category"])
    # For models without primary_category, use first in category list
    for m in all_models:
        if "primary_category" not in m or not m.get("primary_category"):
            if m["category"]:
                m["primary_category"] = m["category"][0]
            else:
                m["primary_category"] = "PARKED"
    primary_cat_dist = Counter(m["primary_category"] for m in all_models)

    # All-category distribution (counting each category a model belongs to)
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

    # Build top 50
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
            "new_in_v36": m["new_in_v36"],
        })

    # Build output
    output = {
        "cycle": "v3-6",
        "date": "2026-02-12",
        "engine_version": "3.6",
        "description": (
            "Merged normalized model inventory: 293 models from v3-4 normalized + 32 deep dive "
            "model cards from v3-6 (v35 model cards, defense deep dive, education deep dive). "
            "All 325 models sorted by composite descending, re-ranked 1-325. "
            "new_in_v36 boolean identifies the 32 newly added models."
        ),
        "merge_info": {
            "existing_source": "v3-4_normalized_2026-02-11.json",
            "new_source": "v3-6_scored_deep_dive_cards_2026-02-12.json",
            "existing_count": len(existing_models),
            "new_count": len(new_models),
            "duplicate_ids_found": len(duplicates),
            "merge_date": "2026-02-12",
        },
        "rating_system": existing_data["rating_system"],
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_v36_models": len(new_models),
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "all_category_distribution": dict(sorted(all_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "top_50": top_50,
        "models": all_models,
    }

    # Write output
    print(f"Writing {len(all_models)} models to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Validate
    print("Validating output...")
    with open(OUTPUT_FILE) as f:
        validated = json.load(f)

    assert len(validated["models"]) == 325, f"Expected 325 models, got {len(validated['models'])}"
    assert validated["summary"]["total_models"] == 325
    assert validated["models"][0]["rank"] == 1
    assert validated["models"][-1]["rank"] == 325

    # Check sorting
    for i in range(len(validated["models"]) - 1):
        assert validated["models"][i]["composite"] >= validated["models"][i + 1]["composite"], \
            f"Sort violation at rank {i+1}: {validated['models'][i]['composite']} < {validated['models'][i+1]['composite']}"

    # Check new_in_v36 counts
    new_count = sum(1 for m in validated["models"] if m["new_in_v36"])
    old_count = sum(1 for m in validated["models"] if not m["new_in_v36"])
    assert new_count == 32, f"Expected 32 new models, got {new_count}"
    assert old_count == 293, f"Expected 293 existing models, got {old_count}"

    # Check all models have required fields
    required_fields = ["id", "name", "sector_naics", "composite", "category", "scores", "rank", "new_in_v36"]
    score_axes = ["SN", "FA", "EC", "TG", "CE"]
    for m in validated["models"]:
        for field in required_fields:
            assert field in m, f"Model {m.get('id', '?')} missing field: {field}"
        for axis in score_axes:
            assert axis in m["scores"], f"Model {m['id']} missing score axis: {axis}"

    # Check no duplicate IDs in output
    output_ids = [m["id"] for m in validated["models"]]
    assert len(output_ids) == len(set(output_ids)), "Duplicate IDs found in output!"

    print()
    print("=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"  Total models: {len(validated['models'])}")
    print(f"  Existing:     {old_count}")
    print(f"  New (v3-6):   {new_count}")
    print(f"  Composite:    min={composite_stats['min']}, max={composite_stats['max']}, "
          f"mean={composite_stats['mean']}, median={composite_stats['median']}")
    print(f"  Distribution: {comp_dist}")
    print(f"  Categories:   {dict(primary_cat_dist)}")
    print()
    print("  Top 10 models:")
    for m in validated["models"][:10]:
        flag = " [NEW]" if m["new_in_v36"] else ""
        print(f"    {m['rank']:3d}. {m['composite']:5.1f}  {m['id']:<20s}  {m['name'][:50]}{flag}")
    print()
    print("  New v3-6 models placement:")
    for m in validated["models"]:
        if m["new_in_v36"]:
            print(f"    {m['rank']:3d}. {m['composite']:5.1f}  {m['id']:<20s}  {m['name'][:50]}")
    print()
    print(f"  Output: {OUTPUT_FILE}")
    print("  All validations PASSED")


if __name__ == "__main__":
    main()
