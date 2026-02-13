#!/usr/bin/env python3
"""
v3-16 SN Axis: Data-Driven Market Necessity

Builds on v3-15's 4-component SN scoring by replacing the hardcoded
INCUMBENT_ADAPTATION_RISK table (Component 3) with live data:
  - Polanyi automation_exposure (0-1) from O*NET enrichment
  - QCEW Baumol score (sector avg_pay / economy avg) from BLS data

Cross-reference logic:
  High automation + High Baumol → cost disease + viable automation = HIGH necessity
  High automation + Low Baumol → low wages but automatable = urgent need
  Low automation + High Baumol → defended sector, incumbents can build → LOWER necessity
  Low automation + Low Baumol → moderate baseline

For 70 models without Polanyi data (ag/mining/utilities/gov), uses
QCEW wage_growth as a proxy signal.

Components 1 (arch uniqueness, 40%), 2 (density, 25%), 4 (market concentration, 15%)
are unchanged from v3-15.

Target: r(SN, FA) stays < 0.35 (was 0.040 in v3-15)
"""

import json
import sys
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
QCEW_FILE = Path("/Users/mv/Documents/research/data/cache/qcew_sn_lookup.json")

def clamp(v, lo=1.0, hi=10.0):
    return max(lo, min(hi, round(v, 1)))


# ── Component 1: Architecture Substitutability (unchanged from v3-15) ──
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
    # v3-18 new architectures
    "open_core_ecosystem": 4,       # ecosystem hard to replicate
    "outcome_based": 5,             # pricing innovation, not tech
    "coordination_protocol": 3,     # very hard to replicate a standard
}

# ── Component 3 baseline: Incumbent Adaptation Risk (fallback only) ──
INCUMBENT_ADAPTATION_RISK = {
    "11": 2, "21": 3, "22": 4, "23": 2, "31": 4, "32": 4, "33": 5,
    "42": 4, "44": 6, "45": 5, "48": 5, "49": 4, "51": 9, "52": 7,
    "53": 4, "54": 6, "55": 6, "56": 3, "61": 5, "62": 5, "71": 4,
    "72": 3, "81": 2, "92": 3,
}

# QCEW NAICS mapping for combined codes
NAICS_COMBINED = {"31": "31-33", "32": "31-33", "33": "31-33", "44": "44-45", "45": "44-45",
                  "48": "48-49", "49": "48-49"}


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
        # Try exact match
        if prefix in qcew_data["sectors"]:
            return qcew_data["sectors"][prefix]
        # Try combined code (31→31-33, etc.)
        combined = NAICS_COMBINED.get(prefix)
        if combined and combined in qcew_data["sectors"]:
            return qcew_data["sectors"][combined]
    return None


