#!/usr/bin/env python3
"""
v3-14 Score Correction: Fix redundancy issues identified in methodology review.

Fixes:
  1. CLA MO/MA differentiation — decouple adjustments
  2. CLA VD discrimination — add sector-specific value chain depth
  3. VCR CAP/VEL partial decoupling — add independent modifiers
  4. Batch normalization — correct deep-dive inflation

Only modifies HEURISTIC-scored models (those without manual overrides).
Preserves all manual override scores.

Run modes:
  --analyze: Show before/after without writing (default)
  --apply: Apply corrections and write to normalized file
"""

import json
import sys
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

# ── CLA Manual Override IDs (do not touch these) ──
# Load from cla_scoring.py MANUAL_CLA dict
# We detect manual overrides by checking if rationale does NOT start with "Heuristic:"
# and does NOT contain "Fundamental" (VCR heuristic markers)

# ── CLA VD: Sector Value Chain Depth ──
# How many independent layers exist in the sector's value chain?
# More layers = more entry points = higher VD
SECTOR_VD_ADJUSTMENT = {
    "11": -1,  # Agriculture: few layers (grow → process → distribute)
    "21": -1,  # Mining: few layers (extract → process → ship)
    "22": 0,   # Utilities: moderate (generation → transmission → distribution → retail)
    "23": 1,   # Construction: many layers (design → materials → labor → inspect → maintain)
    "31": 1,   # Manufacturing: many layers (design → source → produce → QA → distribute)
    "32": 1,   # Manufacturing
    "33": 1,   # Manufacturing
    "42": 0,   # Wholesale: moderate
    "44": 1,   # Retail: many layers (sourcing → merchandising → logistics → POS → returns)
    "45": 1,   # Retail
    "48": 0,   # Transportation: moderate
    "49": 1,   # Warehousing: moderate-high (receive → store → pick → pack → ship)
    "51": 1,   # Information: many layers (create → process → distribute → monetize)
    "52": 2,   # Finance: very deep (origination → underwrite → service → secondary → compliance)
    "53": 1,   # Real Estate: many (source → evaluate → transact → manage → maintain)
    "54": 0,   # Professional Services: moderate (acquire client → deliver → bill)
    "55": 0,   # Management
    "56": -1,  # Admin: shallow (staff → place → manage)
    "61": 0,   # Education: moderate
    "62": 1,   # Healthcare: deep (triage → diagnose → treat → bill → follow-up)
    "71": 0,   # Arts: moderate
    "72": 0,   # Accommodation/Food: moderate
    "81": -1,  # Other Services: shallow
    "92": 0,   # Government: moderate
}

# ── CLA MO/MA Differentiation ──
# MO focuses on market structure (fragmentation, incumbent count)
# MA focuses on execution barriers (capital, regulation, technical complexity)
# Currently they move together. We differentiate by:
# - High-capital sectors: MA lower (harder to execute) even if MO is open
# - Fragmented sectors: MO higher (market open) even if MA is moderate
SECTOR_MO_MA_DIFF = {
    # (MO_adj, MA_adj) — DIFFERENTIAL adjustment to SEPARATE the axes
    # MO = market structure openness; MA = incumbent moat fragility
    # Key principle: adjust in OPPOSITE directions to reduce r=0.77
    "21": (1, -2),   # Mining: fragmented operators (MO+) but massive capital moats (MA--)
    "22": (0, -2),   # Utilities: regulated market, extreme capital moats (MA--)
    "23": (2, -1),   # Construction: extremely fragmented (MO++) but unionized/licensed (MA-)
    "42": (1, -1),   # Wholesale: fragmented (MO+) but relationship-locked (MA-)
    "48": (1, -2),   # Transportation: fragmented operators (MO+) but fleet capital moats (MA--)
    "52": (-2, 1),   # Finance: concentrated (MO--) but regulation creates moat fragility (MA+)
    "53": (2, -1),   # Real Estate: very fragmented (MO++) but relationship moats (MA-)
    "61": (-1, 1),   # Education: consolidated (MO-) but accreditation moats are cracking (MA+)
    "62": (-2, 0),   # Healthcare: highly concentrated systems (MO--)
    "72": (2, 0),    # Accommodation/Food: extremely fragmented (MO++)
    "81": (2, -1),   # Other Services: very fragmented (MO++) but franchise moats (MA-)
    "92": (-2, -1),  # Government: procurement concentrated AND moats strong
}

