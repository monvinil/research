#!/usr/bin/env python3
"""v3-13: Enrich models with O*NET Polanyi automation data.

Reads cached Polanyi screen results and maps them to models via
NAICS-to-SOC bridge. Adds `polanyi` field to each model.
"""

import json
import statistics
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
CACHE_FILE = Path("/Users/mv/Documents/research/data/cache/onet_polanyi_screen.json")

# ── NAICS-to-SOC Bridge ────────────────────────────────────────────
# Maps 2-digit NAICS to relevant SOC codes from the 37 screened
NAICS_TO_SOC = {
    '52': ['13-2011.00', '13-2082.00', '41-3021.00', '43-3031.00'],  # Finance: accountants, tax prep, insurance, bookkeeping
    '54': ['13-1111.00', '23-1011.00', '23-2011.00', '13-1071.00', '27-3031.00'],  # Professional: mgmt analysts, lawyers, paralegals, HR, PR
    '62': ['29-1141.00', '29-2052.00'],  # Healthcare: nurses, pharmacy techs (removed invalid codes)
    '51': ['15-1252.00', '15-1232.00', '15-1299.08', '27-1024.00'],  # Information: software devs, support, architects, designers
    '31': ['35-2014.00'],  # Food manufacturing: restaurant cooks (proxy)
    '32': ['47-2061.00'],  # Non-metallic manufacturing: construction laborers (proxy)
    '33': ['47-2061.00', '15-1252.00'],  # Metal/electronics manufacturing: laborers + software
    '44': ['43-4051.00', '41-3021.00'],  # Retail: customer service, insurance sales
    '45': ['43-4051.00', '41-3021.00'],  # Retail
    '56': ['43-9061.00', '43-6014.00', '33-9032.00', '37-2011.00'],  # Admin: office clerks, secretaries, security, janitors
    '23': ['47-2061.00'],  # Construction: construction laborers
    '61': ['25-1011.00'],  # Education: business teachers
    '72': ['35-2014.00', '39-9011.00'],  # Accommodation/food: cooks, childcare (proxy for hospitality)
    '48': ['53-3032.00'],  # Transportation: truck drivers
    '49': ['53-3032.00', '43-9061.00'],  # Warehousing: truck drivers + office clerks
    '81': ['37-2011.00', '39-9011.00'],  # Other services: janitors, childcare
    '55': ['11-1021.00', '13-1111.00'],  # Management: ops managers, mgmt analysts
    '53': ['11-1021.00', '41-3021.00'],  # Real estate: ops managers, insurance sales
    '71': ['27-1024.00'],  # Arts/entertainment: graphic designers
    '42': ['43-4051.00', '53-3032.00'],  # Wholesale: customer service, truck drivers
    # Sectors with no good SOC match — will get null polanyi
    '22': [],  # Utilities
    '92': [],  # Government
    '21': [],  # Mining
    '11': [],  # Agriculture
}


def main():
    print("=" * 70)
    print("v3-13 Polanyi Model Enrichment")
    print("=" * 70)

    # Load Polanyi screen cache
    with open(CACHE_FILE) as f:
        screen = json.load(f)

    # Build SOC → Polanyi lookup
    soc_lookup = {}
    for r in screen.get('results', []):
        soc = r.get('soc_code', '')
        if soc and r.get('automation_exposure') is not None:
            soc_lookup[soc] = {
                'automation_exposure': r.get('automation_exposure', 0),
                'judgment_premium': r.get('judgment_premium', 0),
                'human_premium': r.get('human_premium', 0),
                'dominant_category': r.get('dominant_category', ''),
                'title': r.get('title', ''),
            }

    print(f"\n  SOC codes in cache: {len(soc_lookup)}")

    # Load models
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)

    models = data['models']
    print(f"  Models to enrich: {len(models)}")

    enriched = 0
    skipped = 0
    sector_stats = {}

    for m in models:
        naics = (m.get('sector_naics', '') or '')[:2]
        soc_codes = NAICS_TO_SOC.get(naics, [])

        if not soc_codes:
            m['polanyi'] = None
            skipped += 1
            continue

        # Get Polanyi data for matching SOC codes
        matched = [soc_lookup[s] for s in soc_codes if s in soc_lookup]
        if not matched:
            m['polanyi'] = None
            skipped += 1
            continue

        # Average across matched occupations
        avg_auto = statistics.mean([x['automation_exposure'] for x in matched])
        avg_judgment = statistics.mean([x['judgment_premium'] for x in matched])
        avg_human = statistics.mean([x['human_premium'] for x in matched])

        # Determine dominant category
        if avg_auto > avg_judgment and avg_auto > avg_human:
            dominant = 'routine_cognitive'
        elif avg_judgment > avg_human:
            dominant = 'nonroutine_cognitive_analytical'
        else:
            dominant = 'nonroutine_cognitive_interpersonal'

        m['polanyi'] = {
            'automation_exposure': round(avg_auto, 3),
            'judgment_premium': round(avg_judgment, 3),
            'human_premium': round(avg_human, 3),
            'dominant_category': dominant,
            'relevant_soc_codes': [s for s in soc_codes if s in soc_lookup],
        }
        enriched += 1

        # Track sector stats
        if naics not in sector_stats:
            sector_stats[naics] = []
        sector_stats[naics].append(avg_auto)

    print(f"\n  Enriched: {enriched}")
    print(f"  Skipped (no SOC match): {skipped}")

    print(f"\n  Automation Exposure by Sector (avg):")
    for naics in sorted(sector_stats.keys()):
        vals = sector_stats[naics]
        avg = statistics.mean(vals)
        print(f"    NAICS {naics}: {avg:.3f} ({len(vals)} models)")

    # Save
    with open(NORMALIZED_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  Saved to {NORMALIZED_FILE}")


if __name__ == '__main__':
    main()
