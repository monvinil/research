#!/usr/bin/env python3
"""
v3-18 Model Generation: ~45 new models across 3 clusters.

Cluster A: Architecture Gap Models (3 new architecture types)
  - open_core_ecosystem (8 models)
  - outcome_based (6 models)
  - coordination_protocol (5 models)

Cluster B: Sector Gap Models (thin sectors)
  - Wholesale Trade 42 (5 models)
  - Arts/Entertainment 71 (4 models)
  - Utilities 22 (3 models)

Cluster C: Emerging Pattern Models
  - Agent-as-a-Service (3 models)
  - Human-Premium Verified (3 models)
  - Synthetic Media (2 models)
  - Temporal Extraction (3 models)

Each model gets T-scores, CLA (heuristic), VCR (heuristic), EQ, confidence tier.
"""

import json
import statistics
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"


def make_model(mid, name, sector_naics, sector_name, architecture, one_liner,
               scores, forces, primary_category, categories=None, eq=5,
               confidence_tier="MODERATE"):
    """Build a complete model dict matching normalized file structure."""
    sn, fa, ec, tg, ce = scores
    composite = round((sn * 25 + fa * 25 + ec * 20 + tg * 15 + ce * 15) / 10, 2)
    return {
        "id": mid,
        "name": name,
        "sector_naics": sector_naics,
        "sector_name": sector_name,
        "architecture": architecture,
        "one_liner": one_liner,
        "scores": {"SN": sn, "FA": fa, "EC": ec, "TG": tg, "CE": ce},
        "composite": composite,
        "rank": 0,  # will be set after merge
        "category": categories or [primary_category],
        "primary_category": primary_category,
        "forces_v3": forces,
        "evidence_quality": eq,
        "confidence_tier": confidence_tier,
        "source_batch": "v3-18_gap_fill",
        "new_in_v36": False,
        "falsification_criteria": [],
        "deep_dive_evidence": None,
        "polanyi": None,  # will be enriched by sector proxy
        # Placeholder CLA and VCR — will be scored by heuristic
        "cla": {
            "scores": {"MO": 5, "MA": 5, "VD": 5, "DV": 5},
            "composite": 50.0,
            "category": "CONTESTED",
            "rationale": "v3-18 heuristic pending"
        },
        "vcr": {
            "scores": {"MKT": 5, "CAP": 5, "ECO": 5, "VEL": 5, "MOA": 5},
            "composite": 50.0,
            "category": "VIABLE_RETURN",
            "roi_estimate": {
                "year5_revenue_M": 10,
                "revenue_multiple": 5,
                "exit_val_M": 50,
                "seed_roi_multiple": 5.0
            },
            "rationale": "v3-18 heuristic pending"
        },
        "opportunity_rank": 0,
        "vcr_rank": 0,
    }


# ═══════════════════════════════════════════════════════════════
# CLUSTER A: Architecture Gap Models
# ═══════════════════════════════════════════════════════════════

