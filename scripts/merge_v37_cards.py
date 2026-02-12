#!/usr/bin/env python3
"""
Merge v3-7 model cards from 4 sector deep dives + healthcare monoculture
into the existing v3-7 normalized inventory (345 models).

Input files:
  1. v3-7_normalized_2026-02-12.json              (345 models, the base)
  2. v3-7_it_services_model_cards_2026-02-12.json  (new IT Services cards)
  3. v3-7_securities_model_cards_2026-02-12.json   (new Securities cards)
  4. v3-7_re_mgmt_model_cards_2026-02-12.json      (new RE + Management cards)
  5. v3-7_healthcare_model_cards_2026-02-12.json    (new Healthcare cards)

Produces:
  - v3-7_normalized_final_2026-02-12.json  (full inventory)
  - updates data/ui/models.json            (slim UI format)
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

EXISTING_FILE = BASE / "v3-7_normalized_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-7_normalized_final_2026-02-12.json"
UI_OUTPUT = UI_DIR / "models.json"

NEW_CARD_FILES = [
    BASE / "v3-7_it_services_model_cards_2026-02-12.json",
    BASE / "v3-7_securities_model_cards_2026-02-12.json",
    BASE / "v3-7_re_mgmt_model_cards_2026-02-12.json",
    BASE / "v3-7_healthcare_model_cards_2026-02-12.json",
]

WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}

AXIS_MAP = {
    "SN": "structural_necessity",
    "FA": "force_alignment",
    "EC": "external_context",
    "TG": "timing_grade",
    "CE": "capital_efficiency",
}


def calc_composite(scores):
    return round(sum(scores[axis] * WEIGHTS[axis] for axis in WEIGHTS) / 10, 2)


def extract_score(scores_obj, axis_short, axis_long):
    if axis_short in scores_obj:
        val = scores_obj[axis_short]
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, dict) and "score" in val:
            return val["score"]
    if axis_long in scores_obj:
        val = scores_obj[axis_long]
        if isinstance(val, dict) and "score" in val:
            return val["score"]
        if isinstance(val, (int, float)):
            return val
    raise KeyError(f"Cannot find score for {axis_short}/{axis_long} in {list(scores_obj.keys())}")


def enforce_category(composite, scores, stated_categories, card):
    enforced = []
    if composite >= 80 and scores["SN"] >= 9:
        enforced.append("STRUCTURAL_WINNER")
    if composite >= 70 and scores["FA"] >= 7:
        enforced.append("FORCE_RIDER")
    if scores["TG"] >= 8 and scores["SN"] >= 6:
        enforced.append("TIMING_ARBITRAGE")
    if scores["CE"] >= 8 and scores["SN"] >= 6:
        enforced.append("CAPITAL_MOAT")

    forces = card.get("forces", card.get("forces_v3", []))
    macro = card.get("macro_source", "") or ""
    if any("fear" in str(f).lower() or "F5" in str(f) for f in forces) or "fear" in macro.lower():
        if "FEAR_ECONOMY" in stated_categories or "F5_psychology" in forces:
            enforced.append("FEAR_ECONOMY")
    if "EMERGING_CATEGORY" in stated_categories:
        enforced.append("EMERGING_CATEGORY")

    seen = set()
    unique = []
    for c in enforced:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    enforced = unique

    if not enforced:
        if composite >= 60:
            enforced = ["CONDITIONAL"]
        else:
            enforced = ["PARKED"]
    return enforced


def normalize_new_card(card):
    """Convert a new model card into normalized inventory format."""
    raw_scores = card.get("scores", {})
    scores = {}
    for short, long in AXIS_MAP.items():
        try:
            scores[short] = extract_score(raw_scores, short, long)
        except KeyError:
            print(f"  WARNING: Missing {short} for {card.get('id', '?')}, defaulting to 5.0")
            scores[short] = 5.0

    recalc = calc_composite(scores)

    stated_cat = card.get("category", "")
    cats_list = card.get("categories", [])
    if isinstance(stated_cat, list):
        stated_categories = stated_cat
    elif cats_list:
        stated_categories = cats_list
    else:
        stated_categories = [stated_cat] if stated_cat else []

    categories = enforce_category(recalc, scores, stated_categories, card)
    primary_category = categories[0]

    model = {
        "id": card.get("id", card.get("card_id", "UNKNOWN")),
        "name": card.get("name", card.get("model_name", "Unknown")),
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": card.get("forces", card.get("forces_v3", [])),
        "scores": scores,
        "composite": recalc,
        "composite_stated": card.get("composite"),
        "category": categories,
        "one_liner": card.get("one_liner"),
        "deep_dive_evidence": card.get("deep_dive_evidence"),
        "key_v3_context": None,
        "source_batch": card.get("source_batch", "v37_deep_dive"),
        "macro_source": card.get("macro_source"),
        "rank": None,
        "primary_category": primary_category,
        "new_in_v36": True,
    }
    return model


def build_slim_model(m):
    return {
        "rank": m["rank"],
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "category": m.get("primary_category", m["category"][0] if m["category"] else "PARKED"),
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
    print("MERGE v3-7 CARDS: Sector deep dive model cards into 345-model base")
    print("=" * 70)
    print()

    # Load existing inventory
    print("Loading existing inventory...")
    with open(EXISTING_FILE) as f:
        existing_data = json.load(f)
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models")

    existing_ids = {m["id"] for m in existing_models}

    # Load new card files
    all_new_cards = []
    for card_file in NEW_CARD_FILES:
        if not card_file.exists():
            print(f"  SKIP: {card_file.name} not found")
            continue
        print(f"Loading {card_file.name}...")
        with open(card_file) as f:
            data = json.load(f)
        # Handle multiple formats
        cards = []
        if isinstance(data, list):
            cards = data
        elif "models" in data:
            cards = data["models"]
        elif "cards" in data:
            cards = data["cards"]
        elif "model_cards" in data:
            cards = data["model_cards"]
        else:
            # Check for split-section files (e.g., real_estate_cards + management_cards)
            for key in data:
                if isinstance(data[key], list) and len(data[key]) > 0 and key.endswith("_cards"):
                    print(f"  Found section '{key}' with {len(data[key])} cards")
                    cards.extend(data[key])
            if not cards:
                # Fallback: find any list in the top-level keys
                for key in data:
                    if isinstance(data[key], list) and len(data[key]) > 0:
                        cards = data[key]
                        break
                else:
                    print(f"  WARNING: Cannot find cards array in {card_file.name}")
                    continue
        # Infer source_batch from file-level data or file name
        file_source_batch = data.get("source_batch") if isinstance(data, dict) else None
        if not file_source_batch:
            stem = card_file.stem.lower()
            if "it_services" in stem:
                file_source_batch = "v37_deep_dive_it_services"
            elif "securities" in stem:
                file_source_batch = "v37_deep_dive_securities"
            elif "re_mgmt" in stem:
                file_source_batch = "v37_deep_dive_re_mgmt"
            elif "healthcare" in stem:
                file_source_batch = "v37_healthcare_monoculture"
            else:
                file_source_batch = "v37_deep_dive"
        # Tag cards with source_batch if missing
        for c in cards:
            if "source_batch" not in c:
                c["source_batch"] = file_source_batch
        print(f"  Found {len(cards)} cards total (source_batch={file_source_batch})")
        all_new_cards.extend(cards)

    print(f"\nTotal new cards to merge: {len(all_new_cards)}")

    # Check for collisions
    collisions = []
    new_ids = set()
    for card in all_new_cards:
        cid = card.get("id", card.get("card_id", "?"))
        if cid in existing_ids:
            collisions.append(cid)
        if cid in new_ids:
            collisions.append(f"{cid} (duplicate within new)")
        new_ids.add(cid)

    if collisions:
        print(f"  WARNING: {len(collisions)} collision(s): {collisions[:10]}")
        # Filter out collisions
        all_new_cards = [c for c in all_new_cards
                         if c.get("id", c.get("card_id")) not in existing_ids]
        print(f"  After filtering: {len(all_new_cards)} new cards")

    # Normalize new cards
    print("\nNormalizing new cards...")
    new_models = []
    for card in all_new_cards:
        model = normalize_new_card(card)
        new_models.append(model)
        print(f"  {model['id']}: {model['composite']:.2f} {model['primary_category']:<22s} {model['name'][:50]}")

    # Merge
    all_models = existing_models + new_models
    print(f"\nTotal models after merge: {len(all_models)}")

    # Sort by composite descending
    all_models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Re-rank
    for i, m in enumerate(all_models, 1):
        m["rank"] = i

    # Compute stats
    composites = [m["composite"] for m in all_models]
    composite_stats = {
        "max": max(composites),
        "min": min(composites),
        "mean": round(statistics.mean(composites), 2),
        "median": round(statistics.median(composites), 2),
    }

    primary_cat_dist = Counter(
        m.get("primary_category", m["category"][0] if isinstance(m["category"], list) and m["category"] else "PARKED")
        for m in all_models
    )

    all_cat_dist = Counter()
    for m in all_models:
        cats = m["category"] if isinstance(m["category"], list) else [m["category"]]
        for c in cats:
            all_cat_dist[c] += 1

    comp_dist = {
        "above_80": sum(1 for c in composites if c >= 80),
        "70_to_80": sum(1 for c in composites if 70 <= c < 80),
        "60_to_70": sum(1 for c in composites if 60 <= c < 70),
        "50_to_60": sum(1 for c in composites if 50 <= c < 60),
        "below_50": sum(1 for c in composites if c < 50),
    }

    source_counts = Counter(m.get("source_batch", "unknown") for m in all_models)

    new_count = len(new_models)

    # Build output
    output = {
        "cycle": "v3-7",
        "date": "2026-02-12",
        "engine_version": "3.7",
        "description": (
            f"Full v3-7 normalized inventory: {len(existing_models)} base + "
            f"{new_count} new model cards from IT Services, Securities, "
            f"Real Estate, Management, and Healthcare deep dives. "
            f"All {len(all_models)} models sorted by composite, re-ranked."
        ),
        "rating_system": existing_data.get("rating_system", {}),
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_v37_cards": new_count,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "all_category_distribution": dict(sorted(all_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "models": all_models,
    }

    # Write full output
    print(f"\nWriting {len(all_models)} models to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Write UI models.json
    print(f"Writing UI models.json...")
    ui_models = [build_slim_model(m) for m in all_models]
    ui_output = {
        "cycle": "v3-7",
        "date": "2026-02-12",
        "total": len(all_models),
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_v37_cards": new_count,
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

    # Print summary
    print()
    print("=" * 70)
    print("MERGE COMPLETE")
    print("=" * 70)
    print(f"  Total models: {len(all_models)}")
    print(f"  Base: {len(existing_models)}")
    print(f"  New cards: {new_count}")
    print(f"  Composite: max={composite_stats['max']}, min={composite_stats['min']}, "
          f"mean={composite_stats['mean']}, median={composite_stats['median']}")
    print()
    print("  Distribution:")
    for bucket, count in comp_dist.items():
        print(f"    {bucket:>10s}: {count}")
    print()
    print("  Categories:")
    for cat in sorted(primary_cat_dist.keys()):
        print(f"    {cat:<25s}: {primary_cat_dist[cat]}")
    print()
    print("  Top 20:")
    for m in all_models[:20]:
        flag = " [NEW]" if m.get("source_batch", "").startswith("v37_") else ""
        print(f"    {m['rank']:3d}. {m['composite']:6.2f}  "
              f"{m.get('primary_category', m['category'][0] if isinstance(m['category'], list) else m['category']):<22s}  "
              f"{m['id']:<25s}  {m['name'][:40]}{flag}")
    print()
    print("  New cards placement:")
    for m in all_models:
        if m.get("source_batch", "").startswith("v37_"):
            print(f"    {m['rank']:3d}. {m['composite']:6.2f}  "
                  f"{m.get('primary_category', '?'):<22s}  "
                  f"{m['id']:<25s}  {m['name'][:45]}")
    print()
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  UI:     {UI_OUTPUT}")


if __name__ == "__main__":
    main()
