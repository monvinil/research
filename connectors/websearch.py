"""Web search connector — DuckDuckGo (free) + Serper (paid, optional).

This is Agent A's general scanning backbone. All source categories
except structured financial data flow through web search.

DuckDuckGo: Free, no key, good for general queries. Rate limits apply.
Serper: $50/mo, higher volume/reliability, structured results.

The connector auto-selects: uses Serper if key is available, falls back
to DuckDuckGo.
"""

import requests
from datetime import datetime
from .config import SERPER_API_KEY

HAS_DDGS = False
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    pass

# DuckDuckGo HTML-based fallback (no TLS issues, no package needed)
DDG_HTML_URL = 'https://html.duckduckgo.com/html/'


class WebSearchConnector:
    """Web search with automatic backend selection.

    Priority: Serper (paid) > DDGS package > DuckDuckGo HTML scrape (always works)
    """

    def __init__(self, serper_key=None):
        self.serper_key = serper_key or SERPER_API_KEY
        self.use_serper = bool(self.serper_key)

    def search(self, query, num_results=10, time_range=None):
        """Search the web.

        Args:
            query: Search query string
            num_results: Max results to return
            time_range: 'd' (day), 'w' (week), 'm' (month), 'y' (year), or None

        Returns:
            list of {'title', 'url', 'snippet', 'source'}
        """
        if self.use_serper:
            return self._serper_search(query, num_results, time_range)
        if HAS_DDGS:
            try:
                return self._ddgs_search(query, num_results, time_range)
            except Exception:
                pass
        return self._ddg_html_search(query, num_results)

    def news_search(self, query, num_results=10, time_range=None):
        """Search news specifically.

        Better for Agent A scanning — catches press releases,
        industry news, earnings reports, policy announcements.
        """
        if self.use_serper:
            return self._serper_news(query, num_results, time_range)
        if HAS_DDGS:
            try:
                return self._ddgs_news(query, num_results, time_range)
            except Exception:
                pass
        # Fall back to regular search with "news" prefix
        return self._ddg_html_search(f'{query} news', num_results)

    def _serper_search(self, query, num_results, time_range):
        params = {'q': query, 'num': num_results}
        if time_range:
            tbs_map = {'d': 'qdr:d', 'w': 'qdr:w', 'm': 'qdr:m', 'y': 'qdr:y'}
            params['tbs'] = tbs_map.get(time_range, '')

        r = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': self.serper_key, 'Content-Type': 'application/json'},
            json=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get('organic', [])[:num_results]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'source': 'serper',
            })
        return results

    def _serper_news(self, query, num_results, time_range):
        params = {'q': query, 'num': num_results}
        if time_range:
            tbs_map = {'d': 'qdr:d', 'w': 'qdr:w', 'm': 'qdr:m', 'y': 'qdr:y'}
            params['tbs'] = tbs_map.get(time_range, '')

        r = requests.post(
            'https://google.serper.dev/news',
            headers={'X-API-KEY': self.serper_key, 'Content-Type': 'application/json'},
            json=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get('news', [])[:num_results]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'date': item.get('date', ''),
                'source_name': item.get('source', ''),
                'source': 'serper',
            })
        return results

    def _ddg_html_search(self, query, num_results):
        """Fallback: scrape DuckDuckGo HTML endpoint. No package or API key needed."""
        import re
        r = requests.post(
            DDG_HTML_URL,
            data={'q': query, 'b': ''},
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ResearchEngine/1.0)'},
            timeout=15,
        )
        r.raise_for_status()
        html = r.text

        results = []
        # Parse result blocks from HTML
        for match in re.finditer(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.+?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.+?)</a>',
            html, re.DOTALL
        ):
            if len(results) >= num_results:
                break
            url = match.group(1)
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            if url and title:
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'source': 'duckduckgo_html',
                })
        return results

    def _ddgs_search(self, query, num_results, time_range):
        timelimit = time_range  # DDGS uses same format: d, w, m
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results, timelimit=timelimit):
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', ''),
                    'snippet': r.get('body', ''),
                    'source': 'duckduckgo',
                })
        return results

    def _ddgs_news(self, query, num_results, time_range):
        timelimit = time_range
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=num_results, timelimit=timelimit):
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'snippet': r.get('body', ''),
                    'date': r.get('date', ''),
                    'source_name': r.get('source', ''),
                    'source': 'duckduckgo',
                })
        return results

    # ---- Pre-built scans for Agent A ----

    def scan_liquidation_signals(self, num_results=10):
        """P2: Search for businesses in distress / consolidation."""
        queries = [
            'small business closures 2025 2026 industry consolidation',
            'AI disruption forcing business closures layoffs',
            'private equity roll-up AI competition pressure',
            'bankruptcy filings increase industry 2026',
        ]
        results = {}
        for q in queries:
            results[q] = self.news_search(q, num_results=num_results, time_range='m')
        return {
            'signal_type': 'liquidation_cascade',
            'principle': 'P2',
            'data': results,
        }

    def scan_practitioner_pain(self, num_results=10):
        """P2/P3: Search for practitioner complaints about industry costs."""
        queries = [
            'site:reddit.com "this industry is broken" AI cost',
            'site:reddit.com "can\'t hire enough" workers shortage',
            '"replaced with AI" cost savings results',
            'site:news.ycombinator.com "business model" "doesn\'t work" labor cost',
        ]
        results = {}
        for q in queries:
            results[q] = self.search(q, num_results=num_results, time_range='m')
        return {
            'signal_type': 'practitioner_pain',
            'principle': 'P2,P3',
            'data': results,
        }

    def scan_dead_business_revival(self, num_results=10):
        """P4: Search for failed business models that might work with AI."""
        queries = [
            'startup failed "unit economics" "labor costs" postmortem',
            '"shut down" startup "couldn\'t scale" operations coordination',
            'business model "didn\'t work" AI "now possible"',
            'site:reddit.com "business idea" "too expensive" AI automation',
        ]
        results = {}
        for q in queries:
            results[q] = self.search(q, num_results=num_results, time_range='y')
        return {
            'signal_type': 'dead_revival',
            'principle': 'P4',
            'data': results,
        }

    def scan_demographic_gaps(self, num_results=10):
        """P5: Search for labor shortage and demographic gap signals."""
        queries = [
            'labor shortage 2026 "can\'t find workers" industry',
            'retiring workforce aging "not enough" replacements',
            'nursing shortage accounting shortage trades shortage 2026',
            'immigration policy worker shortage impact',
        ]
        results = {}
        for q in queries:
            results[q] = self.news_search(q, num_results=num_results, time_range='m')
        return {
            'signal_type': 'demographic_gap',
            'principle': 'P5',
            'data': results,
        }

    def scan_inference_cost_drops(self, num_results=10):
        """P1: Track AI inference cost trajectory."""
        queries = [
            'AI inference cost reduction 2026 price per token',
            'LLM API pricing comparison cheaper',
            'open source model performance "good enough" production',
            'edge AI deployment cost local inference',
        ]
        results = {}
        for q in queries:
            results[q] = self.news_search(q, num_results=num_results, time_range='m')
        return {
            'signal_type': 'infra_overhang',
            'principle': 'P1',
            'data': results,
        }

    def test_connection(self):
        """Verify search access."""
        try:
            results = self.search('test query', num_results=1)
            backend = 'serper' if self.use_serper else 'duckduckgo'
            return {
                'status': 'ok',
                'source': f'Web Search ({backend})',
                'backend': backend,
                'test_result': results[0] if results else 'no results',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'Web Search', 'error': str(e)}
