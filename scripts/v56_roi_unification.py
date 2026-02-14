#!/usr/bin/env python3
"""
v5.6 ROI Unification Pass
Re-derives roi_estimate for all 828 models through the single canonical
formula from vcr_scoring.py. Fixes inconsistencies across batch rounds.
"""

import json
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MODELS_FILE = BASE / "data" / "v4" / "models.json"
STATE_FILE = BASE / "data" / "v5" / "state.json"

SEED_VALUATION_M = 10  # $10M seed

# Canonical lookup tables (from vcr_scoring.py)
MKT_TO_TAM_M = {
    1: 10, 2: 30, 3: 75, 4: 150, 5: 400,
    6: 800, 7: 2000, 8: 4000, 9: 8000, 10: 20000
}

CAP_TO_SHARE = {
    1: 0.001, 2: 0.002, 3: 0.004, 4: 0.006, 5: 0.01,
    6: 0.015, 7: 0.02, 8: 0.03, 9: 0.04, 10: 0.05
}

# Revenue multiples by architecture (from vcr_scoring.py + missing archs)
ARCH_MULTIPLES = {
    "data_compounding": (12, 25),
    "platform": (10, 20),
    "platform_infrastructure": (10, 18),
    "infrastructure_platform": (10, 18),
    "network_platform": (10, 18),
    "vertical_saas": (8, 15),
    "saas": (8, 12),
    "platform_saas": (8, 15),
    "marketplace_network": (5, 12),
    "marketplace_platform": (5, 12),
    "marketplace": (5, 10),
    "marketplace_optimizer": (5, 10),
    "platform_marketplace": (6, 12),
    "regulatory_moat_builder": (6, 12),
    "fear_economy_capture": (8, 15),
    "product_platform": (6, 12),
    "physical_product_platform": (5, 10),
    "hardware_plus_saas": (6, 10),
    "service_platform": (5, 10),
    "platform_service": (5, 10),
    "advisory_platform": (4, 8),
    "academy_platform": (4, 8),
    "product": (5, 10),
    "full_service_replacement": (3, 6),
    "acquire_and_modernize": (4, 8),
    "rollup_consolidation": (3, 5),
    "roll_up_modernize": (3, 5),
    "rollup": (3, 5),
    "automation": (5, 8),
    "physical_production_ai": (4, 7),
    "project_developer": (3, 5),
    "project_development": (3, 5),
    "distress_operator": (3, 6),
    "arbitrage_window": (3, 7),
    "geographic_arbitrage": (3, 6),
    "advisory": (3, 6),
    "managed_service": (3, 6),
    "service": (3, 5),
    "hybrid_service": (3, 6),
    "open_core_ecosystem": (10, 20),
    "outcome_based": (4, 10),
    "coordination_protocol": (8, 18),
    # Architectures present in corpus but missing from vcr_scoring.py
    "ai_copilot": (8, 15),             # SaaS-like recurring revenue, high engagement
    "compliance_automation": (6, 12),   # regulatory moat, sticky contracts
    "enabling_infrastructure": (10, 18),# platform-tier multiples
    "hardware_ai": (6, 10),            # hardware+SaaS blend
    "robotics_automation": (5, 10),    # physical+software, moderate multiples
}


def estimate_roi(model):
    """Canonical ROI estimator — identical to vcr_scoring.py."""
    arch = model.get("architecture", "")
    vcr_scores = model.get("vcr", {}).get("scores", {})

    if not vcr_scores:
        return None

    mult_range = ARCH_MULTIPLES.get(arch, (5, 10))

    moa = vcr_scores.get("MOA", 5)
    mult = mult_range[0] + (mult_range[1] - mult_range[0]) * (moa - 1) / 9

    mkt_rounded = max(1, min(10, round(vcr_scores.get("MKT", 5))))
    tam = MKT_TO_TAM_M.get(mkt_rounded, 400)

    cap_rounded = max(1, min(10, round(vcr_scores.get("CAP", 5))))
    share = CAP_TO_SHARE.get(cap_rounded, 0.01)

    vel_mult = 0.7 + (vcr_scores.get("VEL", 5) - 1) * 0.1

    year5_revenue = tam * share * vel_mult
    exit_val = year5_revenue * mult
    roi_multiple = round(exit_val / SEED_VALUATION_M, 1)
    roi_multiple = max(0.1, min(500, roi_multiple))

    return {
        "year5_revenue_M": round(year5_revenue, 1),
        "revenue_multiple": round(mult, 1),
        "exit_val_M": round(exit_val, 0),
        "seed_roi_multiple": roi_multiple,
    }