# Architecture-level MA differentiation (moat fragility varies by business model)
ARCH_MA_ADJUSTMENT = {
    # Architecture types where moats are MORE fragile (disruptable)
    "vertical_saas": 1,         # SaaS moats are moderate, switchable
    "ai_copilot": 1,            # Copilots compete on quality, not lock-in
    "arbitrage_window": 2,      # By definition, moats don't exist yet
    # Architecture types where moats are STRONGER (less fragile)
    "data_compounding": -1,     # Data moats compound over time
    "platform_infrastructure": -1,  # Platform lock-in is real
    "hardware_ai": -2,          # Hardware + capital moats are very strong
    "robotics_automation": -1,  # Physical deployment moats
    "regulatory_moat_builder": -2,  # Regulatory moats are by design
}

# ── VCR CAP/VEL Decoupling ──
# CAP additional modifier: sector fragmentation (independent of buyer-type)
# VEL additional modifier: sales cycle length (independent of buyer-type)
# ── VCR CAP/VEL Decoupling ──
# Problem: both driven by same arch→buyer-type mapping (r=0.78)
# Fix: adjust in OPPOSITE directions by architecture
# CAP = "can a startup capture market share?" → fragmentation matters
# VEL = "how fast from $0 to $5M ARR?" → sales cycle length matters
# Key: some archs have high CAP but low VEL (fragmented markets, slow sales)
#      others have low CAP but high VEL (concentrated markets, large deals)
ARCH_CAP_VEL_DECOUPLE = {
    # (CAP_adj, VEL_adj) — OPPOSITE directions to reduce r=0.78
    "acquire_and_modernize": (2, -2),   # Easy to buy businesses, slow to integrate revenue
    "rollup_consolidation": (2, -2),    # Same — acquisition is capture, but integration is slow
    "platform_infrastructure": (-1, 1), # Hard to capture (platform competition) but fast velocity once adopted
    "marketplace_network": (-1, 2),     # Hard to build supply/demand, but network effects create fast growth
    "vertical_saas": (0, 1),            # Moderate capture, fast SMB velocity
    "robotics_automation": (1, -2),     # Can capture physical niches, very slow deployment revenue
    "hardware_ai": (1, -3),             # Can capture with better hardware, extremely slow sales cycle
    "physical_production_ai": (1, -2),  # Can capture factory floor, slow implementation
    "data_compounding": (-1, 1),        # Hard to get initial data, but compounds fast once flowing
    "compliance_automation": (0, -1),   # Moderate capture, compliance sales cycles are long
    "regulatory_moat_builder": (-1, -1), # Hard to capture, slow regulatory sales
}

