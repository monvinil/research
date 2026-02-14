#!/usr/bin/env python3
"""
v5.4 "Calibration Pass"

Applies comprehensive overscoring and underscoring corrections identified
by the structural audit + 2026 evidence review.

8 Fix Categories:
  OVERSCORING:
  1. FSR_CLA_RECALIBRATION:   Reduce full_service_replacement heuristic CLA
                               (gap +20.7pt vs manual overrides, 127 models)
  2. SECTOR_CLA_DEFLATION:    Reduce inflated CLA in Real Estate, Education,
                               Other Services, Wholesale (sector-level gaps)

  UNDERSCORING (2026 evidence):
  3. EDUCATION_T_BOOST:       SN +1.0, FA +0.5, EC +0.5  (~+5pts, 24 models)
                               Enrollment cliff Fall 2025, 80+ closures, $10B/yr
  4. GOVERNMENT_T_BOOST:      SN +1.0, EC +1.0, TG +0.5  (~+5pts, 16 models)
                               82% CIO adoption, Pentagon AI, $50B IT/quarter
  5. RETAIL_OPP_BOOST:        MO +0.5, MA +0.5, DV +1.0  (~+5pts, 23 models)
                               46.5% CAGR, 87-94% adoption, AI-commerce vectors
  6. MINING_T_BOOST:          SN +1.0, TG +0.5, CE +0.5  (~+4pts, 13 models)
                               BHP/Rio Tinto autonomous ops at production scale
  7. AGRICULTURE_OPP_BOOST:   MO +1.0, MA +0.5, DV +1.0  (~+7pts, 15 models)
                               71% precision ag funding jump, John Deere autonomy
  8. TRANSPORTATION_TG_BOOST: TG +1.5                     (~+2pts, 25 models)
                               Aurora commercial revenue, 1000+ delivery robots

  NEW MODELS:
  9. ARTS_ENTERTAINMENT:      3-4 new models for AI content generation, gaming,
                               live entertainment (major coverage gap, NAICS 71)

Input:  data/v4/models.json (793 models)
Output: data/v4/models.json (updated — rescored + new models)
        data/v5/calibration_report.json (detailed change log)
"""

import json
import math
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"

MODELS_FILE = V4_DIR / "models.json"
NARRATIVES_FILE = V4_DIR / "narratives.json"
STATE_FILE = V5_DIR / "state.json"
REPORT_FILE = V5_DIR / "calibration_report.json"

T_WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}
CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}
VCR_WEIGHTS = {"MKT": 25, "CAP": 25, "ECO": 20, "VEL": 15, "MOA": 15}


def t_category(composite):
    if composite >= 80: return "DEFINING"
    if composite >= 65: return "MAJOR"
    if composite >= 50: return "MODERATE"
    if composite >= 35: return "EMERGING"
    return "SPECULATIVE"

def cla_category(composite):
    if composite >= 75: return "WIDE_OPEN"
    if composite >= 60: return "ACCESSIBLE"
    if composite >= 45: return "CONTESTED"
    if composite >= 30: return "FORTIFIED"
    return "LOCKED"

def vcr_category(composite):
    if composite >= 75: return "FUND_RETURNER"
    if composite >= 60: return "STRONG_MULTIPLE"
    if composite >= 45: return "VIABLE_RETURN"
    if composite >= 30: return "MARGINAL"
    return "VC_POOR"


def compute_t(scores):
    return sum(scores[a] * T_WEIGHTS[a] for a in T_WEIGHTS) / 10.0

def compute_cla(scores):
    return sum(scores[a] * CLA_WEIGHTS[a] for a in CLA_WEIGHTS) / 10.0

def compute_vcr(scores):
    return sum(scores[a] * VCR_WEIGHTS[a] for a in VCR_WEIGHTS) / 10.0

def geo_mean(t, o, v):
    return (t * o * v) ** (1.0 / 3.0)

def clamp(val, lo=1.0, hi=10.0):
    return max(lo, min(hi, val))

def get_naics2(model):
    sn = str(model.get("sector_naics", ""))
    return sn[:2] if len(sn) >= 2 else sn

def is_heuristic(model):
    """Check if model has heuristic-scored CLA (not manual override)."""
    rationale = model.get("cla", {}).get("rationale", "")
    return rationale.startswith("Heuristic")


# ══════════════════════════════════════════════════════════════════════
# UPDATED CLA DEFAULTS for full_service_replacement
# ══════════════════════════════════════════════════════════════════════
# Old: (6, 6, 6, 7) → base CLA = 63.5 — way too generous
# Manual override average: 42.8 — shows FSR is much harder than assumed
# New: (4, 4, 5, 5) → base CLA = 44.5 — aligned with manual evidence
#
# Rationale per axis:
#   MO: 6→4 — FSR faces client lock-in, relationship-based sales, trust barriers
#   MA: 6→4 — incumbent moats are STRONG (domain expertise, client relationships, data)
#   VD: 6→5 — value chain depth is real but entry points are gated by trust
#   DV: 7→5 — disruption vectors exist but implementation requires deep domain work
FSR_NEW_DEFAULTS = (4, 4, 5, 5)  # base CLA = 44.5

