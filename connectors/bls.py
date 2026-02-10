"""BLS (Bureau of Labor Statistics) connector.

Key data for the research engine:
- Occupation-level employment and wages (P5 demographic gaps)
- Industry-level employment trends (P2 liquidation cascades)
- Wage inflation by occupation (P3 cost advantage baselines)
- Job openings by industry (P5 gap detection)

API docs: https://www.bls.gov/developers/
Free key (higher rate limits): https://data.bls.gov/registrationEngine/
Without key: 25 requests/day, 10 years of data
With key: 500 requests/day, 20 years of data
"""

import requests
import json
from datetime import datetime
from .config import BLS_API_KEY

BASE_URL_V2 = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
BASE_URL_V1 = 'https://api.bls.gov/publicAPI/v1/timeseries/data/'

# Series relevant to our Principles Engine
# Format: {series_id: (description, principle)}
SERIES_CATALOG = {
    # Occupational Employment & Wages (OES) — Annual
    # These are computed series IDs. For specific occupations, use search.
    #
    # Employment Cost Index by industry — Quarterly
    'CIU1010000000000A': ('ECI: Total compensation, All workers', 'P2,P3'),
    'CIU1010000000000I': ('ECI: Total compensation, All workers (index)', 'P2,P3'),
    'CIU2010000000000A': ('ECI: Wages & salaries, All workers', 'P2,P3'),
    'CIU2020000000000A': ('ECI: Wages & salaries, Private industry', 'P2,P3'),

    # Current Employment Statistics — Monthly
    'CES0000000001': ('Total Nonfarm Employment', 'P5'),
    'CES0500000003': ('Avg Hourly Earnings, Private', 'P2,P3'),
    'CES6500000001': ('Education & Health Services Employment', 'P5'),
    'CES5500000001': ('Financial Activities Employment', 'P2'),
    'CES6000000001': ('Professional & Business Services Employment', 'P2'),
    'CES4300000001': ('Transportation & Warehousing Employment', 'P2'),
    'CES4142000001': ('Accounting & Bookkeeping Services Employment', 'P2'),

    # Job Openings and Labor Turnover (JOLTS) — Monthly
    'JTS000000000000000JOL': ('Total Nonfarm Job Openings', 'P5'),
    'JTS000000000000000QUR': ('Total Nonfarm Quits Rate', 'P5'),

    # Consumer Price Index — Monthly
    'CUUR0000SA0': ('CPI-U All Items', 'P3'),
    'CUUR0000SA0L1E': ('CPI-U All Items Less Food & Energy', 'P3'),

    # Producer Price Index — Monthly
    'PCU--': ('PPI: Final Demand', 'P3'),

    # CES Average Hourly Earnings by industry (wage premium detection)
    'CES5500000003': ('Avg Hourly Earnings, Financial Activities', 'P3'),
    'CES6054000003': ('Avg Hourly Earnings, Professional and Technical Services', 'P3'),
    'CES6561000003': ('Avg Hourly Earnings, Educational Services', 'P3'),
    'CES6562000003': ('Avg Hourly Earnings, Health Care', 'P3'),
    'CES6500000003': ('Avg Hourly Earnings, Education and Health Services', 'P3'),
}

# Occupations most vulnerable to AI/agentic disruption (SOC codes, no hyphens)
AI_VULNERABLE_OCCUPATIONS = {
    '232011': 'Paralegals and Legal Assistants',
    '232092': 'Law Clerks',
    '132011': 'Accountants and Auditors',
    '132082': 'Tax Preparers',
    '433031': 'Bookkeeping, Accounting, and Auditing Clerks',
    '439061': 'Office Clerks, General',
    '131111': 'Management Analysts',
    '151252': 'Software Quality Assurance Analysts',
    '434051': 'Customer Service Representatives',
    '292052': 'Pharmacy Technicians',
}

# Industries with high labor cost ratios — key targets for P2/P3
INDUSTRY_NAICS = {
    '5411': 'Legal Services',
    '5412': 'Accounting & Bookkeeping',
    '5413': 'Architecture & Engineering',
    '5416': 'Management Consulting',
    '6211': 'Physician Offices',
    '6212': 'Dental Offices',
    '6216': 'Home Health Care',
    '6231': 'Nursing Care Facilities',
    '5242': 'Insurance Agencies',
    '5311': 'Real Estate Lessors',
    '4841': 'Trucking',
    '4885': 'Freight Transportation Arrangement',
    '5221': 'Depository Credit Intermediation',
    '5239': 'Other Financial Investment Activities',
}


