#!/usr/bin/env python3
"""
v4_enrich_batch1.py — Enrich 4 transformation narratives with detailed
year_by_year projections, geographic_variation, and falsification_criteria.

Targets: TN-012 (Real Estate), TN-002 (Professional Services),
         TN-010 (IT Services), TN-006 (Construction)
"""

import json
import os
from datetime import datetime

NARRATIVES_PATH = "/Users/mv/Documents/research/data/v4/narratives.json"

# ─────────────────────────────────────────────────────────────────────
# TN-012 — Real Estate and Rental and Leasing
# ─────────────────────────────────────────────────────────────────────

TN012_YEAR_BY_YEAR = {
    "2026": {
        "phase": "acceleration",
        "description": "Commercial real estate vacancy rates at 20-year highs (office 18%+). Residential affordability crisis: median home price 5.5x median income. PropTech platforms managing $500B+ AUM. AI property valuation reaching institutional accuracy. Remote work stabilized at 28% of workdays, permanently reducing office demand.",
        "indicators": [
            "CBRE/JLL office vacancy rate tracking (baseline: 18%+)",
            "NAR median home price-to-income ratio (baseline: 5.5x)",
            "PropTech AUM via PitchBook (baseline: $500B+)",
            "Kastle Systems office occupancy data (proxy for remote work share)",
            "AI property valuation accuracy vs appraiser benchmarks"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "Office-to-residential conversion projects accelerate in top 20 metros. AI-driven property management reducing operating costs 15-20%. First AI-underwritten commercial mortgages at scale. REIT sector bifurcation: data centers/logistics up, office/retail down.",
        "indicators": [
            "Office-to-residential conversion permits in top 20 metros",
            "AI property management cost reduction benchmarks (target: 15-20%)",
            "AI-underwritten commercial mortgage volume",
            "REIT sector total returns: data center vs office sub-indices",
            "CoStar commercial property price index by segment"
        ]
    },
    "2028": {
        "phase": "restructuring",
        "description": "Commercial real estate debt maturity crisis ($900B maturing). Distressed office assets available at 40-60% of 2019 valuations. AI lease analysis and optimization standard. Smart building platforms reach $10B market.",
        "indicators": [
            "CRE debt maturities via Trepp/MSCI ($900B baseline)",
            "Distressed office transaction prices vs 2019 peak",
            "AI lease analysis adoption rate among commercial landlords",
            "Smart building platform market size (target: $10B)",
            "CMBS delinquency rates by property type"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "CRE restructuring complete for early-cycle assets. Mixed-use development model dominant in new construction. AI-native property management firms manage 10%+ of rental units. Climate risk AI pricing affects coastal/flood zone valuations.",
        "indicators": [
            "Mixed-use share of new construction permits",
            "AI-native property management market share (target: 10%+ of rental units)",
            "Climate risk discount in coastal/flood zone property valuations",
            "CRE loan workout completion rates for 2024-2026 vintage",
            "FEMA flood zone property price differential vs pre-AI-pricing"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "New CRE equilibrium: 25% less office space, 15% more mixed-use. Residential: AI-managed portfolios standard for institutional investors. Property management workforce restructured: fewer property managers, more technology operators.",
        "indicators": [
            "Total US office space vs 2024 baseline (target: -25%)",
            "Mixed-use share of commercial real estate (target: +15%)",
            "AI-managed residential portfolio share among institutional investors",
            "BLS property management employment vs 2024 baseline",
            "Technology operator roles in real estate job postings"
        ]
    }
}

TN012_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest CRE market. Office vacancy crisis centered in NYC, SF, Chicago. Sunbelt migration driving residential demand. $900B debt maturity wall."
    },
    "China": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Evergrande aftermath. Government-managed restructuring. Ghost cities and oversupply. Different crisis dynamics than US."
    },
    "Japan": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "Declining population reducing demand. Tokyo still premium. Rural depopulation accelerating. Government incentives for rural relocation."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Energy efficiency regulations driving renovation. London CRE under pressure. Paris, Berlin more stable. Green building requirements."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "+1 year",
        "notes": "Urbanization driving 10M+ housing unit demand/yr. REITs emerging. Smart city projects. Mumbai, Delhi NCR hotspots."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Informal housing dominant. Brazil Minha Casa program. Mexico nearshoring driving industrial real estate."
    },
    "SEA": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "Singapore hub. Vietnam, Indonesia urbanizing rapidly. Data center real estate booming."
    },
    "MENA": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Saudi NEOM, Egypt New Capital. Dubai continued expansion. Mega-project driven."
    }
}

