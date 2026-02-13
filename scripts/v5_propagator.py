#!/usr/bin/env python3
"""
v5_propagator.py — Bounded score adjustment engine with audit trail.

Reads tensions.json and applies 5 propagation rules with damping to
prevent oscillation. Pure algorithmic — no LLM needed.

Propagation Rules:
  1. Narrative phase → Model TG adjustment (damping: 0.3)
  2. Model O-score aggregates → TNS ES recalibration (damping: 0.2)
  3. VCR ROI → CLA MA challenge (damping: 0.25)
  4. Architecture cross-sector pattern → MO adjustment (damping: 0.2)
  5. Model cluster → Force velocity signal (advisory only, no score change)

Anti-Circularity: Each rule only modifies scores using evidence INDEPENDENT
of that score's own derivation chain.

Convergence: Max 3 iterations, stop if max score change < 0.5.

Output:
  - Updated data/v4/models.json (score adjustments)
  - Updated data/v4/narratives.json (TNS recalibration)
  - data/v5/propagation_log.json (full audit trail)
"""

import copy
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"

# Convergence parameters
MAX_ITERATIONS = 3
CONVERGENCE_THRESHOLD = 0.5  # max score change before stopping
MAX_AXIS_CHANGE = 3.0        # absolute cap on any single axis adjustment


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def clamp(val, lo=1.0, hi=10.0):
    return max(lo, min(hi, val))


def recompute_t_composite(scores):
    """T-composite: (SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10"""
    return (scores["SN"] * 25 + scores["FA"] * 25 + scores["EC"] * 20 +
            scores["TG"] * 15 + scores["CE"] * 15) / 10


def recompute_cla_composite(scores):
    """CLA composite: (MO*30 + MA*25 + VD*20 + DV*25) / 10"""
    return (scores["MO"] * 30 + scores["MA"] * 25 + scores["VD"] * 20 +
            scores["DV"] * 25) / 10


def recompute_tns_composite(tns):
    """TNS composite: (EM*25 + FC*25 + ES*20 + TC*15 + IR*15) / 10"""
    return (tns["economic_magnitude"] * 25 + tns["force_convergence"] * 25 +
            tns["evidence_strength"] * 20 + tns["timing_confidence"] * 15 +
            tns["irreversibility"] * 15) / 10


def tns_category(composite):
    if composite >= 80:
        return "DEFINING"
    elif composite >= 65:
        return "MAJOR"
    elif composite >= 50:
        return "MODERATE"
    elif composite >= 35:
        return "EMERGING"
    return "SPECULATIVE"


def cla_category(composite):
    if composite >= 75:
        return "WIDE_OPEN"
    elif composite >= 60:
        return "ACCESSIBLE"
    elif composite >= 45:
        return "CONTESTED"
    elif composite >= 30:
        return "FORTIFIED"
    return "LOCKED"


def is_heuristic_cla(model):
    """Check if CLA scores were heuristic-generated (not manually overridden)."""
    rationale = model.get("cla", {}).get("rationale", "")
    return rationale.startswith("Heuristic")


def normalize_force(f):
    FORCE_MAP = {
        "F1": "F1_technology", "F1_technology": "F1_technology",
        "F2": "F2_demographics", "F2_demographics": "F2_demographics",
        "F3": "F3_geopolitics", "F3_geopolitics": "F3_geopolitics",
        "F4": "F4_capital", "F4_capital": "F4_capital",
        "F5": "F5_psychology", "F5_psychology": "F5_psychology",
        "F6": "F6_energy", "F6_energy": "F6_energy",
    }
    return FORCE_MAP.get(f, f)


# ---------------------------------------------------------------------------
# Propagation Rule 1: Narrative phase → Model TG adjustment
# ---------------------------------------------------------------------------