# Sector adjustments that are too generous for CLA
# These compound with FSR defaults to create the massive gaps
SECTOR_CLA_DEFLATION = {
    # Real Estate: gap +22.2. Currently (1,0,0,1) — remove MO bonus, keep DV
    "53": {"old": (1, 0, 0, 1), "new": (0, 0, 0, 1)},
    # Education: gap +21.5. Currently (1,1,0,0) — remove both
    "61": {"old": (1, 1, 0, 0), "new": (0, 0, 0, 0)},
    # Other Services: gap +15.7. Currently (1,1,0,0) — remove both
    "81": {"old": (1, 1, 0, 0), "new": (0, 0, 0, 0)},
    # Wholesale: gap +14.6. Currently (1,1,0,1) — reduce to neutral
    "42": {"old": (1, 1, 0, 1), "new": (0, 0, 0, 0)},
}


# ══════════════════════════════════════════════════════════════════════
# SECTOR BOOSTING RULES (2026 evidence)
# ══════════════════════════════════════════════════════════════════════

def apply_calibration(model):
    """Apply all calibration rules. Returns list of adjustments."""
    adjustments = []
    arch = model.get("architecture", "")
    naics = str(model.get("sector_naics", ""))
    naics2 = get_naics2(model)
    t_scores = model["scores"]
    cla_scores = model["cla"]["scores"]
    vcr_scores = model["vcr"]["scores"]
    mid = model.get("id", "")

    # ── Fix 1: FSR CLA Recalibration ──
    # Only for heuristic-scored models with full_service_replacement architecture
    if arch == "full_service_replacement" and is_heuristic(model):
        old_mo = cla_scores["MO"]
        old_ma = cla_scores["MA"]
        old_vd = cla_scores["VD"]
        old_dv = cla_scores["DV"]
        old_comp = model["cla"]["composite"]

        # Recalculate from new FSR defaults + existing sector/category logic
        mo, ma, vd, dv = FSR_NEW_DEFAULTS

        # Apply sector adjustment (use current SECTOR_ADJUSTMENTS, not old)
        # Note: some sectors also got deflated (Fix 2), use NEW values
        sector_adj = _get_sector_adj(naics2)
        mo += sector_adj[0]
        ma += sector_adj[1]
        vd += sector_adj[2]
        dv += sector_adj[3]

        # Defense penalty
        if any(mid.startswith(p) for p in ("V3-DEF-", "MC-DEF-")):
            mo -= 2
            ma -= 2

        # Category adjustment
        primary_cat = model.get("primary_category", "")
        cat_adj = _get_category_adj(primary_cat)
        mo += cat_adj[0]
        ma += cat_adj[1]
        vd += cat_adj[2]
        dv += cat_adj[3]

        # Multi-category bonus
        cats = model.get("category", [])
        if isinstance(cats, list):
            for cat in cats:
                if cat == "FEAR_ECONOMY" and primary_cat != "FEAR_ECONOMY":
                    mo += 1; dv += 1
                if cat == "EMERGING_CATEGORY" and primary_cat != "EMERGING_CATEGORY":
                    mo += 1

        # Competitive density
        cd = model.get("competitive_density", {})
        if isinstance(cd, dict):
            status = cd.get("status", "")
            if status == "zero": mo += 2; ma += 2
            elif status == "low": mo += 1; ma += 1
            elif status == "crowded": mo -= 2; dv -= 1

        # Platform oligopoly penalty (from v5.3) — inline check
        PLATFORM_OLIGOPOLY = {
            "saas_in_info": {
                "archs": {"vertical_saas", "ai_copilot", "data_compounding"},
                "naics_prefixes": {"51", "5112", "5415"},
                "penalty": (-1, -1),
            },
            "saas_in_insurance": {
                "archs": {"vertical_saas"},
                "naics_prefixes": {"5242", "5241"},
                "penalty": (-2, -1),
            },
            "saas_in_healthcare": {
                "archs": {"vertical_saas", "compliance_automation"},
                "naics_prefixes": {"62", "6211", "6221"},
                "penalty": (-1, 0),
            },
            "saas_in_telecom": {
                "archs": {"vertical_saas", "platform_infrastructure"},
                "naics_prefixes": {"517"},
                "penalty": (-2, -1),
            },
        }
        for rule in PLATFORM_OLIGOPOLY.values():
            if arch in rule["archs"]:
                if any(naics.startswith(p) for p in rule["naics_prefixes"]):
                    mo += rule["penalty"][0]
                    ma += rule["penalty"][1]
                    break

        # Keyword analysis (simplified — major signals only)
        one_liner = (model.get("one_liner") or "").lower()
        macro = (model.get("macro_source") or "").lower()
        text = one_liner + " " + macro
        if any(kw in text for kw in ["amazon", "google", "microsoft", "meta", "apple"]):
            mo -= 1
        if any(kw in text for kw in ["monopoly", "dominant", "controls", "dominates"]):
            mo -= 1; ma -= 1
        if any(kw in text for kw in ["fragmented", "highly fragmented", "thousands of"]):
            mo += 1; ma += 1

        # Clamp
        mo = clamp(mo)
        ma = clamp(ma)
        vd = clamp(vd)
        dv = clamp(dv)

        cla_scores["MO"] = mo
        cla_scores["MA"] = ma
        cla_scores["VD"] = vd
        cla_scores["DV"] = dv

        new_comp = compute_cla(cla_scores)
        delta = new_comp - old_comp

        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "FSR_CLA_RECALIBRATION",
                "axis": "CLA.ALL",
                "old_scores": {"MO": old_mo, "MA": old_ma, "VD": old_vd, "DV": old_dv},
                "new_scores": {"MO": mo, "MA": ma, "VD": vd, "DV": dv},
                "delta_composite": round(delta, 2),
                "reason": "FSR arch defaults reduced (6,6,6,7)→(4,4,5,5): "
                          "manual override avg 42.8 vs old heuristic 63.5"
            })

    # ── Fix 2: Sector CLA Deflation (non-FSR heuristic models) ──
    # For non-FSR heuristic models in overscored sectors, apply the deflation delta
    elif is_heuristic(model) and naics2 in SECTOR_CLA_DEFLATION:
        defl = SECTOR_CLA_DEFLATION[naics2]
        old_adj = defl["old"]
        new_adj = defl["new"]
        # Delta: new - old
        d_mo = new_adj[0] - old_adj[0]
        d_ma = new_adj[1] - old_adj[1]
        d_vd = new_adj[2] - old_adj[2]
        d_dv = new_adj[3] - old_adj[3]

        if any(d != 0 for d in [d_mo, d_ma, d_vd, d_dv]):
            old_comp = model["cla"]["composite"]
            cla_scores["MO"] = clamp(cla_scores["MO"] + d_mo)
            cla_scores["MA"] = clamp(cla_scores["MA"] + d_ma)
            cla_scores["VD"] = clamp(cla_scores["VD"] + d_vd)
            cla_scores["DV"] = clamp(cla_scores["DV"] + d_dv)
            new_comp = compute_cla(cla_scores)
            delta = new_comp - old_comp
            if abs(delta) > 0.1:
                adjustments.append({
                    "rule": "SECTOR_CLA_DEFLATION",
                    "axis": "CLA",
                    "sector": naics2,
                    "delta_composite": round(delta, 2),
                    "reason": "Sector {} CLA deflated: adj {} → {}".format(
                        naics2, old_adj, new_adj)
                })

    # ── Fix 3: Education T-Score Boost ──
    # NAICS 61xx — enrollment cliff, 80+ closures, $10B/yr AI investment
    if naics2 == "61":
        old_t = compute_t(t_scores)
        old_sn, old_fa, old_ec = t_scores["SN"], t_scores["FA"], t_scores["EC"]
        t_scores["SN"] = clamp(old_sn + 1.0)
        t_scores["FA"] = clamp(old_fa + 0.5)
        t_scores["EC"] = clamp(old_ec + 0.5)
        new_t = compute_t(t_scores)
        delta = new_t - old_t
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "EDUCATION_T_BOOST",
                "axis": "T.SN/FA/EC",
                "deltas": {"SN": round(t_scores["SN"] - old_sn, 2),
                           "FA": round(t_scores["FA"] - old_fa, 2),
                           "EC": round(t_scores["EC"] - old_ec, 2)},
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: enrollment cliff arrived Fall 2025, "
                          "80+ closures predicted, $10B/yr AI investment"
            })

    # ── Fix 4: Government T-Score Boost ──
    # NAICS 92xx — 82% CIO adoption, Pentagon AI strategy, $50B IT/quarter
    if naics2 == "92":
        old_t = compute_t(t_scores)
        old_sn, old_ec, old_tg = t_scores["SN"], t_scores["EC"], t_scores["TG"]
        t_scores["SN"] = clamp(old_sn + 1.0)
        t_scores["EC"] = clamp(old_ec + 1.0)
        t_scores["TG"] = clamp(old_tg + 0.5)
        new_t = compute_t(t_scores)
        delta = new_t - old_t
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "GOVERNMENT_T_BOOST",
                "axis": "T.SN/EC/TG",
                "deltas": {"SN": round(t_scores["SN"] - old_sn, 2),
                           "EC": round(t_scores["EC"] - old_ec, 2),
                           "TG": round(t_scores["TG"] - old_tg, 2)},
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: 82% gov CIO adopted AI, Pentagon AI "
                          "strategy, $50B federal IT/quarter, FedRAMP acceleration"
            })

    # ── Fix 5: Retail OPP Boost ──
    # NAICS 44xx, 45xx — 46.5% CAGR, 87-94% positive revenue impact
    if naics2 in ("44", "45"):
        old_comp = compute_cla(cla_scores)
        old_mo, old_ma, old_dv = cla_scores["MO"], cla_scores["MA"], cla_scores["DV"]
        cla_scores["MO"] = clamp(old_mo + 0.5)
        cla_scores["MA"] = clamp(old_ma + 0.5)
        cla_scores["DV"] = clamp(old_dv + 1.0)
        new_comp = compute_cla(cla_scores)
        delta = new_comp - old_comp
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "RETAIL_OPP_BOOST",
                "axis": "CLA.MO/MA/DV",
                "deltas": {"MO": round(cla_scores["MO"] - old_mo, 2),
                           "MA": round(cla_scores["MA"] - old_ma, 2),
                           "DV": round(cla_scores["DV"] - old_dv, 2)},
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: AI-retail 46.5% CAGR, 87-94% of "
                          "retailers report positive AI revenue impact"
            })

    # ── Fix 6: Mining T-Score Boost ──
    # NAICS 21xx — BHP/Rio Tinto autonomous ops at production scale
    if naics2 == "21":
        old_t = compute_t(t_scores)
        old_sn, old_tg, old_ce = t_scores["SN"], t_scores["TG"], t_scores["CE"]
        t_scores["SN"] = clamp(old_sn + 1.0)
        t_scores["TG"] = clamp(old_tg + 0.5)
        t_scores["CE"] = clamp(old_ce + 0.5)
        new_t = compute_t(t_scores)
        delta = new_t - old_t
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "MINING_T_BOOST",
                "axis": "T.SN/TG/CE",
                "deltas": {"SN": round(t_scores["SN"] - old_sn, 2),
                           "TG": round(t_scores["TG"] - old_tg, 2),
                           "CE": round(t_scores["CE"] - old_ce, 2)},
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: BHP/Rio Tinto autonomous ops at "
                          "production scale, Caterpillar 600+ autonomous trucks"
            })

    # ── Fix 7: Agriculture OPP Boost ──
    # NAICS 11xx — 71% precision ag funding jump, John Deere autonomy
    if naics2 == "11":
        old_comp = compute_cla(cla_scores)
        old_mo, old_ma, old_dv = cla_scores["MO"], cla_scores["MA"], cla_scores["DV"]
        cla_scores["MO"] = clamp(old_mo + 1.0)
        cla_scores["MA"] = clamp(old_ma + 0.5)
        cla_scores["DV"] = clamp(old_dv + 1.0)
        new_comp = compute_cla(cla_scores)
        delta = new_comp - old_comp
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "AGRICULTURE_OPP_BOOST",
                "axis": "CLA.MO/MA/DV",
                "deltas": {"MO": round(cla_scores["MO"] - old_mo, 2),
                           "MA": round(cla_scores["MA"] - old_ma, 2),
                           "DV": round(cla_scores["DV"] - old_dv, 2)},
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: precision ag VC funding +71%, "
                          "John Deere fully autonomous tractors at scale"
            })

    # ── Fix 8: Transportation TG Boost ──
    # NAICS 48xx, 49xx — Aurora commercial revenue, 1000+ delivery robots
    if naics2 in ("48", "49"):
        old_t = compute_t(t_scores)
        old_tg = t_scores["TG"]
        t_scores["TG"] = clamp(old_tg + 1.5)
        new_t = compute_t(t_scores)
        delta = new_t - old_t
        if abs(delta) > 0.1:
            adjustments.append({
                "rule": "TRANSPORTATION_TG_BOOST",
                "axis": "T.TG",
                "delta_tg": round(t_scores["TG"] - old_tg, 2),
                "delta_composite": round(delta, 2),
                "reason": "2026 evidence: Aurora generating commercial revenue, "
                          "Serve Robotics 1000+ sidewalk robots, Waymo 150K+ "
                          "rides/week"
            })

    return adjustments


