#!/usr/bin/env python3
"""
v5_requirement_generator.py — Converts tensions into specific external data requirements.

Reads tensions.json (from v5_tension_detector.py) and generates structured
data requirements that replace generic "scan for signals" directives with
specific questions Agent A can answer.

Each requirement has:
  - A specific question derived from the tension
  - Validation data sources to check
  - Clear validate/falsify thresholds
  - Models affected and score impact predictions

Output: data/v5/requirements.json
"""

import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"


def load_json(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Requirement generators per tension type
# ---------------------------------------------------------------------------

def gen_narrative_opportunity_divergence(t, narr_idx, models):
    """Generate requirements for narrative-opportunity divergence tensions."""
    reqs = []
    nid = t["narrative_id"]
    narr = narr_idx.get(nid, {})
    name = t["narrative_name"]
    direction = t["direction"]

    # Get linked model IDs
    linked = [m["id"] for m in models if nid in m.get("narrative_ids", [])]

    if direction == "strong_narrative_closed_market":
        # Strong narrative, low O-score → is the market actually inaccessible?
        sectors = [s.get("naics", "") for s in narr.get("sectors", [])]
        sector_str = ", ".join(sectors[:3]) if sectors else "N/A"

        reqs.append({
            "requirement_id": f"REQ-{nid}-ACCESS",
            "tension_source": "narrative_opportunity_divergence",
            "tension_id": t["tension_id"],
            "priority": "high",
            "question": f"Is {name} accessible to new entrants or structurally locked by incumbents/regulation?",
            "validation_data": [
                f"Startup funding in {name.replace(' Transformation', '')} sectors (2024-2026) from Crunchbase/PitchBook",
                f"New establishment formation rate in NAICS {sector_str} (Census Business Dynamics)",
                f"Regulatory permitting/licensing timeline for new entrants in this sector",
                f"HHI (market concentration) for key sub-sectors",
            ],
            "threshold_validate": f"3+ startups funded >$10M in 24mo AND establishment formation rate positive AND HHI < 2500",
            "threshold_falsify": f"0-1 startups funded AND establishment formation declining AND HHI > 5000",
            "models_affected": linked,
            "models_affected_count": len(linked),
            "score_impact_if_validated": f"{nid} models: MO += 1-2, avg O rises by ~5-8 points",
            "score_impact_if_falsified": f"{nid} TNS ES -= 1.0, models confirmed FORTIFIED/LOCKED",
        })

    elif direction == "weak_narrative_open_market":
        # Weak narrative, high O-score → is opportunity real despite weak transformation?
        reqs.append({
            "requirement_id": f"REQ-{nid}-VALID",
            "tension_source": "narrative_opportunity_divergence",
            "tension_id": t["tension_id"],
            "priority": "medium",
            "question": f"Is {name} genuinely open for new entrants, or are O-scores inflated by heuristic scoring?",
            "validation_data": [
                f"Venture funding and startup activity in {name.replace(' Transformation', '')} (2024-2026)",
                f"Incumbent digital adoption rate in this sector",
                f"Customer switching costs and contract lock-in data",
                f"Technology pilot programs and deployment timelines",
            ],
            "threshold_validate": f"Active startup ecosystem AND low switching costs AND technology adoption accelerating",
            "threshold_falsify": f"No funded startups AND high incumbent adoption AND long contract cycles (3+ years)",
            "models_affected": linked,
            "models_affected_count": len(linked),
            "score_impact_if_validated": f"{nid} TNS ES += 0.5-1.0, narrative may upgrade to MAJOR",
            "score_impact_if_falsified": f"{nid} models: MO -= 1-2, some may drop to CONTESTED",
        })

    return reqs


def gen_architecture_cross_sector_gap(t, narr_idx, models):
    """Generate requirements for architecture cross-sector gap tensions."""
    arch = t["architecture"]
    best_nid = t["best_narrative"]
    worst_nid = t["worst_narrative"]
    best_name = t["best_narrative_name"]
    worst_name = t["worst_narrative_name"]
    spread = t["spread"]

    # Get affected models in worst-performing narrative
    worst_models = [m["id"] for m in models
                    if m.get("architecture") == arch and worst_nid in m.get("narrative_ids", [])]

    return [{
        "requirement_id": f"REQ-ARCH-{arch[:15].upper()}-GAP",
        "tension_source": "architecture_cross_sector_gap",
        "tension_id": t["tension_id"],
        "priority": "high" if spread > 25 else "medium",
        "question": (f"Why does '{arch}' architecture score O={t['best_avg_o']} in {best_name} "
                     f"but only O={t['worst_avg_o']} in {worst_name}? "
                     f"What market structure variable explains the {spread:.0f}-point gap?"),
        "validation_data": [
            f"Market concentration (HHI) comparison: {best_name.replace(' Transformation', '')} vs {worst_name.replace(' Transformation', '')}",
            f"Incumbent technology adoption rates in both sectors",
            f"Regulatory barriers comparison between sectors",
            f"Customer procurement patterns (RFP vs self-serve) in both sectors",
            f"Successful {arch} startups in {worst_name.replace(' Transformation', '')} (existence proof)",
        ],
        "threshold_validate": f"Structural differences confirmed (HHI gap > 1000 or regulatory barrier identified) → gap is real, scores are correct",
        "threshold_falsify": f"No structural difference found → scoring heuristic is creating artificial gap, worst-sector MO should increase",
        "models_affected": worst_models,
        "models_affected_count": len(worst_models),
        "score_impact_if_validated": f"Worst-sector scores confirmed accurate. Best-sector pattern does not transfer.",
        "score_impact_if_falsified": f"Worst-sector models: MO += 1-2 (spread * 0.01 damped adjustment)",
    }]


def gen_t_o_extreme_divergence(tensions, models):
    """Generate requirements for T-O extreme divergence (batch by direction)."""
    reqs = []

    # Group by direction
    t_high = [t for t in tensions if t["direction"] == "transformation_certain_door_closed"]
    o_high = [t for t in tensions if t["direction"] == "market_open_transformation_uncertain"]

    if t_high:
        # Top 5 most extreme T >> O cases
        top_t_high = t_high[:5]
        model_ids = [t["model_id"] for t in top_t_high]
        reqs.append({
            "requirement_id": "REQ-TO-CERTAIN-CLOSED",
            "tension_source": "t_o_extreme_divergence",
            "tension_id": "TENS-TO-BATCH-T-HIGH",
            "priority": "high",
            "question": ("{} models have T >> O (transformation certain but market closed). "
                         "Top gaps: {}. "
                         "Should these be decomposed into accessible sub-layers?").format(
                             len(t_high),
                             ", ".join("{} ({:+.0f})".format(t["model_name"], t["gap"]) for t in top_t_high)),
            "validation_data": [
                "Value chain analysis of top-gap models: which layers are accessible?",
                "Successful startup examples in adjacent/sub-layer markets",
                "Incumbent vulnerability analysis (debt, tech debt, succession)",
            ],
            "threshold_validate": "2+ models can be decomposed into layers with O > 55",
            "threshold_falsify": "All layers are equally fortified → these are genuinely locked markets",
            "models_affected": model_ids,
            "models_affected_count": len(t_high),
            "score_impact_if_validated": "Parent models get decomposed; sub-models created with independent CLA scores",
            "score_impact_if_falsified": "Models confirmed as observation-only (high T, low O = watch but don't enter)",
        })

    if o_high:
        top_o_high = o_high[:5]
        model_ids = [t["model_id"] for t in top_o_high]
        reqs.append({
            "requirement_id": "REQ-TO-OPEN-UNCERTAIN",
            "tension_source": "t_o_extreme_divergence",
            "tension_id": "TENS-TO-BATCH-O-HIGH",
            "priority": "medium",
            "question": ("{} models have O >> T (market open but transformation uncertain). "
                         "Top gaps: {}. "
                         "What external evidence would validate these transformations?").format(
                             len(o_high),
                             ", ".join("{} ({:+.0f})".format(t["model_name"], t["gap"]) for t in top_o_high)),
            "validation_data": [
                "Technology readiness evidence for transformation thesis",
                "Market adoption data (pilot programs, early customers)",
                "Competitive landscape: are startups actually entering?",
            ],
            "threshold_validate": "Technology proven in production AND 3+ startups funded → T-score should rise",
            "threshold_falsify": "Technology still experimental AND no startup activity → O-score may be inflated",
            "models_affected": model_ids,
            "models_affected_count": len(o_high),
            "score_impact_if_validated": "Models T-score components (SN, FA) increase by 1-2 points",
            "score_impact_if_falsified": "Models flagged as 'premature opportunity' — O maintained but confidence lowered",
        })

    return reqs


def gen_force_vcr_inversion(t, models):
    """Generate requirements for force-VCR inversion tensions."""
    force = t["force_id"]
    fr_rate = t["fr_rate_pct"]
    baseline = t["expected_fr_rate_pct"]

    force_models = [m["id"] for m in models
                    if any(f == force or f.startswith(force.split("_")[0])
                           for f in m.get("forces_v3", []))]

    if fr_rate > baseline:
        direction_label = "enriched"
        question = (f"Force {force} has {t['model_count']} models with {fr_rate:.1f}% fund-returner rate "
                    f"(vs {baseline:.1f}% baseline). Is VCR scoring biased toward {force}'s typical "
                    f"market structures, or does this force genuinely produce better investments?")
    else:
        direction_label = "suppressed"
        question = (f"Force {force} has {t['model_count']} models but only {fr_rate:.1f}% fund-returner rate "
                    f"(vs {baseline:.1f}% baseline). Are {force}-driven models systematically "
                    f"underscored on VCR, or is investability genuinely lower?")

    return [{
        "requirement_id": f"REQ-FVCR-{force}",
        "tension_source": "force_vcr_inversion",
        "tension_id": t["tension_id"],
        "priority": "medium",
        "question": question,
        "validation_data": [
            f"Actual VC funding data for {force}-driven startups (2024-2026)",
            f"Exit multiples for {force}-focused companies vs overall market",
            f"VCR scoring formula: check if {force} market structures are penalized/rewarded by architecture defaults",
        ],
        "threshold_validate": f"Real-world VC data confirms {direction_label} pattern → VCR scoring is accurate",
        "threshold_falsify": f"Real-world data contradicts → VCR heuristic has {force}-specific bias, recalibrate",
        "models_affected": force_models[:20],  # cap at 20 for readability
        "models_affected_count": t["model_count"],
        "score_impact_if_validated": "No change — VCR reflects reality",
        "score_impact_if_falsified": f"Recalibrate VCR heuristic for {force} market structures (±1-2 on CAP/VEL)",
    }]


def gen_role_score_paradox(t, models):
    """Generate requirements for role-score paradox tensions."""
    nid = t["narrative_id"]
    name = t["narrative_name"]

    return [{
        "requirement_id": f"REQ-ROLE-{nid}",
        "tension_source": "role_score_paradox",
        "tension_id": t["tension_id"],
        "priority": "low",
        "question": (f"In {name}, what_needed models avg T={t['avg_t_needed']:.1f} vs "
                     f"what_works T={t['avg_t_works']:.1f}. Is infrastructure genuinely more "
                     f"structurally necessary, or are SN/FA scores inherited from parent sector?"),
        "validation_data": [
            f"Check SN/FA scoring derivation for what_needed models in {nid}",
            f"Compare sector-level SN with model-level SN (inheritance test)",
            f"Infrastructure deployment timelines vs business model timelines",
        ],
        "threshold_validate": "Infrastructure SN/FA scores based on independent evidence → paradox is real structural finding",
        "threshold_falsify": "SN/FA inherited from parent sector → scoring artifact, adjust what_needed SN downward",
        "models_affected": t.get("needed_model_ids", []),
        "models_affected_count": t["needed_count"],
        "score_impact_if_validated": "No change — infrastructure genuinely scores higher on structural necessity",
        "score_impact_if_falsified": f"what_needed models in {nid}: SN -= 0.5-1.0 (damped)",
    }]


def gen_collision_coherence(tensions, collisions_data):
    """Generate requirements for collision coherence tensions (deduplicated by narrative)."""
    reqs = []
    seen_narratives = set()
    coll_idx = {c["collision_id"]: c for c in collisions_data}

    for t in tensions:
        cid = t["collision_id"]
        coll = coll_idx.get(cid, {})
        # Deduplicate: all collisions in same sector share the same models
        sectors = tuple(sorted(coll.get("sectors_affected", [])))
        if sectors in seen_narratives:
            continue
        seen_narratives.add(sectors)

        reqs.append({
            "requirement_id": f"REQ-COLL-{cid}",
            "tension_source": "collision_coherence",
            "tension_id": t["tension_id"],
            "priority": "low",
            "question": (f"Collision '{t['collision_name']}' has {t['model_count']} models with "
                         f"T-score stdev={t['t_stdev']} (range {t['t_min']}–{t['t_max']}). "
                         f"If shared force dynamics should produce coherent trajectories, "
                         f"what explains the divergence?"),
            "validation_data": [
                "Check if low-T models are what_dies (expected to be lower)",
                "Check if divergence correlates with architecture type",
                "Verify force velocity is uniformly applicable across all linked models",
            ],
            "threshold_validate": "Divergence explained by role (what_dies vs what_works) or architecture differences → coherent",
            "threshold_falsify": "Same-role, same-architecture models diverge → scoring inconsistency, investigate",
            "models_affected": [s["id"] for s in t.get("models_sample", [])],
            "models_affected_count": t["model_count"],
            "score_impact_if_validated": "No change — divergence is structurally explained",
            "score_impact_if_falsified": "Outlier models flagged for manual T-score review",
        })

    return reqs


def gen_self_fulfillment_reqs(self_check):
    """Generate requirements for self-fulfillment flags."""
    reqs = []

    for flag in self_check.get("flags", []):
        if "disconnected" in flag.lower():
            reqs.append({
                "requirement_id": "REQ-SELF-TNS-O-DISCONNECT",
                "tension_source": "self_fulfillment_check",
                "tension_id": "TENS-SELFCHECK",
                "priority": "medium",
                "question": "TNS and model O-scores are disconnected (r≈0). Should narrative strength predict market openness at all?",
                "validation_data": [
                    "Review TNS formula: does Evidence Strength (ES) incorporate O-score information?",
                    "Check if narrative-level market accessibility signals should feed into TNS",
                    "Compare narrative collisions to O-score patterns",
                ],
                "threshold_validate": "TNS and O intentionally measure different things → disconnection is by design",
                "threshold_falsify": "Narratives should predict openness → add O-score signal to TNS ES component",
                "models_affected": [],
                "models_affected_count": 0,
                "score_impact_if_validated": "No change — independence is a feature",
                "score_impact_if_falsified": "TNS ES formula updated to incorporate avg model O-score quality signal",
            })

    return reqs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print("v5 Requirement Generator")
    print("=" * 60)

    # Load data
    tensions_data = load_json(V5_DIR / "tensions.json")
    models = load_json(V4_DIR / "models.json")["models"]
    narratives = load_json(V4_DIR / "narratives.json")["narratives"]
    collisions = load_json(V4_DIR / "collisions.json")["collisions"]
    narr_idx = {n["narrative_id"]: n for n in narratives}

    tensions = tensions_data["tensions"]
    self_check = tensions_data["self_fulfillment_metrics"]

    print(f"  Input: {len(tensions)} tensions from v5_tension_detector")

    all_reqs = []

    # Group tensions by type
    by_type = {}
    for t in tensions:
        tt = t["tension_type"]
        by_type.setdefault(tt, []).append(t)

    # Generate requirements per type
    for t in by_type.get("narrative_opportunity_divergence", []):
        all_reqs.extend(gen_narrative_opportunity_divergence(t, narr_idx, models))

    for t in by_type.get("architecture_cross_sector_gap", []):
        all_reqs.extend(gen_architecture_cross_sector_gap(t, narr_idx, models))

    if "t_o_extreme_divergence" in by_type:
        all_reqs.extend(gen_t_o_extreme_divergence(by_type["t_o_extreme_divergence"], models))

    for t in by_type.get("force_vcr_inversion", []):
        all_reqs.extend(gen_force_vcr_inversion(t, models))

    for t in by_type.get("role_score_paradox", []):
        all_reqs.extend(gen_role_score_paradox(t, models))

    if "collision_coherence" in by_type:
        all_reqs.extend(gen_collision_coherence(by_type["collision_coherence"], collisions))

    all_reqs.extend(gen_self_fulfillment_reqs(self_check))

    # Deduplicate by requirement_id
    seen = set()
    deduped = []
    for r in all_reqs:
        if r["requirement_id"] not in seen:
            seen.add(r["requirement_id"])
            deduped.append(r)
    all_reqs = deduped

    # Print summary
    print(f"\n  Generated: {len(all_reqs)} requirements")
    by_priority = {"high": 0, "medium": 0, "low": 0}
    for r in all_reqs:
        by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1
    print(f"  Priority: {by_priority}")

    print("\n  Requirements:")
    for r in all_reqs:
        prio_marker = {"high": "!!!", "medium": " ! ", "low": "   "}.get(r["priority"], "   ")
        print(f"  {prio_marker} [{r['requirement_id']}] {r['question'][:100]}...")
        print(f"        Affects: {r['models_affected_count']} models | Source: {r['tension_source']}")

    # Write output
    V5_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "cycle": tensions_data.get("cycle", "v5-0"),
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source_tensions": len(tensions),
        "requirements": all_reqs,
        "summary": {
            "total_requirements": len(all_reqs),
            "by_priority": by_priority,
            "by_source": {k: sum(1 for r in all_reqs if r["tension_source"] == k)
                          for k in set(r["tension_source"] for r in all_reqs)},
        },
    }

    out_path = V5_DIR / "requirements.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Written: {out_path}")

    return output


if __name__ == "__main__":
    run()
