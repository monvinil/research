#!/usr/bin/env python3
"""
v5_tension_detector.py — Core constraint-propagation tension detector.

Reads v4 data (models, narratives, collisions) and detects 7 types of
internal tensions that the linear pipeline never surfaces. Pure algorithmic
pattern detection — no LLM needed.

Tension Types:
  1. Narrative-Opportunity Divergence (TNS category vs avg model O-score)
  2. Architecture Cross-Sector Gap (same architecture, 20+ pt O-score spread)
  3. T-O Extreme Divergence (models where |T - O| > 30)
  4. Force-VCR Inversion (force model count vs fund-returner rate mismatch)
  5. Role-Score Paradox (what_needed scoring higher T than what_works)
  6. Collision Coherence (models sharing collision context with divergent T)
  7. Self-Fulfillment Check (circularity: TNS predicting model scores)

Output: data/v5/tensions.json
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path) as f:
        return json.load(f)


def normalize_force(f):
    """Normalize mixed force labels: 'F1_technology' and 'F1' both → 'F1_technology'."""
    FORCE_MAP = {
        "F1": "F1_technology", "F1_technology": "F1_technology",
        "F2": "F2_demographics", "F2_demographics": "F2_demographics",
        "F3": "F3_geopolitics", "F3_geopolitics": "F3_geopolitics",
        "F4": "F4_capital", "F4_capital": "F4_capital",
        "F5": "F5_psychology", "F5_psychology": "F5_psychology",
        "F6": "F6_energy", "F6_energy": "F6_energy",
    }
    return FORCE_MAP.get(f, f)


def pearson_r(xs, ys):
    """Pearson correlation coefficient. Returns 0.0 if n < 3."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx * dy == 0:
        return 0.0
    return num / (dx * dy)


def stdev(xs):
    """Population standard deviation."""
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_v4_data():
    models = load_json(V4_DIR / "models.json")["models"]
    narratives = load_json(V4_DIR / "narratives.json")["narratives"]
    collisions = load_json(V4_DIR / "collisions.json")["collisions"]
    return models, narratives, collisions


def build_narrative_index(narratives):
    """Map narrative_id → narrative dict."""
    return {n["narrative_id"]: n for n in narratives}


def build_models_by_narrative(models):
    """Map narrative_id → [model, ...]."""
    idx = defaultdict(list)
    for m in models:
        for nid in m.get("narrative_ids", []):
            idx[nid].append(m)
    return idx


def build_models_by_collision(models, narr_idx):
    """Map collision_id → [model, ...] via narrative linkage."""
    # Models don't carry collision_ids directly — link through narratives
    coll_narr = defaultdict(set)  # collision_id → {narrative_id}
    for n in narr_idx.values():
        for cid in n.get("collision_ids", []):
            coll_narr[cid].add(n["narrative_id"])

    coll_models = defaultdict(list)
    for m in models:
        m_narrs = set(m.get("narrative_ids", []))
        for cid, narr_set in coll_narr.items():
            if m_narrs & narr_set:
                coll_models[cid].append(m)
    return coll_models


# ---------------------------------------------------------------------------
# Tension Type 1: Narrative-Opportunity Divergence
# ---------------------------------------------------------------------------

