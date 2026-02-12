"""QCEW (Quarterly Census of Employment and Wages) connector.

BLS QCEW provides quarterly employment, wages, and establishment counts
at county x industry level. More current than CBP (quarterly vs annual)
and includes average weekly wages — essential for Baumol cost disease
detection (T3 lens).

Key uses for the research engine:
- Baumol candidate screening: sectors with wage growth >> CPI = stored energy
- Establishment trends: growing vs. shrinking industries over time
- Wage level benchmarking: where are the highest-paid sectors?
- Cross-reference with CBP fragmentation for composite SN scoring

Data source: BLS QCEW public data files (no API key needed)
URL pattern: https://data.bls.gov/cew/data/api/YEAR/QTR/industry/NAICS_CODE.csv
Annual averages: https://data.bls.gov/cew/data/api/YEAR/a/industry/NAICS_CODE.csv

CSV columns include: area_fips, own_code, industry_code, agglvl_code,
size_code, year, qtr, disclosure_code, area_title, own_title,
industry_title, agglvl_title, size_title, qtrly_estabs, month1_emplvl,
month2_emplvl, month3_emplvl, total_qtrly_wages, avg_wkly_wage, etc.

Filters applied: area_fips='US000' (national), own_code='5' (private sector).
"""

import csv
import io
import os
import json
import time
import requests

BASE_URL = 'https://data.bls.gov/cew/data/api'
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days

# Aggregation level codes for filtering QCEW data
# These determine the NAICS depth of each row
AGGLVL_CODES = {
    'national_total': '10',       # All industries, national
    'national_supersector': '11', # Supersector (2-digit domain), national
    'national_sector': '14',      # NAICS sector (2-digit), national
    'national_3digit': '15',      # NAICS 3-digit subsector, national
    'national_4digit': '16',      # NAICS 4-digit industry group, national
    'national_5digit': '17',      # NAICS 5-digit industry, national
    'national_6digit': '18',      # NAICS 6-digit national industry, national
}

# NAICS code for "all industries" (10 = total covered)
ALL_INDUSTRIES_CODE = '10'

# Approximate CPI growth rate for Baumol indicator calculation
# Updated periodically; this is a reasonable baseline for 2020-2024
DEFAULT_CPI_GROWTH = 0.025  # 2.5% annual