class BLSConnector:
    """Pull labor market and employment data from BLS."""

    def __init__(self, api_key=None):
        self.api_key = api_key or BLS_API_KEY
        self.base_url = BASE_URL_V2 if self.api_key else BASE_URL_V1

    def _post(self, series_ids, start_year=None, end_year=None):
        """BLS v2 API uses POST with JSON body."""
        if not start_year:
            start_year = datetime.now().year - 10
        if not end_year:
            end_year = datetime.now().year

        payload = {
            'seriesid': series_ids if isinstance(series_ids, list) else [series_ids],
            'startyear': str(start_year),
            'endyear': str(end_year),
        }

        if self.api_key:
            payload['registrationkey'] = self.api_key

        r = requests.post(self.base_url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        if data.get('status') != 'REQUEST_SUCCEEDED':
            msg = '; '.join(data.get('message', ['Unknown error']))
            raise RuntimeError(f'BLS API error: {msg}')

        return data

    def get_series(self, series_id, start_year=None, end_year=None):
        """Get time series data for a BLS series.

        Returns:
            dict with series_id, description, and observations
        """
        data = self._post(series_id, start_year, end_year)

        observations = []
        for series in data.get('Results', {}).get('series', []):
            for obs in series.get('data', []):
                period = obs.get('period', '')
                # Skip annual averages
                if period == 'M13':
                    continue
                observations.append({
                    'year': obs['year'],
                    'period': period,
                    'value': float(obs['value']) if obs['value'] != '-' else None,
                    'footnotes': [f.get('text', '') for f in obs.get('footnotes', []) if f.get('text')],
                })

        desc = SERIES_CATALOG.get(series_id, (series_id, ''))[0]

        return {
            'series_id': series_id,
            'title': desc,
            'observations': observations,
        }

    def get_multiple_series(self, series_ids, start_year=None, end_year=None):
        """Get multiple series in a single request (up to 50 with key, 25 without)."""
        data = self._post(series_ids, start_year, end_year)

        results = {}
        for series in data.get('Results', {}).get('series', []):
            sid = series.get('seriesID', '')
            observations = []
            for obs in series.get('data', []):
                if obs.get('period') == 'M13':
                    continue
                observations.append({
                    'year': obs['year'],
                    'period': obs.get('period', ''),
                    'value': float(obs['value']) if obs['value'] != '-' else None,
                })
            desc = SERIES_CATALOG.get(sid, (sid, ''))[0]
            results[sid] = {
                'series_id': sid,
                'title': desc,
                'observations': observations,
            }

        return results

    def get_employment_by_industry(self):
        """P2/P5: Employment trends across key industries.

        Look for: declining employment + rising wages = squeeze.
        """
        industry_series = [
            'CES6500000001',  # Education & Health
            'CES5500000001',  # Financial Activities
            'CES6000000001',  # Professional & Business Services
            'CES4300000001',  # Transportation & Warehousing
        ]

        results = self.get_multiple_series(industry_series)

        return {
            'signal_type': 'industry_employment_trends',
            'principle': 'P2,P5',
            'data': results,
            'interpretation': (
                'Industries with flat/declining employment but rising wages '
                'are in a labor squeeze. Cross-reference with FRED unit labor '
                'costs to confirm cascade pressure.'
            ),
        }

    def get_wage_inflation(self):
        """P3: Wage inflation data — baseline for cost advantage calculation.

        If wages are rising X%/year in an industry, and our agentic cost
        stays flat, the advantage widens automatically over time.
        """
        series = [
            'CES0500000003',  # Avg Hourly Earnings, Private
            'CIU2020000000000A',  # ECI Wages, Private
        ]

        results = self.get_multiple_series(series)

        return {
            'signal_type': 'wage_inflation',
            'principle': 'P3',
            'data': results,
            'interpretation': (
                'Rising wages = growing cost advantage for agentic businesses. '
                'Each percentage point of wage inflation widens the moat for '
                'AI-first cost structures that have near-zero marginal labor cost.'
            ),
        }

    def get_job_openings_and_quits(self):
        """P5: Job openings and quit rates — where are the gaps?

        High openings + high quits = people leaving faster than they
        can be replaced. These are the roles AI can fill with least resistance.
        """
        series = [
            'JTS000000000000000JOL',  # Job Openings
            'JTS000000000000000QUR',  # Quits Rate
        ]

        results = self.get_multiple_series(series)

        return {
            'signal_type': 'labor_gaps',
            'principle': 'P5',
            'data': results,
            'interpretation': (
                'High openings + high quits = structural labor shortage. '
                'Industries where this persists for 12+ months have a gap '
                'that agentic substitution can fill with regulatory tailwind '
                '(solving a shortage, not displacing workers).'
            ),
        }

    def build_oes_series_id(self, area_code='0000000', industry_code='000000',
                            occupation_code='000000', data_type='01'):
        """Build an OES (Occupational Employment Statistics) series ID.

        data_type: 01=Employment, 03=Hourly mean wage, 04=Annual mean wage,
                   13=Annual median wage
        area_code: 0000000=National
        """
        return f'OEUS{area_code}{industry_code}{occupation_code}{data_type}'

    def get_occupational_exposure(self):
        """P3/P5: Employment and wage data for AI-vulnerable occupations.

        Fetches employment level + mean hourly wage for each target occupation.
        Cross-reference rising wages with declining employment to identify
        roles where agentic substitution delivers the highest ROI.
        """
        area_code = '0000000'
        industry_code = '000000'
        series_ids = []
        series_labels = {}

        for occ_code, occ_name in AI_VULNERABLE_OCCUPATIONS.items():
            emp_id = self.build_oes_series_id(
                area_code=area_code, industry_code=industry_code,
                occupation_code=occ_code, data_type='01')
            series_ids.append(emp_id)
            series_labels[emp_id] = f'{occ_name} -- Employment'

            wage_id = self.build_oes_series_id(
                area_code=area_code, industry_code=industry_code,
                occupation_code=occ_code, data_type='03')
            series_ids.append(wage_id)
            series_labels[wage_id] = f'{occ_name} -- Mean Hourly Wage'

        data = self._post(series_ids)
        results = {}
        for series in data.get('Results', {}).get('series', []):
            sid = series.get('seriesID', '')
            observations = []
            for obs in series.get('data', []):
                if obs.get('period') == 'M13':
                    continue
                observations.append({
                    'year': obs['year'],
                    'period': obs.get('period', ''),
                    'value': float(obs['value']) if obs['value'] != '-' else None,
                })
            results[sid] = {
                'series_id': sid,
                'title': series_labels.get(sid, sid),
                'observations': observations,
            }

        return {
            'signal_type': 'occupational_ai_exposure',
            'principle': 'P3,P5',
            'data': results,
            'interpretation': (
                'Occupations with high wages and large employment bases represent '
                'the biggest addressable markets for agentic disruption. Rising '
                'wages widen the cost advantage each year. Declining employment '
                'may indicate disruption already underway.'
            ),
        }

    def get_industry_wage_premium(self):
        """P3: Average hourly earnings by industry -- detect where wages grow fastest."""
        series = [
            'CES5500000003',  # Financial Activities
            'CES6054000003',  # Professional and Technical Services
            'CES6561000003',  # Educational Services
            'CES6562000003',  # Health Care
            'CES6500000003',  # Education and Health Services
        ]
        results = self.get_multiple_series(series)
        return {
            'signal_type': 'industry_wage_premium',
            'principle': 'P3',
            'data': results,
            'interpretation': (
                'Industries with highest and fastest-rising hourly earnings '
                'represent the largest cost-advantage opportunity for agentic '
                'businesses. Compare growth rates to prioritize where P3 moat widens fastest.'
            ),
        }

    def test_connection(self):
        """Verify BLS API access."""
        try:
            result = self.get_series('CES0000000001', start_year=datetime.now().year - 1)
            has_key = bool(self.api_key)
            latest = result['observations'][0] if result['observations'] else None
            return {
                'status': 'ok',
                'source': 'BLS',
                'authenticated': has_key,
                'rate_limit': '500/day' if has_key else '25/day',
                'test_series': 'Total Nonfarm Employment',
                'latest_value': latest,
            }
        except Exception as e:
            return {'status': 'error', 'source': 'BLS', 'error': str(e)}
