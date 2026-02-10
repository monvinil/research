"""OECD Statistics connector.

Composite Leading Indicators, labor statistics, technology adoption,
R&D spending by industry. NO API key needed.

Purpose: Leading indicators that predict turning points.
OECD CLI is one of the best recession/expansion early warning systems.
Technology adoption data shows where AI deployment is ahead/behind.

API: https://data-explorer.oecd.org/
"""

import requests

# OECD SDMX REST API
BASE_URL = 'https://sdmx.oecd.org/public/rest/data'

TARGET_COUNTRIES = ['USA', 'GBR', 'DEU', 'JPN', 'KOR', 'ISR',
                     'IND', 'BRA', 'MEX', 'IDN', 'POL', 'EST',
                     'SGP', 'ARE']


class OECDConnector:
    """Pull leading indicators, labor, and technology data from OECD."""

    def __init__(self):
        pass  # No API key needed

    def _get_json(self, dataset, filter_expr, params=None):
        """Fetch OECD data in JSON format."""
        url = f'{BASE_URL}/OECD.SDD.STES,DSD_{dataset}@DF_{dataset}/{filter_expr}'
        headers = {'Accept': 'application/vnd.sdmx.data+json; charset=utf-8; version=2'}
        default_params = {'dimensionAtObservation': 'TIME_PERIOD', 'detail': 'dataonly'}
        if params:
            default_params.update(params)

        try:
            r = requests.get(url, headers=headers, params=default_params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            # Try alternative agency paths
            for agency in ['OECD.SDD.STES', 'OECD.SDD.NAD', 'OECD.STI.MON', 'OECD']:
                try:
                    alt_url = f'{BASE_URL}/{agency},DSD_{dataset}@DF_{dataset}/{filter_expr}'
                    r = requests.get(alt_url, headers=headers, params=default_params, timeout=30)
                    if r.status_code == 200:
                        return r.json()
                except Exception:
                    continue
            return None

    def _parse_sdmx_json(self, data):
        """Parse SDMX-JSON response into simple dict format."""
        if not data:
            return []

        results = []
        try:
            datasets = data.get('data', {}).get('dataSets', [])
            structure = data.get('data', {}).get('structures', [{}])[0]
            dims = structure.get('dimensions', {}).get('observation', [])
            series_dims = structure.get('dimensions', {}).get('series', [])

            for ds in datasets:
                for series_key, series_data in ds.get('series', {}).items():
                    # Decode series dimensions
                    series_parts = series_key.split(':')
                    series_labels = {}
                    for i, part in enumerate(series_parts):
                        if i < len(series_dims):
                            dim = series_dims[i]
                            values = dim.get('values', [])
                            idx = int(part) if part.isdigit() else 0
                            if idx < len(values):
                                series_labels[dim.get('id', '')] = values[idx].get('name', values[idx].get('id', ''))

                    # Decode observations
                    for obs_key, obs_val in series_data.get('observations', {}).items():
                        time_idx = int(obs_key) if obs_key.isdigit() else 0
                        time_val = ''
                        if dims and time_idx < len(dims[0].get('values', [])):
                            time_val = dims[0]['values'][time_idx].get('id', '')

                        results.append({
                            **series_labels,
                            'time': time_val,
                            'value': obs_val[0] if obs_val else None,
                        })
        except Exception:
            pass

        return results

    def get_composite_leading_indicators(self, countries=None):
        """OECD Composite Leading Indicators — detect turning points.

        CLI > 100 = expansion, CLI < 100 = contraction.
        Rate of change predicts turning points 6-9 months ahead.
        """
        if countries is None:
            countries = '+'.join(TARGET_COUNTRIES[:8])
        elif isinstance(countries, list):
            countries = '+'.join(countries)

        try:
            filter_expr = f'{countries}.M.LI.LOLITOAA..'
            data = self._get_json('MEI_CLI', filter_expr)
            results = self._parse_sdmx_json(data)

            return {
                'signal_type': 'composite_leading_indicators',
                'principle': 'P2,capital_modeling',
                'data': results[-100:],
                'interpretation': (
                    'CLI above 100 = expansion, below 100 = contraction. '
                    'Turning points in CLI lead GDP by 6-9 months. '
                    'Countries where CLI is rolling over are entering '
                    'the window where distressed assets become available.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'composite_leading_indicators', 'error': str(e)}

    def get_labor_statistics(self, countries=None):
        """Short-term labor market stats — unemployment, employment by sector."""
        if countries is None:
            countries = '+'.join(TARGET_COUNTRIES[:8])

        try:
            filter_expr = f'{countries}.M.UNR...'
            data = self._get_json('MEI_LABOUR', filter_expr)
            results = self._parse_sdmx_json(data)

            return {
                'signal_type': 'oecd_labor_statistics',
                'principle': 'P2,P5',
                'data': results[-100:],
                'interpretation': (
                    'Cross-country unemployment trends reveal where labor '
                    'markets are tightest (opportunity for AI substitution) '
                    'vs loosest (available workforce for hybrid models).'
                ),
            }
        except Exception as e:
            return {'signal_type': 'oecd_labor_statistics', 'error': str(e)}

    def get_technology_indicators(self, countries=None):
        """Main Science & Technology Indicators — R&D, researchers, patents."""
        if countries is None:
            countries = '+'.join(TARGET_COUNTRIES[:8])

        try:
            filter_expr = f'{countries}..GERD_GDP..'
            data = self._get_json('MSTI_PUB', filter_expr)
            results = self._parse_sdmx_json(data)

            return {
                'signal_type': 'oecd_technology_indicators',
                'principle': 'P1',
                'data': results[-50:],
                'interpretation': (
                    'Countries with highest R&D/GDP ratio have the deepest '
                    'technology infrastructure. Cross-reference with business '
                    'environment data: high R&D + low friction = fastest AI adoption.'
                ),
            }
        except Exception as e:
            return {'signal_type': 'oecd_technology_indicators', 'error': str(e)}

    def get_full_scan(self):
        """Run all OECD analyses."""
        return {
            'leading_indicators': self.get_composite_leading_indicators(),
            'labor': self.get_labor_statistics(),
            'technology': self.get_technology_indicators(),
        }

    def test_connection(self):
        """Verify OECD API access."""
        try:
            result = self.get_composite_leading_indicators(countries='USA')
            count = len(result.get('data', []))
            return {
                'status': 'ok',
                'source': 'OECD',
                'test': f'US CLI data points: {count}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'OECD', 'error': str(e)}