# Current sector adjustments (post-deflation)
_SECTOR_ADJS = {
    "33": (0, 0, 0, 0), "34": (-1, -1, 0, 0),
    "54": (1, 0, 0, 1), "62": (-1, 0, 0, 1), "52": (0, -1, 0, 1),
    "61": (0, 0, 0, 0),  # DEFLATED from (1,1,0,0)
    "22": (-1, -1, 0, 0),
    "51": (0, 0, 0, 1),  # v5.3 already reduced
    "53": (0, 0, 0, 1),  # DEFLATED from (1,0,0,1)
    "56": (0, 0, 0, 0),  # v5.3 already reduced
    "42": (0, 0, 0, 0),  # DEFLATED from (1,1,0,1)
    "44": (0, 0, 0, 0), "45": (0, 0, 0, 0),
    "23": (1, 1, 0, 0),
    "81": (0, 0, 0, 0),  # DEFLATED from (1,1,0,0)
    "55": (0, 0, 0, 1),
    "31": (1, 1, 0, 0), "32": (0, 0, 0, 0),
    "48": (0, 0, 0, 0), "21": (-1, -1, 0, 0),
}

_CATEGORY_ADJS = {
    "FEAR_ECONOMY": (1, 1, 0, 1),
    "EMERGING_CATEGORY": (2, 2, 0, 1),
    "STRUCTURAL_WINNER": (0, 0, 0, -1),
    "TIMING_ARBITRAGE": (0, 1, 0, 1),
    "CAPITAL_MOAT": (0, 0, 0, 0),
    "PARKED": (-1, 0, 0, -1),
    "CONDITIONAL": (0, 0, 0, 0),
    "FORCE_RIDER": (0, 0, 0, 0),
}