def detect_narrative_opportunity_divergence(models_by_narr, narr_idx):
    """
    Flag: DEFINING narrative with avg O < 55  → "strong story, closed market"
    Flag: MODERATE+ narrative with avg O > 65  → "weak story, open market"
    """
    tensions = []

    # Thresholds per TNS category
    OPP_THRESHOLDS = {
        "DEFINING": {"max_avg_o": 56, "direction": "strong_narrative_closed_market"},
        "MAJOR": {"max_avg_o": 56, "direction": "strong_narrative_closed_market"},
        "MODERATE": {"min_avg_o": 65, "direction": "weak_narrative_open_market"},
        "EMERGING": {"min_avg_o": 60, "direction": "weak_narrative_open_market"},
        "SPECULATIVE": {"min_avg_o": 55, "direction": "weak_narrative_open_market"},
    }

    for nid, narr in narr_idx.items():
        tns = narr.get("tns", {})
        cat = tns.get("category", "UNKNOWN")
        tns_composite = tns.get("composite", 0)
        linked = models_by_narr.get(nid, [])
        if not linked:
            continue

        o_scores = [m.get("cla", {}).get("composite", 0) for m in linked]
        avg_o = sum(o_scores) / len(o_scores)

        # Count opportunity categories
        opp_cats = defaultdict(int)
        for m in linked:
            oc = m.get("cla", {}).get("category", "none")
            opp_cats[oc] += 1
        n_total = len(linked)
        pct_open = round((opp_cats.get("WIDE_OPEN", 0) + opp_cats.get("ACCESSIBLE", 0)) / n_total * 100, 1)
        pct_fortified = round((opp_cats.get("FORTIFIED", 0) + opp_cats.get("LOCKED", 0)) / n_total * 100, 1)

        thresh = OPP_THRESHOLDS.get(cat, {})
        flagged = False
        direction = ""

        if thresh.get("max_avg_o") and avg_o < thresh["max_avg_o"]:
            flagged = True
            direction = thresh["direction"]
        if thresh.get("min_avg_o") and avg_o > thresh["min_avg_o"]:
            flagged = True
            direction = thresh["direction"]

        # Also flag if distribution is extreme regardless of category
        if cat in ("DEFINING", "MAJOR") and pct_fortified > 40:
            flagged = True
            direction = "strong_narrative_closed_market"
        if cat in ("DEFINING", "MAJOR") and pct_open < 30:
            flagged = True
            direction = "strong_narrative_closed_market"
        if cat in ("MODERATE", "EMERGING") and pct_open > 70:
            flagged = True
            direction = "weak_narrative_open_market"

        if flagged:
            magnitude = abs(tns_composite - avg_o)
            tensions.append({
                "tension_id": f"TENS-{nid}-OPP-DIV",
                "tension_type": "narrative_opportunity_divergence",
                "narrative_id": nid,
                "narrative_name": narr.get("name", ""),
                "tns_category": cat,
                "tns_composite": tns_composite,
                "avg_o_score": round(avg_o, 1),
                "pct_open": pct_open,
                "pct_fortified": pct_fortified,
                "direction": direction,
                "tension_magnitude": round(magnitude, 1),
                "model_count": n_total,
                "opp_distribution": dict(opp_cats),
                "question": _narr_opp_question(nid, narr, direction, avg_o, tns_composite),
            })

    return sorted(tensions, key=lambda t: -t["tension_magnitude"])


def _narr_opp_question(nid, narr, direction, avg_o, tns_comp):
    name = narr.get("name", nid)
    if direction == "strong_narrative_closed_market":
        return (f"{name} scores TNS {tns_comp} ({narr['tns']['category']}) but avg O-score "
                f"is only {avg_o:.1f}. Is the market structurally inaccessible to new entrants, "
                f"or are O-scores underestimating openness due to scoring heuristics?")
    else:
        return (f"{name} scores TNS {tns_comp} ({narr['tns']['category']}) but avg O-score "
                f"is {avg_o:.1f}. Is the market genuinely open despite weak transformation signal, "
                f"or is something else driving opportunity scores?")


# ---------------------------------------------------------------------------
# Tension Type 2: Architecture Cross-Sector Gap
# ---------------------------------------------------------------------------

def detect_architecture_cross_sector_gap(models_by_narr, narr_idx, models):
    """
    Flag: Same architecture with 20+ point O-score spread across narratives.
    """
    tensions = []

    # Build architecture → narrative → [O-scores]
    arch_narr = defaultdict(lambda: defaultdict(list))
    for m in models:
        arch = m.get("architecture")
        if not arch:
            continue
        o = m.get("cla", {}).get("composite", 0)
        for nid in m.get("narrative_ids", []):
            arch_narr[arch][nid].append(o)

    for arch, narrs in arch_narr.items():
        if len(narrs) < 2:
            continue
        avgs = {}
        for nid, scores in narrs.items():
            if len(scores) >= 1:
                avgs[nid] = sum(scores) / len(scores)
        if len(avgs) < 2:
            continue

        best_nid = max(avgs, key=avgs.get)
        worst_nid = min(avgs, key=avgs.get)
        spread = avgs[best_nid] - avgs[worst_nid]

        if spread >= 20:
            total_models = sum(len(s) for s in narrs.values())
            best_name = narr_idx.get(best_nid, {}).get("name", best_nid)
            worst_name = narr_idx.get(worst_nid, {}).get("name", worst_nid)

            # Collect affected model IDs
            affected_ids = []
            for nid, scores_list in narrs.items():
                for m in models:
                    if m.get("architecture") == arch and nid in m.get("narrative_ids", []):
                        affected_ids.append(m["id"])

            tensions.append({
                "tension_id": f"TENS-ARCH-{arch[:20].upper()}-XSECTOR",
                "tension_type": "architecture_cross_sector_gap",
                "architecture": arch,
                "best_narrative": best_nid,
                "best_narrative_name": best_name,
                "best_avg_o": round(avgs[best_nid], 1),
                "worst_narrative": worst_nid,
                "worst_narrative_name": worst_name,
                "worst_avg_o": round(avgs[worst_nid], 1),
                "spread": round(spread, 1),
                "narratives_count": len(avgs),
                "models_affected": len(set(affected_ids)),
                "question": (f"Architecture '{arch}' scores O={avgs[best_nid]:.1f} in {best_name} "
                             f"but only O={avgs[worst_nid]:.1f} in {worst_name} (spread: {spread:.1f}). "
                             f"What market structure variable explains this gap?"),
            })

    return sorted(tensions, key=lambda t: -t["spread"])


