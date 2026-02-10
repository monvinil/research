#!/usr/bin/env python3
"""Research cycle runner — Cycle 1: Full live data pull + analysis.

Pulls from all 4 connectors, extracts signals, scores them through
the Principles Engine, identifies opportunity clusters, and writes
results to the dashboard JSON files.

Usage:
    python scripts/run_cycle.py
    python scripts/run_cycle.py --verbose
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Data I/O helpers
# ---------------------------------------------------------------------------

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_state():
    return load_json(os.path.join(DATA_DIR, 'context', 'state.json'))


def save_state(state):
    save_json(os.path.join(DATA_DIR, 'context', 'state.json'), state)


# ---------------------------------------------------------------------------
# Phase 1: SCAN — pull raw data from all connectors
# ---------------------------------------------------------------------------

def phase_scan(verbose=False):
    """Pull data from all 4 connectors and return raw results."""
    print('\n' + '=' * 60)
    print('PHASE 1: SCANNING — pulling live data from all connectors')
    print('=' * 60)

    raw = {}

    # --- FRED ---
    print('\n[FRED] Pulling macro economic indicators...')
    try:
        from connectors.fred import FredConnector
        fred = FredConnector()

        print('  Labor cost squeeze (P2)...')
        raw['fred_labor_squeeze'] = fred.get_labor_cost_squeeze()

        print('  Credit stress (P2)...')
        raw['fred_credit_stress'] = fred.get_credit_stress()

        print('  Job market gaps (P5)...')
        raw['fred_job_gaps'] = fred.get_job_market_gaps()

        print('  Interest rate environment...')
        raw['fred_rates'] = fred.get_interest_rate_environment()

        print('  [FRED] OK — 4 datasets pulled')
    except Exception as e:
        print(f'  [FRED] ERROR: {e}')

    # --- BLS ---
    print('\n[BLS] Pulling employment and wage data...')
    try:
        from connectors.bls import BLSConnector
        bls = BLSConnector()

        print('  Industry employment trends (P2/P5)...')
        raw['bls_industry'] = bls.get_employment_by_industry()

        print('  Wage inflation (P3)...')
        raw['bls_wages'] = bls.get_wage_inflation()

        print('  Job openings & quits (P5)...')
        raw['bls_jolts'] = bls.get_job_openings_and_quits()

        print('  [BLS] OK — 3 datasets pulled')
    except Exception as e:
        print(f'  [BLS] ERROR: {e}')

    # --- EDGAR ---
    print('\n[EDGAR] Scanning SEC filings for distress signals...')
    try:
        from connectors.edgar import EdgarConnector
        edgar = EdgarConnector()

        print('  Corporate distress scan (P2)...')
        raw['edgar_distress'] = edgar.scan_for_distress()

        print('  AI adoption failures (P2)...')
        raw['edgar_ai_failures'] = edgar.scan_for_ai_adoption_failures()

        print('  [EDGAR] OK — 2 scans complete')
    except Exception as e:
        print(f'  [EDGAR] ERROR: {e}')

    # --- Web Search ---
    print('\n[WEB] Scanning for qualitative signals...')
    try:
        from connectors.websearch import WebSearchConnector
        ws = WebSearchConnector()

        print('  Liquidation cascade signals (P2)...')
        raw['web_liquidation'] = ws.scan_liquidation_signals(num_results=5)

        print('  Practitioner pain signals (P2/P3)...')
        raw['web_practitioner'] = ws.scan_practitioner_pain(num_results=5)

        print('  Dead business revival signals (P4)...')
        raw['web_dead_revival'] = ws.scan_dead_business_revival(num_results=5)

        print('  Demographic gap signals (P5)...')
        raw['web_demographics'] = ws.scan_demographic_gaps(num_results=5)

        print('  Inference cost signals (P1)...')
        raw['web_inference'] = ws.scan_inference_cost_drops(num_results=5)

        print('  [WEB] OK — 5 scans complete')
    except Exception as e:
        print(f'  [WEB] ERROR: {e}')

    return raw


# ---------------------------------------------------------------------------
# Phase 2: EXTRACT — turn raw data into structured signals
# ---------------------------------------------------------------------------

def extract_signals(raw, verbose=False):
    """Extract actionable signals from raw connector data."""
    print('\n' + '=' * 60)
    print('PHASE 2: EXTRACTING SIGNALS from raw data')
    print('=' * 60)

    signals = []

    # --- FRED signals ---
    if 'fred_labor_squeeze' in raw:
        signals.extend(_extract_fred_squeeze(raw['fred_labor_squeeze']))
    if 'fred_credit_stress' in raw:
        signals.extend(_extract_fred_credit(raw['fred_credit_stress']))
    if 'fred_job_gaps' in raw:
        signals.extend(_extract_fred_jobs(raw['fred_job_gaps']))
    if 'fred_rates' in raw:
        signals.extend(_extract_fred_rates(raw['fred_rates']))

    # --- BLS signals ---
    if 'bls_industry' in raw:
        signals.extend(_extract_bls_industry(raw['bls_industry']))
    if 'bls_wages' in raw:
        signals.extend(_extract_bls_wages(raw['bls_wages']))
    if 'bls_jolts' in raw:
        signals.extend(_extract_bls_jolts(raw['bls_jolts']))

    # --- EDGAR signals ---
    if 'edgar_distress' in raw:
        signals.extend(_extract_edgar_distress(raw['edgar_distress']))
    if 'edgar_ai_failures' in raw:
        signals.extend(_extract_edgar_ai(raw['edgar_ai_failures']))

    # --- Web signals ---
    for key in ['web_liquidation', 'web_practitioner', 'web_dead_revival',
                'web_demographics', 'web_inference']:
        if key in raw:
            signals.extend(_extract_web_signals(raw[key]))

    print(f'\n  Total signals extracted: {len(signals)}')
    return signals


def _latest(series_data, key='observations'):
    """Get latest observation from a series."""
    obs = series_data.get(key, [])
    return obs[0] if obs else None


def _pct_change(obs_list, periods=12):
    """Calculate % change over N periods in a series."""
    if len(obs_list) < periods + 1:
        return None
    try:
        current = obs_list[0]['value']
        past = obs_list[periods]['value']
        if past and past != 0:
            return round((current - past) / past * 100, 2)
    except (KeyError, TypeError, IndexError):
        pass
    return None


def _extract_fred_squeeze(data):
    signals = []
    d = data.get('data', {})

    # Unit labor costs trend
    ulc = d.get('unit_labor_costs', {})
    ulc_obs = ulc.get('observations', [])
    if len(ulc_obs) >= 2:
        latest_val = ulc_obs[0]['value']
        prev_val = ulc_obs[1]['value']
        change = round(latest_val - prev_val, 2)
        direction = 'rising' if change > 0 else 'falling'
        signals.append({
            'headline': f'Unit labor costs {direction} ({change:+.1f} pts to {latest_val:.1f})',
            'principle': 'P2',
            'category': 'macro_squeeze',
            'source': 'FRED',
            'data_point': f'ULCNFB: {latest_val:.1f} (latest: {ulc_obs[0]["date"]})',
            'strength': 'strong' if abs(change) > 1 else 'moderate',
            'sector': 'all_nonfarm',
        })

    # Productivity vs wages divergence
    prod = d.get('productivity', {}).get('observations', [])
    wages = d.get('avg_hourly_earnings', {}).get('observations', [])
    if prod and wages:
        prod_chg = _pct_change(prod, min(4, len(prod) - 1))
        wage_chg = _pct_change(wages, min(12, len(wages) - 1))
        if prod_chg is not None and wage_chg is not None:
            gap = round(wage_chg - (prod_chg or 0), 2)
            if gap > 0:
                signals.append({
                    'headline': f'Wage growth ({wage_chg:+.1f}%) outpacing productivity ({prod_chg:+.1f}%) — squeeze widening',
                    'principle': 'P2',
                    'category': 'macro_squeeze',
                    'source': 'FRED',
                    'data_point': f'Wage-productivity gap: {gap:+.1f}pp',
                    'strength': 'strong' if gap > 2 else 'moderate',
                    'sector': 'all_nonfarm',
                })

    # Absolute wage level
    if wages:
        latest_wage = wages[0]
        signals.append({
            'headline': f'Average hourly earnings: ${latest_wage["value"]:.2f} (as of {latest_wage["date"]})',
            'principle': 'P3',
            'category': 'cost_baseline',
            'source': 'FRED',
            'data_point': f'CES0500000003: ${latest_wage["value"]:.2f}',
            'strength': 'reference',
            'sector': 'private_sector',
        })

    return signals


def _extract_fred_credit(data):
    signals = []
    d = data.get('data', {})

    # Business loan delinquency
    delinq = d.get('business_loan_delinquency', {}).get('observations', [])
    if delinq:
        latest = delinq[0]
        signals.append({
            'headline': f'Business loan delinquency rate: {latest["value"]:.2f}% ({latest["date"]})',
            'principle': 'P2',
            'category': 'credit_stress',
            'source': 'FRED',
            'data_point': f'DRSFRMACBS: {latest["value"]:.2f}%',
            'strength': 'strong' if latest['value'] > 3.0 else 'moderate' if latest['value'] > 2.0 else 'weak',
            'sector': 'all_business',
        })

    # High yield spread
    hy = d.get('high_yield_spread', {}).get('observations', [])
    if hy:
        latest = hy[0]
        signals.append({
            'headline': f'High yield corporate bond spread: {latest["value"]:.2f}% ({latest["date"]})',
            'principle': 'P2',
            'category': 'credit_stress',
            'source': 'FRED',
            'data_point': f'BAMLH0A0HYM2: {latest["value"]:.2f}%',
            'strength': 'strong' if latest['value'] > 5.0 else 'moderate' if latest['value'] > 3.5 else 'weak',
            'sector': 'corporate_debt',
        })

    return signals


def _extract_fred_jobs(data):
    signals = []
    d = data.get('data', {})

    openings = d.get('job_openings', {}).get('observations', [])
    quits = d.get('quits_rate', {}).get('observations', [])
    unemp = d.get('unemployment_rate', {}).get('observations', [])

    if openings:
        latest = openings[0]
        val_k = latest['value']
        signals.append({
            'headline': f'Job openings: {val_k:,.0f}K ({latest["date"]}) — {"elevated" if val_k > 7000 else "normalizing" if val_k > 5000 else "contracting"}',
            'principle': 'P5',
            'category': 'labor_gap',
            'source': 'FRED',
            'data_point': f'JOLTS openings: {val_k:,.0f}K',
            'strength': 'strong' if val_k > 8000 else 'moderate',
            'sector': 'all_nonfarm',
        })

    if unemp:
        latest = unemp[0]
        signals.append({
            'headline': f'Unemployment rate: {latest["value"]:.1f}% ({latest["date"]})',
            'principle': 'P5',
            'category': 'labor_market',
            'source': 'FRED',
            'data_point': f'UNRATE: {latest["value"]:.1f}%',
            'strength': 'reference',
            'sector': 'all_civilian',
        })

    # Openings-to-unemployment ratio
    if openings and unemp:
        ratio = round(openings[0]['value'] / (unemp[0]['value'] * 1000) * 100, 2) if unemp[0]['value'] else None
        if ratio:
            signals.append({
                'headline': f'Job openings per unemployed person ratio signals {"tight" if ratio > 1.0 else "loosening"} labor market',
                'principle': 'P5',
                'category': 'labor_gap',
                'source': 'FRED',
                'data_point': f'Openings/Unemployed ratio: ~{ratio:.1f}',
                'strength': 'strong' if ratio > 1.2 else 'moderate',
                'sector': 'all_nonfarm',
            })

    return signals


def _extract_fred_rates(data):
    signals = []
    d = data.get('data', {})

    fed = d.get('fed_funds_rate', {}).get('observations', [])
    spread = d.get('yield_curve_spread', {}).get('observations', [])

    if fed:
        latest = fed[0]
        signals.append({
            'headline': f'Fed funds rate: {latest["value"]:.2f}% — {"restrictive" if latest["value"] > 4 else "neutral" if latest["value"] > 2 else "accommodative"} policy',
            'principle': 'P2',
            'category': 'rate_environment',
            'source': 'FRED',
            'data_point': f'FEDFUNDS: {latest["value"]:.2f}%',
            'strength': 'reference',
            'sector': 'macro',
        })

    if spread:
        latest = spread[0]
        inverted = latest['value'] < 0
        signals.append({
            'headline': f'Yield curve (10Y-2Y): {latest["value"]:+.2f}% — {"INVERTED (recession signal)" if inverted else "normal"}',
            'principle': 'P2',
            'category': 'rate_environment',
            'source': 'FRED',
            'data_point': f'T10Y2Y: {latest["value"]:+.2f}%',
            'strength': 'strong' if inverted else 'reference',
            'sector': 'macro',
        })

    return signals


def _extract_bls_industry(data):
    signals = []
    industry_names = {
        'CES6500000001': 'Education & Health Services',
        'CES5500000001': 'Financial Activities',
        'CES6000000001': 'Professional & Business Services',
        'CES4300000001': 'Transportation & Warehousing',
    }

    for sid, series in data.get('data', {}).items():
        obs = series.get('observations', [])
        if len(obs) >= 13:
            current = obs[0]['value']
            year_ago = obs[12]['value'] if len(obs) > 12 else None
            if current and year_ago:
                change = round((current - year_ago) / year_ago * 100, 2)
                name = industry_names.get(sid, sid)
                direction = 'growing' if change > 0 else 'declining'
                signals.append({
                    'headline': f'{name}: {current:,.0f}K employed, {direction} {abs(change):.1f}% YoY',
                    'principle': 'P2' if change < 0 else 'P5',
                    'category': 'industry_employment',
                    'source': 'BLS',
                    'data_point': f'{sid}: {current:,.0f}K, YoY: {change:+.1f}%',
                    'strength': 'strong' if abs(change) > 2 else 'moderate',
                    'sector': name.lower().replace(' & ', '_').replace(' ', '_'),
                })

    return signals


def _extract_bls_wages(data):
    signals = []
    for sid, series in data.get('data', {}).items():
        obs = series.get('observations', [])
        if obs:
            latest = obs[0]
            yoy = _pct_change_bls(obs, 4)  # quarterly series
            headline = f'{series["title"]}: {latest["value"]}'
            if yoy is not None:
                headline += f' (YoY: {yoy:+.1f}%)'
            signals.append({
                'headline': headline,
                'principle': 'P3',
                'category': 'wage_inflation',
                'source': 'BLS',
                'data_point': f'{sid}: {latest["value"]} ({latest["year"]}-{latest["period"]})',
                'strength': 'strong' if yoy and yoy > 4 else 'moderate',
                'sector': 'private_sector',
            })
    return signals


def _pct_change_bls(obs, periods=4):
    """% change for BLS observations (dict with 'value')."""
    if len(obs) <= periods:
        return None
    try:
        cur = obs[0]['value']
        prev = obs[periods]['value']
        if cur and prev and prev != 0:
            return round((cur - prev) / prev * 100, 2)
    except (TypeError, IndexError):
        pass
    return None


def _extract_bls_jolts(data):
    signals = []
    for sid, series in data.get('data', {}).items():
        obs = series.get('observations', [])
        if obs:
            latest = obs[0]
            signals.append({
                'headline': f'{series["title"]}: {latest["value"]} ({latest["year"]}-{latest["period"]})',
                'principle': 'P5',
                'category': 'labor_gap',
                'source': 'BLS',
                'data_point': f'{sid}: {latest["value"]}',
                'strength': 'moderate',
                'sector': 'all_nonfarm',
            })
    return signals


def _extract_edgar_distress(data):
    signals = []
    for keyword, result in data.get('data', {}).items():
        total = result.get('total_hits', 0)
        if total > 0:
            top_companies = [r['company'] for r in result.get('results', [])[:3]]
            short_kw = keyword[:60].strip('"')
            signals.append({
                'headline': f'SEC filings: {total} hits for "{short_kw}" — {", ".join(top_companies[:2])}...',
                'principle': 'P2',
                'category': 'corporate_distress',
                'source': 'EDGAR',
                'data_point': f'{total} filings matching: {keyword[:40]}',
                'strength': 'strong' if total > 100 else 'moderate' if total > 20 else 'weak',
                'sector': 'public_companies',
                'companies': top_companies,
            })
    return signals


def _extract_edgar_ai(data):
    signals = []
    result = data.get('data', {})
    total = result.get('total_hits', 0)
    if total > 0:
        top = [r['company'] for r in result.get('results', [])[:5]]
        signals.append({
            'headline': f'{total} 10-K filings mention AI implementation challenges — low-mobility incumbents',
            'principle': 'P2',
            'category': 'ai_adoption_failure',
            'source': 'EDGAR',
            'data_point': f'{total} 10-K filings with AI transition language',
            'strength': 'strong' if total > 50 else 'moderate',
            'sector': 'public_companies',
            'companies': top,
        })
    return signals


def _extract_web_signals(data):
    signals = []
    signal_type = data.get('signal_type', 'unknown')
    principle = data.get('principle', '')

    category_map = {
        'liquidation_cascade': ('liquidation', 'P2'),
        'practitioner_pain': ('practitioner_pain', 'P2'),
        'dead_revival': ('dead_revival', 'P4'),
        'demographic_gap': ('demographic_gap', 'P5'),
        'infra_overhang': ('inference_cost', 'P1'),
    }
    cat, princ = category_map.get(signal_type, ('web_scan', principle))

    for query, results in data.get('data', {}).items():
        if not results:
            continue
        for r in results[:3]:
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            if not title:
                continue
            signals.append({
                'headline': title[:120],
                'principle': princ,
                'category': cat,
                'source': f'Web ({r.get("source", "search")})',
                'data_point': snippet[:200] if snippet else '',
                'strength': 'weak',  # web = qualitative, lower weight
                'sector': 'mixed',
                'url': r.get('url', ''),
            })
    return signals


# ---------------------------------------------------------------------------
# Phase 3: SCORE — principles engine scoring
# ---------------------------------------------------------------------------

def score_signals(signals):
    """Score each signal through the Principles Engine."""
    print('\n' + '=' * 60)
    print('PHASE 3: SCORING signals through Principles Engine')
    print('=' * 60)

    source_quality = {
        'FRED': 9, 'BLS': 9, 'EDGAR': 8,
        'Web (duckduckgo)': 4, 'Web (duckduckgo_html)': 4,
        'Web (serper)': 5, 'Web (search)': 4,
    }

    strength_scores = {'strong': 8, 'moderate': 5, 'weak': 3, 'reference': 2}

    principle_weight = {
        'P1': 7, 'P2': 9, 'P3': 8, 'P4': 6, 'P5': 8, 'P6': 5,
        'capital_modeling': 4,
    }

    for s in signals:
        src_score = source_quality.get(s['source'], 3)
        str_score = strength_scores.get(s.get('strength', 'weak'), 3)
        princ = s.get('principle', '').split(',')[0]
        princ_score = principle_weight.get(princ, 4)

        # Timeliness bonus: government data = current, web = varies
        timeliness = 7 if s['source'] in ('FRED', 'BLS', 'EDGAR') else 4

        raw_score = (src_score * 0.25 + str_score * 0.30 +
                     princ_score * 0.25 + timeliness * 0.20)

        s['relevance_score'] = round(raw_score, 1)
        s['status'] = 'new'

    signals.sort(key=lambda s: s['relevance_score'], reverse=True)

    scored_above_5 = sum(1 for s in signals if s['relevance_score'] >= 5)
    print(f'  Scored {len(signals)} signals')
    print(f'  Above threshold (>=5): {scored_above_5}')
    print(f'  Top score: {signals[0]["relevance_score"] if signals else 0}')

    return signals


# ---------------------------------------------------------------------------
# Phase 4: IDENTIFY OPPORTUNITIES — cluster signals into themes
# ---------------------------------------------------------------------------

def identify_opportunities(signals):
    """Cluster high-scoring signals into opportunity themes."""
    print('\n' + '=' * 60)
    print('PHASE 4: IDENTIFYING OPPORTUNITY CLUSTERS')
    print('=' * 60)

    # Group signals by sector/theme
    sector_signals = {}
    for s in signals:
        sector = s.get('sector', 'mixed')
        if sector not in sector_signals:
            sector_signals[sector] = []
        sector_signals[sector].append(s)

    # Group by principle
    principle_signals = {}
    for s in signals:
        p = s.get('principle', 'unknown').split(',')[0]
        if p not in principle_signals:
            principle_signals[p] = []
        principle_signals[p].append(s)

    # Build opportunities from convergence
    opportunities = []

    # Opp 1: Labor-intensive services under squeeze
    squeeze_signals = [s for s in signals if s['category'] in
                       ('macro_squeeze', 'industry_employment', 'wage_inflation', 'credit_stress')
                       and s['relevance_score'] >= 4]
    if squeeze_signals:
        avg_score = sum(s['relevance_score'] for s in squeeze_signals) / len(squeeze_signals)
        top_data = [s['data_point'] for s in squeeze_signals[:3]]
        opportunities.append({
            'name': 'Labor-Intensive Services Disruption',
            'thesis': (
                'Unit labor costs rising while productivity stagnates. '
                'Industries with 60%+ labor cost ratios face existential squeeze. '
                'Agentic-first entrant captures the cost delta.'
            ),
            'score': round(avg_score * 10, 0),
            'horizon': 'H1',
            'principles_passed': ['P2', 'P3'],
            'status': 'scanning',
            'signal_count': len(squeeze_signals),
            'key_data': top_data,
            'vc_hook': 'Every dollar of wage inflation makes the AI cost advantage wider — this is a self-reinforcing moat.',
        })

    # Opp 2: Demographic gap exploitation
    demo_signals = [s for s in signals if s['category'] in
                    ('labor_gap', 'labor_market', 'demographic_gap')
                    and s['relevance_score'] >= 3]
    if demo_signals:
        avg_score = sum(s['relevance_score'] for s in demo_signals) / len(demo_signals)
        top_data = [s['data_point'] for s in demo_signals[:3]]
        opportunities.append({
            'name': 'Demographic Gap — AI Fills the Shortage',
            'thesis': (
                'Job openings persistently high in specific sectors while workforce '
                'ages out. AI/agentic systems fill roles that literally cannot be '
                'staffed. Regulatory tailwind: solving shortage, not displacing.'
            ),
            'score': round(avg_score * 10, 0),
            'horizon': 'H1',
            'principles_passed': ['P5', 'P2'],
            'status': 'scanning',
            'signal_count': len(demo_signals),
            'key_data': top_data,
            'vc_hook': 'Not replacing workers — filling roles nobody can fill. Solves a crisis, not just saves money.',
        })

    # Opp 3: Corporate distress → asset acquisition
    distress_signals = [s for s in signals if s['category'] in
                        ('corporate_distress', 'ai_adoption_failure')
                        and s['relevance_score'] >= 4]
    if distress_signals:
        avg_score = sum(s['relevance_score'] for s in distress_signals) / len(distress_signals)
        companies = []
        for s in distress_signals:
            companies.extend(s.get('companies', []))
        top_companies = list(dict.fromkeys(companies))[:5]
        opportunities.append({
            'name': 'Distressed Incumbent Acquisition Play',
            'thesis': (
                'Incumbents filing restructuring notices and AI-transition challenges. '
                'Their customer contracts, licenses, and relationships become available. '
                'Acquire distressed assets, run them on agentic stack.'
            ),
            'score': round(avg_score * 10, 0),
            'horizon': 'H2',
            'principles_passed': ['P2', 'P4'],
            'status': 'scanning',
            'signal_count': len(distress_signals),
            'key_data': [f'Companies flagged: {", ".join(top_companies[:3])}'] if top_companies else [],
            'vc_hook': 'Buy the customer base for pennies, operate it at 10x lower cost with agents.',
        })

    # Opp 4: Dead business revival
    revival_signals = [s for s in signals if s['category'] == 'dead_revival']
    if revival_signals:
        avg_score = sum(s['relevance_score'] for s in revival_signals) / len(revival_signals)
        opportunities.append({
            'name': 'Dead Business Model Revival (AI Economics)',
            'thesis': (
                'Business models that failed due to unit economics or coordination costs '
                'may now work with agentic infrastructure. The market already validated '
                'demand — only the cost side killed them.'
            ),
            'score': round(avg_score * 10, 0),
            'horizon': 'H2',
            'principles_passed': ['P4', 'P1'],
            'status': 'scanning',
            'signal_count': len(revival_signals),
            'key_data': [s['headline'][:80] for s in revival_signals[:2]],
            'vc_hook': 'The market proved the demand exists. AI just fixed the supply side.',
        })

    # Opp 5: Inference cost collapse
    infra_signals = [s for s in signals if s['category'] == 'inference_cost']
    if infra_signals:
        avg_score = sum(s['relevance_score'] for s in infra_signals) / len(infra_signals)
        opportunities.append({
            'name': 'Infrastructure Overhang Exploitation',
            'thesis': (
                'AI inference costs dropping 10x/year. Businesses designed around '
                'current cost curves will see margins explode as costs collapse. '
                'Build at the cost floor, ride the curve down.'
            ),
            'score': round(avg_score * 10, 0),
            'horizon': 'H1',
            'principles_passed': ['P1'],
            'status': 'scanning',
            'signal_count': len(infra_signals),
            'key_data': [s['headline'][:80] for s in infra_signals[:2]],
            'vc_hook': 'Every quarter, the same product costs less to run. Margins go up automatically.',
        })

    opportunities.sort(key=lambda o: o['score'], reverse=True)

    print(f'  Identified {len(opportunities)} opportunity clusters:')
    for i, opp in enumerate(opportunities, 1):
        print(f'    {i}. {opp["name"]} (score: {opp["score"]}, {opp["signal_count"]} signals)')

    return opportunities


# ---------------------------------------------------------------------------
# Phase 5: COMPILE — write results to UI and data files
# ---------------------------------------------------------------------------

def compile_results(signals, opportunities, state, raw, verbose=False):
    """Write all results to data files for the dashboard."""
    print('\n' + '=' * 60)
    print('PHASE 5: COMPILING results to dashboard')
    print('=' * 60)

    now = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Update state
    state['current_cycle'] = 1
    state['agent_performance']['agent_a']['signals_produced'] = len(signals)
    state['agent_performance']['agent_a']['signals_above_threshold'] = sum(
        1 for s in signals if s['relevance_score'] >= 5)
    state['agent_performance']['agent_a']['avg_relevance_score'] = round(
        sum(s['relevance_score'] for s in signals) / len(signals), 2) if signals else 0

    # Top source categories
    cat_counts = {}
    for s in signals:
        cat = s['source']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    state['agent_performance']['agent_a']['top_source_categories'] = sorted(
        cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Sector heatmap
    sector_counts = {}
    for s in signals:
        sector = s.get('sector', 'mixed')
        if sector not in sector_counts:
            sector_counts[sector] = {'signal_count': 0, 'avg_score': 0, 'scores': []}
        sector_counts[sector]['signal_count'] += 1
        sector_counts[sector]['scores'].append(s['relevance_score'])

    for sector in sector_counts:
        scores = sector_counts[sector]['scores']
        sector_counts[sector]['avg_score'] = round(sum(scores) / len(scores), 1)
        del sector_counts[sector]['scores']

    # Geography heatmap (most signals are US-focused for now)
    geo_heatmap = {
        'US': {'signal_count': sum(1 for s in signals if s['source'] in ('FRED', 'BLS', 'EDGAR')),
               'avg_score': 6.0},
        'Global': {'signal_count': sum(1 for s in signals if 'Web' in s['source']),
                   'avg_score': 4.0},
    }

    # Build dashboard
    dashboard = {
        'last_updated': now,
        'current_cycle': 1,
        'total_signals_scanned': len(signals),
        'total_opportunities_verified': 0,
        'active_opportunities': len(opportunities),
        'top_opportunities': opportunities,
        'sector_heatmap': sector_counts,
        'geography_heatmap': geo_heatmap,
        'cycle_history': [{
            'cycle': 1,
            'signals': len(signals),
            'verified': 0,
            'top_score': opportunities[0]['score'] if opportunities else 0,
        }],
    }

    # Build signals feed (for UI)
    feed_signals = []
    for s in signals:
        feed_signals.append({
            'relevance_score': s['relevance_score'],
            'headline': s['headline'],
            'source': s['source'],
            'category': s['category'],
            'status': s['status'],
            'principle': s.get('principle', ''),
        })

    # Save everything
    save_json(os.path.join(DATA_DIR, 'ui', 'dashboard.json'), dashboard)
    save_json(os.path.join(DATA_DIR, 'ui', 'signals_feed.json'),
              {'recent_signals': feed_signals})
    save_json(os.path.join(DATA_DIR, 'signals', f'{date_str}.json'), {
        'cycle': 1,
        'date': date_str,
        'total_signals': len(signals),
        'signals': signals,
    })
    save_json(os.path.join(DATA_DIR, 'opportunities', f'{date_str}.json'), {
        'cycle': 1,
        'date': date_str,
        'opportunities': opportunities,
    })

    # Save raw data for reference
    raw_safe = {}
    for k, v in raw.items():
        try:
            json.dumps(v)
            raw_safe[k] = v
        except (TypeError, ValueError):
            raw_safe[k] = str(v)
    save_json(os.path.join(DATA_DIR, 'raw', f'{date_str}.json'), {
        'cycle': 1,
        'date': date_str,
        'raw_data': raw_safe,
    })

    save_state(state)

    print(f'  Dashboard updated: data/ui/dashboard.json')
    print(f'  Signals feed updated: data/ui/signals_feed.json ({len(feed_signals)} signals)')
    print(f'  Raw data saved: data/raw/{date_str}.json')
    print(f'  Opportunities saved: data/opportunities/{date_str}.json')

    return dashboard


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Run research cycle')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed output')
    args = parser.parse_args()

    print('\n' + '#' * 60)
    print('#  AI ECONOMIC RESEARCH ENGINE — CYCLE 1')
    print('#  ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))
    print('#' * 60)

    state = load_state()
    start = time.time()

    # Phase 1: Scan
    raw = phase_scan(verbose=args.verbose)

    # Phase 2: Extract signals
    signals = extract_signals(raw, verbose=args.verbose)

    # Phase 3: Score
    signals = score_signals(signals)

    # Phase 4: Identify opportunities
    opportunities = identify_opportunities(signals)

    # Phase 5: Compile
    dashboard = compile_results(signals, opportunities, state, raw, verbose=args.verbose)

    elapsed = round(time.time() - start, 1)

    print('\n' + '#' * 60)
    print(f'#  CYCLE 1 COMPLETE — {elapsed}s')
    print(f'#  Signals: {len(signals)} | Opportunities: {len(opportunities)}')
    print(f'#  Top opportunity: {opportunities[0]["name"] if opportunities else "none"}')
    print(f'#  Score: {opportunities[0]["score"] if opportunities else 0}')
    print('#' * 60)
    print(f'\nDashboard ready. Run:  python scripts/serve_ui.py')
    print(f'Then open:  http://localhost:8080\n')


if __name__ == '__main__':
    main()