CLUSTER_A = [
    # ── open_core_ecosystem (8 models) ──
    make_model(
        "V318-OCE-001", "Open-Source AI Inference Platform",
        "5112", "Software Publishers", "open_core_ecosystem",
        "Free inference server (vLLM/TGI pattern) → managed hosting + enterprise SLA + model management. $12B inference market by 2028; Red Hat pattern for AI infrastructure.",
        (7.5, 8.0, 7.0, 8.0, 7.5), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=5, confidence_tier="MODERATE"
    ),
    make_model(
        "V318-OCE-002", "Open-Source DevOps + Incident Management",
        "5415", "Computer Systems Design", "open_core_ecosystem",
        "Free incident response platform → enterprise observability suite + on-call automation. $40B observability market; PagerDuty + Grafana pattern.",
        (6.0, 7.5, 6.5, 7.5, 7.0), ["F1_technology"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-OCE-003", "Open-Source AI Compliance Framework",
        "5416", "Management/Scientific Consulting", "open_core_ecosystem",
        "Free AI governance toolkit → paid audit certification + continuous monitoring. EU AI Act (Dec 2027) creates $8B+ compliance market; no open standard exists.",
        (8.0, 8.5, 8.5, 7.0, 6.0), ["F1_technology", "F3_geopolitics", "F5_psychology"],
        "STRUCTURAL_WINNER", categories=["STRUCTURAL_WINNER", "FEAR_ECONOMY"], eq=5
    ),
    make_model(
        "V318-OCE-004", "Open-Source Agent Orchestration Framework",
        "5112", "Software Publishers", "open_core_ecosystem",
        "Free multi-agent framework → managed execution + monitoring + billing layer. Agent adoption 5%→40% in 12 months; LangChain/CrewAI pattern but with commercial capture.",
        (8.5, 8.5, 7.0, 9.0, 7.0), ["F1_technology", "F4_capital"],
        "STRUCTURAL_WINNER", eq=5
    ),
    make_model(
        "V318-OCE-005", "Open-Source Healthcare Data Interoperability",
        "6211", "Offices of Physicians", "open_core_ecosystem",
        "Free FHIR/HL7 integration toolkit → certified data exchange + EHR bridge SaaS. 21.3M healthcare workers, 900K physician offices; CMS interoperability mandate.",
        (5.5, 7.0, 8.0, 5.5, 6.0), ["F1_technology", "F2_demographics"],
        "CONDITIONAL", eq=4
    ),
    make_model(
        "V318-OCE-006", "Open-Source Manufacturing Quality Vision",
        "3344", "Semiconductor Manufacturing Equipment", "open_core_ecosystem",
        "Free computer vision QC models → managed deployment + defect analytics + compliance. 350K manufacturing establishments; 78% on spreadsheets (P-041 bimodality).",
        (7.0, 7.5, 6.5, 6.5, 5.5), ["F1_technology", "F2_demographics"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-OCE-007", "Open-Source Financial Data Protocol",
        "5231", "Securities/Commodity Contracts", "open_core_ecosystem",
        "Free market data normalization → premium analytics + compliance feeds. Inverse Baumol confirmed in securities (56% wage deceleration); data standardization is precondition.",
        (6.5, 7.0, 6.0, 7.0, 7.5), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=4
    ),
    make_model(
        "V318-OCE-008", "Open-Source Education Assessment Platform",
        "6111", "Elementary/Secondary Schools", "open_core_ecosystem",
        "Free AI-powered assessment tools → school district licensing + analytics dashboard. Highest fear friction sector (gap=5); trust through transparency is the only path.",
        (4.5, 6.0, 7.0, 4.0, 5.0), ["F1_technology", "F5_psychology"],
        "CONDITIONAL", categories=["CONDITIONAL", "FEAR_ECONOMY"], eq=4
    ),

    # ── outcome_based (6 models) ──
    make_model(
        "V318-OB-001", "Outcome-Based Accounting Automation",
        "5412", "Accounting/Tax/Bookkeeping", "outcome_based",
        "AI-automated bookkeeping charging 15% of cost savings vs human CPA baseline. Inverse Baumol: accounting wages decelerating 56% YoY; savings quantifiable per engagement.",
        (7.0, 8.0, 6.5, 7.5, 8.0), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-OB-002", "Outcome-Based Supply Chain Optimization",
        "4231", "Motor Vehicle Parts Wholesale", "outcome_based",
        "AI procurement optimization charging % of spend reduction. $6T US wholesale; 3-8% typical procurement savings = $180-480B addressable.",
        (6.0, 7.0, 6.0, 6.5, 7.0), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=4
    ),
    make_model(
        "V318-OB-003", "Outcome-Based Energy Efficiency",
        "2211", "Electric Power Generation", "outcome_based",
        "AI building energy optimization charging % of utility savings. 133% data center electricity growth; energy costs are #1 opex for data centers, savings directly measurable.",
        (6.5, 8.0, 7.5, 6.0, 6.5), ["F1_technology", "F6_energy"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-OB-004", "Outcome-Based Healthcare Denial Management",
        "6211", "Offices of Physicians", "outcome_based",
        "AI prior-auth + denial reversal charging % of recovered revenue. $260B annual denied claims; 65% appeal success rate with AI; measurable per-claim outcomes.",
        (5.5, 7.5, 8.0, 7.0, 7.0), ["F1_technology", "F2_demographics"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-OB-005", "Outcome-Based Legal Document Automation",
        "5411", "Legal Services", "outcome_based",
        "AI contract review/generation charging % of time savings vs paralegal baseline. AmLaw 100 avg associate rate $450/hr; 40-60% time savings on routine docs measurable.",
        (5.5, 6.5, 5.5, 6.0, 7.5), ["F1_technology", "F5_psychology"],
        "CONDITIONAL", categories=["CONDITIONAL", "FEAR_ECONOMY"], eq=4
    ),
    make_model(
        "V318-OB-006", "Outcome-Based Manufacturing Quality",
        "3329", "Other Fabricated Metal", "outcome_based",
        "AI quality control charging % of defect cost reduction. Mean defect cost $2.3M/facility; AI vision catches 95%+ defects; savings directly attributable per line.",
        (7.5, 7.5, 6.5, 7.0, 6.0), ["F1_technology", "F2_demographics"],
        "FORCE_RIDER", eq=5
    ),

    # ── coordination_protocol (5 models) ──
    make_model(
        "V318-CP-001", "AI Agent Marketplace Protocol",
        "5112", "Software Publishers", "coordination_protocol",
        "Permissionless agent-to-agent coordination standard with transaction-fee capture. Agent adoption 5%→40%; no dominant protocol yet; Stripe-for-agents opportunity.",
        (9.0, 8.5, 6.0, 9.0, 8.0), ["F1_technology", "F4_capital"],
        "STRUCTURAL_WINNER", eq=5
    ),
    make_model(
        "V318-CP-002", "Supply Chain Visibility Standard",
        "4231", "Motor Vehicle Parts Wholesale", "coordination_protocol",
        "Multi-party supply chain data protocol with certification-fee capture. $6T wholesale trade; zero-density Schumpeterian gap (P-022); visibility is precondition for AI optimization.",
        (6.0, 6.5, 5.5, 5.0, 5.5), ["F1_technology", "F3_geopolitics"],
        "CONDITIONAL", eq=4
    ),
    make_model(
        "V318-CP-003", "Healthcare Data Exchange Protocol",
        "6211", "Offices of Physicians", "coordination_protocol",
        "Interoperability protocol for clinical data with per-query fees. 900K physician offices, 6K hospitals; CMS mandating interoperability; no open standard has won.",
        (5.0, 6.5, 8.0, 4.5, 5.0), ["F1_technology", "F2_demographics"],
        "CONDITIONAL", eq=4
    ),
    make_model(
        "V318-CP-004", "AI Safety Certification Protocol",
        "5416", "Management/Scientific Consulting", "coordination_protocol",
        "Standard for AI model safety evaluation with certification-fee capture. EU AI Act Dec 2027; no global standard; first mover sets protocol. UL/ISO pattern for AI.",
        (7.0, 7.5, 8.0, 6.0, 5.5), ["F1_technology", "F3_geopolitics", "F5_psychology"],
        "FORCE_RIDER", categories=["FORCE_RIDER", "FEAR_ECONOMY"], eq=5
    ),
    make_model(
        "V318-CP-005", "Decentralized AI Training Protocol",
        "5112", "Software Publishers", "coordination_protocol",
        "Multi-party model training/fine-tuning protocol with orchestration fees. GPU backlog 3.6M Blackwell units; distributed training reduces capex; protocol captures coordination value.",
        (8.0, 7.5, 5.5, 7.5, 7.0), ["F1_technology", "F4_capital", "F6_energy"],
        "FORCE_RIDER", eq=4
    ),
]

# ═══════════════════════════════════════════════════════════════
# CLUSTER B: Sector Gap Models
# ═══════════════════════════════════════════════════════════════

CLUSTER_B = [
    # ── Wholesale Trade 42 (5 models) ──
    make_model(
        "V318-WHL-001", "AI-Powered Wholesale Intermediation Platform",
        "4231", "Motor Vehicle Parts Wholesale", "platform_infrastructure",
        "AI matching engine for wholesale buyer-seller coordination. $6T US wholesale, 1% AI startup penetration; zero-density Schumpeterian gap. Alibaba B2B pattern for domestic.",
        (7.5, 7.0, 5.5, 6.5, 6.0), ["F1_technology"],
        "FORCE_RIDER", eq=4
    ),
    make_model(
        "V318-WHL-002", "Algorithmic Wholesale Sourcing Platform",
        "4244", "Grocery/Related Products Wholesale", "data_compounding",
        "AI demand forecasting + automated procurement for wholesale distributors. $950B grocery wholesale; 412K establishments avg 15 employees; spreadsheet-heavy operations.",
        (6.5, 7.0, 6.0, 6.0, 6.5), ["F1_technology", "F2_demographics"],
        "FORCE_RIDER", eq=4
    ),
    make_model(
        "V318-WHL-003", "Wholesale Inventory Intelligence",
        "4234", "Professional Equipment Wholesale", "data_compounding",
        "Predictive inventory + dynamic pricing for professional equipment distributors. $280B market; 84K establishments; high SKU complexity rewards data compounding.",
        (5.5, 6.5, 5.5, 6.0, 7.0), ["F1_technology"],
        "CONDITIONAL", eq=4
    ),
    make_model(
        "V318-WHL-004", "Acquire + Modernize Industrial Supply Distributor",
        "4238", "Machinery/Supply Wholesale", "acquire_and_modernize",
        "Roll-up small industrial distributors + deploy AI inventory/logistics. $500B+ industrial distribution; avg establishment 12 employees; Silver Tsunami succession wave.",
        (8.0, 7.5, 6.0, 8.0, 6.5), ["F1_technology", "F2_demographics", "F4_capital"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-WHL-005", "Wholesale Trade Compliance Automation",
        "4246", "Chemical Wholesale", "compliance_automation",
        "AI regulatory compliance for chemical/hazmat wholesale distribution. 15K chemical distributors; EPA/OSHA/DOT triple compliance burden; AI reduces compliance cost 40-60%.",
        (5.0, 6.0, 7.5, 5.5, 6.5), ["F1_technology", "F3_geopolitics"],
        "CONDITIONAL", eq=4
    ),

    # ── Arts/Entertainment 71 (4 models) ──
    make_model(
        "V318-ART-001", "Synthetic Media Production Studio",
        "5121", "Motion Picture/Video Production", "platform_infrastructure",
        "AI-generated visual content pipeline for film/TV/advertising. 90% of online content may be synthetic by 2026; deepfake losses $12.5B. Production cost collapse creates demand for orchestration.",
        (8.5, 8.0, 6.0, 8.5, 7.0), ["F1_technology", "F5_psychology"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-ART-002", "Live Experience Premium Platform",
        "7111", "Performing Arts Companies", "service_platform",
        "Platform for premium live events leveraging AI-verified-human authenticity. Anti-deepfake trust premium: live attendance up 23% post-pandemic; verified-human content commands 3-5x premium.",
        (5.5, 6.5, 5.5, 5.0, 4.5), ["F5_psychology", "F1_technology"],
        "CONDITIONAL", categories=["CONDITIONAL", "FEAR_ECONOMY"], eq=4
    ),
    make_model(
        "V318-ART-003", "AI IP Rights Management Protocol",
        "5121", "Motion Picture/Video Production", "regulatory_moat_builder",
        "AI content provenance tracking + IP licensing for synthetic media. No standard for AI content attribution; every studio/publisher needs it; first mover sets the standard.",
        (7.0, 7.0, 7.5, 6.0, 5.5), ["F1_technology", "F3_geopolitics", "F5_psychology"],
        "FORCE_RIDER", categories=["FORCE_RIDER", "FEAR_ECONOMY"], eq=5
    ),
    make_model(
        "V318-ART-004", "Creator Economy Operations Platform",
        "7111", "Performing Arts Companies", "vertical_saas",
        "All-in-one business operations for content creators: audience analytics, revenue management, cross-platform scheduling. $250B creator economy; MrBeast model: audience=asset.",
        (4.0, 7.0, 6.0, 7.0, 7.5), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=4
    ),

    # ── Utilities 22 (3 models) ──
    make_model(
        "V318-UTL-001", "AI Grid Optimization Platform",
        "2211", "Electric Power Generation", "platform_infrastructure",
        "AI-powered grid balancing for renewable integration. 2,600 GW in queue, 5+ year wait; solar +51.6% YoY; AI grid ops is bottleneck to clean energy deployment.",
        (7.5, 8.5, 8.0, 6.0, 5.0), ["F1_technology", "F6_energy"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-UTL-002", "Distributed Energy Resource Management",
        "2211", "Electric Power Generation", "data_compounding",
        "AI orchestration for behind-the-meter solar+storage+EV fleets. Meta 6.6 GW nuclear commitment; AI data centers need 133% more electricity; distributed resources compound data value.",
        (6.5, 7.5, 7.0, 5.5, 5.5), ["F1_technology", "F6_energy", "F4_capital"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-UTL-003", "Nuclear Operations AI",
        "2211", "Electric Power Generation", "vertical_saas",
        "AI-augmented nuclear plant monitoring, maintenance prediction, regulatory compliance. Nuclear renaissance: SMR pipeline expanding; NRC approval process is 6-10 years; AI reduces ops cost 20-30%.",
        (5.0, 6.5, 7.5, 4.0, 4.5), ["F1_technology", "F6_energy"],
        "CONDITIONAL", eq=4
    ),
]

# ═══════════════════════════════════════════════════════════════
# CLUSTER C: Emerging Pattern Models
# ═══════════════════════════════════════════════════════════════

CLUSTER_C = [
    # ── Agent-as-a-Service (3 models) ──
    make_model(
        "V318-AGT-001", "Vertical AI Agent Deployment Platform",
        "5415", "Computer Systems Design", "platform_infrastructure",
        "Pre-built AI agents for specific verticals (legal, accounting, healthcare) with per-task billing. Agent adoption 5%→40% in 12mo; enterprise needs vertical-specific, not general.",
        (8.0, 8.5, 7.0, 8.5, 7.5), ["F1_technology", "F4_capital"],
        "STRUCTURAL_WINNER", eq=5
    ),
    make_model(
        "V318-AGT-002", "AI Agent Testing + Monitoring SaaS",
        "5415", "Computer Systems Design", "vertical_saas",
        "Continuous testing, evaluation, and monitoring for deployed AI agents. No QA standard for agents; every enterprise deployer needs validation; regulatory requirement building.",
        (7.5, 8.0, 7.0, 8.0, 7.0), ["F1_technology", "F5_psychology"],
        "FORCE_RIDER", categories=["FORCE_RIDER", "FEAR_ECONOMY"], eq=5
    ),
    make_model(
        "V318-AGT-003", "Multi-Agent Workflow Orchestrator",
        "5415", "Computer Systems Design", "platform_infrastructure",
        "Enterprise orchestration layer for multi-agent workflows with billing + governance. Agent sprawl is the next infrastructure crisis; orchestration captures coordination value.",
        (8.0, 8.0, 6.5, 8.5, 7.5), ["F1_technology", "F4_capital"],
        "FORCE_RIDER", eq=5
    ),

    # ── Human-Premium Verified Services (3 models) ──
    make_model(
        "V318-HPV-001", "Verified Human Financial Advisory",
        "5239", "Other Financial Investment Activities", "service_platform",
        "Certified human-only financial planning with AI augmentation for research (never client-facing). Trust premium: 60% expect AI cuts jobs; 51% fear own job. Human certification = premium pricing.",
        (5.0, 7.0, 6.0, 5.5, 4.5), ["F5_psychology", "F2_demographics"],
        "FEAR_ECONOMY", eq=4
    ),
    make_model(
        "V318-HPV-002", "Human-Premium Healthcare Navigation",
        "6211", "Offices of Physicians", "service_platform",
        "Verified human healthcare advocates for complex medical decisions. AI triage + human decision-maker; trust is non-negotiable for life-altering choices; Baumol premium compounds.",
        (4.5, 6.5, 6.5, 4.5, 4.0), ["F5_psychology", "F2_demographics"],
        "FEAR_ECONOMY", eq=4
    ),
    make_model(
        "V318-HPV-003", "Human-Premium Legal Counsel Platform",
        "5411", "Legal Services", "service_platform",
        "AI-augmented but human-led legal services with verified attorney oversight. 82% ethical concern rate in legal AI; human premium is structural, not temporary.",
        (4.0, 6.0, 5.5, 4.5, 4.5), ["F5_psychology", "F1_technology"],
        "FEAR_ECONOMY", eq=4
    ),

    # ── Synthetic Media (2 models) ──
    make_model(
        "V318-SYN-001", "Enterprise Synthetic Content Factory",
        "5121", "Motion Picture/Video Production", "full_service_replacement",
        "AI-generated marketing/training content at 1/10th cost of traditional production. 90% synthetic content by 2026 forecast; enterprise content budgets shifting from production to orchestration.",
        (7.5, 7.5, 5.5, 8.0, 7.5), ["F1_technology"],
        "FORCE_RIDER", eq=5
    ),
    make_model(
        "V318-SYN-002", "Deepfake Detection + Content Authentication",
        "5112", "Software Publishers", "regulatory_moat_builder",
        "AI-powered content verification with cryptographic provenance. Deepfake fraud $12.5B; regulatory mandates building (EU AI Act, state laws); certification moat.",
        (7.0, 7.5, 8.0, 7.0, 6.0), ["F1_technology", "F3_geopolitics", "F5_psychology"],
        "FORCE_RIDER", categories=["FORCE_RIDER", "FEAR_ECONOMY"], eq=5
    ),

    # ── Temporal Extraction (3 models) ──
    make_model(
        "V318-TMP-001", "CMMC Compliance Sprint Provider",
        "5416", "Management/Scientific Consulting", "arbitrage_window",
        "Fast-track CMMC certification for 220K DIB companies before enforcement cliff. OBBBA Jul 5 2026; $6-8B compliance TAM with 18-month extraction window.",
        (7.5, 8.0, 7.0, 9.0, 8.0), ["F1_technology", "F3_geopolitics"],
        "TIMING_ARBITRAGE", eq=5
    ),
    make_model(
        "V318-TMP-002", "EU AI Act Compliance Accelerator",
        "5416", "Management/Scientific Consulting", "arbitrage_window",
        "Pre-built compliance packages for EU AI Act (Aug 2026 Phase 1, Dec 2027 Phase 2). 27 EU member states + EEA; no dominant provider yet; window closes as market matures.",
        (6.5, 7.5, 8.0, 8.0, 7.0), ["F1_technology", "F3_geopolitics"],
        "TIMING_ARBITRAGE", eq=5
    ),
    make_model(
        "V318-TMP-003", "Solar ITC Credit Capture Accelerator",
        "2211", "Electric Power Generation", "arbitrage_window",
        "Fast-track solar+storage installation before ITC step-down (Jul 2026 credit cliff). 70 GW pipeline; credit value drops 10% in 2026, further in 2027; sprint window.",
        (5.5, 7.0, 6.5, 9.0, 8.5), ["F6_energy", "F4_capital"],
        "TIMING_ARBITRAGE", eq=5
    ),
]


def main():
    print("=" * 70)
    print("v3-18 MODEL GENERATION: Architecture Gaps + Sector Gaps + Emerging Patterns")
    print("=" * 70)

    all_new = CLUSTER_A + CLUSTER_B + CLUSTER_C
    print(f"\nTotal new models: {len(all_new)}")
    print(f"  Cluster A (architecture gaps): {len(CLUSTER_A)}")
    print(f"  Cluster B (sector gaps): {len(CLUSTER_B)}")
    print(f"  Cluster C (emerging patterns): {len(CLUSTER_C)}")

    # Architecture distribution
    from collections import Counter
    arch_dist = Counter(m["architecture"] for m in all_new)
    print(f"\nArchitecture distribution:")
    for a, c in arch_dist.most_common():
        print(f"  {a}: {c}")

    # Category distribution
    cat_dist = Counter(m["primary_category"] for m in all_new)
    print(f"\nCategory distribution:")
    for cat, c in cat_dist.most_common():
        print(f"  {cat}: {c}")

    # Load normalized file
    print(f"\nLoading normalized file...")
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"  Existing models: {len(models)}")

    # Check for ID conflicts
    existing_ids = {m["id"] for m in models}
    for nm in all_new:
        if nm["id"] in existing_ids:
            print(f"  WARNING: ID conflict {nm['id']}")

    # Merge
    models.extend(all_new)
    print(f"  After merge: {len(models)}")

    # Re-rank all by composite
    models.sort(key=lambda m: (-m["composite"], m["id"]))
    for i, m in enumerate(models, 1):
        m["rank"] = i

    # Assign opportunity and VCR ranks
    opp_sorted = sorted(models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(opp_sorted, 1):
        m["opportunity_rank"] = i

    vcr_sorted = sorted(models, key=lambda m: (-m.get("vcr", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(vcr_sorted, 1):
        m["vcr_rank"] = i

    # Update summary
    composites = [m["composite"] for m in models]
    cat_dist_all = Counter(m.get("primary_category") for m in models)
    data["summary"]["composite_stats"] = {
        "max": max(composites),
        "min": min(composites),
        "mean": round(statistics.mean(composites), 2),
        "median": round(statistics.median(composites), 2),
    }
    data["summary"]["primary_category_distribution"] = dict(
        sorted(cat_dist_all.items(), key=lambda x: -x[1])
    )

    # Write back
    data["models"] = models
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nWritten: {NORMALIZED_FILE}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"v3-18 MODEL GENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"\n  Total models: {len(models)}")
    print(f"  New models added: {len(all_new)}")
    print(f"  Architecture types now: {len(Counter(m.get('architecture') for m in models))}")
    print(f"\n  New model composites:")
    new_composites = [m["composite"] for m in all_new]
    print(f"    Max: {max(new_composites)}")
    print(f"    Min: {min(new_composites)}")
    print(f"    Mean: {statistics.mean(new_composites):.1f}")
    print(f"\n  New models by rank:")
    for m in sorted(all_new, key=lambda x: x["rank"]):
        print(f"    #{m['rank']:>3} {m['id']:<25} {m['name'][:45]:<46} T={m['composite']:>5.1f} arch={m['architecture']}")


if __name__ == "__main__":
    main()
