#!/usr/bin/env python3
"""
v3-15 SN Axis Redefinition: "Structural Necessity" → "Market Necessity"

Redefines SN from "do structural forces guarantee demand?" (which overlaps with FA)
to "does this specific model address a gap that alternatives can't fill?"

This decorrelates SN from FA because the new inputs are:
  1. Architecture substitutability (can another arch serve the same need?)
  2. Competitive density (how many models target the same sector?)
  3. Incumbent adaptation inversion (can incumbents just add AI?)
  4. Market concentration necessity (CLA MO inversion — concentrated markets need fewer solutions)

None of these depend on force count or velocity (FA's domain).

Target: r(SN, FA) < 0.35 (was 0.692)
"""

import json
import sys
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

def clamp(v, lo=1.0, hi=10.0):
    return max(lo, min(hi, round(v, 1)))


# ── Component 1: Architecture Substitutability (inverted → uniqueness) ──
# Scale: how easily can ANOTHER architecture serve the same transformation need?
# 10 = highly substitutable (any arch works), 1 = irreplaceable (only this arch can do it)
ARCH_SUBSTITUTABILITY = {
    "full_service_replacement": 3,     # Replaces entire function — hard to substitute
    "vertical_saas": 7,                # Other SaaS or consulting can partially substitute
    "platform_infrastructure": 4,      # Platforms hard to replicate but APIs compete
    "data_compounding": 2,             # Data moat is unique, hard to substitute
    "marketplace_network": 5,          # Other distribution models could work
    "acquire_and_modernize": 1,        # Rollup execution is unique playbook, needs capital
    "rollup_consolidation": 1,         # Same — consolidation requires specific arch
    "service_platform": 8,             # Many ways to deliver managed services
    "regulatory_moat_builder": 3,      # Regulatory position is unique
    "physical_production_ai": 3,       # Physical deployment creates lock-in
    "hardware_ai": 3,                  # Hardware specialization
    "robotics_automation": 1,          # Physical automation irreplaceable by software
    "ai_copilot": 9,                   # Many AI copilots compete on features
    "compliance_automation": 6,        # Moderate — GRC tools overlap
    "arbitrage_window": 9,             # Time-limited, anyone can walk through the window
}

# ── Component 3: Incumbent Adaptation Risk ──
# How likely are incumbents to successfully add AI to their existing offering?
# High = incumbents WILL adapt (bad for entrants), Low = incumbents CAN'T adapt (good for entrants)
INCUMBENT_ADAPTATION_RISK = {
    "11": 2,   # Agriculture: fragmented, barely uses email
    "21": 3,   # Mining: legacy SCADA, slow IT adoption
    "22": 4,   # Utilities: GE/Siemens will try but regulated pace
    "23": 2,   # Construction: lowest digital maturity of any sector
    "31": 4,   # Manufacturing (food): mid-tier adaptation
    "32": 4,   # Manufacturing (chemical/plastics)
    "33": 5,   # Manufacturing (machinery/electronics): some adapt
    "42": 4,   # Wholesale: slow ERP-heavy incumbents
    "44": 6,   # Retail: Amazon adapts but mid-market doesn't
    "45": 5,   # Retail (misc): moderate
    "48": 5,   # Transportation: fleet mgmt vendors adapting
    "49": 4,   # Warehousing: automation vendors exist but slow
    "51": 9,   # Information: Big Tech adapts FAST
    "52": 7,   # Finance: JPM, Goldman building in-house AI
    "53": 4,   # Real estate: PropTech growing but fragmented
    "54": 6,   # Professional services: Big 4/consulting building AI
    "55": 6,   # Management: PE firms building in-house
    "56": 3,   # Admin/support: low-tech, can't adapt
    "61": 5,   # Education: EdTech growing, universities slow
    "62": 5,   # Healthcare: Epic/Cerner adapting BUT slowly
    "71": 4,   # Arts/entertainment: mixed tech maturity
    "72": 3,   # Accommodation/food: low-tech, high turnover
    "81": 2,   # Other services: very fragmented, zero AI capacity
    "92": 3,   # Government: procurement lock-in prevents adaptation
}


