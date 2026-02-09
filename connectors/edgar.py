"""SEC EDGAR connector.

Key data for the research engine:
- 10-K annual filings: cost structure breakdowns (P2, P3)
- 8-K current events: layoffs, restructuring, M&A (P2 cascade)
- Company search: find incumbents by industry (P2, P3)
- Full-text search: find filings mentioning AI, cost reduction, etc.

API docs: https://efts.sec.gov/LATEST/search-index?q=&dateRange=custom
EDGAR full-text search: https://efts.sec.gov/LATEST/search-index
No API key needed. Requires User-Agent header with contact info.
Rate limit: 10 requests/second.
"""

import requests
import time
from .config import EDGAR_CONTACT_EMAIL

SEARCH_URL = 'https://efts.sec.gov/LATEST/search-index'
FULL_TEXT_URL = 'https://efts.sec.gov/LATEST/search-index'
COMPANY_URL = 'https://www.sec.gov/cgi-bin/browse-edgar'
SUBMISSIONS_URL = 'https://data.sec.gov/submissions'
COMPANY_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
EFTS_URL = 'https://efts.sec.gov/LATEST/search-index'


class EdgarConnector:
    """Pull SEC filing data for incumbent analysis."""

    def __init__(self, contact_email=None):
        self.email = contact_email or EDGAR_CONTACT_EMAIL
        self.headers = {
            'User-Agent': f'ResearchEngine/1.0 ({self.email})',
            'Accept': 'application/json',
        }
        self._last_request = 0

    def _throttle(self):
        """EDGAR rate limit: 10 req/sec. Be polite."""
        elapsed = time.time() - self._last_request
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        self._last_request = time.time()

    def _get(self, url, params=None):
        self._throttle()
        r = requests.get(url, headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def search_filings(self, query, form_types=None, date_from=None,
                       date_to=None, limit=20):
        """Full-text search across SEC filings.

        This is the most powerful EDGAR feature for our engine.
        Search for terms like "margin compression", "AI implementation",
        "workforce reduction", "cost restructuring" to find incumbents
        under pressure.

        Args:
            query: Search terms (e.g., "margin compression AI")
            form_types: List of form types (e.g., ['10-K', '8-K'])
            date_from: 'YYYY-MM-DD'
            date_to: 'YYYY-MM-DD'
            limit: Max results
        """
        params = {
            'q': query,
            'dateRange': 'custom',
            'startdt': date_from or '2024-01-01',
            'enddt': date_to or '',
        }
        if form_types:
            params['forms'] = ','.join(form_types)

        self._throttle()
        r = requests.get(
            'https://efts.sec.gov/LATEST/search-index',
            headers=self.headers,
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for hit in data.get('hits', {}).get('hits', [])[:limit]:
            src = hit.get('_source', {})
            results.append({
                'company': src.get('display_names', ['Unknown'])[0] if src.get('display_names') else src.get('entity_name', 'Unknown'),
                'form_type': src.get('form_type', ''),
                'filed_date': src.get('file_date', ''),
                'file_number': src.get('file_num', ''),
                'description': src.get('display_date_filed', ''),
            })

        return {
            'query': query,
            'total_hits': data.get('hits', {}).get('total', {}).get('value', 0),
            'results': results,
        }

    def get_company_filings(self, cik, form_type=None, limit=10):
        """Get recent filings for a specific company by CIK.

        Args:
            cik: Central Index Key (number, with or without leading zeros)
            form_type: Filter by form type (e.g., '10-K', '8-K')
            limit: Max filings to return
        """
        cik_padded = str(cik).zfill(10)
        data = self._get(f'{SUBMISSIONS_URL}/CIK{cik_padded}.json')

        company_info = {
            'name': data.get('name', ''),
            'cik': cik,
            'sic': data.get('sic', ''),
            'sic_description': data.get('sicDescription', ''),
            'state': data.get('stateOfIncorporation', ''),
            'fiscal_year_end': data.get('fiscalYearEnd', ''),
        }

        recent = data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accessions = recent.get('accessionNumber', [])
        descriptions = recent.get('primaryDocDescription', [])

        filings = []
        for i in range(min(len(forms), 40)):
            if form_type and forms[i] != form_type:
                continue
            if len(filings) >= limit:
                break
            filings.append({
                'form_type': forms[i],
                'filing_date': dates[i] if i < len(dates) else '',
                'accession': accessions[i] if i < len(accessions) else '',
                'description': descriptions[i] if i < len(descriptions) else '',
            })

        return {
            'company': company_info,
            'filings': filings,
        }

    def search_companies(self, query, limit=10):
        """Search for companies by name or ticker.

        Use this to find CIKs for specific incumbents Agent B identifies.
        """
        self._throttle()
        r = requests.get(
            COMPANY_TICKERS_URL,
            headers=self.headers,
            timeout=15,
        )
        r.raise_for_status()
        tickers = r.json()

        query_lower = query.lower()
        matches = []
        for entry in tickers.values():
            name = entry.get('title', '').lower()
            ticker = entry.get('ticker', '').lower()
            if query_lower in name or query_lower in ticker:
                matches.append({
                    'cik': entry.get('cik_str'),
                    'ticker': entry.get('ticker', ''),
                    'name': entry.get('title', ''),
                })
                if len(matches) >= limit:
                    break

        return matches

    def scan_for_distress(self, date_from=None):
        """P2: Scan for filings indicating business distress.

        Searches for keywords that signal liquidation cascade:
        - Workforce reduction / restructuring
        - Going concern warnings
        - Margin compression mentions
        - AI disruption mentions in risk factors
        """
        keywords = [
            '"workforce reduction" OR "restructuring charges"',
            '"going concern"',
            '"margin compression" OR "margin pressure"',
            '"artificial intelligence" AND "risk factor"',
            '"cost reduction" AND "automation"',
        ]

        results = {}
        for kw in keywords:
            data = self.search_filings(
                query=kw,
                form_types=['10-K', '8-K'],
                date_from=date_from or '2025-01-01',
                limit=10,
            )
            results[kw] = data

        return {
            'signal_type': 'corporate_distress',
            'principle': 'P2',
            'data': results,
            'interpretation': (
                'Companies filing 8-Ks about restructuring, 10-Ks with going '
                'concern warnings, or mentioning AI as a risk factor are '
                'potential targets. Their customers and contracts may become '
                'available as they consolidate or exit.'
            ),
        }

    def scan_for_ai_adoption_failures(self, date_from=None):
        """P2: Find companies that tried AI transformation and struggled.

        These are incumbents with LOW MOBILITY — they know they need to
        change but can't execute. Prime disruption targets.
        """
        data = self.search_filings(
            query='"artificial intelligence" AND ("implementation challenges" OR "transition" OR "digital transformation")',
            form_types=['10-K'],
            date_from=date_from or '2025-01-01',
            limit=15,
        )

        return {
            'signal_type': 'ai_adoption_failure',
            'principle': 'P2',
            'data': data,
            'interpretation': (
                'Companies discussing AI implementation challenges in 10-K '
                'filings are signaling low mobility. They recognize the need '
                'to adopt AI but face organizational barriers. Their market '
                'position is vulnerable to agentic-first entrants.'
            ),
        }

    def test_connection(self):
        """Verify EDGAR access."""
        try:
            companies = self.search_companies('apple', limit=1)
            return {
                'status': 'ok',
                'source': 'SEC EDGAR',
                'authenticated': 'N/A (no key required)',
                'contact_email': self.email,
                'test_search': companies[0] if companies else 'no results',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'SEC EDGAR', 'error': str(e)}