TN012_FALSIFICATION = [
    "Office vacancy rates reverse below 12% by 2028 — remote work thesis failed",
    "CRE debt successfully refinanced at <7% rates — no distressed asset cascade",
    "AI property management accuracy below 80% on maintenance prediction — technology thesis weakens",
    "Residential affordability improves without policy intervention — crisis thesis weakened"
]

# ─────────────────────────────────────────────────────────────────────
# TN-002 — Professional Services
# ─────────────────────────────────────────────────────────────────────

TN002_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "9.6M professional services workers, $2.1T revenue. Baumol score 1.8x (high stored disruption energy). AI coding tools 84% developer adoption, experienced devs reporting 19% slower with AI (skill ceiling). Legal AI doc review reducing associate hours 30-40%. Consulting firms deploying AI for data analysis, proposal generation. Management consulting margins under pressure from AI-enabled boutiques.",
        "indicators": [
            "BLS QCEW professional services employment (baseline: 9.6M)",
            "Census professional services revenue (baseline: $2.1T)",
            "GitHub/Stack Overflow developer AI tool adoption surveys (baseline: 84%)",
            "Legal AI doc review market size and adoption rate",
            "Management consulting revenue per employee trajectory"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "First AI-native law firms handling routine corporate work at 60% cost reduction. Engineering design AI reaching structural analysis capability. Accounting automation cascading from TN-001 into broader professional services. Consulting firm layoffs at analyst/associate level begin.",
        "indicators": [
            "AI-native law firm count and revenue (target: routine corporate work at 60% cost reduction)",
            "Engineering design AI structural analysis pass rates vs human engineers",
            "Accounting automation spillover: professional services firms adopting AI-first workflows",
            "Consulting firm analyst/associate hiring rates vs 2024 baseline",
            "AmLaw 100 revenue per lawyer trajectory"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Professional services employment inflection: routine analyst/associate roles -15%. AI-augmented senior professionals 3-4x more productive. Boutique AI-native firms capture 10% market share in legal, consulting. Architecture AI handling 80% of code-compliant residential design.",
        "indicators": [
            "BLS analyst/associate employment in professional services (target: -15%)",
            "AI-augmented professional productivity benchmarks (target: 3-4x)",
            "AI-native boutique firm market share in legal and consulting (target: 10%)",
            "Architecture AI code-compliant residential design share (target: 80%)",
            "Professional services firm size distribution shift"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Barbell economy visible: premium human judgment commands 2x premium, routine cognitive work commoditized. Professional licensing reform begins (do you need a CPA for AI-prepared returns?). Micro-firm professional services model proves viable at scale.",
        "indicators": [
            "Billing rate spread: senior advisory vs routine work (target: 2x+ premium)",
            "State licensing reform proposals for AI-assisted professional practice",
            "Solo practitioner / micro-firm professional services revenue growth",
            "CPA exam enrollment trends as proxy for pipeline disruption",
            "AI-prepared tax return accuracy vs CPA-prepared benchmarks"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Professional services restructured: 30% fewer workers, 25% higher revenue/worker. Firms 40% smaller on average. Solo practitioners with AI match mid-size firm capability. Human premium clear in litigation, M&A advisory, complex consulting.",
        "indicators": [
            "BLS professional services employment vs 2024 baseline (target: -30%)",
            "Revenue per worker vs 2024 baseline (target: +25%)",
            "Average professional services firm size vs 2024 (target: -40%)",
            "Solo practitioner win rates in competitive engagements vs mid-size firms",
            "Human premium billing rates in litigation, M&A, complex consulting"
        ]
    }
}

TN002_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest professional services market. Litigation culture creates unique legal AI dynamics. CPA pipeline crisis. 84% dev AI adoption."
    },
    "China": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Different professional services structure. State-directed firms. Rapid legal AI adoption for contract review. Engineering AI advanced."
    },
    "Japan": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "Lifetime employment culture slows workforce restructuring. Aging professionals create succession crisis. Conservative adoption."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "UK leading (London professional services hub). GDPR constrains AI data use. Strong labor protections. Different licensing frameworks."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "+1 year",
        "notes": "IT outsourcing capital. Massive professional workforce. Infosys, TCS, Wipro facing AI disruption of their core model. Legal process outsourcing hub."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Small professional services sectors. Brazil leading. Informal economy limits."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Singapore as professional services hub. Growing but small. Philippines BPO under AI pressure."
    },
    "MENA": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "Dubai/Abu Dhabi professional services hub. Growing with sovereign wealth investment."
    }
}