def compute_new_sn(model, sector_model_counts):
    """Compute new SN based on market necessity (not force strength)."""
    arch = model.get("architecture", "vertical_saas")
    naics2 = (model.get("sector_naics") or "")[:2]

    # Component 1: Architecture uniqueness (40%)
    # Inverse of substitutability — unique architectures are more necessary
    sub = ARCH_SUBSTITUTABILITY.get(arch, 5)
    arch_uniqueness = 11 - sub  # 3→8, 8→3, etc.

    # Component 2: Competitive density penalty (25%)
    # How many models target the same 2-digit NAICS sector?
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

    # Component 3: Incumbent adaptation inversion (20%)
    # If incumbents CAN'T adapt → this model is MORE necessary
    adaptation_risk = INCUMBENT_ADAPTATION_RISK.get(naics2, 5)
    adaptation_necessity = 11 - adaptation_risk  # Low risk for incumbents = high necessity for this model

    # Component 4: Market concentration necessity (15%)
    # In concentrated markets (low CLA MO), the few viable solutions are MORE necessary
    # In fragmented markets (high MO), any specific model is LESS necessary
    mo = model.get("cla", {}).get("scores", {}).get("MO", 5)
    market_necessity = 11 - mo  # Invert: concentrated = more necessary

    # Weighted blend
    raw_sn = (
        arch_uniqueness * 0.40
        + density_score * 0.25
        + adaptation_necessity * 0.20
        + market_necessity * 0.15
    )

    # Spread the distribution: amplify deviations from center
    # Without this, 4-component blend compresses toward mean ~5.5
    center = 5.8
    spread = 1.4  # amplification factor
    new_sn = center + (raw_sn - center) * spread

    # Architecture-specific adjustments for edge cases
    if arch == "arbitrage_window":
        # Arbitrage windows are NOT necessary — they're opportunistic
        new_sn -= 0.8

    # Sub-model adjustment: sub-models that focus on software layers
    # within FORTIFIED parents are more necessary (they're the accessible wedge)
    if model.get("parent_id"):
        layer = (model.get("layer_name") or "").lower()
        if "software" in layer or "data" in layer or "analytics" in layer:
            new_sn += 0.5  # Software layers within hard sectors = more necessary
        elif "physical" in layer or "hardware" in layer:
            new_sn -= 0.3  # Physical layers are less uniquely necessary

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
    print("v3-15 SN AXIS REDEFINITION: 'Market Necessity'")
    print("=" * 70)
    print(f"Mode: {'APPLY (writing changes)' if apply_mode else 'ANALYZE (read-only)'}")
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # Compute sector density
    sector_counts = Counter((m.get("sector_naics") or "")[:2] for m in models)
    print(f"Sectors: {len(sector_counts)} unique 2-digit NAICS")

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
        new_sn = compute_new_sn(m, sector_counts)
        old = m["scores"]["SN"]
        new_sn_scores.append(new_sn)
        changes.append({
            "id": m["id"],
            "name": m["name"],
            "old_sn": old,
            "new_sn": new_sn,
            "delta": new_sn - old,
            "fa": m["scores"]["FA"],
            "arch": m.get("architecture", ""),
            "naics2": (m.get("sector_naics") or "")[:2],
        })

    # ── After analysis ──
    new_r = pearson_r(new_sn_scores, fa_scores)
    new_mean = statistics.mean(new_sn_scores)
    new_stdev = statistics.stdev(new_sn_scores)
    new_min = min(new_sn_scores)
    new_max = max(new_sn_scores)

    # Bucket distribution
    buckets = Counter(round(s) for s in new_sn_scores)
    max_bucket_pct = max(buckets.values()) / len(new_sn_scores) * 100

    # New STRUCTURAL_WINNER count
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

    # Top movers
    changes.sort(key=lambda c: abs(c["delta"]), reverse=True)
    print(f"\nTop 15 largest SN changes:")
    print(f"  {'ID':<22s} {'Old':>5s} {'New':>5s} {'Δ':>6s} {'FA':>5s} {'Arch':<28s} Name")
    print("  " + "-" * 100)
    for c in changes[:15]:
        print(f"  {c['id']:<22s} {c['old_sn']:>5.1f} {c['new_sn']:>5.1f} {c['delta']:>+6.1f} "
              f"{c['fa']:>5.1f} {c['arch']:<28s} {c['name'][:40]}")

    # Divergent models (new SN high, FA low or vice versa)
    print(f"\nTop 10 SN↔FA DIVERGENT models (decorrelation evidence):")
    divergent = sorted(changes, key=lambda c: abs(c["new_sn"] - c["fa"]), reverse=True)
    for c in divergent[:10]:
        gap = c["new_sn"] - c["fa"]
        label = "high SN, low FA" if gap > 0 else "low SN, high FA"
        print(f"  {c['id']:<22s} SN={c['new_sn']:>4.1f} FA={c['fa']:>4.1f} gap={gap:>+5.1f}  ({label})  {c['name'][:40]}")

    # Architecture averages
    print(f"\nNew SN by architecture (avg):")
    arch_groups = {}
    for c in changes:
        arch_groups.setdefault(c["arch"], []).append(c["new_sn"])
    for a, scores in sorted(arch_groups.items(), key=lambda x: -statistics.mean(x[1])):
        if len(scores) >= 5:
            avg_fa = statistics.mean([c["fa"] for c in changes if c["arch"] == a])
            print(f"  {a:<30s} n={len(scores):>3d} avg_SN={statistics.mean(scores):.1f} avg_FA={avg_fa:.1f} gap={statistics.mean(scores)-avg_fa:>+5.1f}")

    # Cross-system correlation check
    print(f"\n{'='*70}")
    print(f"CORRELATION CHECK")
    print(f"{'='*70}")
    print(f"  SN ↔ FA:  {new_r:.3f}  (was {old_r:.3f}, target < 0.35)")

    # Also check SN vs other T axes
    ec_scores = [m["scores"]["EC"] for m in models]
    tg_scores = [m["scores"]["TG"] for m in models]
    ce_scores = [m["scores"]["CE"] for m in models]
    print(f"  SN ↔ EC:  {pearson_r(new_sn_scores, ec_scores):.3f}")
    print(f"  SN ↔ TG:  {pearson_r(new_sn_scores, tg_scores):.3f}")
    print(f"  SN ↔ CE:  {pearson_r(new_sn_scores, ce_scores):.3f}")

    # Validation gate
    if new_r >= 0.35:
        print(f"\n⚠ VALIDATION FAILED: SN↔FA r={new_r:.3f} >= 0.35 threshold")
        print("  Adjustments needed before --apply can proceed.")
        if apply_mode:
            print("  ABORTING apply mode.")
            return

    if max_bucket_pct > 30:
        print(f"\n⚠ WARNING: Dominant bucket at {max_bucket_pct:.1f}% — distribution may be too clustered")

    # ── Apply ──
    if apply_mode:
        print(f"\n{'='*70}")
        print("APPLYING CHANGES")
        print(f"{'='*70}")

        for m, new_sn in zip(models, new_sn_scores):
            old_sn_val = m["scores"]["SN"]
            m["scores"]["SN"] = new_sn

            # Recompute T composite
            s = m["scores"]
            m["composite"] = round(
                (s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2
            )

            # Reclassify categories
            m["category"] = classify_model(s, m.get("forces_v3", []))
            m["primary_category"] = m["category"][0]

        # Re-rank by T composite
        models.sort(key=lambda m: (-m["composite"], m["id"]))
        for i, m in enumerate(models, 1):
            m["rank"] = i

        # Opportunity and VCR ranks stay the same (CLA/VCR scores unchanged)
        models_by_opp = sorted(models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
        for i, m in enumerate(models_by_opp, 1):
            m["opportunity_rank"] = i

        models_by_vcr = sorted(models, key=lambda m: (-m.get("vcr", {}).get("composite", 0), m["id"]))
        for i, m in enumerate(models_by_vcr, 1):
            m["vcr_rank"] = i

        # Sort by T for file
        models.sort(key=lambda m: (-m["composite"], m["id"]))

        # Update summary
        data["summary"]["total_models"] = len(models)

        # Write
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