def main():
    print("=" * 70)
    print("v5.6 ROI Unification Pass")
    print("=" * 70)

    with open(MODELS_FILE) as f:
        models_data = json.load(f)
    models = models_data.get("models", models_data)
    print("Loaded {} models".format(len(models)))

    # Collect before stats
    before_rois = []
    for m in models:
        roi = m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple")
        if roi is not None:
            before_rois.append(roi)

    # Re-derive ROI for every model
    changed = 0
    unchanged = 0
    no_vcr = 0
    big_changes = []

    for m in models:
        roi_new = estimate_roi(m)
        if roi_new is None:
            no_vcr += 1
            continue

        old_roi = m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple", 0)
        new_roi = roi_new["seed_roi_multiple"]

        if old_roi != new_roi:
            delta = new_roi - old_roi
            pct = abs(delta / old_roi * 100) if old_roi else 0
            if abs(delta) > 50 or pct > 200:
                big_changes.append((m["id"], old_roi, new_roi, delta))
            changed += 1
        else:
            unchanged += 1

        m["vcr"]["roi_estimate"] = roi_new

    # After stats
    after_rois = []
    for m in models:
        roi = m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple")
        if roi is not None:
            after_rois.append(roi)

    print("\n  Changed: {}  Unchanged: {}  No VCR: {}".format(changed, unchanged, no_vcr))

    # Distribution comparison
    print("\n  BEFORE:")
    if before_rois:
        print("    Mean={:.1f}x  Median={:.1f}x  Max={:.1f}x  Stdev={:.1f}".format(
            statistics.mean(before_rois), statistics.median(before_rois),
            max(before_rois), statistics.stdev(before_rois)))
        above_500 = sum(1 for r in before_rois if r > 500)
        at_500 = sum(1 for r in before_rois if r == 500)
        print("    Above 500x: {}  At 500x: {}".format(above_500, at_500))

    print("\n  AFTER:")
    if after_rois:
        print("    Mean={:.1f}x  Median={:.1f}x  Max={:.1f}x  Stdev={:.1f}".format(
            statistics.mean(after_rois), statistics.median(after_rois),
            max(after_rois), statistics.stdev(after_rois)))
        above_500 = sum(1 for r in after_rois if r > 500)
        at_500 = sum(1 for r in after_rois if r == 500)
        print("    Above 500x: {}  At 500x: {}".format(above_500, at_500))

    # Show biggest changes
    if big_changes:
        big_changes.sort(key=lambda x: abs(x[3]), reverse=True)
        print("\n  Largest ROI changes (|delta| > 50x or >200%):")
        for mid, old, new, delta in big_changes[:15]:
            print("    {} : {:.1f}x -> {:.1f}x ({:+.1f}x)".format(mid, old, new, delta))

    # Verify consistency
    print("\n  Verification:")
    issues = 0
    for m in models:
        roi = m.get("vcr", {}).get("roi_estimate", {})
        if not roi:
            continue
        sr = roi.get("seed_roi_multiple", 0)
        if sr < 0.1 or sr > 500:
            print("    OUT OF BOUNDS: {} = {}x".format(m["id"], sr))
            issues += 1
        for field in ("year5_revenue_M", "revenue_multiple", "exit_val_M", "seed_roi_multiple"):
            if field not in roi:
                print("    MISSING FIELD: {} missing {}".format(m["id"], field))
                issues += 1
    print("    Issues: {}".format(issues))

    # Save
    with open(MODELS_FILE, "w") as f:
        json.dump(models_data, f, indent=2)
    print("\n  Saved {} models".format(len(models)))

    # Update state
    with open(STATE_FILE) as f:
        state = json.load(f)
    state["engine_version"] = "5.6"
    state["description"] = "v5.6: 828 models. ROI unification pass: all roi_estimate values re-derived through canonical formula (vcr_scoring.py). Fixes v53 exponential bug, v54/v55 simplified formulas."
    state["cycles"].append({
        "cycle_id": "v5-6-roi-unification",
        "date": "2026-02-14",
        "models_before": len(models),
        "models_after": len(models),
        "roi_changed": changed,
        "roi_unchanged": unchanged,
        "key_findings": [
            "Unified ROI formula: all 828 models through canonical vcr_scoring.py estimator",
            "Before: mean={:.1f}x, max={:.1f}x. After: mean={:.1f}x, max={:.1f}x".format(
                statistics.mean(before_rois), max(before_rois),
                statistics.mean(after_rois), max(after_rois)),
            "{} models changed, {} unchanged".format(changed, unchanged),
            "All seed_roi_multiple now in [0.1, 500] range with 1-decimal precision",
        ]
    })
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print("  State updated to v5.6")

    print("=" * 70)


if __name__ == "__main__":
    main()
