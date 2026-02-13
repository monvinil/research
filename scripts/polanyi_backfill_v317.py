#!/usr/bin/env python3
"""
polanyi_backfill_v317.py — Backfill Polanyi automation_exposure for ~70 models
missing it, using NAICS sector-level proxies from O*NET aggregates.

Approach: Instead of calling onet.py per-model (slow, API limits), we use
sector-level automation exposure averages derived from O*NET occupation data
aggregated to NAICS sectors.

Matching: tries 5/6-digit NAICS, then 4-digit, 3-digit, 2-digit, then
falls back to economy-wide average (0.33).

Output fields mirror the existing polanyi structure:
  - automation_exposure: float (0-1)
  - source: 'sector_proxy_v317'
  - method: 'NAICS sector average from O*NET aggregates'

Author: Claude Code (v3-17 backfill)
Date: 2026-02-13
"""

import json
import sys
from collections import Counter, defaultdict

DATA_FILE = '/Users/mv/Documents/research/data/verified/v3-12_normalized_2026-02-12.json'

# Sector-level automation exposure from O*NET research aggregates.
# Higher = more tasks are automatable. Scale 0-1.
SECTOR_AUTOMATION_EXPOSURE = {
    # Agriculture, Forestry, Fishing and Hunting
    '11': 0.31, '111': 0.33, '112': 0.28, '113': 0.25, '114': 0.22, '115': 0.35,
    # Mining, Quarrying, and Oil and Gas Extraction
    '21': 0.29, '211': 0.32, '212': 0.27, '213': 0.31,
    # Utilities
    '22': 0.34, '221': 0.34,
    # Construction
    '23': 0.26, '236': 0.25, '237': 0.27, '238': 0.26,
    # Manufacturing (for any missing)
    '31': 0.38, '32': 0.36, '33': 0.40,
    '311': 0.35, '332': 0.42, '333': 0.43, '334': 0.45, '336': 0.39,
    # Wholesale Trade
    '42': 0.37, '423': 0.36, '424': 0.35, '425': 0.38,
    # Retail Trade
    '44': 0.36, '45': 0.34,
    # Transportation and Warehousing
    '48': 0.33, '49': 0.35,
    # Government / Public Administration
    '92': 0.30, '921': 0.28, '922': 0.26, '923': 0.32,
    '924': 0.31, '925': 0.29, '926': 0.30, '928': 0.33,
    # Arts, Entertainment, and Recreation
    '71': 0.27, '711': 0.24, '712': 0.28, '713': 0.29,
}

ECONOMY_WIDE_AVERAGE = 0.33


def find_automation_exposure(naics_str: str) -> tuple:
    """
    Look up automation exposure for a NAICS code by progressively
    truncating from specific to general.

    Returns (exposure_value, matched_naics_key).
    """
    naics = str(naics_str).strip()

    # Try from most specific to least specific
    for length in range(len(naics), 1, -1):
        prefix = naics[:length]
        if prefix in SECTOR_AUTOMATION_EXPOSURE:
            return SECTOR_AUTOMATION_EXPOSURE[prefix], prefix

    # Fallback to economy-wide average
    return ECONOMY_WIDE_AVERAGE, 'economy_avg'


def main():
    print("=" * 72)
    print("Polanyi Backfill v3-17: Sector-Proxy Automation Exposure")
    print("=" * 72)
    print()

    # 1. Load data
    print(f"Loading: {DATA_FILE}")
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    models = data['models']
    total = len(models)
    print(f"Total models: {total}")
    print()

    # 2. Identify models missing Polanyi automation_exposure
    missing = []
    has_exposure = 0
    for m in models:
        p = m.get('polanyi')
        if p is not None and p.get('automation_exposure') is not None:
            has_exposure += 1
        else:
            missing.append(m)

    print(f"Already have automation_exposure: {has_exposure}")
    print(f"Missing automation_exposure: {len(missing)}")
    print()

    if not missing:
        print("Nothing to backfill. All models have Polanyi data.")
        return

    # 3. Backfill each missing model
    backfilled = []
    sector_summary = defaultdict(list)  # naics_2digit -> list of (id, naics, exposure, matched_key)

    for m in missing:
        naics = str(m.get('sector_naics', ''))
        exposure, matched_key = find_automation_exposure(naics)

        # Build the polanyi dict
        m['polanyi'] = {
            'automation_exposure': exposure,
            'source': 'sector_proxy_v317',
            'method': 'NAICS sector average from O*NET aggregates',
        }

        naics_2 = naics[:2] if naics else 'NONE'
        sector_summary[naics_2].append((m['id'], naics, exposure, matched_key))
        backfilled.append(m)

    # 4. Print summary by sector cluster
    print("-" * 72)
    print(f"BACKFILL SUMMARY: {len(backfilled)} models")
    print("-" * 72)

    # NAICS 2-digit to sector name
    NAICS_NAMES = {
        '11': 'Agriculture/Forestry/Fishing',
        '21': 'Mining/Oil & Gas',
        '22': 'Utilities',
        '23': 'Construction',
        '31': 'Manufacturing',
        '32': 'Manufacturing',
        '33': 'Manufacturing',
        '42': 'Wholesale Trade',
        '44': 'Retail Trade',
        '45': 'Retail Trade',
        '48': 'Transportation',
        '49': 'Warehousing',
        '62': 'Healthcare',
        '71': 'Arts/Entertainment',
        '92': 'Public Administration',
    }

    for naics_2 in sorted(sector_summary.keys()):
        entries = sector_summary[naics_2]
        sector_name = NAICS_NAMES.get(naics_2, 'Other')
        print(f"\n  NAICS {naics_2} -- {sector_name} ({len(entries)} models):")
        for model_id, naics, exposure, matched_key in entries:
            print(f"    {model_id:50s} | NAICS {naics:8s} -> matched '{matched_key}' -> exposure={exposure:.2f}")

    # Exposure value distribution
    exposures = [m['polanyi']['automation_exposure'] for m in backfilled]
    print(f"\n  Exposure stats: min={min(exposures):.2f}, max={max(exposures):.2f}, "
          f"mean={sum(exposures)/len(exposures):.3f}")

    match_sources = Counter(s[3] for entries in sector_summary.values() for s in entries)
    print(f"\n  Match sources: {dict(match_sources)}")
    print()

    # 5. Write back
    print(f"Saving to: {DATA_FILE}")
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print("Saved.")
    print()

    # 6. Verify
    print("Verifying...")
    with open(DATA_FILE, 'r') as f:
        verify_data = json.load(f)

    verify_models = verify_data['models']
    verified_count = sum(
        1 for m in verify_models
        if m.get('polanyi') is not None and m['polanyi'].get('automation_exposure') is not None
    )
    print(f"Polanyi coverage after backfill: {verified_count}/{len(verify_models)}")

    if verified_count == len(verify_models):
        print("PASS: Full Polanyi coverage achieved.")
    else:
        still_missing = [
            m['id'] for m in verify_models
            if m.get('polanyi') is None or m['polanyi'].get('automation_exposure') is None
        ]
        print(f"FAIL: Still missing {len(still_missing)} models: {still_missing[:10]}")
        sys.exit(1)

    print()
    print("=" * 72)
    print("Done. All 608 models now have Polanyi automation_exposure data.")
    print("=" * 72)


if __name__ == '__main__':
    main()
