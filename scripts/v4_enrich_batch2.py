#!/usr/bin/env python3
"""
Enrich batch 2 narratives in narratives.json:
  TN-009 (Educational Services), TN-008 (Defense AI / National Security),
  TN-013 (Securities/Financial Investments), TN-005 (Administrative Services).
Updates: year_by_year, geographic_variation, falsification_criteria.
"""

import json
import sys
from datetime import date

NARRATIVES_PATH = "/Users/mv/Documents/research/data/v4/narratives.json"

# ── TN-009: Educational Services ─────────────────────────────────────────────

TN009_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "4.2M education workers, $800B+ US spending. AI tutoring platforms reaching 10M+ users. Brookings 50-country study confirms AI education potential. Ohio mandates, Michigan chatbot liability creating regulatory patchwork. Corporate training AI adoption fastest segment (fear friction gap=2). University enrollment declining 3rd consecutive year.",
        "indicators": [
            "BLS QCEW education employment (baseline: 4.2M)",
            "US education spending (baseline: $800B+)",
            "AI tutoring platform monthly active users (baseline: 10M+)",
            "State-level AI education regulation count",
            "NCES university enrollment trends (baseline: declining 3rd year)"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "AI-personalized curriculum reaches 20% of K-12 districts (pilot programs). Corporate L&D budgets shift 30% to AI-powered platforms. University admin automation reduces back-office costs 15%. First accredited AI-native degree programs launch. Teacher AI assistants standard in early-adopter districts.",
        "indicators": [
            "K-12 districts with AI-personalized curriculum (target: 20%)",
            "Corporate L&D spend share on AI platforms (target: 30%)",
            "University back-office cost reduction from AI (target: 15%)",
            "Accredited AI-native degree program count",
            "Teacher AI assistant adoption rate in early-adopter districts"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Education employment inflection: administrative roles -10%, teaching roles flat. Bootcamp/micro-credential market exceeds $50B. AI grading and assessment handling 60% of routine evaluation. Student-facing AI tutors reach clinical validation for STEM subjects. University business model under stress: enrollment -15% from peak.",
        "indicators": [
            "BLS education admin employment delta (target: -10%)",
            "Bootcamp/micro-credential market size (target: $50B+)",
            "AI grading share of routine evaluation (target: 60%)",
            "RCTs validating AI STEM tutoring efficacy",
            "University enrollment decline from peak (target: -15%)"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Higher education restructuring: 10% of small private colleges close or merge. AI-enabled competency-based education model scales. Corporate university alternatives capture 20% of professional development. Teacher role transforms: less lecturing, more mentoring/facilitating.",
        "indicators": [
            "Small private college closure/merger rate (target: 10%)",
            "Competency-based education enrollment share",
            "Corporate alternatives share of professional development (target: 20%)",
            "Teacher role surveys: lecturing vs mentoring time allocation",
            "NCES institutional count delta vs 2026 baseline"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Education system restructured: AI handles content delivery and assessment, humans handle mentoring, motivation, and social development. University model bifurcates: research universities thrive, teaching-only institutions under existential pressure. Lifelong learning AI platforms standard for workforce.",
        "indicators": [
            "AI share of content delivery and assessment in K-12",
            "Research vs teaching university revenue divergence",
            "Lifelong learning platform penetration in workforce",
            "Education employment composition: admin vs teaching vs mentoring",
            "Student debt burden trajectory (leading indicator of structural shift)"
        ]
    }
}

TN009_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest education market. Regulatory patchwork by state. University enrollment declining. Student debt crisis driving alternatives. Corporate L&D market $360B+."
    },
    "China": {
        "velocity": "high",
        "timeline_shift": "-1yr",
        "notes": "Government-directed AI education integration. Gaokao exam system creates unique AI tutoring demand. Private tutoring crackdown redirected to AI. 280M+ students."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Declining student population. Juku (cram school) culture adapting to AI. Teacher shortage in rural areas. Society 5.0 education goals."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Bologna Process standardization. Strong public university systems. GDPR limits student data AI. Nordic countries leading in EdTech adoption."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "+1yr",
        "notes": "1.5M schools, 300M+ students. Byju's/Unacademy ecosystem. Massive scale opportunity. Rural education access via AI. NEP 2020 reform enabling."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "Education access gaps large. Brazil, Mexico leading in EdTech. Language-specific content needed."
    },
    "SEA": {
        "velocity": "medium",
        "timeline_shift": "+2yr",
        "notes": "Young demographics. Ruangguru (Indonesia) model. English language AI education demand high."
    },
    "MENA": {
        "velocity": "low",
        "timeline_shift": "+2yr",
        "notes": "Arabic-language AI education emerging. Gulf states investing in education transformation. Large youth populations."
    }
}

