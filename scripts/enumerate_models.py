"""Top-down model enumeration pipeline.

Instead of discovering models bottom-up from signals, this script:
1. Runs SectorScreener to get ALL qualifying NAICS sectors with data
2. Loads existing models and maps coverage (sector × architecture)
3. For each uncovered sector, determines applicable architecture types
4. Generates model stubs with preliminary 5-axis score estimates
5. Outputs candidates for Agent B to flesh out

The goal: systematically expand from 293 models by ensuring every
qualifying sector × applicable architecture combination is considered.
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectors.sector_screener import SectorScreener

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 10 canonical architecture types
ARCHITECTURES = [
    'acquire_and_modernize',
    'rollup_consolidation',
    'full_service_replacement',
    'data_compounding',
    'platform_infrastructure',
    'vertical_saas',
    'marketplace_network',
    'regulatory_moat_builder',
    'physical_production_ai',
    'arbitrage_window',
]

# NAICS 2-digit sectors that have Silver Tsunami exposure (owner age >55)
SILVER_TSUNAMI_SECTORS = {
    '11',  # Agriculture
    '23',  # Construction
    '31', '32', '33',  # Manufacturing
    '42',  # Wholesale
    '44', '45',  # Retail
    '48', '49',  # Transportation
    '53',  # Real Estate
    '56',  # Administrative/Support
    '72',  # Accommodation/Food
    '81',  # Other Services
}

# NAICS 2-digit sectors with heavy regulation
REGULATED_SECTORS = {
    '22',  # Utilities
    '52',  # Finance/Insurance
    '62',  # Healthcare
    '92',  # Public Administration
}

# NAICS codes where regulatory moat applies at 4-digit
REGULATED_4DIGIT = {
    '5411',  # Legal
    '5412',  # Accounting
    '5413',  # Architecture/Engineering
    '6211', '6212', '6213', '6214', '6215', '6216', '6219',  # Healthcare providers
    '5221', '5222', '5223',  # Financial intermediation
    '5241', '5242',  # Insurance
    '4881', '4882', '4883', '4884', '4885',  # Transportation support
    '2361', '2362',  # Construction (licensed)
    '2211', '2212', '2213',  # Utilities
}

# Manufacturing NAICS ranges (physical production AI applicable)
MANUFACTURING_SECTORS = {'31', '32', '33', '11', '21'}

# Sectors where marketplace/network architectures make sense
# (fragmented supply AND demand, matchmaking creates value)
MARKETPLACE_SECTORS = {
    '23',  # Construction (contractor matching)
    '56',  # Administrative/Support (staffing)
    '54',  # Professional Services (expertise matching)
    '81',  # Other Services (local services)
    '72',  # Food/Accommodation (supply chain)
    '48',  # Transportation (logistics)
    '42',  # Wholesale (B2B matching)
}

# Force vectors by NAICS 2-digit sector
# Maps sector -> list of (force_id, contribution_score) tuples
SECTOR_FORCES = {
    '11': [('F1', 7), ('F2', 6), ('F6', 7), ('F4', 5)],
    '21': [('F6', 8), ('F3', 7), ('F1', 5), ('F4', 6)],
    '22': [('F6', 8), ('F1', 6), ('F3', 5), ('F4', 5)],
    '23': [('F2', 8), ('F1', 6), ('F4', 7), ('F5', 5)],
    '31': [('F1', 8), ('F2', 7), ('F3', 7), ('F4', 6), ('F6', 5)],
    '32': [('F1', 8), ('F2', 7), ('F3', 7), ('F4', 6), ('F6', 5)],
    '33': [('F1', 8), ('F2', 7), ('F3', 7), ('F4', 6), ('F6', 5)],
    '42': [('F1', 7), ('F2', 7), ('F4', 6), ('F3', 5)],
    '44': [('F1', 7), ('F2', 6), ('F4', 5), ('F5', 6)],
    '45': [('F1', 7), ('F2', 6), ('F4', 5), ('F5', 6)],
    '48': [('F1', 6), ('F2', 7), ('F3', 6), ('F6', 6)],
    '49': [('F1', 7), ('F2', 6), ('F3', 5), ('F4', 5)],
    '51': [('F1', 9), ('F4', 6), ('F3', 5), ('F5', 5)],
    '52': [('F1', 9), ('F4', 7), ('F3', 6), ('F5', 6)],
    '53': [('F2', 7), ('F4', 7), ('F1', 6), ('F5', 5)],
    '54': [('F1', 8), ('F2', 6), ('F4', 6), ('F5', 6)],
    '56': [('F1', 8), ('F2', 7), ('F4', 6)],
    '61': [('F1', 7), ('F2', 6), ('F5', 7), ('F3', 5)],
    '62': [('F2', 8), ('F1', 7), ('F5', 7), ('F4', 6), ('F3', 5)],
    '71': [('F1', 6), ('F5', 6), ('F2', 5)],
    '72': [('F2', 7), ('F1', 6), ('F4', 5), ('F5', 5)],
    '81': [('F2', 7), ('F1', 7), ('F4', 5)],
    '92': [('F1', 6), ('F3', 7), ('F5', 6), ('F2', 5)],
}

# Default CE (Capital Efficiency) by architecture type
ARCH_CE_DEFAULTS = {
    'acquire_and_modernize': 5.5,   # Capital intensive
    'rollup_consolidation': 4.5,    # Very capital intensive
    'full_service_replacement': 7.0, # AI-first, lean
    'data_compounding': 7.5,        # Software margins
    'platform_infrastructure': 6.0, # Moderate build cost
    'vertical_saas': 8.0,           # SaaS economics
    'marketplace_network': 7.5,     # Low capex, network effects
    'regulatory_moat_builder': 6.5, # Compliance build cost
    'physical_production_ai': 5.0,  # Hardware + AI
    'arbitrage_window': 7.0,        # Timing-dependent
}

# Default EC (External Context) by NAICS 2-digit
SECTOR_EC_DEFAULTS = {
    '11': 6.0,  # Agriculture — international trade exposure
    '21': 7.0,  # Mining — energy geopolitics
    '22': 5.0,  # Utilities — domestic
    '23': 5.0,  # Construction — domestic
    '31': 7.5,  # Manufacturing — supply chain
    '32': 7.0,  # Manufacturing
    '33': 8.0,  # Manufacturing — tech/defense
    '42': 6.0,  # Wholesale
    '44': 5.5,  # Retail
    '45': 5.5,  # Retail
    '48': 6.5,  # Transportation
    '49': 5.5,  # Warehousing
    '51': 6.0,  # Information
    '52': 7.0,  # Finance — international
    '53': 5.0,  # Real estate — domestic
    '54': 6.0,  # Professional services
    '56': 5.5,  # Administrative
    '61': 5.5,  # Education
    '62': 6.0,  # Healthcare — pharma/device imports
    '71': 5.0,  # Arts/Entertainment
    '72': 5.0,  # Accommodation/Food
    '81': 5.0,  # Other Services
    '92': 6.5,  # Government — defense/geopolitics
}


# ---------------------------------------------------------------------------
# Architecture applicability rules
# ---------------------------------------------------------------------------

def get_applicable_architectures(sector: dict) -> List[str]:
    """Determine which architecture types apply to a given sector.

    Uses sector data (fragmentation, Baumol score, NAICS code, employment
    trends) to determine which of the 10 canonical architectures are viable.

    Returns list of applicable architecture type strings.
    """
    code = sector['industry_code']
    naics_2d = code[:2]
    frag = sector.get('fragmentation_proxy', 0)
    baumol = sector.get('baumol_score', 1.0)
    wage_growth = sector.get('wage_growth_yoy', 0)
    emp_growth = sector.get('emp_growth_yoy', 0)
    employment = sector.get('annual_avg_emplvl', 0)
    establishments = sector.get('annual_avg_estabs', 0)

    applicable = []

    # 1. acquire_and_modernize: fragmented + Silver Tsunami exposure
    if (frag > 0.08 and naics_2d in SILVER_TSUNAMI_SECTORS
            and establishments > 1000):
        applicable.append('acquire_and_modernize')

    # 2. rollup_consolidation: highly fragmented + large enough for roll-up
    if (frag > 0.12 and establishments > 3000 and employment > 30000):
        applicable.append('rollup_consolidation')

    # 3. full_service_replacement: Baumol stored energy
    if baumol > 1.15 and wage_growth > -0.02:
        applicable.append('full_service_replacement')

    # 4. data_compounding: recurring relationships + data value
    # Most service sectors qualify; exclude pure retail/manufacturing
    if (naics_2d in {'54', '52', '62', '61', '56', '81', '53', '48'}
            and employment > 20000):
        applicable.append('data_compounding')

    # 5. platform_infrastructure: skip — this is cross-sector, not per-sector

    # 6. vertical_saas: workflow complexity + fragmentation
    if frag > 0.04 and employment > 20000 and baumol > 0.9:
        applicable.append('vertical_saas')

    # 7. marketplace_network: fragmented supply + demand matching
    if (naics_2d in MARKETPLACE_SECTORS and frag > 0.06
            and establishments > 2000):
        applicable.append('marketplace_network')

    # 8. regulatory_moat_builder: regulated sector
    if (naics_2d in REGULATED_SECTORS
            or code in REGULATED_4DIGIT
            or code[:4] in REGULATED_4DIGIT):
        applicable.append('regulatory_moat_builder')

    # 9. physical_production_ai: manufacturing/physical sectors
    if naics_2d in MANUFACTURING_SECTORS:
        applicable.append('physical_production_ai')

    # 10. arbitrage_window: declining employment or distressed sector
    if emp_growth < -0.01 or (baumol > 1.5 and wage_growth > 0.04):
        applicable.append('arbitrage_window')

    return applicable


# ---------------------------------------------------------------------------
# Preliminary scoring
# ---------------------------------------------------------------------------

def estimate_scores(sector: dict, architecture: str) -> dict:
    """Estimate preliminary 5-axis scores from sector data.

    These are rough estimates to prioritize which model stubs deserve
    full Agent B analysis. Not meant to be final ratings.
    """
    code = sector['industry_code']
    naics_2d = code[:2]
    baumol = sector.get('baumol_score', 1.0)
    frag = sector.get('fragmentation_proxy', 0)
    wage_growth = sector.get('wage_growth_yoy', 0)
    emp_growth = sector.get('emp_growth_yoy', 0)
    employment = sector.get('annual_avg_emplvl', 0)
    composite = sector.get('composite_score', 0)

    # --- SN (Structural Necessity) ---
    # Based on Baumol stored energy + employment size + fragmentation
    sn_baumol = min(baumol * 2.5, 7.0)   # Wage premium → demand
    sn_size = min(employment / 500000, 2.0)  # Large markets → more necessity
    sn_frag = min(frag * 8, 1.5)          # Fragmentation → acquisition target
    sn = min(round(sn_baumol + sn_size + sn_frag, 1), 10.0)
    sn = max(sn, 3.0)  # Floor

    # Architecture adjustments to SN
    if architecture == 'acquire_and_modernize':
        sn = min(sn + 0.5, 10.0)  # Silver Tsunami creates structural demand
    elif architecture == 'full_service_replacement' and baumol > 1.5:
        sn = min(sn + 0.5, 10.0)  # High stored energy

    # --- FA (Force Alignment) ---
    forces = SECTOR_FORCES.get(naics_2d, [('F1', 5)])
    # Count forces with contribution >= 6
    strong_forces = sum(1 for _, score in forces if score >= 6)
    # Weighted score
    force_sum = sum(score for _, score in forces)
    fa = min(round(strong_forces * 1.5 + force_sum / len(forces) * 0.3, 1), 10.0)
    fa = max(fa, 3.0)

    # --- EC (External Context) ---
    ec = SECTOR_EC_DEFAULTS.get(naics_2d, 5.5)
    # Adjust for architecture
    if architecture == 'physical_production_ai':
        ec = min(ec + 1.0, 10.0)  # Supply chain / geopolitics
    elif architecture == 'regulatory_moat_builder':
        ec = min(ec + 0.5, 10.0)  # Regulatory contagion

    # --- TG (Timing Grade) ---
    # Based on wage growth trajectory, employment trend, Baumol
    tg = 6.0  # Default: acceptable timing
    if wage_growth > 0.04:
        tg += 1.0  # Cost pressure accelerating = good entry timing
    if emp_growth < -0.01:
        tg += 0.5  # Sector contracting = disruption window open
    if baumol > 1.5:
        tg += 0.5  # High stored energy = ready now
    if architecture == 'arbitrage_window':
        tg += 1.0  # By definition, timing-sensitive
    elif architecture == 'acquire_and_modernize':
        tg += 0.5  # Silver Tsunami = time-limited window
    tg = min(round(tg, 1), 10.0)

    # --- CE (Capital Efficiency) ---
    ce = ARCH_CE_DEFAULTS.get(architecture, 6.0)
    # SaaS/marketplace in high-margin sectors get a boost
    if architecture in ('vertical_saas', 'data_compounding') and baumol > 1.3:
        ce = min(ce + 0.5, 10.0)

    # Composite
    composite_score = round(
        (sn * 25 + fa * 25 + ec * 20 + tg * 15 + ce * 15) / 10, 2
    )

    return {
        'SN': round(sn, 1),
        'FA': round(fa, 1),
        'EC': round(ec, 1),
        'TG': round(tg, 1),
        'CE': round(ce, 1),
        'composite': composite_score,
    }


def classify_category(scores: dict) -> Tuple[str, List[str]]:
    """Apply category classification rules to scores.

    Returns (primary_category, all_categories).
    """
    sn = scores['SN']
    fa = scores['FA']
    ec = scores['EC']
    tg = scores['TG']
    ce = scores['CE']
    composite = scores['composite']

    categories = []

    if sn >= 8.0 and fa >= 8.0:
        categories.append('STRUCTURAL_WINNER')
    if fa >= 7.0 and 'STRUCTURAL_WINNER' not in categories:
        categories.append('FORCE_RIDER')
    if tg >= 8.0 and sn >= 6.0:
        categories.append('TIMING_ARBITRAGE')
    if ce >= 8.0 and sn >= 6.0:
        categories.append('CAPITAL_MOAT')
    # FEAR_ECONOMY and EMERGING_CATEGORY require signal-level data,
    # can't be determined from sector stats alone

    if not categories:
        if composite >= 60:
            categories.append('CONDITIONAL')
        else:
            categories.append('PARKED')

    return categories[0], categories


# ---------------------------------------------------------------------------
# Model stub generation
# ---------------------------------------------------------------------------

def generate_model_name(sector: dict, architecture: str) -> str:
    """Generate a descriptive model name from sector + architecture."""
    title = sector.get('industry_title', '')
    # Clean up NAICS prefix
    if title.startswith('NAICS '):
        title = title.split(' ', 2)[-1] if len(title.split(' ', 2)) > 2 else title

    arch_labels = {
        'acquire_and_modernize': 'Acquire + Modernize',
        'rollup_consolidation': 'Roll-Up Platform',
        'full_service_replacement': 'AI-First',
        'data_compounding': 'Data Compounding',
        'platform_infrastructure': 'Platform',
        'vertical_saas': 'Vertical SaaS for',
        'marketplace_network': 'Marketplace for',
        'regulatory_moat_builder': 'Compliance Platform for',
        'physical_production_ai': 'AI-Augmented',
        'arbitrage_window': 'Arbitrage Play in',
    }
    label = arch_labels.get(architecture, architecture)

    # Build name
    # Truncate long titles
    if len(title) > 50:
        title = title[:47] + '...'

    if architecture in ('vertical_saas', 'marketplace_network',
                        'regulatory_moat_builder', 'arbitrage_window'):
        return f'{label} {title}'
    elif architecture == 'full_service_replacement':
        return f'{label} {title} Service'
    elif architecture == 'acquire_and_modernize':
        return f'{label} {title} Business'
    elif architecture == 'rollup_consolidation':
        return f'{title} {label}'
    elif architecture == 'physical_production_ai':
        return f'{label} {title}'
    elif architecture == 'data_compounding':
        return f'{title} {label} Engine'
    else:
        return f'{title} ({label})'


def generate_one_liner(sector: dict, architecture: str) -> str:
    """Generate a brief description of the model concept."""
    code = sector['industry_code']
    title = sector.get('industry_title', '')
    if title.startswith('NAICS '):
        title = title.split(' ', 2)[-1] if len(title.split(' ', 2)) > 2 else title

    baumol = sector.get('baumol_score', 1.0)
    employment = sector.get('annual_avg_emplvl', 0)
    establishments = sector.get('annual_avg_estabs', 0)

    templates = {
        'acquire_and_modernize': (
            f'Acquire retiring-owner {title.lower()} businesses '
            f'({establishments:,} establishments, aging owners) '
            f'and modernize with AI operations'
        ),
        'rollup_consolidation': (
            f'Consolidate fragmented {title.lower()} sector '
            f'({establishments:,} establishments) into AI-driven platform '
            f'with shared back-office'
        ),
        'full_service_replacement': (
            f'AI-first replacement for traditional {title.lower()} '
            f'({baumol:.1f}x wage premium = ${employment * sector.get("avg_annual_pay", 0) / 1e9:.0f}B stored energy)'
        ),
        'data_compounding': (
            f'Build compounding data asset from {title.lower()} client '
            f'interactions; value grows with each engagement'
        ),
        'vertical_saas': (
            f'Workflow SaaS for {title.lower()} firms '
            f'({establishments:,} potential customers), replacing '
            f'manual processes with AI automation'
        ),
        'marketplace_network': (
            f'Two-sided marketplace matching {title.lower()} supply '
            f'with demand, AI-powered matching and fulfillment'
        ),
        'regulatory_moat_builder': (
            f'Compliance and regulatory platform for {title.lower()}, '
            f'turning regulatory complexity into competitive moat'
        ),
        'physical_production_ai': (
            f'Integrate AI + robotics into {title.lower()} production; '
            f'cobots + predictive quality + autonomous scheduling'
        ),
        'arbitrage_window': (
            f'Time-limited entry into {title.lower()} during '
            f'structural transition; acquire displaced capacity at discount'
        ),
    }

    liner = templates.get(architecture, f'AI-driven business in {title.lower()}')
    return liner[:200]  # Cap length


def generate_forces(sector: dict, architecture: str) -> List[str]:
    """Determine which macro forces drive this model."""
    naics_2d = sector['industry_code'][:2]
    forces = SECTOR_FORCES.get(naics_2d, [('F1', 5)])
    # Return force IDs with contribution >= 5
    return [f for f, score in forces if score >= 5]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_existing_models(path: str) -> Tuple[List[dict], Set[str]]:
    """Load existing models and return coverage set.

    Returns:
        (models_list, coverage_set) where coverage_set contains
        strings like "5239:full_service_replacement" for each
        sector×architecture already covered.
    """
    with open(path, 'r') as f:
        data = json.load(f)

    models = data.get('models', [])
    coverage = set()

    # Normalize architecture names to canonical types
    arch_map = {
        'platform': 'platform_infrastructure',
        'service_platform': 'full_service_replacement',
        'marketplace_platform': 'marketplace_network',
        'marketplace': 'marketplace_network',
        'product_platform': 'platform_infrastructure',
        'network_platform': 'marketplace_network',
        'physical_product_platform': 'physical_production_ai',
        'infrastructure_platform': 'platform_infrastructure',
        'academy_platform': 'platform_infrastructure',
        'platform_service': 'full_service_replacement',
        'product': 'platform_infrastructure',
        'service': 'full_service_replacement',
        'project_development': 'full_service_replacement',
    }

    for m in models:
        naics = str(m.get('sector_naics', ''))
        if len(naics) >= 4:
            naics_4d = naics[:4]
        else:
            continue

        arch = m.get('architecture', '')
        canonical_arch = arch_map.get(arch, arch)
        if canonical_arch in ARCHITECTURES:
            coverage.add(f'{naics_4d}:{canonical_arch}')

    return models, coverage


def run_enumeration(
    models_path: str,
    year: str = '2023',
    min_employment: int = 5000,
    naics_level: int = 4,
    output_path: str = None,
) -> dict:
    """Run the full enumeration pipeline.

    Args:
        models_path: Path to existing normalized models JSON.
        year: QCEW data year.
        min_employment: Minimum employment to qualify.
        naics_level: NAICS digit level (4 or 6).
        output_path: Where to write results.

    Returns:
        Dict with enumeration results.
    """
    # Step 1: Load existing coverage
    logger.info('Loading existing models from %s', models_path)
    existing_models, coverage = load_existing_models(models_path)
    logger.info('Existing coverage: %d sector×architecture combinations',
                len(coverage))

    # Step 2: Screen all sectors
    logger.info('Running SectorScreener...')
    screener = SectorScreener()
    all_sectors = screener.screen_all_sectors(
        year=year, min_employment=min_employment, naics_level=naics_level
    )
    logger.info('SectorScreener returned %d qualifying sectors', len(all_sectors))

    # Step 3: For each sector, determine applicable architectures
    # and generate stubs for uncovered combinations
    new_stubs = []
    coverage_gaps = []
    sectors_with_gaps = 0
    total_possible = 0
    stub_id = 1

    for sector in all_sectors:
        code = sector['industry_code']
        applicable = get_applicable_architectures(sector)
        total_possible += len(applicable)

        sector_has_gap = False
        for arch in applicable:
            key = f'{code}:{arch}'
            if key not in coverage:
                sector_has_gap = True
                # Generate model stub
                scores = estimate_scores(sector, arch)
                primary_cat, all_cats = classify_category(scores)
                forces = generate_forces(sector, arch)

                stub = {
                    'id': f'ENUM-{naics_level}D-{stub_id:04d}',
                    'name': generate_model_name(sector, arch),
                    'sector_naics': code,
                    'sector_name': sector.get('industry_title', ''),
                    'architecture': arch,
                    'one_liner': generate_one_liner(sector, arch),
                    'forces': forces,
                    'scores': {
                        'SN': scores['SN'],
                        'FA': scores['FA'],
                        'EC': scores['EC'],
                        'TG': scores['TG'],
                        'CE': scores['CE'],
                    },
                    'composite': scores['composite'],
                    'primary_category': primary_cat,
                    'category': all_cats,
                    'source': 'enumeration_pipeline',
                    'status': 'stub',
                    'sector_data': {
                        'baumol_score': sector.get('baumol_score', 0),
                        'employment': sector.get('annual_avg_emplvl', 0),
                        'establishments': sector.get('annual_avg_estabs', 0),
                        'avg_annual_pay': sector.get('avg_annual_pay', 0),
                        'wage_growth_yoy': sector.get('wage_growth_yoy', 0),
                        'emp_growth_yoy': sector.get('emp_growth_yoy', 0),
                        'fragmentation_proxy': sector.get('fragmentation_proxy', 0),
                        'screener_composite': sector.get('composite_score', 0),
                        'screener_rank': sector.get('rank', 0),
                    },
                }
                new_stubs.append(stub)
                stub_id += 1
            else:
                coverage_gaps.append({
                    'sector': code,
                    'architecture': arch,
                    'status': 'already_covered',
                })

        if sector_has_gap:
            sectors_with_gaps += 1

    # Step 4: Sort stubs by composite score
    new_stubs.sort(key=lambda s: s['composite'], reverse=True)

    # Assign ranks
    for i, stub in enumerate(new_stubs):
        stub['enum_rank'] = i + 1

    # Step 5: Compile results
    cat_dist = Counter(s['primary_category'] for s in new_stubs)
    arch_dist = Counter(s['architecture'] for s in new_stubs)
    score_stats = {
        'max': max(s['composite'] for s in new_stubs) if new_stubs else 0,
        'min': min(s['composite'] for s in new_stubs) if new_stubs else 0,
        'mean': round(sum(s['composite'] for s in new_stubs) / len(new_stubs), 2) if new_stubs else 0,
    }

    results = {
        'enumeration_date': datetime.now().isoformat(),
        'parameters': {
            'year': year,
            'min_employment': min_employment,
            'naics_level': naics_level,
            'existing_models': len(existing_models),
            'existing_coverage_combos': len(coverage),
        },
        'summary': {
            'sectors_screened': len(all_sectors),
            'total_possible_combinations': total_possible,
            'already_covered': len(coverage),
            'new_stubs_generated': len(new_stubs),
            'sectors_with_gaps': sectors_with_gaps,
            'category_distribution': dict(cat_dist),
            'architecture_distribution': dict(arch_dist),
            'score_stats': score_stats,
        },
        'top_50': [
            {
                'rank': s['enum_rank'],
                'id': s['id'],
                'name': s['name'],
                'sector_naics': s['sector_naics'],
                'architecture': s['architecture'],
                'composite': s['composite'],
                'primary_category': s['primary_category'],
                'scores': s['scores'],
            }
            for s in new_stubs[:50]
        ],
        'stubs': new_stubs,
    }

    # Step 6: Write output
    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info('Results written to %s (%d stubs)', output_path, len(new_stubs))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    models_path = os.path.join(
        PROJECT_ROOT, 'data', 'verified', 'v3-4_normalized_2026-02-11.json'
    )

    if not os.path.exists(models_path):
        logger.error('Models file not found: %s', models_path)
        sys.exit(1)

    today = datetime.now().strftime('%Y-%m-%d')

    # Run 4-digit enumeration
    print('=' * 80)
    print('MODEL ENUMERATION PIPELINE')
    print('Systematically identifying uncovered sector × architecture combinations')
    print('=' * 80)
    print()

    output_4d = os.path.join(
        PROJECT_ROOT, 'data', 'verified', f'enumerated_4digit_{today}.json'
    )
    results_4d = run_enumeration(
        models_path=models_path,
        year='2023',
        min_employment=5000,
        naics_level=4,
        output_path=output_4d,
    )

    s = results_4d['summary']
    print(f'\n=== 4-DIGIT NAICS ENUMERATION ===')
    print(f'Sectors screened:          {s["sectors_screened"]}')
    print(f'Total possible combos:     {s["total_possible_combinations"]}')
    print(f'Already covered:           {s["already_covered"]}')
    print(f'NEW stubs generated:       {s["new_stubs_generated"]}')
    print(f'Sectors with gaps:         {s["sectors_with_gaps"]}')
    print(f'Score range:               {s["score_stats"]["min"]:.1f} - {s["score_stats"]["max"]:.1f}')
    print(f'Mean composite:            {s["score_stats"]["mean"]:.1f}')
    print()

    print('Category distribution:')
    for cat, count in sorted(s['category_distribution'].items(),
                             key=lambda x: -x[1]):
        print(f'  {cat}: {count}')
    print()

    print('Architecture distribution:')
    for arch, count in sorted(s['architecture_distribution'].items(),
                              key=lambda x: -x[1]):
        print(f'  {arch}: {count}')
    print()

    print('Top 20 new model stubs:')
    print(f'{"Rank":>4}  {"Composite":>9}  {"Category":<20}  {"NAICS":>6}  '
          f'{"Architecture":<28}  {"Name"}')
    print('-' * 120)
    for stub in results_4d['top_50'][:20]:
        print(f'{stub["rank"]:>4}  '
              f'{stub["composite"]:>9.1f}  '
              f'{stub["primary_category"]:<20}  '
              f'{stub["sector_naics"]:>6}  '
              f'{stub["architecture"]:<28}  '
              f'{stub["name"][:50]}')

    print(f'\nResults saved to: {output_4d}')
    print()

    # Run 6-digit enumeration
    print('=' * 80)
    print('>>> Phase 2: 6-digit NAICS enumeration (granular)')
    print('=' * 80)

    output_6d = os.path.join(
        PROJECT_ROOT, 'data', 'verified', f'enumerated_6digit_{today}.json'
    )
    results_6d = run_enumeration(
        models_path=models_path,
        year='2023',
        min_employment=5000,
        naics_level=6,
        output_path=output_6d,
    )

    s6 = results_6d['summary']
    print(f'\n=== 6-DIGIT NAICS ENUMERATION ===')
    print(f'Sub-industries screened:   {s6["sectors_screened"]}')
    print(f'Total possible combos:     {s6["total_possible_combinations"]}')
    print(f'Already covered:           {s6["already_covered"]}')
    print(f'NEW stubs generated:       {s6["new_stubs_generated"]}')
    print(f'Score range:               {s6["score_stats"]["min"]:.1f} - {s6["score_stats"]["max"]:.1f}')
    print(f'Mean composite:            {s6["score_stats"]["mean"]:.1f}')
    print()

    print('Top 20 new model stubs (6-digit):')
    print(f'{"Rank":>4}  {"Composite":>9}  {"Category":<20}  {"NAICS":>6}  '
          f'{"Architecture":<28}  {"Name"}')
    print('-' * 120)
    for stub in results_6d['top_50'][:20]:
        print(f'{stub["rank"]:>4}  '
              f'{stub["composite"]:>9.1f}  '
              f'{stub["primary_category"]:<20}  '
              f'{stub["sector_naics"]:>6}  '
              f'{stub["architecture"]:<28}  '
              f'{stub["name"][:50]}')

    print(f'\nResults saved to: {output_6d}')

    # Combined summary
    total_new = s['new_stubs_generated'] + s6['new_stubs_generated']
    total_existing = len(json.load(open(models_path))['models'])
    print()
    print('=' * 80)
    print(f'TOTAL: {total_existing} existing + {total_new} new stubs = '
          f'{total_existing + total_new} model candidates')
    print('Next step: Agent B reviews top stubs, fleshes out model cards')
    print('=' * 80)


if __name__ == '__main__':
    main()
