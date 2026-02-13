#!/usr/bin/env python3
"""
Enrich TN-014 (Retail Trade) and TN-004 (Healthcare) narratives in narratives.json.
Updates: year_by_year, geographic_variation, falsification_criteria.
"""

import json
import sys
from datetime import date

NARRATIVES_PATH = "/Users/mv/Documents/research/data/v4/narratives.json"

# ── TN-014: Retail Trade Transformation ──────────────────────────────────────

TN014_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "E-commerce 22% of retail sales and rising. 1.05M retail establishments, 15.6M workers. Autonomous checkout expanding beyond grocery. Inventory AI reducing stockouts 20-30%. Last-mile delivery costs falling with route optimization. Dollar stores and off-price still growing (counter-trend to premium). Restaurant automation: ghost kitchens, kiosk ordering standard in QSR.",
        "indicators": [
            "Census e-commerce share of retail sales (baseline: 22%)",
            "BLS QCEW retail employment (baseline: 15.6M)",
            "Census retail establishment count (baseline: 1.05M)",
            "Autonomous checkout transaction share in grocery (baseline: <5%)",
            "Last-mile delivery cost per package (benchmark: $8-12)"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "Computer vision checkout reaches 10% of grocery transactions. AI-driven dynamic pricing standard in mid-market retail. First fully autonomous convenience stores at scale. Restaurant labor crisis peaks (average age 45+ for owners, 50%+ turnover for staff). AI-native restaurant OS platforms emerging.",
        "indicators": [
            "Computer vision checkout penetration in grocery (target: 10%)",
            "Restaurant industry staff turnover rate (baseline: 50%+)",
            "Autonomous convenience store count in US (watch for >500)",
            "Dynamic pricing adoption in mid-market retail (%)",
            "AI-native restaurant OS platform funding and deployment metrics"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Retail employment inflection: -5% YoY in cashier/stock roles. Personalization AI drives 15-20% revenue lift for adopters. Warehouse automation reaches cost parity with manual for mid-size operations. Restaurant sector bifurcates: automated efficiency vs premium human experience.",
        "indicators": [
            "BLS cashier/stocker employment YoY change (target: -5%)",
            "Personalization AI revenue lift for adopters (target: 15-20%)",
            "Warehouse automation cost per unit vs manual labor parity",
            "Restaurant sector revenue split: automated vs premium human service"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Mall anchor closures accelerate second wave. Experiential retail grows while commodity retail automates. Grocery delivery profitability inflection via autonomous vehicles. Restaurant consolidation: 15% of independent restaurants acquired by AI-enabled operators.",
        "indicators": [
            "Mall anchor store closure rate (watch for acceleration)",
            "Autonomous grocery delivery route profitability",
            "Independent restaurant acquisition rate by AI-enabled operators (target: 15%)",
            "Experiential retail revenue growth vs commodity retail"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Retail workforce restructured: fewer cashiers/stockers, more experience curators and logistics coordinators. Restaurant industry: automated back-of-house standard, front-of-house premium for human service. E-commerce 30%+ of retail.",
        "indicators": [
            "E-commerce share of retail (target: 30%+)",
            "BLS occupational mix shift: cashier vs experience curator roles",
            "Restaurant back-of-house automation penetration rate",
            "Retail sector total employment vs 2026 baseline"
        ]
    }
}

TN014_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "Largest retail market. Amazon effect driving transformation. 1.05M establishments, extreme fragmentation in restaurants (600K+). Lowest Baumol score in restaurants (0.396)."
    },
    "China": {
        "velocity": "high",
        "timeline_shift": "-1 year",
        "notes": "Already ahead: Alibaba New Retail, JD.com autonomous logistics. Luckin Coffee model. Social commerce dominant. Live-streaming commerce $500B+."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Convenience store automation advanced (7-Eleven AI). Restaurant robots deployed. Cultural premium on human service limits full automation. Aging workforce drives urgency."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "Aldi/Lidl efficiency model. GDPR limits personalization AI. Strong labor protections slow workforce restructuring. UK further ahead than continental EU."
    },
    "India": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "Reliance JioMart, Flipkart driving digital retail. Kirana store network (12M+) = massive fragmentation. Quick commerce (Zepto, Blinkit) leapfrogging. Food delivery dominant (Swiggy, Zomato)."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "MercadoLibre dominant. Informal retail large. Rappi delivery platform. Low automation penetration but greenfield opportunity in modern retail."
    },
    "SEA": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "Shopee, Lazada dominating e-commerce. Social commerce growing. Young demographics favor digital. Grab food delivery dominant."
    },
    "MENA": {
        "velocity": "low",
        "timeline_shift": "+2 years",
        "notes": "Noon.com, Amazon.ae growing. Mall culture strong. Food delivery (Talabat, Careem) growing fast. Labor-rich economy reduces automation urgency."
    }
}

