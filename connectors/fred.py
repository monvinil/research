"""FRED (Federal Reserve Economic Data) connector.

Key series for the research engine:
- Labor costs by industry (P2 liquidation cascade detection)
- CPI and inflation metrics (P3 cost advantage baselines)
- Interest rates (runway/capital modeling)
- Industry production indices (P2 cascade signals)

API docs: https://fred.stlouisfed.org/docs/api/fred/
Free key: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import requests
from datetime import datetime, timedelta
from .config import FRED_API_KEY

BASE_URL = 'https://api.stlouisfed.org/fred'

# Series relevant to our Principles Engine
SERIES_CATALOG = {
    # P2: Liquidation cascade — labor cost squeeze indicators
    'ECIWAG': 'Employment Cost Index: Wages & Salaries (quarterly)',
    'CES0500000003': 'Average Hourly Earnings, Private (monthly)',
    'OPHNFB': 'Nonfarm Business Output Per Hour (quarterly, productivity)',
    'ULCNFB': 'Unit Labor Costs: Nonfarm Business (quarterly)',

    # P2: Industry health — margin pressure
    'INDPRO': 'Industrial Production Index (monthly)',
    'CMRMTSPL': 'Real Retail Sales (monthly)',
    'BUSLOANS': 'Commercial & Industrial Loans (weekly, credit stress)',
    'DRSFRMACBS': 'Delinquency Rate on Business Loans (quarterly)',

    # P3: Cost baselines for unit economics
    'CPIAUCSL': 'Consumer Price Index, All Urban (monthly)',
    'PPIACO': 'Producer Price Index, All Commodities (monthly)',
    'PCEPILFE': 'Core PCE Price Index (monthly)',

    # P5: Demographic / labor market gaps
    'UNRATE': 'Unemployment Rate (monthly)',
    'JTSJOL': 'Job Openings: Total Nonfarm (monthly, JOLTS)',
    'JTSQUL': 'Quits: Total Nonfarm (monthly, JOLTS)',
    'LNS14000006': 'Unemployment Rate: Black/African American',
    'LNS14000009': 'Unemployment Rate: Hispanic/Latino',

    # Capital / interest rate environment
    'FEDFUNDS': 'Federal Funds Effective Rate (monthly)',
    'DGS10': '10-Year Treasury Yield (daily)',
    'BAMLH0A0HYM2': 'High Yield Corporate Bond Spread (daily)',
    'T10Y2Y': '10Y-2Y Treasury Spread (daily, recession signal)',

    # P1: Infrastructure overhang indicators
    'BOGZ1FL893065105Q': 'Nonfinancial Corporate Business: Capital Expenditures',

    # Corporate profitability
    'CP': 'Corporate Profits After Tax (quarterly)',
    'CPATAX': 'Corporate Profits After Tax with IVA and CCAdj (quarterly)',
    'A445RC1Q027SBEA': 'Corporate Profits: Nonfinancial (quarterly)',
    'W260RC1Q027SBEA': 'Corporate Profits: Financial (quarterly)',

    # Financial stress and volatility
    'VIXCLS': 'CBOE Volatility Index (daily)',
    'STLFSI4': 'St. Louis Fed Financial Stress Index (weekly)',
    'DRTSCILM': 'Net % Banks Tightening C&I Loan Standards, Large Firms (quarterly)',
    'DRTSCLCC': 'Net % Banks Tightening Credit Card Loan Standards (quarterly)',

    # Employment Cost Index by sector
    'ECIALLCIV': 'ECI Total Compensation All Civilian (quarterly)',
    'ECIWAG': 'ECI Wages and Salaries All Civilian (quarterly)',

    # Small business health
    'EVANQ': 'Business Applications, High-Propensity (quarterly)',
    'BABATOTALSAUS': 'Business Applications Total (monthly)',
    'BUSAPPWNSAUS': 'Business Applications Without Planned Wages (monthly)',

    # Asset prices and transactions (P2 liquidation cascades)
    'BOGZ1FL893065005Q': 'Nonfinancial Business: Total Liabilities (quarterly)',
    'NCBEILQ027S': 'Nonfinancial Corporate Business: Inventories (quarterly)',
}


class FredConnector:
    """Pull economic data series from FRED."""

    def __init__(self, api_key=None):
        self.api_key = api_key or FRED_API_KEY
        if not self.api_key:
            raise ValueError(
                'FRED API key required. Get free key at: '
                'https://fred.stlouisfed.org/docs/api/api_key.html\n'
                'Then set FRED_API_KEY in .env'
            )

    def _get(self, endpoint, params=None):
        params = params or {}
        params['api_key'] = self.api_key
        params['file_type'] = 'json'
        r = requests.get(f'{BASE_URL}/{endpoint}', params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_series(self, series_id, start_date=None, end_date=None, limit=100):
        """Get observations for a FRED series.

        Args:
            series_id: FRED series ID (e.g., 'UNRATE')
            start_date: 'YYYY-MM-DD' or None for 2 years back
            end_date: 'YYYY-MM-DD' or None for today
            limit: max observations to return

        Returns:
            dict with 'series_id', 'title', 'observations' list
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

        params = {
            'series_id': series_id,
            'observation_start': start_date,
            'sort_order': 'desc',
            'limit': limit,
        }
        if end_date:
            params['observation_end'] = end_date

        try:
            data = self._get('series/observations', params)
        except Exception:
            return {
                'series_id': series_id,
                'title': SERIES_CATALOG.get(series_id, series_id),
                'observations': [],
                'error': f'Failed to fetch {series_id}',
            }

        observations = []
        for obs in data.get('observations', []):
            val = obs.get('value', '.')
            if val != '.':
                observations.append({
                    'date': obs['date'],
                    'value': float(val),
                })

        return {
            'series_id': series_id,
            'title': SERIES_CATALOG.get(series_id, series_id),
            'observations': observations,
        }

    def get_series_info(self, series_id):
        """Get metadata about a FRED series."""
        data = self._get('series', {'series_id': series_id})
        s = data.get('seriess', [{}])[0]
        return {
            'id': s.get('id'),
            'title': s.get('title'),
            'frequency': s.get('frequency'),
            'units': s.get('units'),
            'seasonal_adjustment': s.get('seasonal_adjustment'),
            'last_updated': s.get('last_updated'),
            'notes': s.get('notes', '')[:200],
        }

    def search_series(self, query, limit=10):
        """Search FRED for series matching a query.

        Use this to find series relevant to specific industries/patterns
        the engine identifies.
        """
        data = self._get('series/search', {
            'search_text': query,
            'limit': limit,
            'order_by': 'popularity',
        })
        results = []
        for s in data.get('seriess', []):
            results.append({
                'id': s.get('id'),
                'title': s.get('title'),
                'frequency': s.get('frequency'),
                'popularity': s.get('popularity'),
                'last_updated': s.get('last_updated'),
            })
        return results

    def get_labor_cost_squeeze(self):
        """P2 signal: Get labor cost vs. productivity data to detect squeeze.

        When unit labor costs rise faster than output, industries are in
        a cost squeeze — prime candidates for agentic disruption.
        """
        ulc = self.get_series('ULCNFB', limit=20)
        productivity = self.get_series('OPHNFB', limit=20)
        wages = self.get_series('CES0500000003', limit=24)
        cpi = self.get_series('CPIAUCSL', limit=24)

        return {
            'signal_type': 'labor_cost_squeeze',
            'principle': 'P2',
            'data': {
                'unit_labor_costs': ulc,
                'productivity': productivity,
                'avg_hourly_earnings': wages,
                'cpi': cpi,
            },
            'interpretation': (
                'If unit labor costs rising while productivity flat/falling, '
                'industries are in a squeeze. Cross-reference with BLS '
                'occupation data to find which specific roles are driving costs.'
            ),
        }

    def get_credit_stress(self):
        """P2 signal: Business loan delinquency + credit conditions.

        Rising delinquency = businesses struggling to service debt.
        Combined with AI competition pressure = liquidation cascade.
        """
        delinquency = self.get_series('DRSFRMACBS', limit=20)
        loans = self.get_series('BUSLOANS', limit=50)
        hy_spread = self.get_series('BAMLH0A0HYM2', limit=50)

        return {
            'signal_type': 'credit_stress',
            'principle': 'P2',
            'data': {
                'business_loan_delinquency': delinquency,
                'commercial_loans_outstanding': loans,
                'high_yield_spread': hy_spread,
            },
            'interpretation': (
                'Rising delinquency + widening HY spread = businesses under '
                'financial stress. These are the ones most vulnerable to '
                'cost-structure disruption from agentic competitors.'
            ),
        }

    def get_job_market_gaps(self):
        """P5 signal: Job openings vs. unemployment — where are the gaps?"""
        openings = self.get_series('JTSJOL', limit=24)
        quits = self.get_series('JTSQUL', limit=24)
        unemployment = self.get_series('UNRATE', limit=24)

        return {
            'signal_type': 'labor_market_gap',
            'principle': 'P5',
            'data': {
                'job_openings': openings,
                'quits_rate': quits,
                'unemployment_rate': unemployment,
            },
            'interpretation': (
                'High openings + high quits + low unemployment = tight labor '
                'market where employers cannot fill roles. These gaps are where '
                'agentic substitution faces least resistance.'
            ),
        }

    def get_interest_rate_environment(self):
        """Capital modeling: What does the rate environment favor?"""
        fed_funds = self.get_series('FEDFUNDS', limit=24)
        ten_year = self.get_series('DGS10', limit=50)
        spread = self.get_series('T10Y2Y', limit=50)

        return {
            'signal_type': 'rate_environment',
            'principle': 'capital_modeling',
            'data': {
                'fed_funds_rate': fed_funds,
                'ten_year_yield': ten_year,
                'yield_curve_spread': spread,
            },
            'interpretation': (
                'High rates favor cash-flow-positive, low-burn businesses. '
                'This aligns with agentic-first cost structures. Inverted '
                'yield curve = recession signal = accelerated liquidation cascades.'
            ),
        }

    def get_industry_profitability(self):
        """Corporate profitability trends -- detect margin compression by sector."""
        series = ['CP', 'CPATAX', 'A445RC1Q027SBEA', 'W260RC1Q027SBEA']
        results = {sid: self.get_series(sid, limit=20) for sid in series}
        return {
            'signal_type': 'industry_profitability',
            'principle': 'P2',
            'data': results,
            'interpretation': (
                'Declining corporate profits = margin compression. '
                'Divergence between financial and nonfinancial profits '
                'indicates sector-specific stress patterns.'
            ),
        }

    def get_market_stress_indicators(self):
        """Financial stress and volatility -- macro risk environment."""
        series = ['VIXCLS', 'STLFSI4', 'DRTSCILM', 'DRTSCLCC']
        results = {sid: self.get_series(sid, limit=50) for sid in series}
        return {
            'signal_type': 'market_stress',
            'principle': 'P2,capital_modeling',
            'data': results,
            'interpretation': (
                'Rising VIX + tightening lending standards = credit stress. '
                'Banks tightening C&I loans = incumbents losing access to '
                'restructuring capital. Favors cash-flow-positive agentic entrants.'
            ),
        }

    def get_sector_employment_costs(self):
        """Employment Cost Index by sector -- where is labor getting most expensive?"""
        series = ['ECIALLCIV', 'ECIWAG']
        results = {sid: self.get_series(sid, limit=20) for sid in series}
        return {
            'signal_type': 'sector_employment_costs',
            'principle': 'P3',
            'data': results,
            'interpretation': (
                'Sectors where total compensation grows fastest offer widest '
                'cost advantage for agentic substitution. Compare Professional & '
                'Business Services vs. Education & Health to find divergence.'
            ),
        }

    def get_small_business_indicators(self):
        """Small business formation and health -- P2 cascade + P4 revival signals."""
        series = ['EVANQ', 'BABATOTALSAUS', 'BUSAPPWNSAUS', 'DRSFRMACBS']
        results = {sid: self.get_series(sid, limit=30) for sid in series}
        return {
            'signal_type': 'small_business_health',
            'principle': 'P2,P4',
            'data': results,
            'interpretation': (
                'Rising business applications + rising delinquency = churn. '
                'Old businesses dying, new ones forming. Applications without '
                'planned wages may indicate solo/agentic business formation.'
            ),
        }

    def get_asset_prices_and_transactions(self):
        """Asset and liability indicators -- P2 liquidation cascade timing."""
        series = ['BOGZ1FL893065005Q', 'NCBEILQ027S', 'BOGZ1FL893065105Q']
        results = {sid: self.get_series(sid, limit=20) for sid in series}
        return {
            'signal_type': 'asset_transactions',
            'principle': 'P2',
            'data': results,
            'interpretation': (
                'Rising liabilities + falling capex = businesses taking on '
                'debt without investing. Inventory buildup may signal demand '
                'collapse. These are pre-liquidation indicators.'
            ),
        }

    def test_connection(self):
        """Verify the API key works."""
        try:
            result = self.get_series('UNRATE', limit=1)
            latest = result['observations'][0] if result['observations'] else None
            return {
                'status': 'ok',
                'source': 'FRED',
                'test_series': 'UNRATE (Unemployment Rate)',
                'latest_value': latest,
                'catalog_size': len(SERIES_CATALOG),
            }
        except Exception as e:
            return {'status': 'error', 'source': 'FRED', 'error': str(e)}