# ── VCR ECO/MOA Decoupling ──
# Problem: r=0.693, MOA only 19 unique values (architecture template dominates)
# ECO = unit economics quality (margins, LTV/CAC, scalability)
# MOA = moat trajectory (will competitive advantage grow or erode?)
# Fix: add sector + architecture differential adjustments in OPPOSITE directions
SECTOR_ECO_MOA_DIFF = {
    # (ECO_adj, MOA_adj) — OPPOSITE directions where conceptually justified
    "21": (0, 1),     # Mining: neutral economics, but high switching costs for embedded systems
    "23": (0, -1),    # Construction: neutral economics, weak moats (project-based)
    "31": (-1, 1),    # Manufacturing: heavy capex hurts economics, but physical deployment = lock-in
    "32": (-1, 1),
    "33": (-1, 1),
    "44": (1, -1),    # Retail: SaaS can have good economics, but consumer moats are weak
    "45": (1, -1),
    "48": (-1, 1),    # Transportation: fleet costs hurt economics, but integration lock-in = moat
    "51": (1, -1),    # Information: digital margins great, but moats erode quickly (tech shifts)
    "54": (1, -1),    # Professional Services: good margins, weak lock-in
    "62": (-1, 1),    # Healthcare: billing complexity hurts economics, but regulatory moat strong
    "72": (1, -1),    # Accommodation/Food: good per-location unit economics, but weak moat
    "92": (-1, 2),    # Government: procurement kills economics, but once in = massive lock-in
}
ARCH_ECO_MOA_DIFF = {
    # Architecture types where economics and moat should diverge
    "acquire_and_modernize": (-1, 1),   # Integration costs hurt ECO, but acquired assets = moat
    "rollup_consolidation": (-1, 1),    # Same — consolidation costs vs asset moat
    "arbitrage_window": (1, -2),        # Quick returns but NO lasting moat (by definition)
    "regulatory_moat_builder": (-1, 1), # Compliance is expensive but moat grows
    "marketplace_network": (0, 1),      # Network effects create strong moat
    "service_platform": (0, -1),        # Services are hard to differentiate
    "hardware_ai": (-1, 1),             # Hardware costs hurt ECO, physical deployment = moat
    "physical_production_ai": (-1, 1),  # Same
}

# ── Batch Normalization ──
# Correction factors based on mean T-composite deviation from overall mean (67.30)
# Only apply to non-manual-override models
BATCH_CORRECTIONS = {
    # batch_prefix: (SN_adj, FA_adj, EC_adj, TG_adj, CE_adj)
    # v3-2_cycle already corrected (-1.5, -1.5, 0, -2.5, 0) — skip
    # Deep dive batches systematically score higher
    "v36_deep_dive": (-1.0, -0.5, 0, -0.5, 0),   # +5.65 above mean
    "v37_deep_dive": (-1.0, -0.5, 0, -0.5, 0),   # +5.21 above mean
    # v38 and v3-12 batches are closer to mean, lighter correction
    "v38_deep_dive": (-0.5, 0, 0, -0.5, 0),       # +3.41 above mean
    # v3-9 and v3-10 have the most inflation
    "v39_deep_dive": (-1.0, -1.0, 0, -1.0, 0),   # +7.95 above mean
    "v310_decomposition": (-1.0, -1.0, -0.5, -1.0, -0.5),  # +10.86 above mean
}


def clamp(v, lo=1, hi=10):
    return max(lo, min(hi, round(v, 1)))


def is_manual_cla(model):
    """Check if model has manual CLA override."""
    rationale = model.get("cla", {}).get("rationale", "")
    return rationale and not rationale.startswith("Heuristic:")


def is_manual_vcr(model):
    """Check if model has manual VCR override."""
    rationale = model.get("vcr", {}).get("rationale", "")
    return rationale and not rationale.startswith("Fundamental") and "Heuristic" not in rationale


