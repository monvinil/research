#!/usr/bin/env python3
"""v3-13: Run O*NET Polanyi classification on 37 key occupations.

Calls the O*NET API via connectors/onet.py to classify occupations
into Acemoglu-Autor task categories. Caches results for model enrichment.

Runtime: ~90 seconds (37 SOC codes × 2 API calls × 1.2s rate limit)
"""

import json
import sys
from pathlib import Path

# Add project root to path for connector imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.onet import ONetConnector

CACHE_FILE = Path("/Users/mv/Documents/research/data/cache/onet_polanyi_screen.json")


def main():
    print("=" * 70)
    print("v3-13 O*NET Polanyi Classification Screen")
    print("=" * 70)

    connector = ONetConnector()

    # Test connection first
    print("\nTesting O*NET API connection...")
    test = connector.test_connection()
    if test.get('status') != 'ok':
        print(f"  ERROR: {test}")
        return

    print(f"  Connected: {test.get('test_occupation', '?')}")

    # Run bulk Polanyi screen on 37 KEY_OCCUPATIONS
    print(f"\nScreening {len(connector.__class__.__dict__.get('KEY_OCCUPATIONS', {}) or {})} key occupations...")
    print("  (This takes ~90 seconds due to API rate limiting)")

    from connectors.onet import KEY_OCCUPATIONS
    print(f"  SOC codes to screen: {len(KEY_OCCUPATIONS)}")

    results = connector.screen_occupations()

    # Report
    screened = results.get('occupations_screened', 0)
    errors = results.get('errors', [])
    occ_results = results.get('results', [])

    print(f"\n  Screened: {screened}")
    print(f"  Errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"    {e['soc_code']}: {e['error']}")

    # Top 10 by automation exposure
    print(f"\n  Top 10 by Automation Exposure (Baumol Cure targets):")
    for r in occ_results[:10]:
        label = r.get('occupation_label', r.get('title', '?'))
        ae = r.get('automation_exposure', 0)
        jp = r.get('judgment_premium', 0)
        hp = r.get('human_premium', 0)
        print(f"    {label}: auto={ae:.2f}, judgment={jp:.2f}, human={hp:.2f}")

    # Bottom 5 (human premium)
    print(f"\n  Bottom 5 (Human Premium — Baumol Premium candidates):")
    for r in occ_results[-5:]:
        label = r.get('occupation_label', r.get('title', '?'))
        ae = r.get('automation_exposure', 0)
        hp = r.get('human_premium', 0)
        print(f"    {label}: auto={ae:.2f}, human={hp:.2f}")

    # Save to cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved to {CACHE_FILE}")


if __name__ == '__main__':
    main()