def _get_sector_adj(naics2):
    return _SECTOR_ADJS.get(naics2, (0, 0, 0, 0))

def _get_category_adj(cat):
    return _CATEGORY_ADJS.get(cat, (0, 0, 0, 0))


# ══════════════════════════════════════════════════════════════════════
# NEW MODELS: Arts/Entertainment (NAICS 71)
# ══════════════════════════════════════════════════════════════════════

NEW_MODELS = [
    {
        "id": "MC-V54-AICONT-001",
        "name": "AI Content Generation Studio Platform",
        "one_liner": "End-to-end AI video/image/audio generation platform for "
                     "studios, agencies, and creators — Runway, Kling, Sora "
                     "democratized for professional workflows",
        "architecture": "open_core_ecosystem",
        "sector_naics": "7115",
        "sector_name": "Independent Artists, Writers, and Performers",
        "scores": {"SN": 9.0, "FA": 8.5, "EC": 8.0, "TG": 9.0, "CE": 7.5},
        "cla": {
            "scores": {"MO": 7, "MA": 8, "VD": 8, "DV": 9},
            "rationale": "Runway $4B valuation, Kling/Sora competing, but market "
                "is expanding not zero-sum. Multi-layer stack: generation, editing, "
                "compositing, distribution. Open-source models (Stable Diffusion, "
                "Flux) provide entry wedge. Professional workflow integration is "
                "the moat. $50B+ creative content TAM being reshaped."
        },
        "vcr": {
            "scores": {"MKT": 9.0, "CAP": 8.0, "ECO": 8.5, "VEL": 8.5, "MOA": 7.0},
            "rationale": "TAM $50B+ (global content creation market). PLG with "
                "freemium, <1 month to revenue. 80%+ software margins. Fast "
                "adoption among creators/agencies. Data moat from usage patterns "
                "but model improvements commoditize quickly."
        },
        "forces_v3": ["F1_technology", "F4_capital", "F5_psychology"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_calibration_evidence",
        "source_batch": "v54_calibration_models",
        "primary_category": "FORCE_RIDER",
        "narrative_ids": ["TN-004"],
        "framework_evidence": {
            "jevons": "AI content tools expand total content production (Jevons "
                      "confirmed: creator economy doubled 2024-2026)",
            "perez": "Revenue-generating immediately, crash-resilient",
            "fear": "Copyright/authenticity fears create demand for trusted "
                    "professional-grade platforms vs raw model access"
        }
    },
    {
        "id": "MC-V54-GAMEA-001",
        "name": "AI-Native Game Development Engine",
        "one_liner": "AI-powered game engine with procedural content generation, "
                     "NPC behavior AI, and real-time asset creation — enabling "
                     "10x faster game development at 1/10th the team size",
        "architecture": "platform_infrastructure",
        "sector_naics": "5112",
        "sector_name": "Software Publishers",
        "scores": {"SN": 8.5, "FA": 7.5, "EC": 7.5, "TG": 8.0, "CE": 7.0},
        "cla": {
            "scores": {"MO": 6, "MA": 7, "VD": 8, "DV": 8},
            "rationale": "Unity + Unreal dominate but AI-native engines are new "
                "category. Multi-layer opportunity: asset generation, NPC AI, "
                "procedural worlds, testing. Indie studios (growing segment) "
                "need AI-first tools. Open-source Godot shows viable alternative "
                "to incumbents. $200B gaming market with AI spend accelerating."
        },
        "vcr": {
            "scores": {"MKT": 8.5, "CAP": 7.0, "ECO": 7.5, "VEL": 7.0, "MOA": 7.0},
            "rationale": "TAM $15-25B (game development tools + AI middleware). "
                "B2B developer sales, 6-month adoption cycle. Platform margins "
                "65-75% (lower than pure SaaS due to compute). Developer "
                "ecosystem moat once adopted. $200B gaming market is AI's next "
                "transformation frontier."
        },
        "forces_v3": ["F1_technology", "F4_capital"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_calibration_evidence",
        "source_batch": "v54_calibration_models",
        "primary_category": "STRUCTURAL_WINNER",
        "narrative_ids": ["TN-004"],
        "framework_evidence": {
            "jevons": "AI tools expand total games produced (indie/solo dev boom)",
            "coase": "Enables solo developer to produce AAA-quality content",
            "perez": "Developer tools monetize quickly via subscriptions"
        }
    },
    {
        "id": "MC-V54-LIVEV-001",
        "name": "AI Live Entertainment Optimization Platform",
        "one_liner": "Vertical SaaS for venues, promoters, and events — AI-driven "
                     "dynamic pricing, demand forecasting, audience analytics, "
                     "and personalized marketing for live entertainment",
        "architecture": "vertical_saas",
        "sector_naics": "7111",
        "sector_name": "Performing Arts Companies",
        "scores": {"SN": 7.5, "FA": 6.5, "EC": 7.0, "TG": 7.0, "CE": 6.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 6, "DV": 7},
            "rationale": "Live entertainment is highly fragmented (100K+ venues, "
                "thousands of promoters). Ticketmaster/Live Nation dominate "
                "ticketing but venue management software is fragmented. AI "
                "pricing/demand forecasting is nascent. Revenue management "
                "approach proven in hotels/airlines, not yet applied to venues."
        },
        "vcr": {
            "scores": {"MKT": 7.0, "CAP": 7.0, "ECO": 7.0, "VEL": 7.0, "MOA": 6.0},
            "rationale": "TAM $5-10B (venue management + event optimization). "
                "B2B SaaS with 6-month sales cycles. 75%+ margins. Venue "
                "operators desperate for yield optimization post-COVID recovery. "
                "Data moat from pricing/attendance patterns."
        },
        "forces_v3": ["F1_technology", "F5_psychology"],
        "confidence_tier": "MEDIUM",
        "evidence_quality": "2026_calibration_evidence",
        "source_batch": "v54_calibration_models",
        "primary_category": "TIMING_ARBITRAGE",
        "narrative_ids": ["TN-014"],
        "framework_evidence": {
            "baumol": "Live entertainment is classic Baumol cost-disease — "
                      "AI cracks it via yield optimization not cost reduction",
            "fear": "Post-COVID venue recovery creates urgency for optimization"
        }
    },
    {
        "id": "MC-V54-SYNMED-001",
        "name": "Synthetic Media Rights & Compliance Platform",
        "one_liner": "Compliance automation for AI-generated content — provenance "
                     "tracking, rights clearance, deepfake detection, and "
                     "regulatory compliance for studios and platforms",
        "architecture": "compliance_automation",
        "sector_naics": "7112",
        "sector_name": "Spectator Sports",
        "scores": {"SN": 8.0, "FA": 8.5, "EC": 6.5, "TG": 8.0, "CE": 6.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 7, "DV": 8},
            "rationale": "Nascent market with no dominant player. EU AI Act mandates "
                "content provenance by Aug 2026. C2PA standard exists but no "
                "enterprise compliance platform. Deepfake detection is $5B+ "
                "growing market. Content authenticity is fear-driven demand "
                "(studios, news organizations, sports leagues all need it)."
        },
        "vcr": {
            "scores": {"MKT": 7.5, "CAP": 7.0, "ECO": 7.5, "VEL": 7.5, "MOA": 7.5},
            "rationale": "TAM $10-20B (content compliance + provenance). Enterprise "
                "B2B sales, regulation-driven urgency. 70%+ margins. Regulatory "
                "moat once certified (EU AI Act compliance = recurring revenue). "
                "C2PA coalition creates standard, platform owns implementation."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics", "F5_psychology"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_calibration_evidence",
        "source_batch": "v54_calibration_models",
        "primary_category": "FEAR_ECONOMY",
        "narrative_ids": ["TN-004", "TN-014"],
        "framework_evidence": {
            "fear": "Deepfake crisis + EU AI Act creates massive compliance demand",
            "oversight": "THIS model enables oversight of AI-generated content",
            "perez": "Regulation-driven revenue is countercyclical"
        }
    },
]


def build_new_model(template):
    """Build complete model from template, computing composites and categories."""
    m = deepcopy(template)
    m["composite"] = compute_t(m["scores"])
    m["cla"]["composite"] = compute_cla(m["cla"]["scores"])
    m["cla"]["category"] = cla_category(m["cla"]["composite"])

    m["vcr"]["composite"] = compute_vcr(m["vcr"]["scores"])
    m["vcr"]["category"] = vcr_category(m["vcr"]["composite"])

    # ROI estimate
    vcr_s = m["vcr"]["scores"]
    tam_factor = vcr_s["MKT"] * 100  # rough $M
    cap_rate = vcr_s["CAP"] * 0.002
    vel = 1.0 + (vcr_s["VEL"] - 5) * 0.15
    rev_multiple = 12.0 if "saas" in m.get("architecture", "") else 8.0
    y5_rev = tam_factor * cap_rate * vel
    exit_val = y5_rev * rev_multiple
    m["vcr"]["roi_estimate"] = {
        "year5_revenue_M": round(y5_rev, 1),
        "revenue_multiple": rev_multiple,
        "exit_val_M": round(exit_val, 1),
        "seed_roi_multiple": round(exit_val / 10.0, 1)
    }

    m["category"] = [m["primary_category"]]
    m["new_in_v36"] = False
    return m


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("v5.4 Calibration Pass")
    print("=" * 70)

    # Load data
    with open(MODELS_FILE) as f:
        models_data = json.load(f)
    models = models_data.get("models", models_data) if isinstance(models_data, dict) else models_data

    print("Loaded {} models".format(len(models)))

    # ── Phase 1: Apply calibration rules ──
    print("\n── Phase 1: Applying calibration rules ──")
    all_adjustments = {}
    rule_counts = Counter()
    total_adjusted = 0

    for m in models:
        adjs = apply_calibration(m)
        if adjs:
            total_adjusted += 1
            all_adjustments[m["id"]] = adjs
            for a in adjs:
                rule_counts[a["rule"]] += 1

            # Recompute composites
            m["composite"] = round(compute_t(m["scores"]), 2)
            m["cla"]["composite"] = round(compute_cla(m["cla"]["scores"]), 2)
            m["cla"]["category"] = cla_category(m["cla"]["composite"])
            # VCR unchanged by these rules (except indirectly)
            m["vcr"]["composite"] = round(compute_vcr(m["vcr"]["scores"]), 2)
            m["vcr"]["category"] = vcr_category(m["vcr"]["composite"])

    print("Models adjusted: {}".format(total_adjusted))
    print("Adjustments by rule:")
    for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
        print("  {}: {} models".format(rule, count))

    # ── Phase 2: Add new models ──
    print("\n── Phase 2: Adding new Arts/Entertainment models ──")
    existing_ids = {m["id"] for m in models}
    added = []
    for template in NEW_MODELS:
        if template["id"] not in existing_ids:
            m = build_new_model(template)
            models.append(m)
            added.append(m["id"])
            print("  + {} — {} (T={}, CLA={}, VCR={})".format(
                m["id"], m["name"],
                round(m["composite"], 1),
                round(m["cla"]["composite"], 1),
                round(m["vcr"]["composite"], 1)))
    print("Added {} new models".format(len(added)))

    # ── Phase 3: Recompute all ranks ──
    print("\n── Phase 3: Recomputing all ranks ──")

    # T-rank
    models.sort(key=lambda m: -m["composite"])
    for i, m in enumerate(models):
        m["rank"] = i + 1

    # CLA/Opportunity rank
    models.sort(key=lambda m: -m["cla"]["composite"])
    for i, m in enumerate(models):
        m["opportunity_rank"] = i + 1

    # VCR rank
    models.sort(key=lambda m: -m["vcr"]["composite"])
    for i, m in enumerate(models):
        m["vcr_rank"] = i + 1

    # Sort back by T-rank for output
    models.sort(key=lambda m: m["rank"])

    # ── Phase 4: Statistics ──
    print("\n── Phase 4: Distribution statistics ──")
    t_scores_all = [m["composite"] for m in models]
    cla_scores_all = [m["cla"]["composite"] for m in models]
    vcr_scores_all = [m["vcr"]["composite"] for m in models]

    print("T-Score:  mean={:.1f}, median={:.1f}, stdev={:.1f}".format(
        statistics.mean(t_scores_all),
        statistics.median(t_scores_all),
        statistics.stdev(t_scores_all)))
    print("CLA:      mean={:.1f}, median={:.1f}, stdev={:.1f}".format(
        statistics.mean(cla_scores_all),
        statistics.median(cla_scores_all),
        statistics.stdev(cla_scores_all)))
    print("VCR:      mean={:.1f}, median={:.1f}, stdev={:.1f}".format(
        statistics.mean(vcr_scores_all),
        statistics.median(vcr_scores_all),
        statistics.stdev(vcr_scores_all)))

    # T↔CLA correlation
    t_mean = statistics.mean(t_scores_all)
    cla_mean = statistics.mean(cla_scores_all)
    n = len(models)
    cov = sum((t_scores_all[i] - t_mean) * (cla_scores_all[i] - cla_mean)
              for i in range(n)) / n
    t_std = statistics.stdev(t_scores_all)
    cla_std = statistics.stdev(cla_scores_all)
    t_cla_r = cov / (t_std * cla_std) if t_std > 0 and cla_std > 0 else 0
    print("T↔CLA correlation: r={:.3f}".format(t_cla_r))

    # Category distributions
    t_cats = Counter(t_category(m["composite"]) for m in models)
    cla_cats = Counter(m["cla"]["category"] for m in models)
    vcr_cats = Counter(m["vcr"]["category"] for m in models)
    print("\nT categories: {}".format(dict(t_cats)))
    print("CLA categories: {}".format(dict(cla_cats)))
    print("VCR categories: {}".format(dict(vcr_cats)))

    # Top 10 by geometric mean
    print("\n── Top 10 Triple Actionable (post-calibration) ──")
    for m in models:
        m["_gm"] = geo_mean(m["composite"], m["cla"]["composite"],
                            m["vcr"]["composite"])
    models.sort(key=lambda m: -m["_gm"])
    for i, m in enumerate(models[:10]):
        print("  #{}: {} — GM={:.1f} (T={:.1f}, CLA={:.1f}, VCR={:.1f})".format(
            i + 1, m["name"], m["_gm"],
            m["composite"], m["cla"]["composite"], m["vcr"]["composite"]))
    # Clean up temp field
    for m in models:
        del m["_gm"]

    # Sort back by T-rank
    models.sort(key=lambda m: m["rank"])

    # ── Phase 5: Biggest movers ──
    print("\n── Phase 5: Biggest CLA changes (top 15 drops) ──")
    cla_changes = []
    for mid, adjs in all_adjustments.items():
        for a in adjs:
            if "delta_composite" in a and a["rule"] in ("FSR_CLA_RECALIBRATION",
                                                         "SECTOR_CLA_DEFLATION"):
                cla_changes.append((mid, a["delta_composite"], a["rule"]))
    cla_changes.sort(key=lambda x: x[1])
    for mid, delta, rule in cla_changes[:15]:
        m = next(m for m in models if m["id"] == mid)
        print("  {} ({}) → CLA={:.1f} (Δ={:.1f}) [{}]".format(
            mid, m.get("architecture", "?"),
            m["cla"]["composite"], delta, rule))

    print("\n── Biggest T-score boosts (top 10) ──")
    t_changes = []
    for mid, adjs in all_adjustments.items():
        for a in adjs:
            if "delta_composite" in a and a["rule"].endswith("_T_BOOST"):
                t_changes.append((mid, a["delta_composite"], a["rule"]))
    t_changes.sort(key=lambda x: -x[1])
    for mid, delta, rule in t_changes[:10]:
        m = next(m for m in models if m["id"] == mid)
        print("  {} → T={:.1f} (Δ=+{:.1f}) [{}]".format(
            mid, m["composite"], delta, rule))

    # ── Phase 6: Save ──
    print("\n── Phase 6: Saving ──")

    # Update models file
    if isinstance(models_data, dict):
        models_data["models"] = models
        models_data["count"] = len(models)
        models_data["last_updated"] = datetime.now().isoformat()
        models_data["version"] = "v5.4_calibration"
    else:
        models_data = models

    with open(MODELS_FILE, "w") as f:
        json.dump(models_data, f, indent=2)
    print("Saved {} models to {}".format(len(models), MODELS_FILE))

    # Add new model IDs to narratives
    with open(NARRATIVES_FILE) as f:
        narr_data = json.load(f)
    narratives = narr_data.get("narratives", narr_data) if isinstance(narr_data, dict) else narr_data

    narr_map = {n["narrative_id"]: n for n in narratives}
    for template in NEW_MODELS:
        mid = template["id"]
        for nid in template.get("narrative_ids", []):
            if nid in narr_map:
                narr = narr_map[nid]
                ww = narr.get("outputs", {}).get("what_works", [])
                if isinstance(ww, list):
                    if mid not in ww:
                        ww.append(mid)
                elif isinstance(ww, str):
                    if mid not in ww:
                        narr["outputs"]["what_works"] = ww + ", " + mid

    with open(NARRATIVES_FILE, "w") as f:
        json.dump(narr_data, f, indent=2)
    print("Updated narratives with new model references")

    # Save calibration report
    report = {
        "version": "v5.4",
        "timestamp": datetime.now().isoformat(),
        "description": "Calibration pass: FSR CLA recalibration (127→{}), "
                       "sector CLA deflation (4 sectors), 2026 T-score boosts "
                       "(Education, Government, Mining, Transportation), OPP boosts "
                       "(Retail, Agriculture), 4 new Arts/Entertainment models".format(
                           rule_counts.get("FSR_CLA_RECALIBRATION", 0)),
        "models_before": 793,
        "models_after": len(models),
        "total_adjusted": total_adjusted,
        "new_models": added,
        "rule_counts": dict(rule_counts),
        "statistics": {
            "t_mean": round(statistics.mean(t_scores_all), 1),
            "t_median": round(statistics.median(t_scores_all), 1),
            "cla_mean": round(statistics.mean(cla_scores_all), 1),
            "cla_median": round(statistics.median(cla_scores_all), 1),
            "vcr_mean": round(statistics.mean(vcr_scores_all), 1),
            "vcr_median": round(statistics.median(vcr_scores_all), 1),
            "t_cla_correlation": round(t_cla_r, 3),
        },
        "adjustments_detail": all_adjustments,
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print("Saved calibration report to {}".format(REPORT_FILE))

    # Update state
    with open(STATE_FILE) as f:
        state = json.load(f)
    state["engine_version"] = "5.4"
    state["description"] = (
        "v5.4: {} models ({} adjusted, {} new). Calibration pass: "
        "FSR CLA recalibration, sector CLA deflation, 2026 evidence "
        "T/OPP boosts (Education, Government, Mining, Retail, Agriculture, "
        "Transportation), 4 new Arts/Entertainment models.".format(
            len(models), total_adjusted, len(added))
    )
    state["entity_counts"]["models"] = len(models)
    state["cycles"].append({
        "cycle_id": "v5-4-calibration",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "models_before": 793,
        "models_after": len(models),
        "new_models": added,
        "calibration_rules_applied": len(rule_counts),
        "models_adjusted": total_adjusted,
        "total_adjustments": sum(rule_counts.values()),
        "key_findings": []
    })
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print("Updated state to v5.4")

    print("\n" + "=" * 70)
    print("v5.4 Calibration COMPLETE")
    print("  Models: {} ({} adjusted, {} new)".format(
        len(models), total_adjusted, len(added)))
    print("  Rules applied: {}".format(sum(rule_counts.values())))
    print("=" * 70)


if __name__ == "__main__":
    main()