# ---------------------------------------------------------------------------
# Tension Type 3: T-O Extreme Divergence
# ---------------------------------------------------------------------------

def detect_t_o_divergence(models):
    """
    Flag: Models where |T - O| > 30.
    T >> O = transformation certain but door closed.
    O >> T = market open but transformation uncertain.
    """
    tensions = []
    THRESHOLD = 30

    for m in models:
        t = m.get("composite", 0)
        o = m.get("cla", {}).get("composite", 0)
        gap = t - o

        if abs(gap) > THRESHOLD:
            direction = "transformation_certain_door_closed" if gap > 0 else "market_open_transformation_uncertain"
            narr_ids = m.get("narrative_ids", [])

            tensions.append({
                "tension_id": f"TENS-TO-{m['id']}",
                "tension_type": "t_o_extreme_divergence",
                "model_id": m["id"],
                "model_name": m.get("name", ""),
                "t_score": round(t, 1),
                "o_score": round(o, 1),
                "gap": round(gap, 1),
                "abs_gap": round(abs(gap), 1),
                "direction": direction,
                "narrative_ids": narr_ids,
                "narrative_role": m.get("narrative_role", "unlinked"),
                "architecture": m.get("architecture", ""),
                "question": _t_o_question(m, gap, direction),
            })

    return sorted(tensions, key=lambda t: -t["abs_gap"])


def _t_o_question(m, gap, direction):
    name = m.get("name", m["id"])
    if direction == "transformation_certain_door_closed":
        return (f"'{name}' has T={m['composite']:.1f} but O={m['cla']['composite']:.1f} "
                f"(gap {gap:+.1f}). Transformation is near-certain but market is closed. "
                f"Should this model be decomposed into more accessible sub-layers?")
    else:
        return (f"'{name}' has T={m['composite']:.1f} but O={m['cla']['composite']:.1f} "
                f"(gap {gap:+.1f}). Market is open but transformation evidence is weak. "
                f"What external evidence would validate this transformation?")


# ---------------------------------------------------------------------------
# Tension Type 4: Force-VCR Inversion
# ---------------------------------------------------------------------------

