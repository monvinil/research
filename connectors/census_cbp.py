"""Census Bureau County Business Patterns (CBP) connector.

Provides establishment counts, employment, and payroll by NAICS sector
at national level. Critical for computing Structural Necessity (SN) scores:
- Fragmentation level (many small firms = high SN)
- Firm size distribution (micro-heavy = ripe for consolidation via AI)
- Total establishments and employment per sector

Uses the 2022 CBP dataset (latest available annual release).

API docs: https://www.census.gov/data/developers/data-sets/cbp-nonemp.html
Free key: https://api.census.gov/data/key_signup.html
"""

import math
import requests
from .config import CENSUS_API_KEY

BASE_URL = 'https://api.census.gov/data/2022/cbp'

# NAICS 2-digit sector codes and labels
NAICS_SECTORS = {
    '11': 'Agriculture, Forestry, Fishing and Hunting',
    '21': 'Mining, Quarrying, and Oil and Gas Extraction',
    '22': 'Utilities',
    '23': 'Construction',
    '31-33': 'Manufacturing',
    '42': 'Wholesale Trade',
    '44-45': 'Retail Trade',
    '48-49': 'Transportation and Warehousing',
    '51': 'Information',
    '52': 'Finance and Insurance',
    '53': 'Real Estate and Rental and Leasing',
    '54': 'Professional, Scientific, and Technical Services',
    '55': 'Management of Companies and Enterprises',
    '56': 'Administrative and Support and Waste Management',
    '61': 'Educational Services',
    '62': 'Health Care and Social Assistance',
    '71': 'Arts, Entertainment, and Recreation',
    '72': 'Accommodation and Food Services',
    '81': 'Other Services (except Public Administration)',
}

# Employee size class codes used by CBP
# EMPSZES codes and their labels (enterprise size not used; establishment size)
EMPSIZE_CODES = {
    '001': 'All establishments',
    '210': '< 5 employees',
    '220': '5-9 employees',
    '230': '10-19 employees',
    '241': '20-49 employees',
    '242': '50-99 employees',
    '251': '100-249 employees',
    '252': '250-499 employees',
    '254': '500-999 employees',
    '260': '1,000+ employees',
}

# Mapping from size code to midpoint employee count for Herfindahl approximation
EMPSIZE_MIDPOINTS = {
    '210': 2.5,
    '220': 7,
    '230': 14.5,
    '241': 34.5,
    '242': 74.5,
    '251': 174.5,
    '252': 374.5,
    '254': 749.5,
    '260': 2000,  # conservative estimate for 1000+
}