def compute_new_sn(model, sector_model_counts, qcew_data):
    """Compute SN with data-driven Polanyi + Baumol component."""
    arch = model.get("architecture", "vertical_saas")
    naics2 = (model.get("sector_naics") or "")[:2]

    # Component 1: Architecture uniqueness (40%) — unchanged
    sub = ARCH_SUBSTITUTABILITY.get(arch, 5)
    arch_uniqueness = 11 - sub

    # Component 2: Competitive density penalty (25%) — unchanged
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

    # Component 3: Data-driven Polanyi + Baumol (20%) — NEW
    polanyi = model.get("polanyi", {})
    automation_exp = polanyi.get("automation_exposure") if polanyi else None
    qcew_sector = qcew_lookup(qcew_data, model.get("sector_naics") or "")
    base_adapt = INCUMBENT_ADAPTATION_RISK.get(naics2, 5)
    base_necessity = 11 - base_adapt

    if automation_exp is not None:
        # Primary path: Polanyi-driven necessity
        # Scale: 0.28→2.5, 0.33→5.5, 0.39→9.0
        polanyi_necessity = 2.5 + (automation_exp - 0.28) * (6.5 / 0.11)
        polanyi_necessity = max(1.5, min(9.5, polanyi_necessity))

        # Baumol cross-reference: CONTINUOUS modifier, not threshold-based
        # This splits models that share the same automation_exposure
        if qcew_sector:
            baumol = qcew_sector.get("baumol_score", 1.0)

            # Baumol modifier: maps baumol_score to a multiplier
            # Low baumol (0.4) → 1.10 (low wages = urgent need for cheap automation)
            # Mid baumol (1.0) → 1.00 (neutral)
            # High baumol (1.7) → depends on sector tech maturity:
            #   Tech-savvy (adapt≥7): 0.80 (incumbents build in-house)
            #   Non-tech (adapt<5):   1.20 (cost disease = strong push)
            #   Mid-tech:             1.05 (slight boost)
            if baumol < 1.0:
                # Below-average wages: urgency modifier (mild boost)
                baumol_mod = 1.0 + (1.0 - baumol) * 0.15
            else:
                # Above-average wages: depends on incumbent tech maturity
                excess = baumol - 1.0  # 0 to ~1.1
                if base_adapt >= 7:
                    # Tech/finance: incumbents WILL adapt → penalty
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
        # Fallback for 70 models without Polanyi (ag, mining, utilities, gov)
        if qcew_sector:
            wage_growth = qcew_sector.get("wage_growth", 0)
            # Scale: negative growth → 3, zero → 5, 10%+ → 8
            growth_necessity = 5.0 + (wage_growth * 30.0)
            growth_necessity = max(2.0, min(9.0, growth_necessity))
            # Blend: 35% wage signal, 65% baseline
            adaptation_necessity = growth_necessity * 0.35 + base_necessity * 0.65
        else:
            adaptation_necessity = base_necessity

    # Component 4: Market concentration necessity (15%) — unchanged
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


def classify_model(scores, forces_v3):
    """Reclassify model categories based on new SN scores."""
    cats = []
    if scores["SN"] >= 8.0 and scores["FA"] >= 8.0:
        cats.append("STRUCTURAL_WINNER")
    if scores["FA"] >= 7.0 and "STRUCTURAL_WINNER" not in cats:
        cats.append("FORCE_RIDER")
    if scores["TG"] >= 8.0 and scores["SN"] >= 6.0:
        cats.append("TIMING_ARBITRAGE")
    if scores["CE"] >= 8.0 and scores["SN"] >= 6.0:
        cats.append("CAPITAL_MOAT")

    if any("psychology" in str(f).lower() for f in (forces_v3 or [])):
        cats.append("FEAR_ECONOMY")

    if not cats:
        composite = (scores["SN"] * 25 + scores["FA"] * 25 + scores["EC"] * 20 +
                     scores["TG"] * 15 + scores["CE"] * 15) / 10
        if composite >= 60:
            cats.append("CONDITIONAL")
        else:
            cats.append("PARKED")
    return cats


