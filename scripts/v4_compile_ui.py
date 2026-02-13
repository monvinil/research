#!/usr/bin/env python3
"""
v4.1 UI Compilation: Generate model-first UI JSON files with narrative context.

Reads:
  - data/v4/narratives.json (scored narratives with model links)
  - data/v4/models.json (650 models with narrative_ids)
  - data/v4/collisions.json
  - data/v4/cascades.json
  - data/v4/geographies.json
  - data/v4/state.json

Writes:
  - data/ui/dashboard.json (updated for v4)
  - data/ui/narratives.json (slim narrative data for UI)
  - data/ui/models.json (updated with narrative_ids)
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data/v4"
UI_DIR = BASE / "data/ui"


def build_slim_narrative(n):
    """Build slim narrative for UI display."""
    tns = n.get("tns", {})
    outputs = n.get("outputs", {})

    return {
        "narrative_id": n["narrative_id"],
        "name": n["name"],
        "slug": n.get("slug", ""),
        "tns_composite": tns.get("composite", 0),
        "tns_category": tns.get("category", "SPECULATIVE"),
        "tns_rank": tns.get("rank", 999),
        "tns_scores": {
            "EM": tns.get("economic_magnitude", 0),
            "FC": tns.get("force_convergence", 0),
            "ES": tns.get("evidence_strength", 0),
            "TC": tns.get("timing_confidence", 0),
            "IR": tns.get("irreversibility", 0),
        },
        "sectors": n.get("sectors", []),
        "forces": n.get("forces_acting", []),
        "transformation_phase": n.get("transformation_phase", ""),
        "summary": n.get("summary", "")[:500],
        "year_by_year": n.get("year_by_year", {}),
        "geographic_variation": n.get("geographic_variation", {}),
        "outputs": {
            "what_works": outputs.get("what_works", []),
            "whats_needed": outputs.get("whats_needed", []),
            "what_dies": outputs.get("what_dies", []),
        },
        "model_counts": {
            "what_works": len(outputs.get("what_works", [])),
            "whats_needed": len(outputs.get("whats_needed", [])),
            "what_dies": len(outputs.get("what_dies", [])),
            "total": sum(len(outputs.get(b, [])) for b in ["what_works", "whats_needed", "what_dies"]),
        },
        "cascade_dependencies": n.get("cascade_dependencies", {}),
        "fear_friction": n.get("fear_friction", {}),
        "falsification_criteria": n.get("falsification_criteria", []),
        "confidence": n.get("confidence", {}),
        "collision_ids": n.get("collision_ids", []),
    }


def build_slim_model(m):
    """Build slim model for UI display (preserves v3 format + narrative fields)."""
    cla = m.get("cla", {})
    vcr = m.get("vcr", {})

    slim = {
        "rank": m.get("rank"),
        "opportunity_rank": m.get("opportunity_rank"),
        "vcr_rank": m.get("vcr_rank"),
        "id": m["id"],
        "name": m["name"],
        "composite": m.get("composite", 0),
        "opportunity_composite": cla.get("composite"),
        "vcr_composite": vcr.get("composite"),
        "vcr_roi_multiple": vcr.get("roi_estimate", {}).get("seed_roi_multiple") if isinstance(vcr.get("roi_estimate"), dict) else None,
        "category": m.get("primary_category", m.get("category", "")),
        "opportunity_category": cla.get("category"),
        "vcr_category": vcr.get("category"),
        "scores": m.get("scores", {}),
        "cla_scores": cla.get("scores"),
        "vcr_scores": vcr.get("scores"),
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "one_liner": m.get("one_liner"),
        "sector_name": m.get("sector_name"),
        "confidence_tier": m.get("confidence_tier"),
        "evidence_quality": m.get("evidence_quality"),
        "forces": m.get("forces_v3"),
        # v4 fields
        "narrative_ids": m.get("narrative_ids", []),
        "narrative_role": m.get("narrative_role", "unlinked"),
    }

    # Polanyi
    pol = m.get("polanyi")
    if pol:
        slim["polanyi"] = {
            "automation_exposure": pol.get("automation_exposure"),
            "dominant_category": pol.get("dominant_category"),
        }

    return slim


def main():
    print("=" * 70)
    print("v4.1 UI COMPILATION: Generating model-first UI data")
    print("=" * 70)
    print()

    # Load all v4 data
    print("Loading v4 data...")

    with open(V4_DIR / "narratives.json") as f:
        narr_data = json.load(f)
    narratives = narr_data["narratives"]

    with open(V4_DIR / "models.json") as f:
        models_data = json.load(f)
    models = models_data["models"]

    with open(V4_DIR / "collisions.json") as f:
        coll_data = json.load(f)

    with open(V4_DIR / "cascades.json") as f:
        casc_data = json.load(f)

    with open(V4_DIR / "geographies.json") as f:
        geo_data = json.load(f)

    with open(V4_DIR / "state.json") as f:
        state = json.load(f)

    print(f"  {len(narratives)} narratives, {len(models)} models")
    print(f"  {len(coll_data['collisions'])} collisions, {len(casc_data['cascades'])} cascades")
    print(f"  {len(geo_data['geographies'])} geographies")
    print()

    # Build UI narratives
    print("Building UI narratives...")
    ui_narratives = [build_slim_narrative(n) for n in narratives]

    narratives_output = {
        "engine_version": "v4.1",
        "cycle": "v4-0",
        "date": "2026-02-12",
        "total_narratives": len(ui_narratives),
        "tns_system": {
            "axes": {
                "EM": {"name": "Economic Magnitude", "weight": 25, "question": "How large is the GDP/employment impact?"},
                "FC": {"name": "Force Convergence", "weight": 25, "question": "How many forces drive this, how aligned?"},
                "ES": {"name": "Evidence Strength", "weight": 20, "question": "How much hard data confirms direction?"},
                "TC": {"name": "Timing Confidence", "weight": 15, "question": "How confident are we in the timeline?"},
                "IR": {"name": "Irreversibility", "weight": 15, "question": "Once started, can this be reversed?"},
            },
            "composite_formula": "(EM*25 + FC*25 + ES*20 + TC*15 + IR*15) / 10",
            "categories": {
                "DEFINING": ">=80: Economy-reshaping, high confidence",
                "MAJOR": ">=65: Significant with strong evidence",
                "MODERATE": ">=50: Clear direction, moderate evidence",
                "EMERGING": ">=35: Early signals, plausible",
                "SPECULATIVE": "<35: Hypothesis stage",
            },
        },
        "narratives": ui_narratives,
    }

    with open(UI_DIR / "narratives.json", "w") as f:
        json.dump(narratives_output, f, indent=2, ensure_ascii=False)
    print(f"  Written: {UI_DIR / 'narratives.json'} ({len(ui_narratives)} narratives)")

    # Build UI models
    print("Building UI models...")
    ui_models = [build_slim_model(m) for m in models]

    # Model summary for UI filters
    model_cat_dist = Counter(m.get("primary_category", m.get("category", "")) for m in models if m.get("primary_category") or m.get("category"))
    model_opp_dist = Counter(m.get("cla", {}).get("category", "") for m in models if m.get("cla", {}).get("category"))
    model_vcr_dist = Counter(m.get("vcr", {}).get("category", "") for m in models if m.get("vcr", {}).get("category"))

    models_output = {
        "engine_version": "v4.1",
        "cycle": "v4-0",
        "date": "2026-02-12",
        "total": len(ui_models),
        "dual_ranking": True,
        "triple_ranking": True,
        "narrative_linked": True,
        "summary": {
            "category_distribution": dict(sorted(model_cat_dist.items())),
            "opp_category_distribution": dict(sorted(model_opp_dist.items())),
            "vcr_category_distribution": dict(sorted(model_vcr_dist.items())),
        },
        "models": ui_models,
    }

    with open(UI_DIR / "models.json", "w") as f:
        json.dump(models_output, f, indent=2, ensure_ascii=False)
    print(f"  Written: {UI_DIR / 'models.json'} ({len(ui_models)} models)")

    # Build dashboard
    print("Building dashboard...")
    tns_composites = [n["tns"]["composite"] for n in narratives]
    tns_cat_dist = Counter(n["tns"]["category"] for n in narratives)

    # Force velocities — full format for UI renderForces()
    force_names = {
        "F1_technology": "Technology & AI",
        "F2_demographics": "Demographics & Labor",
        "F3_geopolitics": "Geopolitics & Trade",
        "F4_capital": "Capital & Financial",
        "F5_psychology": "Psychology & Sentiment",
        "F6_energy": "Energy & Resources",
    }
    raw_forces = state.get("force_velocities", {})
    force_summary = {}
    force_velocities_ui = {}
    for fid, fv in raw_forces.items():
        force_summary[fid] = {
            "velocity": fv.get("velocity", "steady"),
            "confidence": fv.get("confidence", "medium"),
        }
        # Full force data for renderForces()
        km = fv.get("key_metrics", {})
        key_data = []
        for k, v in list(km.items())[:5]:
            val = str(v)
            if len(val) > 120:
                val = val[:117] + "..."
            key_data.append(f"{k.replace('_', ' ').title()}: {val}")
        force_velocities_ui[fid] = {
            "name": force_names.get(fid, fid),
            "velocity": fv.get("velocity", "steady"),
            "confidence": fv.get("confidence", "medium"),
            "key_metric": fv.get("direction", "")[:200] if fv.get("direction") else "",
            "key_data": key_data,
            "2031_projection": "",
        }

    # Geographic profiles for renderMap()
    geo_emojis = {"US": "🇺🇸", "Japan": "🇯🇵", "China": "🇨🇳", "EU": "🇪🇺",
                  "India": "🇮🇳", "LATAM": "🌎", "SEA": "🌏", "MENA": "🏜️"}
    geo_key_map = {"US": "us", "Japan": "japan", "China": "china", "EU": "eu",
                   "India": "india", "LATAM": "latam", "SEA": "sea", "MENA": "mena"}
    geo_profiles = {}
    for g in geo_data.get("geographies", []):
        rid = g.get("region_id", "")
        key = geo_key_map.get(rid, rid.lower())
        tv = g.get("transformation_velocity", {})
        demo = g.get("demographic_profile", {})
        ai = g.get("ai_readiness", {})
        fastest = tv.get("fastest_sectors", [])
        vel_label = ai.get("adoption_rate", "moderate")
        if vel_label in ("leading", "accelerating"):
            vel_label = "fast — " + vel_label
        elif vel_label == "lagging":
            vel_label = "moderate — " + vel_label
        geo_profiles[key] = {
            "name": g.get("name", rid),
            "emoji": geo_emojis.get(rid, "🌐"),
            "transformation_velocity": vel_label,
            "key_metrics": {
                "median_age": str(demo.get("median_age", "?")),
                "population": demo.get("population_trend", "?"),
                "ai_access": ai.get("frontier_access", "?"),
                "regulation": ai.get("regulatory_stance", "?")[:60],
            },
            "top_forces": fastest[:3],
            "2031_outlook": demo.get("key_pressure", "")[:200],
        }

    # Fear friction index from narrative data
    fear_friction_index = []
    for n in narratives:
        ff = n.get("fear_friction", {})
        if ff and ff.get("economic_readiness"):
            econ = ff.get("economic_readiness", 5)
            psych = ff.get("psychological_readiness", 5)
            fear_friction_index.append({
                "sector": n["name"].replace(" Transformation", ""),
                "economic_readiness": econ,
                "psychological_readiness": psych,
                "fear_friction_gap": round(econ - psych, 1) if isinstance(econ, (int, float)) and isinstance(psych, (int, float)) else 0,
            })
    fear_friction_index.sort(key=lambda x: x.get("fear_friction_gap", 0), reverse=True)

    # Sector transformations from narratives
    sector_transformations = []
    for n in narratives:
        outputs = n.get("outputs", {})
        ww = len(outputs.get("what_works", []))
        wn = len(outputs.get("whats_needed", []))
        wd = len(outputs.get("what_dies", []))
        sectors = n.get("sectors", [])
        naics = sectors[0]["naics"] if sectors else ""
        sector_transformations.append({
            "name": n["name"].replace(" Transformation", ""),
            "naics": str(naics),
            "phase": n.get("transformation_phase", "early_disruption"),
            "employment_2026": "",
            "employment_2031": "",
            "change_pct": 0,
            "top_model": f"{ww} works, {wn} needed, {wd} dies",
        })

    # Force-model distribution
    force_model_dist = Counter()
    for m in models:
        for f in (m.get("forces_v3") or []):
            key = f[:2]  # F1, F2, etc.
            force_model_dist[key] += 1

    # Cascade graph for UI
    cascade_graph = {
        "nodes": [
            {
                "id": n["narrative_id"],
                "name": n["name"],
                "tns": n["tns"]["composite"],
                "category": n["tns"]["category"],
            }
            for n in narratives
        ],
        "edges": [],
    }
    for n in narratives:
        deps = n.get("cascade_dependencies", {})
        for target in deps.get("upstream_of", []):
            cascade_graph["edges"].append({
                "from": n["narrative_id"],
                "to": target,
                "type": "upstream_of",
            })

    dashboard = {
        "engine_version": "v4.1",
        "current_cycle": "v4-0",
        "last_updated": "2026-02-12",
        "architecture": "transformation_narrative",
        "total_narratives": len(narratives),
        "total_models": len(models),
        "total_collisions": len(coll_data["collisions"]),
        "total_cascades": len(casc_data["cascades"]),
        "total_geographies": len(geo_data["geographies"]),
        "tns_stats": {
            "mean": round(statistics.mean(tns_composites), 1),
            "stdev": round(statistics.stdev(tns_composites), 1),
            "min": round(min(tns_composites), 1),
            "max": round(max(tns_composites), 1),
        },
        "tns_category_distribution": dict(sorted(tns_cat_dist.items())),
        "force_summary": force_summary,
        "force_velocities": force_velocities_ui,
        "geographic_profiles": geo_profiles,
        "fear_friction_index": fear_friction_index,
        "sector_transformations": sector_transformations,
        "force_model_distribution": dict(force_model_dist),
        "top_narratives": [
            {
                "narrative_id": n["narrative_id"],
                "name": n["name"],
                "tns_composite": n["tns"]["composite"],
                "tns_category": n["tns"]["category"],
                "sectors": [s["naics"] for s in n.get("sectors", [])],
                "forces": n.get("forces_acting", []),
                "phase": n.get("transformation_phase", ""),
                "model_count": sum(len(n["outputs"].get(b, [])) for b in ["what_works", "whats_needed", "what_dies"]),
            }
            for n in narratives[:10]
        ],
        "cascade_graph": cascade_graph,
        "models_linked": models_data.get("linked_count", 0),
        "models_unlinked": models_data.get("unlinked_count", 0),
    }

    # Model-centric stats for UI KPIs
    t_composites = [m.get("composite", 0) for m in models if m.get("composite")]
    vcr_composites = [m.get("vcr", {}).get("composite", 0) for m in models if m.get("vcr", {}).get("composite")]
    vcr_rois = [m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple", 0) for m in models
                if isinstance(m.get("vcr", {}).get("roi_estimate"), dict) and m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple")]
    cla_composites = [m.get("cla", {}).get("composite", 0) for m in models if m.get("cla", {}).get("composite")]

    # T-Score stats
    if t_composites:
        dashboard["t_score_stats"] = {
            "mean": round(statistics.mean(t_composites), 1),
            "median": round(statistics.median(t_composites), 1),
            "stdev": round(statistics.stdev(t_composites), 1) if len(t_composites) > 1 else 0,
            "min": round(min(t_composites), 1),
            "max": round(max(t_composites), 1),
        }

    # VCR stats
    if vcr_composites:
        vcr_cat_dist = Counter()
        for m in models:
            cat = m.get("vcr", {}).get("category")
            if cat:
                vcr_cat_dist[cat] += 1
        dashboard["vcr_stats"] = {
            "mean": round(statistics.mean(vcr_composites), 1),
            "median": round(statistics.median(vcr_composites), 1),
            "stdev": round(statistics.stdev(vcr_composites), 1) if len(vcr_composites) > 1 else 0,
            "min": round(min(vcr_composites), 1),
            "max": round(max(vcr_composites), 1),
        }
        dashboard["vcr_category_distribution"] = dict(sorted(vcr_cat_dist.items()))

    # VCR ROI stats
    if vcr_rois:
        sorted_rois = sorted(vcr_rois)
        dashboard["vcr_roi_stats"] = {
            "mean": round(statistics.mean(vcr_rois), 1),
            "median": round(statistics.median(vcr_rois), 1),
            "max": round(max(vcr_rois), 1),
            "above_10x": sum(1 for r in vcr_rois if r >= 10),
            "above_50x": sum(1 for r in vcr_rois if r >= 50),
        }

    # Category distribution (T-score categories)
    cat_dist = Counter()
    for m in models:
        cat = m.get("primary_category", m.get("category", ""))
        if cat:
            cat_dist[cat] += 1
    if cat_dist:
        dashboard["model_category_distribution"] = dict(sorted(cat_dist.items()))

    # Opportunity category distribution
    opp_cat_dist = Counter()
    for m in models:
        opp = m.get("cla", {}).get("category")
        if opp:
            opp_cat_dist[opp] += 1
    if opp_cat_dist:
        dashboard["opp_category_distribution"] = dict(sorted(opp_cat_dist.items()))

    with open(UI_DIR / "dashboard.json", "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    print(f"  Written: {UI_DIR / 'dashboard.json'}")

    # Summary
    print()
    print("=" * 70)
    print("v4.1 UI COMPILATION COMPLETE")
    print("=" * 70)
    print()
    print(f"  Models: {len(ui_models)} (primary output)")
    print(f"  Narratives: {len(ui_narratives)} ({tns_cat_dist})")
    print(f"  Linked: {models_data.get('linked_count', 0)} models have narrative context")
    print()
    print("  Top 5 Transformation Narratives:")
    for n in narratives[:5]:
        tns = n["tns"]
        total = sum(len(n["outputs"].get(b, [])) for b in ["what_works", "whats_needed", "what_dies"])
        print(f"    #{tns['rank']}  {tns['composite']:5.1f}  [{tns['category']}]  {n['name'][:50]}  ({total} models)")
    print()
    print("  Files:")
    print(f"    {UI_DIR / 'narratives.json'}")
    print(f"    {UI_DIR / 'models.json'}")
    print(f"    {UI_DIR / 'dashboard.json'}")


if __name__ == "__main__":
    main()
