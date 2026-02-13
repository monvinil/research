#!/usr/bin/env python3
"""
v4_enrich_tn003.py — Enrich TN-003 (Manufacturing Transformation) with real data.

Replaces generic year_by_year skeleton with specific indicators from v3 deep dives,
adds geographic_variation across 8 regions, and populates falsification_criteria.
"""

import json
import sys
from pathlib import Path

NARRATIVES_PATH = Path("/Users/mv/Documents/research/data/v4/narratives.json")


def build_year_by_year():
    """Year-by-year projection with specific indicators from v3 evidence base."""
    return {
        "2026": {
            "phase": "early_disruption",
            "description": (
                "12.87M workers, 392K establishments. Cobot deployments accelerating "
                "($25-60K units, 6-18mo ROI). Robot orders +85.6% in food mfg. "
                "Top 1% AI-sophisticated, bottom 72% on spreadsheets "
                "(Bimodality Pattern P-041). CHIPS Act driving $52B semiconductor "
                "reshoring. Average age of manufacturing owner 58+."
            ),
            "indicators": [
                "BLS QCEW manufacturing employment (baseline: 12.87M)",
                "Census establishment count (baseline: 392K)",
                "Robot orders via RIA quarterly data (baseline: +85.6% food mfg)",
                "Cobot unit pricing (baseline: $25-60K per unit)",
                "CHIPS Act facility construction starts"
            ]
        },
        "2027": {
            "phase": "acceleration",
            "description": (
                "Cobot cost below $20K for basic units. First autonomous production "
                "lines in food/beverage. Reshoring factory completions: TSMC Arizona, "
                "Samsung Texas, Intel Ohio. PE refinancing wall begins ($400B+ "
                "mfg-related debt maturing). Retirement wave accelerating: 50K+ "
                "establishments seeking succession."
            ),
            "indicators": [
                "Cobot unit pricing trajectory (target: <$20K basic)",
                "Autonomous production line deployments (food/beverage sector)",
                "TSMC/Samsung/Intel factory completion milestones",
                "PE debt maturity wall ($400B+ manufacturing-related)",
                "Census business dynamics: establishment exits in NAICS 31-33"
            ]
        },
        "2028": {
            "phase": "acceleration",
            "description": (
                "AI-native manufacturing OS platforms reach scale (MES replacement). "
                "Predictive maintenance standard in top-quartile plants. Autonomous "
                "quality inspection >90% accuracy. Reshoring employment measurable "
                "in BLS data. Small manufacturer acquisition pricing drops 15-25%."
            ),
            "indicators": [
                "Manufacturing OS / MES replacement adoption rates",
                "Predictive maintenance penetration in top-quartile plants",
                "Autonomous QC inspection accuracy benchmarks",
                "BLS reshoring employment delta vs 2026 baseline",
                "Small manufacturer M&A multiples (baseline: current EV/EBITDA)"
            ]
        },
        "2029": {
            "phase": "restructuring",
            "description": (
                "Bimodality resolves: bottom-quartile manufacturers either modernize "
                "or exit. Cobot-human ratio crosses 1:5 in food manufacturing. "
                "Supply chain AI optimization reduces inventory costs 20-30%. "
                "PE-backed roll-ups face debt wall distress, creating acquisition "
                "opportunities."
            ),
            "indicators": [
                "Census establishment count delta (expect -5% to -10%)",
                "Cobot-to-human ratio in NAICS 311 (food mfg)",
                "Inventory-to-sales ratio for manufacturing sector",
                "PE-backed manufacturing platform default/restructuring rate",
                "Bimodality index: % of plants with AI vs spreadsheet-only"
            ]
        },
        "2030_2031": {
            "phase": "new_equilibrium",
            "description": (
                "New manufacturing equilibrium: AI-augmented workforce standard. "
                "Firm count decreases 10-15% but output/worker up 25-35%. "
                "Reshored capacity represents 15-20% of semiconductor, 10% of "
                "pharma production. Micro-factory model viable for custom/local "
                "production."
            ),
            "indicators": [
                "Manufacturing output per worker (target: +25-35% vs 2026)",
                "Establishment count (target: -10% to -15% vs 2026 baseline 392K)",
                "Domestic semiconductor production share (target: 15-20%)",
                "Domestic pharma API production share (target: ~10%)",
                "Micro-factory establishment count (new Census category expected)"
            ]
        }
    }