TN002_FALSIFICATION = [
    "AI coding tool productivity gains reverse or plateau below 15% — developer augmentation thesis weakened",
    "Professional licensing bodies successfully block AI from core practice areas for 3+ years",
    "AI-native boutique firms fail to capture >5% market share by 2028 — incumbent advantage dominates",
    "Baumol score decreases (wage growth slows to CPI) — stored disruption energy dissipates naturally",
    "AI hallucination rates remain >3% in legal/accounting work — trust barrier prevents adoption"
]

# ─────────────────────────────────────────────────────────────────────
# TN-010 — IT Services
# ─────────────────────────────────────────────────────────────────────

TN010_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "2.46M IT workers, $366.8B payroll, Baumol 2.05x. 84% of developers using AI coding daily. Experienced devs 19% SLOWER with AI (the skill ceiling paradox). Cloud spending $600B+ globally. Cybersecurity spending $180B+. AI infrastructure buildout consuming 40% of cloud growth. Content verification and deepfake detection emerging as new markets.",
        "indicators": [
            "BLS QCEW IT services employment (baseline: 2.46M)",
            "IT services payroll (baseline: $366.8B)",
            "Developer AI tool adoption rate (baseline: 84%)",
            "Global cloud infrastructure spending (baseline: $600B+)",
            "Cybersecurity market size (baseline: $180B+)",
            "AI infrastructure share of cloud spending growth (baseline: 40%)"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "AI handles 60% of Tier 1 support tickets autonomously. Junior developer hiring -25% as AI coding scales. Cloud-native AI platforms reach enterprise maturity. Cybersecurity AI reduces false positive rates 80%. Telecom network automation reaches 50% of routine operations.",
        "indicators": [
            "AI autonomous resolution rate for Tier 1 support tickets (target: 60%)",
            "Junior developer hiring volume vs 2024 baseline (target: -25%)",
            "Cloud-native AI platform enterprise adoption rates",
            "Cybersecurity AI false positive reduction rate (target: 80%)",
            "Telecom network automation share of routine operations (target: 50%)"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "IT services restructuring visible: managed services models transforming from headcount-based to outcome-based. AI-native media production studios viable at 10% of traditional cost. Autonomous software testing standard. Publishing industry consolidation accelerates.",
        "indicators": [
            "Managed services contract structure shift (headcount-based vs outcome-based %)",
            "AI-native media production cost benchmarks vs traditional studios",
            "Autonomous software testing adoption rate in enterprise CI/CD pipelines",
            "Publishing industry M&A volume and revenue consolidation",
            "IT outsourcing contract values: per-seat vs per-outcome pricing"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "IT outsourcing model fundamentally changed: India/Philippines BPO workforce -20% in routine IT support. DevOps automation reduces ops teams by 40%. Content authenticity infrastructure becomes standard (watermarking, provenance). Regional telecom automation mature.",
        "indicators": [
            "India/Philippines IT BPO employment in routine support (target: -20%)",
            "DevOps team size vs 2024 baseline (target: -40%)",
            "Content authenticity standard adoption (C2PA/watermarking) in major platforms",
            "Telecom OPEX reduction from automation benchmarks",
            "NASSCOM IT services headcount and revenue per employee"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "IT services employment restructured: fewer administrators and support staff, more architects and AI system managers. New equilibrium: smaller IT departments, higher per-worker value. AI infrastructure management standard. Human premium in security architecture, system design, client advisory.",
        "indicators": [
            "IT administrator/support employment vs 2024 baseline",
            "Architect/AI system manager job postings growth",
            "Average IT department size vs 2024 baseline",
            "Revenue per IT worker trajectory",
            "Security architect and system design billing rate premiums"
        ]
    }
}

TN010_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest IT market. Silicon Valley leading AI infrastructure. 84% developer AI adoption. Cloud hyperscalers headquartered. Cybersecurity capital."
    },
    "China": {
        "velocity": "high",
        "timeline_shift": "-1 year",
        "notes": "Parallel AI ecosystem (Baidu, Alibaba Cloud, Huawei). 5G infrastructure ahead. ByteDance/TikTok driving content tech. Government surveillance AI advanced."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Enterprise IT modernization lagging (legacy COBOL). NEC, Fujitsu transitioning. Digital Agency pushing modernization. IT worker shortage acute."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "GDPR shapes AI deployment. SAP ecosystem dominant in enterprise. AI Act compliance creating new IT service needs. Strong in industrial IoT."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "0 years",
        "notes": "IT services heartland (TCS, Infosys, Wipro). 5M+ IT workers. BPO model directly threatened. GCCs (Global Capability Centers) growing as alternative."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "Nearshore IT services growing (Mexico, Colombia, Argentina). Talent arbitrage. Smaller but growing startup ecosystems."
    },
    "SEA": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "Vietnam emerging as IT outsourcing destination. Singapore tech hub. Growing cloud adoption."
    },
    "MENA": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "UAE tech hub aspirations. Limited IT services sector. Cloud adoption growing from low base."
    }
}

