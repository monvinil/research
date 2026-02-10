"""World Bank Open Data connector.

International comparative data — NO API key needed.
Provides cross-country comparison of business environment,
labor markets, services trade, and technology adoption.

Purpose: Confirm or challenge US-centric analytical biases.
Markets with less regulatory friction and lower labor costs
may show disruption patterns earlier or differently.

API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import requests

BASE_URL = 'https://api.worldbank.org/v2'

# Target countries for comparative analysis
TARGET_COUNTRIES = {
    'US': 'United States',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'JP': 'Japan',
    'KR': 'South Korea',
    'SG': 'Singapore',
    'AE': 'United Arab Emirates',
    'IL': 'Israel',
    'IN': 'India',
    'BR': 'Brazil',
    'AR': 'Argentina',
    'MX': 'Mexico',
    'ID': 'Indonesia',
    'VN': 'Vietnam',
    'PL': 'Poland',
    'EE': 'Estonia',
}

# Indicators organized by analytical purpose
INDICATORS = {
    # Business environment friction
    'IC.REG.DURS': 'Time to start a business (days)',
    'IC.REG.COST.PC.ZS': 'Cost to start a business (% GNI per capita)',
    'IC.TAX.TOTL.CP.ZS': 'Total tax & contribution rate (% of profit)',

    # Labor market structure
    'SL.TLF.CACT.ZS': 'Labor force participation rate (%)',
    'SL.UEM.TOTL.ZS': 'Unemployment rate (%)',
    'SL.TLF.TOTL.IN': 'Total labor force',
    'SL.SRV.EMPL.ZS': 'Employment in services (% of total)',

    # Economic structure
    'NY.GDP.MKTP.KD.ZG': 'GDP growth (%)',
    'NY.GDP.PCAP.PP.KD': 'GDP per capita, PPP (constant 2017 $)',
    'NV.SRV.TOTL.ZS': 'Services value added (% of GDP)',
    'NV.IND.TOTL.ZS': 'Industry value added (% of GDP)',

    # Services trade (cross-border arbitrage signals)
    'BX.GSR.NFSV.CD': 'Service exports (current US$)',
    'BM.GSR.NFSV.CD': 'Service imports (current US$)',

    # Technology readiness
    'GB.XPD.RSDV.GD.ZS': 'R&D expenditure (% of GDP)',
    'IT.NET.BBND.P2': 'Fixed broadband per 100 people',
    'IT.NET.USER.ZS': 'Internet users (% of population)',

    # Financial system
    'FS.AST.PRVT.GD.ZS': 'Domestic credit to private sector (% of GDP)',
    'CM.MKT.LCAP.GD.ZS': 'Market capitalization (% of GDP)',
}


class WorldBankConnector:
    """Pull international comparative data from World Bank."""

    def __init__(self):
        pass  # No API key needed

    def _get(self, endpoint, params=None):
        params = params or {}
        params['format'] = 'json'
        params['per_page'] = 500
        r = requests.get(f'{BASE_URL}/{endpoint}', params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        # World Bank returns [metadata, data] array
        if isinstance(data, list) and len(data) > 1:
            return data[1] or []
        return []

    def get_indicator(self, indicator, countries=None, date_range='2018:2024'):
        """Get a single indicator for target countries."""
        if countries is None:
            countries = ';'.join(TARGET_COUNTRIES.keys())
        elif isinstance(countries, list):
            countries = ';'.join(countries)

        data = self._get(
            f'country/{countries}/indicator/{indicator}',
            params={'date': date_range}
        )

        results = {}
        for entry in data:
            if not entry:
                continue
            country = entry.get('country', {}).get('id', '')
            country_name = entry.get('country', {}).get('value', '')
            year = entry.get('date', '')
            value = entry.get('value')

            if country not in results:
                results[country] = {
                    'country': country_name,
                    'observations': []
                }
            results[country]['observations'].append({
                'year': year,
                'value': value
            })

        return {
            'indicator': indicator,
            'description': INDICATORS.get(indicator, indicator),
            'data': results,
        }

    def get_business_environment_comparison(self):
        """Compare business formation friction across target markets.

        Less friction = faster AI adoption potential.
        """
        indicators = [
            'IC.REG.DURS', 'IC.REG.COST.PC.ZS', 'IC.TAX.TOTL.CP.ZS'
        ]
        results = {}
        for ind in indicators:
            try:
                results[ind] = self.get_indicator(ind)
            except Exception as e:
                results[ind] = {'error': str(e)}

        return {
            'signal_type': 'international_business_environment',
            'principle': 'geographic_arbitrage',
            'data': results,
            'interpretation': (
                'Countries with fastest business formation + lowest tax burden '
                'are where AI-native entrants face least friction. Compare with '
                'services trade data to find markets where AI businesses can '
                'serve US/EU clients from lower-friction jurisdictions.'
            ),
        }

    def get_labor_market_comparison(self):
        """Compare labor market structures — where is Baumol stored energy highest?"""
        indicators = [
            'SL.TLF.CACT.ZS', 'SL.UEM.TOTL.ZS', 'SL.SRV.EMPL.ZS',
            'NY.GDP.PCAP.PP.KD'
        ]
        results = {}
        for ind in indicators:
            try:
                results[ind] = self.get_indicator(ind)
            except Exception as e:
                results[ind] = {'error': str(e)}

        return {
            'signal_type': 'international_labor_markets',
            'principle': 'P3,P5',
            'data': results,
            'interpretation': (
                'High GDP per capita + high services employment % = maximum '
                'Baumol stored energy. These markets have the most to gain '
                'from AI cost structure collapse. Low GDP per capita markets '
                'have less stored energy but also less competitive density.'
            ),
        }

    def get_services_trade_flows(self):
        """Services trade — where is cross-border outsourcing accelerating?"""
        indicators = ['BX.GSR.NFSV.CD', 'BM.GSR.NFSV.CD', 'NV.SRV.TOTL.ZS']
        results = {}
        for ind in indicators:
            try:
                results[ind] = self.get_indicator(ind)
            except Exception as e:
                results[ind] = {'error': str(e)}

        return {
            'signal_type': 'international_services_trade',
            'principle': 'P3,geographic_arbitrage',
            'data': results,
            'interpretation': (
                'Countries with rapidly growing service exports (India, Poland, '
                'Philippines) are already capturing cross-border arbitrage. '
                'Rising US service imports = growing demand for cheaper delivery. '
                'AI augmentation of offshore professionals amplifies this trend.'
            ),
        }

    def get_technology_readiness(self):
        """Technology infrastructure — where can AI deploy fastest?"""
        indicators = [
            'GB.XPD.RSDV.GD.ZS', 'IT.NET.BBND.P2', 'IT.NET.USER.ZS'
        ]
        results = {}
        for ind in indicators:
            try:
                results[ind] = self.get_indicator(ind)
            except Exception as e:
                results[ind] = {'error': str(e)}

        return {
            'signal_type': 'international_tech_readiness',
            'principle': 'P1',
            'data': results,
            'interpretation': (
                'High R&D spending + high broadband penetration = AI-ready '
                'infrastructure. Markets with high tech readiness but low '
                'competitive density are prime for leapfrog disruption.'
            ),
        }

    def get_full_comparative_scan(self):
        """Run all comparative analyses."""
        return {
            'business_environment': self.get_business_environment_comparison(),
            'labor_markets': self.get_labor_market_comparison(),
            'services_trade': self.get_services_trade_flows(),
            'tech_readiness': self.get_technology_readiness(),
        }

    def test_connection(self):
        """Verify World Bank API access."""
        try:
            data = self.get_indicator('NY.GDP.MKTP.KD.ZG', countries='US',
                                       date_range='2023:2024')
            return {
                'status': 'ok',
                'source': 'World Bank',
                'test': f'US GDP growth data points: {len(data.get("data", {}).get("US", {}).get("observations", []))}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'World Bank', 'error': str(e)}