class QCEWConnector:
    """Pull quarterly employment and wage data from BLS QCEW.

    No API key required. Data is downloaded as CSV files and cached
    locally to data/cache/ with a 7-day TTL to avoid re-downloading.
    """

    def __init__(self, cache_dir=None, cache_ttl=None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_ttl = cache_ttl if cache_ttl is not None else CACHE_TTL_SECONDS
        os.makedirs(self.cache_dir, exist_ok=True)

    def _build_url(self, year, quarter, naics_code):
        """Build the QCEW data URL.

        Args:
            year: Data year (e.g. 2023)
            quarter: 1-4 for quarterly, or 'a' for annual averages
            naics_code: NAICS code or '10' for all industries
        """
        qtr = str(quarter) if quarter != 'a' else 'a'
        return f'{BASE_URL}/{year}/{qtr}/industry/{naics_code}.csv'

    def _cache_path(self, year, quarter, naics_code):
        """Generate a cache file path for a given query."""
        qtr_str = f'q{quarter}' if quarter != 'a' else 'annual'
        safe_naics = naics_code.replace('-', '_')
        return os.path.join(self.cache_dir, f'qcew_{safe_naics}_{year}_{qtr_str}.csv')

    def _meta_path(self, cache_path):
        """Path for the cache metadata file (stores fetch timestamp)."""
        return cache_path.replace('.csv', '.meta.json')

    def _is_cache_valid(self, cache_path):
        """Check if a cached file exists and is within TTL."""
        meta_path = self._meta_path(cache_path)
        if not os.path.exists(cache_path) or not os.path.exists(meta_path):
            return False
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            fetched_at = meta.get('fetched_at', 0)
            return (time.time() - fetched_at) < self.cache_ttl
        except (json.JSONDecodeError, OSError):
            return False

    def _fetch_csv(self, year, quarter, naics_code):
        """Fetch QCEW CSV data, using cache if available.

        Returns:
            list of dicts (parsed CSV rows)
        """
        cache_path = self._cache_path(year, quarter, naics_code)

        # Check cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            except (OSError, csv.Error):
                pass  # Cache read failure — re-fetch

        # Download fresh data
        url = self._build_url(year, quarter, naics_code)
        r = requests.get(url, timeout=60)
        r.raise_for_status()

        # Save to cache
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(r.text)
            meta_path = self._meta_path(cache_path)
            with open(meta_path, 'w') as f:
                json.dump({'fetched_at': time.time(), 'year': str(year),
                           'quarter': str(quarter), 'naics_code': str(naics_code)}, f)
        except OSError:
            pass  # Cache write failure is non-fatal

        # Parse CSV
        reader = csv.DictReader(io.StringIO(r.text))
        return list(reader)

    def _filter_national_private(self, rows, agglvl_code=None):
        """Filter QCEW rows to national-level private sector data.

        Args:
            rows: list of CSV row dicts
            agglvl_code: if specified, also filter to this aggregation level

        Returns:
            filtered list of row dicts
        """
        filtered = []
        for row in rows:
            # National level
            if row.get('area_fips', '').strip() != 'US000':
                continue
            # Private sector (own_code = 5)
            if row.get('own_code', '').strip() != '5':
                continue
            # Aggregation level filter
            if agglvl_code and row.get('agglvl_code', '').strip() != agglvl_code:
                continue
            # Skip rows with disclosure suppression
            if row.get('disclosure_code', '').strip() not in ('', 'N'):
                continue

            filtered.append(row)
        return filtered

    def get_national_industry(self, naics_code, year=2023, quarter=None):
        """Get employment and wage data for a NAICS code at national level.

        Args:
            naics_code: NAICS code (e.g. '54', '5411', '62')
            year: Data year (default 2023)
            quarter: 1-4 for quarterly data, or None for annual averages

        Returns:
            dict with naics_code, industry_title, establishments, employment,
            avg_weekly_wage, total_wages, and source metadata
        """
        qtr = quarter if quarter else 'a'

        # Determine the right aggregation level based on NAICS code length
        naics_clean = str(naics_code).replace('-', '')
        if naics_clean == '10' or naics_clean == ALL_INDUSTRIES_CODE:
            agglvl = AGGLVL_CODES['national_total']
        elif len(naics_clean) == 2:
            agglvl = AGGLVL_CODES['national_sector']
        elif len(naics_clean) == 3:
            agglvl = AGGLVL_CODES['national_3digit']
        elif len(naics_clean) == 4:
            agglvl = AGGLVL_CODES['national_4digit']
        elif len(naics_clean) == 5:
            agglvl = AGGLVL_CODES['national_5digit']
        elif len(naics_clean) == 6:
            agglvl = AGGLVL_CODES['national_6digit']
        else:
            agglvl = None

        rows = self._fetch_csv(year, qtr, naics_code)
        filtered = self._filter_national_private(rows, agglvl_code=agglvl)

        if not filtered:
            return {
                'naics_code': str(naics_code),
                'year': year,
                'quarter': quarter,
                'error': f'No national private-sector data found for NAICS {naics_code}, year {year}',
            }

        # Take the first matching row (there should be exactly one for a specific NAICS + agglvl)
        row = filtered[0]

        estabs = self._safe_int(row.get('qtrly_estabs'))
        # Use average of three monthly employment levels
        m1 = self._safe_int(row.get('month1_emplvl'))
        m2 = self._safe_int(row.get('month2_emplvl'))
        m3 = self._safe_int(row.get('month3_emplvl'))
        emp_values = [v for v in [m1, m2, m3] if v is not None]
        avg_employment = round(sum(emp_values) / len(emp_values)) if emp_values else None

        avg_wkly_wage = self._safe_int(row.get('avg_wkly_wage'))
        total_wages = self._safe_int(row.get('total_qtrly_wages'))
        avg_annual_pay = self._safe_int(row.get('avg_annual_pay'))

        return {
            'naics_code': str(naics_code),
            'industry_title': row.get('industry_title', '').strip(),
            'year': year,
            'quarter': quarter,
            'establishments': estabs,
            'employment': avg_employment,
            'avg_weekly_wage': avg_wkly_wage,
            'avg_annual_pay': avg_annual_pay,
            'total_wages': total_wages,
            'total_wages_note': 'quarterly total in dollars' if quarter else 'annual total in dollars',
        }

    def get_all_sectors(self, year=2023):
        """Get all 2-digit NAICS sectors with employment and wages.

        Returns list sorted by employment descending. Uses annual averages
        for the most stable comparison.

        Returns:
            dict with signal_type, sectors list, and interpretation
        """
        rows = self._fetch_csv(year, 'a', ALL_INDUSTRIES_CODE)
        filtered = self._filter_national_private(rows, agglvl_code=AGGLVL_CODES['national_sector'])

        sectors = []
        for row in filtered:
            naics = row.get('industry_code', '').strip()
            m1 = self._safe_int(row.get('month1_emplvl'))
            m2 = self._safe_int(row.get('month2_emplvl'))
            m3 = self._safe_int(row.get('month3_emplvl'))
            emp_values = [v for v in [m1, m2, m3] if v is not None]
            avg_emp = round(sum(emp_values) / len(emp_values)) if emp_values else None

            sectors.append({
                'naics_code': naics,
                'industry_title': row.get('industry_title', '').strip(),
                'establishments': self._safe_int(row.get('qtrly_estabs')),
                'employment': avg_emp,
                'avg_weekly_wage': self._safe_int(row.get('avg_wkly_wage')),
                'avg_annual_pay': self._safe_int(row.get('avg_annual_pay')),
                'total_annual_wages': self._safe_int(row.get('total_qtrly_wages')),
            })

        sectors.sort(key=lambda x: x.get('employment') or 0, reverse=True)

        return {
            'signal_type': 'qcew_sector_overview',
            'year': year,
            'sectors': sectors,
            'interpretation': (
                'All 2-digit NAICS sectors ranked by employment. '
                'Cross-reference avg_weekly_wage with CBP fragmentation scores '
                'to identify high-wage, fragmented sectors — prime targets '
                'for agentic cost-structure disruption.'
            ),
        }

    def get_wage_growth(self, naics_code, years_back=3):
        """Calculate wage growth rate for a NAICS code over N years.

        Uses annual average weekly wages. Computes CAGR and a Baumol
        indicator (wage CAGR minus estimated CPI growth).

        A positive Baumol indicator means wages are outpacing inflation,
        indicating stored energy for disruption (T3 lens).

        Args:
            naics_code: NAICS code to analyze
            years_back: number of years to look back (default 3)

        Returns:
            dict with wage_cagr, latest_wage, earliest_wage, baumol_indicator,
            and year-by-year wage data
        """
        import datetime
        current_year = datetime.datetime.now().year

        wages_by_year = {}
        errors = []

        for offset in range(years_back + 1):
            year = current_year - years_back + offset
            try:
                data = self.get_national_industry(naics_code, year=year, quarter=None)
                wage = data.get('avg_weekly_wage')
                if wage is not None:
                    wages_by_year[year] = wage
            except Exception as e:
                errors.append(f'{year}: {str(e)}')

        if len(wages_by_year) < 2:
            return {
                'naics_code': str(naics_code),
                'error': f'Insufficient wage data (got {len(wages_by_year)} years). Errors: {errors}',
            }

        sorted_years = sorted(wages_by_year.keys())
        earliest_year = sorted_years[0]
        latest_year = sorted_years[-1]
        earliest_wage = wages_by_year[earliest_year]
        latest_wage = wages_by_year[latest_year]
        n_years = latest_year - earliest_year

        if n_years > 0 and earliest_wage > 0:
            wage_cagr = (latest_wage / earliest_wage) ** (1 / n_years) - 1
        else:
            wage_cagr = 0

        baumol_indicator = wage_cagr - DEFAULT_CPI_GROWTH

        return {
            'naics_code': str(naics_code),
            'wage_cagr': round(wage_cagr, 4),
            'wage_cagr_pct': round(wage_cagr * 100, 2),
            'baumol_indicator': round(baumol_indicator, 4),
            'baumol_indicator_pct': round(baumol_indicator * 100, 2),
            'latest_wage': latest_wage,
            'latest_year': latest_year,
            'earliest_wage': earliest_wage,
            'earliest_year': earliest_year,
            'wages_by_year': wages_by_year,
            'cpi_assumption': DEFAULT_CPI_GROWTH,
            'signal_type': 'wage_growth',
            'interpretation': (
                f'Wage CAGR: {wage_cagr*100:.1f}% ({earliest_year}-{latest_year}). '
                f'Baumol indicator: {baumol_indicator*100:+.1f}pp above CPI. '
                f'{"STRONG Baumol signal — wages far outpacing inflation, high stored energy for disruption." if baumol_indicator > 0.02 else "Moderate Baumol signal — wages slightly above CPI." if baumol_indicator > 0 else "Weak/no Baumol signal — wages tracking or below CPI."}'
            ),
        }

    def get_establishment_trends(self, naics_code, years_back=3):
        """Track establishment count over time for consolidation/fragmentation trends.

        Uses annual average establishment counts. A shrinking establishment
        count with stable employment signals consolidation. Growing count
        signals fragmentation or new market entry.

        Args:
            naics_code: NAICS code to track
            years_back: number of years to look back (default 3)

        Returns:
            dict with trend classification, CAGR, and year-by-year data
        """
        import datetime
        current_year = datetime.datetime.now().year

        estabs_by_year = {}
        errors = []

        for offset in range(years_back + 1):
            year = current_year - years_back + offset
            try:
                data = self.get_national_industry(naics_code, year=year, quarter=None)
                estab = data.get('establishments')
                if estab is not None:
                    estabs_by_year[year] = estab
            except Exception as e:
                errors.append(f'{year}: {str(e)}')

        if len(estabs_by_year) < 2:
            return {
                'naics_code': str(naics_code),
                'error': f'Insufficient establishment data (got {len(estabs_by_year)} years). Errors: {errors}',
            }

        sorted_years = sorted(estabs_by_year.keys())
        earliest_year = sorted_years[0]
        latest_year = sorted_years[-1]
        earliest = estabs_by_year[earliest_year]
        latest = estabs_by_year[latest_year]
        n_years = latest_year - earliest_year

        if n_years > 0 and earliest > 0:
            cagr = (latest / earliest) ** (1 / n_years) - 1
        else:
            cagr = 0

        # Classify trend
        if cagr > 0.02:
            trend = 'growing'
        elif cagr < -0.02:
            trend = 'shrinking'
        else:
            trend = 'stable'

        return {
            'naics_code': str(naics_code),
            'trend': trend,
            'cagr': round(cagr, 4),
            'cagr_pct': round(cagr * 100, 2),
            'latest': latest,
            'latest_year': latest_year,
            'earliest': earliest,
            'earliest_year': earliest_year,
            'establishments_by_year': estabs_by_year,
            'signal_type': 'establishment_trend',
            'interpretation': (
                f'Establishments {trend} at {cagr*100:+.1f}%/yr ({earliest_year}-{latest_year}). '
                f'{earliest:,} -> {latest:,}. '
                f'{"Consolidation underway — fewer firms serving the market." if trend == "shrinking" else "Market expanding — new entrants or fragmentation increasing." if trend == "growing" else "Stable market structure."}'
            ),
        }

    def screen_baumol_candidates(self, min_employment=50000):
        """Find sectors with wage growth significantly above CPI.

        These are Baumol cost disease candidates (T3 lens) -- sectors where
        wages have been rising faster than inflation, building up stored
        energy for AI-driven cost-structure disruption.

        Filters to sectors with at least min_employment workers to ensure
        material market size.

        Args:
            min_employment: minimum employment threshold (default 50,000)

        Returns:
            dict with signal_type, candidates list sorted by baumol_indicator,
            and interpretation
        """
        import datetime
        current_year = datetime.datetime.now().year
        latest_year = current_year - 1  # Most recent complete year

        # First, get all sectors to find those meeting the employment threshold
        all_sectors = self.get_all_sectors(year=latest_year)
        qualifying_sectors = [
            s for s in all_sectors.get('sectors', [])
            if (s.get('employment') or 0) >= min_employment
        ]

        candidates = []
        for sector in qualifying_sectors:
            naics = sector['naics_code']
            try:
                wage_data = self.get_wage_growth(naics, years_back=3)
                if 'error' in wage_data:
                    continue

                candidates.append({
                    'naics_code': naics,
                    'industry_title': sector['industry_title'],
                    'employment': sector['employment'],
                    'avg_weekly_wage': sector['avg_weekly_wage'],
                    'wage_cagr_pct': wage_data['wage_cagr_pct'],
                    'baumol_indicator_pct': wage_data['baumol_indicator_pct'],
                    'latest_wage': wage_data['latest_wage'],
                    'earliest_wage': wage_data['earliest_wage'],
                    'wage_period': f"{wage_data['earliest_year']}-{wage_data['latest_year']}",
                })
            except Exception:
                continue

        # Sort by Baumol indicator descending (strongest cost disease first)
        candidates.sort(
            key=lambda x: x.get('baumol_indicator_pct', 0),
            reverse=True,
        )

        return {
            'signal_type': 'baumol_candidates',
            'principle': 'T3_baumol_cost_disease',
            'min_employment': min_employment,
            'candidates': candidates,
            'interpretation': (
                f'Found {len(candidates)} sectors with employment >= {min_employment:,} workers. '
                f'Sorted by Baumol indicator (wage CAGR minus ~{DEFAULT_CPI_GROWTH*100:.1f}% CPI). '
                'Top candidates have wages rising fastest above inflation — maximum stored energy '
                'for agentic disruption. Cross-reference with CBP fragmentation scores for '
                'composite SN scoring.'
            ),
        }

    @staticmethod
    def _safe_int(val):
        """Safely convert string to int, handling empty strings and non-numeric values."""
        if val is None:
            return None
        val = str(val).strip().replace(',', '')
        if val == '' or val == 'N' or val == 'n':
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            # Try float -> int for values like "1234.0"
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None

    def test_connection(self):
        """Verify QCEW data access by fetching a small dataset."""
        try:
            # Fetch all-industries national data for the most recent likely year
            import datetime
            test_year = datetime.datetime.now().year - 1
            data = self.get_national_industry(ALL_INDUSTRIES_CODE, year=test_year)

            if 'error' in data:
                # Try one year earlier if latest year not yet available
                test_year -= 1
                data = self.get_national_industry(ALL_INDUSTRIES_CODE, year=test_year)

            return {
                'status': 'ok' if 'error' not in data else 'partial',
                'source': 'BLS QCEW',
                'authenticated': False,
                'note': 'No API key required',
                'test_year': test_year,
                'test_result': {
                    'employment': data.get('employment'),
                    'avg_weekly_wage': data.get('avg_weekly_wage'),
                    'establishments': data.get('establishments'),
                },
            }
        except Exception as e:
            return {
                'status': 'error',
                'source': 'BLS QCEW',
                'error': str(e),
            }
