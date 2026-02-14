#!/usr/bin/env python3
"""
v5.3 "Framework Validation Rescore"

Applies 2026 framework validation findings as systematic score adjustments
to all 788 models, creates new evidence-based models, and reranks.

8 Rescoring Rules (axis-level adjustments):
  1. JEVONS_TAM_EXPANSION:   SN +0.5 — efficiency expands demand (devs +60%, cloud doubles)
  2. FEAR_STRUCTURAL:        FA +0.5 — fear is structural adoption barrier (F5 models)
  3. BAUMOL_WRAPPER:         SN +0.5 — AI wrappers crack Baumol in cost-disease sectors
  4. PEREZ_CRASH_RESILIENCE: TG ±0.5 — revenue models boosted, capital-dependent penalized
  5. OVERSIGHT_BOTTLENECK:   CE -0.5 — HITL constraint in high-trust sectors (11% in prod)
  6. PHYSICAL_AUTOMATION:    CE +0.5 — robot payback 5.3→1.3yr validated
  7. COASE_MICRO:            MO +0.5 — micro-firm viability validated (Coasean singularity)
  8. VELOCITY_ASYMMETRY:     MOA +0.5 — workforce-bridge models get moat boost

New Models (5):
  - AI Agent Reliability Platform
  - AI Developer Productivity OS (open-core)
  - Sovereign AI Infrastructure Platform
  - AI Workforce Transition Platform
  - Humanoid Robot Fleet Management SaaS

Input:  data/v4/models.json (788 models)
Output: data/v4/models.json (updated in place, rescored + new models)
        data/v5/framework_rescore_report.json (detailed change log)
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
REPORT_FILE = V5_DIR / "framework_rescore_report.json"

T_WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}
CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}
VCR_WEIGHTS = {"MKT": 25, "CAP": 25, "ECO": 20, "VEL": 15, "MOA": 15}

# ── T-score category thresholds ──
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


def compute_t_composite(scores):
    return sum(scores[a] * T_WEIGHTS[a] for a in T_WEIGHTS) / 10.0

def compute_cla_composite(scores):
    return sum(scores[a] * CLA_WEIGHTS[a] for a in CLA_WEIGHTS) / 10.0

def compute_vcr_composite(scores):
    return sum(scores[a] * VCR_WEIGHTS[a] for a in VCR_WEIGHTS) / 10.0

def geo_mean(t, o, v):
    return (t * o * v) ** (1.0 / 3.0)

def clamp(val, lo=1.0, hi=10.0):
    return max(lo, min(hi, val))


# ══════════════════════════════════════════════════════════════════════
# Sector / Architecture Classifications
# ══════════════════════════════════════════════════════════════════════

# Sectors where Jevons paradox is confirmed (efficiency → TAM expansion)
JEVONS_SECTORS = {"51", "54", "52", "5415", "5112", "5411", "5412",
                  "5416", "5231", "5239", "5221"}

# Sectors with Baumol cost disease where AI wrappers crack it
BAUMOL_SECTORS = {"62", "61", "54", "81", "6211", "6214", "6221",
                  "6231", "6241", "5411", "5412", "5413", "5416",
                  "6111", "6113", "6115", "8111", "8121"}

# AI wrapper architectures (layer ON TOP of Baumol sectors)
BAUMOL_WRAPPER_ARCHS = {"vertical_saas", "platform_infrastructure",
                        "ai_copilot", "compliance_automation",
                        "data_compounding", "open_core_ecosystem"}

# High-trust sectors requiring human oversight
OVERSIGHT_SECTORS = {"62", "52", "92", "6211", "6214", "6221", "6231",
                     "5221", "5231", "5241", "5411", "9211", "9221"}

# Oversight-constrained architectures
OVERSIGHT_ARCHS = {"full_service_replacement", "ai_copilot"}

# Physical automation architectures
PHYSICAL_ARCHS = {"robotics_automation", "physical_production_ai",
                  "hardware_ai", "hardware_plus_saas"}

# Workforce bridge sectors (velocity asymmetry)
VELOCITY_BRIDGE_SECTORS = {"61", "56", "6111", "6113", "6115",
                           "5613", "5614", "5615"}

# Workforce bridge architectures
VELOCITY_BRIDGE_ARCHS = {"service_platform", "academy_platform",
                         "platform_infrastructure", "marketplace_network"}


def normalize_forces(forces):
    """Convert force tags to set of short codes (F1, F2, etc.)."""
    result = set()
    if not forces:
        return result
    for f in forces:
        if f.startswith("F") and len(f) <= 3:
            result.add(f[:2])
        elif "_" in f:
            result.add(f.split("_")[0])
        else:
            result.add(f)
    return result


def get_naics2(model):
    """Get 2-digit NAICS from model."""
    sn = str(model.get("sector_naics", ""))
    return sn[:2] if len(sn) >= 2 else sn


# ══════════════════════════════════════════════════════════════════════
# RULE ENGINE
# ══════════════════════════════════════════════════════════════════════

def apply_rules(model):
    """Apply all 8 framework validation rules to a model.
    Returns dict of adjustments applied with reasons."""
    adjustments = []
    arch = model.get("architecture", "")
    naics = str(model.get("sector_naics", ""))
    naics2 = get_naics2(model)
    forces = normalize_forces(model.get("forces_v3", []))
    t_scores = model["scores"]
    cla_scores = model["cla"]["scores"]
    vcr_scores = model["vcr"]["scores"]
    name = model.get("name", "")

    # ── Rule 1: JEVONS_TAM_EXPANSION ──
    # Efficiency gains expand TAM (devs +60%, cloud doubles)
    # AI tool models in software/professional/finance sectors
    if (naics in JEVONS_SECTORS or naics2 in JEVONS_SECTORS) and \
       arch in {"ai_copilot", "vertical_saas", "open_core_ecosystem",
                "platform_infrastructure", "data_compounding"}:
        old_sn = t_scores["SN"]
        t_scores["SN"] = clamp(old_sn + 0.5)
        if t_scores["SN"] != old_sn:
            adjustments.append({
                "rule": "JEVONS_TAM_EXPANSION",
                "axis": "T.SN", "delta": round(t_scores["SN"] - old_sn, 2),
                "reason": "Jevons paradox: efficiency expands demand in {}"
                          .format(naics)
            })

    # ── Rule 2: FEAR_STRUCTURAL ──
    # Fear is structural adoption barrier, not noise
    if "F5" in forces:
        old_fa = t_scores["FA"]
        t_scores["FA"] = clamp(old_fa + 0.5)
        if t_scores["FA"] != old_fa:
            adjustments.append({
                "rule": "FEAR_STRUCTURAL",
                "axis": "T.FA", "delta": round(t_scores["FA"] - old_fa, 2),
                "reason": "Fear economics: F5 validated as structural "
                          "(AI usage +13% but confidence -18%)"
            })

    # ── Rule 3: BAUMOL_WRAPPER ──
    # AI wrapper models crack Baumol in cost-disease sectors
    if (naics in BAUMOL_SECTORS or naics2 in BAUMOL_SECTORS) and \
       arch in BAUMOL_WRAPPER_ARCHS:
        old_sn = t_scores["SN"]
        t_scores["SN"] = clamp(old_sn + 0.5)
        if t_scores["SN"] != old_sn:
            adjustments.append({
                "rule": "BAUMOL_WRAPPER",
                "axis": "T.SN", "delta": round(t_scores["SN"] - old_sn, 2),
                "reason": "Baumol crack: AI wrapper bypasses cost disease "
                          "in {} (20-40% measured reductions)".format(naics)
            })

    # ── Rule 4: PEREZ_CRASH_RESILIENCE ──
    # Revenue-generating models are crash-resilient; capital-dependent are not
    vel_score = vcr_scores.get("VEL", 5)
    if vel_score >= 7 and arch not in {"arbitrage_window"}:
        # Fast revenue = crash resilient
        old_tg = t_scores["TG"]
        t_scores["TG"] = clamp(old_tg + 0.5)
        if t_scores["TG"] != old_tg:
            adjustments.append({
                "rule": "PEREZ_CRASH_RESILIENCE_BOOST",
                "axis": "T.TG", "delta": round(t_scores["TG"] - old_tg, 2),
                "reason": "Perez frenzy: fast-revenue model (VEL={}) survives "
                          "crash (Mag7 35% S&P, frenzy peak)".format(vel_score)
            })
    elif arch == "arbitrage_window" and t_scores["TG"] <= 5:
        # Capital dependent = crash vulnerable
        old_tg = t_scores["TG"]
        t_scores["TG"] = clamp(old_tg - 0.5)
        if t_scores["TG"] != old_tg:
            adjustments.append({
                "rule": "PEREZ_CRASH_VULNERABILITY",
                "axis": "T.TG", "delta": round(t_scores["TG"] - old_tg, 2),
                "reason": "Perez crash risk: capital-dependent arbitrage window "
                          "vulnerable in frenzy peak"
            })

    # ── Rule 5: OVERSIGHT_BOTTLENECK ──
    # Full-service replacement in high-trust sectors faces HITL constraint
    if arch in OVERSIGHT_ARCHS and \
       (naics in OVERSIGHT_SECTORS or naics2 in OVERSIGHT_SECTORS):
        old_ce = t_scores["CE"]
        t_scores["CE"] = clamp(old_ce - 0.5)
        if t_scores["CE"] != old_ce:
            adjustments.append({
                "rule": "OVERSIGHT_BOTTLENECK",
                "axis": "T.CE", "delta": round(t_scores["CE"] - old_ce, 2),
                "reason": "Oversight constraint: only 11% agentic AI in "
                          "production, {} requires HITL in {}".format(arch, naics)
            })

    # ── Rule 6: PHYSICAL_AUTOMATION_BOOST ──
    # Robot payback 5.3→1.3yr validated
    if arch in PHYSICAL_ARCHS:
        old_ce = t_scores["CE"]
        t_scores["CE"] = clamp(old_ce + 0.5)
        if t_scores["CE"] != old_ce:
            adjustments.append({
                "rule": "PHYSICAL_AUTOMATION_BOOST",
                "axis": "T.CE", "delta": round(t_scores["CE"] - old_ce, 2),
                "reason": "Physical automation: robot payback 5.3→1.3yr, "
                          "Figure AI $39B validates economics"
            })

    # ── Rule 7: COASE_MICRO ──
    # Micro-firm viability validated (Coasean singularity)
    narrative_ids = model.get("narrative_ids", [])
    if "TN-016" in narrative_ids or arch in {"micro_firm_os"}:
        old_mo = cla_scores["MO"]
        cla_scores["MO"] = clamp(old_mo + 0.5)
        if cla_scores["MO"] != old_mo:
            adjustments.append({
                "rule": "COASE_MICRO",
                "axis": "CLA.MO", "delta": round(cla_scores["MO"] - old_mo, 2),
                "reason": "Coase bimodal: micro-firm viability confirmed "
                          "(Lovable unicorn w/45 people, NBER Coasean Singularity)"
            })

    # ── Rule 8: VELOCITY_ASYMMETRY_MOAT ──
    # Workforce-bridge models get moat from structural gap
    if (naics in VELOCITY_BRIDGE_SECTORS or naics2 in VELOCITY_BRIDGE_SECTORS) \
       and arch in VELOCITY_BRIDGE_ARCHS:
        old_moa = vcr_scores["MOA"]
        vcr_scores["MOA"] = clamp(old_moa + 0.5)
        if vcr_scores["MOA"] != old_moa:
            adjustments.append({
                "rule": "VELOCITY_ASYMMETRY_MOAT",
                "axis": "VCR.MOA", "delta": round(vcr_scores["MOA"] - old_moa, 2),
                "reason": "Velocity asymmetry: capital 10x faster than "
                          "workforce, bridge models get structural moat"
            })

    return adjustments


# ══════════════════════════════════════════════════════════════════════
# NEW MODEL DEFINITIONS
# ══════════════════════════════════════════════════════════════════════

NEW_MODELS = [
    {
        "id": "MC-V53-AGREL-001",
        "name": "AI Agent Reliability & Evaluation Platform",
        "one_liner": "Observability, testing, and guardrails platform for "
                     "production AI agent deployments — the DataDog of agentic AI",
        "architecture": "open_core_ecosystem",
        "sector_naics": "5415",
        "sector_name": "Computer Systems Design and Related Services",
        "scores": {"SN": 9.0, "FA": 8.5, "EC": 7.5, "TG": 8.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 9, "MA": 9, "VD": 8, "DV": 9},
            "rationale": "Nascent market with no dominant player. ArizeAI, "
                "LangSmith early but no platform owns agent reliability. "
                "Open-source wedge + enterprise SaaS model proven. Only 11% "
                "of agentic AI in production — everyone needs guardrails."
        },
        "vcr": {
            "scores": {"MKT": 8.5, "CAP": 8.0, "ECO": 9.0, "VEL": 8.0, "MOA": 8.0},
            "rationale": "AI observability TAM $5-15B by 2028 (from $1B). "
                "Open-core PLG, 80%+ margins. Developer adoption <6 months. "
                "Data moat from production telemetry. Akin to Datadog's early "
                "trajectory ($2.2B revenue, 80% margins)."
        },
        "forces_v3": ["F1_technology", "F4_capital", "F5_psychology"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_framework_validation",
        "source_batch": "v53_framework_models",
        "primary_category": "STRUCTURAL_WINNER",
        "narrative_ids": ["TN-004"],
        "framework_evidence": {
            "jevons": "More AI agents = more monitoring needed (demand grows with supply)",
            "fear": "Enterprise trust deficit (only 11% in production) creates demand",
            "perez": "Revenue-generating within 6 months, crash-resilient",
            "oversight": "THIS model solves the oversight bottleneck itself"
        }
    },
    {
        "id": "MC-V53-DEVAI-001",
        "name": "AI-Native Developer Productivity OS",
        "one_liner": "Open-core AI coding platform combining code generation, "
                     "review, testing, and deployment — productivity layer for "
                     "every developer",
        "architecture": "open_core_ecosystem",
        "sector_naics": "5112",
        "sector_name": "Software Publishers",
        "scores": {"SN": 9.5, "FA": 9.0, "EC": 8.0, "TG": 9.0, "CE": 7.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 8, "DV": 9},
            "rationale": "GitHub Copilot dominates but market is expanding, not "
                "zero-sum (Jevons). Cursor $500M ARR in <2yr proves second "
                "mover viability. Anthropic Claude Code $2.5B ARR. Multi-layer "
                "stack (IDE, CI/CD, review, testing, deployment) means multiple "
                "entry points. Open-source critical for developer adoption."
        },
        "vcr": {
            "scores": {"MKT": 9.0, "CAP": 8.0, "ECO": 9.0, "VEL": 9.0, "MOA": 7.5},
            "rationale": "TAM $50B+ (28M developers × $1.8K/yr avg spend). "
                "PLG with developer community, <3 months to revenue. Pure "
                "software 85%+ margins. Cursor proves: $500M ARR in 18 months. "
                "Data moat from code patterns but AI advances erode quickly."
        },
        "forces_v3": ["F1_technology", "F4_capital"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_framework_validation",
        "source_batch": "v53_framework_models",
        "primary_category": "FORCE_RIDER",
        "narrative_ids": ["TN-004"],
        "framework_evidence": {
            "jevons": "STRONGEST case: developer demand +60% despite Copilot, "
                      "Cursor $500M ARR proves TAM expansion not substitution",
            "perez": "Revenue-generating day 1, PLG model crash-proof",
            "coase": "Enables 5-person firm to ship like 50-person team"
        }
    },
    {
        "id": "MC-V53-SOVAI-001",
        "name": "Sovereign AI Infrastructure Platform",
        "one_liner": "Turnkey national AI compute + model serving + data "
                     "sovereignty stack for non-US governments deploying "
                     "domestic AI capability",
        "architecture": "platform_infrastructure",
        "sector_naics": "5415",
        "sector_name": "Computer Systems Design and Related Services",
        "scores": {"SN": 8.5, "FA": 7.5, "EC": 6.5, "TG": 7.0, "CE": 6.0},
        "cla": {
            "scores": {"MO": 6, "MA": 6, "VD": 7, "DV": 7},
            "rationale": "Hyperscalers (AWS, Azure, GCP) are primary competitors "
                "but sovereignty requirements actively exclude US clouds in EU, "
                "India, Japan, MENA. Aleph Alpha (EU), Sakana AI (Japan) are "
                "early. Multi-layer stack: compute, model serving, data "
                "governance, applications. Government procurement is slow "
                "but sovereignty mandates create urgency."
        },
        "vcr": {
            "scores": {"MKT": 8.0, "CAP": 4.5, "ECO": 5.5, "VEL": 4.0, "MOA": 7.5},
            "rationale": "TAM $30-50B (government AI spend outside US). "
                "Government sales 18-36 month cycles. Infrastructure margins "
                "lower (50-60%) but massive contract values. Regulatory moat "
                "once certified (data sovereignty = permanent lock-in). "
                "Government procurement limits seed-stage capture."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics", "F4_capital"],
        "confidence_tier": "HIGH",
        "evidence_quality": "2026_framework_validation",
        "source_batch": "v53_framework_models",
        "primary_category": "STRUCTURAL_WINNER",
        "narrative_ids": ["TN-004", "TN-008"],
        "framework_evidence": {
            "geopolitics": "Every G20 building domestic AI, EU AI Act mandates "
                           "sovereignty, $650B hyperscaler capex forces response",
            "perez": "Government spending countercyclical — survives any crash",
            "coase": "Breaks Coase toward larger entities (sovereignty requires scale)"
        }
    },
    {
        "id": "MC-V53-WKTRN-001",
        "name": "AI Workforce Transition Platform",
        "one_liner": "Skills mapping, retraining orchestration, and career "
                     "pathway platform for workers displaced by AI automation — "
                     "bridging the velocity asymmetry gap",
        "architecture": "service_platform",
        "sector_naics": "6113",
        "sector_name": "Colleges, Universities, and Professional Schools",
        "scores": {"SN": 8.0, "FA": 8.5, "EC": 7.0, "TG": 7.5, "CE": 6.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 8},
            "rationale": "LinkedIn Learning, Coursera exist but none purpose-built "
                "for AI displacement. Guild Education ($4.4B) proved employer-paid "
                "model. 245K tech layoffs + AI adoption creates acute demand. "
                "Government mandates likely (WARN Act expansion). No dominant "
                "AI-native reskilling platform exists. Entry through employer "
                "relationships or government contracts."
        },
        "vcr": {
            "scores": {"MKT": 7.5, "CAP": 6.5, "ECO": 6.5, "VEL": 6.0, "MOA": 7.0},
            "rationale": "TAM $20-30B (corporate training $370B shifting to AI "
                "reskilling). Mixed B2B/B2G sales. Platform margins 55-65%. "
                "12-month enterprise cycles. Strong moat from outcomes data "
                "(which transitions actually work). Velocity asymmetry is "
                "structural — demand grows every year."
        },
        "forces_v3": ["F1_technology", "F2_demographics", "F5_psychology"],
        "confidence_tier": "MEDIUM",
        "evidence_quality": "2026_framework_validation",
        "source_batch": "v53_framework_models",
        "primary_category": "STRUCTURAL_WINNER",
        "narrative_ids": ["TN-005"],
        "framework_evidence": {
            "velocity_asymmetry": "Capital deploys 10x faster than workforce "
                "adapts — this model bridges the gap directly",
            "fear": "ManpowerGroup: AI usage +13%, confidence -18% — fear "
                    "creates demand for trusted transition pathways",
            "demographics": "245K tech layoffs, 40% of workers need reskilling"
        }
    },
    {
        "id": "MC-V53-ROBFL-001",
        "name": "Humanoid Robot Fleet Management SaaS",
        "one_liner": "Cloud-native fleet orchestration, task scheduling, and "
                     "performance monitoring for humanoid robot deployments in "
                     "manufacturing and logistics",
        "architecture": "vertical_saas",
        "sector_naics": "3364",
        "sector_name": "Aerospace Product and Parts Manufacturing",
        "scores": {"SN": 8.5, "FA": 8.0, "EC": 7.0, "TG": 7.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 7, "DV": 8},
            "rationale": "Market barely exists — Figure AI, Boston Dynamics, "
                "Apptronik, Unitree are building robots but fleet management "
                "software is greenfield. Every manufacturer deploying humanoids "
                "needs orchestration (scheduling, monitoring, OTA updates, task "
                "allocation). Robot-agnostic SaaS layer has no incumbent. "
                "Similar to fleet management for autonomous vehicles."
        },
        "vcr": {
            "scores": {"MKT": 7.5, "CAP": 7.0, "ECO": 7.5, "VEL": 6.0, "MOA": 7.5},
            "rationale": "TAM $5-15B by 2030 (humanoid robot fleet at scale). "
                "B2B enterprise sales but pull demand from early adopters. "
                "SaaS margins 75%+. 12-month sales cycle. Strong data moat "
                "from operational telemetry. Robot payback 1.3yr means fleet "
                "expansion is accelerating."
        },
        "forces_v3": ["F1_technology", "F2_demographics", "F4_capital"],
        "confidence_tier": "MEDIUM",
        "evidence_quality": "2026_framework_validation",
        "source_batch": "v53_framework_models",
        "primary_category": "TIMING_ARBITRAGE",
        "narrative_ids": ["TN-001"],
        "framework_evidence": {
            "physical_automation": "Robot payback 5.3→1.3yr, Figure AI $39B, "
                "Boston Dynamics Atlas fully allocated",
            "demographics": "Manufacturing labor shortage 2.1M unfilled by 2030",
            "perez": "Software layer on top of hardware — high margins, "
                     "crash-resilient recurring revenue"
        }
    },
]


def build_new_model(template):
    """Build a fully-formed model from a template definition."""
    m = deepcopy(template)

    # Compute composites
    m["composite"] = round(compute_t_composite(m["scores"]), 2)
    m["cla"]["composite"] = round(compute_cla_composite(m["cla"]["scores"]), 2)
    m["cla"]["category"] = cla_category(m["cla"]["composite"])
    m["vcr"]["composite"] = round(compute_vcr_composite(m["vcr"]["scores"]), 2)
    m["vcr"]["category"] = vcr_category(m["vcr"]["composite"])

    # ROI estimate
    mkt_s = m["vcr"]["scores"]["MKT"]
    cap_s = m["vcr"]["scores"]["CAP"]
    vel_s = m["vcr"]["scores"]["VEL"]
    eco_s = m["vcr"]["scores"]["ECO"]
    tam_est = 10 ** (1 + mkt_s * 0.4)  # rough TAM from score
    capture = cap_s * 0.01
    rev_5yr = tam_est * capture * (1 + vel_s * 0.1)
    margin = eco_s * 0.1
    rev_mult = 6 + eco_s * 0.8
    exit_val = rev_5yr * margin * rev_mult
    m["vcr"]["roi_estimate"] = {
        "year5_revenue_M": round(rev_5yr, 1),
        "revenue_multiple": round(rev_mult, 1),
        "exit_val_M": round(exit_val, 1),
        "seed_roi_multiple": round(exit_val / 10, 1)
    }

    # Add standard fields
    m.setdefault("role", "what_works")
    m.setdefault("category", [m["primary_category"]])

    return m


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=== v5.3 Framework Validation Rescore ===\n")

    # Load data
    with open(MODELS_FILE) as f:
        data = json.load(f)
    models_list = data.get("models", data) if isinstance(data, dict) else data
    is_wrapped = isinstance(data, dict) and "models" in data
    print("Loaded {} models".format(len(models_list)))

    # ── Phase 1: Apply rescoring rules to existing models ──
    print("\n── Phase 1: Applying 8 framework rules ──")
    all_adjustments = {}
    rule_counts = Counter()
    models_affected = set()
    score_deltas = {"T": [], "CLA": [], "VCR": []}

    for m in models_list:
        mid = m["id"]
        old_t = m["composite"]
        old_cla = m["cla"]["composite"]
        old_vcr = m["vcr"]["composite"]

        adjustments = apply_rules(m)

        if adjustments:
            # Recompute composites
            new_t = round(compute_t_composite(m["scores"]), 2)
            new_cla = round(compute_cla_composite(m["cla"]["scores"]), 2)
            new_vcr = round(compute_vcr_composite(m["vcr"]["scores"]), 2)

            m["composite"] = new_t
            m["cla"]["composite"] = new_cla
            m["cla"]["category"] = cla_category(new_cla)
            m["vcr"]["composite"] = new_vcr
            m["vcr"]["category"] = vcr_category(new_vcr)

            all_adjustments[mid] = {
                "name": m.get("name", ""),
                "adjustments": adjustments,
                "before": {"T": old_t, "CLA": old_cla, "VCR": old_vcr},
                "after": {"T": new_t, "CLA": new_cla, "VCR": new_vcr},
                "delta": {
                    "T": round(new_t - old_t, 2),
                    "CLA": round(new_cla - old_cla, 2),
                    "VCR": round(new_vcr - old_vcr, 2),
                }
            }
            models_affected.add(mid)
            for adj in adjustments:
                rule_counts[adj["rule"]] += 1

            score_deltas["T"].append(new_t - old_t)
            score_deltas["CLA"].append(new_cla - old_cla)
            score_deltas["VCR"].append(new_vcr - old_vcr)

    print("Models adjusted: {}".format(len(models_affected)))
    print("Rule application counts:")
    for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
        print("  {}: {}".format(rule, count))

    if score_deltas["T"]:
        print("\nScore delta stats:")
        for dim in ["T", "CLA", "VCR"]:
            vals = [v for v in score_deltas[dim] if v != 0]
            if vals:
                print("  {}: mean={:.2f}, min={:.2f}, max={:.2f}, "
                      "affected={}".format(
                    dim, statistics.mean(vals), min(vals), max(vals), len(vals)
                ))

    # ── Phase 2: Add new models ──
    print("\n── Phase 2: Adding {} new evidence-based models ──".format(
        len(NEW_MODELS)))
    new_model_objects = []
    for template in NEW_MODELS:
        m = build_new_model(template)
        models_list.append(m)
        new_model_objects.append(m)
        print("  + {} (T={}, CLA={}, VCR={})".format(
            m["id"], m["composite"],
            m["cla"]["composite"], m["vcr"]["composite"]
        ))

    # ── Phase 3: Recompute all ranks ──
    print("\n── Phase 3: Recomputing ranks ──")

    # T-rank
    models_list.sort(key=lambda m: -m["composite"])
    for i, m in enumerate(models_list):
        m["rank"] = i + 1

    # CLA/Opportunity rank
    models_list.sort(key=lambda m: -m["cla"]["composite"])
    for i, m in enumerate(models_list):
        m["opportunity_rank"] = i + 1

    # VCR rank
    models_list.sort(key=lambda m: -m["vcr"]["composite"])
    for i, m in enumerate(models_list):
        m["vcr_rank"] = i + 1

    # Triple actionable rank (geometric mean)
    for m in models_list:
        m["_triple"] = geo_mean(
            m["composite"], m["cla"]["composite"], m["vcr"]["composite"]
        )
    models_list.sort(key=lambda m: -m["_triple"])
    for i, m in enumerate(models_list):
        m["triple_actionable_rank"] = i + 1

    # Show new top 20
    print("\nNew Top 20 by Triple Actionable:")
    for m in models_list[:20]:
        gm = m["_triple"]
        flag = " *** NEW" if m.get("source_batch") == "v53_framework_models" else ""
        changed = " [RESCORED]" if m["id"] in models_affected else ""
        print("  #{:>3}  {:<55s} T={:>5.1f}  CLA={:>5.1f}  "
              "VCR={:>5.1f}  GM={:>5.2f}{}{}".format(
            m["triple_actionable_rank"], m["name"][:55],
            m["composite"], m["cla"]["composite"],
            m["vcr"]["composite"], gm, changed, flag
        ))

    # ── Phase 4: Identify top-50 movers ──
    print("\n── Phase 4: Top-50 Movement Analysis ──")
    top50_ids = {m["id"] for m in models_list[:50]}

    # New entries to top 50
    new_in_top50 = [m for m in models_list[:50]
                    if m.get("source_batch") == "v53_framework_models"]
    rescored_in_top50 = [m for m in models_list[:50]
                         if m["id"] in models_affected]

    print("New models in top 50: {}".format(len(new_in_top50)))
    for m in new_in_top50:
        print("  #{} {} (T={}, CLA={}, VCR={})".format(
            m["triple_actionable_rank"], m["name"],
            m["composite"], m["cla"]["composite"], m["vcr"]["composite"]
        ))

    print("Rescored models in top 50: {}".format(len(rescored_in_top50)))

    # Clean up temp field
    for m in models_list:
        del m["_triple"]

    # Sort by ID for stable output
    models_list.sort(key=lambda m: m["id"])

    # ── Save ──
    print("\n── Saving ──")
    if is_wrapped:
        data["models"] = models_list
        data["count"] = len(models_list)
        data["last_updated"] = datetime.now().isoformat()
    else:
        data = models_list

    with open(MODELS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("Saved {} models to {}".format(len(models_list), MODELS_FILE))

    # ── Generate report ──
    report = {
        "cycle": "v5-3",
        "timestamp": datetime.now().isoformat(),
        "engine_version": "5.3",
        "description": "Framework validation rescore: 8 rules applied to "
                       "{} models, {} adjusted, {} new models added".format(
                           len(models_list) - len(NEW_MODELS),
                           len(models_affected), len(NEW_MODELS)),
        "rules": {
            "JEVONS_TAM_EXPANSION": {
                "axis": "T.SN +0.5",
                "evidence": "Developer demand +60%, cloud spend doubles despite "
                            "unit cost drops, Cursor $500M ARR",
                "framework": "T6 Jevons Paradox — STRONGLY VALIDATED 2026"
            },
            "FEAR_STRUCTURAL": {
                "axis": "T.FA +0.5",
                "evidence": "ManpowerGroup: AI usage +13% but confidence -18%, "
                            "46% adoption plateau",
                "framework": "T25 Fear Economics — STRONGLY VALIDATED 2026"
            },
            "BAUMOL_WRAPPER": {
                "axis": "T.SN +0.5",
                "evidence": "Healthcare admin AI 20-40% cost reduction measured, "
                            "AI wrappers bypass cost disease",
                "framework": "T3 Baumol — VALIDATED WITH MODIFICATION (split)"
            },
            "PEREZ_CRASH_RESILIENCE": {
                "axis": "T.TG ±0.5",
                "evidence": "Mag 7 at 35% S&P (2x dot-com peak), frenzy phase "
                            "confirmed",
                "framework": "T5 Perez — STRONGLY VALIDATED 2026"
            },
            "OVERSIGHT_BOTTLENECK": {
                "axis": "T.CE -0.5",
                "evidence": "Only 11% of agentic AI in production, oversight "
                            "is the bottleneck",
                "framework": "NEW — Oversight Bottleneck (proposed T26)"
            },
            "PHYSICAL_AUTOMATION_BOOST": {
                "axis": "T.CE +0.5",
                "evidence": "Robot payback 5.3→1.3yr, Figure AI $39B, "
                            "Boston Dynamics Atlas fully allocated",
                "framework": "T24 Robotics×AI — STRONGLY VALIDATED 2026"
            },
            "COASE_MICRO": {
                "axis": "CLA.MO +0.5",
                "evidence": "Lovable unicorn w/45 people, NBER Coasean "
                            "Singularity paper",
                "framework": "T10 Coase — VALIDATED (bimodal split)"
            },
            "VELOCITY_ASYMMETRY_MOAT": {
                "axis": "VCR.MOA +0.5",
                "evidence": "Capital deploys 10x faster than workforce adapts, "
                            "245K layoffs, retraining gap",
                "framework": "NEW — Velocity Asymmetry (proposed T27)"
            }
        },
        "rule_counts": dict(rule_counts),
        "models_adjusted": len(models_affected),
        "new_models": [
            {
                "id": m["id"],
                "name": m["name"],
                "T": m["composite"],
                "CLA": m["cla"]["composite"],
                "VCR": m["vcr"]["composite"],
                "triple": round(geo_mean(
                    m["composite"], m["cla"]["composite"],
                    m["vcr"]["composite"]
                ), 2)
            }
            for m in new_model_objects
        ],
        "total_models": len(models_list),
        "adjustments_detail": all_adjustments
    }

    V5_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print("Report saved to {}".format(REPORT_FILE))

    # ── Update state ──
    with open(STATE_FILE) as f:
        state = json.load(f)

    state["engine_version"] = "5.3"
    state["description"] = (
        "v5.3: {} models ({} framework rescore adjustments, {} new models). "
        "8 rules from 2026 framework validation: Jevons, Fear, Baumol wrapper, "
        "Perez crash resilience, Oversight bottleneck, Physical automation, "
        "Coase micro, Velocity asymmetry.".format(
            len(models_list), len(models_affected), len(NEW_MODELS))
    )
    state["entity_counts"]["models"] = len(models_list)
    state["cycles"].append({
        "cycle_id": "v5-3-framework",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "models_before": len(models_list) - len(NEW_MODELS),
        "models_after": len(models_list),
        "new_models": [m["id"] for m in new_model_objects],
        "framework_rules_applied": 8,
        "models_rescored": len(models_affected),
        "score_adjustments": sum(rule_counts.values()),
        "key_findings": []
    })

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print("State updated to v5.3")

    print("\n=== DONE ===")
    return models_list, report


if __name__ == "__main__":
    models, report = main()