TN014_FALSIFICATION = [
    "E-commerce share plateaus at 22-24% for 3+ years — physical retail more resilient than projected",
    "Autonomous checkout technology reliability stays below 95% — customer friction prevents scaling",
    "Restaurant labor crisis resolves via immigration reform providing 500K+ food service workers",
    "Amazon/Walmart AI retail dominance prevents new entrant viability — opportunity thesis for startups fails",
    "Consumer preference for human interaction in retail INCREASES measurably — automation backlash"
]

# ── TN-004: Healthcare Transformation ────────────────────────────────────────

TN004_YEAR_BY_YEAR = {
    "2026": {
        "phase": "early_disruption",
        "description": "19.6M healthcare workers, $4.3T US healthcare spending (18% GDP). AI diagnostic tools FDA-approved in radiology, dermatology, pathology. Nurse shortage critical: 200K+ unfilled positions. Administrative costs 30% of healthcare spending. AI medical scribes reducing clinician documentation time 40-60%. Mental health crisis driving telehealth demand.",
        "indicators": [
            "BLS QCEW healthcare employment (baseline: 19.6M)",
            "CMS national health expenditure (baseline: $4.3T, 18% GDP)",
            "FDA AI/ML medical device clearances (baseline: 500+)",
            "BLS nursing vacancy rate (baseline: 200K+ unfilled)",
            "Administrative cost share of healthcare spending (baseline: 30%)",
            "AI medical scribe adoption rate in health systems"
        ]
    },
    "2027": {
        "phase": "acceleration",
        "description": "AI clinical decision support standard in top-quartile health systems. Administrative AI handles 50% of prior authorization, coding, billing. Nursing home automation begins (monitoring, medication management). Drug discovery AI produces first fully AI-designed Phase 3 candidates. RPM (remote patient monitoring) devices reach 50M+ US users.",
        "indicators": [
            "AI clinical decision support penetration in top-quartile systems",
            "Prior authorization automation rate (target: 50%)",
            "RPM device installed base in US (target: 50M+)",
            "AI-designed drug candidates entering Phase 3 trials",
            "Nursing home automation deployment metrics (monitoring, med mgmt)"
        ]
    },
    "2028": {
        "phase": "acceleration",
        "description": "Healthcare employment bifurcation visible: administrative roles -10%, clinical roles flat, AI-augmented specialists +15% productivity. Hospital-at-home models reach 5% of acute care. AI pathology reads standard for screening. Pharma manufacturing AI reduces production costs 20-30%.",
        "indicators": [
            "BLS healthcare administrative employment YoY (target: -10%)",
            "AI-augmented specialist productivity gain (target: +15%)",
            "Hospital-at-home share of acute care (target: 5%)",
            "AI pathology screening adoption rate",
            "Pharma manufacturing cost reduction from AI (target: 20-30%)"
        ]
    },
    "2029": {
        "phase": "restructuring",
        "description": "Rural healthcare transformation: AI-enabled community health models replace closing rural hospitals. Mental health AI reaches clinical validation for CBT delivery. Insurance underwriting fully algorithmic for standard policies. Healthcare consolidation: 15% of independent practices acquired.",
        "indicators": [
            "Rural hospital closure rate vs AI-enabled community health openings",
            "Mental health AI clinical validation studies for CBT",
            "Insurance underwriting automation rate for standard policies",
            "Independent practice acquisition rate (target: 15%)"
        ]
    },
    "2030_2031": {
        "phase": "new_equilibrium",
        "description": "Healthcare spending growth rate declines from 5.4% to 3-4%/yr as AI compression takes effect. Administrative staff down 25-30%. Clinical productivity up 30-40%. Barbell: AI handles routine diagnosis/admin, humans handle surgical/empathetic/complex care. New equilibrium: fewer workers, higher pay, better outcomes.",
        "indicators": [
            "CMS national health expenditure growth rate (target: 3-4%/yr, down from 5.4%)",
            "Healthcare administrative staffing vs 2026 baseline (target: -25-30%)",
            "Clinical productivity per provider vs 2026 baseline (target: +30-40%)",
            "Healthcare worker average compensation trend",
            "Patient outcome metrics (mortality, readmission) vs 2026 baseline"
        ]
    }
}