def apply_cla_corrections(model):
    """Apply CLA MO/MA differentiation and VD discrimination."""
    if is_manual_cla(model):
        return False

    cla = model.get("cla", {})
    scores = cla.get("scores", {})
    if not scores:
        return False

    old_mo, old_ma, old_vd, old_dv = scores["MO"], scores["MA"], scores["VD"], scores["DV"]
    naics = (model.get("sector_naics") or "")[:2]

    # VD adjustment
    vd_adj = SECTOR_VD_ADJUSTMENT.get(naics, 0)
    new_vd = clamp(old_vd + vd_adj)

    # MO/MA differentiation: sector + architecture layers
    mo_adj, ma_adj = SECTOR_MO_MA_DIFF.get(naics, (0, 0))
    arch = model.get("architecture", "")
    arch_ma_adj = ARCH_MA_ADJUSTMENT.get(arch, 0)
    new_mo = clamp(old_mo + mo_adj)
    new_ma = clamp(old_ma + ma_adj + arch_ma_adj)
    new_dv = old_dv  # DV unchanged

    changed = (new_mo != old_mo or new_ma != old_ma or new_vd != old_vd)
    if changed:
        scores["MO"] = new_mo
        scores["MA"] = new_ma
        scores["VD"] = new_vd
        # Recompute composite
        old_comp = cla["composite"]
        cla["composite"] = round((new_mo * 30 + new_ma * 25 + new_vd * 20 + new_dv * 25) / 10, 2)
        # Reclassify
        comp = cla["composite"]
        if comp >= 75:
            cla["category"] = "WIDE_OPEN"
        elif comp >= 60:
            cla["category"] = "ACCESSIBLE"
        elif comp >= 45:
            cla["category"] = "CONTESTED"
        elif comp >= 30:
            cla["category"] = "FORTIFIED"
        else:
            cla["category"] = "LOCKED"

    return changed


def apply_vcr_corrections(model):
    """Apply VCR CAP/VEL partial decoupling via architecture-level differentiation."""
    if is_manual_vcr(model):
        return False

    vcr = model.get("vcr", {})
    scores = vcr.get("scores", {})
    if not scores:
        return False

    old_cap, old_vel = scores["CAP"], scores["VEL"]
    arch = model.get("architecture", "")

    cap_adj, vel_adj = ARCH_CAP_VEL_DECOUPLE.get(arch, (0, 0))

    new_cap = clamp(old_cap + cap_adj)
    new_vel = clamp(old_vel + vel_adj)

    changed = (new_cap != old_cap or new_vel != old_vel)
    if changed:
        scores["CAP"] = new_cap
        scores["VEL"] = new_vel
        # Recompute VCR composite
        vcr["composite"] = round(
            (scores["MKT"] * 25 + new_cap * 25 + scores["ECO"] * 20 +
             new_vel * 15 + scores["MOA"] * 15) / 10, 2)
        # Reclassify
        comp = vcr["composite"]
        if comp >= 75:
            vcr["category"] = "FUND_RETURNER"
        elif comp >= 60:
            vcr["category"] = "STRONG_MULTIPLE"
        elif comp >= 45:
            vcr["category"] = "VIABLE_RETURN"
        elif comp >= 30:
            vcr["category"] = "MARGINAL"
        else:
            vcr["category"] = "VC_POOR"

        # Update ROI estimate (simplified — scale with composite change)
        roi = vcr.get("roi_estimate", {})
        if roi:
            old_comp = (scores["MKT"] * 25 + old_cap * 25 + scores["ECO"] * 20 +
                        old_vel * 15 + scores["MOA"] * 15) / 10
            if old_comp > 0:
                ratio = vcr["composite"] / old_comp
                roi["seed_roi_multiple"] = round(roi["seed_roi_multiple"] * ratio, 1)
                roi["exit_val_M"] = round(roi["exit_val_M"] * ratio, 1)

    return changed


