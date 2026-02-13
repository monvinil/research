#!/usr/bin/env python3
"""v5.0 Cycle Applier — applies Agent C graded score adjustments and creates new models.

Reads: data/graded/v5-0_graded_2026-02-13.json
Modifies: data/v4/models.json
"""

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
MODELS_FILE = ROOT / "data" / "v4" / "models.json"
GRADED_FILE = ROOT / "data" / "graded" / "v5-0_graded_2026-02-13.json"

def calc_t_composite(s):
    return round((s["SN"]*25 + s["FA"]*25 + s["EC"]*20 + s["TG"]*15 + s["CE"]*15) / 10, 2)

def calc_cla_composite(s):
    return round((s["MO"]*30 + s["MA"]*25 + s["VD"]*20 + s["DV"]*25) / 10, 2)

def calc_vcr_composite(s):
    return round((s["MKT"]*25 + s["CAP"]*25 + s["ECO"]*20 + s["VEL"]*15 + s["MOA"]*15) / 10, 2)

def cla_category(c):
    if c >= 75: return "WIDE_OPEN"
    if c >= 60: return "ACCESSIBLE"
    if c >= 45: return "CONTESTED"
    if c >= 30: return "FORTIFIED"
    return "LOCKED"

def vcr_category(c):
    if c >= 75: return "FUND_RETURNER"
    if c >= 60: return "STRONG_MULTIPLE"
    if c >= 45: return "VIABLE_RETURN"
    if c >= 30: return "MARGINAL"
    return "VC_POOR"