TN004_GEOGRAPHIC_VARIATION = {
    "US": {
        "velocity": "high",
        "timeline_shift": "baseline",
        "notes": "$4.3T market, 18% GDP. Highest administrative waste globally. FDA AI device approvals accelerating (500+ cleared). Nurse shortage most acute. Highest per-capita spending creates strongest Baumol cure incentive."
    },
    "China": {
        "velocity": "high",
        "timeline_shift": "0 years",
        "notes": "Parallel AI healthcare ecosystem. Massive patient data advantage (1.4B population). AI diagnostics deployed at scale in tier-1 hospitals. TCM + AI integration unique. Rural healthcare challenge similar to US."
    },
    "Japan": {
        "velocity": "medium",
        "timeline_shift": "-1 year",
        "notes": "Most aging population globally. Robotics in elder care advanced. Nursing robot deployment leading. Universal healthcare system enables centralized AI deployment. Caregiver shortage most acute."
    },
    "EU": {
        "velocity": "medium",
        "timeline_shift": "+1 year",
        "notes": "GDPR constrains health data AI. National health systems enable scale deployment but slower procurement. UK NHS AI adoption leading in EU. EU AI Act medical device classification adds compliance burden."
    },
    "India": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "1.4B population, 1 doctor per 1,500 people. AI diagnostics can leapfrog (rural health centers). Ayushman Bharat scheme digitizing records. Apollo/Practo telemedicine scaling. Pharma manufacturing hub."
    },
    "LATAM": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Fragmented health systems. Brazil SUS universal but underfunded. Private healthcare concentrated. Telemedicine adoption accelerated by COVID. Low AI readiness."
    },
    "SEA": {
        "velocity": "low",
        "timeline_shift": "+3 years",
        "notes": "Medical tourism hub (Thailand, Singapore). Emerging digital health ecosystems. Low physician density. Mobile health platforms growing."
    },
    "MENA": {
        "velocity": "medium",
        "timeline_shift": "+2 years",
        "notes": "UAE/Saudi investing heavily in health AI. Cleveland Clinic Abu Dhabi model. Large expat populations in Gulf. Saudi health transformation under Vision 2030."
    }
}

TN004_FALSIFICATION = [
    "FDA blocks or severely restricts AI diagnostic tools — regulatory barrier prevents clinical deployment at scale",
    "AI medical scribes produce liability-creating errors in >2% of encounters — trust barrier blocks adoption",
    "Nurse shortage resolves via compensation increases (+25%) and immigration — demographic supply thesis weakened",
    "Healthcare spending growth ACCELERATES above 6%/yr — Baumol cure fails, cost disease worsens",
    "Patient resistance to AI diagnosis exceeds 60% in surveys for 3+ years — psychological barrier dominates",
    "Drug discovery AI fails to produce successful Phase 3 candidates by 2028 — technology thesis for pharma weakened"
]


def main():
    # Load
    with open(NARRATIVES_PATH, "r") as f:
        data = json.load(f)

    updated = []
    for narrative in data["narratives"]:
        nid = narrative.get("narrative_id")

        if nid == "TN-014":
            narrative["year_by_year"] = TN014_YEAR_BY_YEAR
            narrative["geographic_variation"] = TN014_GEOGRAPHIC_VARIATION
            narrative["falsification_criteria"] = TN014_FALSIFICATION
            narrative["last_updated"] = str(date.today())
            updated.append("TN-014")
            print(f"[OK] TN-014 (Retail Trade) enriched:")
            print(f"     - year_by_year: {len(TN014_YEAR_BY_YEAR)} periods")
            print(f"     - geographic_variation: {len(TN014_GEOGRAPHIC_VARIATION)} regions")
            print(f"     - falsification_criteria: {len(TN014_FALSIFICATION)} criteria")

        elif nid == "TN-004":
            narrative["year_by_year"] = TN004_YEAR_BY_YEAR
            narrative["geographic_variation"] = TN004_GEOGRAPHIC_VARIATION
            narrative["falsification_criteria"] = TN004_FALSIFICATION
            narrative["last_updated"] = str(date.today())
            updated.append("TN-004")
            print(f"[OK] TN-004 (Healthcare) enriched:")
            print(f"     - year_by_year: {len(TN004_YEAR_BY_YEAR)} periods")
            print(f"     - geographic_variation: {len(TN004_GEOGRAPHIC_VARIATION)} regions")
            print(f"     - falsification_criteria: {len(TN004_FALSIFICATION)} criteria")

    if len(updated) != 2:
        missing = {"TN-014", "TN-004"} - set(updated)
        print(f"[ERROR] Could not find: {missing}")
        sys.exit(1)

    # Write
    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\n[DONE] Updated {len(updated)} narratives in {NARRATIVES_PATH}")

    # Verification pass
    print("\n── Verification ──")
    with open(NARRATIVES_PATH, "r") as f:
        verify = json.load(f)
    for narrative in verify["narratives"]:
        nid = narrative.get("narrative_id")
        if nid in ("TN-014", "TN-004"):
            yby = narrative["year_by_year"]
            geo = narrative["geographic_variation"]
            fc = narrative["falsification_criteria"]
            # Check year_by_year descriptions are non-template
            sample_desc = yby["2026"]["description"]
            is_template = "Disruption underway" in sample_desc or "disruption" == sample_desc.split()[0].lower()
            has_indicators = all(len(yby[yr].get("indicators", [])) > 0 for yr in yby)
            has_geo = len(geo) >= 8
            has_fc = len(fc) >= 4
            print(f"  {nid}: year_by_year={'ENRICHED' if not is_template else 'TEMPLATE'}, "
                  f"indicators={'OK' if has_indicators else 'MISSING'}, "
                  f"geo={len(geo)} regions, "
                  f"falsification={len(fc)} criteria, "
                  f"last_updated={narrative.get('last_updated', 'NONE')}")


if __name__ == "__main__":
    main()