def pearson_r(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return cov / (sx * sy) if sx * sy > 0 else 0


def main():
    apply_mode = "--apply" in sys.argv

    print("=" * 70)
    print("v3-16 SN AXIS: Data-Driven Market Necessity (Polanyi + Baumol)")
    print("=" * 70)
    print(f"Mode: {'APPLY (writing changes)' if apply_mode else 'ANALYZE (read-only)'}")
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # Load QCEW data
    qcew_data = load_qcew()
    print(f"Loaded QCEW: {qcew_data['_meta']['total_sectors']} sectors")

    # Polanyi coverage
    polanyi_count = sum(1 for m in models if (m.get("polanyi") or {}).get("automation_exposure") is not None)
    print(f"Polanyi coverage: {polanyi_count}/{len(models)}")

    # Compute sector density
    sector_counts = Counter((m.get("sector_naics") or "")[:2] for m in models)

    # ── Before state ──
    old_sn = [m["scores"]["SN"] for m in models]
    fa_scores = [m["scores"]["FA"] for m in models]
    old_r = pearson_r(old_sn, fa_scores)
    print(f"\nBEFORE: SN mean={statistics.mean(old_sn):.2f}, stdev={statistics.stdev(old_sn):.2f}")
    print(f"BEFORE: SN↔FA r={old_r:.3f}")

    old_struct_winners = sum(1 for m in models
                            if m["scores"]["SN"] >= 8.0 and m["scores"]["FA"] >= 8.0)
    print(f"BEFORE: STRUCTURAL_WINNER count={old_struct_winners}")

    # ── Compute new SN scores ──
    new_sn_scores = []
    changes = []
    for m in models:
        new_sn = compute_new_sn(m, sector_counts, qcew_data)
        old = m["scores"]["SN"]
        new_sn_scores.append(new_sn)
        polanyi = m.get("polanyi", {})
        ae = polanyi.get("automation_exposure") if polanyi else None
        qcew_sector = qcew_lookup(qcew_data, m.get("sector_naics") or "")
        baumol = qcew_sector.get("baumol_score") if qcew_sector else None
        changes.append({
            "id": m["id"],
            "name": m["name"],
            "old_sn": old,
            "new_sn": new_sn,
            "delta": new_sn - old,
            "fa": m["scores"]["FA"],
            "arch": m.get("architecture", ""),
            "naics2": (m.get("sector_naics") or "")[:2],
            "ae": ae,
            "baumol": baumol,
        })

    # ── After analysis ──
    new_r = pearson_r(new_sn_scores, fa_scores)
    new_mean = statistics.mean(new_sn_scores)
    new_stdev = statistics.stdev(new_sn_scores)
    new_min = min(new_sn_scores)
    new_max = max(new_sn_scores)

    buckets = Counter(round(s) for s in new_sn_scores)
    max_bucket_pct = max(buckets.values()) / len(new_sn_scores) * 100

    new_struct_winners = sum(1 for sn, fa in zip(new_sn_scores, fa_scores)
                            if sn >= 8.0 and fa >= 8.0)

    print(f"\nAFTER: SN mean={new_mean:.2f}, stdev={new_stdev:.2f}, min={new_min}, max={new_max}")
    print(f"AFTER: SN↔FA r={new_r:.3f}  (target < 0.35)")
    print(f"AFTER: STRUCTURAL_WINNER count={new_struct_winners} (was {old_struct_winners})")
    print(f"AFTER: Max bucket = {max_bucket_pct:.1f}% (target < 25%)")

    # Distribution
    print(f"\nNew SN distribution:")
    for k in sorted(buckets.keys()):
        bar = "█" * (buckets[k] // 3)
        print(f"  {k:>4.0f}: {buckets[k]:>4d} {bar}")

    # Data source breakdown
    polanyi_used = sum(1 for c in changes if c["ae"] is not None)
    baumol_used = sum(1 for c in changes if c["baumol"] is not None)
    print(f"\nData sources used:")
    print(f"  Polanyi automation_exposure: {polanyi_used}/{len(models)}")
    print(f"  QCEW Baumol cross-reference: {baumol_used}/{len(models)}")

    # Top movers
    changes.sort(key=lambda c: abs(c["delta"]), reverse=True)
    print(f"\nTop 15 largest SN changes:")
    print(f"  {'ID':<22s} {'Old':>5s} {'New':>5s} {'Δ':>6s} {'FA':>5s} {'AE':>5s} {'Baum':>5s} Name")
    print("  " + "-" * 110)
    for c in changes[:15]:
        ae_str = f"{c['ae']:.2f}" if c["ae"] is not None else "  -- "
        bm_str = f"{c['baumol']:.2f}" if c["baumol"] is not None else "  -- "
        print(f"  {c['id']:<22s} {c['old_sn']:>5.1f} {c['new_sn']:>5.1f} {c['delta']:>+6.1f} "
              f"{c['fa']:>5.1f} {ae_str:>5s} {bm_str:>5s} {c['name'][:38]}")

    # Divergent models
    print(f"\nTop 10 SN↔FA DIVERGENT models:")
    divergent = sorted(changes, key=lambda c: abs(c["new_sn"] - c["fa"]), reverse=True)
    for c in divergent[:10]:
        gap = c["new_sn"] - c["fa"]
        label = "high SN, low FA" if gap > 0 else "low SN, high FA"
        print(f"  {c['id']:<22s} SN={c['new_sn']:>4.1f} FA={c['fa']:>4.1f} gap={gap:>+5.1f}  ({label})")

    # Architecture averages
    print(f"\nNew SN by architecture (avg, n>=5):")
    arch_groups = {}
    for c in changes:
        arch_groups.setdefault(c["arch"], []).append(c["new_sn"])
    for a, scores in sorted(arch_groups.items(), key=lambda x: -statistics.mean(x[1])):
        if len(scores) >= 5:
            avg_fa = statistics.mean([c["fa"] for c in changes if c["arch"] == a])
            print(f"  {a:<30s} n={len(scores):>3d} avg_SN={statistics.mean(scores):.1f} avg_FA={avg_fa:.1f}")

    # Correlation check
    print(f"\n{'='*70}")
    print(f"CORRELATION CHECK")
    print(f"{'='*70}")
    print(f"  SN ↔ FA:  {new_r:.3f}  (was {old_r:.3f}, target < 0.35)")
    ec_scores = [m["scores"]["EC"] for m in models]
    tg_scores = [m["scores"]["TG"] for m in models]
    ce_scores = [m["scores"]["CE"] for m in models]
    print(f"  SN ↔ EC:  {pearson_r(new_sn_scores, ec_scores):.3f}")
    print(f"  SN ↔ TG:  {pearson_r(new_sn_scores, tg_scores):.3f}")
    print(f"  SN ↔ CE:  {pearson_r(new_sn_scores, ce_scores):.3f}")

    # Validation gate
    if new_r >= 0.35:
        print(f"\n⚠ VALIDATION FAILED: SN↔FA r={new_r:.3f} >= 0.35 threshold")
        if apply_mode:
            print("  ABORTING apply mode.")
            return

    if max_bucket_pct > 30:
        print(f"\n⚠ WARNING: Dominant bucket at {max_bucket_pct:.1f}%")

    # ── Apply ──
    if apply_mode:
        print(f"\n{'='*70}")
        print("APPLYING CHANGES")
        print(f"{'='*70}")

        for m, new_sn in zip(models, new_sn_scores):
            m["scores"]["SN"] = new_sn

            # Recompute T composite
            s = m["scores"]
            m["composite"] = round(
                (s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2
            )

            # Reclassify categories
            m["category"] = classify_model(s, m.get("forces_v3", []))
            m["primary_category"] = m["category"][0]

        # Re-rank all three dimensions
        models.sort(key=lambda m: (-m["composite"], m["id"]))
        for i, m in enumerate(models, 1):
            m["rank"] = i

        models_by_opp = sorted(models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
        for i, m in enumerate(models_by_opp, 1):
            m["opportunity_rank"] = i

        models_by_vcr = sorted(models, key=lambda m: (-m.get("vcr", {}).get("composite", 0), m["id"]))
        for i, m in enumerate(models_by_vcr, 1):
            m["vcr_rank"] = i

        models.sort(key=lambda m: (-m["composite"], m["id"]))
        data["summary"]["total_models"] = len(models)

        print(f"Writing {len(models)} models...")
        with open(NORMALIZED_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Written: {NORMALIZED_FILE}")

        # Post-apply stats
        final_sn = [m["scores"]["SN"] for m in models]
        final_fa = [m["scores"]["FA"] for m in models]
        final_r = pearson_r(final_sn, final_fa)
        cat_dist = Counter(m["primary_category"] for m in models)
        t_comps = [m["composite"] for m in models]

        print(f"\nFinal state:")
        print(f"  SN↔FA r={final_r:.3f}")
        print(f"  T-composite: mean={statistics.mean(t_comps):.1f}, median={statistics.median(t_comps):.1f}")
        print(f"  Category distribution:")
        for cat, count in cat_dist.most_common():
            print(f"    {cat:<22s} {count:>4d}")
    else:
        print(f"\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
