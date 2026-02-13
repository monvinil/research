#!/usr/bin/env python3
"""
v3-18 UI Refresh: Regenerate models.json and dashboard.json with all v3-18 changes.

Includes:
  - All v3-17 preserved (Polanyi backfill, EQ audit, confidence recalibration, conviction UI)
  - v3-18 Systematic regrading: 5 corrections across 608 models (SN skepticism discount,
    flat profile differentiation, FA validation gate, trust reclassification, PARKED revalidation)
  - v3-18 Gap fill: 42 new models across 3 clusters (architecture gaps, sector gaps, emerging patterns)
  - v3-18 New architectures: open_core_ecosystem, outcome_based, coordination_protocol
  - v3-18 FORCE_RIDER sub-categorization: 7 sub-types (FR_STRUCTURAL, FR_PLATFORM, etc.)

Dashboard updates:
  - engine_version → v3.18
  - enrichment_summary, research_priorities (RPS-based)

State updates:
  - state_version → 28
  - current_cycle → v3-18
  - engine_version description updated
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")
STATE_FILE = Path("/Users/mv/Documents/research/data/context/state.json")

NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
UI_MODELS = UI_DIR / "models.json"
UI_DASHBOARD = UI_DIR / "dashboard.json"


def build_slim_model(m):
    """Build UI-facing slim model with triple ranking + v3-15 enrichment."""
    cla = m.get("cla", {})
    vcr = m.get("vcr", {})
    roi = vcr.get("roi_estimate", {})

    slim = {
        "rank": m["rank"],
        "opportunity_rank": m.get("opportunity_rank"),
        "vcr_rank": m.get("vcr_rank"),
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "opportunity_composite": cla.get("composite"),
        "vcr_composite": vcr.get("composite"),
        "vcr_roi_multiple": roi.get("seed_roi_multiple"),
        "vcr_exit_val_M": roi.get("exit_val_M"),
        "category": m.get("primary_category", m["category"][0] if isinstance(m.get("category"), list) and m["category"] else "PARKED"),
        "opportunity_category": cla.get("category"),
        "vcr_category": vcr.get("category"),
        "categories": m["category"] if isinstance(m.get("category"), list) else [m.get("category", "PARKED")],
        "scores": m["scores"],
        "cla_scores": cla.get("scores"),
        "vcr_scores": vcr.get("scores"),
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "source_batch": m.get("source_batch"),
        "new_in_v36": m.get("new_in_v36", False),
        "one_liner": m.get("one_liner"),
        "sector_name": m.get("sector_name"),
        # v3-13 enrichment fields
        "confidence_tier": m.get("confidence_tier"),
        "evidence_quality": m.get("evidence_quality"),
        "falsification_criteria": m.get("falsification_criteria"),
        "forces": m.get("forces_v3"),
        # Rationales — the "why" behind scores
        "cla_rationale": cla.get("rationale"),
        "vcr_rationale": vcr.get("rationale"),
        "deep_dive_evidence": m.get("deep_dive_evidence") if isinstance(m.get("deep_dive_evidence"), str) else None,
    }

    # v3-18 FORCE_RIDER sub-type
    fr_sub = m.get("force_rider_subtype")
    if fr_sub:
        slim["force_rider_subtype"] = fr_sub

    # Polanyi — only include key metrics, not full SOC lists
    pol = m.get("polanyi")
    if pol:
        slim["polanyi"] = {
            "automation_exposure": pol.get("automation_exposure"),
            "dominant_category": pol.get("dominant_category"),
        }

    # Decomposition fields
    if m.get("decomposed"):
        slim["decomposed"] = True
        slim["sub_model_count"] = m.get("sub_model_count")
        slim["sub_model_opp_range"] = m.get("sub_model_opp_range")
    if m.get("parent_id"):
        slim["parent_id"] = m["parent_id"]
        slim["layer"] = m.get("layer")
        slim["layer_name"] = m.get("layer_name")
        slim["granularity_type"] = m.get("granularity_type")

    # Catalyst scenario (v3-16)
    cat_sc = m.get("catalyst_scenario")
    if cat_sc:
        slim["catalyst_scenario"] = {
            "cluster": cat_sc.get("cluster"),
            "cluster_name": cat_sc.get("cluster_name"),
            "current_composite": cat_sc.get("current_composite"),
            "conditional_composite": cat_sc.get("conditional_composite"),
            "asymmetry_ratio": cat_sc.get("asymmetry_ratio"),
            "timeline": cat_sc.get("timeline"),
            "propagation_chain": cat_sc.get("propagation_chain"),
            "triggers": [
                {"event": t["event"], "probability_2yr": t["probability_2yr"], "probability_5yr": t["probability_5yr"]}
                for t in cat_sc.get("triggers", [])
            ],
        }

    return slim


def main():
    print("=" * 70)
    print("v3-18 UI REFRESH: Structured Review + Gap Fill")
    print("=" * 70)
    print()

    # Load normalized file
    print("Loading normalized inventory...")
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"  Loaded {len(models)} models")

    # ── Compute enrichment statistics ──
    print("Computing enrichment statistics...")

    # Confidence tiers
    tier_dist = Counter(m.get("confidence_tier", "UNKNOWN") for m in models)
    eq_scores = [m.get("evidence_quality", 0) for m in models]
    eq_stats = {
        "mean": round(statistics.mean(eq_scores), 2),
        "median": round(statistics.median(eq_scores), 1),
        "max": max(eq_scores),
        "min": min(eq_scores),
    }

    # Polanyi
    pol_models = [m for m in models if m.get("polanyi")]
    ae_scores = [m["polanyi"]["automation_exposure"] for m in pol_models]
    pol_stats = {
        "models_with_polanyi": len(pol_models),
        "models_without": len(models) - len(pol_models),
        "automation_exposure_mean": round(statistics.mean(ae_scores), 3) if ae_scores else None,
        "automation_exposure_median": round(statistics.median(ae_scores), 3) if ae_scores else None,
        "automation_exposure_range": [round(min(ae_scores), 3), round(max(ae_scores), 3)] if ae_scores else None,
    }
    dom_cat_dist = Counter(m["polanyi"]["dominant_category"] for m in pol_models)

    # Architecture
    arch_dist = Counter(m.get("architecture", "MISSING") for m in models)

    # Falsification criteria
    fals_count = sum(1 for m in models if m.get("falsification_criteria"))
    total_criteria = sum(len(m.get("falsification_criteria", [])) for m in models)
    all_criteria = []
    for m in models:
        all_criteria.extend(m.get("falsification_criteria", []))
    unique_criteria = len(set(all_criteria))

    # FORCE_RIDER sub-types (v3-18)
    fr_subtype_dist = Counter(
        m.get("force_rider_subtype", "none")
        for m in models if m.get("force_rider_subtype")
    )

    enrichment_summary = {
        "confidence_tier_distribution": dict(sorted(tier_dist.items())),
        "evidence_quality_stats": eq_stats,
        "polanyi_stats": pol_stats,
        "polanyi_dominant_category_distribution": dict(sorted(dom_cat_dist.items())),
        "architecture_distribution": dict(sorted(arch_dist.items(), key=lambda x: -x[1])),
        "architecture_canonical_types": len(arch_dist),
        "falsification_criteria_coverage": f"{fals_count}/{len(models)}",
        "falsification_unique_criteria": unique_criteria,
        "falsification_total_criteria": total_criteria,
        "force_rider_subtype_distribution": dict(sorted(fr_subtype_dist.items(), key=lambda x: -x[1])),
    }

    print(f"  Confidence: {dict(tier_dist)}")
    print(f"  Evidence quality: mean={eq_stats['mean']}, median={eq_stats['median']}")
    print(f"  Polanyi: {len(pol_models)}/{len(models)} models")
    print(f"  Architecture types: {len(arch_dist)}")
    print(f"  Falsification: {fals_count}/{len(models)} models, {unique_criteria} unique criteria")
    print()

    # ── Rebuild VCR stats (unchanged from v3-12 but needed for UI) ──
    vcr_composites = [m["vcr"]["composite"] for m in models]
    vcr_stats = {
        "max": max(vcr_composites),
        "min": min(vcr_composites),
        "mean": round(statistics.mean(vcr_composites), 2),
        "median": round(statistics.median(vcr_composites), 2),
    }
    vcr_cat_dist = Counter(m["vcr"]["category"] for m in models)
    vcr_comp_dist = {
        "above_75": sum(1 for c in vcr_composites if c >= 75),
        "60_to_75": sum(1 for c in vcr_composites if 60 <= c < 75),
        "45_to_60": sum(1 for c in vcr_composites if 45 <= c < 60),
        "30_to_45": sum(1 for c in vcr_composites if 30 <= c < 45),
        "below_30": sum(1 for c in vcr_composites if c < 30),
    }
    roi_multiples = [m["vcr"]["roi_estimate"]["seed_roi_multiple"] for m in models]
    roi_stats = {
        "max": max(roi_multiples),
        "min": min(roi_multiples),
        "mean": round(statistics.mean(roi_multiples), 1),
        "median": round(statistics.median(roi_multiples), 1),
        "above_10x": sum(1 for r in roi_multiples if r >= 10),
        "above_20x": sum(1 for r in roi_multiples if r >= 20),
        "above_50x": sum(1 for r in roi_multiples if r >= 50),
    }

    # ── Write UI models.json ──
    print("Writing UI models.json...")
    ui_models = [build_slim_model(m) for m in models]

    # Load VCR system definition from normalized data
    vcr_system = data.get("rating_system", {}).get("vcr_system", {})

    ui_output = {
        "cycle": "v3-18",
        "date": "2026-02-12",
        "total": len(models),
        "dual_ranking": True,
        "triple_ranking": True,
        "granularity_layer": True,
        "enrichment": True,
        "vcr_system": vcr_system,
        "summary": {
            "total_models": len(models),
            "composite_stats": data["summary"].get("composite_stats", {}),
            "primary_category_distribution": data["summary"].get("primary_category_distribution", {}),
            "opportunity_stats": data["summary"].get("opportunity_stats", {}),
            "opportunity_category_distribution": data["summary"].get("opportunity_category_distribution", {}),
            "vcr_stats": vcr_stats,
            "vcr_distribution": vcr_comp_dist,
            "vcr_category_distribution": dict(sorted(vcr_cat_dist.items())),
            "vcr_roi_stats": roi_stats,
        },
        "enrichment_summary": enrichment_summary,
        "models": ui_models,
    }
    with open(UI_MODELS, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)
    print(f"  Written: {UI_MODELS} ({len(ui_models)} models)")

    # ── Update dashboard.json ──
    print("Updating dashboard.json...")
    with open(UI_DASHBOARD) as f:
        dashboard = json.load(f)

    dashboard["engine_version"] = "v3.18"
    dashboard["current_cycle"] = "v3-18"
    dashboard["total_models_rated"] = len(models)
    dashboard["enrichment"] = True
    dashboard["enrichment_summary"] = enrichment_summary

    # Update evidence base model count
    if "evidence_base" in dashboard:
        dashboard["evidence_base"]["v3_models_rated"] = len(models)

    # Update stats (top-level in dashboard, not nested under "summary")
    dashboard["vcr_stats"] = vcr_stats
    dashboard["vcr_roi_stats"] = roi_stats
    dashboard["vcr_category_distribution"] = dict(sorted(vcr_cat_dist.items()))

    # Rebuild top 20 triple actionable with canonical architectures
    models_by_vcr = sorted(models, key=lambda m: (-m["vcr"]["composite"], m["id"]))
    tri_ranked = sorted(models,
        key=lambda m: -(
            m["composite"] *
            m.get("cla", {}).get("composite", 1) *
            m.get("vcr", {}).get("composite", 1)
        ) ** (1/3))
    top20_tri = []
    for m in tri_ranked[:20]:
        tri_score = round((
            m["composite"] *
            m.get("cla", {}).get("composite", 1) *
            m.get("vcr", {}).get("composite", 1)
        ) ** (1/3), 2)
        top20_tri.append({
            "tri_score": tri_score,
            "transformation_rank": m["rank"],
            "opportunity_rank": m.get("opportunity_rank"),
            "vcr_rank": m.get("vcr_rank"),
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m.get("cla", {}).get("composite"),
            "vcr_composite": m.get("vcr", {}).get("composite"),
            "seed_roi_multiple": m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple"),
            "architecture": m.get("architecture"),
            "confidence_tier": m.get("confidence_tier"),
        })
    dashboard["top_20_tri_actionable"] = top20_tri

    # Rebuild top 20 by VCR ROI
    top20_vcr = []
    for m in models_by_vcr[:20]:
        roi = m["vcr"]["roi_estimate"]
        top20_vcr.append({
            "vcr_rank": m["vcr_rank"],
            "transformation_rank": m["rank"],
            "opportunity_rank": m.get("opportunity_rank"),
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m.get("cla", {}).get("composite"),
            "vcr_composite": m["vcr"]["composite"],
            "vcr_category": m["vcr"]["category"],
            "seed_roi_multiple": roi["seed_roi_multiple"],
            "exit_val_M": roi["exit_val_M"],
            "architecture": m.get("architecture"),
            "vcr_scores": m["vcr"]["scores"],
        })
    dashboard["top_20_by_vcr_roi"] = top20_vcr

    # Rebuild architecture breakdown with canonical types
    arch_data = {}
    for m in models:
        a = m.get("architecture", "unknown")
        if a not in arch_data:
            arch_data[a] = {"count": 0, "eco_sum": 0, "moa_sum": 0, "roi_sum": 0}
        arch_data[a]["count"] += 1
        arch_data[a]["eco_sum"] += m["vcr"]["scores"]["ECO"]
        arch_data[a]["moa_sum"] += m["vcr"]["scores"]["MOA"]
        arch_data[a]["roi_sum"] += m["vcr"]["roi_estimate"]["seed_roi_multiple"]
    arch_breakdown = []
    for a, d in sorted(arch_data.items(), key=lambda x: -x[1]["roi_sum"]/x[1]["count"]):
        if d["count"] >= 2:
            arch_breakdown.append({
                "architecture": a,
                "count": d["count"],
                "avg_eco": round(d["eco_sum"] / d["count"], 1),
                "avg_moa": round(d["moa_sum"] / d["count"], 1),
                "avg_roi_multiple": round(d["roi_sum"] / d["count"], 1),
            })
    dashboard["vcr_architecture_breakdown"] = arch_breakdown

    # Update evidence base
    dashboard["evidence_base"]["enrichment_dimensions"] = [
        "confidence_tiers", "evidence_quality", "falsification_criteria",
        "polanyi_automation", "architecture_normalization"
    ]

    # ── Sector-level aggregation (new for v3-14 review) ──
    sector_agg = {}
    for m in models:
        naics = (m.get("sector_naics") or "")[:2]
        sname = m.get("sector_name", "")
        if not naics:
            continue
        if naics not in sector_agg:
            sector_agg[naics] = {
                "sector_naics": naics,
                "sector_name": sname,
                "count": 0,
                "t_sum": 0, "opp_sum": 0, "vcr_sum": 0,
                "structural_winners": 0,
                "fund_returners": 0,
                "high_confidence": 0,
                "architectures": Counter(),
            }
        s = sector_agg[naics]
        s["count"] += 1
        s["t_sum"] += m["composite"]
        s["opp_sum"] += m.get("cla", {}).get("composite", 0)
        s["vcr_sum"] += m.get("vcr", {}).get("composite", 0)
        cats = m.get("category", [])
        if isinstance(cats, list) and "STRUCTURAL_WINNER" in cats:
            s["structural_winners"] += 1
        if m.get("vcr", {}).get("category") == "FUND_RETURNER":
            s["fund_returners"] += 1
        if m.get("confidence_tier") == "HIGH":
            s["high_confidence"] += 1
        s["architectures"][m.get("architecture", "unknown")] += 1
    sector_summary = []
    for naics, s in sorted(sector_agg.items(), key=lambda x: -x[1]["count"]):
        top_arch = s["architectures"].most_common(1)[0] if s["architectures"] else ("unknown", 0)
        sector_summary.append({
            "sector_naics": naics,
            "sector_name": s["sector_name"],
            "model_count": s["count"],
            "avg_t": round(s["t_sum"] / s["count"], 1),
            "avg_opp": round(s["opp_sum"] / s["count"], 1),
            "avg_vcr": round(s["vcr_sum"] / s["count"], 1),
            "structural_winners": s["structural_winners"],
            "fund_returners": s["fund_returners"],
            "high_confidence": s["high_confidence"],
            "top_architecture": top_arch[0],
            "top_architecture_count": top_arch[1],
        })
    dashboard["sector_model_aggregation"] = sector_summary

    # ── Force convergence analysis ──
    force_counts = Counter()
    force_convergence = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for m in models:
        forces = m.get("forces_v3", [])
        normalized = set()
        for f in forces:
            key = f[:2] if f.startswith("F") else f
            normalized.add(key)
        for f in normalized:
            force_counts[f] += 1
        n = len(normalized)
        if n > 0:
            force_convergence[min(n, 5)] = force_convergence.get(min(n, 5), 0) + 1
    dashboard["force_model_distribution"] = dict(sorted(force_counts.items()))
    dashboard["force_convergence"] = {
        f"{k}_forces": v for k, v in sorted(force_convergence.items())
    }

    # ── Research priority queue: RPS-based (v3-17) ──
    # RPS = composite_potential * 0.40 + evidence_gap * 0.35 + coverage_impact * 0.25
    # Prioritizes MODERATE confidence where marginal research has most impact
    naics_counts = Counter((m.get("sector_naics") or "")[:2] for m in models)
    research_priorities = []
    for m in models:
        eq = m.get("evidence_quality", 0)
        tier = m.get("confidence_tier", "LOW")
        t_comp = m.get("composite", 0)
        tier_mult = {"HIGH": 1, "MODERATE": 3, "LOW": 2}.get(tier, 2)
        composite_potential = (10 - eq) * tier_mult * max(t_comp / 100, 0.5)
        evidence_gap = 10 - eq
        naics2 = (m.get("sector_naics") or "")[:2]
        nc = naics_counts.get(naics2, 1)
        coverage_impact = min(nc, 10) if nc >= 20 else (8 if nc >= 10 else (5 if nc >= 5 else nc))
        rps = composite_potential * 0.40 + evidence_gap * 0.35 + coverage_impact * 0.25
        research_priorities.append({
            "rank": m["rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m.get("cla", {}).get("composite"),
            "vcr_composite": m.get("vcr", {}).get("composite"),
            "confidence_tier": tier,
            "evidence_quality": eq,
            "architecture": m.get("architecture"),
            "rps_score": round(rps, 2),
        })
    research_priorities.sort(key=lambda x: -x["rps_score"])
    dashboard["research_priorities"] = research_priorities[:30]

    # ── Catalyst summary (v3-16) ──
    catalyst_models = [m for m in models if m.get("catalyst_scenario")]
    if catalyst_models:
        cluster_summary = Counter(m["catalyst_scenario"]["cluster"] for m in catalyst_models)
        ratios = [m["catalyst_scenario"]["asymmetry_ratio"] for m in catalyst_models]
        dashboard["catalyst_summary"] = {
            "total_catalyst_models": len(catalyst_models),
            "cluster_distribution": dict(sorted(cluster_summary.items(), key=lambda x: -x[1])),
            "asymmetry_ratio_range": [round(min(ratios), 2), round(max(ratios), 2)],
            "asymmetry_ratio_mean": round(statistics.mean(ratios), 2),
        }

    with open(UI_DASHBOARD, "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    print(f"  Written: {UI_DASHBOARD}")

    # ── Update state.json ──
    print("Updating state.json...")
    with open(STATE_FILE) as f:
        state = json.load(f)

    state["state_version"] = 28
    state["current_cycle"] = "v3-18"
    state["engine_version"] = (
        "3.18 — 'Structured Review + Gap Fill': 650 models, 18 architectures. "
        "(1) Systematic regrading: 5 corrections across 608 models — SN skepticism discount (70 models), "
        "flat profile differentiation (34), FA validation gate (4), trust reclassification (15), "
        "PARKED revalidation (68→CONDITIONAL). "
        "(2) Gap fill: 42 new models across 3 clusters — 19 architecture gap (open_core_ecosystem, "
        "outcome_based, coordination_protocol), 12 sector gap (wholesale/arts/utilities), "
        "11 emerging patterns (agent-as-a-service, human-premium, temporal extraction). "
        "(3) 3 new architecture types with full scoring support (CLA, VCR, SN substitutability). "
        "(4) FORCE_RIDER sub-categorization: 327 models → 7 sub-types "
        "(FR_STRUCTURAL, FR_PLATFORM, FR_VERTICAL, FR_SERVICE, FR_CONSOLIDATION, FR_COMPLIANCE, FR_GENERAL). "
        "(5) All v3-17 preserved (Polanyi 608/608, EQ grading, confidence tiers, conviction UI, catalysts)."
    )

    # Update rated_models_index
    rmi = state.get("rated_models_index", {})
    rmi["enrichment_dimensions"] = {
        "confidence_tiers": dict(sorted(tier_dist.items())),
        "evidence_quality_mean": eq_stats["mean"],
        "polanyi_coverage": f"{len(pol_models)}/{len(models)}",
        "architecture_canonical_types": len(arch_dist),
        "falsification_unique_criteria": unique_criteria,
    }

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  Written: {STATE_FILE}")

    # ── Summary ──
    print()
    print("=" * 70)
    print("v3-18 UI REFRESH COMPLETE")
    print("=" * 70)
    print()
    print(f"  Models: {len(models)}")
    print(f"  Confidence tiers: HIGH={tier_dist.get('HIGH',0)}, MODERATE={tier_dist.get('MODERATE',0)}, LOW={tier_dist.get('LOW',0)}")
    print(f"  Evidence quality: mean={eq_stats['mean']}, median={eq_stats['median']}")
    print(f"  Polanyi coverage: {len(pol_models)}/{len(models)}")
    print(f"  Architecture types: {len(arch_dist)} canonical")
    print(f"  Falsification: {unique_criteria} unique criteria across {fals_count} models")
    print()
    print("  Files updated:")
    print(f"    {UI_MODELS}")
    print(f"    {UI_DASHBOARD}")
    print(f"    {STATE_FILE}")
    print()
    print("  Top 5 Triple Actionable (with confidence):")
    for m in top20_tri[:5]:
        print(f"    {m['tri_score']:>6.2f}  [{m['confidence_tier']}]  {m['name']}  ({m['architecture']})")


if __name__ == "__main__":
    main()
