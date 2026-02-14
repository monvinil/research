#!/usr/bin/env python3
"""v5.1 Cycle 1 Applier — applies Agent C graded score adjustments and creates new models.

Reads: data/graded/v5-1_graded_2026-02-13.json
Modifies: data/v4/models.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_FILE = ROOT / "data" / "v4" / "models.json"
GRADED_FILE = ROOT / "data" / "graded" / "v5-1_graded_2026-02-13.json"

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
            "id": "MC-V51-VOICE-001",
            "name": "Enterprise AI Voice Agent Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5614",
            "sector_name": "Business Support Services",
            "architecture": "vertical_saas",
            "forces_v3": ["F1_technology", "F4_capital", "F2_demographics"],
            "scores": {"SN": 8.5, "FA": 8.0, "EC": 7.5, "TG": 8.0, "CE": 7.5},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "FORCE_RIDER"],
            "one_liner": "Enterprise platform replacing IVR and human contact center agents with AI voice agents that handle inbound/outbound calls end-to-end — scheduling, billing inquiries, claims processing, and appointment reminders across BFSI (32.9% of market), healthcare, and hospitality verticals with per-call/per-minute pricing",
            "key_v3_context": "Conversational AI market $19.21B (2025) growing to $132.86B by 2034. Voice AI VC grew 7x from $315M (2022) to $2.1B (2024). ElevenLabs $3.3B valuation, Giga $61M raise, VoiceRun $5.5M seed. Distinct from chat/copilot agents (MC-V50-AGENT-001) — voice agents have different latency requirements, telephony integration, and per-interaction economics.",
            "source_batch": "v5-1_cycle",
            "macro_source": "Conversational AI market $19.21B (2025) to $132.86B by 2034. Voice AI VC $2.1B in 2024 (7x in 2yr). ElevenLabs $180M Series C at $3.3B. Giga $61M for enterprise voice automation. VoiceRun $5.5M seed. BFSI leads 32.9%. Gartner: $80B contact center cost reduction from AI voice. Clients: Marriott, Caesars. North America 40%+ market share.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 5, "VD": 7, "DV": 6},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: Voice AI market nascent with no dominant platform. ElevenLabs focused on voice synthesis, not end-to-end enterprise deployment. High value density: each voice agent replaces $40-60K/yr human agent. Competition fragmenting across verticals (healthcare vs BFSI vs hospitality). Moat from vertical-specific training data and telephony integration depth."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Major cloud providers (AWS Connect, Google CCAI, Azure) build turnkey voice agent solutions that dominate enterprise adoption",
                "Voice AI accuracy remains below 95% for complex multi-turn conversations, limiting enterprise trust",
                "Contact center labor costs decrease (immigration, remote work) removing cost pressure for automation",
                "Enterprise buyers prefer text-based AI agents over voice for cost/reliability reasons"
            ],
            "vcr_evidence": {
                "tam_estimate": "$5-10B by 2030 (enterprise voice AI capturing 3-6% of $132.86B conversational AI market)",
                "capture_analysis": "Vertical specialization is the moat — healthcare voice agents need HIPAA compliance + medical terminology, BFSI needs PCI compliance + financial product knowledge. Horizontal players can't match vertical depth.",
                "unit_economics": "Per-call/per-minute pricing. $0.10-0.50/call vs $5-15/call for human agents. 80-90% gross margins. Revenue scales with call volume, not seats.",
                "velocity_indicators": "Sales cycle 3-6 months for mid-market, 6-12 months for enterprise. Pilot to production 2-4 weeks (faster than text agents). Fastest in healthcare (appointment reminders) and hospitality (reservations).",
                "moat_sources": "Vertical training data (millions of domain-specific calls), telephony infrastructure integration, sub-500ms latency engineering, regulatory compliance frameworks (HIPAA, PCI)."
            },
            "vcr": {
                "scores": {"MKT": 9.0, "CAP": 6.5, "ECO": 7.5, "VEL": 7.0, "MOA": 6.5},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 40.0,
                    "revenue_multiple": 14.0,
                    "exit_val_M": 560.0,
                    "seed_roi_multiple": 56.0
                },
                "rationale": "v5.1 cycle: Enterprise voice AI. Very high TAM, strong capture via vertical specialization, excellent unit economics (per-call vs per-seat), good velocity (quick pilots). Moat from vertical training data."
            },
            "narrative_id": "TN-010",
            "role": "what_works",
            "confidence_tier": "HIGH",
            "evidence_quality": 8
        },
        {
            "id": "MC-V51-SYNTH-001",
            "name": "Domain-Specific Synthetic Data Generation Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5112",
            "sector_name": "Software Publishers",
            "architecture": "data_compounding",
            "forces_v3": ["F1_technology", "F4_capital"],
            "scores": {"SN": 8.0, "FA": 7.5, "EC": 7.0, "TG": 7.0, "CE": 7.0},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "FORCE_RIDER"],
            "one_liner": "Platform generating high-fidelity domain-specific synthetic data for AI model training — healthcare records (HIPAA-compliant), financial transactions (PCI-compliant), manufacturing sensor data, and autonomous vehicle scenarios where real data is scarce, expensive, or privacy-restricted",
            "key_v3_context": "Synthetic data projected 70% of AI training data by 2030 (up from 20% in 2025). TAM $60-90B through 2030. Synthesia crossed $100M ARR at $4B valuation. Enterprises pay $500K-$5M/yr for domain-specific datasets. Domain expertise + regulatory compliance (HIPAA/GDPR) = moat that hyperscalers lack.",
            "source_batch": "v5-1_cycle",
            "macro_source": "Synthetic data generation 70% of AI training by 2030 (from 20% in 2025). Specialized synthetic data TAM $60-90B by 2030. Synthesia $100M+ ARR at $4B. Enterprises paying $500K-$5M/yr. Domain expertise + HIPAA/GDPR compliance = competitive moat. Model-guided synthetic data emerging as key technique in 2026.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 6, "VD": 6, "DV": 5},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: Market open — no dominant horizontal player. Synthesia focused on video, not training data. Domain expertise is the moat: healthcare synthetic data requires clinical knowledge + HIPAA expertise. Moderate value density — data is consumable, not SaaS (usage-based pricing). Competition from hyperscalers on commodity data but NOT on domain-specific regulated data."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Foundation model companies generate sufficient synthetic data internally, eliminating need for third-party providers",
                "Regulatory frameworks restrict synthetic data use in sensitive domains (healthcare, finance)",
                "Real data becomes more accessible through federated learning or privacy-preserving techniques, reducing synthetic data demand",
                "Quality gap between synthetic and real data persists, preventing enterprise adoption for critical applications"
            ],
            "vcr_evidence": {
                "tam_estimate": "$4-8B by 2030 (domain-specific synthetic data capturing 5-10% of $60-90B TAM)",
                "capture_analysis": "Domain specialization creates defensible niches — a healthcare synthetic data company can't easily pivot to manufacturing sensor data. Winner-take-most within each vertical.",
                "unit_economics": "Usage-based pricing. $500K-$5M/yr per enterprise customer. 70-80% gross margins (compute-intensive but high-value). Revenue scales with customer AI training budgets.",
                "velocity_indicators": "Sales cycle 3-6 months for mid-market. POC to production 1-3 months. Fastest in healthcare and autonomous vehicles where real data scarcity is acute.",
                "moat_sources": "Domain expertise (clinical knowledge, financial patterns), regulatory compliance frameworks, proprietary generation models trained on domain-specific distributions, quality validation methodology."
            },
            "vcr": {
                "scores": {"MKT": 9.0, "CAP": 6.0, "ECO": 6.5, "VEL": 6.0, "MOA": 6.5},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 25.0,
                    "revenue_multiple": 12.0,
                    "exit_val_M": 300.0,
                    "seed_roi_multiple": 30.0
                },
                "rationale": "v5.1 cycle: Domain-specific synthetic data. Very high TAM, moderate capture (domain expertise moat), good unit economics, moderate velocity. Moat from regulatory compliance + domain knowledge."
            },
            "narrative_id": "TN-001",
            "role": "whats_needed",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V51-AISAFE-001",
            "name": "AI Safety & Compliance Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5415",
            "sector_name": "Computer Systems Design and Related Services",
            "architecture": "vertical_saas",
            "forces_v3": ["F1_technology", "F3_geopolitics", "F5_psychology"],
            "scores": {"SN": 9.0, "FA": 7.5, "EC": 8.0, "TG": 8.5, "CE": 7.5},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER", "TIMING_PLAY"],
            "one_liner": "Platform providing automated AI model red-teaming, bias detection, risk assessment, and regulatory compliance documentation for enterprises deploying AI under EU AI Act (penalties up to 7% global turnover) and emerging US state-level AI regulations — the GDPR-compliance-tooling equivalent for the AI era",
            "key_v3_context": "EU AI Act fully applicable August 2, 2026 for high-risk AI systems. Penalties: up to EUR 35M or 7% global annual turnover. Insurers now requiring documented adversarial red-teaming as prerequisite for underwriting. 175+ AI security startups funded. Mandatory demand driver (not optional adoption) — similar to GDPR creating cybersecurity compliance market.",
            "source_batch": "v5-1_cycle",
            "macro_source": "EU AI Act: fully applicable Aug 2, 2026 for high-risk systems. Penalties: EUR 35M / 7% global turnover. Insurers requiring red-teaming documentation. 175+ AI security startups funded. Code of Practice requires adversarial testing. US state-level AI regulation accelerating. Mandatory compliance = structural necessity above normal F1 signal.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 8, "MA": 5, "VD": 7, "DV": 6},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: Market wide open — no dominant AI compliance platform yet. Regulatory deadline (Aug 2026) creates urgent mandatory demand. 175+ startups means market fragmented. Moat from compliance framework depth and regulatory relationship (similar to OneTrust in GDPR). High value density: non-compliance costs EUR 35M+."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "EU AI Act enforcement is weak/delayed — penalties rarely applied, reducing urgency",
                "Foundation model companies (OpenAI, Anthropic, Google) build comprehensive safety tooling that enterprises use directly",
                "AI regulation fragments so badly across jurisdictions that no platform can cover requirements",
                "Manual compliance (law firms + consultants) remains preferred over automated tooling"
            ],
            "vcr_evidence": {
                "tam_estimate": "$3-6B by 2030 (AI compliance/safety capturing 2-4% of broader AI governance market)",
                "capture_analysis": "First-mover advantage critical — regulatory compliance tools become embedded in enterprise workflows. OneTrust precedent: GDPR compliance startup to $5.3B valuation.",
                "unit_economics": "SaaS pricing. $50K-500K/yr per enterprise. 80-90% gross margins. Pricing power from regulatory mandate (compliance not optional).",
                "velocity_indicators": "Sales cycle 3-6 months (accelerating as Aug 2026 deadline approaches). Enterprise urgency high. Fastest: financial services and healthcare (already compliance-oriented cultures).",
                "moat_sources": "Regulatory framework expertise across jurisdictions (EU AI Act + US state laws + sector-specific), compliance documentation standards, red-teaming methodology library, audit trail data across deployments."
            },
            "vcr": {
                "scores": {"MKT": 8.0, "CAP": 7.0, "ECO": 8.0, "VEL": 7.5, "MOA": 6.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 35.0,
                    "revenue_multiple": 14.0,
                    "exit_val_M": 490.0,
                    "seed_roi_multiple": 49.0
                },
                "rationale": "v5.1 cycle: AI safety/compliance. Strong TAM with regulatory tailwind, high capture (mandatory demand), excellent unit economics, fast velocity (deadline-driven). OneTrust parallel: GDPR compliance created $5B+ company."
            },
            "narrative_id": "TN-010",
            "role": "whats_needed",
            "confidence_tier": "HIGH",
            "evidence_quality": 8
        },
        {
            "id": "MC-V51-LLMOPS-001",
            "name": "LLMOps & AI Agent Observability Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "5415",
            "sector_name": "Computer Systems Design and Related Services",
            "architecture": "enabling_infrastructure",
            "forces_v3": ["F1_technology", "F4_capital"],
            "scores": {"SN": 8.0, "FA": 7.5, "EC": 7.0, "TG": 7.5, "CE": 6.5},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER"],
            "one_liner": "Platform providing monitoring, evaluation, cost tracking, and governance for LLM-powered applications and AI agents in production — the Datadog/New Relic equivalent for the AI agent era, tracking prompt quality, model drift, hallucination rates, and compliance across enterprise AI deployments",
            "key_v3_context": "WitnessAI closed $58M for enterprise AI security/governance. LangWatch EUR 1M pre-seed for LLMOps monitoring. Arize AI and W&B expanding into LLM observability. As AI agents proliferate (40% enterprise apps by 2026 — Gartner), monitoring/governance becomes critical infrastructure. Similar pattern to APM (application performance monitoring) market which produced Datadog ($40B+).",
            "source_batch": "v5-1_cycle",
            "macro_source": "WitnessAI $58M for AI security/governance. LangWatch EUR 1M pre-seed. Arize AI expanding into LLM observability. W&B Weave for LLM monitoring. Gartner: 40% enterprise apps agentic by 2026. Trust/observability funding surging as AI scales from cloud to edge. APM precedent: Datadog $40B+.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 7, "MA": 5, "VD": 5, "DV": 6},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: LLMOps market early but opening fast. No dominant player yet (Datadog, Weights & Biases, and startups all competing). APM companies (Datadog, New Relic) have adjacent capability but lack LLM-specific depth. Moderate moat from integration depth and evaluation methodology. Lower value density than APM (AI budgets still growing)."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Major APM companies (Datadog, New Relic, Splunk) build comprehensive LLM observability that commoditizes startup offerings",
                "Cloud providers (AWS, Azure, GCP) bundle LLM monitoring into their AI platforms at no additional cost",
                "AI agent adoption stalls — fewer production AI systems means less monitoring demand",
                "Open-source LLM observability tools (LangSmith, Phoenix) become good enough for enterprise needs"
            ],
            "vcr_evidence": {
                "tam_estimate": "$3-5B by 2030 (LLMOps observability as subset of $15B+ AI infrastructure monitoring market)",
                "capture_analysis": "Startup advantage: purpose-built for LLM/agent monitoring (not retrofitted APM). Risk: Datadog enters aggressively. Winner needs to establish standard before incumbent catch-up.",
                "unit_economics": "Usage-based pricing (per trace/per evaluation). $20K-200K/yr per enterprise. 75-85% gross margins. Revenue scales with AI deployment volume.",
                "velocity_indicators": "Sales cycle 1-3 months (developer-led adoption, PLG model). Quick time-to-value (install SDK, see traces immediately). Fastest: tech companies already deploying LLMs.",
                "moat_sources": "Integration depth across LLM providers (OpenAI, Anthropic, Google, open-source), evaluation methodology (hallucination detection, prompt quality scoring), historical trace data for drift detection."
            },
            "vcr": {
                "scores": {"MKT": 8.0, "CAP": 6.0, "ECO": 6.5, "VEL": 7.5, "MOA": 5.5},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 20.0,
                    "revenue_multiple": 15.0,
                    "exit_val_M": 300.0,
                    "seed_roi_multiple": 30.0
                },
                "rationale": "v5.1 cycle: LLMOps/AI observability. Good TAM with Datadog precedent, moderate capture (incumbent risk from APM players), good unit economics, fast velocity (PLG). Moderate moat."
            },
            "narrative_id": "TN-010",
            "role": "whats_needed",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V51-DRONE-001",
            "name": "Commercial Drone Inspection & Delivery Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "4885",
            "sector_name": "Freight Transportation Arrangement",
            "architecture": "platform",
            "forces_v3": ["F1_technology", "F4_capital", "F3_geopolitics"],
            "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 6.5, "CE": 7.0},
            "composite": 0,
            "composite_stated": None,
            "category": ["FORCE_RIDER", "TIMING_PLAY"],
            "one_liner": "Platform for commercial drone operations — last-mile delivery (medical supplies, retail packages), infrastructure inspection (power lines, pipelines, cell towers), and precision agriculture aerial services — capturing the accessible commercial layer distinct from military drone command platforms",
            "key_v3_context": "Zipline raised $600M at $7.6B valuation, surpassed 2M commercial drone deliveries. Dronamics $58M for cargo drones. Voltair builds power-line-charging inspection drones (infinite range). Total drone startup funding >$2B. Regulatory progress enabling wider commercial deployment. Distinct from V3-DEF-001 (military drone swarm command) — commercial layer is accessible.",
            "source_batch": "v5-1_cycle",
            "macro_source": "Zipline $600M at $7.6B valuation, 2M+ deliveries, expanding to 4+ US states in 2026. Dronamics $58M ($200M valuation) for cargo drones. Voltair infinite-range power-line drones. Matternet $74M medical supply delivery. Total drone startup funding >$2B. Commercial drone market $25.24B. Regulatory progress enabling deployment.",
            "rank": None,
            "primary_category": "FORCE_RIDER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 6, "MA": 5, "VD": 5, "DV": 5},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: Commercial drone market accessible but capital-intensive for delivery (Zipline model). Inspection is more accessible (software + standard drone hardware). No dominant platform for multi-use commercial operations. Regulatory risk remains (FAA BVLOS rules still evolving). Moat from regulatory relationships and operational data."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "FAA BVLOS regulations remain restrictive for 3+ years, limiting commercial deployment",
                "Amazon/UPS/FedEx build proprietary drone delivery networks that lock out third-party platforms",
                "Drone hardware commoditizes without platform economics emerging (each operator builds custom)",
                "Ground-based autonomous delivery (robots) proves more economical for last-mile"
            ],
            "vcr_evidence": {
                "tam_estimate": "$2-4B by 2030 (commercial drone operations platform capturing 8-15% of $25.24B market)",
                "capture_analysis": "Platform opportunity: coordinate drone fleets across inspection + delivery + agriculture use cases. Zipline model is vertically integrated (hardware + operations) — platform play would aggregate heterogeneous fleets.",
                "unit_economics": "Per-flight/per-inspection pricing. $5-50/flight for delivery, $200-2000/inspection for infrastructure. 50-65% gross margins (hardware depreciation + operations overhead). Revenue scales with flight volume.",
                "velocity_indicators": "Sales cycle 3-6 months for enterprise inspection. Faster for healthcare delivery (urgent need + regulatory support). Regulatory timeline is key constraint (FAA BVLOS).",
                "moat_sources": "FAA operating certificates (BVLOS waivers), airspace management data, fleet coordination algorithms, customer-specific flight corridor data, safety/compliance track record."
            },
            "vcr": {
                "scores": {"MKT": 7.5, "CAP": 5.5, "ECO": 5.5, "VEL": 5.0, "MOA": 6.5},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 15.0,
                    "revenue_multiple": 10.0,
                    "exit_val_M": 150.0,
                    "seed_roi_multiple": 15.0
                },
                "rationale": "v5.1 cycle: Commercial drone ops. Good TAM, moderate capture (regulatory moat), moderate economics (hardware costs), slower velocity (regulatory dependency). Zipline precedent: $7.6B."
            },
            "narrative_id": "TN-003",
            "role": "what_works",
            "confidence_tier": "MEDIUM",
            "evidence_quality": 7
        },
        {
            "id": "MC-V51-GOVAI-001",
            "name": "AI-Powered Government Procurement Platform",
            "v2_score": None,
            "v2_rank": None,
            "sector_naics": "9211",
            "sector_name": "Executive, Legislative, and Other General Government Support",
            "architecture": "vertical_saas",
            "forces_v3": ["F1_technology", "F3_geopolitics", "F4_capital"],
            "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.5, "TG": 6.5, "CE": 7.0},
            "composite": 0,
            "composite_stated": None,
            "category": ["STRUCTURAL_WINNER"],
            "one_liner": "Vertical SaaS platform automating the full government procurement lifecycle — requirements generation, market research, solicitation drafting, proposal evaluation, and vendor management — replacing manual 6-12 month RFP processes with AI-driven automation for state, local, and federal agencies",
            "key_v3_context": "Starbridge raised $42M ($10M seed + $32M Series A from Craft Ventures) for AI procurement. OpenGov agreed to sell at $1.8B valuation. PermitFlow $31M for government permit automation. GovTech Series A progression rate up 30% (18%→23%). Average GovTech investment $15.2M/round. Hazel AI automates full procurement lifecycle.",
            "source_batch": "v5-1_cycle",
            "macro_source": "Starbridge $42M for procurement AI (Craft Ventures lead). OpenGov $1.8B valuation (Cox Enterprises). PermitFlow $31M Series A. CHAMP Titles $55M. GovTech Series A rate up 30%. Average investment $15.2M/round across 1,180+ rounds. Hazel AI automates procurement for state/local/federal.",
            "rank": None,
            "primary_category": "STRUCTURAL_WINNER",
            "new_in_v36": False,
            "cla": {
                "scores": {"MO": 6, "MA": 6, "VD": 6, "DV": 5},
                "composite": 0,
                "category": "",
                "rationale": "v5.1 cycle: GovTech procurement accessible — proven by Starbridge $42M and OpenGov $1.8B. But government sales cycles long (12-24 months), and procurement compliance requirements create barriers to entry. Moat from regulatory understanding + agency relationships. Higher moat than typical SaaS because government buyers are sticky and trust-sensitive."
            },
            "deep_dive_evidence": None,
            "falsification_criteria": [
                "Government procurement reform stalls — agencies continue using legacy processes and manual RFPs",
                "Major enterprise software companies (SAP Ariba, Coupa) add AI procurement features that government agencies adopt",
                "Government budget constraints reduce IT spending, delaying AI procurement tool adoption",
                "Security/compliance requirements for government AI tools become prohibitively expensive for startups (FedRAMP, etc.)"
            ],
            "vcr_evidence": {
                "tam_estimate": "$2-4B by 2030 (AI procurement capturing 3-5% of $80B+ government procurement technology market)",
                "capture_analysis": "Vertical specialization for government buyers. Enterprise procurement tools (Coupa, SAP) don't understand government-specific compliance (FAR, DFARS). Starbridge and OpenGov prove market is real.",
                "unit_economics": "SaaS + usage-based pricing. $50K-300K/yr per agency. 75-85% gross margins. Government contracts are multi-year (predictable revenue). Retention high (switching costs + trust + compliance).",
                "velocity_indicators": "Sales cycle 12-24 months for federal, 6-12 months for state/local. Long but predictable. Once sold, contract lengths 3-5 years. GovTech Fund and dedicated investors accelerate ecosystem.",
                "moat_sources": "Government compliance frameworks (FAR, DFARS, state procurement codes), FedRAMP authorization, agency relationships and trust, procurement domain expertise, contract vehicle positioning."
            },
            "vcr": {
                "scores": {"MKT": 7.5, "CAP": 5.5, "ECO": 6.5, "VEL": 4.5, "MOA": 7.0},
                "composite": 0,
                "category": "",
                "roi_estimate": {
                    "year5_revenue_M": 15.0,
                    "revenue_multiple": 10.0,
                    "exit_val_M": 150.0,
                    "seed_roi_multiple": 15.0
                },
                "rationale": "v5.1 cycle: GovTech procurement AI. Good TAM, moderate capture (long sales cycles), good economics (sticky government contracts), slow velocity (12-24mo sales). Strong moat from compliance + relationships. OpenGov $1.8B precedent."
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