TN009_FALSIFICATION = [
    "AI tutoring outcomes no better than traditional methods in 3+ RCTs — effectiveness thesis invalidated",
    "State/federal regulation bans AI grading for K-12 — deployment blocked at scale",
    "University enrollment reverses and grows 5%+ — decline thesis weakened",
    "Teacher unions successfully block AI classroom tools in 10+ states — institutional resistance dominates",
    "Corporate L&D spending on AI platforms grows <10%/yr — adoption slower than projected"
]

# ── TN-008: Defense AI / National Security ───────────────────────────────────

TN008_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "US defense AI spending $15B+ annually. Replicator initiative producing 1000+ autonomous drones. Ukraine conflict proving AI in ISR, targeting, logistics. China military AI budget estimated $10B+. NATO allies increasing defense spending to 2%+ GDP. AUKUS driving submarine and AI tech sharing.",
        "indicators": [
            "US defense AI budget allocation (baseline: $15B+)",
            "Replicator initiative autonomous drone production count (baseline: 1000+)",
            "Ukraine AI deployment case studies (ISR, targeting, logistics)",
            "NATO member defense spending as % GDP (target: 2%+)",
            "AUKUS technology sharing milestones"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "Autonomous systems reach 10% of deployed ISR assets. AI-enabled predictive maintenance standard across major weapons platforms. Defense AI procurement reforms (faster acquisition cycles). First AI-native defense primes emerge as competitors to legacy contractors. Space-based AI surveillance operational.",
        "indicators": [
            "Autonomous ISR asset share (target: 10%)",
            "AI predictive maintenance adoption across major weapons platforms",
            "Defense acquisition cycle time benchmarks",
            "AI-native defense company contract wins vs legacy primes",
            "Space-based AI surveillance system deployments"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Human-AI teaming doctrine established for major US/allied forces. Autonomous logistics convoys deployed. AI cyber defense handles 80% of routine threat detection. Defense industrial base modernization measurable: shipyard/arsenal capacity expanding. Critical mineral supply chains partially reshored.",
        "indicators": [
            "Human-AI teaming doctrine publication by DoD/allied forces",
            "Autonomous logistics convoy deployment count",
            "AI cyber defense share of routine threat detection (target: 80%)",
            "Shipyard/arsenal capacity metrics vs 2026 baseline",
            "Critical mineral domestic production share"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "AI changes military force structure: smaller human units augmented by autonomous systems. Defense AI export controls tighten as capabilities advance. Second-generation autonomous weapons systems in testing. Defense tech investment from VC reaches $30B+ cumulative.",
        "indicators": [
            "Military force structure changes: unit size vs autonomous augmentation",
            "Defense AI export control policy updates",
            "Second-gen autonomous weapons test milestones",
            "Cumulative VC investment in defense tech (target: $30B+)",
            "Defense workforce composition: human vs autonomous system operators"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Military transformation visible: 20% fewer personnel, 3x more autonomous systems. AI-enabled logistics reduces sustainment costs 25%. Defense AI ecosystem matured: specialized defense AI companies at scale. Dual-use technology transfer accelerating between defense and commercial.",
        "indicators": [
            "Military personnel count delta (target: -20%)",
            "Autonomous system deployment ratio vs 2026 baseline (target: 3x)",
            "Sustainment cost reduction from AI logistics (target: 25%)",
            "Defense AI company revenue and scale metrics",
            "Dual-use technology transfer volume (defense to commercial)"
        ]
    }
}

TN008_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest defense budget ($886B). Replicator, JADC2 programs. Defense VC ecosystem (Anduril, Shield AI, Palantir). Silicon Valley-Pentagon bridge. ITAR constraints."
    },
    "China": {
        "velocity": "high",
        "timeline_shift": "-1yr",
        "notes": "Military-civil fusion strategy. AI weapons development prioritized. Autonomous swarm technology advanced. PLA modernization accelerating. Unique civil-military integration model."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+2yr",
        "notes": "Post-Ukraine defense spending surge. Fragmented procurement. FCAS, Tempest fighter programs. European Defence Fund. France, UK leading."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Defense spending doubling to 2% GDP. Counterstrike capability development. AI-enabled maritime surveillance priority. US-Japan tech alliance deepening."
    },
    "India": {
        "velocity": "medium",
        "timeline_shift": "+2yr",
        "notes": "Defense modernization push. Indigenous defense AI (DRDO). $75B defense budget. Make in India defense manufacturing. Border security AI priority."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+4yr",
        "notes": "Minimal defense AI investment. Brazil largest military in region. Security applications over military."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "South China Sea driving maritime AI demand. Singapore defense tech advanced. ASEAN security cooperation limited."
    },
    "MENA": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "UAE leading in defense AI adoption. Saudi defense spending high. Israel defense AI most advanced in region. Abraham Accords enabling defense tech sharing."
    }
}