def rule_1_narrative_phase_tg(models, narratives, log, cumulative):
    """
    If narrative is 'acceleration' phase and model TG < 7: TG += min(1.0, (7 - TG) * 0.3)
    If narrative is 'pre_disruption' and model TG > 7: TG -= min(1.0, (TG - 7) * 0.3)
    Anti-circularity: Only applies to heuristic-scored models.
    """
    DAMPING = 0.3
    adjustments = []
    narr_idx = {n["narrative_id"]: n for n in narratives}

    for m in models:
        if not is_heuristic_cla(m):
            continue

        mid = m["id"]
        scores = m.get("scores", {})
        tg = scores.get("TG", 5)

        # Check cumulative cap
        cum_tg = cumulative[mid]["TG"]
        remaining = MAX_AXIS_CHANGE - abs(cum_tg)
        if remaining < 0.01:
            continue

        for nid in m.get("narrative_ids", []):
            narr = narr_idx.get(nid)
            if not narr:
                continue

            phase = narr.get("transformation_phase", "")
            delta = 0

            if phase == "acceleration" and tg < 7:
                delta = min(1.0, (7 - tg) * DAMPING)
            elif phase == "pre_disruption" and tg > 7:
                delta = -min(1.0, (tg - 7) * DAMPING)

            if abs(delta) > 0.01:
                # Cap by cumulative remaining
                if delta > 0:
                    delta = min(delta, remaining)
                else:
                    delta = max(delta, -remaining)

                old_tg = tg
                new_tg = clamp(round(tg + delta, 2))

                if abs(new_tg - old_tg) > 0.01:
                    scores["TG"] = new_tg
                    old_composite = m["composite"]
                    m["composite"] = round(recompute_t_composite(scores), 2)
                    cumulative[mid]["TG"] += (new_tg - old_tg)

                    adjustments.append({
                        "rule": "rule_1_narrative_phase_tg",
                        "model_id": mid,
                        "narrative_id": nid,
                        "narrative_phase": phase,
                        "field": "scores.TG",
                        "old_value": old_tg,
                        "new_value": new_tg,
                        "delta": round(new_tg - old_tg, 3),
                        "cumulative_tg": round(cumulative[mid]["TG"], 3),
                        "old_composite": old_composite,
                        "new_composite": m["composite"],
                        "evidence": f"Narrative {nid} phase={phase}, heuristic TG adjusted with damping {DAMPING}",
                    })
                break

    log["rule_1_adjustments"] = len(adjustments)
    log["adjustments"].extend(adjustments)
    return adjustments


# ---------------------------------------------------------------------------
# Propagation Rule 2: Model O-score aggregates → TNS ES recalibration
# ---------------------------------------------------------------------------

def rule_2_model_vcr_to_tns_es(models, narratives, log):
    """
    Current ES = evidence-quality-based score.
    New: ES also considers avg model VCR of linked models (quality, not just quantity).
    If avg_VCR > 65: ES += 0.5. If avg_VCR < 45: ES -= 0.5.
    Anti-circularity: VCR is independent of narrative (verified: VCR ↔ TNS r < 0.1).
    """
    DAMPING = 0.2
    adjustments = []

    models_by_narr = defaultdict(list)
    for m in models:
        for nid in m.get("narrative_ids", []):
            models_by_narr[nid].append(m)

    for narr in narratives:
        nid = narr["narrative_id"]
        linked = models_by_narr.get(nid, [])
        if not linked:
            continue

        avg_vcr = sum(m.get("vcr", {}).get("composite", 0) for m in linked) / len(linked)
        tns = narr.get("tns", {})
        old_es = tns.get("evidence_strength", 5)

        delta = 0
        if avg_vcr > 65:
            delta = 0.5 * DAMPING
        elif avg_vcr < 45:
            delta = -0.5 * DAMPING

        if abs(delta) > 0.01:
            delta = max(-MAX_AXIS_CHANGE, min(MAX_AXIS_CHANGE, delta))
            new_es = clamp(round(old_es + delta, 2))

            if abs(new_es - old_es) > 0.01:
                tns["evidence_strength"] = new_es
                old_composite = tns.get("composite", 0)
                tns["composite"] = round(recompute_tns_composite(tns), 2)
                tns["category"] = tns_category(tns["composite"])

                adjustments.append({
                    "rule": "rule_2_model_vcr_to_tns_es",
                    "narrative_id": nid,
                    "field": "tns.evidence_strength",
                    "old_value": old_es,
                    "new_value": new_es,
                    "delta": round(new_es - old_es, 3),
                    "avg_vcr": round(avg_vcr, 1),
                    "old_composite": old_composite,
                    "new_composite": tns["composite"],
                    "evidence": f"Avg VCR of {len(linked)} linked models = {avg_vcr:.1f}, damping {DAMPING}",
                })

    log["rule_2_adjustments"] = len(adjustments)
    log["adjustments"].extend(adjustments)
    return adjustments


# ---------------------------------------------------------------------------
# Propagation Rule 3: VCR ROI → CLA MA challenge
# ---------------------------------------------------------------------------

