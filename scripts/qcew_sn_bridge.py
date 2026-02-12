#!/usr/bin/env python3
"""QCEW-to-SN Bridge: Build a NAICS lookup table for Structural Necessity scoring.

Reads cached QCEW national CSV files (data/cache/qcew_national_YYYY.csv) and
computes per-NAICS-sector metrics that the scoring pipeline needs:

  - baumol_score:       avg_annual_pay / economy-wide avg_annual_pay (ratio)
  - fragmentation_proxy: annual_avg_estabs / annual_avg_emplvl
  - employment:         annual_avg_emplvl
  - establishments:     annual_avg_estabs
  - avg_pay:            avg_annual_pay (dollars)
  - avg_weekly_wage:    annual_avg_wkly_wage (dollars)
  - wage_growth:        year-over-year % change in avg_annual_pay
  - emp_growth:         year-over-year % change in annual_avg_emplvl
  - total_annual_wages: total_annual_wages (dollars)

Output: data/cache/qcew_sn_lookup.json
  A JSON dict mapping NAICS code -> metrics dict.
  Includes entries at 2-digit, 3-digit, 4-digit, 5-digit, and 6-digit levels.

The scoring scripts (enumerate_models.py, rate_expansion.py) can import this
lookup to replace hardcoded/estimated key_data values with real QCEW data.

Usage:
    python3 scripts/qcew_sn_bridge.py
    python3 scripts/qcew_sn_bridge.py --year 2023
    python3 scripts/qcew_sn_bridge.py --year 2023 --prior-year 2022 --min-employment 100
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / 'data' / 'cache'
OUTPUT_PATH = CACHE_DIR / 'qcew_sn_lookup.json'

# ---------------------------------------------------------------------------
# QCEW aggregation level codes (for national-level private-sector data)
# ---------------------------------------------------------------------------
# The CSV uses own_code to distinguish ownership type:
#   0 = total covered (all ownerships)
#   5 = private sector
#
# agglvl_code determines NAICS depth:
#   10 = total, all industries (own_code=0)
#   11 = total private (own_code=5)
#   14 = 2-digit NAICS sector (private)
#   15 = 3-digit NAICS subsector (private)
#   16 = 4-digit NAICS industry group (private)
#   17 = 5-digit NAICS industry (private)
#   18 = 6-digit NAICS US industry (private)

PRIVATE_OWN_CODE = '5'

# Map from agglvl_code to NAICS digit depth label
AGGLVL_LABELS = {
    '11': 'total_private',
    '14': '2digit',
    '15': '3digit',
    '16': '4digit',
    '17': '5digit',
    '18': '6digit',
}

# We keep all of these levels in the lookup
KEEP_AGGLVL_CODES = set(AGGLVL_LABELS.keys())

# Unclassified / catch-all codes to skip
SKIP_INDUSTRY_CODES = {
    '10', '101', '1011', '1012', '1013',
    '1021', '1022', '1023', '1024', '1025', '1026', '1027', '1028', '1029',
    '99', '999', '9999', '99999', '999999', 'TOTAL',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_int(val, default=0):
    """Convert a CSV string value to int, handling empties and commas."""
    if val is None:
        return default
    val = str(val).strip().replace(',', '').replace('"', '')
    if val in ('', 'N', 'n'):
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default


def safe_float(val, default=0.0):
    """Convert a CSV string value to float."""
    if val is None:
        return default
    val = str(val).strip().replace(',', '').replace('"', '')
    if val in ('', 'N', 'n'):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def load_qcew_csv(year):
    """Load a cached QCEW national CSV file and return parsed rows.

    Args:
        year: e.g. '2023' or 2023

    Returns:
        list of dicts (one per CSV row), or empty list if file not found
    """
    year_str = str(year)
    csv_path = CACHE_DIR / f'qcew_national_{year_str}.csv'

    if not csv_path.exists():
        print(f'WARNING: Cache file not found: {csv_path}')
        print(f'  Run the sector screener first to download QCEW data,')
        print(f'  or download manually from https://data.bls.gov/cew/data/api/{year_str}/a/area/US000.csv')
        return []

    print(f'Loading {csv_path} ...')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f'  Parsed {len(rows):,} rows.')
    return rows


def filter_private_sector(rows):
    """Filter QCEW rows to private sector only (own_code = 5).

    Also filters to the aggregation levels we care about (2-6 digit NAICS
    plus total private).
    """
    filtered = []
    for row in rows:
        own_code = row.get('own_code', '').strip().replace('"', '')
        agglvl = row.get('agglvl_code', '').strip().replace('"', '')

        if own_code != PRIVATE_OWN_CODE:
            continue
        if agglvl not in KEEP_AGGLVL_CODES:
            continue

        filtered.append(row)
    return filtered


def get_economy_avg_pay(rows):
    """Extract economy-wide average annual pay from total private row.

    Looks for agglvl_code = '11' (total private sector, national).
    """
    for row in rows:
        agglvl = row.get('agglvl_code', '').strip().replace('"', '')
        own_code = row.get('own_code', '').strip().replace('"', '')
        if agglvl == '11' and own_code == PRIVATE_OWN_CODE:
            pay = safe_float(row.get('avg_annual_pay'))
            if pay > 0:
                return pay

    # Fallback: reasonable US private sector average
    print('  WARNING: Could not find total private sector avg pay, using $70,000 fallback.')
    return 70000.0


def build_sector_map(rows):
    """Build a dict mapping industry_code -> parsed row data.

    Only includes rows at NAICS sector levels (2-6 digit), skipping
    the total private row and unclassified codes.
    """
    sector_map = {}
    for row in rows:
        agglvl = row.get('agglvl_code', '').strip().replace('"', '')
        code = row.get('industry_code', '').strip().replace('"', '')

        # Skip total private row (we use it only for economy avg pay)
        if agglvl == '11':
            continue

        # Skip unclassified codes
        if code in SKIP_INDUSTRY_CODES:
            continue

        employment = safe_int(row.get('annual_avg_emplvl'))
        establishments = safe_int(row.get('annual_avg_estabs'))
        avg_pay = safe_float(row.get('avg_annual_pay'))
        avg_wkly_wage = safe_float(row.get('annual_avg_wkly_wage'))
        total_wages = safe_float(row.get('total_annual_wages'))

        # Over-the-year changes (built into the CSV by BLS)
        oty_emp_pct = safe_float(row.get('oty_annual_avg_emplvl_pct_chg'))
        oty_pay_pct = safe_float(row.get('oty_avg_annual_pay_pct_chg'))

        # Industry title from QCEW CSV (may or may not be present)
        title = row.get('industry_title', '').strip().replace('"', '')

        sector_map[code] = {
            'industry_code': code,
            'industry_title': title,
            'naics_depth': AGGLVL_LABELS.get(agglvl, 'unknown'),
            'employment': employment,
            'establishments': establishments,
            'avg_pay': avg_pay,
            'avg_weekly_wage': avg_wkly_wage,
            'total_annual_wages': total_wages,
            'oty_emp_growth_pct': oty_emp_pct,
            'oty_wage_growth_pct': oty_pay_pct,
        }

    return sector_map


def compute_cross_year_growth(current_map, prior_map):
    """Compute year-over-year growth rates using two years of data.

    Falls back to the OTY fields embedded in the current-year CSV if the
    prior year is not available for a given sector.

    Mutates current_map in place, adding:
      - emp_growth: (emp_current - emp_prior) / emp_prior
      - wage_growth: (pay_current - pay_prior) / pay_prior
    """
    for code, current in current_map.items():
        prior = prior_map.get(code)

        if prior and prior.get('employment', 0) > 0:
            emp_current = current['employment']
            emp_prior = prior['employment']
            current['emp_growth'] = round(
                (emp_current - emp_prior) / emp_prior, 4
            )
        else:
            # Fall back to OTY field (already a percent, convert to fraction)
            current['emp_growth'] = round(
                current.get('oty_emp_growth_pct', 0) / 100.0, 4
            )

        if prior and prior.get('avg_pay', 0) > 0:
            pay_current = current['avg_pay']
            pay_prior = prior['avg_pay']
            current['wage_growth'] = round(
                (pay_current - pay_prior) / pay_prior, 4
            )
        else:
            current['wage_growth'] = round(
                current.get('oty_wage_growth_pct', 0) / 100.0, 4
            )


def compute_sn_metrics(sector_map, economy_avg_pay):
    """Compute SN-relevant derived metrics for each sector.

    Adds to each sector dict:
      - baumol_score: avg_pay / economy_avg_pay (ratio, >1 = above average)
      - fragmentation_proxy: establishments / employment
    """
    for code, sector in sector_map.items():
        avg_pay = sector.get('avg_pay', 0)
        employment = sector.get('employment', 0)
        establishments = sector.get('establishments', 0)

        # Baumol score: wage premium relative to economy average
        if economy_avg_pay > 0:
            sector['baumol_score'] = round(avg_pay / economy_avg_pay, 4)
        else:
            sector['baumol_score'] = 0.0

        # Fragmentation proxy: more establishments per employee = more fragmented
        if employment > 0:
            sector['fragmentation_proxy'] = round(
                establishments / employment, 6
            )
        else:
            sector['fragmentation_proxy'] = 0.0


def build_lookup(sector_map, min_employment=0):
    """Build the final lookup dict from sector_map.

    Each entry contains exactly the fields the scoring scripts need,
    plus metadata for provenance.

    Args:
        sector_map: dict of industry_code -> sector metrics
        min_employment: filter out sectors below this threshold (0 = keep all)

    Returns:
        dict mapping industry_code -> SN metrics
    """
    lookup = {}

    for code, sector in sector_map.items():
        if sector['employment'] < min_employment:
            continue

        lookup[code] = {
            # Core SN scoring fields (consumed by rate_expansion.py and enumerate_models.py)
            'baumol_score': sector['baumol_score'],
            'fragmentation_proxy': sector['fragmentation_proxy'],
            'employment': sector['employment'],
            'establishments': sector['establishments'],
            'emp_growth': sector['emp_growth'],
            'wage_growth': sector['wage_growth'],
            'avg_pay': sector['avg_pay'],

            # Additional context (useful for enrichment and interpretation)
            'avg_weekly_wage': sector.get('avg_weekly_wage', 0),
            'total_annual_wages': sector.get('total_annual_wages', 0),
            'industry_title': sector.get('industry_title', ''),
            'naics_depth': sector.get('naics_depth', ''),
        }

    return lookup



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build QCEW-to-SN lookup table for scoring pipeline.'
    )
    parser.add_argument(
        '--year', default='2023',
        help='Primary data year (default: 2023)'
    )
    parser.add_argument(
        '--prior-year', default=None,
        help='Prior year for growth calculation (default: year - 1)'
    )
    parser.add_argument(
        '--min-employment', type=int, default=0,
        help='Minimum employment to include a sector (default: 0 = all)'
    )
    parser.add_argument(
        '--output', default=str(OUTPUT_PATH),
        help=f'Output JSON path (default: {OUTPUT_PATH})'
    )
    args = parser.parse_args()

    year = args.year
    prior_year = args.prior_year or str(int(year) - 1)
    min_employment = args.min_employment
    output_path = args.output

    print('=' * 70)
    print('QCEW-to-SN Bridge')
    print(f'  Primary year:     {year}')
    print(f'  Prior year:       {prior_year}')
    print(f'  Min employment:   {min_employment}')
    print(f'  Output:           {output_path}')
    print('=' * 70)
    print()

    # --- Step 1: Load QCEW data ---
    current_rows = load_qcew_csv(year)
    if not current_rows:
        print(f'ERROR: No QCEW data for {year}. Cannot proceed.')
        sys.exit(1)

    prior_rows = load_qcew_csv(prior_year)
    # Prior year is optional — we can fall back to OTY fields in current year

    # --- Step 2: Filter to private sector ---
    print('\nFiltering to private sector...')
    current_private = filter_private_sector(current_rows)
    print(f'  Current year ({year}): {len(current_private):,} private-sector rows')

    prior_private = filter_private_sector(prior_rows) if prior_rows else []
    print(f'  Prior year ({prior_year}): {len(prior_private):,} private-sector rows')

    # --- Step 3: Get economy-wide average pay ---
    economy_avg_pay = get_economy_avg_pay(current_private)
    print(f'\n  Economy-wide avg annual pay: ${economy_avg_pay:,.0f}')

    # --- Step 4: Build sector maps ---
    print('\nBuilding sector maps...')
    current_map = build_sector_map(current_private)
    prior_map = build_sector_map(prior_private) if prior_private else {}
    print(f'  Current year sectors: {len(current_map):,}')
    print(f'  Prior year sectors:   {len(prior_map):,}')

    # --- Step 5: Compute cross-year growth ---
    print('\nComputing year-over-year growth rates...')
    compute_cross_year_growth(current_map, prior_map)

    # Count how many used direct YoY vs OTY fallback
    direct_count = sum(
        1 for code in current_map
        if code in prior_map and prior_map[code].get('employment', 0) > 0
    )
    fallback_count = len(current_map) - direct_count
    print(f'  Direct YoY calculation: {direct_count:,} sectors')
    print(f'  OTY fallback:           {fallback_count:,} sectors')

    # --- Step 6: Compute SN metrics ---
    print('\nComputing SN metrics (Baumol score, fragmentation proxy)...')
    compute_sn_metrics(current_map, economy_avg_pay)

    # --- Step 7: Build and write lookup ---
    print('\nBuilding lookup table...')
    lookup = build_lookup(current_map, min_employment=min_employment)
    print(f'  Sectors in lookup: {len(lookup):,}')

    # Summary stats
    if lookup:
        baumol_scores = [v['baumol_score'] for v in lookup.values() if v['baumol_score'] > 0]
        frag_scores = [v['fragmentation_proxy'] for v in lookup.values() if v['fragmentation_proxy'] > 0]
        emp_values = [v['employment'] for v in lookup.values() if v['employment'] > 0]

        # Count by depth
        depth_counts = {}
        for v in lookup.values():
            d = v.get('naics_depth', 'unknown')
            depth_counts[d] = depth_counts.get(d, 0) + 1

        print(f'\n  By NAICS depth:')
        for depth, count in sorted(depth_counts.items()):
            print(f'    {depth}: {count:,} sectors')

        if baumol_scores:
            print(f'\n  Baumol score range: {min(baumol_scores):.3f} - {max(baumol_scores):.3f}')
            print(f'  Baumol > 1.5 (high stored energy): {sum(1 for b in baumol_scores if b > 1.5)} sectors')
            print(f'  Baumol > 1.0 (above average): {sum(1 for b in baumol_scores if b > 1.0)} sectors')

        if frag_scores:
            print(f'\n  Fragmentation proxy range: {min(frag_scores):.6f} - {max(frag_scores):.6f}')

        if emp_values:
            print(f'\n  Total employment covered: {sum(emp_values):,}')
            print(f'  Sectors with >100K employment: {sum(1 for e in emp_values if e > 100000)}')
            print(f'  Sectors with >1M employment: {sum(1 for e in emp_values if e > 1000000)}')

    # Build output JSON
    output = {
        '_meta': {
            'description': (
                'QCEW-to-SN bridge lookup. Maps NAICS codes to Structural '
                'Necessity scoring metrics derived from BLS QCEW data.'
            ),
            'source': 'BLS Quarterly Census of Employment and Wages',
            'primary_year': year,
            'prior_year': prior_year,
            'economy_avg_pay': economy_avg_pay,
            'min_employment_filter': min_employment,
            'total_sectors': len(lookup),
            'fields': {
                'baumol_score': 'avg_annual_pay / economy-wide avg_annual_pay (ratio >1 = above avg)',
                'fragmentation_proxy': 'establishments / employment (higher = more fragmented)',
                'employment': 'annual average employment level',
                'establishments': 'annual average establishment count',
                'emp_growth': 'year-over-year employment growth (fraction, e.g. 0.02 = 2%)',
                'wage_growth': 'year-over-year average pay growth (fraction)',
                'avg_pay': 'average annual pay in dollars',
                'avg_weekly_wage': 'average weekly wage in dollars',
                'total_annual_wages': 'total annual wages in dollars',
                'industry_title': 'BLS industry title',
                'naics_depth': 'NAICS digit level (2digit, 3digit, 4digit, 5digit, 6digit)',
            },
            'usage': (
                'In scoring scripts, load this file and use '
                'data["sectors"][naics_code] as key_data for SN scoring. '
                'Fields match what rate_expansion.py and enumerate_models.py expect: '
                'employment, baumol_score, fragmentation_proxy, establishments, '
                'emp_growth, avg_pay.'
            ),
            'usage_example': (
                'import json\n'
                'with open("data/cache/qcew_sn_lookup.json") as f:\n'
                '    qcew = json.load(f)\n'
                'key_data = qcew["sectors"].get(naics_code, {})\n'
                'employment = key_data.get("employment", 0)\n'
                'baumol = key_data.get("baumol_score", 0)\n'
            ),
        },
        'sectors': lookup,
    }

    # Write output
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f'\nLookup written to: {output_path}')

    # Print top 20 by Baumol score as a sanity check
    print('\n' + '=' * 70)
    print('TOP 20 SECTORS BY BAUMOL SCORE (sanity check)')
    print('=' * 70)
    sorted_sectors = sorted(
        lookup.items(),
        key=lambda x: x[1].get('baumol_score', 0),
        reverse=True,
    )
    print(f'{"NAICS":>6}  {"Baumol":>7}  {"Empl":>10}  {"Estabs":>8}  '
          f'{"FragProxy":>10}  {"EmpGr":>6}  {"WageGr":>6}  '
          f'{"AvgPay":>9}  {"Title"}')
    print('-' * 110)
    for code, metrics in sorted_sectors[:20]:
        print(
            f'{code:>6}  '
            f'{metrics["baumol_score"]:>7.3f}  '
            f'{metrics["employment"]:>10,}  '
            f'{metrics["establishments"]:>8,}  '
            f'{metrics["fragmentation_proxy"]:>10.6f}  '
            f'{metrics["emp_growth"]:>+5.1%}  '
            f'{metrics["wage_growth"]:>+5.1%}  '
            f'${metrics["avg_pay"]:>8,.0f}  '
            f'{metrics.get("industry_title", "")[:40]}'
        )

    # Print top 20 by fragmentation proxy
    print('\n' + '=' * 70)
    print('TOP 20 SECTORS BY FRAGMENTATION (sanity check)')
    print('=' * 70)
    sorted_frag = sorted(
        [(c, m) for c, m in lookup.items() if m.get('employment', 0) >= 5000],
        key=lambda x: x[1].get('fragmentation_proxy', 0),
        reverse=True,
    )
    print(f'{"NAICS":>6}  {"FragProxy":>10}  {"Estabs":>8}  {"Empl":>10}  '
          f'{"Baumol":>7}  {"Title"}')
    print('-' * 90)
    for code, metrics in sorted_frag[:20]:
        print(
            f'{code:>6}  '
            f'{metrics["fragmentation_proxy"]:>10.6f}  '
            f'{metrics["establishments"]:>8,}  '
            f'{metrics["employment"]:>10,}  '
            f'{metrics["baumol_score"]:>7.3f}  '
            f'{metrics.get("industry_title", "")[:40]}'
        )

    print(f'\nDone. {len(lookup):,} sectors ready for SN scoring pipeline.')


if __name__ == '__main__':
    main()