TN010_FALSIFICATION = [
    "AI coding productivity reverses for senior developers — skill ceiling paradox confirmed as dominant",
    "AI Tier 1 support accuracy stays below 70% — human support remains essential for routine queries",
    "India IT outsourcing revenues INCREASE by >15%/yr despite AI — outsourcing model proves resilient",
    "Cybersecurity AI false positive rates don't improve — human analysts remain essential",
    "Content authenticity solutions fail to reach adoption >20% — deepfake/provenance market doesn't materialize"
]

# ─────────────────────────────────────────────────────────────────────
# TN-006 — Construction
# ─────────────────────────────────────────────────────────────────────

TN006_YEAR_BY_YEAR = {
    "2026": {
        "phase": "pre_disruption",
        "description": "7.9M construction workers, 920K establishments. Most under-digitized major sector (negative productivity growth over 20 years). 650K unfilled positions. Average contractor age 57+. Modular construction growing 15%/yr. Construction tech funding $3B+ annually. BIM adoption reaching 60% for large projects.",
        "indicators": [
            "BLS QCEW construction employment (baseline: 7.9M)",
            "Census construction establishments (baseline: 920K)",
            "Construction productivity index vs 20-year trend (baseline: negative)",
            "JOLTS construction job openings (baseline: 650K unfilled)",
            "Modular construction market growth rate (baseline: 15%/yr)",
            "BIM adoption rate on large commercial projects (baseline: 60%)"
        ]
    },
    "2027": {
        "phase": "early_adoption",
        "description": "3D-printed structures reach code compliance in 10+ states. Autonomous heavy equipment deployed on highway/infrastructure projects. Drone site surveys standard (80% of large commercial projects). Labor shortage worsens: retirement wave accelerates, apprenticeship pipeline insufficient.",
        "indicators": [
            "3D-printed structure code compliance by state count (target: 10+)",
            "Autonomous heavy equipment deployments on infrastructure projects",
            "Drone site survey adoption on large commercial projects (target: 80%)",
            "Construction apprenticeship enrollment vs retirement outflow",
            "Average contractor age tracking via Census/trade associations"
        ]
    },
    "2028": {
        "phase": "early_disruption",
        "description": "Modular construction reaches 10% of new residential starts. AI project management reducing cost overruns by 20-30%. Robotic bricklaying and drywall finishing commercially viable. Infrastructure bill projects peak employment demand, worsening labor competition.",
        "indicators": [
            "Modular/prefab share of new residential housing starts (target: 10%)",
            "AI project management cost overrun reduction benchmarks (target: 20-30%)",
            "Robotic bricklaying and drywall commercial deployment count",
            "IIJA infrastructure project employment demand vs labor supply",
            "Construction cost index trajectory"
        ]
    },
    "2029": {
        "phase": "acceleration",
        "description": "Construction productivity finally inflects positive after 20-year decline. Small contractor acquisition wave (Silver Tsunami + modernization). Prefab factories operational in 30+ metros. Climate adaptation construction becomes major category.",
        "indicators": [
            "BLS construction productivity index (target: positive inflection)",
            "Small contractor M&A volume and valuation multiples",
            "Prefab/modular factory count by metro (target: 30+ metros)",
            "Climate adaptation construction spending as share of total",
            "Census business dynamics: construction establishment exits vs entries"
        ]
    },
    "2030_2031": {
        "phase": "restructuring",
        "description": "Construction industry restructured: fewer workers, higher productivity. Modular/prefab 20%+ of residential. AI-managed projects standard for commercial. Human premium in skilled trades (electricians, plumbers) with AI augmentation. Average project delivery time -20%.",
        "indicators": [
            "Construction employment vs 2024 baseline",
            "Modular/prefab share of residential construction (target: 20%+)",
            "AI-managed commercial project share",
            "Skilled trades wage premium (electricians, plumbers) trajectory",
            "Average project delivery time vs 2024 baseline (target: -20%)"
        ]
    }
}