def rule_3_vcr_roi_ma_challenge(models, log, cumulative):
    """
    If model ROI < 5x but CLA MA > 7: flag as "moat overestimate", MA decreases.
    If model ROI > 50x but CLA MA < 5: flag as "moat underestimate", MA increases.
    Anti-circularity: VCR reads 20% of CAP from MO, but MA is independent.
    Only applies to heuristic-scored models.
    """
    DAMPING = 0.25
    adjustments = []

    for m in models:
        if not is_heuristic_cla(m):
            continue

        mid = m["id"]

        # Check cumulative cap
        cum_ma = cumulative[mid]["MA"]
        remaining = MAX_AXIS_CHANGE - abs(cum_ma)
        if remaining < 0.01:
            continue

        roi_est = m.get("vcr", {}).get("roi_estimate", {})
        if not isinstance(roi_est, dict):
            continue
        roi = roi_est.get("seed_roi_multiple", 0)
        if not roi:
            continue

        cla = m.get("cla", {})
        cla_scores = cla.get("scores", {})
        ma = cla_scores.get("MA", 5)

        delta = 0
        flag = ""

        if roi < 5 and ma > 7:
            expected_ma = 5
            delta = round((expected_ma - ma) * DAMPING, 2)
            flag = "moat_overestimate"
        elif roi > 50 and ma < 5:
            expected_ma = 6
            delta = round((expected_ma - ma) * DAMPING, 2)
            flag = "moat_underestimate"

        if abs(delta) > 0.01:
            # Cap by cumulative remaining
            if delta > 0:
                delta = min(delta, remaining)
            else:
                delta = max(delta, -remaining)

            old_ma = ma
            new_ma = clamp(round(ma + delta, 1))

            if abs(new_ma - old_ma) > 0.01:
                cla_scores["MA"] = new_ma
                old_composite = cla.get("composite", 0)
                cla["composite"] = round(recompute_cla_composite(cla_scores), 2)
                cla["category"] = cla_category(cla["composite"])
                cumulative[mid]["MA"] += (new_ma - old_ma)

                adjustments.append({
                    "rule": "rule_3_vcr_roi_ma_challenge",
                    "model_id": mid,
                    "field": "cla.scores.MA",
                    "old_value": old_ma,
                    "new_value": new_ma,
                    "delta": round(new_ma - old_ma, 3),
                    "cumulative_ma": round(cumulative[mid]["MA"], 3),
                    "roi_multiple": roi,
                    "flag": flag,
                    "old_composite": old_composite,
                    "new_composite": cla["composite"],
                    "evidence": f"ROI={roi:.1f}x, MA={old_ma} → {flag}, damping {DAMPING}",
                })

    log["rule_3_adjustments"] = len(adjustments)
    log["adjustments"].extend(adjustments)
    return adjustments


# ---------------------------------------------------------------------------
# Propagation Rule 4: Architecture cross-sector pattern → MO adjustment
# ---------------------------------------------------------------------------

def rule_4_architecture_cross_sector_mo(models, tensions_data, narr_idx, log, cumulative):
    """
    For architectures with 20+ point O-score spread:
    Worst-sector models: MO += min(1.0, spread * 0.01) if >3 best-sector examples validate.
    Only applies to heuristic-scored models in worst-performing narrative.
    Anti-circularity: Cross-sector comparison is independent of within-sector scoring.
    """
    DAMPING = 0.2
    adjustments = []

    arch_tensions = [t for t in tensions_data.get("tensions", [])
                     if t["tension_type"] == "architecture_cross_sector_gap"]

    for t in arch_tensions:
        arch = t["architecture"]
        worst_nid = t["worst_narrative"]
        spread = t["spread"]

        best_nid = t["best_narrative"]
        best_count = sum(1 for m in models
                         if m.get("architecture") == arch and best_nid in m.get("narrative_ids", []))

        if best_count < 3:
            continue

        raw_delta = spread * 0.01 * DAMPING
        base_delta = min(1.0, raw_delta)

        for m in models:
            if m.get("architecture") != arch:
                continue
            if worst_nid not in m.get("narrative_ids", []):
                continue
            if not is_heuristic_cla(m):
                continue

            mid = m["id"]
            cum_mo = cumulative[mid]["MO"]
            remaining = MAX_AXIS_CHANGE - abs(cum_mo)
            if remaining < 0.01:
                continue

            delta = min(base_delta, remaining)
            cla = m.get("cla", {})
            cla_scores = cla.get("scores", {})
            old_mo = cla_scores.get("MO", 5)
            new_mo = clamp(round(old_mo + delta, 1))

            if abs(new_mo - old_mo) > 0.01:
                cla_scores["MO"] = new_mo
                old_composite = cla.get("composite", 0)
                cla["composite"] = round(recompute_cla_composite(cla_scores), 2)
                cla["category"] = cla_category(cla["composite"])
                cumulative[mid]["MO"] += (new_mo - old_mo)

                adjustments.append({
                    "rule": "rule_4_architecture_cross_sector_mo",
                    "model_id": mid,
                    "field": "cla.scores.MO",
                    "old_value": old_mo,
                    "new_value": new_mo,
                    "delta": round(new_mo - old_mo, 3),
                    "cumulative_mo": round(cumulative[mid]["MO"], 3),
                    "architecture": arch,
                    "worst_narrative": worst_nid,
                    "spread": spread,
                    "best_sector_examples": best_count,
                    "old_composite": old_composite,
                    "new_composite": cla["composite"],
                    "evidence": (f"Architecture '{arch}' spread={spread:.1f} across sectors. "
                                 f"{best_count} examples in best sector validate pattern. "
                                 f"Damping {DAMPING}."),
                })

    log["rule_4_adjustments"] = len(adjustments)
    log["adjustments"].extend(adjustments)
    return adjustments


