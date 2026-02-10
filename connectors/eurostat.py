"""Eurostat connector — EU-specific economic data. NO API key needed.

Covers: labor costs by NACE sector, digital economy indicators,
services trade, business demography, structural business statistics.

Purpose: EU is the closest comparable to US in services economy maturity.
EU labor markets are MORE regulated (harder to fire → more Baumol stored energy
but slower adoption). Digital Economy and Society Index (DESI) shows
which EU countries are most AI-ready.

API docs: https://ec.europa.eu/eurostat/web/main/data/database
JSON API: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/
"""

import requests

BASE_URL = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data'

# Key EU economies for comparison
TARGET_COUNTRIES = ['DE', 'FR', 'NL', 'SE', 'IE', 'EE', 'PL', 'ES', 'IT', 'DK']

# Dataset codes mapped to analytical purpose
DATASETS = {
    # Labor costs
    'lc_lci_r2_q': 'Labour Cost Index by NACE sector (quarterly)',
    'earn_ses18_46': 'Hourly earnings by NACE section',

    # Business demography
    'bd_9bd_sz_cl_r2': 'Business demography by size class',

    # Digital economy
    'isoc_eb_ai': 'Enterprises using AI technologies',
    'isoc_eb_ict': 'ICT specialists in employment',

    # Services trade
    'bop_its6_det': 'International trade in services, detailed',

    # Structural business statistics
    'sbs_na_1a_se_r2': 'Annual enterprise statistics for services',
}


