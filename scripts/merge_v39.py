#!/usr/bin/env python3
"""
Merge v3-9 model cards from Manufacturing + Micro-Firm deep dives
into the existing v3-8 inventory (413 models).

Also integrates CLA refinements from mid-tier assessment.

Input files:
  1. v3-8_normalized_2026-02-12.json              (413 models, the base — already has CLA)
  2. v3-9_manufacturing_deep_dive_2026-02-12.json  (12 new Manufacturing cards)
  3. v3-9_micro_firm_deep_dive_2026-02-12.json     (10 new Micro-Firm cards)
  4. v3-9_cla_refinement_2026-02-12.json           (CLA override updates for mid-tier models)

Produces:
  - v3-9_normalized_2026-02-12.json  (full inventory)
  - updates data/ui/models.json      (slim UI format with dual ranking)
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

EXISTING_FILE = BASE / "v3-8_normalized_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-9_normalized_2026-02-12.json"
UI_OUTPUT = UI_DIR / "models.json"

NEW_CARD_FILES = [
    BASE / "v3-9_manufacturing_deep_dive_2026-02-12.json",
    BASE / "v3-9_micro_firm_deep_dive_2026-02-12.json",
]

CLA_REFINEMENT_FILE = BASE / "v3-9_cla_refinement_2026-02-12.json"

WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}
CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}

AXIS_MAP = {
    "SN": "structural_necessity",
    "FA": "force_alignment",
    "EC": "external_context",
    "TG": "timing_grade",
    "CE": "capital_efficiency",
}


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
    """Convert a new model card into normalized inventory format, including CLA."""
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

    # Extract CLA if present in the card
    cla_raw = card.get("competitive_landscape_assessment", {})
    cla = None
    if cla_raw and all(k in cla_raw for k in ("MO", "MA", "VD", "DV")):
        cla_scores = {
            "MO": cla_raw["MO"],
            "MA": cla_raw["MA"],
            "VD": cla_raw["VD"],
            "DV": cla_raw["DV"],
        }
        opp_comp = calc_opp_composite(cla_scores)
        cla = {
            "scores": cla_scores,
            "composite": opp_comp,
            "category": classify_opportunity(opp_comp),
            "rationale": cla_raw.get("rationale", "From deep dive assessment"),
        }

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
        "source_batch": card.get("source_batch", "v39_deep_dive"),
        "macro_source": card.get("macro_source"),
        "rank": None,
        "primary_category": primary_category,
        "new_in_v36": True,
    }

    if cla:
        model["cla"] = cla

    return model


def build_slim_model(m):
    cla = m.get("cla", {})
    return {
        "rank": m["rank"],
        "opportunity_rank": m.get("opportunity_rank"),
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "opportunity_composite": cla.get("composite"),
        "category": m.get("primary_category", m["category"][0] if m["category"] else "PARKED"),
        "opportunity_category": cla.get("category"),
        "categories": m["category"],
        "scores": m["scores"],
        "cla_scores": cla.get("scores"),
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "source_batch": m.get("source_batch"),
        "new_in_v36": m.get("new_in_v36", False),
        "one_liner": m.get("one_liner"),
    }


def main():
    print("=" * 70)
    print("MERGE v3-9 CARDS: Manufacturing + Micro-Firm into 413-model base")
    print("=" * 70)
    print()

    # Load existing inventory
    print("Loading existing inventory...")
    with open(EXISTING_FILE) as f:
        existing_data = json.load(f)
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models")

    existing_ids = {m["id"] for m in existing_models}

    # Load CLA refinements and apply to existing models
    cla_updates = 0
    if CLA_REFINEMENT_FILE.exists():
        print(f"\nLoading CLA refinements from {CLA_REFINEMENT_FILE.name}...")
        with open(CLA_REFINEMENT_FILE) as f:
            cla_data = json.load(f)
        overrides = cla_data.get("overrides", {})
        print(f"  Found {len(overrides)} CLA overrides")

        for model in existing_models:
            mid = model["id"]
            if mid in overrides:
                o = overrides[mid]
                cla_scores = {"MO": o["MO"], "MA": o["MA"], "VD": o["VD"], "DV": o["DV"]}
                opp_comp = calc_opp_composite(cla_scores)
                model["cla"] = {
                    "scores": cla_scores,
                    "composite": opp_comp,
                    "category": classify_opportunity(opp_comp),
                    "rationale": o.get("rationale", "CLA refinement override"),
                }
                cla_updates += 1
        print(f"  Applied {cla_updates} CLA updates to existing models")

    # Load new card files
    all_new_cards = []
    for card_file in NEW_CARD_FILES:
        if not card_file.exists():
            print(f"\n  SKIP: {card_file.name} not found")
            continue
        print(f"\nLoading {card_file.name}...")
        with open(card_file) as f:
            data = json.load(f)
        cards = []
        if isinstance(data, list):
            cards = data
        elif "model_cards" in data:
            cards = data["model_cards"]
        elif "models" in data:
            cards = data["models"]
        elif "cards" in data:
            cards = data["cards"]
        else:
            # Check top-level lists
            for key in data:
                if isinstance(data[key], list) and len(data[key]) > 0:
                    if key.endswith("_cards") or key == "model_cards":
                        cards.extend(data[key])
            # Check nested dicts for model_cards (e.g. section_5_model_cards.model_cards)
            if not cards:
                for key in data:
                    if isinstance(data[key], dict) and "model_cards" in data[key]:
                        nested = data[key]["model_cards"]
                        if isinstance(nested, list) and len(nested) > 0:
                            cards.extend(nested)
            if not cards:
                for key in data:
                    if isinstance(data[key], list) and len(data[key]) > 0:
                        cards = data[key]
                        break

        file_source_batch = data.get("source_batch") if isinstance(data, dict) else None
        if not file_source_batch:
            stem = card_file.stem.lower()
            if "manufacturing" in stem:
                file_source_batch = "v39_deep_dive_manufacturing"
            elif "micro_firm" in stem:
                file_source_batch = "v39_deep_dive_micro_firm"
            else:
                file_source_batch = "v39_deep_dive"
        for c in cards:
            if "source_batch" not in c:
                c["source_batch"] = file_source_batch
        print(f"  Found {len(cards)} cards (source_batch={file_source_batch})")
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
        all_new_cards = [c for c in all_new_cards
                         if c.get("id", c.get("card_id")) not in existing_ids]
        print(f"  After filtering: {len(all_new_cards)} new cards")

    # Normalize new cards
    print("\nNormalizing new cards...")
    new_models = []
    for card in all_new_cards:
        model = normalize_new_card(card)
        new_models.append(model)
        cla_info = ""
        if "cla" in model:
            cla_info = f" OPP={model['cla']['composite']:.1f} {model['cla']['category']}"
        print(f"  {model['id']}: {model['composite']:.2f} {model['primary_category']:<22s}{cla_info}  {model['name'][:45]}")

    # Assign default CLA to new models without one (heuristic fallback)
    for model in new_models:
        if "cla" not in model:
            # Import heuristic from cla_scoring if available
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from cla_scoring import heuristic_cla, calc_opp_composite as cla_calc, classify_opportunity as cla_classify
                mo, ma, vd, dv, rationale = heuristic_cla(model)
                opp = cla_calc(mo, ma, vd, dv)
                model["cla"] = {
                    "scores": {"MO": mo, "MA": ma, "VD": vd, "DV": dv},
                    "composite": opp,
                    "category": cla_classify(opp),
                    "rationale": rationale,
                }
            except ImportError:
                # Fallback: use architecture-based defaults
                model["cla"] = {
                    "scores": {"MO": 5, "MA": 5, "VD": 5, "DV": 5},
                    "composite": 50.0,
                    "category": "CONTESTED",
                    "rationale": "Default — no CLA assessment available",
                }

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

    # Re-sort by transformation rank for output
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
        "cycle": "v3-9",
        "date": "2026-02-12",
        "engine_version": "3.9",
        "description": (
            f"v3-9 'Opportunity First' cycle: {len(existing_models)} base + "
            f"{new_count} new model cards from Manufacturing and Micro-Firm deep dives. "
            f"First manufacturing coverage (12.4M workers). First micro-firm emerging category deep dive. "
            f"Dual ranking active: Transformation + Opportunity (CLA). "
            f"{cla_updates} CLA refinements applied to existing models. "
            f"All {len(all_models)} models sorted by composite, re-ranked on both dimensions."
        ),
        "rating_system": existing_data.get("rating_system", {}),
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_v39_cards": new_count,
            "cla_refinements": cla_updates,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "opportunity_stats": opp_stats,
            "opportunity_category_distribution": dict(sorted(opp_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "models": all_models,
    }

    # Write full output
    print(f"\nWriting {len(all_models)} models to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Write UI models.json
    print("Writing UI models.json...")
    ui_models = [build_slim_model(m) for m in all_models]
    ui_output = {
        "cycle": "v3-9",
        "date": "2026-02-12",
        "total": len(all_models),
        "dual_ranking": True,
        "summary": output["summary"],
        "models": ui_models,
    }
    with open(UI_OUTPUT, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)

    # Print summary
    print()
    print("=" * 70)
    print("MERGE COMPLETE — v3-9 'Opportunity First'")
    print("=" * 70)
    print(f"  Total models: {len(all_models)}")
    print(f"  Base: {len(existing_models)}")
    print(f"  New cards: {new_count}")
    print(f"  CLA refinements: {cla_updates}")
    print(f"  Transformation: max={composite_stats['max']}, mean={composite_stats['mean']}, median={composite_stats['median']}")
    print(f"  Opportunity:    max={opp_stats['max']}, mean={opp_stats['mean']}, median={opp_stats['median']}")
    print()

    print("  Top 20 by TRANSFORMATION (with Opportunity Rank):")
    print(f"  {'T#':>3s}  {'O#':>3s}  {'TComp':>6s}  {'OComp':>6s}  {'TCat':<22s}  {'OCat':<12s}  Name")
    for m in all_models[:20]:
        opp_c = m.get("cla", {}).get("composite", 0)
        opp_cat = m.get("cla", {}).get("category", "?")
        print(f"  {m['rank']:3d}  {m.get('opportunity_rank', 0):3d}  "
              f"{m['composite']:6.2f}  {opp_c:6.2f}  "
              f"{m.get('primary_category', '?'):<22s}  {opp_cat:<12s}  "
              f"{m['name'][:45]}")
    print()

    print("  Top 20 ACTIONABLE (geometric mean):")
    actionable = sorted(all_models,
        key=lambda m: -(m["composite"] * m.get("cla", {}).get("composite", 1)) ** 0.5)
    for m in actionable[:20]:
        opp_c = m.get("cla", {}).get("composite", 0)
        geo = (m["composite"] * opp_c) ** 0.5 if opp_c > 0 else 0
        print(f"  {geo:6.2f}  T#{m['rank']:3d}  O#{m.get('opportunity_rank', 0):3d}  "
              f"TC={m['composite']:5.1f}  OC={opp_c:5.1f}  "
              f"{m['id']:<30s}  {m['name'][:40]}")
    print()

    # New v3-9 cards placement
    print("  New v3-9 cards placement:")
    for m in all_models:
        if m.get("source_batch", "").startswith("v39_"):
            opp_c = m.get("cla", {}).get("composite", 0)
            opp_cat = m.get("cla", {}).get("category", "?")
            print(f"    T#{m['rank']:3d}  O#{m.get('opportunity_rank', 0):3d}  "
                  f"TC={m['composite']:5.1f}  OC={opp_c:5.1f}  {opp_cat:<12s}  "
                  f"{m['id']:<30s}  {m['name'][:40]}")
    print()
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  UI:     {UI_OUTPUT}")


if __name__ == "__main__":
    main()
