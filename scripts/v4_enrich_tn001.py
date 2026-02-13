#!/usr/bin/env python3
"""
v4_enrich_tn001.py — Enrich TN-001 (Financial Services Transformation) in narratives.json
with real data: year_by_year indicators, geographic_variation, falsification_criteria.
"""

import json
import sys
from pathlib import Path
from copy import deepcopy

NARRATIVES_PATH = Path("/Users/mv/Documents/research/data/v4/narratives.json")


def main():
    # Load
    with open(NARRATIVES_PATH) as f:
        data = json.load(f)

    # Find TN-001
    tn001 = None
    tn001_idx = None
    for i, n in enumerate(data["narratives"]):
        if n["narrative_id"] == "TN-001":
            tn001 = n
            tn001_idx = i
            break

    if tn001 is None:
        print("ERROR: TN-001 not found in narratives.json")
        sys.exit(1)

    print(f"Found TN-001 at index {tn001_idx}: {tn001['name']}")
    print(f"  Current year_by_year keys: {list(tn001['year_by_year'].keys())}")
    print(f"  Current geographic_variation: {tn001['geographic_variation']}")
    print(f"  Current falsification_criteria: {tn001['falsification_criteria']}")

    # --- 1. Update year_by_year with specific indicators ---
    tn001["year_by_year"] = {
        "2026": {
            "phase": "acceleration",
            "description": (
                "Cascade ACTIVE: accounting employment -49K YoY, staffing stocks -53%. "
                "7 independent data sources confirm. Baumol score highest in economy "
                "(wages +4%/yr vs CPI 2.5%). AI coding assistants 84% developer adoption. "
                "Tax prep automation >60% of simple returns. Big 4 headcount flat despite "
                "revenue growth. PE-backed accounting roll-ups debt/EBITDA averaging 5.2x."
            ),
            "indicators": [
                "BLS: Accounting employment -49K YoY",
                "Staffing sector stocks -53% from peak",
                "Baumol score: wages +4%/yr vs CPI 2.5%",
                "AI coding assistant adoption: 84% of developers",
                "Tax prep automation: >60% of simple returns",
                "Big 4 headcount flat despite revenue growth",
                "PE-backed accounting roll-ups: debt/EBITDA 5.2x"
            ]
        },
        "2027": {
            "phase": "restructuring",
            "description": (
                "First PE-backed accounting firm failures (debt wall $200B+ financial services). "
                "AI handles 80% of bookkeeping, 50% of audit prep. Regional bank back-office "
                "staff cuts 15-25%. Insurance underwriting automation reaches mid-market. "
                "Compliance-as-code platforms handle 70% of routine regulatory filing."
            ),
            "indicators": [
                "PE debt wall: $200B+ financial services refinancing due",
                "AI bookkeeping automation: 80% of routine entries",
                "AI audit prep: 50% of standard procedures",
                "Regional bank back-office cuts: 15-25%",
                "Insurance underwriting automation: mid-market penetration",
                "Compliance-as-code: 70% of routine regulatory filing"
            ]
        },
        "2028": {
            "phase": "restructuring",
            "description": (
                "Tax preparation industry consolidates: 40% of independent tax preparers exit "
                "(Silver Tsunami + AI competition). AI-native financial advisory platforms reach "
                "$50B+ AUM. Audit transformation: continuous monitoring replaces annual audit "
                "cycle for mid-market. Banking branch workforce down 20% from 2025."
            ),
            "indicators": [
                "Independent tax preparer exits: 40% (Silver Tsunami + AI)",
                "AI-native advisory platforms: $50B+ AUM",
                "Continuous audit monitoring: mid-market adoption",
                "Banking branch workforce: -20% from 2025 baseline"
            ]
        },
        "2029": {
            "phase": "new_equilibrium",
            "description": (
                "Professional services cascade fully propagates: legal, consulting affected by "
                "same Baumol cure dynamics. CPA firm count down 25% from peak. AI-augmented "
                "accountant productivity 4-5x, creating premium for judgment-heavy work. "
                "Insurance claims processing 90%+ automated."
            ),
            "indicators": [
                "Professional services cascade: legal + consulting affected",
                "CPA firm count: -25% from peak",
                "AI-augmented accountant productivity: 4-5x baseline",
                "Insurance claims processing: 90%+ automated",
                "Premium for judgment-heavy work emerging"
            ]
        },
        "2030_2031": {
            "phase": "new_equilibrium",
            "description": (
                "New equilibrium: financial services employment down 30-40% in routine roles, "
                "up 15-20% in judgment/advisory. Barbell economy fully visible — AI handles "
                "routine cognitive, humans handle trust/judgment. Average financial services "
                "firm 40% smaller by headcount, 20% higher revenue/employee."
            ),
            "indicators": [
                "Routine role employment: -30-40% from 2025",
                "Judgment/advisory employment: +15-20% from 2025",
                "Barbell economy fully visible in sector structure",
                "Average firm headcount: -40%",
                "Revenue per employee: +20%"
            ]
        }
    }

    # --- 2. Update geographic_variation ---
    tn001["geographic_variation"] = {
        "US": {
            "velocity": "high",
            "timeline_shift": "baseline",
            "notes": (
                "Cascade already active. 49K accounting job losses confirmed. "
                "PE refinancing wall 2027-2029. Largest professional services market globally. "
                "CPA pipeline crisis (exam candidates -33% since 2016)."
            )
        },
        "China": {
            "velocity": "medium",
            "timeline_shift": "+1 year",
            "notes": (
                "Rapid fintech adoption (Ant Group, WeChat Pay). State banks slower to automate. "
                "Unique regulatory environment. Shadow banking cleanup creates different "
                "transformation path."
            )
        },
        "Japan": {
            "velocity": "low",
            "timeline_shift": "+2 years",
            "notes": (
                "Conservative banking culture. Aging workforce creates urgency but institutional "
                "resistance high. Megabanks slowly adopting. Regional banks face existential "
                "demographic pressure."
            )
        },
        "EU": {
            "velocity": "medium",
            "timeline_shift": "+1 year",
            "notes": (
                "DORA regulation drives compliance automation demand. Open Banking/PSD2 creating "
                "platform dynamics. UK (post-Brexit) moving faster than continental EU. "
                "GDPR constrains AI data usage."
            )
        },
        "India": {
            "velocity": "high",
            "timeline_shift": "+1 year",
            "notes": (
                "UPI digital payments infrastructure world-leading. Leapfrogging legacy systems. "
                "Young workforce + digital-native banking. PhonePe, Razorpay, Zerodha disrupting "
                "incumbents. Back-office outsourcing jobs at risk."
            )
        },
        "LATAM": {
            "velocity": "medium",
            "timeline_shift": "+2 years",
            "notes": (
                "Nubank model proving digital-first banking at scale. Brazil, Mexico leading. "
                "Low banking penetration = greenfield opportunity. Remittance disruption."
            )
        },
        "SEA": {
            "velocity": "medium",
            "timeline_shift": "+2 years",
            "notes": (
                "GrabFin, GoTo Financial expanding. Underbanked population large. "
                "Mobile-first financial services. Singapore as regional fintech hub."
            )
        },
        "MENA": {
            "velocity": "medium",
            "timeline_shift": "+1 year",
            "notes": (
                "Islamic finance creates unique AI compliance needs. Saudi PIF investing heavily "
                "in fintech. UAE as regional hub. Large unbanked population."
            )
        }
    }

    # --- 3. Update falsification_criteria ---
    tn001["falsification_criteria"] = [
        "Accounting employment reverses: BLS shows +30K jobs for 2 consecutive quarters — cascade thesis invalidated",
        "AI audit accuracy fails regulatory scrutiny — PCAOB or SEC blocks automated audit procedures",
        "PE-backed financial services firms successfully refinance at favorable rates — no debt wall cascade",
        "CPA exam candidate pipeline recovers (+20% YoY) — labor supply thesis weakened",
        "Incumbent Big 4 successfully deploy AI internally and INCREASE margins without headcount cuts — disruption absorbed",
        "AI hallucination rates in financial reporting remain >5% — trust barrier prevents automation of judgment-heavy work"
    ]

    # --- 4. Update summary to reflect enrichment ---
    tn001["summary"] = (
        "Financial services cascade ACTIVE — accounting employment -49K YoY, staffing stocks -53%, "
        "7 data sources confirm. Professional services wages +4%/yr vs CPI 2.5%. "
        "PE debt wall $200B+ due 2027-2029. Tax prep automation >60% simple returns. "
        "Big 4 headcount flat despite revenue growth. CPA pipeline crisis (exam candidates -33% since 2016). "
        "Geographic variation: US baseline (cascade active), India high velocity (UPI leapfrog), "
        "Japan slow (+2yr, institutional resistance). Barbell endpoint: routine roles -30-40%, "
        "judgment/advisory +15-20% by 2031."
    )

    # Update last_updated
    tn001["last_updated"] = "v4-enriched"

    # Write back
    data["narratives"][tn001_idx] = tn001

    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Verify
    with open(NARRATIVES_PATH) as f:
        verify = json.load(f)

    for n in verify["narratives"]:
        if n["narrative_id"] == "TN-001":
            print("\n--- VERIFICATION ---")
            print(f"  year_by_year keys: {list(n['year_by_year'].keys())}")
            yby = n["year_by_year"]
            for year, info in yby.items():
                print(f"    {year}: phase={info['phase']}, indicators={len(info['indicators'])}, desc_len={len(info['description'])}")
            print(f"  geographic_variation regions: {list(n['geographic_variation'].keys())}")
            for region, info in n["geographic_variation"].items():
                print(f"    {region}: velocity={info['velocity']}, shift={info['timeline_shift']}")
            print(f"  falsification_criteria: {len(n['falsification_criteria'])} items")
            for i, fc in enumerate(n["falsification_criteria"]):
                print(f"    [{i+1}] {fc[:80]}...")
            print(f"  summary length: {len(n['summary'])} chars")
            print(f"  last_updated: {n['last_updated']}")
            print("\nTN-001 enrichment complete.")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
