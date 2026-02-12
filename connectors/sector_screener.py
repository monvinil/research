"""Data-driven sector screening system.

Replaces LLM brainstorming for sector discovery with a systematic screen
of every NAICS sub-industry in the US economy. Pulls real employment,
wage, and establishment data from federal statistical agencies and computes
composite opportunity scores for agentic disruption potential.

Data sources:
  1. BLS QCEW (no key) -- employment, wages, establishments for ALL NAICS codes
  2. Census CBP (key)  -- establishment size distribution (fragmentation)
  3. BEA GDP-by-Industry (key) -- value added / productivity context

The core insight: industries with HIGH wages, LARGE employment, and HIGH
fragmentation (many small firms) are the richest targets for AI-driven
roll-up or displacement. This screener finds them mechanically rather
than relying on human intuition about which sectors "seem" ripe.
"""

import csv
import io
import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from .config import CENSUS_API_KEY, BEA_API_KEY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QCEW_BASE_URL = 'https://data.bls.gov/cew/data/api'
CENSUS_CBP_URL = 'https://api.census.gov/data/2022/cbp'
BEA_BASE_URL = 'https://apps.bea.gov/api/data'

# QCEW own_code: 5 = private sector (exclude government)
PRIVATE_OWN_CODE = '5'

# QCEW agglvl_code reference — national totals by NAICS level (US000 area)
# For national-level private-sector data (own_code=5, area_fips=US000):
#   11 = total all industries
#   14 = NAICS 2-digit sector
#   15 = NAICS 3-digit subsector
#   16 = NAICS 4-digit industry group
#   17 = NAICS 5-digit industry
#   18 = NAICS 6-digit US industry
AGGLVL_CODES = {
    3: '15',   # 3-digit NAICS subsector, national private
    4: '16',   # 4-digit NAICS industry group, national private
    5: '17',   # 5-digit NAICS industry, national private
    6: '18',   # 6-digit NAICS US industry, national private
}

# Census CBP establishment size codes
EMPSZES_CODES = {
    '001': 'All establishments',
    '212': '1-4 employees',
    '220': '5-9 employees',
    '230': '10-19 employees',
    '241': '20-49 employees',
    '242': '50-99 employees',
    '251': '100-249 employees',
    '252': '250-499 employees',
    '254': '500-999 employees',
    '260': '1000+ employees',
}

# Small firm size codes (fewer than 20 employees)
SMALL_FIRM_CODES = {'212', '220', '230'}

# Composite score weights
WEIGHTS = {
    'wage_premium':        0.30,   # Baumol score: avg pay / economy avg
    'market_size':         0.20,   # log10(employment) normalized
    'fragmentation_proxy': 0.20,   # establishments per employee
    'absolute_pay':        0.15,   # raw pay level (higher = more stored energy)
    'establishment_count': 0.15,   # raw establishment count (market breadth)
}

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
QCEW_CACHE_TTL_HOURS = 168  # 7 days — annual data, doesn't change often


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(val, default=0):
    """Convert a value to int, returning default on failure."""
    try:
        return int(str(val).replace(',', '').strip())
    except (ValueError, TypeError, AttributeError):
        return default


def _safe_float(val, default=0.0):
    """Convert a value to float, returning default on failure."""
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError, AttributeError):
        return default


def _normalize_01(values: List[float]) -> List[float]:
    """Min-max normalize a list of values to [0, 1]."""
    if not values:
        return values
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.5] * len(values)
    return [(v - lo) / span for v in values]


# ---------------------------------------------------------------------------
# QCEW CSV file cache (the CSV is ~50MB, avoid re-downloading)
# ---------------------------------------------------------------------------