# ---------------------------------------------------------------------------
# Propagation Rule 5: Model cluster → Force velocity signal (advisory)
# ---------------------------------------------------------------------------

def rule_5_force_velocity_signal(models, log):
    """
    If 20+ models driven by force F have avg T > 70: signal "force confirmed"
    If 20+ models driven by force F have avg T < 55: signal "force weakening"
    ADVISORY ONLY — no scores change.
    """
    signals = []

    force_models = defaultdict(list)
    for m in models:
        for f in m.get("forces_v3", []):
            fn = normalize_force(f)
            force_models[fn].append(m)

    for force, fmodels in force_models.items():
        if len(fmodels) < 20:
            continue

        avg_t = sum(m.get("composite", 0) for m in fmodels) / len(fmodels)

        signal = None
        if avg_t > 70:
            signal = "force_confirmed"
        elif avg_t < 55:
            signal = "force_weakening"

        if signal:
            signals.append({
                "rule": "rule_5_force_velocity_signal",
                "force_id": force,
                "signal": signal,
                "model_count": len(fmodels),
                "avg_t": round(avg_t, 1),
                "note": f"Advisory only — force {force} has {len(fmodels)} models with avg T={avg_t:.1f}. Signal: {signal}.",
            })

    log["rule_5_signals"] = signals
    return signals


# ---------------------------------------------------------------------------
# Main propagation loop
# ---------------------------------------------------------------------------

