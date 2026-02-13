#!/usr/bin/env python3
"""
Fix TN-011 (Management of Companies) and TN-007 (Wholesale Trade)
year_by_year entries from plain strings to structured {phase, description, indicators} objects.
"""

import json
import sys
from pathlib import Path

NARRATIVES_PATH = Path("/Users/mv/Documents/research/data/v4/narratives.json")

PHASE_MAP = {
    "2026": "early_disruption",
    "2027": "acceleration",
    "2028": "acceleration",
    "2029": "restructuring",
    "2030_2031": "new_equilibrium",
}

# Hand-crafted measurable indicators extracted from each year's description text
INDICATORS = {
    "TN-011": {
        "2026": [
            "BLS QCEW employment in NAICS 55 Management of Companies (baseline: 2.4M)",
            "Fortune 500 board members with AI expertise or literacy credentials",
            "Enterprise strategic planning AI tool adoption rate (Gartner survey)",
            "PE deal volume with AI-first value creation playbooks (PitchBook data)",
            "M&A due diligence cycle time reduction via AI automation (days saved)",
        ],
        "2027": [
            "Share of corporate reporting/analysis automated by AI (target: 50% at early adopters)",
            "Middle management headcount change at Fortune 500 early adopters (BLS proxy: NAICS 55 employment)",
            "Fortune 500 companies with Chief AI Officer role (target: 20%)",
            "Enterprise AI strategy tool market revenue (Gartner/IDC estimates)",
            "PE portfolio companies with active AI transformation programs (PitchBook)",
        ],
        "2028": [
            "Fortune 500 corporate HQ headcount change (target: -10% at early adopters)",
            "AI scenario planning accuracy vs traditional consulting benchmarks",
            "PE deal theses requiring AI transformation plan (% of new deals)",
            "Board composition: % of Fortune 500 boards with AI expertise requirement",
            "Management consulting revenue mix shift: AI analytics vs human advisory",
        ],
        "2029": [
            "BLS QCEW NAICS 55 employment trajectory (management layer compression signal)",
            "Average manager span of control at large firms (target: 15-20 reports, was 7-10)",
            "AI-augmented executive decision-making tool penetration (enterprise survey)",
            "PE portfolio consolidation rate: acquisitions integrated via AI per fund",
            "Organizational layer count at Fortune 500 (flattening trend measurement)",
        ],
        "2030_2031": [
            "BLS QCEW NAICS 55 employment (target: -25-30% from 2026 baseline at early adopters)",
            "Average corporate HQ size vs 2026 baseline (headcount per $B revenue)",
            "Management consulting industry revenue composition: AI vs change management",
            "PE operational value creation attributed to AI (% of EBITDA improvement)",
            "Manager-to-individual-contributor ratio across Fortune 500 (structural flattening)",
        ],
    },
    "TN-007": {
        "2026": [
            "BLS QCEW wholesale trade employment NAICS 42 (baseline: 5.9M)",
            "Census wholesale establishment count (baseline: 410K)",
            "AI startup count in wholesale/distribution (Crunchbase, baseline: ~0 per P-022)",
            "Average wholesale gross margin (baseline: 2-5%)",
            "Average wholesale establishment owner age (Census ABS, baseline: 60+)",
        ],
        "2027": [
            "AI-native wholesale distributor launches in commodity sectors (building materials, electrical)",
            "Inventory optimization AI adoption: working capital reduction (target: 15-20%)",
            "EDI-to-AI procurement platform migration rate (% of wholesale transactions)",
            "Wholesale business succession/transfer volume (Silver Tsunami first wave)",
            "Trade policy hedging technology market size (tariff risk management tools)",
        ],
        "2028": [
            "BLS QCEW wholesale employment change in order processing/logistics roles (target: -5%)",
            "B2B marketplace GMV in fragmented wholesale verticals",
            "AI-managed supplier negotiation penetration (target: 40% of routine negotiations)",
            "PE-backed wholesale roll-up deal volume (PitchBook, Silver Tsunami exits)",
            "First wholesale AI platform revenue milestones (target: $100M+)",
        ],
        "2029": [
            "Funded AI-native wholesale startups (Crunchbase, target: 10+ closing Schumpeterian gap)",
            "Census wholesale establishment count change (target: -10% from baseline)",
            "AI just-in-time inventory adoption rate across wholesale sectors",
            "B2B AI commerce platform share of commodity product wholesale transactions",
            "Wholesale sector average days inventory outstanding (DIO reduction trend)",
        ],
        "2030_2031": [
            "BLS QCEW wholesale employment per establishment (target: -20% from 2026 baseline)",
            "Average wholesale firm gross margin (target: +15% improvement from baseline)",
            "Wholesale establishment count concentration ratio (fewer, larger firms)",
            "Human-premium specialty distribution revenue share vs AI-managed commodity distribution",
            "Wholesale sales role composition: order-taking vs consultative/technical (BLS OES data)",
        ],
    },
}


def main():
    print(f"Reading {NARRATIVES_PATH}")
    with open(NARRATIVES_PATH, "r") as f:
        data = json.load(f)

    narratives = data.get("narratives", data) if isinstance(data, dict) else data
    fixed_count = 0

    for narrative in narratives:
        nid = narrative.get("narrative_id", "")
        if nid not in ("TN-011", "TN-007"):
            continue

        yby = narrative.get("year_by_year", {})
        print(f"\nProcessing {nid}:")

        for year_key in ["2026", "2027", "2028", "2029", "2030_2031"]:
            val = yby.get(year_key)
            if val is None:
                print(f"  WARNING: {year_key} not found")
                continue

            if isinstance(val, str):
                phase = PHASE_MAP[year_key]
                indicators = INDICATORS[nid][year_key]
                yby[year_key] = {
                    "phase": phase,
                    "description": val,
                    "indicators": indicators,
                }
                print(f"  {year_key}: CONVERTED (phase={phase}, {len(indicators)} indicators)")
                fixed_count += 1
            elif isinstance(val, dict):
                print(f"  {year_key}: already structured (skipping)")
            else:
                print(f"  WARNING: {year_key} has unexpected type: {type(val).__name__}")

    print(f"\nTotal entries fixed: {fixed_count}")

    # Write back
    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Written to {NARRATIVES_PATH}")

    # Final verification: scan ALL 16 narratives
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION: Scanning all narratives")
    print("=" * 60)

    issues = []
    for narrative in narratives:
        nid = narrative.get("narrative_id", "")
        yby = narrative.get("year_by_year", {})
        for year_key, val in yby.items():
            if isinstance(val, str):
                issues.append(f"  {nid}/{year_key}: STILL A STRING")
            elif isinstance(val, dict):
                missing = [k for k in ("phase", "description", "indicators") if k not in val]
                if missing:
                    issues.append(f"  {nid}/{year_key}: dict missing keys: {missing}")
                elif not isinstance(val["indicators"], list):
                    issues.append(f"  {nid}/{year_key}: indicators is not a list")
                elif len(val["indicators"]) < 3:
                    issues.append(f"  {nid}/{year_key}: only {len(val['indicators'])} indicators (want >=3)")
            else:
                issues.append(f"  {nid}/{year_key}: unexpected type {type(val).__name__}")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(issue)
    else:
        print("ALL 16 NARRATIVES PASS: every year_by_year entry is {phase, description, indicators}")

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