def detect_force_vcr_inversion(models):
    """
    Flag: Force with high model count but low fund-returner rate (or vice versa).
    """
    tensions = []

    # Group models by primary force
    force_models = defaultdict(list)
    for m in models:
        for f in m.get("forces_v3", []):
            fn = normalize_force(f)
            force_models[fn].append(m)

    # Compute overall fund-returner rate for baseline
    total_fr = sum(1 for m in models if m.get("vcr", {}).get("category") == "FUND_RETURNER")
    overall_fr_rate = total_fr / len(models) * 100 if models else 0

    for force, fmodels in force_models.items():
        n = len(fmodels)
        if n < 10:
            continue  # too few to be meaningful

        fr_count = sum(1 for m in fmodels if m.get("vcr", {}).get("category") == "FUND_RETURNER")
        fr_rate = fr_count / n * 100

        # Expected rate based on proportional share
        expected_fr_rate = overall_fr_rate

        # Flag inversions
        inversion = False
        if n > 100 and fr_rate < expected_fr_rate * 0.5:
            inversion = True  # high count, low FR rate
        elif n < 50 and fr_rate > expected_fr_rate * 2:
            inversion = True  # low count, high FR rate
        # Also flag any force where FR rate diverges >2.5pp from baseline
        elif abs(fr_rate - expected_fr_rate) > 2.5:
            inversion = True

        if inversion:
            # Compute avg T, O, VCR for context
            avg_t = sum(m.get("composite", 0) for m in fmodels) / n
            avg_o = sum(m.get("cla", {}).get("composite", 0) for m in fmodels) / n
            avg_vcr = sum(m.get("vcr", {}).get("composite", 0) for m in fmodels) / n

            tensions.append({
                "tension_id": f"TENS-FVCR-{force}",
                "tension_type": "force_vcr_inversion",
                "force_id": force,
                "model_count": n,
                "fund_returner_count": fr_count,
                "fr_rate_pct": round(fr_rate, 1),
                "expected_fr_rate_pct": round(expected_fr_rate, 1),
                "inversion_magnitude": round(abs(fr_rate - expected_fr_rate), 1),
                "avg_t": round(avg_t, 1),
                "avg_o": round(avg_o, 1),
                "avg_vcr": round(avg_vcr, 1),
                "question": (f"Force {force} has {n} models but only {fr_rate:.1f}% fund-returner rate "
                             f"(baseline: {expected_fr_rate:.1f}%). Is VCR biased toward this force's "
                             f"market structure, or is this a real signal about investability?"),
            })

    return sorted(tensions, key=lambda t: -t["inversion_magnitude"])


# ---------------------------------------------------------------------------
# Tension Type 5: Role-Score Paradox
# ---------------------------------------------------------------------------

def detect_role_score_paradox(models_by_narr, narr_idx):
    """
    Flag: avg T(what_needed) > avg T(what_works) by >2 points within a narrative.
    Infrastructure scoring higher than the businesses it enables is suspicious.
    """
    tensions = []
    THRESHOLD = 2.0

    for nid, linked in models_by_narr.items():
        by_role = defaultdict(list)
        for m in linked:
            role = m.get("narrative_role", "unlinked")
            by_role[role].append(m)

        works = by_role.get("what_works", [])
        needed = by_role.get("whats_needed", [])

        if len(works) < 3 or len(needed) < 2:
            continue

        avg_t_works = sum(m.get("composite", 0) for m in works) / len(works)
        avg_t_needed = sum(m.get("composite", 0) for m in needed) / len(needed)
        gap = avg_t_needed - avg_t_works

        if gap > THRESHOLD:
            # Also compute O-score comparison
            avg_o_works = sum(m.get("cla", {}).get("composite", 0) for m in works) / len(works)
            avg_o_needed = sum(m.get("cla", {}).get("composite", 0) for m in needed) / len(needed)

            narr = narr_idx.get(nid, {})
            tensions.append({
                "tension_id": f"TENS-ROLE-{nid}",
                "tension_type": "role_score_paradox",
                "narrative_id": nid,
                "narrative_name": narr.get("name", nid),
                "avg_t_works": round(avg_t_works, 1),
                "avg_t_needed": round(avg_t_needed, 1),
                "t_gap": round(gap, 1),
                "avg_o_works": round(avg_o_works, 1),
                "avg_o_needed": round(avg_o_needed, 1),
                "works_count": len(works),
                "needed_count": len(needed),
                "question": (f"In {narr.get('name', nid)}, what_needed models avg T={avg_t_needed:.1f} "
                             f"vs what_works T={avg_t_works:.1f} (gap +{gap:.1f}). Is infrastructure "
                             f"genuinely more structurally necessary, or is this a scoring artifact "
                             f"(e.g., SN/FA inherited from parent sector)?"),
                "works_model_ids": [m["id"] for m in works],
                "needed_model_ids": [m["id"] for m in needed],
            })

    return sorted(tensions, key=lambda t: -t["t_gap"])


# ---------------------------------------------------------------------------
# Tension Type 6: Collision Coherence
# ---------------------------------------------------------------------------