def run(dry_run=False):
    print("v5 Propagator")
    print("=" * 60)

    # Load data
    models_data = load_json(V4_DIR / "models.json")
    narratives_data = load_json(V4_DIR / "narratives.json")
    tensions_data = load_json(V5_DIR / "tensions.json")

    models = models_data["models"]
    narratives = narratives_data["narratives"]
    narr_idx = {n["narrative_id"]: n for n in narratives}

    print(f"  Models: {len(models)}, Narratives: {len(narratives)}")
    print(f"  Tensions: {len(tensions_data.get('tensions', []))}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")

    # Take snapshot for comparison
    original_models = copy.deepcopy(models)
    original_narratives = copy.deepcopy(narratives)

    # Cumulative change tracker: model_id → {axis: cumulative_delta}
    # Enforces MAX_AXIS_CHANGE across all iterations combined
    cumulative = defaultdict(lambda: defaultdict(float))

    # Propagation log
    full_log = {
        "cycle": tensions_data.get("cycle", "v5-0"),
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "dry_run" if dry_run else "live",
        "convergence": {
            "max_iterations": MAX_ITERATIONS,
            "convergence_threshold": CONVERGENCE_THRESHOLD,
            "max_axis_change": MAX_AXIS_CHANGE,
        },
        "iterations": [],
    }

    # Iterative propagation
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")

        iter_log = {
            "iteration": iteration,
            "adjustments": [],
        }

        # Apply all 5 rules (cumulative tracker enforces MAX_AXIS_CHANGE across iterations)
        print("  Rule 1: Narrative phase → Model TG...")
        a1 = rule_1_narrative_phase_tg(models, narratives, iter_log, cumulative)
        print(f"    {len(a1)} adjustments")

        print("  Rule 2: Model VCR → TNS ES...")
        a2 = rule_2_model_vcr_to_tns_es(models, narratives, iter_log)
        print(f"    {len(a2)} adjustments")

        print("  Rule 3: VCR ROI → CLA MA...")
        a3 = rule_3_vcr_roi_ma_challenge(models, iter_log, cumulative)
        print(f"    {len(a3)} adjustments")

        print("  Rule 4: Architecture cross-sector → MO...")
        a4 = rule_4_architecture_cross_sector_mo(models, tensions_data, narr_idx, iter_log, cumulative)
        print(f"    {len(a4)} adjustments")

        print("  Rule 5: Force velocity signal (advisory)...")
        s5 = rule_5_force_velocity_signal(models, iter_log)
        print(f"    {len(s5)} signals")

        # Composite capping: enforce ±3 on T-composite and CLA-composite
        composite_caps = 0
        for i_m, m in enumerate(models):
            om = original_models[i_m]
            # T-composite cap
            t_delta = m["composite"] - om["composite"]
            if abs(t_delta) > MAX_AXIS_CHANGE:
                # Scale TG back to stay within composite cap
                target_composite = om["composite"] + (MAX_AXIS_CHANGE if t_delta > 0 else -MAX_AXIS_CHANGE)
                # Reverse-engineer TG: target = (SN*25+FA*25+EC*20+TG*15+CE*15)/10
                scores = m["scores"]
                needed_tg = (target_composite * 10 - scores["SN"]*25 - scores["FA"]*25 - scores["EC"]*20 - scores["CE"]*15) / 15
                needed_tg = clamp(round(needed_tg, 2))
                scores["TG"] = needed_tg
                m["composite"] = round(recompute_t_composite(scores), 2)
                cumulative[m["id"]]["TG"] = needed_tg - om["scores"]["TG"]
                composite_caps += 1

            # CLA-composite cap
            o_delta = m.get("cla", {}).get("composite", 0) - om.get("cla", {}).get("composite", 0)
            if abs(o_delta) > MAX_AXIS_CHANGE:
                # Scale back the CLA axis that changed most
                cla = m["cla"]
                cla_scores = cla["scores"]
                ocla = om["cla"]["scores"]
                # Find which axis changed most
                max_axis = max(["MO", "MA", "VD", "DV"],
                               key=lambda a: abs(cla_scores.get(a, 0) - ocla.get(a, 0)))
                # Target composite
                target_cla = om["cla"]["composite"] + (MAX_AXIS_CHANGE if o_delta > 0 else -MAX_AXIS_CHANGE)
                # Reverse-engineer: what value of max_axis gives target?
                weights = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}
                other_sum = sum(cla_scores[a] * weights[a] for a in weights if a != max_axis)
                needed_val = (target_cla * 10 - other_sum) / weights[max_axis]
                needed_val = clamp(round(needed_val, 1))
                cla_scores[max_axis] = needed_val
                cla["composite"] = round(recompute_cla_composite(cla_scores), 2)
                cla["category"] = cla_category(cla["composite"])
                cumulative[m["id"]][max_axis] = needed_val - ocla[max_axis]
                composite_caps += 1

        if composite_caps:
            print(f"    Composite caps applied: {composite_caps}")

        # Compute max change this iteration
        max_change = 0
        for adj in iter_log["adjustments"]:
            max_change = max(max_change, abs(adj.get("delta", 0)))

        iter_log["max_change"] = round(max_change, 3)
        iter_log["total_adjustments"] = len(iter_log["adjustments"])
        full_log["iterations"].append(iter_log)

        print(f"\n  Iteration {iteration} summary:")
        print(f"    Total adjustments: {iter_log['total_adjustments']}")
        print(f"    Max single change: {max_change:.3f}")

        if max_change < CONVERGENCE_THRESHOLD:
            print(f"    CONVERGED (max change {max_change:.3f} < threshold {CONVERGENCE_THRESHOLD})")
            break
        elif iteration == MAX_ITERATIONS:
            print(f"    MAX ITERATIONS reached (max change {max_change:.3f})")

    # Compute summary statistics
    total_adjustments = sum(i["total_adjustments"] for i in full_log["iterations"])
    models_changed = set()
    narratives_changed = set()
    for i in full_log["iterations"]:
        for adj in i["adjustments"]:
            if "model_id" in adj:
                models_changed.add(adj["model_id"])
            if "narrative_id" in adj:
                narratives_changed.add(adj["narrative_id"])

    # Score change analysis
    t_changes = []
    o_changes = []
    for i, m in enumerate(models):
        om = original_models[i]
        t_delta = m["composite"] - om["composite"]
        o_delta = m.get("cla", {}).get("composite", 0) - om.get("cla", {}).get("composite", 0)
        if abs(t_delta) > 0.01:
            t_changes.append({"id": m["id"], "old": om["composite"], "new": m["composite"], "delta": round(t_delta, 2)})
        if abs(o_delta) > 0.01:
            o_changes.append({"id": m["id"], "old": om.get("cla", {}).get("composite", 0),
                              "new": m.get("cla", {}).get("composite", 0), "delta": round(o_delta, 2)})

    tns_changes = []
    for i, n in enumerate(narratives):
        on = original_narratives[i]
        tns_delta = n.get("tns", {}).get("composite", 0) - on.get("tns", {}).get("composite", 0)
        if abs(tns_delta) > 0.01:
            tns_changes.append({"id": n["narrative_id"], "old": on["tns"]["composite"],
                                "new": n["tns"]["composite"], "delta": round(tns_delta, 2)})

    full_log["summary"] = {
        "total_adjustments": total_adjustments,
        "iterations_run": len(full_log["iterations"]),
        "converged": full_log["iterations"][-1]["max_change"] < CONVERGENCE_THRESHOLD,
        "models_changed": len(models_changed),
        "narratives_changed": len(narratives_changed),
        "t_score_changes": len(t_changes),
        "o_score_changes": len(o_changes),
        "tns_changes": len(tns_changes),
        "force_signals": full_log["iterations"][-1].get("rule_5_signals", []),
    }

    # Validate bounds
    violations = []
    for m in models:
        for axis, val in m.get("scores", {}).items():
            if val < 1 or val > 10:
                violations.append(f"{m['id']}.scores.{axis} = {val}")
        for axis, val in m.get("cla", {}).get("scores", {}).items():
            if val < 1 or val > 10:
                violations.append(f"{m['id']}.cla.scores.{axis} = {val}")

    if violations:
        print(f"\n  ⚠ BOUND VIOLATIONS: {len(violations)}")
        for v in violations[:5]:
            print(f"    {v}")
    else:
        print("\n  All scores within bounds [1, 10].")

    # Print change summary
    print(f"\n{'=' * 60}")
    print(f"PROPAGATION COMPLETE")
    print(f"  Iterations: {len(full_log['iterations'])}")
    print(f"  Converged: {full_log['summary']['converged']}")
    print(f"  Total adjustments: {total_adjustments}")
    print(f"  Models changed: {len(models_changed)}/{len(models)}")
    print(f"  Narratives changed: {len(narratives_changed)}/{len(narratives)}")

    if t_changes:
        print(f"\n  T-score changes ({len(t_changes)}):")
        for c in sorted(t_changes, key=lambda x: -abs(x["delta"]))[:5]:
            print(f"    {c['id']}: {c['old']} → {c['new']} ({c['delta']:+.2f})")
        if len(t_changes) > 5:
            print(f"    ... and {len(t_changes) - 5} more")

    if o_changes:
        print(f"\n  O-score changes ({len(o_changes)}):")
        for c in sorted(o_changes, key=lambda x: -abs(x["delta"]))[:5]:
            print(f"    {c['id']}: {c['old']} → {c['new']} ({c['delta']:+.2f})")
        if len(o_changes) > 5:
            print(f"    ... and {len(o_changes) - 5} more")

    if tns_changes:
        print(f"\n  TNS changes ({len(tns_changes)}):")
        for c in tns_changes:
            print(f"    {c['id']}: {c['old']} → {c['new']} ({c['delta']:+.2f})")

    # Force velocity signals
    signals = full_log["summary"]["force_signals"]
    if signals:
        print(f"\n  Force velocity signals ({len(signals)}):")
        for s in signals:
            print(f"    {s['force_id']}: {s['signal']} (n={s['model_count']}, avgT={s['avg_t']})")

    # Write propagation log
    V5_DIR.mkdir(parents=True, exist_ok=True)
    log_path = V5_DIR / "propagation_log.json"
    save_json(log_path, full_log)
    print(f"\n  Propagation log: {log_path}")

    # Write updated data (unless dry run)
    if not dry_run:
        save_json(V4_DIR / "models.json", models_data)
        save_json(V4_DIR / "narratives.json", narratives_data)
        print(f"  Updated: data/v4/models.json ({len(models_changed)} models changed)")
        print(f"  Updated: data/v4/narratives.json ({len(narratives_changed)} narratives changed)")
    else:
        print(f"\n  DRY RUN — no files modified.")

    return full_log


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    run(dry_run=dry)