def run():
    with open(MODELS_FILE) as f:
        data = json.load(f)
    models = data["models"]
    model_idx = {m["id"]: i for i, m in enumerate(models)}

    with open(GRADED_FILE) as f:
        graded = json.load(f)

    # Apply score adjustments
    adjustments_applied = 0
    for adj in graded["score_adjustments"]:
        mid = adj["model_id"]
        if mid not in model_idx:
            print("  WARNING: model {} not found".format(mid))
            continue
        m = models[model_idx[mid]]
        changes = adj["changes"]
        for axis, vals in changes.items():
            old_val = vals["old"]
            new_val = vals["new"]
            if axis in ("SN", "FA", "EC", "TG", "CE"):
                if m["scores"].get(axis) is not None:
                    m["scores"][axis] = new_val
                    print("  {} {}: {} -> {}".format(mid, axis, old_val, new_val))
            elif axis in ("MO", "MA", "VD", "DV"):
                if m.get("cla") and m["cla"].get("scores"):
                    m["cla"]["scores"][axis] = new_val
                    print("  {} CLA.{}: {} -> {}".format(mid, axis, old_val, new_val))
        # Recalculate composites
        m["composite"] = calc_t_composite(m["scores"])
        if m.get("cla") and m["cla"].get("scores"):
            m["cla"]["composite"] = calc_cla_composite(m["cla"]["scores"])
            m["cla"]["category"] = cla_category(m["cla"]["composite"])
        adjustments_applied += 1
        print("  {} T={} O={} [{}]".format(
            mid, m["composite"],
            m["cla"]["composite"] if m.get("cla") else "N/A",
            adj.get("requirement_id", "manual")
        ))

    print("\nApplied {} score adjustments".format(adjustments_applied))

    # Create new models
    new_models = [
        {
            "id": "MC-V50-RMN-001",
            "name": "Retail Media Network Technology Enabler",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5112",
            "sector_name": "Software Publishers",
            "architecture": "enabling_infrastructure",
            "forces_v3": ["F1_technology", "F4_capital"],
            "scores": {"SN": 8.0, "FA": 7.5, "EC": 8.0, "TG": 7.0, "CE": 7.0},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER"],
            "one_liner": "Technology platform enabling mid-market retailers to build and operate retail media networks without Amazon-scale resources — measurement, ad serving, audience segmentation, and reporting infrastructure for the 200+ RMNs competing for the 16% of spend not captured by Amazon and Walmart",
            "key_v3_context": "Decomposition of MC-V38-44-003 (Retail Media Network Platform). Parent model scores T=80, O=31 (FORTIFIED at platform level). This tech enablement layer is ACCESSIBLE because 200+ retailers need tooling but lack internal capability.",
            "source_batch": "v5-0_cycle",
            "macro_source": "Retail media networks market $24B (2025) growing to $34.7B by 2031. Amazon+Walmart capture 84% of ad spend, but 200+ named RMNs and 80% of top 100 retailers now operate networks. Technology partners make RMN accessible to retailers without Amazon-level resources. Digital retail ad spending $166B in 2025, growing 20% YoY — 5x faster than overall ad market.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 6, "VD": 5, "DV": 6},
                "composite": 0,
                "category": "",
                "rationale": "v5.0 cycle: Platform level locked (Amazon/Walmart 84%) but tech enablement layer open. 200+ RMNs need measurement, ad serving, audience tools. Low switching costs at tech layer (not at platform level). Moat from data network effects across multiple retailer clients."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Amazon/Walmart launch white-label RMN tooling for mid-market retailers, eliminating need for independent tech providers",
                "Retail media consolidates to <50 networks, reducing addressable market for enablement tools",
                "Major ad-tech players (The Trade Desk, Google) build turnkey RMN solutions that dominate the tech layer"
            ],
            "vcr_evidence": {
                "tam_estimate": "$2-4B by 2030 (tech enablement capturing 8-12% of $34.7B retail media market)",
                "capture_analysis": "Startup can win mid-market retailers (rank 10-100) who lack internal tech teams. Key: multi-retailer data advantage that improves targeting for each client.",
                "unit_economics": "SaaS + revenue share model. $50K-500K/year per retailer + 5-10% of incremental ad revenue. 70-80% gross margins.",
                "velocity_indicators": "Sales cycle 3-6 months for mid-market retailers. Pilot to full deployment 3-6 months. Fastest in grocery and specialty retail.",
                "moat_sources": "Cross-retailer data network effects, integration depth with retailer POS/inventory systems, measurement methodology standards."
            },
            "vcr": {
                "scores": {"MKT": 8.0, "CAP": 6.5, "ECO": 7.5, "VEL": 6.0, "MOA": 7.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 25.0,
                    "revenue_multiple": 12.0,
                    "exit_val_M": 300.0,
                    "seed_roi_multiple": 30.0
                },
                "rationale": "v5.0 cycle: RMN tech enablement. High TAM ($2-4B), good capture via network effects, strong unit economics (SaaS + rev share), moderate velocity (6-12mo sales cycle)."
            },
            "narrative_id": "TN-005",
            "role": "what_works",
            "parent_model": "MC-V38-44-003",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V50-ROBO-001",
            "name": "Industrial Robotics Integration Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "3339",
            "sector_name": "Other General Purpose Machinery Manufacturing",
            "architecture": "enabling_infrastructure",
            "forces_v3": ["F1_technology", "F2_demographics", "F4_capital"],
            "scores": {"SN": 8.5, "FA": 8.0, "EC": 7.0, "TG": 6.5, "CE": 6.5},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "FORCE_RIDER"],
            "one_liner": "Middleware platform connecting AI/ML models to industrial robotic hardware — providing deployment orchestration, safety certification, and fleet management for the $13.8B robotics startup ecosystem moving from digital AI into physical-world automation",
            "key_v3_context": "Physical AI robotics funding surged 77% to $13.8B in 2025 (exceeding 2021 peak). Capital rotating from digital AI into physical AI. Manufacturing/logistics sectors have acute labor shortages but high barriers to robotics deployment. This middleware layer solves integration complexity.",
            "source_batch": "v5-0_cycle",
            "macro_source": "Robotics startups raised $13.8B in 2025 (+77% YoY). Skild AI $1.4B at $14B valuation. RobCo $100M for autonomous industrial robotics. Capital rotating from digital to physical AI. US manufacturing: 600K+ unfilled positions. Construction: 650K unfilled positions. ABI Research: industrial robotics market $75.3B by 2030.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 5, "VD": 5, "DV": 5},
                "composite": 0,
                "category": "",
                "rationale": "v5.0 cycle: Middleware layer for robotics deployment is open — no dominant platform yet. Skild AI ($14B) focused on foundation models, not deployment orchestration. Manufacturing/logistics buyers are fragmented. Moat from hardware integration depth and safety certification data."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Major robotics OEMs (Fanuc, ABB, KUKA) build integrated deployment platforms that eliminate middleware need",
                "AI foundation model companies (Skild, Google DeepMind robotics) vertically integrate into deployment",
                "Industrial robotics deployment remains bespoke (no platform economics emerge)",
                "Manufacturing labor shortage resolves through immigration or wage increases"
            ],
            "vcr_evidence": {
                "tam_estimate": "$3-6B by 2030 (integration/middleware capturing 4-8% of $75.3B industrial robotics market)",
                "capture_analysis": "Startup advantage: neutral multi-OEM positioning (works with Fanuc AND ABB AND startups). Incumbent robotics companies have conflicting incentives to support competitors' hardware.",
                "unit_economics": "SaaS + deployment fee model. $100K-1M/year per factory + $20K-50K per robot deployment. 65-75% gross margins after platform built.",
                "velocity_indicators": "Sales cycle 6-12 months (manufacturing procurement). Pilot to production 6-12 months per facility. Fastest in automotive and electronics assembly.",
                "moat_sources": "Multi-OEM integration library (each robot model = 3-6 months engineering), safety certification data across deployments, factory floor digital twin data."
            },
            "vcr": {
                "scores": {"MKT": 8.5, "CAP": 5.5, "ECO": 5.0, "VEL": 4.5, "MOA": 7.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 30.0,
                    "revenue_multiple": 10.0,
                    "exit_val_M": 300.0,
                    "seed_roi_multiple": 30.0
                },
                "rationale": "v5.0 cycle: Physical AI middleware. High TAM, moderate capture (fragmented buyer base), moderate velocity (long manufacturing sales cycles)."
            },
            "narrative_id": "TN-003",
            "role": "whats_needed",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V50-AGENT-001",
            "name": "Enterprise Autonomous AI Agent Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5415",
            "sector_name": "Computer Systems Design and Related Services",
            "architecture": "platform",
            "forces_v3": ["F1_technology", "F4_capital", "F5_psychology"],
            "scores": {"SN": 9.0, "FA": 9.0, "EC": 7.5, "TG": 8.0, "CE": 7.0},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "TIMING_PLAY"],
            "one_liner": "Platform for deploying autonomous AI agents that execute multi-step business workflows end-to-end — beyond copilot/chat interfaces into agents that independently manage compliance review, code deployment, customer resolution, and financial reconciliation with human-in-the-loop guardrails",
            "key_v3_context": "Agentic AI emerging as dominant paradigm beyond chat/copilot. Claude Code, Devin, Cursor agent mode represent shift from human-directed to AI-directed workflows. Enterprise adoption accelerating. Distinct from V318-AGT-001 (which focuses on deployment infrastructure) — this model is the autonomous execution layer itself.",
            "source_batch": "v5-0_cycle",
            "macro_source": "AI coding market $7.37B (2025, up from $4.91B). 85% developers use AI tools. GitHub Copilot 20M users, 50K+ orgs. GPT-5.3-Codex 'instrumental in creating itself.' Agentic AI distinct category: autonomous multi-step task execution. Enterprise adoption: agents managing deployment pipelines, compliance, customer service. Gartner: 90% enterprise engineers using AI coding by 2028.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 5, "VD": 6, "DV": 6},
                "composite": 0,
                "category": "",
                "rationale": "v5.0 cycle: Agentic AI market is nascent — no dominant platform yet. OpenAI (Frontier), Anthropic (Claude Code), Google (agents) are building foundation-level agents but enterprise orchestration/deployment layer is open. High value density (agents replace $200K+ knowledge workers). Competition from foundation model companies but enterprise needs are distinct."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Foundation model companies (OpenAI, Anthropic, Google) vertically integrate into enterprise agent deployment, eliminating platform layer",
                "Enterprise AI adoption stalls due to trust/liability concerns — agents remain demo-only",
                "Autonomous agent reliability remains below enterprise requirements (>99.5% accuracy) for 3+ years",
                "Enterprise customers prefer building agents internally over using platforms"
            ],
            "vcr_evidence": {
                "tam_estimate": "$8-15B by 2030 (enterprise agent platforms capturing 5-10% of $100B+ enterprise AI market)",
                "capture_analysis": "First-mover advantage critical. Winner captures enterprise workflows that become mission-critical (compliance, deployment, financial ops). High switching costs once agents trained on company data/processes.",
                "unit_economics": "SaaS + usage-based pricing. $50K-500K/year per enterprise + per-agent-execution fees. 70-85% gross margins. AI infrastructure costs declining 30-50% annually.",
                "velocity_indicators": "Sales cycle 3-9 months for tech enterprises. Longer (9-18 months) for regulated industries. Developer adoption bottom-up (like GitHub Copilot) is fastest path.",
                "moat_sources": "Agent training on enterprise-specific workflows, compliance/audit trail data, multi-system integration depth, safety/guardrail frameworks that enterprises trust."
            },
            "vcr": {
                "scores": {"MKT": 9.0, "CAP": 6.0, "ECO": 7.0, "VEL": 7.0, "MOA": 7.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 50.0,
                    "revenue_multiple": 15.0,
                    "exit_val_M": 750.0,
                    "seed_roi_multiple": 75.0
                },
                "rationale": "v5.0 cycle: Enterprise autonomous AI agents. Very high TAM, strong capture via workflow lock-in, good velocity (developer-led adoption), strong moat from enterprise data training."
            },
            "narrative_id": "TN-010",
            "role": "what_works",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V50-DEF-001",
            "name": "Defense AI Software Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "9281",
            "sector_name": "National Security and International Affairs",
            "architecture": "vertical_saas",
            "forces_v3": ["F1_technology", "F3_geopolitics", "F4_capital"],
            "scores": {"SN": 8.0, "FA": 8.5, "EC": 9.0, "TG": 7.0, "CE": 6.5},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "FORCE_RIDER"],
            "one_liner": "Vertical SaaS platform for defense mission planning, intelligence analysis, and training simulation — the software layer carved out from locked defense platform models, targeting the $7.7B defense tech VC ecosystem where Anduril ($30.5B), Saronic ($600M), and Helsing ($694M) prove startup viability",
            "key_v3_context": "Defense VC funding doubled to $7.7B in 2025. Software/AI defense layer is accessible to startups despite platform/procurement layers being locked. This is a decomposition carve-out: parent defense models (V3-DEF-002, V3-DEF-004) score high T but low O at platform level. This model captures the accessible software layer.",
            "source_batch": "v5-0_cycle",
            "macro_source": "Defense tech startup VC $7.7B across ~100 deals in 2025 (Crunchbase), 2x prior year. CB Insights: $17.9B equity funding. Anduril $2.5B Series G at $30.5B. Saronic $600M Series C. Helsing $694M. Manufacturing defense $4.7B across 39 deals. Pentagon budget: $886B FY2025, AI/autonomous systems prioritized.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 5, "MA": 5, "VD": 6, "DV": 5},
                "composite": 0,
                "category": "",
                "rationale": "v5.0 cycle: Defense software layer accessible (proven by $7.7B VC). But procurement cycle 18-36 months, ITAR restrictions, security clearance requirements limit pool. Moat from classified data access and compliance frameworks. Higher O than parent defense models because software layer avoids worst procurement barriers."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Major defense primes (Lockheed, Raytheon, Northrop) build competitive internal AI platforms that lock out startups",
                "DoD procurement reforms stall — SBIR/STTR remains the only path for startups",
                "Security clearance bottleneck prevents startups from accessing classified programs",
                "Defense budget cuts reduce AI/autonomous systems funding below $5B annually"
            ],
            "vcr_evidence": {
                "tam_estimate": "$3-5B by 2030 (software platform layer of defense AI, excluding hardware/munitions)",
                "capture_analysis": "Startup can capture mission planning / intelligence analysis niches. Key: Anduril proves defense startups can scale. But requires clearances, compliance, patient capital.",
                "unit_economics": "Contract-based + SaaS hybrid. $1-10M per program + recurring license. 50-65% gross margins (lower than pure SaaS due to compliance overhead). Government contract terms are favorable for recurring revenue.",
                "velocity_indicators": "Sales cycle 12-24 months (defense procurement). Pilot to production 12-18 months. Fastest path: SBIR/STTR to SOCOM/JSOC for rapid acquisition programs.",
                "moat_sources": "Classified data access (SCIF-compatible), ITAR/EAR compliance frameworks, cleared engineering team, existing program of record relationships."
            },
            "vcr": {
                "scores": {"MKT": 8.0, "CAP": 3.5, "ECO": 6.0, "VEL": 3.0, "MOA": 8.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 20.0,
                    "revenue_multiple": 8.0,
                    "exit_val_M": 160.0,
                    "seed_roi_multiple": 16.0
                },
                "rationale": "v5.0 cycle: Defense AI software. High TAM but low capture rate (clearances, procurement). Slow velocity (12-24mo sales). Strong moat from classified access. VCR penalized by defense procurement friction."
            },
            "narrative_id": "TN-008",
            "role": "what_works",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        }
    ]

    # Calculate composites for new models
    for nm in new_models:
        nm["composite"] = calc_t_composite(nm["scores"])
        nm["cla"]["composite"] = calc_cla_composite(nm["cla"]["scores"])
        nm["cla"]["category"] = cla_category(nm["cla"]["composite"])
        nm["vcr"]["composite"] = calc_vcr_composite(nm["vcr"]["scores"])
        nm["vcr"]["category"] = vcr_category(nm["vcr"]["composite"])
        models.append(nm)
        print("  NEW: {} ({}) T={} O={} [{}] VCR={} [{}]".format(
            nm["id"], nm["name"], nm["composite"],
            nm["cla"]["composite"], nm["cla"]["category"],
            nm["vcr"]["composite"], nm["vcr"]["category"]))

    # Save
    data["models"] = models
    with open(MODELS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print("\nTotal models: {}".format(len(models)))
    print("Written: {}".format(MODELS_FILE))

    return {
        "adjustments_applied": adjustments_applied,
        "new_models": len(new_models),
        "total_models": len(models)
    }

if __name__ == "__main__":
    run()
