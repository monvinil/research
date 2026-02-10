"""Census Bureau connector.

Business Dynamics Statistics, County Business Patterns,
Construction Spending, Annual Business Survey.

Essential for: firm birth/death rates by industry and geography,
establishment counts by NAICS code, construction activity.

API docs: https://www.census.gov/data/developers.html
Free key: https://api.census.gov/data/key_signup.html
"""

import requests
from .config import CENSUS_API_KEY

BASE_URL = 'https://api.census.gov/data'


class CensusConnector:
    """Pull business demographics, construction, and establishment data."""

    def __init__(self, api_key=None):
        self.api_key = api_key or CENSUS_API_KEY
        if not self.api_key:
            raise ValueError(
                'Census API key required. Get free key at: '
                'https://api.census.gov/data/key_signup.html\n'
                'Then set CENSUS_API_KEY in .env'
            )

    def _get(self, endpoint, params=None):
        params = params or {}
        params['key'] = self.api_key
        r = requests.get(f'{BASE_URL}/{endpoint}', params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_business_dynamics(self, year='2021', measure='firmdeath_firms'):
        """Business Dynamics Statistics — firm birth/death rates by industry.

        This is THE dataset for detecting liquidation cascades at the firm level.
        Variables: firm births, firm deaths, job creation, job destruction,
        establishment entry/exit, net job creation rate.

        Available by NAICS 2-digit sector.
        """
        try:
            data = self._get(
                f'{year}/bds/firms',
                params={
                    'get': 'firmdeath_firms,firmbirth_firms,firms,net_job_creation_rate,sector',
                    'for': 'us:*',
                }
            )
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            results = []
            for row in rows:
                entry = dict(zip(headers, row))
                results.append(entry)

            return {
                'signal_type': 'business_dynamics',
                'principle': 'P2,P4',
                'data': results,
                'year': year,
                'interpretation': (
                    'Industries with firm deaths > firm births are in net contraction. '
                    'Cross-reference with net_job_creation_rate: negative rate + high '
                    'death rate = liquidation cascade in progress. High birth rate = '
                    'new entrants sensing opportunity.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'business_dynamics', 'error': str(e), 'year': year}

    def get_county_business_patterns(self, year='2022', naics='54',
                                      geography='state:*'):
        """County Business Patterns — establishment counts by industry and geography.

        NAICS 54 = Professional Services, 62 = Healthcare, 23 = Construction
        Get number of establishments, employment, payroll by state/county.
        Essential for market sizing and geographic targeting.
        """
        try:
            data = self._get(
                f'{year}/cbp',
                params={
                    'get': 'ESTAB,EMP,PAYANN,NAICS2017',
                    'for': geography,
                    'NAICS2017': naics,
                }
            )
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            results = []
            for row in rows:
                entry = dict(zip(headers, row))
                results.append(entry)

            return {
                'signal_type': 'county_business_patterns',
                'principle': 'P2',
                'data': results,
                'year': year,
                'naics': naics,
                'interpretation': (
                    'Establishment counts and payroll by geography reveal market '
                    'size and concentration. Declining establishment counts in a '
                    'NAICS code = consolidation or exit. Rising payroll per establishment '
                    '= fewer firms paying more per worker (squeeze).'
                ),
            }
        except Exception as e:
            return {'signal_type': 'county_business_patterns', 'error': str(e)}

    def get_construction_spending(self, year='2024', category='TOTAL'):
        """Construction spending — monthly, by category.

        Relevant for construction sector analysis and infrastructure spending.
        """
        try:
            data = self._get(
                f'{year}/vip',
                params={
                    'get': 'cell_value,time_slot_name,category_code',
                    'for': 'us:*',
                    'category_code': category,
                }
            )
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            results = []
            for row in rows:
                entry = dict(zip(headers, row))
                results.append(entry)

            return {
                'signal_type': 'construction_spending',
                'principle': 'P5',
                'data': results,
                'year': year,
            }
        except Exception as e:
            return {'signal_type': 'construction_spending', 'error': str(e)}

    def get_annual_business_survey(self, year='2021', naics='54'):
        """Annual Business Survey — technology adoption, innovation, R&D by industry.

        Includes questions on AI adoption, cloud computing, robotics.
        Essential for understanding technology readiness by sector.
        """
        try:
            data = self._get(
                f'{year}/abscs',
                params={
                    'get': 'FIRMPDEMP,RCPPDEMP,NAICS2017,NAICS2017_LABEL',
                    'for': 'us:*',
                    'NAICS2017': naics,
                }
            )
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            results = []
            for row in rows:
                entry = dict(zip(headers, row))
                results.append(entry)

            return {
                'signal_type': 'annual_business_survey',
                'principle': 'P1,P2',
                'data': results,
                'year': year,
            }
        except Exception as e:
            return {'signal_type': 'annual_business_survey', 'error': str(e)}

    def get_nonemployer_statistics(self, year='2021', naics='54'):
        """Nonemployer Statistics — solo businesses by industry.

        Rising nonemployer count in a NAICS = more solo operators.
        Could indicate: gig economy growth, AI-enabled solo practitioners,
        or industry fragmentation.
        """
        try:
            data = self._get(
                f'{year}/nonemp',
                params={
                    'get': 'NESTAB,RCPTOT,NAICS2017,NAICS2017_LABEL',
                    'for': 'us:*',
                    'NAICS2017': naics,
                }
            )
            headers = data[0] if data else []
            rows = data[1:] if len(data) > 1 else []

            results = []
            for row in rows:
                entry = dict(zip(headers, row))
                results.append(entry)

            return {
                'signal_type': 'nonemployer_statistics',
                'principle': 'P4',
                'data': results,
                'year': year,
                'interpretation': (
                    'Rising nonemployer establishments = more solo operators. '
                    'In professional services, this may indicate AI-enabled '
                    'solo practitioners competing with traditional firms. '
                    'Cross-reference with firm death rates.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'nonemployer_statistics', 'error': str(e)}

    def test_connection(self):
        """Verify Census API access."""
        try:
            data = self._get('2022/cbp', params={
                'get': 'ESTAB',
                'for': 'us:*',
                'NAICS2017': '54',
            })
            return {
                'status': 'ok',
                'source': 'Census',
                'test': f'Professional services establishments: {data[1][0] if len(data) > 1 else "N/A"}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'Census', 'error': str(e)}