class _QCEWFileCache:
    """Caches raw QCEW CSV text on disk so we only download once per year."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, year: str) -> str:
        return os.path.join(self.cache_dir, f'qcew_national_{year}.csv')

    def _meta_path(self, year: str) -> str:
        return os.path.join(self.cache_dir, f'qcew_national_{year}.meta.json')

    def get(self, year: str) -> Optional[str]:
        """Return cached CSV text if fresh enough, else None."""
        path = self._path(year)
        meta_path = self._meta_path(year)
        if not os.path.exists(path) or not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            fetched_at = meta.get('fetched_at', 0)
            age_hours = (time.time() - fetched_at) / 3600
            if age_hours > QCEW_CACHE_TTL_HOURS:
                return None
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except (OSError, json.JSONDecodeError):
            return None

    def put(self, year: str, csv_text: str):
        """Store CSV text and metadata."""
        path = self._path(year)
        meta_path = self._meta_path(year)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(csv_text)
            with open(meta_path, 'w') as f:
                json.dump({'fetched_at': time.time(), 'year': year}, f)
        except OSError as exc:
            logger.warning('QCEW cache write failed: %s', exc)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SectorScreener:
    """Data-driven sector discovery -- screens every NAICS sub-industry.

    Instead of brainstorming "which industries might be disrupted by AI?",
    this class downloads the full universe of US private-sector industries
    from BLS and mechanically scores each one on dimensions that predict
    agentic disruption opportunity:

        1. Wage premium (Baumol cost disease stored energy)
        2. Market size (total employment)
        3. Fragmentation (many small establishments = acquirable/disruptable)
        4. Absolute pay level (total addressable labor cost)
        5. Establishment breadth (number of firms in the market)

    Usage:
        screener = SectorScreener()
        top = screener.get_top_candidates(n=50)
        for sector in top:
            print(sector['industry_code'], sector['industry_title'],
                  f"score={sector['composite_score']:.3f}")
    """

    def __init__(self, census_api_key: str = None, bea_api_key: str = None,
                 cache_dir: str = CACHE_DIR):
        self.census_api_key = census_api_key or CENSUS_API_KEY
        self.bea_api_key = bea_api_key or BEA_API_KEY
        self._qcew_cache = _QCEWFileCache(cache_dir)
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'EconResearchEngine/1.0 (sector-screener)',
        })
        self._naics_titles: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # 0. NAICS industry title lookup
    # ------------------------------------------------------------------

    def _load_naics_titles(self):
        """Download BLS industry titles CSV (one-time, ~160KB).

        The QCEW CSV does NOT include industry_title, so we need this
        reference table to map industry_code -> human-readable name.
        """
        if self._naics_titles:
            return  # Already loaded

        url = 'https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv'
        try:
            resp = self._session.get(url, timeout=30)
            resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                code = row.get('industry_code', '').strip()
                title = row.get('industry_title', '').strip()
                # Remove the leading code prefix from titles (e.g. "5411 Legal services" -> "Legal services")
                if title.startswith(code):
                    title = title[len(code):].strip().lstrip('-').strip()
                self._naics_titles[code] = title
            logger.info('Loaded %d NAICS industry titles.', len(self._naics_titles))
        except requests.RequestException as exc:
            logger.warning('Could not load NAICS titles: %s', exc)

    def _get_title(self, industry_code: str) -> str:
        """Look up human-readable title for a NAICS code."""
        self._load_naics_titles()
        return self._naics_titles.get(industry_code, industry_code)

    # ------------------------------------------------------------------
    # 1. BLS QCEW — bulk national data (no API key needed)
    # ------------------------------------------------------------------

    def get_qcew_national(self, year: str = '2023') -> List[dict]:
        """Download national QCEW data for ALL industries.

        Returns parsed CSV rows filtered to private sector (own_code=5).
        The CSV contains every NAICS code at every aggregation level with
        employment, wages, and establishment counts.

        The CSV is ~50MB and is cached on disk after first download.
        """
        # Check disk cache first
        csv_text = self._qcew_cache.get(year)

        if csv_text is None:
            url = f'{QCEW_BASE_URL}/{year}/a/area/US000.csv'
            logger.info('Downloading QCEW national data for %s (may take a minute)...', year)
            try:
                resp = self._session.get(url, timeout=120)
                resp.raise_for_status()
                csv_text = resp.text
                self._qcew_cache.put(year, csv_text)
                logger.info('QCEW download complete (%d bytes), cached to disk.', len(csv_text))
            except requests.RequestException as exc:
                logger.error('Failed to download QCEW data for %s: %s', year, exc)
                raise RuntimeError(
                    f'Could not download QCEW data for {year}. '
                    f'URL: {url} -- Error: {exc}'
                ) from exc

        # Parse CSV, filter to private sector
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = []
        for row in reader:
            if row.get('own_code', '').strip() == PRIVATE_OWN_CODE:
                rows.append(row)

        logger.info('QCEW %s: %d private-sector rows parsed.', year, len(rows))
        return rows

    def _filter_qcew_by_naics_level(self, rows: List[dict],
                                      naics_level: int = 4) -> List[dict]:
        """Filter QCEW rows to a specific NAICS digit level.

        Uses agglvl_code to select the right aggregation level:
          4-digit NAICS -> agglvl_code = 74
          5-digit NAICS -> agglvl_code = 76
          6-digit NAICS -> agglvl_code = 78
        """
        target_agglvl = AGGLVL_CODES.get(naics_level)
        if target_agglvl is None:
            raise ValueError(
                f'Unsupported naics_level={naics_level}. '
                f'Supported: {list(AGGLVL_CODES.keys())}'
            )

        filtered = []
        for row in rows:
            if row.get('agglvl_code', '').strip() == target_agglvl:
                filtered.append(row)
        return filtered

    # ------------------------------------------------------------------
    # 2. Census CBP — establishment size distribution (fragmentation)
    # ------------------------------------------------------------------

    def get_cbp_fragmentation(self, naics_code: str,
                               year: str = '2022') -> Optional[dict]:
        """Get establishment size distribution for a specific NAICS code.

        Returns a dict with:
          - size_distribution: {size_code: establishment_count}
          - small_firm_pct: fraction of establishments with <20 employees
          - total_establishments: total count
          - fragmentation_score: small_firm_pct (0-1, higher = more fragmented)

        Returns None if the API call fails or no data is available.
        Requires CENSUS_API_KEY.
        """
        if not self.census_api_key:
            logger.debug('No Census API key; skipping CBP fragmentation for %s', naics_code)
            return None

        params = {
            'get': 'ESTAB,EMP,PAYANN,EMPSZES,EMPSZES_LABEL',
            'for': 'us:*',
            'NAICS2017': naics_code,
            'key': self.census_api_key,
        }
        try:
            resp = self._session.get(
                f'https://api.census.gov/data/{year}/cbp',
                params=params, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.debug('CBP request failed for NAICS %s: %s', naics_code, exc)
            return None

        if not data or len(data) < 2:
            return None

        headers = data[0]
        size_dist = {}
        total_estabs = 0

        for row in data[1:]:
            entry = dict(zip(headers, row))
            size_code = entry.get('EMPSZES', '').strip()
            estab_count = _safe_int(entry.get('ESTAB', 0))
            size_dist[size_code] = estab_count
            if size_code == '001':
                total_estabs = estab_count

        if total_estabs == 0:
            return None

        small_count = sum(size_dist.get(code, 0) for code in SMALL_FIRM_CODES)
        small_pct = small_count / total_estabs if total_estabs > 0 else 0.0

        return {
            'naics_code': naics_code,
            'size_distribution': size_dist,
            'total_establishments': total_estabs,
            'small_firm_count': small_count,
            'small_firm_pct': round(small_pct, 4),
            'fragmentation_score': round(small_pct, 4),
        }

    # ------------------------------------------------------------------
    # 3. BEA GDP-by-Industry (enrichment, not required for core screen)
    # ------------------------------------------------------------------

    def get_bea_gdp_by_industry(self, year: str = '2023') -> dict:
        """Fetch GDP-by-industry value added data from BEA.

        Returns a dict mapping BEA industry code -> value added (billions $).
        Used for productivity enrichment of screened sectors.
        """
        if not self.bea_api_key:
            logger.debug('No BEA API key; skipping GDP-by-industry.')
            return {}

        params = {
            'UserID': self.bea_api_key,
            'method': 'GetData',
            'DataSetName': 'GDPbyIndustry',
            'TableID': '1',
            'Industry': 'ALL',
            'Frequency': 'A',
            'Year': year,
            'ResultFormat': 'JSON',
        }

        try:
            resp = self._session.get(BEA_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.debug('BEA GDP-by-industry request failed: %s', exc)
            return {}

        results = payload.get('BEAAPI', {}).get('Results', {})
        data_rows = results.get('Data', results.get('data', []))

        gdp_map = {}
        for row in data_rows:
            ind_code = row.get('Industry', '').strip()
            desc = row.get('IndustrYDescription',
                           row.get('IndustryDescription', '')).strip()
            val_str = row.get('DataValue', '').replace(',', '').strip()
            try:
                value = float(val_str)
            except (ValueError, TypeError):
                continue
            gdp_map[ind_code] = {
                'description': desc,
                'value_added_billions': value,
            }

        return gdp_map

    # ------------------------------------------------------------------
    # Scoring methods
    # ------------------------------------------------------------------

    @staticmethod
    def compute_baumol_score(avg_annual_pay: float,
                              economy_avg_pay: float) -> float:
        """Wage premium relative to economy average.

        A score > 1.0 means the sector pays above average (Baumol cost
        disease stored energy). Higher = more labor cost that can be
        displaced by AI.

        Returns:
            Ratio of sector avg pay to economy-wide avg pay.
        """
        if economy_avg_pay <= 0:
            return 0.0
        return avg_annual_pay / economy_avg_pay

    @staticmethod
    def compute_fragmentation_score(size_distribution: dict) -> float:
        """What fraction of the industry is small firms (<20 employees)?

        Higher score = more fragmented = more acquirable/disruptable.

        Args:
            size_distribution: dict of {empszes_code: establishment_count}

        Returns:
            Float in [0, 1] representing share of establishments that are small.
        """
        total = size_distribution.get('001', 0)
        if total <= 0:
            return 0.0

        small = sum(size_distribution.get(code, 0) for code in SMALL_FIRM_CODES)
        return small / total

    @staticmethod
    def compute_growth_score(current_employment: float,
                              prior_employment: float) -> float:
        """Employment trajectory -- growing, stable, or declining.

        Returns:
            Percentage change in employment. Positive = growing,
            negative = declining. Returns 0 if prior data unavailable.
        """
        if prior_employment <= 0:
            return 0.0
        return (current_employment - prior_employment) / prior_employment

    @staticmethod
    def _fragmentation_proxy(establishments: int, employment: int) -> float:
        """Compute establishments-per-employee ratio.

        Higher ratio means more fragmented (many firms per worker).
        This is a proxy when we don't have Census CBP size data.
        """
        if employment <= 0:
            return 0.0
        return establishments / employment

    # ------------------------------------------------------------------
    # Main screening pipeline
    # ------------------------------------------------------------------

    def screen_all_sectors(self, year: str = '2023',
                            min_employment: int = 5000,
                            naics_level: int = 4) -> List[dict]:
        """THE MAIN METHOD. Screens all NAICS codes at the specified level.

        Downloads the full QCEW national dataset, filters to the requested
        NAICS level and private sector, then computes a multi-factor composite
        score for each industry.

        For each sector computes:
          - baumol_score: wage premium (avg_annual_pay / economy average)
          - size_score: log10(employment) normalized to [0,1]
          - pay_score: absolute annual pay, normalized
          - fragmentation_proxy: establishments / employment ratio, normalized
          - estab_score: log10(establishments) normalized
          - wage_growth: YoY change if prior year data available
          - composite_score: weighted combination of all factors

        Args:
            year: Data year to screen (default '2023').
            min_employment: Filter out industries below this employment
                threshold. Default 5000 avoids noisy micro-sectors.
            naics_level: NAICS digit level to screen. 4, 5, or 6.

        Returns:
            List of dicts sorted descending by composite_score. Each dict
            contains the raw QCEW fields plus all computed scores.
        """
        # -- Step 1: Download and filter QCEW data --------------------------
        logger.info('Screening NAICS %d-digit sectors for %s (min emp=%d)...',
                     naics_level, year, min_employment)

        all_rows = self.get_qcew_national(year)
        sector_rows = self._filter_qcew_by_naics_level(all_rows, naics_level)
        logger.info('Filtered to %d %d-digit sectors.', len(sector_rows), naics_level)

        # -- Step 2: Try to get prior year for growth calculation -----------
        prior_year = str(int(year) - 1)
        prior_map = {}
        try:
            prior_rows = self.get_qcew_national(prior_year)
            prior_filtered = self._filter_qcew_by_naics_level(prior_rows, naics_level)
            for row in prior_filtered:
                code = row.get('industry_code', '').strip()
                emp = _safe_int(row.get('annual_avg_emplvl', 0))
                pay = _safe_int(row.get('avg_annual_pay', 0))
                if code and emp > 0:
                    prior_map[code] = {'employment': emp, 'avg_pay': pay}
            logger.info('Prior year (%s) loaded: %d sectors for growth calc.',
                         prior_year, len(prior_map))
        except Exception as exc:
            logger.warning('Could not load prior year %s for growth: %s',
                            prior_year, exc)

        # -- Step 3: Compute economy-wide average pay -----------------------
        #   Use the total private sector row (agglvl_code = 11, own_code = 5)
        economy_avg_pay = 0
        for row in all_rows:
            if (row.get('agglvl_code', '').strip() == '11' and
                    row.get('own_code', '').strip() == PRIVATE_OWN_CODE):
                economy_avg_pay = _safe_float(row.get('avg_annual_pay', 0))
                break

        if economy_avg_pay == 0:
            # Fallback: compute weighted average across all rows at this level
            total_wages = sum(_safe_float(r.get('total_annual_wages', 0))
                              for r in sector_rows)
            total_emp = sum(_safe_int(r.get('annual_avg_emplvl', 0))
                            for r in sector_rows)
            if total_emp > 0:
                economy_avg_pay = total_wages / total_emp
            else:
                economy_avg_pay = 60000  # Reasonable US private sector fallback

        logger.info('Economy average annual pay: $%.0f', economy_avg_pay)

        # -- Step 4: Build sector records and compute raw scores ------------
        # Load NAICS titles for human-readable names
        self._load_naics_titles()

        sectors = []
        for row in sector_rows:
            code = row.get('industry_code', '').strip()
            title = self._get_title(code)
            employment = _safe_int(row.get('annual_avg_emplvl', 0))
            establishments = _safe_int(row.get('annual_avg_estabs', 0))
            avg_pay = _safe_float(row.get('avg_annual_pay', 0))
            total_wages = _safe_float(row.get('total_annual_wages', 0))
            avg_wkly_wage = _safe_float(row.get('annual_avg_wkly_wage', 0))

            # Skip sub-threshold industries
            if employment < min_employment:
                continue

            # Skip unclassified / catch-all codes
            if code in ('10', '101', '1011', '1012', '1013', '1021', '1022',
                        '1023', '1024', '1025', '1026', '1027', '1028', '1029',
                        '99', '999', '9999', '99999', '999999', 'TOTAL'):
                continue

            # Baumol score
            baumol = self.compute_baumol_score(avg_pay, economy_avg_pay)

            # Fragmentation proxy
            frag_proxy = self._fragmentation_proxy(establishments, employment)

            # Employment growth
            prior = prior_map.get(code)
            wage_growth = 0.0
            emp_growth = 0.0
            if prior:
                emp_growth = self.compute_growth_score(
                    employment, prior['employment'])
                if prior['avg_pay'] > 0:
                    wage_growth = (avg_pay - prior['avg_pay']) / prior['avg_pay']

            sector = {
                # Identifiers
                'industry_code': code,
                'industry_title': title,
                # Raw data
                'annual_avg_emplvl': employment,
                'annual_avg_estabs': establishments,
                'avg_annual_pay': round(avg_pay, 2),
                'total_annual_wages': round(total_wages, 2),
                'annual_avg_wkly_wage': round(avg_wkly_wage, 2),
                # Computed scores (raw, pre-normalization)
                'baumol_score': round(baumol, 4),
                'fragmentation_proxy': round(frag_proxy, 6),
                'emp_growth_yoy': round(emp_growth, 4),
                'wage_growth_yoy': round(wage_growth, 4),
                # Log-scale for size scoring
                '_log_employment': math.log10(max(employment, 1)),
                '_log_establishments': math.log10(max(establishments, 1)),
            }
            sectors.append(sector)

        if not sectors:
            logger.warning('No sectors passed filters.')
            return []

        # -- Step 5: Normalize scores to [0, 1] across universe ------------
        baumol_vals = [s['baumol_score'] for s in sectors]
        log_emp_vals = [s['_log_employment'] for s in sectors]
        frag_vals = [s['fragmentation_proxy'] for s in sectors]
        pay_vals = [s['avg_annual_pay'] for s in sectors]
        log_estab_vals = [s['_log_establishments'] for s in sectors]

        norm_baumol = _normalize_01(baumol_vals)
        norm_log_emp = _normalize_01(log_emp_vals)
        norm_frag = _normalize_01(frag_vals)
        norm_pay = _normalize_01(pay_vals)
        norm_log_estab = _normalize_01(log_estab_vals)

        for i, sector in enumerate(sectors):
            sector['_norm_baumol'] = round(norm_baumol[i], 4)
            sector['_norm_size'] = round(norm_log_emp[i], 4)
            sector['_norm_frag'] = round(norm_frag[i], 4)
            sector['_norm_pay'] = round(norm_pay[i], 4)
            sector['_norm_estab'] = round(norm_log_estab[i], 4)

            composite = (
                WEIGHTS['wage_premium']        * norm_baumol[i] +
                WEIGHTS['market_size']         * norm_log_emp[i] +
                WEIGHTS['fragmentation_proxy'] * norm_frag[i] +
                WEIGHTS['absolute_pay']        * norm_pay[i] +
                WEIGHTS['establishment_count'] * norm_log_estab[i]
            )
            sector['composite_score'] = round(composite, 4)

            # Clean up internal fields
            del sector['_log_employment']
            del sector['_log_establishments']

        # -- Step 6: Sort by composite score descending ---------------------
        sectors.sort(key=lambda s: s['composite_score'], reverse=True)

        # Assign rank
        for i, sector in enumerate(sectors):
            sector['rank'] = i + 1

        logger.info('Screening complete: %d sectors scored and ranked.', len(sectors))
        return sectors

    # ------------------------------------------------------------------
    # Enrichment: CBP fragmentation overlay
    # ------------------------------------------------------------------

    def enrich_with_cbp(self, sectors: List[dict],
                         max_queries: int = 50) -> List[dict]:
        """Enrich top sectors with Census CBP establishment size data.

        Adds true fragmentation_score (% of firms with <20 employees)
        for the top sectors. Rate-limited to avoid hammering Census API.

        Args:
            sectors: Output of screen_all_sectors(), must be sorted by rank.
            max_queries: Maximum number of CBP API calls to make.

        Returns:
            The same list with cbp_fragmentation_score added where available.
        """
        if not self.census_api_key:
            logger.info('No Census API key; skipping CBP enrichment.')
            return sectors

        count = 0
        for sector in sectors:
            if count >= max_queries:
                break

            code = sector['industry_code']
            cbp = self.get_cbp_fragmentation(code)
            if cbp is not None:
                sector['cbp_fragmentation_score'] = cbp['fragmentation_score']
                sector['cbp_small_firm_pct'] = cbp['small_firm_pct']
                sector['cbp_total_establishments'] = cbp['total_establishments']
                count += 1

            # Be polite to the Census API
            time.sleep(0.2)

        logger.info('CBP enrichment: %d sectors enriched.', count)
        return sectors

    # ------------------------------------------------------------------
    # Top-level convenience method
    # ------------------------------------------------------------------

    def get_top_candidates(self, n: int = 50, year: str = '2023',
                            min_employment: int = 5000,
                            naics_level: int = 4,
                            enrich_cbp: bool = False) -> List[dict]:
        """Run full screen and return top N candidates with interpretation.

        This is the primary entry point. Downloads QCEW data, scores all
        sectors, and returns the most promising candidates for agentic
        disruption.

        Args:
            n: Number of top candidates to return.
            year: Data year.
            min_employment: Minimum employment threshold.
            naics_level: NAICS digit level (4, 5, or 6).
            enrich_cbp: If True, query Census CBP for size distribution
                on top candidates (requires CENSUS_API_KEY, slower).

        Returns:
            List of top N sector dicts with scores and interpretation.
        """
        all_sectors = self.screen_all_sectors(
            year=year, min_employment=min_employment, naics_level=naics_level
        )

        top = all_sectors[:n]

        if enrich_cbp:
            top = self.enrich_with_cbp(top, max_queries=n)

        # Add human-readable interpretation to each sector
        for sector in top:
            sector['interpretation'] = self._interpret(sector)

        return top

    def _interpret(self, sector: dict) -> str:
        """Generate a brief interpretation string for a sector result."""
        parts = []

        baumol = sector.get('baumol_score', 0)
        if baumol >= 1.5:
            parts.append(f'pays {baumol:.1f}x economy avg (high Baumol premium)')
        elif baumol >= 1.1:
            parts.append(f'pays {baumol:.1f}x economy avg (moderate premium)')
        else:
            parts.append(f'pays {baumol:.1f}x economy avg (below avg wages)')

        emp = sector.get('annual_avg_emplvl', 0)
        if emp >= 1_000_000:
            parts.append(f'{emp/1e6:.1f}M workers (massive market)')
        elif emp >= 100_000:
            parts.append(f'{emp/1e3:.0f}K workers (large market)')
        else:
            parts.append(f'{emp/1e3:.0f}K workers')

        estabs = sector.get('annual_avg_estabs', 0)
        if estabs >= 100_000:
            parts.append(f'{estabs/1e3:.0f}K establishments (highly fragmented)')
        elif estabs >= 10_000:
            parts.append(f'{estabs/1e3:.0f}K establishments')
        else:
            parts.append(f'{estabs:,} establishments')

        wage_g = sector.get('wage_growth_yoy', 0)
        if wage_g > 0.03:
            parts.append(f'wages rising {wage_g:.1%}/yr (widening AI advantage)')
        elif wage_g > 0:
            parts.append(f'wages up {wage_g:.1%}/yr')

        emp_g = sector.get('emp_growth_yoy', 0)
        if emp_g < -0.02:
            parts.append('employment declining (possible liquidation)')
        elif emp_g > 0.02:
            parts.append('employment growing (demand-driven)')

        cbp_frag = sector.get('cbp_fragmentation_score')
        if cbp_frag is not None:
            parts.append(f'{cbp_frag:.0%} of firms have <20 employees (CBP)')

        return '; '.join(parts)

    # ------------------------------------------------------------------
    # Summary / display helpers
    # ------------------------------------------------------------------

    def format_results_table(self, sectors: List[dict],
                              max_title_len: int = 45) -> str:
        """Format screening results as a readable text table."""
        if not sectors:
            return 'No sectors to display.'

        lines = []
        header = (
            f'{"Rank":>4}  {"NAICS":>6}  {"Score":>6}  '
            f'{"Baumol":>6}  {"AvgPay":>8}  {"Empl":>10}  {"Estabs":>8}  '
            f'{"FragProxy":>9}  {"WageGr":>6}  {"Title"}'
        )
        lines.append(header)
        lines.append('-' * len(header))

        for s in sectors:
            title = s.get('industry_title', '')
            if len(title) > max_title_len:
                title = title[:max_title_len - 3] + '...'

            line = (
                f'{s.get("rank", ""):>4}  '
                f'{s.get("industry_code", ""):>6}  '
                f'{s.get("composite_score", 0):>6.3f}  '
                f'{s.get("baumol_score", 0):>6.2f}  '
                f'${s.get("avg_annual_pay", 0):>7,.0f}  '
                f'{s.get("annual_avg_emplvl", 0):>10,}  '
                f'{s.get("annual_avg_estabs", 0):>8,}  '
                f'{s.get("fragmentation_proxy", 0):>9.5f}  '
                f'{s.get("wage_growth_yoy", 0):>5.1%}  '
                f'{title}'
            )
            lines.append(line)

        return '\n'.join(lines)

    def to_json(self, sectors: List[dict], path: str = None) -> str:
        """Serialize results to JSON. Optionally write to file."""
        output = json.dumps(sectors, indent=2, default=str)
        if path:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w') as f:
                f.write(output)
            logger.info('Results written to %s', path)
        return output

    def summary_stats(self, sectors: List[dict]) -> dict:
        """Compute summary statistics over screened sectors."""
        if not sectors:
            return {}

        pays = [s['avg_annual_pay'] for s in sectors]
        emps = [s['annual_avg_emplvl'] for s in sectors]
        scores = [s['composite_score'] for s in sectors]

        return {
            'sectors_screened': len(sectors),
            'avg_composite_score': round(sum(scores) / len(scores), 4),
            'median_avg_pay': round(sorted(pays)[len(pays) // 2], 2),
            'total_employment': sum(emps),
            'top_score': round(max(scores), 4),
            'bottom_score': round(min(scores), 4),
            'avg_pay_range': (round(min(pays), 2), round(max(pays), 2)),
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Run the sector screener and print top 50 results."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    print('=' * 80)
    print('SECTOR SCREENER -- Data-Driven Industry Discovery')
    print('Screening the entire US private sector economy for')
    print('agentic disruption opportunity...')
    print('=' * 80)
    print()

    screener = SectorScreener()

    # --- 4-digit NAICS screen (broad sectors) ---
    print('>>> Phase 1: 4-digit NAICS screen (broad industry groups)')
    print()

    top_4digit = screener.get_top_candidates(
        n=50, year='2023', min_employment=5000, naics_level=4,
    )

    if top_4digit:
        stats = screener.summary_stats(top_4digit)
        print(f'Sectors scored: {stats.get("sectors_screened", 0)}')
        print(f'Total employment covered (top 50): {stats.get("total_employment", 0):,}')
        print(f'Median avg pay: ${stats.get("median_avg_pay", 0):,.0f}')
        print(f'Score range: {stats.get("bottom_score", 0):.3f} '
              f'- {stats.get("top_score", 0):.3f}')
        print()
        print(screener.format_results_table(top_4digit))
        print()

        # Print interpretations for top 10
        print('-' * 80)
        print('TOP 10 INTERPRETATIONS:')
        print('-' * 80)
        for sector in top_4digit[:10]:
            print(f'\n#{sector["rank"]} {sector["industry_code"]} '
                  f'{sector["industry_title"]}')
            print(f'   Composite: {sector["composite_score"]:.3f}  |  '
                  f'Baumol: {sector["baumol_score"]:.2f}x  |  '
                  f'Pay: ${sector["avg_annual_pay"]:,.0f}  |  '
                  f'Employment: {sector["annual_avg_emplvl"]:,}')
            print(f'   {sector.get("interpretation", "")}')
    else:
        print('WARNING: No sectors returned. Check network connectivity.')

    # --- 6-digit NAICS drill-down (granular sub-industries) ---
    print()
    print('=' * 80)
    print('>>> Phase 2: 6-digit NAICS drill-down (granular sub-industries)')
    print()

    top_6digit = screener.get_top_candidates(
        n=50, year='2023', min_employment=5000, naics_level=6,
    )

    if top_6digit:
        stats6 = screener.summary_stats(top_6digit)
        print(f'Sub-industries scored: {stats6.get("sectors_screened", 0)}')
        print(f'Total employment covered (top 50): {stats6.get("total_employment", 0):,}')
        print()
        print(screener.format_results_table(top_6digit))
        print()

        print('-' * 80)
        print('TOP 10 INTERPRETATIONS (6-digit):')
        print('-' * 80)
        for sector in top_6digit[:10]:
            print(f'\n#{sector["rank"]} {sector["industry_code"]} '
                  f'{sector["industry_title"]}')
            print(f'   Composite: {sector["composite_score"]:.3f}  |  '
                  f'Baumol: {sector["baumol_score"]:.2f}x  |  '
                  f'Pay: ${sector["avg_annual_pay"]:,.0f}  |  '
                  f'Employment: {sector["annual_avg_emplvl"]:,}')
            print(f'   {sector.get("interpretation", "")}')
    else:
        print('WARNING: No 6-digit sectors returned.')

    # --- Save results to JSON ---
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'data', 'scans')
    os.makedirs(output_dir, exist_ok=True)

    if top_4digit:
        path_4 = os.path.join(output_dir, 'sector_screen_4digit.json')
        screener.to_json(top_4digit, path_4)
        print(f'\n4-digit results saved to {path_4}')

    if top_6digit:
        path_6 = os.path.join(output_dir, 'sector_screen_6digit.json')
        screener.to_json(top_6digit, path_6)
        print(f'6-digit results saved to {path_6}')

    print('\nDone.')


if __name__ == '__main__':
    main()