def apply_eco_moa_corrections(model):
    """Apply VCR ECO/MOA decoupling via sector + architecture differentiation."""
    if is_manual_vcr(model):
        return False

    vcr = model.get("vcr", {})
    scores = vcr.get("scores", {})
    if not scores:
        return False

    old_eco, old_moa = scores["ECO"], scores["MOA"]
    naics = (model.get("sector_naics") or "")[:2]
    arch = model.get("architecture", "")

    eco_adj, moa_adj = SECTOR_ECO_MOA_DIFF.get(naics, (0, 0))
    arch_eco_adj, arch_moa_adj = ARCH_ECO_MOA_DIFF.get(arch, (0, 0))

    new_eco = clamp(old_eco + eco_adj + arch_eco_adj)
    new_moa = clamp(old_moa + moa_adj + arch_moa_adj)

    changed = (new_eco != old_eco or new_moa != old_moa)
    if changed:
        scores["ECO"] = new_eco
        scores["MOA"] = new_moa
        # Recompute VCR composite
        vcr["composite"] = round(
            (scores["MKT"] * 25 + scores["CAP"] * 25 + new_eco * 20 +
             scores["VEL"] * 15 + new_moa * 15) / 10, 2)
        # Reclassify
        comp = vcr["composite"]
        if comp >= 75: vcr["category"] = "FUND_RETURNER"
        elif comp >= 60: vcr["category"] = "STRONG_MULTIPLE"
        elif comp >= 45: vcr["category"] = "VIABLE_RETURN"
        elif comp >= 30: vcr["category"] = "MARGINAL"
        else: vcr["category"] = "VC_POOR"

        # Update ROI estimate
        roi = vcr.get("roi_estimate", {})
        if roi:
            old_comp = (scores["MKT"] * 25 + scores["CAP"] * 25 + old_eco * 20 +
                        scores["VEL"] * 15 + old_moa * 15) / 10
            if old_comp > 0:
                ratio = vcr["composite"] / old_comp
                roi["seed_roi_multiple"] = round(roi["seed_roi_multiple"] * ratio, 1)
                roi["exit_val_M"] = round(roi["exit_val_M"] * ratio, 1)

    return changed


def apply_batch_corrections(model):
    """Apply batch normalization to inflated deep-dive batches."""
    batch = model.get("source_batch", "")
    correction = None
    for prefix, corr in BATCH_CORRECTIONS.items():
        if batch.startswith(prefix):
            correction = corr
            break

    if not correction:
        return False

    scores = model.get("scores", {})
    axes = ["SN", "FA", "EC", "TG", "CE"]
    old_scores = {a: scores[a] for a in axes}
    changed = False

    for i, axis in enumerate(axes):
        adj = correction[i]
        if adj != 0:
            new_val = clamp(scores[axis] + adj)
            if new_val != scores[axis]:
                scores[axis] = new_val
                changed = True

    if changed:
        # Recompute T-composite
        model["composite"] = round(
            (scores["SN"] * 25 + scores["FA"] * 25 + scores["EC"] * 20 +
             scores["TG"] * 15 + scores["CE"] * 15) / 10, 2)

    return changed


