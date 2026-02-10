"""BEA (Bureau of Economic Analysis) connector.

GDP by industry, input-output propagation tables, regional GDP,
international services trade. Essential for understanding HOW
disruption propagates across sectors and geographies.

API docs: https://apps.bea.gov/api/
Free key: https://apps.bea.gov/api/signup/
"""

import requests
from .config import BEA_API_KEY

BASE_URL = 'https://apps.bea.gov/api/data'


class BEAConnector:
    """Pull GDP-by-industry, input-output tables, services trade, regional GDP."""

    def __init__(self, api_key=None):
        self.api_key = api_key or BEA_API_KEY
        if not self.api_key:
            raise ValueError(
                'BEA API key required. Get free key at: '
                'https://apps.bea.gov/api/signup/\n'
                'Then set BEA_API_KEY in .env'
            )

    def _get(self, params):
        params['UserID'] = self.api_key
        params['ResultFormat'] = 'JSON'
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_gdp_by_industry(self, year='2024', quarter='Q1Q2Q3Q4',
                             industry='ALL', frequency='Q'):
        """GDP by industry — detect REAL output changes, not just employment.

        This is critical: employment can decline while output rises (productivity),
        or employment can be stable while output collapses (zombie firms).
        GDP-by-industry separates these cases.
        """
        try:
            data = self._get({
                'DataSetName': 'GDPByIndustry',
                'Method': 'GetData',
                'Year': year,
                'Quarter': quarter,
                'Industry': industry,
                'Frequency': frequency,
                'TableID': '1',
            })
            results = data.get('BEAAPI', {}).get('Results', {})
            rows = results.get('Data', results.get('data', []))

            industries = {}
            for row in rows:
                ind = row.get('Industry', '')
                desc = row.get('IndustrYDescription', row.get('IndustryDescription', ''))
                val = row.get('DataValue', '')
                yr = row.get('Year', '')
                qtr = row.get('Quarter', '')

                if ind not in industries:
                    industries[ind] = {
                        'description': desc,
                        'observations': [],
                    }
                industries[ind]['observations'].append({
                    'year': yr, 'quarter': qtr, 'value': val
                })

            return {
                'signal_type': 'gdp_by_industry',
                'principle': 'P2',
                'data': industries,
                'interpretation': (
                    'Industries with declining real GDP contribution are in '
                    'structural contraction — not cyclical. Cross-reference with '
                    'BLS employment to separate output decline from productivity gain.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'gdp_by_industry', 'error': str(e)}

    def get_input_output_requirements(self, year='2022', table_id='56'):
        """Get input-output Use tables — trace disruption propagation.

        Table 56: Use of Commodities by Industry (After Redefinitions)
        Shows which industries buy from which other industries.
        If professional services collapses, this shows downstream effects.
        """
        try:
            data = self._get({
                'DataSetName': 'InputOutput',
                'Method': 'GetData',
                'TableID': table_id,
                'Year': year,
            })
            results = data.get('BEAAPI', {}).get('Results', {})
            rows = results.get('Data', results.get('data', []))
            return {
                'signal_type': 'input_output_propagation',
                'principle': 'P2',
                'data': rows[:500],
                'row_count': len(rows),
                'interpretation': (
                    'Input-output tables show how disruption propagates. '
                    'If legal services output drops 20%, which industries '
                    'that depend on legal services are affected? This identifies '
                    'second-order opportunity chains.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'input_output_propagation', 'error': str(e)}

    def get_international_services_trade(self, type_of_service='ALL',
                                          trade_direction='ALL',
                                          year='2024',
                                          affiliation='ALL'):
        """International trade in services — where is outsourcing accelerating?

        Detects: which services are being exported/imported more,
        indicating cross-border arbitrage opportunities.
        """
        try:
            data = self._get({
                'DataSetName': 'IntlServTrade',
                'Method': 'GetData',
                'TypeOfService': type_of_service,
                'TradeDirection': trade_direction,
                'Year': year,
                'Affiliation': affiliation,
                'AreaOrCountry': 'ALL',
            })
            results = data.get('BEAAPI', {}).get('Results', {})
            rows = results.get('Data', results.get('data', []))
            return {
                'signal_type': 'services_trade',
                'principle': 'P3,geographic_arbitrage',
                'data': rows[:200],
                'row_count': len(rows),
                'interpretation': (
                    'Rising services imports = outsourcing accelerating. '
                    'Rising services exports in specific categories = US has '
                    'competitive advantage. Cross-border service flows reveal '
                    'where geographic arbitrage works.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'services_trade', 'error': str(e)}

    def get_regional_gdp(self, geo_fips='STATE', year='2023',
                          table_name='SAGDP2N'):
        """Regional GDP by state — identify geographic concentration of distress."""
        try:
            data = self._get({
                'DataSetName': 'Regional',
                'Method': 'GetData',
                'TableName': table_name,
                'GeoFips': geo_fips,
                'Year': year,
                'LineCode': '1',
            })
            results = data.get('BEAAPI', {}).get('Results', {})
            rows = results.get('Data', results.get('data', []))
            return {
                'signal_type': 'regional_gdp',
                'principle': 'P2,geographic',
                'data': rows[:200],
                'row_count': len(rows),
                'interpretation': (
                    'States/regions with declining GDP in specific industries '
                    'are geographic concentration points for distressed assets. '
                    'Cross-reference with business application data to find '
                    'where new formation outpaces the decline.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'regional_gdp', 'error': str(e)}

    def get_personal_income_by_industry(self, geo_fips='US', year='2023',
                                         table_name='SA6N'):
        """Personal income by industry — more granular compensation trends."""
        try:
            data = self._get({
                'DataSetName': 'Regional',
                'Method': 'GetData',
                'TableName': table_name,
                'GeoFips': geo_fips,
                'Year': year,
                'LineCode': '1',
            })
            results = data.get('BEAAPI', {}).get('Results', {})
            rows = results.get('Data', results.get('data', []))
            return {
                'signal_type': 'personal_income_by_industry',
                'principle': 'P3',
                'data': rows[:200],
                'row_count': len(rows),
            }
        except Exception as e:
            return {'signal_type': 'personal_income_by_industry', 'error': str(e)}

    def test_connection(self):
        """Verify BEA API access."""
        try:
            data = self._get({
                'DataSetName': 'GDPByIndustry',
                'Method': 'GetParameterValues',
                'ParameterName': 'Year',
            })
            return {
                'status': 'ok',
                'source': 'BEA',
                'test': 'GetParameterValues for GDPByIndustry years',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'BEA', 'error': str(e)}