TN006_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest construction market. Most under-digitized. 650K unfilled positions. Infrastructure bill driving demand. Silver Tsunami acute in contractors."
    },
    "China": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Massive construction capacity but real estate slowdown. Advanced in prefab/modular. High-speed rail expertise. Infrastructure export."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "-1 year",
        "notes": "Labor shortage most acute. Leading in construction robotics (Shimizu, Obayashi). Disaster resilience driving innovation. Declining new construction volume."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Green renovation wave (Renovation Wave initiative). Energy efficiency requirements. Strong labor protections. Passive house standard driving precision."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "+2 years",
        "notes": "Massive housing deficit (30M+ units). Infrastructure buildout accelerating. Low-cost labor reduces automation urgency but quality/speed needs drive tech."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Informal construction dominant. Brazil housing deficit. Limited construction tech adoption."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Rapid urbanization. Infrastructure buildout phase. Limited construction tech penetration."
    },
    "MENA": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "NEOM, Egyptian New Capital, Dubai mega-projects. Advanced construction methods at scale in prestige projects."
    }
}

TN006_FALSIFICATION = [
    "Construction productivity remains negative for 3+ more years — digital transformation thesis fails",
    "Modular/prefab share stays below 5% of new residential by 2029 — adoption barriers stronger than projected",
    "Labor shortage resolves via immigration providing 300K+ construction workers — demographic thesis weakened",
    "3D printing and construction robotics fail code compliance in major markets — technology path blocked",
    "Small contractor acquisition multiples stay above 5x EBITDA — Silver Tsunami discount doesn't materialize"
]

# ─────────────────────────────────────────────────────────────────────
# ENRICHMENT MAP
# ─────────────────────────────────────────────────────────────────────

ENRICHMENTS = {
    "TN-012": {
        "year_by_year": TN012_YEAR_BY_YEAR,
        "geographic_variation": TN012_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN012_FALSIFICATION,
    },
    "TN-002": {
        "year_by_year": TN002_YEAR_BY_YEAR,
        "geographic_variation": TN002_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN002_FALSIFICATION,
    },
    "TN-010": {
        "year_by_year": TN010_YEAR_BY_YEAR,
        "geographic_variation": TN010_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN010_FALSIFICATION,
    },
    "TN-006": {
        "year_by_year": TN006_YEAR_BY_YEAR,
        "geographic_variation": TN006_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN006_FALSIFICATION,
    },
}


def main():
    # Load
    with open(NARRATIVES_PATH, "r") as f:
        data = json.load(f)

    updated = []
    for narrative in data["narratives"]:
        nid = narrative["narrative_id"]
        if nid in ENRICHMENTS:
            enrich = ENRICHMENTS[nid]
            # Update year_by_year (preserve phase from original if not overridden)
            narrative["year_by_year"] = enrich["year_by_year"]
            narrative["geographic_variation"] = enrich["geographic_variation"]
            narrative["falsification_criteria"] = enrich["falsification_criteria"]
            narrative["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            updated.append(nid)

            # Print summary
            name = narrative["name"]
            n_years = len(enrich["year_by_year"])
            n_geo = len(enrich["geographic_variation"])
            n_fc = len(enrich["falsification_criteria"])
            n_indicators = sum(
                len(yr.get("indicators", []))
                for yr in enrich["year_by_year"].values()
            )
            print(f"  {nid} ({name}):")
            print(f"    year_by_year: {n_years} periods, {n_indicators} indicators")
            print(f"    geographic_variation: {n_geo} regions")
            print(f"    falsification_criteria: {n_fc} criteria")

    if not updated:
        print("ERROR: No narratives matched target IDs!")
        return

    # Write back
    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nEnriched {len(updated)} narratives: {', '.join(updated)}")
    print(f"Written to: {NARRATIVES_PATH}")

    # Verification: re-read and validate
    with open(NARRATIVES_PATH, "r") as f:
        verify = json.load(f)

    print("\n--- Verification ---")
    for narrative in verify["narratives"]:
        nid = narrative["narrative_id"]
        if nid in ENRICHMENTS:
            geo_count = len(narrative["geographic_variation"])
            fc_count = len(narrative["falsification_criteria"])
            yby_filled = all(
                len(v.get("indicators", [])) > 0
                for v in narrative["year_by_year"].values()
            )
            print(f"  {nid}: geo={geo_count} regions, "
                  f"falsification={fc_count} criteria, "
                  f"all_indicators_populated={yby_filled}, "
                  f"last_updated={narrative.get('last_updated', 'N/A')}")


if __name__ == "__main__":
    print("v4_enrich_batch1.py — Enriching 4 transformation narratives\n")
    main()
