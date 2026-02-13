#!/usr/bin/env python3
"""Fix TN-015 and TN-016 year_by_year format in narratives.json.

These two narratives have plain-string year_by_year entries instead of
the structured format used by all other narratives:
  { "phase": "...", "description": "...", "indicators": [...] }

This script:
1. Reads narratives.json
2. Converts TN-015 and TN-016 year_by_year to structured format
3. Extracts measurable claims from descriptions to populate indicators (5 per year)
4. Writes back
"""

import json
import sys
from pathlib import Path

NARRATIVES_PATH = Path("/Users/mv/Documents/research/data/v4/narratives.json")

# Phase assignments per the spec
PHASES = {
    "TN-015": {
        "2026": "early_disruption",
        "2027": "acceleration",
        "2028": "acceleration",
        "2029": "restructuring",
        "2030_2031": "new_equilibrium",
    },
    "TN-016": {
        "2026": "early_disruption",
        "2027": "acceleration",
        "2028": "acceleration",
        "2029": "restructuring",
        "2030_2031": "new_equilibrium",
    },
}

# Hand-extracted measurable indicators from the description text.
# Each indicator references a specific quantifiable claim from the narrative.
INDICATORS = {
    "TN-015": {
        "2026": [
            "US utility sector revenue (baseline: $1.3T)",
            "Data center energy demand YoY growth (baseline: 25%+)",
            "Renewable share of US electricity generation (baseline: 30%+)",
            "Grid interconnection queue backlog (baseline: 2,000+ GW)",
            "Critical minerals lithium demand trajectory (baseline: 3x by 2030, 80% refined in China)",
        ],
        "2027": [
            "Grid-scale AI energy management system deployments (first operational systems)",
            "Behind-the-meter storage + solar cost parity vs commercial grid rates",
            "US lithium processing facility milestones (first operational facility)",
            "Oilfield autonomous drilling operation adoption by majors",
            "Data center renewable PPA volume and new capacity driven",
        ],
        "2028": [
            "Virtual power plant share of peak load management (target: 5%+)",
            "Annual grid modernization investment (target: $50B+)",
            "AI-optimized grid outage reduction rate (target: 20-30%)",
            "Energy storage cost per kWh at scale (target: below $100/kWh)",
            "Small modular reactor design approval status (NRC pipeline)",
        ],
        "2029": [
            "Renewable + storage vs gas peaker cost comparison across US markets",
            "Autonomous oilfield operations adoption rate among major producers",
            "Utility grid-as-platform / orchestration business model adoption",
            "Data center water stress and cooling innovation deployments",
            "Critical minerals non-China supply share (target: 50%)",
        ],
        "2030_2031": [
            "Distributed + renewable + AI-managed grid penetration in new construction",
            "Utility revenue model mix shift from volumetric to platform/service",
            "Oilfield services workforce size and autonomous operations share",
            "Critical minerals domestic supply share of US demand (target: 30%+)",
            "Data center co-located generation and advanced cooling adoption rate",
        ],
    },
    "TN-016": {
        "2026": [
            "Monthly new business applications via Census (baseline: 532K/mo)",
            "Solo operator output equivalence vs traditional firms (baseline: matching 10-person firm in content/design/code)",
            "AI tools annual revenue (baseline: $50B+)",
            "Freelancer platform per-project revenue trends (Upwork, Fiverr)",
            "New business delinquency rates alongside formation rates (selection pressure signal)",
        ],
        "2027": [
            "AI-native businesses reaching $1M revenue with 1-2 employees (first cohort)",
            "Vertical AI tool adoption in legal, accounting, design professions",
            "Micro-firm insurance and benefits platform launches",
            "AI-automated business formation rate (target: 80% of incorporation/compliance/tax)",
            "Micro-firm SaaS market size (target: $10B+)",
        ],
        "2028": [
            "Number of sectors with proven micro-firm model (target: 20+)",
            "Average solo operator revenue vs 2024 baseline (target: 3x with AI augmentation)",
            "Micro-firm OS platform market share of small business software (target: 5%+)",
            "Micro-firm franchise model emergence and count",
            "Traditional professional services client loss to micro-firm competitors (target: 10%)",
        ],
        "2029": [
            "NAICS revision discussions regarding micro-firm economy as structural category",
            "AI-core micro-firm count (target: 1M+)",
            "Micro-firm collective models adoption (shared infrastructure, joint bidding)",
            "Bank lending product adaptation for micro-firm credit models",
            "Micro-firm share of new business formation by sector",
        ],
        "2030_2031": [
            "Micro-firm share of professional services delivery (target: 15-20% by 1-5 person firms with AI)",
            "Micro-firm revenue per worker vs traditional small business (target: 2-3x)",
            "Micro-firm infrastructure ecosystem maturity (insurance, lending, benefits)",
            "Traditional firm structure share of total business activity trend",
            "AI capability per micro-firm worker (composite productivity index)",
        ],
    },
}


def fix_narratives():
    with open(NARRATIVES_PATH) as f:
        data = json.load(f)

    narratives = data["narratives"]
    fixed = []

    for n in narratives:
        nid = n.get("narrative_id", "")
        if nid not in ("TN-015", "TN-016"):
            continue

        yby = n.get("year_by_year", {})
        needs_fix = False
        for year_key, val in yby.items():
            if isinstance(val, str):
                needs_fix = True
                break

        if not needs_fix:
            print(f"{nid}: already in correct format, skipping.")
            continue

        new_yby = {}
        for year_key, val in yby.items():
            if isinstance(val, str):
                new_yby[year_key] = {
                    "phase": PHASES[nid][year_key],
                    "description": val,
                    "indicators": INDICATORS[nid][year_key],
                }
            else:
                # Already structured, keep as-is
                new_yby[year_key] = val

        n["year_by_year"] = new_yby
        fixed.append(nid)
        print(f"{nid}: converted {len(new_yby)} year entries to structured format.")

    if not fixed:
        print("Nothing to fix.")
        return

    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"\nWrote updated narratives.json. Fixed: {', '.join(fixed)}")


if __name__ == "__main__":
    fix_narratives()