def detect_collision_coherence(coll_models, collisions):
    """
    Flag: Models sharing same collision context with T-score stdev > 10.
    If the same forces collide on these models, they should have similar
    transformation trajectories.
    """
    tensions = []
    STDEV_THRESHOLD = 8
    coll_idx = {c["collision_id"]: c for c in collisions}

    for cid, cmodels in coll_models.items():
        if len(cmodels) < 3:
            continue

        t_scores = [m.get("composite", 0) for m in cmodels]
        sd = stdev(t_scores)

        if sd > STDEV_THRESHOLD:
            coll = coll_idx.get(cid, {})
            tensions.append({
                "tension_id": f"TENS-COLL-{cid}",
                "tension_type": "collision_coherence",
                "collision_id": cid,
                "collision_name": coll.get("name", cid),
                "collision_type": coll.get("collision_type", "unknown"),
                "model_count": len(cmodels),
                "t_stdev": round(sd, 1),
                "t_min": round(min(t_scores), 1),
                "t_max": round(max(t_scores), 1),
                "t_mean": round(sum(t_scores) / len(t_scores), 1),
                "question": (f"Collision '{coll.get('name', cid)}' ({coll.get('collision_type', '?')}) "
                             f"has {len(cmodels)} models with T-score stdev={sd:.1f} "
                             f"(range {min(t_scores):.1f}–{max(t_scores):.1f}). "
                             f"If these models share the same force dynamics, why do they diverge?"),
                "models_sample": [
                    {"id": m["id"], "name": m.get("name", ""), "t": m.get("composite", 0)}
                    for m in sorted(cmodels, key=lambda m: m.get("composite", 0))[:5]
                ] + [
                    {"id": m["id"], "name": m.get("name", ""), "t": m.get("composite", 0)}
                    for m in sorted(cmodels, key=lambda m: -m.get("composite", 0))[:3]
                ],
            })

    return sorted(tensions, key=lambda t: -t["t_stdev"])


# ---------------------------------------------------------------------------
# Tension Type 7: Self-Fulfillment Check
# ---------------------------------------------------------------------------