class CensusCBPConnector:
    """Pull County Business Patterns data for fragmentation and market sizing.

    CBP is the definitive source for establishment counts by industry and size.
    Combined with employment and payroll data, it enables:
    - Structural Necessity scoring (fragmented = high SN)
    - Market sizing (total establishments x avg revenue proxy)
    - Firm size distribution analysis (micro-heavy vs. concentrated)
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or CENSUS_API_KEY
        if not self.api_key:
            raise ValueError(
                'Census API key required. Get free key at: '
                'https://api.census.gov/data/key_signup.html\n'
                'Then set CENSUS_API_KEY in .env'
            )

    def _get(self, params):
        """Make a request to the CBP API.

        The Census API returns data as a list of lists: first row is headers,
        subsequent rows are data. This method returns the raw parsed JSON.
        """
        params['key'] = self.api_key
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _parse_response(self, data):
        """Convert Census API array-of-arrays response to list of dicts."""
        if not data or len(data) < 2:
            return []
        headers = data[0]
        rows = data[1:]
        return [dict(zip(headers, row)) for row in rows]

    def get_sector_overview(self, naics_2digit=None):
        """Get establishment count, employment, payroll for all 2-digit NAICS sectors.

        If naics_2digit specified (e.g. '54'), filter to that sector only.

        Returns:
            list of {naics_code, naics_label, establishments, employment,
                     annual_payroll, avg_payroll_per_employee}
        """
        params = {
            'get': 'NAICS2017,NAICS2017_LABEL,ESTAB,EMP,PAYANN',
            'for': 'us:*',
        }
        if naics_2digit:
            params['NAICS2017'] = naics_2digit

        data = self._get(params)
        rows = self._parse_response(data)

        results = []
        for row in rows:
            naics_code = row.get('NAICS2017', '')
            # Skip the total row and codes that are not 2-digit sectors
            # (unless a specific code was requested)
            if not naics_2digit:
                # 2-digit sectors have codes like '54', '62', '31-33', etc.
                if len(naics_code) > 5 or naics_code == '00':
                    continue

            estab = self._safe_int(row.get('ESTAB'))
            emp = self._safe_int(row.get('EMP'))
            payann = self._safe_int(row.get('PAYANN'))

            avg_pay = None
            if emp and emp > 0 and payann is not None:
                # PAYANN is in $1,000s
                avg_pay = round((payann * 1000) / emp)

            results.append({
                'naics_code': naics_code,
                'naics_label': row.get('NAICS2017_LABEL', NAICS_SECTORS.get(naics_code, '')),
                'establishments': estab,
                'employment': emp,
                'annual_payroll': payann,
                'annual_payroll_note': 'in $1,000s',
                'avg_payroll_per_employee': avg_pay,
            })

        # Sort by employment descending
        results.sort(key=lambda x: x.get('employment') or 0, reverse=True)
        return results

    def get_subsector_detail(self, naics_prefix):
        """Get 4-digit and 6-digit breakdown for a NAICS prefix.

        For example, naics_prefix='54' returns all professional services
        sub-industries (5411 Legal, 5412 Accounting, 5413 Architecture, etc.)

        Args:
            naics_prefix: 2-digit NAICS code (e.g. '54', '62')

        Returns:
            list of {naics_code, naics_label, establishments, employment,
                     annual_payroll} for all sub-industries under the prefix
        """
        params = {
            'get': 'NAICS2017,NAICS2017_LABEL,ESTAB,EMP,PAYANN',
            'for': 'us:*',
            'NAICS2017': f'{naics_prefix}*',
        }

        data = self._get(params)
        rows = self._parse_response(data)

        results = []
        for row in rows:
            naics_code = row.get('NAICS2017', '')
            # Include 3-digit through 6-digit codes (skip the 2-digit parent)
            if naics_code == naics_prefix:
                continue

            estab = self._safe_int(row.get('ESTAB'))
            emp = self._safe_int(row.get('EMP'))
            payann = self._safe_int(row.get('PAYANN'))

            results.append({
                'naics_code': naics_code,
                'naics_label': row.get('NAICS2017_LABEL', ''),
                'establishments': estab,
                'employment': emp,
                'annual_payroll': payann,
                'annual_payroll_note': 'in $1,000s',
                'depth': len(naics_code.replace('-', '')),
            })

        results.sort(key=lambda x: x.get('employment') or 0, reverse=True)
        return results

    def get_firm_size_distribution(self, naics_code):
        """Get establishment count by employee size class for a NAICS code.

        Returns the distribution of firms across size buckets plus
        computed fragmentation metrics.

        Args:
            naics_code: Any NAICS code (2-digit '54', 4-digit '5411', etc.)

        Returns:
            dict with:
            - size_distribution: list of {size_class, size_label, establishments, pct}
            - pct_micro: % of establishments with < 5 employees
            - pct_small: % with < 20 employees
            - pct_large: % with 100+ employees
            - herfindahl_proxy: estimated HHI based on size distribution
            - total_establishments: total count
        """
        params = {
            'get': 'NAICS2017,EMPSZES,EMPSZES_LABEL,ESTAB',
            'for': 'us:*',
            'NAICS2017': naics_code,
        }

        data = self._get(params)
        rows = self._parse_response(data)

        total = 0
        size_dist = []
        for row in rows:
            size_code = row.get('EMPSZES', '')
            estab = self._safe_int(row.get('ESTAB'))

            if size_code == '001':
                # This is the total row
                total = estab or 0
                continue

            if size_code in EMPSIZE_CODES and estab is not None:
                size_dist.append({
                    'size_code': size_code,
                    'size_label': row.get('EMPSZES_LABEL', EMPSIZE_CODES.get(size_code, '')),
                    'establishments': estab,
                })

        # Calculate percentages
        if total > 0:
            for entry in size_dist:
                entry['pct'] = round(100 * entry['establishments'] / total, 1)
        else:
            for entry in size_dist:
                entry['pct'] = 0

        # Compute fragmentation metrics
        pct_micro = sum(e['pct'] for e in size_dist if e['size_code'] == '210')
        pct_small = sum(e['pct'] for e in size_dist
                        if e['size_code'] in ('210', '220', '230'))
        pct_large = sum(e['pct'] for e in size_dist
                        if e['size_code'] in ('251', '252', '254', '260'))

        # Herfindahl proxy: estimate HHI from size distribution
        # Lower HHI = more fragmented
        hhi = self._estimate_herfindahl(size_dist, total)

        return {
            'naics_code': naics_code,
            'total_establishments': total,
            'size_distribution': size_dist,
            'pct_micro': round(pct_micro, 1),
            'pct_small': round(pct_small, 1),
            'pct_large': round(pct_large, 1),
            'herfindahl_proxy': round(hhi, 4),
            'interpretation': (
                f'{"Highly fragmented" if pct_small > 75 else "Moderately concentrated" if pct_small > 50 else "Concentrated"} '
                f'market: {pct_small:.0f}% of establishments have < 20 employees. '
                f'Micro firms (< 5 emp) = {pct_micro:.0f}%. '
                f'HHI proxy: {hhi:.4f} (lower = more fragmented).'
            ),
        }

    def _estimate_herfindahl(self, size_dist, total):
        """Estimate Herfindahl-Hirschman Index from size distribution.

        Uses midpoint employee counts as a proxy for market share.
        This is a rough approximation — true HHI requires firm-level revenue data.
        A low HHI (< 0.01) indicates extreme fragmentation.
        """
        if total == 0:
            return 0

        # Total employment proxy
        total_emp = sum(
            e['establishments'] * EMPSIZE_MIDPOINTS.get(e['size_code'], 0)
            for e in size_dist
            if e['size_code'] in EMPSIZE_MIDPOINTS
        )

        if total_emp == 0:
            return 0

        # HHI = sum of squared market shares
        # Treat each size bucket as a group of identical firms
        hhi = 0
        for entry in size_dist:
            midpoint = EMPSIZE_MIDPOINTS.get(entry['size_code'])
            if midpoint is None or entry['establishments'] == 0:
                continue

            n_firms = entry['establishments']
            firm_share = midpoint / total_emp
            # Each firm in this bucket has the same estimated share
            hhi += n_firms * (firm_share ** 2)

        return hhi

    def get_fragmentation_score(self, naics_code):
        """Compute a fragmentation score (0-10) for SN scoring.

        10 = maximally fragmented (many tiny firms, no dominant players)
        1 = highly concentrated (few large firms dominate)

        The score combines:
        - % micro firms (< 5 emp): weighted 40%
        - % small firms (< 20 emp): weighted 30%
        - Inverse HHI proxy: weighted 30%

        Args:
            naics_code: NAICS code to score

        Returns:
            dict with score (0-10), components, and interpretation
        """
        dist = self.get_firm_size_distribution(naics_code)

        if dist['total_establishments'] == 0:
            return {
                'naics_code': naics_code,
                'fragmentation_score': None,
                'error': 'No establishment data found',
            }

        pct_micro = dist['pct_micro']
        pct_small = dist['pct_small']
        hhi = dist['herfindahl_proxy']

        # Score components (each 0-10)
        # pct_micro: 80%+ micro = 10, 0% = 0
        micro_score = min(10, pct_micro / 8)

        # pct_small: 90%+ small = 10, 0% = 0
        small_score = min(10, pct_small / 9)

        # HHI inverse: very low HHI (< 0.001) = 10, high HHI (> 0.1) = 0
        if hhi > 0:
            hhi_score = max(0, min(10, 10 * (1 - math.log10(hhi * 10000) / 4)))
        else:
            hhi_score = 10  # Zero HHI = maximally fragmented

        # Weighted combination
        score = round(
            0.4 * micro_score + 0.3 * small_score + 0.3 * hhi_score,
            1
        )

        return {
            'naics_code': naics_code,
            'fragmentation_score': score,
            'components': {
                'pct_micro': pct_micro,
                'micro_score': round(micro_score, 1),
                'pct_small': pct_small,
                'small_score': round(small_score, 1),
                'herfindahl_proxy': hhi,
                'hhi_score': round(hhi_score, 1),
            },
            'total_establishments': dist['total_establishments'],
            'signal_type': 'fragmentation_score',
            'interpretation': (
                f'Fragmentation score: {score}/10. '
                f'{"Highly fragmented — strong SN candidate" if score >= 7 else "Moderately fragmented" if score >= 4 else "Concentrated — low SN potential"}. '
                f'{pct_micro:.0f}% micro firms, {pct_small:.0f}% small firms, '
                f'HHI proxy: {hhi:.4f}.'
            ),
        }

    def screen_sectors(self):
        """Screen all 2-digit NAICS sectors and return sorted by fragmentation + employment.

        This feeds the top-down enumeration pipeline: start with the biggest,
        most fragmented sectors and work down.

        Returns:
            dict with signal_type, sectors list (sorted by composite score),
            and interpretation
        """
        overview = self.get_sector_overview()

        results = []
        for sector in overview:
            naics = sector['naics_code']
            if not naics or naics == '00':
                continue

            try:
                frag = self.get_fragmentation_score(naics)
                frag_score = frag.get('fragmentation_score')
            except Exception:
                frag_score = None

            # Employment scale score (log-scaled, 0-10)
            emp = sector.get('employment') or 0
            if emp > 0:
                # 10M+ emp = 10, 1K emp ~ 2
                emp_score = min(10, round(math.log10(max(emp, 1)) / 0.7, 1))
            else:
                emp_score = 0

            # Composite: 60% fragmentation, 40% employment scale
            if frag_score is not None:
                composite = round(0.6 * frag_score + 0.4 * emp_score, 1)
            else:
                composite = None

            results.append({
                'naics_code': naics,
                'naics_label': sector['naics_label'],
                'establishments': sector['establishments'],
                'employment': sector['employment'],
                'annual_payroll': sector['annual_payroll'],
                'fragmentation_score': frag_score,
                'employment_scale_score': emp_score,
                'composite_score': composite,
            })

        # Sort by composite score descending (None values at bottom)
        results.sort(
            key=lambda x: x['composite_score'] if x['composite_score'] is not None else -1,
            reverse=True,
        )

        return {
            'signal_type': 'sector_screen',
            'principle': 'SN_scoring',
            'sectors': results,
            'interpretation': (
                'Sectors sorted by composite score (60% fragmentation + 40% employment scale). '
                'Top-ranked sectors have the most fragmented markets with the largest employment '
                'bases — these are the highest Structural Necessity candidates for AI disruption. '
                'Feed top sectors into subsector detail and QCEW wage analysis.'
            ),
        }

    @staticmethod
    def _safe_int(val):
        """Safely convert Census API string values to int, handling nulls and suppressed data."""
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def test_connection(self):
        """Verify Census API access with a minimal CBP query."""
        try:
            data = self._get({
                'get': 'ESTAB',
                'for': 'us:*',
                'NAICS2017': '54',
            })
            estab = data[1][0] if len(data) > 1 else 'N/A'
            return {
                'status': 'ok',
                'source': 'Census CBP (2022)',
                'test': f'Professional services (NAICS 54) establishments: {estab}',
            }
        except Exception as e:
            return {
                'status': 'error',
                'source': 'Census CBP',
                'error': str(e),
            }