TN008_FALSIFICATION = [
    "Autonomous weapons face global treaty ban ratified by US, China, and EU — deployment thesis blocked",
    "AI-enabled targeting produces catastrophic friendly fire incident — trust and deployment reversed",
    "Defense budget cuts >10% in real terms for US — spending thesis weakened",
    "Defense AI procurement remains locked in traditional 7+ year cycles — acquisition reform fails",
    "China achieves AI military parity without US detecting — surprise scenario"
]

# ── TN-013: Securities / Financial Investments ──────────────────────────────

TN013_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "$55T US securities market. Algorithmic trading already 70%+ of equity volume. AI-powered quant funds outperforming discretionary. Wealth management robo-advisors managing $2T+ AUM. Crypto/DeFi regulatory framework emerging. Private credit market $1.5T+ as bank disintermediation continues.",
        "indicators": [
            "US securities market capitalization (baseline: $55T)",
            "Algorithmic trading share of equity volume (baseline: 70%+)",
            "Robo-advisory AUM (baseline: $2T+)",
            "Private credit market size (baseline: $1.5T+)",
            "SEC crypto/DeFi regulatory framework milestones"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "AI-native hedge funds capture significant alpha in alternative data. Robo-advisory reaches mass affluent segment ($500K-$5M). Tokenized securities reach $500B market cap. AI compliance monitoring standard for broker-dealers. Private credit AI underwriting reduces costs 30%.",
        "indicators": [
            "AI-native hedge fund alpha vs traditional quant (benchmark)",
            "Robo-advisory penetration in mass affluent segment",
            "Tokenized securities market cap (target: $500B)",
            "AI compliance tool adoption among broker-dealers",
            "Private credit AI underwriting cost reduction (target: 30%)"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Traditional sell-side research under existential pressure: AI-generated research 80% of routine coverage. IPO process partially automated. AI risk models outperform VaR in stress scenarios. Wealth management firm count -15% as robo-advisors scale.",
        "indicators": [
            "AI-generated research share of routine coverage (target: 80%)",
            "IPO process automation milestones",
            "AI risk model performance vs VaR in stress tests",
            "Wealth management firm count delta (target: -15%)",
            "Sell-side research headcount trends"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Securities employment restructuring: trading floors 50% smaller, research departments 40% smaller. AI-driven market making dominant. Tokenized real-world assets reach $2T+. Family office model enabled by AI at $10M+ threshold (was $100M+). Private equity AI due diligence standard.",
        "indicators": [
            "Trading floor headcount delta (target: -50%)",
            "Research department headcount delta (target: -40%)",
            "Tokenized real-world assets market cap (target: $2T+)",
            "Minimum threshold for AI-enabled family office services (target: $10M)",
            "PE firms using AI due diligence as standard practice (%)"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Securities industry equilibrium: AI handles execution, analysis, compliance. Human premium in relationship management, complex structuring, and judgment-heavy advisory. Average securities firm 30% smaller by headcount, higher revenue/employee. Democratized access to institutional-quality investment tools.",
        "indicators": [
            "Securities industry headcount delta vs 2026 baseline (target: -30%)",
            "Revenue per employee trajectory in securities firms",
            "Institutional-quality tool accessibility for retail investors",
            "Human advisory premium: fee differential for human vs AI advisory",
            "Securities firm count and concentration metrics"
        ]
    }
}

TN013_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "World's largest capital market. NYSE/NASDAQ. Regulatory innovation (SEC). FinTech hub (NYC). Largest wealth management market."
    },
    "China": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Shanghai/Shenzhen exchanges growing. Government-controlled market dynamics. Ant Group/digital yuan implications. Capital controls limit."
    },
    "Japan": {
        "velocity": "low",
        "timeline_shift": "+2yr",
        "notes": "Tokyo Stock Exchange AI trading growing. Conservative investment culture. Aging investor base. Corporate governance reforms."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "MiFID II driving transparency. London still dominant (post-Brexit). Euronext growing. PSD2 Open Banking implications."
    },
    "India": {
        "velocity": "high",
        "timeline_shift": "+1yr",
        "notes": "NSE/BSE growing rapidly. Zerodha model (tech-first brokerage). Young investor demographics. UPI enabling micro-investing."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "B3 (Brazil) leading. Small capital markets. Nubank brokerage. Growing retail investor base."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "Singapore as financial hub. Small but growing capital markets. Crypto adoption high in Philippines."
    },
    "MENA": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Dubai/Abu Dhabi financial centers. Saudi Tadawul IPOs. Islamic finance creates unique AI compliance needs."
    }
}

