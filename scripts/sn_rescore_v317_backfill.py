#!/usr/bin/env python3
"""
v3-17 SN Backfill: Re-score 70 models that previously lacked Polanyi data.

These 70 models (NAICS 11, 21, 22, 92) had polanyi=None and used the
wage-growth fallback path in v3-16's SN scoring. They've now been backfilled
with sector-level proxy automation_exposure values (tagged source: sector_proxy_v317).

This script:
1. Assigns sector-level proxy Polanyi data to the 70 models
2. Applies the SAME Polanyi+Baumol data-driven Component 3 formula from v316
3. Recomputes SN using the 4-component blend
4. Recomputes t_composite: (SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10
5. Saves back to the normalized file
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
QCEW_FILE = Path("/Users/mv/Documents/research/data/cache/qcew_sn_lookup.json")

# ── Sector-level proxy automation_exposure values ──────────────────
# These are estimated from:
#   - Adjacent/similar sector averages from the enriched 538 models
#   - BLS occupation structure for each sector
#   - Literature on automation potential (Frey & Osborne, McKinsey)
#
# NAICS 11 (Agriculture): Physical + seasonal labor, moderate routine tasks
#   Closest analogs: Construction (0.330), Manufacturing (0.320-0.350)
#   Agriculture has high routine-manual (harvesting, planting) but low
#   routine-cognitive. Proxy: 0.310 (slightly below construction)
#
# NAICS 21 (Mining): Heavy equipment operation, geological analysis
#   Closest analogs: Construction (0.330), Transportation (0.390)
#   Mining has high routine-manual (extraction) + moderate analytical.
#   Proxy: 0.345 (between construction and transport)
#
# NAICS 22 (Utilities): Grid ops, plant monitoring, field maintenance
#   Closest analogs: Manufacturing (0.330-0.350), Transportation (0.390)
#   Utilities have high routine-cognitive (monitoring/dispatch) but
#   also high safety-critical human judgment. Proxy: 0.355
#
# NAICS 92 (Government): Administrative, policy, enforcement
#   Closest analogs: Professional Services (0.308), Admin (0.340)
#   Government is a mix of clerical (high automation) and policy/enforcement
#   (low automation). Proxy: 0.320 (weighted toward admin-heavy)
SECTOR_PROXY_AE = {
    '11': 0.310,  # Agriculture
    '21': 0.345,  # Mining
    '22': 0.355,  # Utilities
    '92': 0.320,  # Government
}

# Dominant task categories for sector proxies
SECTOR_PROXY_DOMINANT = {
    '11': 'routine_manual',
    '21': 'routine_manual',
    '22': 'routine_cognitive',
    '92': 'routine_cognitive',
}


def clamp(v, lo=1.0, hi=10.0):
    return max(lo, min(hi, round(v, 1)))


# ── Component 1: Architecture Substitutability (from v316) ──
ARCH_SUBSTITUTABILITY = {
    "full_service_replacement": 3,
    "vertical_saas": 7,
    "platform_infrastructure": 4,
    "data_compounding": 2,
    "marketplace_network": 5,
    "acquire_and_modernize": 1,
    "rollup_consolidation": 1,
    "service_platform": 8,
    "regulatory_moat_builder": 3,
    "physical_production_ai": 3,
    "hardware_ai": 3,
    "robotics_automation": 1,
    "ai_copilot": 9,
    "compliance_automation": 6,
    "arbitrage_window": 9,
}

# ── Component 3 baseline: Incumbent Adaptation Risk (from v316) ──
INCUMBENT_ADAPTATION_RISK = {
    "11": 2, "21": 3, "22": 4, "23": 2, "31": 4, "32": 4, "33": 5,
    "42": 4, "44": 6, "45": 5, "48": 5, "49": 4, "51": 9, "52": 7,
    "53": 4, "54": 6, "55": 6, "56": 3, "61": 5, "62": 5, "71": 4,
    "72": 3, "81": 2, "92": 3,
}

# QCEW NAICS mapping for combined codes (from v316)
NAICS_COMBINED = {
    "31": "31-33", "32": "31-33", "33": "31-33",
    "44": "44-45", "45": "44-45",
    "48": "48-49", "49": "48-49",
}


def load_qcew():
    """Load QCEW sector lookup data."""
    with open(QCEW_FILE) as f:
        return json.load(f)


def qcew_lookup(qcew_data, naics_full):
    """Look up QCEW data for a NAICS code, trying progressively shorter prefixes."""
    for length in (4, 3, 2):
        prefix = naics_full[:length] if len(naics_full) >= length else None
        if not prefix:
            continue
        if prefix in qcew_data["sectors"]:
            return qcew_data["sectors"][prefix]
        combined = NAICS_COMBINED.get(prefix)
        if combined and combined in qcew_data["sectors"]:
            return qcew_data["sectors"][combined]
    return None


def compute_new_sn(model, sector_model_counts, qcew_data):
    """
    Compute SN with data-driven Polanyi + Baumol component.
    
    This is the EXACT same formula as v316's compute_new_sn, but now
    all models have automation_exposure (the 70 backfilled models take
    the primary Polanyi path instead of the wage-growth fallback).
    """
    arch = model.get("architecture", "vertical_saas")
    naics2 = (model.get("sector_naics") or "")[:2]

    # Component 1: Architecture uniqueness (40%) -- unchanged from v316
    sub = ARCH_SUBSTITUTABILITY.get(arch, 5)
    arch_uniqueness = 11 - sub

    # Component 2: Competitive density penalty (25%) -- unchanged from v316
    sector_count = sector_model_counts.get(naics2, 10)
    if sector_count <= 5:
        density_score = 10.0
    elif sector_count <= 10:
        density_score = 8.5
    elif sector_count <= 18:
        density_score = 7.0
    elif sector_count <= 28:
        density_score = 5.0
    elif sector_count <= 45:
        density_score = 3.0
    else:
        density_score = 1.5

    # Component 3: Data-driven Polanyi + Baumol (20%) -- SAME formula as v316
    polanyi = model.get("polanyi", {})
    automation_exp = polanyi.get("automation_exposure") if polanyi else None
    qcew_sector = qcew_lookup(qcew_data, model.get("sector_naics") or "")
    base_adapt = INCUMBENT_ADAPTATION_RISK.get(naics2, 5)
    base_necessity = 11 - base_adapt

    if automation_exp is not None:
        # Primary path: Polanyi-driven necessity
        # Scale: 0.28->2.5, 0.33->5.5, 0.39->9.0
        polanyi_necessity = 2.5 + (automation_exp - 0.28) * (6.5 / 0.11)
        polanyi_necessity = max(1.5, min(9.5, polanyi_necessity))

        # Baumol cross-reference: CONTINUOUS modifier
        if qcew_sector:
            baumol = qcew_sector.get("baumol_score", 1.0)

            if baumol < 1.0:
                # Below-average wages: urgency modifier (mild boost)
                baumol_mod = 1.0 + (1.0 - baumol) * 0.15
            else:
                # Above-average wages: depends on incumbent tech maturity
                excess = baumol - 1.0
                if base_adapt >= 7:
                    # Tech/finance: incumbents WILL adapt -> penalty
                    baumol_mod = 1.0 - excess * 0.25
                elif base_adapt <= 3:
                    # Low-tech sectors: cost disease = strong push
                    baumol_mod = 1.0 + excess * 0.30
                else:
                    # Mid-tech: slight boost
                    baumol_mod = 1.0 + excess * 0.08

            baumol_mod = max(0.70, min(1.35, baumol_mod))
            polanyi_necessity *= baumol_mod

        polanyi_necessity = max(1.0, min(10.0, polanyi_necessity))

        # Blend: 65% Polanyi-Baumol, 35% baseline
        adaptation_necessity = polanyi_necessity * 0.65 + base_necessity * 0.35
    else:
        # This path should NOT be reached for backfilled models
        raise ValueError(f"Model {model['id']} still has no automation_exposure after backfill")

    # Component 4: Market concentration necessity (15%) -- unchanged from v316
    mo = model.get("cla", {}).get("scores", {}).get("MO", 5)
    market_necessity = 11 - mo

    # Weighted blend
    raw_sn = (
        arch_uniqueness * 0.40
        + density_score * 0.25
        + adaptation_necessity * 0.20
        + market_necessity * 0.15
    )

    # Spread the distribution
    center = 5.8
    spread = 1.65
    new_sn = center + (raw_sn - center) * spread

    # Architecture-specific adjustments
    if arch == "arbitrage_window":
        new_sn -= 0.8

    # Sub-model adjustment
    if model.get("parent_id"):
        layer = (model.get("layer_name") or "").lower()
        if "software" in layer or "data" in layer or "analytics" in layer:
            new_sn += 0.5
        elif "physical" in layer or "hardware" in layer:
            new_sn -= 0.3

    return clamp(new_sn)


def main():
    print("=" * 70)
    print("v3-17 SN BACKFILL: Re-score 70 models with sector-proxy Polanyi data")
    print("=" * 70)

    # Load data
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models from {NORMALIZED_FILE.name}")

    qcew_data = load_qcew()
    print(f"Loaded QCEW: {qcew_data['_meta']['total_sectors']} sectors")

    # Identify the 70 models with polanyi=None
    backfill_targets = [m for m in models if m.get("polanyi") is None]
    print(f"\nModels needing backfill: {len(backfill_targets)}")

    if len(backfill_targets) == 0:
        print("No models need backfill -- all already have Polanyi data.")
        return

    # Show NAICS distribution
    naics_dist = Counter((m.get("sector_naics") or "??")[:2] for m in backfill_targets)
    for naics, count in sorted(naics_dist.items()):
        proxy_ae = SECTOR_PROXY_AE.get(naics, "???")
        print(f"  NAICS {naics}: {count} models -> proxy automation_exposure = {proxy_ae}")

    # Step 1: Backfill Polanyi data with sector-level proxies
    print(f"\n--- Step 1: Backfilling Polanyi data ---")
    for m in backfill_targets:
        naics2 = (m.get("sector_naics") or "")[:2]
        ae = SECTOR_PROXY_AE.get(naics2)
        if ae is None:
            print(f"  WARNING: No proxy AE for {m['id']} (NAICS {naics2}), using 0.330")
            ae = 0.330

        dominant = SECTOR_PROXY_DOMINANT.get(naics2, "routine_cognitive")

        m["polanyi"] = {
            "automation_exposure": ae,
            "judgment_premium": round(0.50 - ae, 3),  # Complementary estimate
            "human_premium": round(1.0 - ae - (0.50 - ae), 3),  # Remainder
            "dominant_category": dominant,
            "source": "sector_proxy_v317",
            "proxy_naics": naics2,
        }

    backfilled_count = sum(1 for m in models if (m.get("polanyi") or {}).get("source") == "sector_proxy_v317")
    print(f"  Backfilled: {backfilled_count} models tagged with source=sector_proxy_v317")

    # Step 2: Compute sector density (needed for Component 2)
    sector_counts = Counter((m.get("sector_naics") or "")[:2] for m in models)

    # Step 3: Re-score SN for ONLY the 70 backfilled models
    print(f"\n--- Step 2: Re-scoring SN for {len(backfill_targets)} models ---")
    print()
    print(f"  {'ID':<28s} {'Name':<42s} {'Old SN':>6s} {'New SN':>6s} {'Chg':>6s}  {'Old T':>6s} {'New T':>6s} {'Chg':>6s}")
    print("  " + "-" * 148)

    changes = []
    for m in backfill_targets:
        old_sn = m["scores"]["SN"]
        old_composite = m.get("composite", 0)

        # Compute new SN using data-driven Polanyi+Baumol path
        new_sn = compute_new_sn(m, sector_counts, qcew_data)

        # Update SN
        m["scores"]["SN"] = new_sn

        # Recompute t_composite
        s = m["scores"]
        new_composite = round(
            (s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2
        )
        m["composite"] = new_composite

        sn_delta = new_sn - old_sn
        t_delta = new_composite - old_composite

        changes.append({
            "id": m["id"],
            "name": m["name"],
            "old_sn": old_sn,
            "new_sn": new_sn,
            "sn_delta": sn_delta,
            "old_composite": old_composite,
            "new_composite": new_composite,
            "t_delta": t_delta,
            "naics2": (m.get("sector_naics") or "")[:2],
            "arch": m.get("architecture", ""),
        })

        direction = "+" if sn_delta > 0 else ("-" if sn_delta < 0 else "=")
        print(f"  {m['id']:<28s} {m['name'][:40]:<42s} {old_sn:>6.1f} {new_sn:>6.1f} {sn_delta:>+6.1f}  {old_composite:>6.1f} {new_composite:>6.1f} {t_delta:>+6.1f}")

    # Summary statistics
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")

    sn_deltas = [c["sn_delta"] for c in changes]
    t_deltas = [c["t_delta"] for c in changes]
    went_up = sum(1 for d in sn_deltas if d > 0)
    went_down = sum(1 for d in sn_deltas if d < 0)
    stayed_same = sum(1 for d in sn_deltas if d == 0)

    print(f"\n  Models rescored: {len(changes)}")
    print(f"  SN went UP:      {went_up}")
    print(f"  SN went DOWN:    {went_down}")
    print(f"  SN unchanged:    {stayed_same}")
    print(f"\n  Mean SN change:   {statistics.mean(sn_deltas):+.2f}")
    print(f"  Median SN change: {statistics.median(sn_deltas):+.2f}")
    print(f"  Stdev SN change:  {statistics.stdev(sn_deltas):.2f}")
    print(f"  Min SN change:    {min(sn_deltas):+.1f}")
    print(f"  Max SN change:    {max(sn_deltas):+.1f}")

    print(f"\n  Mean T-composite change:   {statistics.mean(t_deltas):+.2f}")
    print(f"  Median T-composite change: {statistics.median(t_deltas):+.2f}")

    # By NAICS sector
    print(f"\n  SN change by sector:")
    for naics in sorted(set(c["naics2"] for c in changes)):
        sector_deltas = [c["sn_delta"] for c in changes if c["naics2"] == naics]
        avg = statistics.mean(sector_deltas)
        print(f"    NAICS {naics}: n={len(sector_deltas):>2d}, mean SN change={avg:+.2f}")

    # Largest movers
    changes.sort(key=lambda c: abs(c["sn_delta"]), reverse=True)
    print(f"\n  Top 10 largest SN changes:")
    for c in changes[:10]:
        print(f"    {c['id']:<28s} {c['old_sn']:>5.1f} -> {c['new_sn']:>5.1f} ({c['sn_delta']:>+5.1f})  {c['name'][:35]}")

    # Step 4: Re-rank all models by t_composite (since composites changed)
    print(f"\n--- Step 3: Re-ranking all models ---")
    models.sort(key=lambda m: (-m["composite"], m["id"]))
    for i, m in enumerate(models, 1):
        m["rank"] = i

    # Opportunity and VCR ranks unchanged (CLA and VCR composites not affected)
    models_by_opp = sorted(models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(models_by_opp, 1):
        m["opportunity_rank"] = i

    models_by_vcr = sorted(models, key=lambda m: (-m.get("vcr", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(models_by_vcr, 1):
        m["vcr_rank"] = i

    # Sort back to T-rank order for output
    models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Step 5: Save
    print(f"\n--- Step 4: Saving ---")
    data["summary"]["total_models"] = len(models)

    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Written {len(models)} models to {NORMALIZED_FILE}")

    # Verify: count Polanyi coverage
    polanyi_count = sum(1 for m in models if (m.get("polanyi") or {}).get("automation_exposure") is not None)
    proxy_count = sum(1 for m in models if (m.get("polanyi") or {}).get("source") == "sector_proxy_v317")
    none_count = sum(1 for m in models if m.get("polanyi") is None)
    print(f"\n  Polanyi coverage: {polanyi_count}/{len(models)} (was {polanyi_count - proxy_count}/{len(models)})")
    print(f"  Sector proxies:   {proxy_count}")
    print(f"  Still missing:    {none_count}")
    print(f"\n  Done.")


if __name__ == "__main__":
    main()
