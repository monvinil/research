"""Google Trends connector — search interest as leading indicator.

NO API key needed (uses unofficial trends URL that returns JSON).

Purpose: Search interest is a LEADING indicator of economic activity.
When people search for "layoff" or "bankruptcy" or "AI replacement",
it shows up in search trends BEFORE it shows up in employment data.

Also useful for: competitive landscape validation (search volume for
competitor names), market sizing (search volume for service categories),
and geographic targeting (search interest by region).
"""

import requests
import json
import time

BASE_URL = 'https://trends.google.com/trends/api'


class GoogleTrendsConnector:
    """Pull search interest data from Google Trends."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
        })

    def _get_interest_over_time(self, keywords, timeframe='today 12-m', geo='US'):
        """Get search interest over time for keywords.

        Google Trends returns relative interest (0-100 scale).
        """
        url = f'{BASE_URL}/widgetdata/multiline'
        # Google Trends requires a token from the explore endpoint first
        explore_url = f'{BASE_URL}/explore'

        try:
            # Build comparison query
            comparison_item = []
            for kw in keywords[:5]:  # Max 5 keywords
                comparison_item.append({
                    'keyword': kw,
                    'geo': geo,
                    'time': timeframe,
                })

            params = {
                'hl': 'en-US',
                'tz': '240',
                'req': json.dumps({
                    'comparisonItem': comparison_item,
                    'category': 0,
                    'property': '',
                }),
            }

            r = self.session.get(explore_url, params=params, timeout=15)
            if r.status_code != 200:
                return {'error': f'explore failed: {r.status_code}'}

            # Parse the explore response (Google prepends ")]}',\n")
            text = r.text
            if text.startswith(")]}'"):
                text = text[5:]

            explore_data = json.loads(text)
            widgets = explore_data.get('widgets', [])

            # Find the interest over time widget
            timeline_widget = None
            for w in widgets:
                if w.get('id') == 'TIMESERIES':
                    timeline_widget = w
                    break

            if not timeline_widget:
                return {'error': 'no_timeline_widget'}

            # Fetch the actual data
            token = timeline_widget.get('token', '')
            req = timeline_widget.get('request', {})

            data_params = {
                'hl': 'en-US',
                'tz': '240',
                'req': json.dumps(req),
                'token': token,
            }

            r2 = self.session.get(url, params=data_params, timeout=15)
            if r2.status_code != 200:
                return {'error': f'data fetch failed: {r2.status_code}'}

            text2 = r2.text
            if text2.startswith(")]}'"):
                text2 = text2[5:]

            data = json.loads(text2)
            timeline = data.get('default', {}).get('timelineData', [])

            results = []
            for point in timeline:
                time_str = point.get('formattedTime', '')
                values = point.get('value', [])
                results.append({
                    'date': time_str,
                    'values': {keywords[i]: values[i] for i in range(min(len(keywords), len(values)))},
                })

            return {
                'signal_type': 'search_interest',
                'keywords': keywords,
                'geo': geo,
                'timeframe': timeframe,
                'data': results,
            }

        except Exception as e:
            return {'error': str(e)}

    def get_distress_signals(self, geo='US'):
        """Search interest for distress-related terms.

        Rising search interest for layoffs, bankruptcy, debt relief
        is a leading indicator of economic distress.
        """
        keywords = ['layoff', 'bankruptcy', 'debt relief', 'unemployment benefits']
        result = self._get_interest_over_time(keywords, geo=geo)
        result['principle'] = 'P2'
        result['interpretation'] = (
            'Rising distress search interest leads actual economic data by '
            '2-4 weeks. Spikes in "layoff" searches precede BLS job loss data. '
            '"bankruptcy" search interest precedes court filing data.'
        )
        return result

    def get_ai_adoption_interest(self, geo='US'):
        """Search interest for AI tools and services by category."""
        keywords = ['AI assistant', 'ChatGPT for business', 'automate my job']
        result = self._get_interest_over_time(keywords, geo=geo)
        result['principle'] = 'P1'
        result['interpretation'] = (
            'Rising "automate my job" searches indicate workers sensing '
            'displacement. Rising "AI assistant" and business AI searches '
            'indicate employer adoption. The gap between the two is '
            'the P7 timing arbitrage window.'
        )
        return result

    def get_sector_interest(self, sector_keywords, geo='US'):
        """Search interest for specific sector services.

        Use to validate market size and demand trends.
        """
        result = self._get_interest_over_time(sector_keywords, geo=geo)
        result['principle'] = 'market_validation'
        return result

    def get_geographic_interest(self, keyword, regions=None):
        """Compare search interest across geographies.

        Reveals where demand is strongest for a given service.
        """
        if regions is None:
            regions = ['US', 'GB', 'DE', 'IN', 'BR']

        results = {}
        for geo in regions:
            time.sleep(0.5)  # Rate limiting
            results[geo] = self._get_interest_over_time([keyword], geo=geo)

        return {
            'signal_type': 'geographic_interest',
            'keyword': keyword,
            'data': results,
            'interpretation': (
                'Higher relative interest = higher demand in that geography. '
                'Cross-reference with World Bank labor costs to find where '
                'demand is high but delivery cost is low.'
            ),
        }

    def test_connection(self):
        """Verify Google Trends access."""
        try:
            result = self._get_interest_over_time(['test'], timeframe='now 7-d')
            if 'error' in result:
                return {'status': 'error', 'source': 'Google Trends', 'error': result['error']}
            return {
                'status': 'ok',
                'source': 'Google Trends',
                'test': f'Data points: {len(result.get("data", []))}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'Google Trends', 'error': str(e)}
