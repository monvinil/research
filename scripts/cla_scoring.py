#!/usr/bin/env python3
"""
Competitive Landscape Assessment (CLA) — Dual Ranking System

Adds a second independent ranking ("Opportunity Rank") alongside the existing
Transformation Certainty ranking (5-axis composite).

The CLA measures: "Given that this transformation WILL happen (per 5-axis),
how accessible is this opportunity for a new entrant?"

4 CLA Axes:
  MO — Market Openness (30%): Current market concentration + trend + entry friction
  MA — Moat Architecture (25%): Fragility of incumbent moats (higher = more fragile = better for entrants)
  VD — Value Chain Depth (20%): Number of defensible entry points in the stack
  DV — Disruption Vectors (25%): Plausible mechanisms that create openings for new entrants

Opportunity Composite = (MO*30 + MA*25 + VD*20 + DV*25) / 10

Opportunity Categories:
  WIDE_OPEN:  OPP >= 75 — nascent/highly fragmented, no meaningful incumbents
  ACCESSIBLE: OPP >= 60 — fragmented with breakable moats, multiple entry paths
  CONTESTED:  OPP >= 45 — incumbents exist but disruption vectors are viable
  FORTIFIED:  OPP >= 30 — strong incumbents, limited entry paths
  LOCKED:     OPP < 30  — monopoly/duopoly with structural moats

Dual Ranking Principle:
  Transformation Rank (existing) and Opportunity Rank (CLA) sit side by side.
  They are NEVER merged into a single number.
  A model can be Rank #1 in Transformation and #200 in Opportunity (and vice versa).
  Both rankings carry independent analytical weight.

Input:  data/verified/v3-8_normalized_2026-02-12.json
Output: data/verified/v3-8_normalized_2026-02-12.json (updated in place)
        data/ui/models.json (updated)
        data/ui/dashboard.json (updated)
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
UI_MODELS = UI_DIR / "models.json"
UI_DASHBOARD = UI_DIR / "dashboard.json"

CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}


# ──────────────────────────────────────────────────────────────────────
# CLA Framework Definition
# ──────────────────────────────────────────────────────────────────────

CLA_SYSTEM = {
    "axes": {
        "MO": {
            "name": "Market Openness",
            "weight": 0.30,
            "description": "How open is this market to new entrants? Measures current concentration, entry barriers, and trend direction.",
            "scale": {
                "1-2": "Monopoly/duopoly (>80% top-2 share), regulatory capture, structural barriers",
                "3-4": "Oligopoly (3-5 players dominate), high capital/regulatory barriers",
                "5-6": "Concentrated but with viable entry paths, moderate barriers",
                "7-8": "Fragmented market, many players, low structural barriers",
                "9-10": "Nascent/emerging market, no incumbents, greenfield"
            }
        },
        "MA": {
            "name": "Moat Architecture",
            "weight": 0.25,
            "description": "How fragile are incumbent moats? Higher = more fragile = better for entrants.",
            "scale": {
                "1-2": "Network effects + data moat + regulatory capture (nearly unbreakable)",
                "3-4": "Strong data or network effects with some cracks",
                "5-6": "Moderate moats (brand, scale) that technology could erode",
                "7-8": "Weak moats primarily from switching costs or legacy relationships",
                "9-10": "No meaningful moats, or moats about to be disrupted by technology shift"
            }
        },
        "VD": {
            "name": "Value Chain Depth",
            "weight": 0.20,
            "description": "How many independent defensible positions exist in the value chain? More layers = more ways to enter and differentiate.",
            "scale": {
                "1-2": "Single-layer opportunity, easily commoditized",
                "3-4": "2 layers but unclear differentiation",
                "5-6": "3+ layers with some defensible positions",
                "7-8": "Multiple entry points at different stack levels, each independently viable",
                "9-10": "Deep multi-layer stack where entrants can own unique positions"
            }
        },
        "DV": {
            "name": "Disruption Vectors",
            "weight": 0.25,
            "description": "How many plausible mechanisms exist that create openings for new entrants? Includes technology shifts, regulatory changes, incumbent weaknesses.",
            "scale": {
                "1-2": "No credible disruption path; incumbents have locked in",
                "3-4": "Theoretical disruption but requires massive capital or rare conditions",
                "5-6": "1-2 plausible disruption paths actively in play",
                "7-8": "Multiple disruption vectors simultaneously opening the market",
                "9-10": "Incumbent position actively eroding from multiple simultaneous vectors"
            }
        }
    },
    "composite_formula": "(MO*30 + MA*25 + VD*20 + DV*25) / 10",
    "categories": {
        "WIDE_OPEN": "OPP >= 75 — nascent/highly fragmented, no meaningful incumbents, multiple entry paths",
        "ACCESSIBLE": "OPP >= 60 — fragmented with breakable moats, viable entry strategies exist",
        "CONTESTED": "OPP >= 45 — incumbents exist but real disruption vectors create openings",
        "FORTIFIED": "OPP >= 30 — strong incumbents with real moats, limited entry paths, niche-only",
        "LOCKED": "OPP < 30 — monopoly/duopoly with structural moats, entry requires 100x capital"
    },
    "dual_ranking_principle": (
        "Transformation Rank (5-axis composite) and Opportunity Rank (CLA composite) "
        "are independent analytical systems that sit side by side. They are NEVER merged "
        "into a single number. High Transformation + Low Opportunity = 'will happen but "
        "you can't play it.' Low Transformation + High Opportunity = 'accessible but may "
        "not materialize.' The most actionable models score high on BOTH dimensions."
    )
}


# ──────────────────────────────────────────────────────────────────────
# Manual CLA Overrides — Top 40 Models + Notable Lower-Ranked
# ──────────────────────────────────────────────────────────────────────
# Each entry: (MO, MA, VD, DV, rationale)

MANUAL_CLA = {
    # Rank 1: Amazon 77% share, network + data moat, thin enabling layer
    "MC-V38-44-003": (2, 2, 5, 4,
        "Amazon controls 77% of retail media ($56B). First-party purchase data + retailer exclusivity = near-unbreakable moat. "
        "Enabling tech layer (Criteo, CitrusAd, Kevel) exists but is thin and commoditizable. Google Ads could aggregate mid-market "
        "but doesn't solve the retailer-owned data problem. Entry limited to ad-tech tools, not the network itself."),

    # Rank 2: Amazon Robotics + Symbotic dominate warehouse automation
    "MC-V38-44-002": (3, 3, 6, 5,
        "Amazon Robotics (ex-Kiva) and Symbotic (Walmart) dominate. Capital + IP + installation lock-in form hard moats. "
        "Multi-layer stack (hardware AMR/AGV, pick-path AI, integration, maintenance) provides entry points. "
        "Humanoid robotics (Unitree, AgiBot, Figure) is a real disruption vector but 3-5 years from warehouse deployment. "
        "Open-source robot brains (Alibaba RynnBrain VLA) could democratize software layer."),

    # Rank 3: Nascent AI governance market, no dominant player, regulatory forcing function
    "V3-FEAR-001": (8, 9, 7, 8,
        "Market is nascent ($309M→$15.8B projected, 51x). No dominant AI-native governance platform exists. "
        "Legacy compliance tools (ServiceNow, IBM) haven't pivoted to AI governance. Three diverging regulatory regimes "
        "(US/EU/China) prevent single-winner dynamics and reward specialized expertise. EU AI Act deadline (Aug 2026) "
        "is a hard forcing function. Fear-driven demand (46% adoption plateau) CREATES market rather than just filling it."),

    # Rank 4: CMMC compliance for 220K+ defense contractors, fragmented
    "MC-DEF-011": (6, 7, 6, 7,
        "220K+ Defense Industrial Base companies need CMMC 2.0 certification. Market is fragmented — PreVeil, Coalfire, Forcepoint "
        "are early but no one dominates. FedRAMP certification is both a barrier and a moat for first movers. "
        "CMMC enforcement deadline is a hard forcing function creating urgent demand. Tool + platform + managed service "
        "layers are all viable entry points."),

    # Rank 5: AI code security, growing market, legacy tools can't audit AI-generated code
    "MC-INFO-002": (7, 8, 6, 7,
        "Market growing 40%+ annually. Snyk, Veracode, Checkmarx exist but are scan-based, not AI-native. "
        "82% of developers now use AI coding tools, creating massive new attack surface that legacy tools can't audit. "
        "IDE plugins, CI/CD integration, enterprise dashboards, remediation — multiple layers. "
        "No dominant AI-native code audit platform exists yet."),

    # Rank 6: Data center ops — Schneider Electric, Vertiv have presence but not AI-native
    "MC-INFO-001": (5, 5, 5, 6,
        "Schneider Electric, Vertiv, Siemens have existing DC management tools. But AI-native optimization is genuinely new. "
        "1,000+ smaller DC operators in US are underserved by hyperscaler-grade tools. "
        "Energy constraints (F6) force adoption. AI itself demands more DC capacity, creating recursive demand. "
        "Best entry through mid-market DCs not served by existing vendors."),

    # Rank 7: Defense drone procurement — Anduril, Shield AI, L3Harris dominating
    "V3-DEF-001": (3, 3, 5, 5,
        "Defense procurement barriers, security clearances, ITAR restrictions severely limit entry. "
        "Anduril, Shield AI, L3Harris dominate. Classified tech and government relationships are hard moats. "
        "Commercial drone tech is cheaper and evolving faster — Ukraine conflict proves smaller companies can compete. "
        "AUKUS opens allied markets. Best entry through NATO allies or specific subsystems."),

    # Rank 8: Defense cybersecurity — crowded overall but defense-specific niche viable
    "V3-DEF-003": (5, 5, 6, 6,
        "Cyber market broadly is crowded (CrowdStrike, Palo Alto dominate enterprise). But defense-specific AI-native "
        "cybersecurity is less crowded. CMMC certification creates barrier-as-moat. "
        "Expanding attack surface + AI-generated attacks require AI defense. Defense budgets growing."),

    # Rank 9: Intelligence fusion — Palantir fortress
    "V3-DEF-002": (3, 2, 4, 4,
        "Palantir dominates ($2.65B revenue, 90%+ of classified analytics). Clearance requirements severe. "
        "Government relationships deeply entrenched. Palantir's data moat + classified environment access = very strong moats. "
        "Only entry is through very specific niches (tactical-edge fusion for small units) or allied nations. "
        "Open-source LLMs could democratize some fusion but classified data handling limits this severely."),

    # Rank 10: Grid optimization — 3,000+ fragmented utilities, legacy SCADA
    "MC-UTL-001": (6, 6, 6, 7,
        "US has 3,000+ utilities, most served by legacy SCADA systems. AutoGrid, Opus One, Stem are early AI entrants "
        "but market is fragmented. Legacy SCADA vendors (Siemens, ABB) slow to innovate on AI-native optimization. "
        "Grid complexity doubling (bidirectional + DC load spikes). IRA renewable targets force adoption. "
        "Long sales cycles (18-24mo) are the main barrier, not technology."),

    # Rank 11: Cashierless checkout — Amazon retreating from external JWO
    "MC-V38-44-001": (4, 5, 5, 6,
        "Amazon Just Walk Out dominates mindshare but is retreating from external licensing (shifting to Smart Carts). "
        "Grabango, Zippin, Trigo viable in mid-market grocery. Computer vision IP creates moderate moat. "
        "Store retrofit installation creates switching costs. Self-checkout fatigue creates demand for frictionless alternatives. "
        "Amazon's strategic retreat from external JWO is the key opening."),

    # Rank 12: Securities compliance RegTech — fragmented, no AI-native dominant player
    "MC-V37-523-002": (7, 7, 6, 7,
        "RegTech market fragmented. No dominant AI-native compliance platform for broker-dealers/RIAs. "
        "Legacy compliance tools (NICE Actimize, Broadridge) are heavyweight, not AI-native. "
        "SEC/FINRA enforcement increasing. 80% of compliance work automatable. "
        "AI can monitor 100% of communications vs legacy 2-5% sampling — 20-50x coverage advantage."),

    # Rank 13: AI OS for micro-firms — emerging category, no incumbent
    "V3-EMRG-001": (9, 9, 8, 9,
        "Category barely exists. No incumbent. '1-5 person firm with AI employees' is an emerging category. "
        "No moats to break — this is greenfield. Finance, ops, legal, customer service, project management — "
        "many layers for the AI OS. Every SaaS tool (QuickBooks, Salesforce) is a potential vector to build from, "
        "but none are building the integrated AI OS. Highest opportunity score in entire inventory."),

    # Rank 14: Healthcare AI compliance — fragmented, regulatory complexity is the driver
    "C7-RMB-HC-01": (7, 7, 6, 7,
        "Multi-state healthcare compliance is fragmented. Existing platforms (MedTrainer, Symplr) aren't AI-native. "
        "FDA deregulation (Jan 6, 2026) + state-level AI regulation divergence = complexity that demands specialized tools. "
        "Similar dynamics to general AI governance (#3) but specialized for healthcare."),

    # Rank 15: Healthcare full-service replacement — large incumbents exist
    "MC-V37-62-003": (5, 5, 6, 6,
        "Healthcare services market has large incumbents (HCA, UHS, DaVita). AI-native full replacement is new. "
        "Regulatory moats (licensure, insurance networks) are significant. AI can automate admin (30%+ of costs). "
        "Best entry through admin automation, not clinical. Clinical AI requires FDA pathway."),

    # Rank 16: RIA rollup — 15,000+ fragmented firms, mass retirement wave
    "MC-V37-523-001": (7, 7, 4, 6,
        "15,000+ RIAs in US, highly fragmented. 31% of advisors retiring by 2029. Average firm $150M AUM. "
        "Legacy RIA tech (Orion, Black Diamond) is tired. Relationships are advisor-personal, not platform-locked. "
        "Execution-heavy (need to do deals). Silver Tsunami creates structural window."),

    # Rank 17: Content authentication — nascent, standards still evolving
    "MC-INFO-003": (7, 8, 6, 7,
        "C2PA coalition exists but market is nascent. No dominant platform. Standards still evolving. "
        "Deepfakes escalating — elections, journalism, legal proceedings all need authentication. "
        "Capture, distribution, verification, marketplace — multiple viable layers. "
        "Regulatory mandates likely coming (EU already drafting)."),

    # Rank 18: AI IB analyst replacement — big banks build in-house
    "MC-V37-523-003": (5, 4, 5, 6,
        "Goldman, JPM, Morgan Stanley building in-house AI tools. But mid-market advisory (Houlihan Lokey tier) "
        "underserved. Data access (CapIQ, Bloomberg) and IB brand are strong moats. "
        "60-70% of entry-level IB work automatable. Opportunity is selling to mid-market advisory and PE firms "
        "who can't afford to build. Banks won't buy external."),

    # Rank 19: Single CNC shop acquisition — 150K+ fragmented shops
    "C7-AM-MFG-01": (9, 9, 4, 8,
        "150,000+ machine shops in US, highly fragmented. Average owner age 57, most no succession plan. "
        "No moats to speak of — local relationships and reputation are it. "
        "AI+cobot upgrade creates competitive advantage from zero. Cobot ROI at 6-18mo. "
        "Classic search fund + tech upgrade. Execution-heavy but wide open."),

    # Rank 20: Nuclear plant AI — only 93 plants, extreme regulatory barriers
    "MC-UTL-002": (4, 4, 5, 5,
        "Only 93 nuclear plants in US. Vendor relationships with Framatome, Westinghouse, GE-Hitachi deeply entrenched. "
        "NRC certification process is multi-year. Nuclear renaissance (SMRs, 80-year extensions) creates some new demand. "
        "Entry through SMR builders (NuScale, Kairos) who need modern AI tools. Very small addressable market."),

    # Rank 21: AI bookkeeping for SMBs — massively fragmented, CPA shortage
    "C7-DC-FIN-01": (8, 7, 5, 7,
        "600,000+ bookkeeping firms, massively fragmented. CPA pipeline collapse (-33%) creates structural demand. "
        "Intuit/QuickBooks dominates self-service tools but AI-native full-service is different category. "
        "AI can handle routine bookkeeping entirely. SMBs can't hire bookkeepers at any price in many markets."),

    # Rank 22: Financial services RegTech (earlier vintage than #12)
    "MC-V35-5239-001": (7, 7, 5, 7,
        "Similar dynamics to MC-V37-523-002. RegTech for financial services is fragmented and growing. "
        "No dominant AI-native platform. Legacy compliance tools are heavyweight. Regulatory pressure mounting."),

    # Rank 23: Defense cloud infrastructure — hyperscaler fortress
    "MC-DEF-012": (3, 3, 5, 4,
        "AWS GovCloud, Azure Government, Google DoD dominate. IL-5/IL-6 certification extremely expensive ($100M+). "
        "Capital requirements ($B+), security certifications, government relationships are massive moats. "
        "Edge/tactical compute is the only viable entry for startups. But even there, Palantir, Anduril, CACI are ahead."),

    # Rank 24: Insurance claims AI — moderate incumbent presence
    "MC-V35-5223-001": (6, 6, 5, 6,
        "Insurance tech market has incumbents (Guidewire, Duck Creek) but AI-native claims processing is new. "
        "Data access and carrier relationships are moderate moats. AI processes claims 10x faster. "
        "InsurTech wave already disrupted distribution; AI processing is the next wave."),

    # Rank 25: PE portfolio AI operations — no incumbent platform
    "MC-V37-55-002": (7, 8, 6, 7,
        "PE firms ($6T+ AUM) have no dominant operations platform. Excel + consultants is the status quo. "
        "No incumbent SaaS platform for PE portfolio ops. PE firms managing 5-10x more companies per partner. "
        "AI enables this scale. Strong budget and urgency among buyers."),

    # Rank 26: Battery storage — capital-intensive, Fluence/Tesla dominant
    "MC-UTL-003": (5, 5, 6, 6,
        "Fluence (Siemens/AES), Tesla Energy, NextEra dominate grid storage. Capital-intensive ($100M+ per project). "
        "IRA subsidies help. AI management layer is the most accessible entry point (vs project development). "
        "Grid complexity and renewable intermittency drive adoption."),

    # Rank 27: RIA AI operating system — pure SaaS approach
    "MC-V37-523-004": (7, 7, 6, 7,
        "No dominant AI-native RIA platform. Legacy platforms (Orion, Tamarac) not AI-native. "
        "Client comm, portfolio management, rebalancing, compliance, reporting — rich layer stack. "
        "Advisor retirements + fee compression + AI enabling 1:5x client scaling."),

    # Rank 28: Wholesale trade AI replacement — extremely fragmented
    "PC8-FSR-WHOLESALE-01": (8, 8, 5, 8,
        "Wholesale trade (NAICS 4251) extremely fragmented with 360K+ establishments. "
        "Personal-relationship moats are breakable. Digital wholesale platforms (Faire) already disrupting. "
        "AI adds prediction/pricing on top. Multiple entry points at different parts of the value chain."),

    # Rank 29: Home health AI — large incumbents but many small agencies
    "MC-V37-62-001": (6, 6, 5, 6,
        "Home health has large players (Amedisys, LHC Group) but thousands of small agencies. "
        "Medicare certification + state licensing are barriers. Smaller agencies are technology-poor. "
        "Aging population, hospital-at-home trend, labor shortage create multiple disruption vectors."),

    # Rank 30: Military predictive maintenance — OEM data lock-in
    "V3-DEF-010": (4, 4, 5, 5,
        "Lockheed Martin, Raytheon, BAE own maintenance contracts. OEM data access is critical bottleneck. "
        "ITAR restrictions, long-term contracts are hard moats. "
        "Entry through DoD-mandated data sharing programs or specific non-OEM subsystems."),

    # ── Notable lower-ranked models with extreme CLA profiles ──

    # Rank 33: SaaS rollup — fragmented, distress-driven
    "MC-INFO-006": (8, 7, 4, 7,
        "Mid-market SaaS companies facing margin pressure from AI commoditization. "
        "Highly fragmented (thousands of targets). AI enables radical margin improvement post-acquisition."),

    # Rank 34: Military supply chain — Lockheed fortress
    "V3-DEF-004": (3, 3, 5, 5,
        "Military supply chain dominated by prime contractors. Clearance requirements, OEM relationships. "
        "AI optimization needed but primes control the contracts."),

    # Rank 36: Defense satellite imagery — NRO/NGA relationships critical
    "V3-DEF-007": (4, 4, 5, 5,
        "Commercial satellite imagery for defense intelligence. Planet Labs, Maxar, BlackSky have data moats. "
        "NRO/NGA relationships critical. AI processing layer more accessible than data layer."),

    # Rank 37: Food producer acquisition — highly fragmented
    "C7-AM-FOOD-01": (9, 9, 4, 7,
        "Specialty food production extremely fragmented. Owner retirements creating acquisition pipeline. "
        "No moats — local brand and recipes. AI+automation upgrade creates margin expansion."),

    # Rank 38: Manufacturing rollup — fragmented machine shops
    "C7-RC-MFG-01": (9, 8, 4, 8,
        "Machine shop rollup — 150K+ shops, average owner 57. No moats. "
        "Scale + cobot deployment creates operational advantage. Execution-heavy."),

    # Rank 39: Data marketplace — standards still forming
    "MC-INFO-007": (6, 7, 7, 6,
        "Data marketplace connecting owners with AI trainers. Snowflake, Databricks have platform position. "
        "But AI training data marketplace is genuinely new. Standards evolving. Multiple viable layers."),

    # ── Retail deep dive cards ──
    "MC-V38-44-004": (7, 7, 5, 7,
        "AI demand forecasting for retail — fragmented market. Legacy ERPs (SAP, Oracle) slow to adapt. "
        "Retailers desperately need better forecasting (10-15% shrink reduction). Multiple entry points."),

    "MC-V38-44-005": (6, 6, 6, 6,
        "Dynamic pricing and markdown optimization. Some incumbents (Revionics, Blue Yonder) but not AI-native. "
        "Retailers need real-time pricing. Moderate barriers, moderate opportunity."),

    "MC-V38-44-006": (5, 5, 5, 6,
        "Last-mile delivery optimization. FedEx, UPS, Amazon dominate. Route optimization AI is competitive. "
        "But final-mile autonomous delivery (Nuro, Starship) could disrupt."),

    "MC-V38-44-007": (7, 7, 5, 7,
        "Smart inventory and supply chain AI for retailers. Fragmented mid-market. "
        "Amazon has best-in-class but mid-market retailers are underserved."),

    "MC-V38-44-008": (4, 4, 5, 5,
        "Autonomous store format (fully cashierless, robotic restocking). Amazon Go proved concept but scaling slowly. "
        "Capital-intensive, technology risk. Only viable for high-traffic urban locations."),

    "MC-V38-44-009": (6, 6, 5, 6,
        "Retail workforce AI scheduling and optimization. Some incumbents (Legion, Quinyx) but AI-native is new. "
        "15.5M retail workers need scheduling. Moderate barriers."),

    "MC-V38-44-010": (7, 7, 5, 7,
        "Returns management and reverse logistics AI. Fragmented, high-waste problem ($816B in returns). "
        "No dominant AI-native player. Multiple entry points (SaaS, marketplace, managed service)."),

    "MC-V38-44-011": (6, 6, 5, 6,
        "Retail computer vision analytics (in-store behavior, planogram compliance). "
        "Some incumbents but market growing rapidly. Privacy concerns moderate entry."),

    "MC-V38-44-012": (5, 5, 4, 5,
        "Social commerce and live shopping platform. TikTok Shop, Meta dominate. "
        "Platform concentration makes independent entry difficult."),

    # ── Healthcare deep dive cards ──
    "MC-V38-62-001": (6, 6, 6, 7,
        "AI clinical decision support for hospitals. FDA deregulation (Jan 6, 2026) opens massive market. "
        "Epic/Cerner have EHR moats but CDS layer is new. 71% of hospitals deploying predictive AI."),

    "MC-V38-62-002": (7, 7, 5, 7,
        "AI medical coding and billing automation. 30%+ of healthcare costs are admin. "
        "Market fragmented among hundreds of billing companies. AI can automate 80%+ of coding."),

    "MC-V38-62-003": (5, 5, 5, 6,
        "AI-powered telehealth and remote monitoring platform. Teladoc, Amwell have market position "
        "but post-COVID volume declining. AI differentiation is the next wave. CMS reimbursement uncertain."),

    "MC-V38-62-004": (6, 6, 5, 6,
        "AI nursing workflow optimization. Nursing shortage (250K RN gap by 2030) creates urgent demand. "
        "Hospital IT departments are conservative buyers. Multiple workflow layers."),

    "MC-V38-62-005": (7, 8, 6, 7,
        "AI-native mental health platform. Market fragmented, massive demand (youth mental health crisis). "
        "Existing telehealth providers not AI-native. Low regulatory barrier for non-clinical tools."),

    "MC-V38-62-006": (5, 5, 5, 6,
        "AI drug discovery and development acceleration. Dominated by well-funded startups "
        "(Recursion, Insilico, Isomorphic Labs). Capital-intensive. But pharma partnerships accessible."),

    "MC-V38-62-007": (7, 7, 5, 7,
        "AI-powered home health and aging-in-place technology. Fragmented market. "
        "Aging demographics create massive demand. No dominant AI-native platform."),

    "MC-V38-62-008": (6, 6, 5, 6,
        "Healthcare AI workforce training and certification platform. Growing need as AI deploys. "
        "No dominant player. Regulatory requirements vary by state."),

    "MC-V38-62-009": (6, 7, 6, 6,
        "AI-powered medical imaging analysis. Some incumbents (Viz.ai, Aidoc) but market growing rapidly. "
        "FDA clearance required but pathway well-established. Multiple sub-specialties."),

    "MC-V38-62-010": (7, 7, 5, 7,
        "Healthcare supply chain and pharmacy AI optimization. Fragmented distribution. "
        "Drug shortage crisis creates urgent demand. Multiple entry points."),

    "MC-V38-62-011": (5, 5, 5, 5,
        "AI hospital operations and capacity management. Epic has strong position through EHR integration. "
        "But standalone AI optimization layer is emerging. Long sales cycles."),

    "MC-V38-62-012": (6, 6, 5, 6,
        "AI-powered healthcare PE portfolio optimization. PE owns 30%+ of physician practices. "
        "AI enables operational improvement across portfolio. Niche but well-funded buyers."),
}


# ──────────────────────────────────────────────────────────────────────
# Heuristic Scoring Engine
# ──────────────────────────────────────────────────────────────────────
# For models without manual overrides, compute CLA from model attributes.

# Architecture → base CLA scores (MO, MA, VD, DV)
ARCH_DEFAULTS = {
    "full_service_replacement":   (6, 6, 6, 7),
    "vertical_saas":              (7, 7, 5, 7),
    "platform_infrastructure":    (5, 5, 6, 6),
    "platform":                   (5, 5, 7, 5),
    "data_compounding":           (5, 4, 5, 5),
    "acquire_and_modernize":      (8, 8, 4, 7),
    "rollup_consolidation":       (7, 7, 4, 6),
    "regulatory_moat_builder":    (6, 6, 5, 6),
    "marketplace_network":        (5, 4, 6, 5),
    "saas":                       (6, 6, 5, 6),
    "arbitrage_window":           (7, 8, 3, 7),
    "physical_production_ai":     (6, 6, 6, 6),
    "service_platform":           (6, 6, 5, 6),
    "marketplace_platform":       (5, 5, 6, 5),
    "product_platform":           (5, 5, 5, 5),
    "marketplace":                (5, 5, 5, 5),
    "service":                    (6, 6, 4, 5),
    "automation":                 (5, 5, 6, 6),
    "project_developer":          (5, 5, 5, 5),
    "managed_service":            (6, 6, 4, 5),
    "network_platform":           (4, 4, 6, 5),
    "platform_saas":              (6, 6, 5, 6),
    "roll_up_modernize":          (7, 7, 4, 6),
    "platform_marketplace":       (5, 5, 6, 5),
    "rollup":                     (7, 7, 4, 6),
    "physical_product_platform":  (5, 5, 5, 5),
    "distress_operator":          (8, 8, 3, 7),
    "advisory":                   (6, 6, 4, 5),
    "marketplace_optimizer":      (5, 5, 5, 5),
    "project_development":        (5, 5, 5, 5),
    "infrastructure_platform":    (5, 5, 6, 6),
    "hybrid_service":             (6, 6, 5, 6),
    "advisory_platform":          (6, 6, 5, 6),
    "academy_platform":           (7, 7, 5, 6),
    "hardware_plus_saas":         (5, 5, 5, 5),
    "platform_service":           (6, 6, 5, 6),
    "fear_economy_capture":       (7, 8, 5, 7),
    "product":                    (5, 5, 4, 5),
    "geographic_arbitrage":       (7, 7, 4, 6),
    # v3-18 new architectures (Experiment 1 inversions)
    "open_core_ecosystem":        (8, 7, 9, 8),   # free product → wide open, deep value chain
    "outcome_based":              (7, 6, 7, 8),   # outcome alignment opens markets
    "coordination_protocol":      (6, 8, 6, 7),   # standard-setting barrier, once set = wide moat
}

# NAICS 2-digit sector adjustments: (MO_adj, MA_adj, VD_adj, DV_adj)
SECTOR_ADJUSTMENTS = {
    # Defense sectors — procurement barriers, clearance requirements
    "33": (0, 0, 0, 0),  # Manufacturing — neutral, depends on sub-sector
    "34": (-1, -1, 0, 0),  # Defense manufacturing
    # Professional services — generally fragmented, AI disruption
    "54": (1, 0, 0, 1),
    # Healthcare — regulatory barriers but massive transformation
    "62": (-1, 0, 0, 1),
    # Finance — regulatory complexity but fragmented
    "52": (0, -1, 0, 1),
    # Education — enrollment cliff creates openings
    "61": (1, 1, 0, 0),
    # Utilities — regulated monopolies
    "22": (-1, -1, 0, 0),
    # Information — AI-native disruption
    "51": (1, 1, 0, 1),
    # Real estate — fragmented, distress creating openings
    "53": (1, 0, 0, 1),
    # Admin/support services — highly fragmented
    "56": (1, 1, 0, 0),
    # Wholesale — fragmented, AI disintermediation
    "42": (1, 1, 0, 1),
    # Retail — Amazon dominance for e-commerce, fragmented for physical
    "44": (0, 0, 0, 0),
    "45": (0, 0, 0, 0),
    # Construction — trades shortage, technology-poor
    "23": (1, 1, 0, 0),
    # Other services — fragmented
    "81": (1, 1, 0, 0),
    # Management of companies — PE driven
    "55": (0, 0, 0, 1),
    # Manufacturing (food, etc.)
    "31": (1, 1, 0, 0),
    "32": (0, 0, 0, 0),
    # Transportation
    "48": (0, 0, 0, 0),
    # Mining — capital-intensive
    "21": (-1, -1, 0, 0),
}

# Category adjustments
CATEGORY_ADJUSTMENTS = {
    "FEAR_ECONOMY": (1, 1, 0, 1),        # New markets, no incumbents, fear creates openings
    "EMERGING_CATEGORY": (2, 2, 0, 1),    # Nascent markets
    "STRUCTURAL_WINNER": (0, 0, 0, -1),   # Harder to disrupt what's structurally necessary
    "TIMING_ARBITRAGE": (0, 1, 0, 1),     # Windows opening
    "CAPITAL_MOAT": (0, 0, 0, 0),         # Neutral — could be capital-efficient entrant or incumbent
    "PARKED": (-1, 0, 0, -1),             # Less attractive
    "CONDITIONAL": (0, 0, 0, 0),          # Neutral
    "FORCE_RIDER": (0, 0, 0, 0),          # Neutral
}

# Defense-specific model IDs — extra barrier penalty
DEFENSE_MODEL_PREFIXES = ("V3-DEF-", "MC-DEF-")


def clamp(val, lo=1, hi=10):
    return max(lo, min(hi, val))


def heuristic_cla(model):
    """Compute CLA scores heuristically from model attributes."""
    arch = model.get("architecture", "")
    base = ARCH_DEFAULTS.get(arch, (5, 5, 5, 5))
    mo, ma, vd, dv = base

    # Sector adjustment
    naics = str(model.get("sector_naics", ""))
    naics2 = naics[:2] if len(naics) >= 2 else ""
    if naics2 in SECTOR_ADJUSTMENTS:
        adj = SECTOR_ADJUSTMENTS[naics2]
        mo += adj[0]
        ma += adj[1]
        vd += adj[2]
        dv += adj[3]

    # Defense-specific penalty
    mid = model.get("id", "")
    if any(mid.startswith(prefix) for prefix in DEFENSE_MODEL_PREFIXES):
        mo -= 2
        ma -= 2

    # Category adjustment (use primary_category)
    primary_cat = model.get("primary_category", "")
    if primary_cat in CATEGORY_ADJUSTMENTS:
        adj = CATEGORY_ADJUSTMENTS[primary_cat]
        mo += adj[0]
        ma += adj[1]
        vd += adj[2]
        dv += adj[3]

    # Multi-category bonus: if model has FEAR_ECONOMY or EMERGING_CATEGORY in categories list
    cats = model.get("category", [])
    if isinstance(cats, list):
        for cat in cats:
            if cat == "FEAR_ECONOMY" and primary_cat != "FEAR_ECONOMY":
                mo += 1
                dv += 1
            if cat == "EMERGING_CATEGORY" and primary_cat != "EMERGING_CATEGORY":
                mo += 1

    # Competitive density adjustment (if available)
    cd = model.get("competitive_density", {})
    if isinstance(cd, dict):
        status = cd.get("status", "")
        if status == "zero":
            mo += 2
            ma += 2
        elif status == "low":
            mo += 1
            ma += 1
        elif status == "crowded":
            mo -= 2
            dv -= 1

    # One-liner keyword analysis for concentration signals
    one_liner = (model.get("one_liner") or "").lower()
    macro = (model.get("macro_source") or "").lower()
    combined_text = one_liner + " " + macro

    # Concentration keywords → lower MO
    if any(kw in combined_text for kw in ["amazon", "google", "microsoft", "meta", "apple"]):
        mo -= 1
    if any(kw in combined_text for kw in ["monopoly", "dominant", "controls", "dominates"]):
        mo -= 1
        ma -= 1
    if any(kw in combined_text for kw in ["77%", "80%", "90%"]):
        mo -= 2

    # Fragmentation keywords → higher MO
    if any(kw in combined_text for kw in ["fragmented", "highly fragmented", "thousands of"]):
        mo += 1
        ma += 1
    if any(kw in combined_text for kw in ["retiring", "succession", "silver tsunami"]):
        mo += 1
        dv += 1
    if any(kw in combined_text for kw in ["nascent", "emerging", "greenfield", "no incumbent"]):
        mo += 1
        ma += 1

    # Regulatory keywords → barrier signal
    if any(kw in combined_text for kw in ["compliance", "regulatory", "mandate", "requirement"]):
        dv += 1  # regulatory change creates disruption vectors

    mo = clamp(mo)
    ma = clamp(ma)
    vd = clamp(vd)
    dv = clamp(dv)

    # Build rationale
    rationale = f"Heuristic: arch={arch}, NAICS={naics}, cat={primary_cat}"
    if any(mid.startswith(p) for p in DEFENSE_MODEL_PREFIXES):
        rationale += ". Defense procurement barriers applied."

    return mo, ma, vd, dv, rationale


def calc_opp_composite(mo, ma, vd, dv):
    return round((mo * 30 + ma * 25 + vd * 20 + dv * 25) / 10, 2)


def classify_opportunity(opp):
    if opp >= 75:
        return "WIDE_OPEN"
    elif opp >= 60:
        return "ACCESSIBLE"
    elif opp >= 45:
        return "CONTESTED"
    elif opp >= 30:
        return "FORTIFIED"
    else:
        return "LOCKED"


def score_model(model):
    """Score a single model on CLA axes. Use manual override if available, else heuristic."""
    mid = model.get("id", "")
    if mid in MANUAL_CLA:
        mo, ma, vd, dv, rationale = MANUAL_CLA[mid]
    else:
        mo, ma, vd, dv, rationale = heuristic_cla(model)

    opp = calc_opp_composite(mo, ma, vd, dv)
    opp_cat = classify_opportunity(opp)

    return {
        "scores": {"MO": mo, "MA": ma, "VD": vd, "DV": dv},
        "composite": opp,
        "category": opp_cat,
        "rationale": rationale,
    }


def build_slim_model(m):
    """Build UI-facing slim model with dual ranking."""
    cla = m.get("cla", {})
    return {
        "rank": m["rank"],
        "opportunity_rank": m.get("opportunity_rank"),
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "opportunity_composite": cla.get("composite"),
        "category": m.get("primary_category", m["category"][0] if m["category"] else "PARKED"),
        "opportunity_category": cla.get("category"),
        "categories": m["category"],
        "scores": m["scores"],
        "cla_scores": cla.get("scores"),
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "source_batch": m.get("source_batch"),
        "new_in_v36": m.get("new_in_v36", False),
        "one_liner": m.get("one_liner"),
    }


def main():
    print("=" * 70)
    print("CLA SCORING: Competitive Landscape Assessment — Dual Ranking System")
    print("=" * 70)
    print()

    # Load normalized file
    print("Loading normalized inventory...")
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"  Loaded {len(models)} models")
    print()

    # Score all models
    print("Scoring CLA for all models...")
    manual_count = 0
    heuristic_count = 0

    for model in models:
        cla = score_model(model)
        model["cla"] = cla

        if model["id"] in MANUAL_CLA:
            manual_count += 1
        else:
            heuristic_count += 1

    print(f"  Manual overrides: {manual_count}")
    print(f"  Heuristic scores: {heuristic_count}")
    print()

    # Sort by OPP composite for Opportunity Rank (descending)
    models_by_opp = sorted(models, key=lambda m: (-m["cla"]["composite"], m["id"]))
    for i, m in enumerate(models_by_opp, 1):
        # Find this model in the original list and set opportunity_rank
        m["opportunity_rank"] = i

    # Re-sort by transformation composite (original order) for the file
    models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Compute OPP stats
    opp_composites = [m["cla"]["composite"] for m in models]
    opp_stats = {
        "max": max(opp_composites),
        "min": min(opp_composites),
        "mean": round(statistics.mean(opp_composites), 2),
        "median": round(statistics.median(opp_composites), 2),
    }

    opp_cat_dist = Counter(m["cla"]["category"] for m in models)
    opp_comp_dist = {
        "above_75": sum(1 for c in opp_composites if c >= 75),
        "60_to_75": sum(1 for c in opp_composites if 60 <= c < 75),
        "45_to_60": sum(1 for c in opp_composites if 45 <= c < 60),
        "30_to_45": sum(1 for c in opp_composites if 30 <= c < 45),
        "below_30": sum(1 for c in opp_composites if c < 30),
    }

    # Add CLA system to rating_system
    data["rating_system"]["cla_system"] = CLA_SYSTEM

    # Add OPP summary
    data["summary"]["opportunity_stats"] = opp_stats
    data["summary"]["opportunity_distribution"] = opp_comp_dist
    data["summary"]["opportunity_category_distribution"] = dict(sorted(opp_cat_dist.items()))

    # Write updated normalized file
    print(f"Writing updated normalized file ({len(models)} models)...")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Write UI models.json
    print("Writing UI models.json...")
    ui_models = [build_slim_model(m) for m in models]
    ui_output = {
        "cycle": data["cycle"],
        "date": data["date"],
        "total": len(models),
        "dual_ranking": True,
        "summary": {
            "total_models": len(models),
            "existing_models": data["summary"].get("existing_models", 0),
            "composite_stats": data["summary"].get("composite_stats", {}),
            "composite_distribution": data["summary"].get("composite_distribution", {}),
            "primary_category_distribution": data["summary"].get("primary_category_distribution", {}),
            "opportunity_stats": opp_stats,
            "opportunity_distribution": opp_comp_dist,
            "opportunity_category_distribution": dict(sorted(opp_cat_dist.items())),
            "source_batch_counts": data["summary"].get("source_batch_counts", {}),
        },
        "cla_system": CLA_SYSTEM,
        "models": ui_models,
    }
    with open(UI_MODELS, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)

    # Update dashboard.json
    print("Updating dashboard.json...")
    with open(UI_DASHBOARD) as f:
        dashboard = json.load(f)

    # Add CLA data to dashboard
    dashboard["dual_ranking"] = True
    dashboard["cla_system"] = CLA_SYSTEM
    dashboard["opportunity_stats"] = opp_stats
    dashboard["opportunity_distribution"] = opp_comp_dist
    dashboard["opportunity_category_distribution"] = dict(sorted(opp_cat_dist.items()))

    # Build top 20 by opportunity
    top20_opp = []
    for m in models_by_opp[:20]:
        top20_opp.append({
            "opportunity_rank": m["opportunity_rank"],
            "transformation_rank": m["rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m["cla"]["composite"],
            "category": m.get("primary_category", "?"),
            "opportunity_category": m["cla"]["category"],
            "cla_scores": m["cla"]["scores"],
        })
    dashboard["top_20_by_opportunity"] = top20_opp

    # Build top 20 "actionable" — high on BOTH dimensions
    # Use geometric mean of transformation and opportunity composites
    actionable = sorted(models,
        key=lambda m: -(m["composite"] * m["cla"]["composite"]) ** 0.5)
    top20_actionable = []
    for m in actionable[:20]:
        geo_mean = round((m["composite"] * m["cla"]["composite"]) ** 0.5, 2)
        top20_actionable.append({
            "actionable_score": geo_mean,
            "transformation_rank": m["rank"],
            "opportunity_rank": m["opportunity_rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m["cla"]["composite"],
            "category": m.get("primary_category", "?"),
            "opportunity_category": m["cla"]["category"],
        })
    dashboard["top_20_actionable"] = top20_actionable

    # Update the top_20_by_composite to include opportunity data
    top20_trans = []
    for m in models[:20]:
        top20_trans.append({
            "transformation_rank": m["rank"],
            "opportunity_rank": m["opportunity_rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m["cla"]["composite"],
            "category": m.get("primary_category", "?"),
            "opportunity_category": m["cla"]["category"],
            "scores": m["scores"],
            "cla_scores": m["cla"]["scores"],
        })
    dashboard["top_20_by_composite"] = top20_trans

    # Fix the ID discrepancy while we're here
    # (Rank 2 was incorrectly listed as MC-V38-44-005 in some places)

    with open(UI_DASHBOARD, "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    # ── Print Summary ──
    print()
    print("=" * 70)
    print("CLA SCORING COMPLETE — DUAL RANKING SYSTEM ACTIVE")
    print("=" * 70)
    print()

    print("  Opportunity Statistics:")
    print(f"    Max:    {opp_stats['max']}")
    print(f"    Min:    {opp_stats['min']}")
    print(f"    Mean:   {opp_stats['mean']}")
    print(f"    Median: {opp_stats['median']}")
    print()

    print("  Opportunity Distribution:")
    for bucket, count in opp_comp_dist.items():
        print(f"    {bucket:>10s}: {count}")
    print()

    print("  Opportunity Categories:")
    for cat in sorted(opp_cat_dist.keys()):
        print(f"    {cat:<15s}: {opp_cat_dist[cat]}")
    print()

    print("  Top 20 by TRANSFORMATION (with Opportunity Rank):")
    print(f"  {'T#':>3s}  {'O#':>3s}  {'TComp':>6s}  {'OComp':>6s}  {'TCat':<22s}  {'OCat':<12s}  {'ID':<30s}  Name")
    for m in models[:20]:
        print(f"  {m['rank']:3d}  {m['opportunity_rank']:3d}  "
              f"{m['composite']:6.2f}  {m['cla']['composite']:6.2f}  "
              f"{m.get('primary_category', '?'):<22s}  {m['cla']['category']:<12s}  "
              f"{m['id']:<30s}  {m['name'][:40]}")
    print()

    print("  Top 20 by OPPORTUNITY (with Transformation Rank):")
    print(f"  {'O#':>3s}  {'T#':>3s}  {'OComp':>6s}  {'TComp':>6s}  {'OCat':<12s}  {'TCat':<22s}  {'ID':<30s}  Name")
    for m in models_by_opp[:20]:
        print(f"  {m['opportunity_rank']:3d}  {m['rank']:3d}  "
              f"{m['cla']['composite']:6.2f}  {m['composite']:6.2f}  "
              f"{m['cla']['category']:<12s}  {m.get('primary_category', '?'):<22s}  "
              f"{m['id']:<30s}  {m['name'][:40]}")
    print()

    print("  Top 20 ACTIONABLE (high on both dimensions):")
    print(f"  {'Geo':>6s}  {'T#':>3s}  {'O#':>3s}  {'TComp':>6s}  {'OComp':>6s}  {'ID':<30s}  Name")
    for a in top20_actionable:
        print(f"  {a['actionable_score']:6.2f}  {a['transformation_rank']:3d}  "
              f"{a['opportunity_rank']:3d}  {a['composite']:6.2f}  "
              f"{a['opportunity_composite']:6.2f}  "
              f"{a['id']:<30s}  {a['name'][:40]}")
    print()

    # Show biggest rank deltas (transformation rank vs opportunity rank)
    print("  Biggest Rank Divergences (Transformation vs Opportunity):")
    rank_deltas = [(m, m["rank"] - m["opportunity_rank"]) for m in models]
    rank_deltas.sort(key=lambda x: x[1])

    print("  Most OVERRANKED by transformation (high T rank, low O rank = locked market):")
    for m, delta in rank_deltas[:5]:
        print(f"    T#{m['rank']:3d} → O#{m['opportunity_rank']:3d}  (delta {delta:+d})  "
              f"{m['id']:<25s}  {m['name'][:40]}")

    print("  Most UNDERRANKED by transformation (low T rank, high O rank = accessible opportunity):")
    for m, delta in rank_deltas[-5:]:
        print(f"    T#{m['rank']:3d} → O#{m['opportunity_rank']:3d}  (delta {delta:+d})  "
              f"{m['id']:<25s}  {m['name'][:40]}")

    print()
    print(f"  Output: {NORMALIZED_FILE}")
    print(f"  UI:     {UI_MODELS}")
    print(f"  Dash:   {UI_DASHBOARD}")


if __name__ == "__main__":
    main()