TN013_FALSIFICATION = [
    "AI quant funds underperform discretionary managers for 3+ years — alpha generation thesis fails",
    "SEC or major regulator bans AI-generated research reports — deployment blocked",
    "Robo-advisory AUM growth stalls below $3T — mass adoption thesis fails",
    "Tokenized securities face regulatory block in US, EU — tokenization thesis delayed",
    "AI risk models fail during market stress event — trust barrier reinforced"
]

# ── TN-005: Administrative Services ─────────────────────────────────────────

TN005_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "9.1M admin/support workers, $540B revenue. Staffing industry disrupted (stocks -53%). AI handling 40% of routine admin tasks (scheduling, data entry, correspondence). Janitorial/security services increasingly automated. Transportation/logistics fragmented: 500K+ trucking establishments, 90% with <6 trucks. Auto repair: 162K establishments, average owner age 58+.",
        "indicators": [
            "BLS QCEW admin/support employment (baseline: 9.1M)",
            "Admin services revenue (baseline: $540B)",
            "Staffing industry stock index performance (baseline: -53%)",
            "Trucking establishment count (baseline: 500K+)",
            "Auto repair establishment count and owner age demographics (baseline: 162K, avg 58+)"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "Staffing agency model transforming: AI matching replaces 50% of recruiter function. Call center employment -20% as AI voice agents scale. Fleet management AI reaches mid-market trucking. Auto repair diagnostics AI reaches 80% accuracy for common issues. Facility management automation standard in commercial buildings.",
        "indicators": [
            "Staffing agency recruiter headcount delta",
            "Call center employment delta (target: -20%)",
            "AI voice agent resolution rate (benchmark)",
            "Auto repair diagnostic AI accuracy (target: 80%)",
            "Fleet management AI adoption in mid-market trucking (%)"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Administrative services employment inflection: -10% in routine clerical roles. AI-managed temp staffing platforms handling 30% of placements. Autonomous towing dispatch operational in 20+ metros. Beauty salon tech platforms managing scheduling, inventory, marketing. Warehouse automation cost parity for mid-size facilities.",
        "indicators": [
            "Routine clerical role employment delta (target: -10%)",
            "AI temp staffing platform placement share (target: 30%)",
            "Autonomous towing dispatch metro count (target: 20+)",
            "Beauty salon tech platform adoption rates",
            "Warehouse automation cost parity metrics for mid-size facilities"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Small business service sector consolidation: auto repair chains (AI-diagnosed), beauty salon platforms, commercial equipment repair networks. Last-mile courier automation begins. Freight optimization AI reduces empty miles 25%. Business associations/charities automate back-office 60%+.",
        "indicators": [
            "Auto repair chain market share vs independents",
            "Freight empty mile reduction (target: 25%)",
            "Last-mile courier automation deployment count",
            "Business association back-office automation rate (target: 60%+)",
            "Small business service consolidation M&A activity"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Admin services restructured: fewer workers in routine roles, more in human-judgment positions. Service sector micro-firms viable with AI (1-person auto shop, solo beauty operator with AI). Transportation efficiency up 30%. Warehouse employment down 25% with robotic automation.",
        "indicators": [
            "Admin services employment composition: routine vs human-judgment roles",
            "Micro-firm viability metrics in service sector (solo operator revenue)",
            "Transportation efficiency gain vs 2026 baseline (target: 30%)",
            "Warehouse employment delta (target: -25%)",
            "Service sector revenue per worker trajectory"
        ]
    }
}

TN005_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest admin services market. Staffing industry $150B+. 500K+ trucking establishments. 162K auto repair shops. Extreme fragmentation across all sub-sectors."
    },
    "China": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Different service structure. Ride-hailing dominant (DiDi). Manufacturing logistics advanced. Government-organized labor markets."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "0yr",
        "notes": "Labor shortage most acute in services. Temp staffing market large (¥6T+). Convenience store services diversifying. Aging workforce driving automation."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1yr",
        "notes": "Strong labor protections slow restructuring. UK staffing market large. Gig economy regulation (Platform Work Directive) shapes dynamics."
    },
    "India": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "Massive informal service sector. Ola, Porter disrupting logistics. Low wages reduce automation ROI. Urban services platforms growing (Urban Company)."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "Informal economy dominant in services. Rappi, 99 in logistics. Low automation penetration."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3yr",
        "notes": "Grab, GoTo providing platform services. Young demographics. Low-cost labor limits automation urgency."
    },
    "MENA": {
        "velocity": "low",
        "timeline_shift": "+2yr",
        "notes": "Migrant labor dominant in services. GCC countries investing in automation to reduce labor dependency. Unique demographic dynamics."
    }
}