class EurostatConnector:
    """Pull EU economic data from Eurostat."""

    def __init__(self):
        pass  # No API key needed

    def _get(self, dataset, params=None):
        url = f'{BASE_URL}/{dataset}'
        default_params = {
            'format': 'JSON',
            'lang': 'en',
        }
        if params:
            default_params.update(params)

        r = requests.get(url, params=default_params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _parse_eurostat_json(self, data):
        """Parse Eurostat JSON-stat format into readable structure."""
        dimensions = data.get('dimension', {})
        values = data.get('value', {})

        # Get dimension sizes and labels
        dim_info = {}
        dim_order = data.get('id', [])
        dim_sizes = data.get('size', [])

        for i, dim_id in enumerate(dim_order):
            dim = dimensions.get(dim_id, {})
            categories = dim.get('category', {})
            labels = categories.get('label', {})
            index = categories.get('index', {})
            dim_info[dim_id] = {
                'labels': labels,
                'index': index,
                'size': dim_sizes[i] if i < len(dim_sizes) else 0,
            }

        # Convert flat index to records
        records = []
        for flat_idx, value in values.items():
            idx = int(flat_idx)
            record = {'value': value}

            # Decode flat index to dimension positions
            remaining = idx
            for dim_id in reversed(dim_order):
                size = dim_info[dim_id]['size']
                if size > 0:
                    pos = remaining % size
                    remaining //= size

                    # Find label for this position
                    index_map = dim_info[dim_id]['index']
                    for code, position in index_map.items():
                        if position == pos:
                            label = dim_info[dim_id]['labels'].get(code, code)
                            record[dim_id] = code
                            record[f'{dim_id}_label'] = label
                            break

            records.append(record)

        return records

    def get_labor_cost_index(self, countries=None):
        """Labour Cost Index by NACE sector — quarterly.

        Directly comparable to US ECI. Rising LCI in services
        sectors confirms Baumol cost disease in EU.
        """
        if countries is None:
            countries = TARGET_COUNTRIES[:6]

        geo_filter = '+'.join(countries)
        try:
            data = self._get('lc_lci_r2_q', params={
                'geo': geo_filter,
                's_adj': 'SCA',  # Seasonally/calendar adjusted
                'nace_r2': 'B-S',  # All NACE sectors
                'lcstruct': 'D1_D4_MD5',  # Total labor cost
                'sinceTimePeriod': '2020-Q1',
            })
            records = self._parse_eurostat_json(data)
            return {
                'signal_type': 'eu_labor_cost_index',
                'principle': 'P2,P3',
                'data': records[:200],
                'record_count': len(records),
                'interpretation': (
                    'EU Labour Cost Index rising in services = Baumol stored energy '
                    'building in EU. Compare with US ECI to see if pressure is '
                    'higher/lower in EU. Higher EU labor rigidity means MORE stored '
                    'energy but SLOWER release.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'eu_labor_cost_index', 'error': str(e)}

    def get_ai_adoption(self, countries=None):
        """Enterprise AI adoption by country — how far ahead/behind is EU?"""
        if countries is None:
            countries = TARGET_COUNTRIES

        geo_filter = '+'.join(countries)
        try:
            data = self._get('isoc_eb_ai', params={
                'geo': geo_filter,
                'sinceTimePeriod': '2020',
            })
            records = self._parse_eurostat_json(data)
            return {
                'signal_type': 'eu_ai_adoption',
                'principle': 'P1',
                'data': records[:200],
                'record_count': len(records),
                'interpretation': (
                    'EU AI adoption rate by country shows where the market is '
                    'most receptive. Higher adoption = more demand for AI services '
                    'but also more competition. Lower adoption = greenfield but '
                    'may indicate regulatory or cultural barriers.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'eu_ai_adoption', 'error': str(e)}

    def get_services_trade(self, countries=None):
        """International trade in services — EU cross-border flows."""
        if countries is None:
            countries = TARGET_COUNTRIES[:6]

        geo_filter = '+'.join(countries)
        try:
            data = self._get('bop_its6_det', params={
                'geo': geo_filter,
                'bop_item': 'SI',  # Services
                'stk_flow': 'BAL',  # Balance
                'partner': 'WRL_REST',  # World
                'sinceTimePeriod': '2020',
            })
            records = self._parse_eurostat_json(data)
            return {
                'signal_type': 'eu_services_trade',
                'principle': 'P3,geographic_arbitrage',
                'data': records[:200],
                'record_count': len(records),
                'interpretation': (
                    'EU services trade balance shows which countries are net '
                    'exporters (competitive) vs importers (vulnerable). Net '
                    'importers with high labor costs = prime nearshoring targets.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'eu_services_trade', 'error': str(e)}

    def get_business_demography(self, countries=None):
        """Business births and deaths by size class — EU firm dynamics."""
        if countries is None:
            countries = TARGET_COUNTRIES[:6]

        geo_filter = '+'.join(countries)
        try:
            data = self._get('bd_9bd_sz_cl_r2', params={
                'geo': geo_filter,
                'nace_r2': 'B-S_X_K642',  # Business economy
                'indic_sb': 'V97050+V97051',  # Birth/death rates
                'sinceTimePeriod': '2018',
            })
            records = self._parse_eurostat_json(data)
            return {
                'signal_type': 'eu_business_demography',
                'principle': 'P2,P4',
                'data': records[:200],
                'record_count': len(records),
                'interpretation': (
                    'EU firm birth/death rates compared to US Census BDS. '
                    'Higher death rate in services = liquidation cascade '
                    'hitting EU. Compare with US rates to see if EU is '
                    'ahead or behind in the disruption cycle.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'eu_business_demography', 'error': str(e)}

    def get_full_scan(self):
        """Run all Eurostat analyses."""
        return {
            'labor_costs': self.get_labor_cost_index(),
            'ai_adoption': self.get_ai_adoption(),
            'services_trade': self.get_services_trade(),
            'business_demography': self.get_business_demography(),
        }

    def test_connection(self):
        """Verify Eurostat API access."""
        try:
            data = self._get('lc_lci_r2_q', params={
                'geo': 'DE',
                's_adj': 'SCA',
                'nace_r2': 'B-S',
                'lcstruct': 'D1_D4_MD5',
                'sinceTimePeriod': '2024-Q1',
            })
            count = len(data.get('value', {}))
            return {
                'status': 'ok',
                'source': 'Eurostat',
                'test': f'Germany LCI data points: {count}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'Eurostat', 'error': str(e)}