def main():
    mode = "--apply" if "--apply" in sys.argv else "--analyze"

    print("=" * 70)
    print(f"v3-14 SCORE CORRECTION ({'APPLY' if mode == '--apply' else 'ANALYSIS ONLY'})")
    print("=" * 70)
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # Track changes
    cla_changed = 0
    vcr_changed = 0
    eco_moa_changed = 0
    batch_changed = 0
    cla_category_shifts = Counter()
    vcr_category_shifts = Counter()

    # Store before state for analysis
    before = {}
    for m in models:
        before[m["id"]] = {
            "t_comp": m["composite"],
            "opp_comp": m.get("cla", {}).get("composite"),
            "opp_cat": m.get("cla", {}).get("category"),
            "vcr_comp": m.get("vcr", {}).get("composite"),
            "vcr_cat": m.get("vcr", {}).get("category"),
            "mo": m.get("cla", {}).get("scores", {}).get("MO"),
            "ma": m.get("cla", {}).get("scores", {}).get("MA"),
            "vd": m.get("cla", {}).get("scores", {}).get("VD"),
            "cap": m.get("vcr", {}).get("scores", {}).get("CAP"),
            "vel": m.get("vcr", {}).get("scores", {}).get("VEL"),
            "eco": m.get("vcr", {}).get("scores", {}).get("ECO"),
            "moa": m.get("vcr", {}).get("scores", {}).get("MOA"),
        }

    # Apply corrections
    for m in models:
        if apply_cla_corrections(m):
            cla_changed += 1
            b = before[m["id"]]
            old_cat = b["opp_cat"]
            new_cat = m["cla"]["category"]
            if old_cat != new_cat:
                cla_category_shifts[f"{old_cat} → {new_cat}"] += 1

        if apply_vcr_corrections(m):
            vcr_changed += 1
            b = before[m["id"]]
            old_cat = b["vcr_cat"]
            new_cat = m["vcr"]["category"]
            if old_cat != new_cat:
                vcr_category_shifts[f"{old_cat} → {new_cat}"] += 1

        if apply_eco_moa_corrections(m):
            eco_moa_changed += 1

        if apply_batch_corrections(m):
            batch_changed += 1

    # ── Analysis ──
    print(f"\nCLA corrections: {cla_changed} models changed")
    print(f"VCR CAP/VEL corrections: {vcr_changed} models changed")
    print(f"VCR ECO/MOA corrections: {eco_moa_changed} models changed")
    print(f"Batch normalization: {batch_changed} models changed")

    # CLA impact
    if cla_changed:
        opp_deltas = []
        mo_deltas = []
        ma_deltas = []
        vd_deltas = []
        for m in models:
            b = before[m["id"]]
            if b["opp_comp"] and m.get("cla", {}).get("composite"):
                d = m["cla"]["composite"] - b["opp_comp"]
                if d != 0:
                    opp_deltas.append(d)
            if b["mo"] and m.get("cla", {}).get("scores", {}).get("MO"):
                mo_deltas.append(m["cla"]["scores"]["MO"] - b["mo"])
            if b["ma"] and m.get("cla", {}).get("scores", {}).get("MA"):
                ma_deltas.append(m["cla"]["scores"]["MA"] - b["ma"])
            if b["vd"] and m.get("cla", {}).get("scores", {}).get("VD"):
                vd_deltas.append(m["cla"]["scores"]["VD"] - b["vd"])

        print(f"\n  OPP composite deltas: mean={statistics.mean(opp_deltas):.2f}, "
              f"range=[{min(opp_deltas):.1f}, {max(opp_deltas):.1f}]") if opp_deltas else None
        print(f"  MO deltas: mean={statistics.mean([d for d in mo_deltas if d!=0]):.2f}") if [d for d in mo_deltas if d!=0] else None
        print(f"  MA deltas: mean={statistics.mean([d for d in ma_deltas if d!=0]):.2f}") if [d for d in ma_deltas if d!=0] else None
        print(f"  VD deltas: mean={statistics.mean([d for d in vd_deltas if d!=0]):.2f}") if [d for d in vd_deltas if d!=0] else None

        print(f"\n  CLA category shifts:")
        for shift, count in sorted(cla_category_shifts.items(), key=lambda x: -x[1]):
            print(f"    {shift}: {count}")

    # VCR impact
    if vcr_changed:
        vcr_deltas = [m["vcr"]["composite"] - before[m["id"]]["vcr_comp"]
                      for m in models if before[m["id"]]["vcr_comp"] and
                      m["vcr"]["composite"] != before[m["id"]]["vcr_comp"]]
        print(f"\n  VCR composite deltas: mean={statistics.mean(vcr_deltas):.2f}, "
              f"range=[{min(vcr_deltas):.1f}, {max(vcr_deltas):.1f}]") if vcr_deltas else None

        print(f"\n  VCR category shifts:")
        for shift, count in sorted(vcr_category_shifts.items(), key=lambda x: -x[1]):
            print(f"    {shift}: {count}")

    # Batch normalization impact
    if batch_changed:
        t_deltas = [m["composite"] - before[m["id"]]["t_comp"]
                    for m in models if m["composite"] != before[m["id"]]["t_comp"]]
        print(f"\n  T-composite deltas: mean={statistics.mean(t_deltas):.2f}, "
              f"range=[{min(t_deltas):.1f}, {max(t_deltas):.1f}]") if t_deltas else None

    # Post-correction correlation check
    print("\n" + "=" * 70)
    print("POST-CORRECTION AXIS CORRELATIONS")
    print("=" * 70)

    mo_scores = [m["cla"]["scores"]["MO"] for m in models]
    ma_scores = [m["cla"]["scores"]["MA"] for m in models]
    vd_scores = [m["cla"]["scores"]["VD"] for m in models]
    cap_scores = [m["vcr"]["scores"]["CAP"] for m in models]
    vel_scores = [m["vcr"]["scores"]["VEL"] for m in models]
    eco_scores = [m["vcr"]["scores"]["ECO"] for m in models]
    moa_scores = [m["vcr"]["scores"]["MOA"] for m in models]

    def pearson_r(x, y):
        n = len(x)
        mx, my = sum(x)/n, sum(y)/n
        cov = sum((xi-mx)*(yi-my) for xi, yi in zip(x, y))
        sx = sum((xi-mx)**2 for xi in x)**0.5
        sy = sum((yi-my)**2 for yi in y)**0.5
        return cov / (sx * sy) if sx * sy > 0 else 0

    r_mo_ma = pearson_r(mo_scores, ma_scores)
    r_cap_vel = pearson_r(cap_scores, vel_scores)
    r_eco_moa = pearson_r(eco_scores, moa_scores)

    vd_unique = len(set(vd_scores))
    vd_mode_pct = max(Counter(vd_scores).values()) / len(vd_scores) * 100
    moa_unique = len(set(moa_scores))

    print(f"  MO ↔ MA correlation:  {r_mo_ma:.3f}  (was 0.774)")
    print(f"  CAP ↔ VEL correlation: {r_cap_vel:.3f}  (was 0.783)")
    print(f"  ECO ↔ MOA correlation: {r_eco_moa:.3f}  (was 0.693)")
    print(f"  VD unique values: {vd_unique}  (was 8)")
    print(f"  VD mode%: {vd_mode_pct:.1f}%  (was 38.8%)")
    print(f"  MOA unique values: {moa_unique}  (was 19)")

    # Overall distribution check
    t_comps = [m["composite"] for m in models]
    opp_comps = [m["cla"]["composite"] for m in models]
    vcr_comps = [m["vcr"]["composite"] for m in models]

    print(f"\n  T-composite: mean={statistics.mean(t_comps):.1f}, median={statistics.median(t_comps):.1f}")
    print(f"  OPP composite: mean={statistics.mean(opp_comps):.1f}, median={statistics.median(opp_comps):.1f}")
    print(f"  VCR composite: mean={statistics.mean(vcr_comps):.1f}, median={statistics.median(vcr_comps):.1f}")

    # Category distributions
    opp_cats = Counter(m["cla"]["category"] for m in models)
    vcr_cats = Counter(m["vcr"]["category"] for m in models)
    print(f"\n  OPP categories: {dict(sorted(opp_cats.items()))}")
    print(f"  VCR categories: {dict(sorted(vcr_cats.items()))}")

    if mode == "--apply":
        # Re-rank
        models.sort(key=lambda m: (-m["composite"], m["id"]))
        for i, m in enumerate(models, 1):
            m["rank"] = i

        models_by_opp = sorted(models, key=lambda m: (-m["cla"]["composite"], m["id"]))
        for i, m in enumerate(models_by_opp, 1):
            m["opportunity_rank"] = i

        models_by_vcr = sorted(models, key=lambda m: (-m["vcr"]["composite"], m["id"]))
        for i, m in enumerate(models_by_vcr, 1):
            m["vcr_rank"] = i

        # Sort back by T for file
        models.sort(key=lambda m: (-m["composite"], m["id"]))

        print(f"\nWriting corrected normalized file...")
        with open(NORMALIZED_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("  Done. Run update_v313_ui.py to regenerate UI.")
    else:
        print(f"\n  [ANALYSIS ONLY — run with --apply to write changes]")


if __name__ == "__main__":
    main()