TN005_FALSIFICATION = [
    "Staffing industry revenue recovers and grows 10%+/yr — disruption thesis was temporary",
    "AI voice agents achieve <60% resolution rate — call center automation stalls",
    "Auto repair diagnostic AI accuracy stays below 70% — human expertise remains essential",
    "Trucking consolidation reverses: independent operators increase share — fragmentation thesis wrong",
    "Administrative worker wages stagnate (no Baumol pressure) — stored disruption energy dissipates"
]

# ── Enrichment map ───────────────────────────────────────────────────────────

ENRICHMENTS = {
    "TN-009": {
        "year_by_year": TN009_YEAR_BY_YEAR,
        "geographic_variation": TN009_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN009_FALSIFICATION,
    },
    "TN-008": {
        "year_by_year": TN008_YEAR_BY_YEAR,
        "geographic_variation": TN008_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN008_FALSIFICATION,
    },
    "TN-013": {
        "year_by_year": TN013_YEAR_BY_YEAR,
        "geographic_variation": TN013_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN013_FALSIFICATION,
    },
    "TN-005": {
        "year_by_year": TN005_YEAR_BY_YEAR,
        "geographic_variation": TN005_GEOGRAPHIC_VARIATION,
        "falsification_criteria": TN005_FALSIFICATION,
    },
}

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    with open(NARRATIVES_PATH) as f:
        data = json.load(f)

    updated = []
    for narrative in data["narratives"]:
        nid = narrative["narrative_id"]
        if nid in ENRICHMENTS:
            enrichment = ENRICHMENTS[nid]
            narrative["year_by_year"] = enrichment["year_by_year"]
            narrative["geographic_variation"] = enrichment["geographic_variation"]
            narrative["falsification_criteria"] = enrichment["falsification_criteria"]
            narrative["last_updated"] = date.today().isoformat()
            updated.append(nid)
            print(f"  Enriched {nid} — {narrative['name']}")
            print(f"    year_by_year: {len(enrichment['year_by_year'])} periods")
            print(f"    geographic_variation: {len(enrichment['geographic_variation'])} regions")
            print(f"    falsification_criteria: {len(enrichment['falsification_criteria'])} criteria")

    if len(updated) != len(ENRICHMENTS):
        missing = set(ENRICHMENTS.keys()) - set(updated)
        print(f"\n  WARNING: Could not find narratives: {missing}")
        sys.exit(1)

    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone. Enriched {len(updated)} narratives: {', '.join(updated)}")
    print(f"Written to {NARRATIVES_PATH}")

if __name__ == "__main__":
    main()