def build_geographic_variation():
    """Geographic variation across 8 regions with velocity, timeline shift, and notes."""
    return {
        "US": {
            "velocity": "high",
            "timeline_shift": "baseline",
            "notes": (
                "CHIPS Act + Silver Tsunami + reshoring = fastest transformation. "
                "$52B semiconductor, $35B EV battery investment. 392K establishments, "
                "extreme fragmentation."
            )
        },
        "China": {
            "velocity": "high",
            "timeline_shift": "-1 year",
            "notes": (
                "World's largest manufacturing base. Government-directed AI adoption. "
                "Robot density already highest globally. Risk: US-China decoupling "
                "fragments supply chains."
            )
        },
        "Japan": {
            "velocity": "medium",
            "timeline_shift": "-2 years",
            "notes": (
                "Most advanced robotics adoption per capita. Demographic pressure "
                "most acute (population declining). Society 5.0 framework. Leading "
                "in cobot-human integration."
            )
        },
        "EU": {
            "velocity": "medium",
            "timeline_shift": "+1 year",
            "notes": (
                "AI Act regulatory overhead slows adoption. Strong in automotive/"
                "chemicals. Germany's Industrie 4.0 mature but mid-tier adoption "
                "lagging. Energy costs post-Ukraine driving efficiency investment."
            )
        },
        "India": {
            "velocity": "low",
            "timeline_shift": "+3 years",
            "notes": (
                "Demographic dividend (young workforce) reduces automation urgency. "
                "PLI scheme driving manufacturing investment. Electronics assembly "
                "growing. Leapfrog potential in greenfield facilities."
            )
        },
        "LATAM": {
            "velocity": "low",
            "timeline_shift": "+2 years",
            "notes": (
                "Nearshoring wave (Mexico, Brazil). New factories built AI-native "
                "from start. Weak incumbent base = less resistance. Automotive "
                "corridor Monterrey-Guadalajara."
            )
        },
        "SEA": {
            "velocity": "medium",
            "timeline_shift": "+1 year",
            "notes": (
                "Manufacturing migration from China. Vietnam, Thailand, Indonesia "
                "receiving FDI. Mix of greenfield (AI-native) and legacy. Electronics "
                "assembly focus."
            )
        },
        "MENA": {
            "velocity": "low",
            "timeline_shift": "+3 years",
            "notes": (
                "Saudi Vision 2030 manufacturing push. Limited existing base. "
                "Greenfield advantage. Energy-intensive manufacturing leverages "
                "cheap energy."
            )
        }
    }


def build_falsification_criteria():
    """Specific, measurable criteria that would invalidate the transformation thesis."""
    return [
        "Cobot costs plateau above $30K — ROI window doesn't open for small manufacturers",
        "AI inference costs stop declining (>$1/M tokens stable for 12+ months) — automation economics stall",
        "Reshoring reverses: CHIPS Act facilities delayed 3+ years or relocated offshore",
        "Manufacturing employment INCREASES by >5% without wage pressure — labor shortage thesis invalidated",
        "Bottom-72% manufacturers successfully adopt cloud ERP without AI — bimodality resolves via incremental not disruptive path",
        "PE-backed manufacturing platforms successfully refinance at <6% rates — no distressed asset cascade"
    ]


def main():
    # Read
    if not NARRATIVES_PATH.exists():
        print(f"ERROR: {NARRATIVES_PATH} not found")
        sys.exit(1)

    with open(NARRATIVES_PATH) as f:
        data = json.load(f)

    # Find TN-003
    tn003 = None
    for narrative in data["narratives"]:
        if narrative["narrative_id"] == "TN-003":
            tn003 = narrative
            break

    if tn003 is None:
        print("ERROR: TN-003 not found in narratives.json")
        sys.exit(1)

    # Capture old state for diff reporting
    old_yby_desc_lengths = {
        year: len(tn003["year_by_year"][year]["description"])
        for year in tn003["year_by_year"]
    }
    old_yby_indicator_counts = {
        year: len(tn003["year_by_year"][year].get("indicators", []))
        for year in tn003["year_by_year"]
    }
    old_geo_count = len(tn003.get("geographic_variation", {}))
    old_fc_count = len(tn003.get("falsification_criteria", []))

    # Update
    tn003["year_by_year"] = build_year_by_year()
    tn003["geographic_variation"] = build_geographic_variation()
    tn003["falsification_criteria"] = build_falsification_criteria()

    # Write
    with open(NARRATIVES_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Report
    print("=" * 60)
    print("TN-003 Manufacturing Transformation — Enrichment Complete")
    print("=" * 60)

    print("\n--- year_by_year ---")
    for year in tn003["year_by_year"]:
        old_len = old_yby_desc_lengths.get(year, 0)
        new_len = len(tn003["year_by_year"][year]["description"])
        old_ind = old_yby_indicator_counts.get(year, 0)
        new_ind = len(tn003["year_by_year"][year]["indicators"])
        print(f"  {year}: description {old_len} -> {new_len} chars, "
              f"indicators {old_ind} -> {new_ind}")

    print(f"\n--- geographic_variation ---")
    print(f"  Regions: {old_geo_count} -> {len(tn003['geographic_variation'])}")
    for region, info in tn003["geographic_variation"].items():
        print(f"    {region}: velocity={info['velocity']}, "
              f"timeline_shift={info['timeline_shift']}")

    print(f"\n--- falsification_criteria ---")
    print(f"  Criteria: {old_fc_count} -> {len(tn003['falsification_criteria'])}")
    for i, fc in enumerate(tn003["falsification_criteria"], 1):
        print(f"    {i}. {fc[:80]}{'...' if len(fc) > 80 else ''}")

    print(f"\nFile written: {NARRATIVES_PATH}")
    print(f"Total narratives in file: {len(data['narratives'])}")


if __name__ == "__main__":
    main()