def detect_self_fulfillment(models_by_narr, narr_idx):
    """
    Test circularity: Does narrative TNS predict model T-scores?
    r > 0.7  = circular (TNS and T measuring same thing)
    r < 0.1  = disconnected (narratives not adding information)
    Sweet spot: r = 0.2-0.5 (partial overlap, each adds unique signal)

    Also check O-score and VCR correlations.
    """
    tns_vals = []
    avg_t_vals = []
    avg_o_vals = []
    avg_vcr_vals = []
    narr_names = []

    for nid, narr in narr_idx.items():
        tns_comp = narr.get("tns", {}).get("composite", 0)
        linked = models_by_narr.get(nid, [])
        if not linked:
            continue

        avg_t = sum(m.get("composite", 0) for m in linked) / len(linked)
        avg_o = sum(m.get("cla", {}).get("composite", 0) for m in linked) / len(linked)
        avg_vcr = sum(m.get("vcr", {}).get("composite", 0) for m in linked) / len(linked)

        tns_vals.append(tns_comp)
        avg_t_vals.append(avg_t)
        avg_o_vals.append(avg_o)
        avg_vcr_vals.append(avg_vcr)
        narr_names.append(nid)

    r_tns_t = pearson_r(tns_vals, avg_t_vals)
    r_tns_o = pearson_r(tns_vals, avg_o_vals)
    r_tns_vcr = pearson_r(tns_vals, avg_vcr_vals)
    r_t_o = pearson_r(avg_t_vals, avg_o_vals)

    # Assess each correlation — distinguish positive (circularity) from negative (structural inverse)
    def assess(r, label_a, label_b):
        ar = abs(r)
        if r > 0.7:
            return "CIRCULAR", f"{label_a} and {label_b} are measuring essentially the same thing (r={r:.3f}). One is redundant."
        elif r < -0.7:
            return "STRUCTURAL_INVERSE", f"{label_a} and {label_b} are strongly inversely related (r={r:.3f}). This is a structural pattern (e.g., certain transformation → closed market), not circularity."
        elif ar > 0.5:
            return "HIGH_OVERLAP", f"{label_a} and {label_b} have high overlap (r={r:.3f}). Check for shared derivation."
        elif ar > 0.2:
            return "HEALTHY", f"{label_a} and {label_b} have partial overlap (r={r:.3f}). Each adds unique signal."
        elif ar > 0.1:
            return "LOW_OVERLAP", f"{label_a} and {label_b} have minimal overlap (r={r:.3f}). Nearly independent."
        else:
            return "DISCONNECTED", f"{label_a} and {label_b} appear disconnected (r={r:.3f}). Narrative layer may not be informative."

    status_tns_t, msg_tns_t = assess(r_tns_t, "TNS", "Model T-score")
    status_tns_o, msg_tns_o = assess(r_tns_o, "TNS", "Model O-score")
    status_tns_vcr, msg_tns_vcr = assess(r_tns_vcr, "TNS", "Model VCR")
    status_t_o, msg_t_o = assess(r_t_o, "Model T-score", "Model O-score")

    # Per-narrative breakdown
    narr_breakdown = []
    for i, nid in enumerate(narr_names):
        narr_breakdown.append({
            "narrative_id": nid,
            "tns": tns_vals[i],
            "avg_t": round(avg_t_vals[i], 1),
            "avg_o": round(avg_o_vals[i], 1),
            "avg_vcr": round(avg_vcr_vals[i], 1),
        })

    flags = []
    structural_findings = []
    for status, msg in [(status_tns_t, msg_tns_t), (status_tns_o, msg_tns_o),
                         (status_tns_vcr, msg_tns_vcr), (status_t_o, msg_t_o)]:
        if status in ("CIRCULAR", "HIGH_OVERLAP", "DISCONNECTED"):
            flags.append(msg)
        elif status == "STRUCTURAL_INVERSE":
            structural_findings.append(msg)

    return {
        "tension_id": "TENS-SELFCHECK",
        "tension_type": "self_fulfillment_check",
        "correlations": {
            "tns_vs_model_t": {"r": round(r_tns_t, 4), "status": status_tns_t, "message": msg_tns_t},
            "tns_vs_model_o": {"r": round(r_tns_o, 4), "status": status_tns_o, "message": msg_tns_o},
            "tns_vs_model_vcr": {"r": round(r_tns_vcr, 4), "status": status_tns_vcr, "message": msg_tns_vcr},
            "model_t_vs_model_o": {"r": round(r_t_o, 4), "status": status_t_o, "message": msg_t_o},
        },
        "flags": flags,
        "structural_findings": structural_findings,
        "is_circular": any(s == "CIRCULAR" for s, _ in [
            (status_tns_t, None), (status_tns_o, None), (status_tns_vcr, None)]),
        "narrative_breakdown": sorted(narr_breakdown, key=lambda x: -x["tns"]),
    }


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def compute_summary(all_tensions, self_check):
    """Compute summary stats across all tensions."""
    by_type = defaultdict(int)
    for t in all_tensions:
        by_type[t["tension_type"]] += 1

    total_models_affected = set()
    for t in all_tensions:
        if "model_id" in t:
            total_models_affected.add(t["model_id"])
        elif "models_affected" in t and isinstance(t["models_affected"], int):
            pass  # count-based, can't deduplicate
        elif "works_model_ids" in t:
            total_models_affected.update(t["works_model_ids"])
            total_models_affected.update(t.get("needed_model_ids", []))

    return {
        "total_tensions": len(all_tensions),
        "by_type": dict(by_type),
        "models_with_tensions": len(total_models_affected),
        "self_fulfillment_status": "CLEAN" if not self_check["is_circular"] else "CIRCULAR_WARNING",
        "correlation_flags": len(self_check["flags"]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print("v5 Tension Detector")
    print("=" * 60)

    # Load data
    print("Loading v4 data...")
    models, narratives, collisions = load_v4_data()
    print(f"  Models: {len(models)}, Narratives: {len(narratives)}, Collisions: {len(collisions)}")

    narr_idx = build_narrative_index(narratives)
    models_by_narr = build_models_by_narrative(models)
    coll_models = build_models_by_collision(models, narr_idx)

    all_tensions = []

    # Type 1: Narrative-Opportunity Divergence
    print("\n[1/7] Narrative-Opportunity Divergence...")
    t1 = detect_narrative_opportunity_divergence(models_by_narr, narr_idx)
    print(f"  Found: {len(t1)} tensions")
    for t in t1:
        print(f"    {t['narrative_id']} ({t['narrative_name']}): TNS={t['tns_composite']} {t['tns_category']}, "
              f"avgO={t['avg_o_score']}, dir={t['direction']}, mag={t['tension_magnitude']}")
    all_tensions.extend(t1)

    # Type 2: Architecture Cross-Sector Gap
    print("\n[2/7] Architecture Cross-Sector Gap...")
    t2 = detect_architecture_cross_sector_gap(models_by_narr, narr_idx, models)
    print(f"  Found: {len(t2)} tensions")
    for t in t2:
        print(f"    {t['architecture']}: spread={t['spread']}, "
              f"best={t['best_narrative_name']}({t['best_avg_o']}), "
              f"worst={t['worst_narrative_name']}({t['worst_avg_o']})")
    all_tensions.extend(t2)

    # Type 3: T-O Extreme Divergence
    print("\n[3/7] T-O Extreme Divergence...")
    t3 = detect_t_o_divergence(models)
    print(f"  Found: {len(t3)} tensions")
    for t in t3[:5]:
        print(f"    {t['model_id']}: T={t['t_score']}, O={t['o_score']}, gap={t['gap']:+.1f}")
    if len(t3) > 5:
        print(f"    ... and {len(t3) - 5} more")
    all_tensions.extend(t3)

    # Type 4: Force-VCR Inversion
    print("\n[4/7] Force-VCR Inversion...")
    t4 = detect_force_vcr_inversion(models)
    print(f"  Found: {len(t4)} tensions")
    for t in t4:
        print(f"    {t['force_id']}: {t['model_count']} models, FR={t['fr_rate_pct']}% "
              f"(baseline={t['expected_fr_rate_pct']}%), inv_mag={t['inversion_magnitude']}")
    all_tensions.extend(t4)

    # Type 5: Role-Score Paradox
    print("\n[5/7] Role-Score Paradox...")
    t5 = detect_role_score_paradox(models_by_narr, narr_idx)
    print(f"  Found: {len(t5)} tensions")
    for t in t5:
        print(f"    {t['narrative_id']} ({t['narrative_name']}): T_works={t['avg_t_works']}, "
              f"T_needed={t['avg_t_needed']}, gap=+{t['t_gap']}")
    all_tensions.extend(t5)

    # Type 6: Collision Coherence
    print("\n[6/7] Collision Coherence...")
    t6 = detect_collision_coherence(coll_models, collisions)
    print(f"  Found: {len(t6)} tensions")
    for t in t6[:5]:
        print(f"    {t['collision_id']} ({t['collision_name']}): stdev={t['t_stdev']}, "
              f"range={t['t_min']}–{t['t_max']}, n={t['model_count']}")
    if len(t6) > 5:
        print(f"    ... and {len(t6) - 5} more")
    all_tensions.extend(t6)

    # Type 7: Self-Fulfillment Check
    print("\n[7/7] Self-Fulfillment Check...")
    self_check = detect_self_fulfillment(models_by_narr, narr_idx)
    for key, val in self_check["correlations"].items():
        status_marker = "!!" if val["status"] in ("CIRCULAR", "HIGH_OVERLAP", "DISCONNECTED") else "  "
        print(f"  {status_marker} {key}: r={val['r']:.4f} [{val['status']}]")
    if self_check["flags"]:
        print(f"  CIRCULARITY FLAGS ({len(self_check['flags'])}):")
        for flag in self_check["flags"]:
            print(f"    ⚠ {flag}")
    else:
        print("  No circularity flags. System is clean.")
    if self_check.get("structural_findings"):
        print(f"  STRUCTURAL FINDINGS ({len(self_check['structural_findings'])}):")
        for sf in self_check["structural_findings"]:
            print(f"    → {sf}")

    # Summary
    summary = compute_summary(all_tensions, self_check)
    print(f"\n{'=' * 60}")
    print(f"TOTAL TENSIONS: {summary['total_tensions']}")
    print(f"  By type: {summary['by_type']}")
    print(f"  Self-fulfillment: {summary['self_fulfillment_status']}")

    # Write output
    V5_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "cycle": "v5-0",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "engine_version": "5.0",
        "source_data": {
            "models": len(models),
            "narratives": len(narratives),
            "collisions": len(collisions),
        },
        "tensions": all_tensions,
        "self_fulfillment_metrics": self_check,
        "summary": summary,
    }

    out_path = V5_DIR / "tensions.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten: {out_path} ({len(all_tensions)} tensions)")

    return output


if __name__ == "__main__":
    run()
