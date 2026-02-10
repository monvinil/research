#!/usr/bin/env python3
"""Test all API connections and report status.

Usage:
    python scripts/test_connections.py
    python scripts/test_connections.py --verbose
    python scripts/test_connections.py --only fred,bls
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.config import FRED_API_KEY, BLS_API_KEY, EDGAR_CONTACT_EMAIL, SERPER_API_KEY


def test_fred(verbose=False):
    print('\n--- FRED (Federal Reserve Economic Data) ---')
    if not FRED_API_KEY:
        print('  [SKIP] No FRED_API_KEY set.')
        print('  Get free key: https://fred.stlouisfed.org/docs/api/api_key.html')
        return False

    from connectors.fred import FredConnector
    fred = FredConnector()
    result = fred.test_connection()

    if result['status'] == 'ok':
        latest = result.get('latest_value', {})
        print(f'  [OK] Connected. {result["catalog_size"]} pre-mapped series.')
        if latest:
            print(f'  Latest unemployment rate: {latest["value"]}% ({latest["date"]})')

        if verbose:
            print('\n  Pulling labor cost squeeze data...')
            squeeze = fred.get_labor_cost_squeeze()
            for key, series in squeeze['data'].items():
                obs = series['observations']
                if obs:
                    print(f'    {series["title"]}: latest = {obs[0]["value"]} ({obs[0]["date"]})')

            print('\n  Pulling job market gaps...')
            gaps = fred.get_job_market_gaps()
            for key, series in gaps['data'].items():
                obs = series['observations']
                if obs:
                    print(f'    {series["title"]}: latest = {obs[0]["value"]} ({obs[0]["date"]})')
        return True
    else:
        print(f'  [FAIL] {result["error"]}')
        return False


def test_bls(verbose=False):
    print('\n--- BLS (Bureau of Labor Statistics) ---')
    from connectors.bls import BLSConnector
    bls = BLSConnector()
    result = bls.test_connection()

    if result['status'] == 'ok':
        latest = result.get('latest_value', {})
        auth = 'with key' if result['authenticated'] else 'without key (25 req/day limit)'
        print(f'  [OK] Connected {auth}. Rate limit: {result["rate_limit"]}')
        if latest:
            print(f'  Latest nonfarm employment: {latest["value"]}K ({latest["year"]}-{latest["period"]})')
        if not result['authenticated']:
            print('  TIP: Get free key for 500 req/day: https://data.bls.gov/registrationEngine/')

        if verbose:
            print('\n  Pulling wage inflation data...')
            wages = bls.get_wage_inflation()
            for sid, series in wages['data'].items():
                obs = series['observations']
                if obs:
                    print(f'    {series["title"]}: latest = {obs[0]["value"]} ({obs[0]["year"]}-{obs[0]["period"]})')
        return True
    else:
        print(f'  [FAIL] {result["error"]}')
        return False


def test_edgar(verbose=False):
    print('\n--- SEC EDGAR ---')
    from connectors.edgar import EdgarConnector
    edgar = EdgarConnector()
    result = edgar.test_connection()

    if result['status'] == 'ok':
        test = result.get('test_search', {})
        print(f'  [OK] Connected. Contact: {result["contact_email"]}')
        if test:
            print(f'  Test search: {test.get("name", "")} (CIK: {test.get("cik", "")})')

        if verbose:
            print('\n  Scanning for corporate distress signals...')
            distress = edgar.scan_for_distress()
            for query, data in distress['data'].items():
                print(f'    "{query[:50]}..." → {data["total_hits"]} hits')
                for r in data['results'][:2]:
                    print(f'      {r["company"]} ({r["form_type"]}, {r["filed_date"]})')
        return True
    else:
        print(f'  [FAIL] {result["error"]}')
        return False


def test_websearch(verbose=False):
    print('\n--- Web Search ---')
    from connectors.websearch import WebSearchConnector

    try:
        ws = WebSearchConnector()
    except ImportError as e:
        print(f'  [SKIP] {e}')
        return False

    result = ws.test_connection()

    if result['status'] == 'ok':
        backend = result['backend']
        test = result.get('test_result', {})
        print(f'  [OK] Connected via {backend}.')
        if test:
            print(f'  Test result: {test.get("title", "")[:60]}')
        if backend == 'duckduckgo':
            print('  Using free DuckDuckGo backend. For higher volume, set SERPER_API_KEY.')

        if verbose:
            print('\n  Running liquidation cascade scan...')
            scan = ws.scan_liquidation_signals(num_results=3)
            for query, results in scan['data'].items():
                print(f'    "{query[:50]}..."')
                for r in results[:2]:
                    print(f'      {r.get("title", "")[:70]}')
        return True
    else:
        print(f'  [FAIL] {result["error"]}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Test API connections')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Run extended tests with sample data pulls')
    parser.add_argument('--only', type=str, default=None,
                        help='Comma-separated list of connectors to test (fred,bls,edgar,websearch)')
    args = parser.parse_args()

    connectors = {
        'fred': test_fred,
        'bls': test_bls,
        'edgar': test_edgar,
        'websearch': test_websearch,
    }

    if args.only:
        selected = [c.strip() for c in args.only.split(',')]
        connectors = {k: v for k, v in connectors.items() if k in selected}

    print('=' * 50)
    print('RESEARCH ENGINE — API CONNECTION TEST')
    print('=' * 50)

    results = {}
    for name, test_fn in connectors.items():
        try:
            results[name] = test_fn(verbose=args.verbose)
        except Exception as e:
            print(f'  [ERROR] Unexpected: {e}')
            results[name] = False

    print('\n' + '=' * 50)
    print('SUMMARY')
    print('=' * 50)
    for name, ok in results.items():
        status = 'READY' if ok else 'NOT CONNECTED'
        symbol = '+' if ok else '-'
        print(f'  [{symbol}] {name.upper():12s} {status}')

    total = sum(results.values())
    print(f'\n  {total}/{len(results)} connectors ready.')

    if total < len(results):
        print('\n  Next steps:')
        if not results.get('fred'):
            print('    1. Get FRED key: https://fred.stlouisfed.org/docs/api/api_key.html')
        if not results.get('websearch'):
            print('    2. pip install duckduckgo-search  (free web search)')
        print('    3. Copy .env.example to .env and add your keys')
        print('    4. Re-run: python scripts/test_connections.py')


if __name__ == '__main__':
    main()
