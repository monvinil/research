#!/usr/bin/env python3
"""
Merge v3-10 'Granularity Layer' sub-models from decomposition analysis
into the existing v3-9 inventory (435 models).

v3-10 adds VALUE CHAIN LAYER sub-models for FORTIFIED parent models.
Sub-models are linked to parents via parent_id and layer number.
Parent models are preserved and annotated with decomposition metadata.

Input files:
  1. v3-9_normalized_2026-02-12.json               (435 models, the base)
  2. v3-10_decomposition_commercial_2026-02-12.json (Retail Media + Warehouse Robotics)
  3. v3-10_decomposition_defense_2026-02-12.json    (6 Defense models)
  4. v3-10_decomposition_utilities_2026-02-12.json  (Nuclear + Solar/Storage)

Produces:
  - v3-10_normalized_2026-02-12.json  (full inventory with sub-models)
  - updates data/ui/models.json       (slim UI format with dual ranking)
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

EXISTING_FILE = BASE / "v3-9_normalized_2026-02-12.json"
OUTPUT_FILE = BASE / "v3-10_normalized_2026-02-12.json"
UI_OUTPUT = UI_DIR / "models.json"

DECOMPOSITION_FILES = [
    BASE / "v3-10_decomposition_commercial_2026-02-12.json",
    BASE / "v3-10_decomposition_defense_2026-02-12.json",
    BASE / "v3-10_decomposition_utilities_2026-02-12.json",
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
    """Determine categories from scores."""
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


def normalize_sub_model(sub):
    """Convert a decomposition sub-model into normalized inventory format."""
    scores = sub.get("scores", {})

    # Ensure all axes exist
    for axis in WEIGHTS:
        if axis not in scores:
            # Try inherited + independent
            inherited = sub.get("inherited_scores", {})
            independent = sub.get("independent_scores", {})
            if axis in inherited:
                scores[axis] = inherited[axis]
            elif axis in independent:
                scores[axis] = independent[axis]
            else:
                print(f"  WARNING: Missing {axis} for {sub.get('id', '?')}, defaulting to 5.0")
                scores[axis] = 5.0

    recalc = calc_composite(scores)

    # CLA
    cla_raw = sub.get("cla", {})
    cla_scores_raw = cla_raw.get("scores", {})
    if all(k in cla_scores_raw for k in CLA_WEIGHTS):
        opp_comp = calc_opp_composite(cla_scores_raw)
        cla = {
            "scores": cla_scores_raw,
            "composite": opp_comp,
            "category": classify_opportunity(opp_comp),
            "rationale": cla_raw.get("rationale", "From decomposition analysis"),
        }
    else:
        cla = {
            "scores": {"MO": 5, "MA": 5, "VD": 5, "DV": 5},
            "composite": 50.0,
            "category": "CONTESTED",
            "rationale": "Default — CLA scores incomplete in decomposition",
        }

    # Categories
    stated_cats = sub.get("category", [])
    if isinstance(stated_cats, str):
        stated_cats = [stated_cats]
    primary_cat = sub.get("primary_category", "")

    # Use enforce_category as base, but preserve FEAR_ECONOMY / EMERGING_CATEGORY if stated
    cats = enforce_category(recalc, scores)
    for c in stated_cats:
        if c in ("FEAR_ECONOMY", "EMERGING_CATEGORY") and c not in cats:
            cats.append(c)
    if primary_cat and primary_cat not in cats:
        cats.insert(0, primary_cat)

    model = {
        "id": sub.get("id", "UNKNOWN"),
        "name": sub.get("name", "Unknown"),
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": sub.get("sector_naics"),
        "sector_name": sub.get("sector_name"),
        "architecture": sub.get("architecture"),
        "forces_v3": sub.get("forces_v3", sub.get("forces", [])),
        "scores": scores,
        "composite": recalc,
        "composite_stated": sub.get("composite"),
        "category": cats,
        "one_liner": sub.get("one_liner"),
        "key_v3_context": None,
        "source_batch": "v310_decomposition",
        "macro_source": sub.get("macro_source"),
        "rank": None,
        "primary_category": cats[0] if cats else "PARKED",
        "new_in_v36": True,
        "cla": cla,
        # Decomposition-specific fields
        "parent_id": sub.get("parent_id"),
        "parent_name": sub.get("parent_name"),
        "layer": sub.get("layer"),
        "layer_name": sub.get("layer_name"),
        "granularity_type": "value_chain_layer",
    }
    return model


def annotate_parent(parent_model, sub_models):
    """Annotate a parent model with decomposition metadata."""
    opp_composites = [s.get("cla", {}).get("composite", 0) for s in sub_models]
    opp_categories = [s.get("cla", {}).get("category", "?") for s in sub_models]
    sub_ids = [s.get("id", "?") for s in sub_models]

    parent_model["decomposed"] = True
    parent_model["sub_model_count"] = len(sub_models)
    parent_model["sub_model_ids"] = sub_ids
    parent_model["sub_model_opp_range"] = [
        min(opp_composites) if opp_composites else 0,
        max(opp_composites) if opp_composites else 0,
    ]
    parent_model["sub_model_opp_categories"] = list(set(opp_categories))

    # Append to CLA rationale
    existing_rationale = parent_model.get("cla", {}).get("rationale", "")
    parent_model.setdefault("cla", {})["rationale"] = (
        f"{existing_rationale} "
        f"DECOMPOSED: {len(sub_models)} sub-models spanning "
        f"{', '.join(sorted(set(opp_categories)))}. "
        f"OPP range [{min(opp_composites):.1f} — {max(opp_composites):.1f}]. "
        f"See sub-models for layer-specific entry analysis."
    ).strip()


def build_slim_model(m):
    cla = m.get("cla", {})
    slim = {
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
    # Add decomposition fields if present
    if m.get("parent_id"):
        slim["parent_id"] = m["parent_id"]
        slim["layer"] = m.get("layer")
        slim["layer_name"] = m.get("layer_name")
        slim["granularity_type"] = "value_chain_layer"
    if m.get("decomposed"):
        slim["decomposed"] = True
        slim["sub_model_count"] = m.get("sub_model_count")
        slim["sub_model_opp_range"] = m.get("sub_model_opp_range")
    return slim


def main():
    print("=" * 70)
    print("MERGE v3-10 'Granularity Layer': Decomposition sub-models into 435-model base")
    print("=" * 70)
    print()

    # Load existing inventory
    print("Loading existing inventory...")
    with open(EXISTING_FILE) as f:
        existing_data = json.load(f)
    existing_models = existing_data["models"]
    print(f"  Loaded {len(existing_models)} existing models")

    existing_ids = {m["id"] for m in existing_models}
    parent_model_map = {m["id"]: m for m in existing_models}

    # Load decomposition files and extract sub-models
    all_sub_models = []
    all_targets = []
    decomp_stats = {
        "files_loaded": 0,
        "targets_analyzed": 0,
        "sub_models_total": 0,
        "layers_rejected": 0,
        "parent_cla_confirmed": 0,
    }

    for decomp_file in DECOMPOSITION_FILES:
        if not decomp_file.exists():
            print(f"\n  SKIP: {decomp_file.name} not found")
            continue
        print(f"\nLoading {decomp_file.name}...")
        with open(decomp_file) as f:
            data = json.load(f)

        decomp_stats["files_loaded"] += 1
        targets = data.get("decomposition_targets", [])
        all_targets.extend(targets)

        for target in targets:
            decomp_stats["targets_analyzed"] += 1
            parent_id = target.get("parent_id", "?")
            sub_models = target.get("sub_models", [])
            rejected = target.get("layers_rejected", [])

            # Only take sub-models that pass IVB test
            passing = [s for s in sub_models
                       if s.get("ivb_test", {}).get("passes", False)]

            decomp_stats["sub_models_total"] += len(passing)
            decomp_stats["layers_rejected"] += len(rejected) + len(sub_models) - len(passing)

            if not passing:
                decomp_stats["parent_cla_confirmed"] += 1

            print(f"  {parent_id}: {len(passing)} sub-models pass IVB "
                  f"({len(rejected)} + {len(sub_models) - len(passing)} rejected)")

            all_sub_models.extend(passing)

            # Annotate parent model
            if parent_id in parent_model_map and passing:
                annotate_parent(parent_model_map[parent_id], passing)

    print(f"\nTotal sub-models to merge: {len(all_sub_models)}")

    # Check for ID collisions
    new_ids = set()
    collisions = []
    for sub in all_sub_models:
        sid = sub.get("id", "?")
        if sid in existing_ids:
            collisions.append(sid)
        if sid in new_ids:
            collisions.append(f"{sid} (duplicate)")
        new_ids.add(sid)

    if collisions:
        print(f"  WARNING: {len(collisions)} collision(s): {collisions[:10]}")
        all_sub_models = [s for s in all_sub_models if s.get("id") not in existing_ids]

    # Normalize sub-models
    print("\nNormalizing sub-models...")
    new_models = []
    for sub in all_sub_models:
        model = normalize_sub_model(sub)
        new_models.append(model)
        cla_info = f" OPP={model['cla']['composite']:.1f} {model['cla']['category']}"
        parent_info = f" (parent: {model.get('parent_id', '?')} L{model.get('layer', '?')})"
        print(f"  {model['id']}: {model['composite']:.2f} {model['primary_category']:<18s}"
              f"{cla_info}  {model['name'][:40]}{parent_info}")

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

    opp_dist = {
        "above_75": sum(1 for c in opp_composites if c >= 75),
        "60_to_75": sum(1 for c in opp_composites if 60 <= c < 75),
        "45_to_60": sum(1 for c in opp_composites if 45 <= c < 60),
        "30_to_45": sum(1 for c in opp_composites if 30 <= c < 45),
        "below_30": sum(1 for c in opp_composites if c < 30),
    }

    source_counts = Counter(m.get("source_batch", "unknown") for m in all_models)

    # Count sub-models vs regular
    sub_model_count = sum(1 for m in all_models if m.get("parent_id"))
    decomposed_parent_count = sum(1 for m in all_models if m.get("decomposed"))

    # Build output
    output = {
        "cycle": "v3-10",
        "date": "2026-02-12",
        "engine_version": "3.10",
        "description": (
            f"v3-10 'Granularity Layer' cycle: {len(existing_models)} base + "
            f"{len(new_models)} value chain sub-models from decomposition of "
            f"{decomp_stats['targets_analyzed']} FORTIFIED parent models. "
            f"First standardized granularity analysis. "
            f"{decomposed_parent_count} parent models annotated with decomposition metadata. "
            f"{decomp_stats['parent_cla_confirmed']} parent CLAs confirmed accurate (all layers equally FORTIFIED). "
            f"All {len(all_models)} models sorted by composite, re-ranked on both dimensions."
        ),
        "rating_system": existing_data.get("rating_system", {}),
        "summary": {
            "total_models": len(all_models),
            "existing_models": len(existing_models),
            "new_sub_models": len(new_models),
            "decomposition_stats": decomp_stats,
            "decomposed_parents": decomposed_parent_count,
            "composite_stats": composite_stats,
            "composite_distribution": comp_dist,
            "primary_category_distribution": dict(sorted(primary_cat_dist.items())),
            "opportunity_stats": opp_stats,
            "opportunity_distribution": opp_dist,
            "opportunity_category_distribution": dict(sorted(opp_cat_dist.items())),
            "source_batch_counts": dict(sorted(source_counts.items())),
        },
        "granularity_framework": {
            "version": "1.0",
            "trigger": "FORTIFIED/LOCKED + VD >= 4 + (T_rank <= 50 OR sector_emp >= 1M OR (T_comp >= 75 AND OPP <= 45))",
            "method": "Value chain layer analysis with Independently Viable Business Test",
            "scoring": "FA/EC inherited from parent; SN/TG/CE re-scored; CLA fully independent",
            "id_convention": "Parent ID + -L[N]",
            "one_level_only": True,
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
        "cycle": "v3-10",
        "date": "2026-02-12",
        "total": len(all_models),
        "dual_ranking": True,
        "granularity_layer": True,
        "summary": output["summary"],
        "models": ui_models,
    }
    with open(UI_OUTPUT, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)

    # Print summary
    print()
    print("=" * 70)
    print("MERGE COMPLETE — v3-10 'Granularity Layer'")
    print("=" * 70)
    print(f"  Total models: {len(all_models)}")
    print(f"  Base (v3-9): {len(existing_models)}")
    print(f"  New sub-models: {len(new_models)}")
    print(f"  Decomposed parents: {decomposed_parent_count}")
    print(f"  Parent CLAs confirmed: {decomp_stats['parent_cla_confirmed']}")
    print(f"  Transformation: max={composite_stats['max']}, mean={composite_stats['mean']:.2f}, median={composite_stats['median']:.2f}")
    print(f"  Opportunity:    max={opp_stats['max']}, mean={opp_stats['mean']:.2f}, median={opp_stats['median']:.2f}")
    print()

    print("  Opportunity Category Distribution:")
    for cat in sorted(opp_cat_dist.keys()):
        print(f"    {cat:<15s}: {opp_cat_dist[cat]}")
    print()

    # Show decomposed parents and their sub-models
    print("  Decomposed Parents → Sub-Models:")
    for m in all_models:
        if m.get("decomposed"):
            opp_range = m.get("sub_model_opp_range", [0, 0])
            sub_cats = m.get("sub_model_opp_categories", [])
            print(f"    {m['id']}: T#{m['rank']} OPP={m.get('cla',{}).get('composite',0):.1f} "
                  f"→ {m.get('sub_model_count', 0)} sub-models "
                  f"(OPP range [{opp_range[0]:.1f} — {opp_range[1]:.1f}], categories: {', '.join(sorted(sub_cats))})")
    print()

    # Show all sub-models
    print("  All Sub-Models:")
    for m in all_models:
        if m.get("parent_id"):
            opp_c = m.get("cla", {}).get("composite", 0)
            opp_cat = m.get("cla", {}).get("category", "?")
            print(f"    T#{m['rank']:3d}  O#{m.get('opportunity_rank', 0):3d}  "
                  f"TC={m['composite']:5.1f}  OC={opp_c:5.1f}  {opp_cat:<12s}  "
                  f"{m['id']:<35s}  {m['name'][:40]}")
    print()

    # Top 20 actionable (including sub-models)
    print("  Top 20 ACTIONABLE (geometric mean, includes sub-models):")
    actionable = sorted(all_models,
        key=lambda m: -(m["composite"] * m.get("cla", {}).get("composite", 1)) ** 0.5)
    for m in actionable[:20]:
        opp_c = m.get("cla", {}).get("composite", 0)
        geo = (m["composite"] * opp_c) ** 0.5 if opp_c > 0 else 0
        is_sub = " [SUB]" if m.get("parent_id") else ""
        print(f"    {geo:6.2f}  T#{m['rank']:3d}  O#{m.get('opportunity_rank', 0):3d}  "
              f"TC={m['composite']:5.1f}  OC={opp_c:5.1f}  "
              f"{m['id']:<35s}  {m['name'][:35]}{is_sub}")
    print()
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  UI:     {UI_OUTPUT}")


if __name__ == "__main__":
    main()
