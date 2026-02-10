"""Business Rotation Engine — systematic discovery of NEW business candidates.

Solves the structural problem identified in Cycle 10: the evaluation pipeline
is strong but the GENERATOR is weak. After Cycle 3, discovery stalled — the
engine kept re-grading the same opportunities instead of finding new ones.

The rotation engine applies the engine's own analytical principles (Baumol,
competitive density, three-layer framework, IO propagation) not just to
EVALUATE businesses but to GENERATE candidates across the full economy.

Design philosophy (from the "new sexy vs old sexy" thesis):
- Software without IP or compute is becoming less attractive
- IP and compute are the new exclusive club
- De-exclusivity is happening across previously "untouchable" businesses
- High-volume low-margin physical operations are an underexplored frontier
- The mechanism must NOT be limited to knowledge-work/SaaS logic

6 Discovery Channels:
    1. Baumol Inversion Scanner — highest stored energy across ALL sectors
    2. Kill Index Re-scan — three-layer framework on killed/parked sectors
    3. Physical Ops Complexity Scanner — high labor + coordination + low tech
    4. VC Anti-Portfolio Scanner — HIGH Baumol + LOW VC/startup density
    5. Regulatory De-exclusivity Scanner — AI eroding credential barriers
    6. Failure Archaeology — failed companies where ops complexity was too high pre-AI

Each channel uses Thompson Sampling (via MethodologyTracker) to allocate
exploration budget across channels based on which ones produce actionable
candidates.
"""

import json
import math
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / 'data'
STATE_PATH = DATA_DIR / 'context' / 'state.json'
SCAN_4DIGIT_PATH = DATA_DIR / 'scans' / 'sector_screen_4digit.json'
SCAN_6DIGIT_PATH = DATA_DIR / 'scans' / 'sector_screen_6digit.json'
OUTPUT_PATH = DATA_DIR / 'scans' / 'rotation_candidates.json'


# ---------------------------------------------------------------------------
# Known competitive density — sectors with significant VC/PE deployment.
# Source: engine's competitive density scans through Cycle 10.
# Values are estimated total deployed capital (millions USD).
# ---------------------------------------------------------------------------

KNOWN_VC_DENSITY = {
    # SATURATED (>$1B deployed)
    'construction': 3500,
    'translation': 2400,
    'freight_brokerage': 5800,
    'insurance_brokerage': 3500,
    'property_management': 1200,
    'legal_tech': 4300,
    'robo_advisory': 6600,
    'engineering_services': 3960,
    'staffing': 5000,
    'customer_support_tools': 5000,  # Tool layer — NOT service layer
    'real_estate_proptech': 3200,
    'executive_search': 2000,
    'accounting_back_office': 1500,
    'dental_tech': 800,
    # MODERATE ($200M-$1B)
    'veterinary_tech': 100,   # Service layer is sparse
    'wholesale_trade': 200,
    'commercial_insurance': 150,
    'trade_finance': 100,
    # SPARSE (<$200M) — these are the interesting ones
    'customer_support_service': 400,  # AI-native service layer
    'veterinary_practice_ops': 80,
    'pest_control': 30,
    'janitorial_commercial': 20,
    'landscaping_commercial': 25,
    'waste_management': 50,
    'laundry_industrial': 15,
    'food_service_contract': 40,
    'auto_repair': 60,
    'funeral_services': 10,
    'parking_management': 20,
    'elevator_maintenance': 15,
}


# ---------------------------------------------------------------------------
# Credential/license-gated sectors where AI may erode barriers.
# Each entry: (sector_name, barrier_type, de_exclusivity_driver, naics_prefix)
# ---------------------------------------------------------------------------

CREDENTIAL_GATED_SECTORS = [
    ('veterinary_services', 'DVM license', 'AI diagnostics reducing need for specialist interpretation', '5411'),
    ('dental_services', 'DDS license', 'AI-guided procedures, teledentistry for triage', '6212'),
    ('optometry', 'OD license', 'AI vision screening, online refraction tools', '6213'),
    ('pharmacy', 'PharmD license', 'AI drug interaction checking, automated dispensing', '4461'),
    ('physical_therapy', 'DPT license', 'AI-guided exercise, remote monitoring', '6214'),
    ('accounting_tax', 'CPA license', 'AI tax preparation, automated audit', '5412'),
    ('architecture', 'AIA license', 'AI-generated designs, parametric modeling', '5413'),
    ('real_estate_brokerage', 'RE license', 'AI property matching, automated transactions', '5312'),
    ('insurance_adjusting', 'adjuster license', 'AI damage assessment, claims automation', '5242'),
    ('pest_control', 'applicator license', 'AI pest identification, precision application', '5617'),
    ('home_inspection', 'inspector license', 'AI visual inspection, sensor-based assessment', '5413'),
    ('notary_services', 'notary commission', 'remote online notarization (RON) laws expanding', '5419'),
    ('commercial_driving', 'CDL license', 'autonomous vehicles eroding CDL requirement', '4841'),
    ('medical_coding', 'CPC certification', 'AI coding from clinical notes', '5611'),
    ('court_reporting', 'RPR certification', 'AI transcription replacing stenography', '5611'),
]


# ---------------------------------------------------------------------------
# Known failure patterns — companies that failed where AI might change the math.
# (company, sector, failure_year, failure_reason, ai_changes_what)
# ---------------------------------------------------------------------------

FAILURE_ARCHAEOLOGY_DB = [
    ('Homejoy', 'home_cleaning', 2015, 'unit economics: customer acquisition > LTV, contractor churn',
     'AI scheduling + quality matching could fix retention; lower CAC via AI-powered matching'),
    ('Exec', 'home_cleaning', 2014, 'coordination costs too high for on-demand model',
     'AI dispatch + dynamic pricing could make coordination profitable'),
    ('Cherry', 'car_wash_mobile', 2014, 'logistics costs killed unit economics at scale',
     'AI route optimization + demand prediction could fix logistics'),
    ('Washio', 'laundry_delivery', 2016, 'last-mile logistics + quality control at scale',
     'AI quality monitoring + route optimization; compute costs 1000x lower'),
    ('Shyp', 'shipping_logistics', 2018, 'manual coordination of pickups + packaging too expensive',
     'AI-automated logistics coordination, computer vision for packaging'),
    ('Sprig', 'food_delivery_prep', 2017, 'food prep + delivery ops complexity, thin margins',
     'AI demand forecasting + kitchen automation + delivery optimization'),
    ('Munchery', 'meal_delivery', 2019, 'inventory waste, delivery logistics, quality at scale',
     'AI demand prediction eliminates waste; route optimization cuts delivery cost'),
    ('Luxe', 'valet_parking', 2017, 'labor costs per transaction too high',
     'AI-coordinated parking + autonomous vehicle movement'),
    ('Zirtual', 'virtual_assistants', 2015, 'human VA costs > what customers would pay',
     'AI agents handle 80%+ of tasks that required human VAs'),
    ('Eaze', 'cannabis_delivery', 2023, 'regulatory + logistics complexity',
     'AI compliance automation + delivery optimization'),
    ('Convoy', 'freight_brokerage', 2023, 'unit economics at $900M funding level; broker margins too thin',
     'AI-first broker with minimal human overhead; BUT market is now saturated'),
    ('Bench', 'bookkeeping', 2024, 'scaling human bookkeepers + quality control',
     'AI handles 90%+ of bookkeeping; BUT Intuit moat remains'),
    ('Body Labs', 'body_scanning', 2017, 'niche market for 3D body scanning',
     'AI computer vision eliminates need for specialized hardware'),
    ('Daqri', 'industrial_AR', 2019, 'hardware costs + enterprise adoption too slow',
     'AI vision models on commodity hardware; enterprise AI adoption accelerating'),
    ('Farmstead', 'grocery_delivery', 2023, 'dark store operations + delivery economics',
     'AI inventory prediction + route optimization could fix unit economics'),
]


# ---------------------------------------------------------------------------
# Physical operations complexity indicators by NAICS 2-digit sector.
# Estimated: labor_intensity (0-10), coordination_complexity (0-10),
#            tech_adoption (0-10, higher = more digitized already)
# ---------------------------------------------------------------------------

PHYSICAL_OPS_PROFILES = {
    '23': {'name': 'Construction', 'labor': 9, 'coordination': 9, 'tech': 3},
    '31': {'name': 'Food Manufacturing', 'labor': 7, 'coordination': 6, 'tech': 5},
    '32': {'name': 'Non-Food Manufacturing', 'labor': 6, 'coordination': 7, 'tech': 6},
    '33': {'name': 'Machinery/Electronics Mfg', 'labor': 5, 'coordination': 8, 'tech': 7},
    '42': {'name': 'Wholesale Trade', 'labor': 5, 'coordination': 7, 'tech': 4},
    '44': {'name': 'Retail Trade', 'labor': 7, 'coordination': 5, 'tech': 6},
    '45': {'name': 'Retail (non-store)', 'labor': 6, 'coordination': 6, 'tech': 7},
    '48': {'name': 'Transportation', 'labor': 8, 'coordination': 9, 'tech': 4},
    '49': {'name': 'Warehousing', 'labor': 8, 'coordination': 7, 'tech': 5},
    '53': {'name': 'Real Estate', 'labor': 4, 'coordination': 6, 'tech': 5},
    '54': {'name': 'Professional Services', 'labor': 3, 'coordination': 4, 'tech': 8},
    '56': {'name': 'Admin/Support/Waste', 'labor': 8, 'coordination': 7, 'tech': 3},
    '61': {'name': 'Education', 'labor': 7, 'coordination': 5, 'tech': 5},
    '62': {'name': 'Healthcare', 'labor': 8, 'coordination': 8, 'tech': 5},
    '71': {'name': 'Arts/Entertainment', 'labor': 6, 'coordination': 6, 'tech': 4},
    '72': {'name': 'Accommodation/Food Svc', 'labor': 9, 'coordination': 7, 'tech': 3},
    '81': {'name': 'Other Services', 'labor': 7, 'coordination': 5, 'tech': 3},
}


class BusinessRotationEngine:
    """Systematic discovery of new business candidates via 6 channels.

    Each channel is an independent discovery method that produces candidates
    in a standard format compatible with the Agent A → C → B → Master pipeline.

    Usage:
        engine = BusinessRotationEngine()
        candidates = engine.run_rotation(max_per_channel=10)
        engine.save_candidates(candidates)
    """

    CHANNEL_IDS = [
        'baumol_inversion',
        'kill_rescan',
        'physical_ops',
        'vc_anti_portfolio',
        'regulatory_deexclusivity',
        'failure_archaeology',
    ]

    CHANNEL_NAMES = {
        'baumol_inversion': 'Baumol Inversion Scanner',
        'kill_rescan': 'Kill Index Re-scan (Three-Layer)',
        'physical_ops': 'Physical Ops Complexity Scanner',
        'vc_anti_portfolio': 'VC Anti-Portfolio Scanner',
        'regulatory_deexclusivity': 'Regulatory De-exclusivity Scanner',
        'failure_archaeology': 'Failure Archaeology',
    }

    def __init__(self):
        self.state = self._load_state()
        self.scan_4digit = self._load_json(SCAN_4DIGIT_PATH)
        self.scan_6digit = self._load_json(SCAN_6DIGIT_PATH)
        self._build_indices()

    @staticmethod
    def _load_json(path):
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _load_state(self):
        if STATE_PATH.exists():
            with open(STATE_PATH) as f:
                return json.load(f)
        return {}

    def _build_indices(self):
        """Build lookup indices from scan data for fast querying."""
        self._scan4_by_code = {}
        for s in (self.scan_4digit or []):
            code = s.get('industry_code', '')
            self._scan4_by_code[code] = s

        self._scan6_by_code = {}
        for s in (self.scan_6digit or []):
            code = s.get('industry_code', '')
            self._scan6_by_code[code] = s

    # ------------------------------------------------------------------
    # Pipeline state helpers
    # ------------------------------------------------------------------

    def _get_killed_sectors(self):
        """Extract killed sectors from state."""
        pipeline = self.state.get('opportunity_pipeline', {})
        return pipeline.get('killed', [])

    def _get_parked_sectors(self):
        """Extract parked sectors from state."""
        pipeline = self.state.get('opportunity_pipeline', {})
        return pipeline.get('parked', [])

    def _get_all_evaluated(self):
        """All sectors already in the pipeline (any status).

        Returns a set of distinctive keyword sets (frozensets) for matching.
        Uses only domain-specific words (>5 chars, not common stopwords)
        extracted from pipeline item names.
        """
        pipeline = self.state.get('opportunity_pipeline', {})
        # Common words to ignore — these appear in many NAICS titles
        stopwords = {
            'naics', 'other', 'services', 'management', 'activities',
            'related', 'general', 'miscellaneous', 'including', 'except',
            'professional', 'technical', 'commercial', 'industrial',
            'residential', 'wholesale', 'retail', 'financial', 'special',
            'trade', 'score', 'cycle', 'density', 'competitive', 'market',
            'deployed', 'failure', 'saturated', 'approaching', 'identified',
            'barrier', 'regulatory', 'incumbent', 'precedent',
        }

        evaluated_keywords = set()
        for status_key in ('pursue', 'investigate_further', 'scanning',
                           'grading', 'verification', 'verified',
                           'killed', 'parked', 'rejected_as_opportunity'):
            items = pipeline.get(status_key, [])
            for item in items:
                text = item.get('name', '') if isinstance(item, dict) else item
                # Extract the business name (before parenthetical notes)
                name = text.split('(')[0].strip().lower() if '(' in text else text.strip().lower()
                # Remove common prefixes/suffixes
                name = name.replace(' ai ', ' ').replace(' ai', '').rstrip()
                # Extract distinctive words
                words = {w for w in name.split() if len(w) > 3 and w not in stopwords}
                if words:
                    evaluated_keywords.add(frozenset(words))

        return evaluated_keywords

    def _is_evaluated(self, title):
        """Check if a sector title matches something already evaluated.

        Requires at least 2 distinctive words to match an evaluated item,
        or an exact match of a single distinctive keyword (>7 chars).
        """
        evaluated = self._get_all_evaluated()
        # Clean the title — remove "NAICS XXXX" prefix
        title_clean = title.lower()
        if title_clean.startswith('naics '):
            parts = title_clean.split(' ', 2)
            title_clean = parts[2] if len(parts) > 2 else title_clean

        title_words = {w for w in title_clean.split()
                       if len(w) > 3 and w not in {
                           'naics', 'other', 'services', 'management',
                           'activities', 'related', 'general', 'miscellaneous',
                           'including', 'except', 'professional', 'technical',
                           'commercial', 'industrial', 'residential', 'wholesale',
                           'retail', 'financial', 'special', 'trade',
                       }}

        for eval_keywords in evaluated:
            overlap = title_words & eval_keywords
            # Need 2+ words matching, or 1 long distinctive word
            if len(overlap) >= 2:
                return True
            if len(overlap) == 1:
                word = next(iter(overlap))
                if len(word) >= 8:  # e.g. "veterinary", "construction", "insurance"
                    return True

        return False

    # ------------------------------------------------------------------
    # Channel 1: Baumol Inversion Scanner
    # ------------------------------------------------------------------

    def channel_baumol_inversion(self, max_candidates=15):
        """Find sectors with highest Baumol stored energy across the FULL economy.

        Key insight: the original screener already computes Baumol scores, but
        the engine only looked at the top composite scores. Baumol inversion
        specifically targets HIGH wage premium + LOW productivity growth
        sectors that may NOT rank highly on composite (because they're small
        or unfragmented) but have massive per-unit disruption potential.

        Focuses on sectors the engine hasn't evaluated yet.
        """
        candidates = []

        # Use both 4-digit and 6-digit scans
        for scan, level in [(self.scan_4digit, '4-digit'), (self.scan_6digit, '6-digit')]:
            if not scan:
                continue

            # Sort by Baumol score (not composite) — this is the inversion
            by_baumol = sorted(scan, key=lambda s: s.get('baumol_score', 0), reverse=True)

            for sector in by_baumol:
                title = sector.get('industry_title', '')
                code = sector.get('industry_code', '')
                baumol = sector.get('baumol_score', 0)

                # Skip if already evaluated
                if self._is_evaluated(title):
                    continue

                # Baumol threshold: must be significantly above economy average
                if baumol < 1.3:
                    continue

                employment = sector.get('annual_avg_emplvl', 0)
                avg_pay = sector.get('avg_annual_pay', 0)
                estabs = sector.get('annual_avg_estabs', 0)

                # Compute disruption potential: baumol × log(employment)
                disruption_potential = baumol * math.log10(max(employment, 1))

                candidates.append({
                    'candidate_id': f'BR-BAUMOL-{code}',
                    'channel': 'baumol_inversion',
                    'naics_code': code,
                    'naics_level': level,
                    'name': sector.get('industry_title', code),
                    'baumol_score': round(baumol, 3),
                    'employment': employment,
                    'avg_annual_pay': round(avg_pay, 0),
                    'establishments': estabs,
                    'disruption_potential': round(disruption_potential, 2),
                    'composite_rank': sector.get('rank', 0),
                    'rationale': (
                        f'Baumol {baumol:.2f}x economy avg pay. '
                        f'{employment:,} workers at ${avg_pay:,.0f}/yr across {estabs:,} establishments. '
                        f'High stored energy suggests AI cost collapse opportunity.'
                    ),
                    'next_step': 'Competitive density scan + three-layer analysis',
                })

        # Sort by disruption potential, deduplicate by code
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: x['disruption_potential'], reverse=True):
            if c['naics_code'] not in seen:
                seen.add(c['naics_code'])
                unique.append(c)

        return unique[:max_candidates]

    # ------------------------------------------------------------------
    # Channel 2: Kill Index Re-scan
    # ------------------------------------------------------------------

    def channel_kill_rescan(self, max_candidates=10):
        """Re-examine killed and parked sectors using three-layer framework.

        Key insight (P-009): a sector that was killed for "competitive density"
        might only be dense at the TOOL layer. The SERVICE layer could be sparse.
        This is exactly what happened with Customer Support — tool layer $5B+
        saturated, but AI-native service layer <$500M.

        Applies the three-layer decomposition:
            Layer 1: Tool/platform layer (SaaS, APIs)
            Layer 2: Incumbent service layer (legacy providers)
            Layer 3: AI-native service layer (the actual opportunity)
        """
        candidates = []
        killed = self._get_killed_sectors()
        parked = self._get_parked_sectors()

        for item in killed + parked:
            text = item if isinstance(item, str) else item.get('name', '')

            # Extract the kill reason if available
            kill_reason = ''
            if '(' in text:
                kill_reason = text[text.index('('):]

            # Flag sectors killed specifically for competitive density
            density_killed = any(kw in text.lower() for kw in
                                 ['density', 'saturated', 'deployed', 'moat'])

            # Also flag parked sectors that might have a service layer gap
            service_gap_potential = any(kw in text.lower() for kw in
                                        ['staffing', 'consulting', 'brokerage',
                                         'management', 'services', 'operations'])

            if not (density_killed or service_gap_potential):
                continue

            candidates.append({
                'candidate_id': f'BR-RESCAN-{len(candidates):03d}',
                'channel': 'kill_rescan',
                'name': text.split('(')[0].strip() if '(' in text else text.strip() if isinstance(text, str) else text,
                'original_status': 'killed' if item in killed else 'parked',
                'original_reason': kill_reason,
                'density_killed': density_killed,
                'service_gap_potential': service_gap_potential,
                'rationale': (
                    f'Originally {"killed" if item in killed else "parked"} '
                    f'{"for competitive density" if density_killed else "with service-layer potential"}. '
                    f'Three-layer re-scan needed: tool layer may be saturated but '
                    f'AI-native service layer could be sparse (cf. Customer Support pattern).'
                ),
                'three_layer_questions': [
                    'What is the tool/platform layer competitive density?',
                    'What is the incumbent service layer? Who are the BPO/legacy providers?',
                    'Is there an AI-native service layer? How much capital deployed?',
                    'Is there a structural inversion barrier (P-010) preventing incumbents from going AI-first?',
                ],
                'next_step': 'Three-layer competitive density decomposition',
            })

        return candidates[:max_candidates]

    # ------------------------------------------------------------------
    # Channel 3: Physical Ops Complexity Scanner
    # ------------------------------------------------------------------

    def channel_physical_ops(self, max_candidates=15):
        """Find sectors with high physical operations complexity that AI could unlock.

        The "old sexy → new sexy" thesis: sectors that were untouchable because
        of physical coordination complexity are becoming accessible as AI handles
        scheduling, routing, quality control, and dispatch.

        Targets: HIGH labor intensity + HIGH coordination + LOW tech adoption.
        These are sectors where the coordination tax is the barrier, not the
        underlying economics.
        """
        candidates = []

        # Score each sector by physical ops opportunity
        for naics_2digit, profile in PHYSICAL_OPS_PROFILES.items():
            labor = profile['labor']
            coordination = profile['coordination']
            tech = profile['tech']

            # Physical ops opportunity = labor × coordination × (10 - tech_adoption)
            # Higher score = more labor, more coordination, less tech
            ops_opportunity = labor * coordination * (10 - tech)

            if ops_opportunity < 200:  # threshold for interesting
                continue

            # Find matching 4-digit subsectors from scan data
            matching_subsectors = []
            for code, sector in self._scan4_by_code.items():
                if code.startswith(naics_2digit):
                    title = sector.get('industry_title', '')
                    if self._is_evaluated(title):
                        continue
                    matching_subsectors.append(sector)

            # Sort subsectors by Baumol × employment (disruption value)
            matching_subsectors.sort(
                key=lambda s: s.get('baumol_score', 0) * math.log10(max(s.get('annual_avg_emplvl', 1), 1)),
                reverse=True,
            )

            for sector in matching_subsectors[:3]:  # Top 3 per 2-digit
                code = sector.get('industry_code', '')
                employment = sector.get('annual_avg_emplvl', 0)
                baumol = sector.get('baumol_score', 0)

                candidates.append({
                    'candidate_id': f'BR-PHYOPS-{code}',
                    'channel': 'physical_ops',
                    'naics_code': code,
                    'name': sector.get('industry_title', code),
                    'parent_sector': profile['name'],
                    'labor_intensity': labor,
                    'coordination_complexity': coordination,
                    'tech_adoption': tech,
                    'ops_opportunity_score': ops_opportunity,
                    'baumol_score': round(baumol, 3),
                    'employment': employment,
                    'rationale': (
                        f'{profile["name"]} subsector: labor={labor}/10, coordination={coordination}/10, '
                        f'tech={tech}/10. Ops opportunity score: {ops_opportunity}. '
                        f'AI could unlock coordination bottleneck — scheduling, routing, quality, dispatch.'
                    ),
                    'new_sexy_thesis': (
                        'Physical operations were "untouchable" due to coordination complexity. '
                        'AI handles the coordination layer, making the underlying economics accessible.'
                    ),
                    'next_step': 'Unit economics model + competitive density scan',
                })

        # Sort by ops_opportunity × baumol
        candidates.sort(
            key=lambda c: c['ops_opportunity_score'] * c.get('baumol_score', 1),
            reverse=True,
        )

        return candidates[:max_candidates]

    # ------------------------------------------------------------------
    # Channel 4: VC Anti-Portfolio Scanner
    # ------------------------------------------------------------------

    def channel_vc_anti_portfolio(self, max_candidates=15):
        """Find HIGH Baumol sectors with LOW VC/startup deployment.

        The anti-portfolio thesis: VCs have a cultural bias toward software,
        SaaS, and knowledge work. Sectors that are economically attractive
        (high Baumol, large market) but physically messy get systematically
        under-invested. These are the sectors where AI-native entrants face
        the least competition from well-funded startups.

        Uses known VC density data + scan Baumol scores.
        """
        candidates = []

        # Build a set of all sector names that have high VC density
        high_density_keywords = set()
        for sector_key, capital_mm in KNOWN_VC_DENSITY.items():
            if capital_mm >= 500:  # $500M+ = meaningful density
                for word in sector_key.split('_'):
                    if len(word) > 3:
                        high_density_keywords.add(word)

        for scan in [self.scan_4digit, self.scan_6digit]:
            if not scan:
                continue

            for sector in scan:
                title = sector.get('industry_title', '')
                title_lower = title.lower()
                code = sector.get('industry_code', '')
                baumol = sector.get('baumol_score', 0)
                employment = sector.get('annual_avg_emplvl', 0)

                # Must have meaningful Baumol stored energy
                if baumol < 1.2:
                    continue

                # Must have meaningful market size
                if employment < 10000:
                    continue

                # Skip already evaluated
                if self._is_evaluated(title):
                    continue

                # Check VC density — is this sector VC-neglected?
                title_words = set(title_lower.replace('-', ' ').replace('/', ' ').split())
                density_overlap = title_words & high_density_keywords
                if len(density_overlap) >= 2:
                    continue  # Likely in a high-density area

                # Estimate VC deployment for this sector
                estimated_vc = 0
                for key, capital in KNOWN_VC_DENSITY.items():
                    key_words = set(key.split('_'))
                    if key_words & title_words:
                        estimated_vc = max(estimated_vc, capital)

                # Anti-portfolio score: high Baumol × low VC density
                vc_penalty = min(1.0, estimated_vc / 1000) if estimated_vc > 0 else 0
                anti_portfolio_score = baumol * (1 - vc_penalty) * math.log10(max(employment, 1))

                if anti_portfolio_score < 3:  # threshold
                    continue

                candidates.append({
                    'candidate_id': f'BR-ANTIP-{code}',
                    'channel': 'vc_anti_portfolio',
                    'naics_code': code,
                    'name': title,
                    'baumol_score': round(baumol, 3),
                    'employment': employment,
                    'estimated_vc_density_mm': estimated_vc,
                    'anti_portfolio_score': round(anti_portfolio_score, 2),
                    'rationale': (
                        f'Baumol {baumol:.2f}x, {employment:,} workers, estimated VC density '
                        f'${estimated_vc}M. Anti-portfolio score: {anti_portfolio_score:.1f}. '
                        f'Economically attractive but VC-neglected — likely due to physical/messy operations.'
                    ),
                    'next_step': 'Validate VC density estimate + competitive landscape deep-dive',
                })

        # Sort by anti-portfolio score, deduplicate
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: x['anti_portfolio_score'], reverse=True):
            if c['naics_code'] not in seen:
                seen.add(c['naics_code'])
                unique.append(c)

        return unique[:max_candidates]

    # ------------------------------------------------------------------
    # Channel 5: Regulatory De-exclusivity Scanner
    # ------------------------------------------------------------------

    def channel_regulatory_deexclusivity(self, max_candidates=10):
        """Find sectors where AI is eroding credential/license barriers.

        The de-exclusivity thesis: for decades, certain sectors were protected
        by professional licensing requirements. AI is now performing tasks that
        required licensed professionals, creating a "de-exclusivity" wave.

        Two types of opportunity:
        1. Sectors where AI can work UNDER a licensed professional (fewer
           professionals needed per unit of output — scaling play)
        2. Sectors where regulatory changes allow AI to operate with reduced
           licensing requirements (barrier removal play)
        """
        candidates = []

        for sector_name, barrier, driver, naics_prefix in CREDENTIAL_GATED_SECTORS:
            # Look up QCEW data for this sector
            matching_sectors = []
            for code, data in self._scan4_by_code.items():
                if code.startswith(naics_prefix[:2]):
                    matching_sectors.append(data)
            for code, data in self._scan6_by_code.items():
                if code.startswith(naics_prefix[:3]):
                    matching_sectors.append(data)

            # Aggregate employment and pay
            total_emp = sum(s.get('annual_avg_emplvl', 0) for s in matching_sectors)
            avg_pay = (
                sum(s.get('avg_annual_pay', 0) * s.get('annual_avg_emplvl', 1) for s in matching_sectors) /
                max(total_emp, 1)
            ) if matching_sectors else 0

            # De-exclusivity score: barrier strength × market size × AI readiness
            barrier_strength = len(barrier)  # crude proxy — longer barrier description = more complex
            market_factor = math.log10(max(total_emp, 1)) if total_emp > 0 else 0

            deex_score = market_factor * (barrier_strength / 20)

            candidates.append({
                'candidate_id': f'BR-DEREG-{sector_name[:10].upper()}',
                'channel': 'regulatory_deexclusivity',
                'name': sector_name.replace('_', ' ').title(),
                'naics_prefix': naics_prefix,
                'credential_barrier': barrier,
                'de_exclusivity_driver': driver,
                'total_employment': total_emp,
                'avg_pay': round(avg_pay, 0),
                'deexclusivity_score': round(deex_score, 2),
                'rationale': (
                    f'Protected by {barrier}. De-exclusivity driver: {driver}. '
                    f'{total_emp:,} workers at ${avg_pay:,.0f}/yr. '
                    f'AI may allow fewer licensed professionals to cover more volume.'
                ),
                'opportunity_types': [
                    f'Scaling play: fewer {barrier} holders needed per unit output',
                    'Barrier removal: regulatory changes allowing AI substitution',
                    'Hybrid model: licensed professional supervises AI for more throughput',
                ],
                'next_step': 'Regulatory landscape scan + competitive density assessment',
            })

        candidates.sort(key=lambda c: c['deexclusivity_score'], reverse=True)
        return candidates[:max_candidates]

    # ------------------------------------------------------------------
    # Channel 6: Failure Archaeology
    # ------------------------------------------------------------------

    def channel_failure_archaeology(self, max_candidates=10):
        """Mine failed startups where operational complexity was too high pre-AI.

        The thesis: many startups failed in 2014-2023 because the human
        coordination overhead made unit economics impossible. With AI handling
        scheduling, dispatch, quality control, and customer communication,
        some of these economics may now work.

        Critical filter: only resurface failures where AI specifically addresses
        the failure mode. Exclude sectors that are now saturated (post-failure
        many others may have entered).
        """
        candidates = []

        for company, sector, year, reason, ai_fix in FAILURE_ARCHAEOLOGY_DB:
            # Check if sector is now saturated
            estimated_density = KNOWN_VC_DENSITY.get(sector, 0)
            if estimated_density > 1000:
                saturated = True
            else:
                saturated = False

            years_since = 2026 - year
            # Recency score: more recent failures are more relevant
            recency = min(1.0, years_since / 10)

            # AI advancement factor: how much better is AI now vs failure year
            ai_factor = min(2.0, 1.0 + (years_since * 0.15))

            archaeology_score = ai_factor * (1 - estimated_density / 5000)

            candidates.append({
                'candidate_id': f'BR-ARCH-{company[:8].upper()}',
                'channel': 'failure_archaeology',
                'failed_company': company,
                'sector': sector.replace('_', ' ').title(),
                'failure_year': year,
                'failure_reason': reason,
                'ai_changes_what': ai_fix,
                'years_since_failure': years_since,
                'sector_now_saturated': saturated,
                'estimated_current_density_mm': estimated_density,
                'archaeology_score': round(archaeology_score, 2),
                'rationale': (
                    f'{company} failed in {year}: {reason}. '
                    f'AI now addresses this: {ai_fix}. '
                    f'{"WARNING: sector now saturated." if saturated else "Sector density appears low."}'
                ),
                'viability_questions': [
                    f'Has the fundamental market demand changed since {year}?',
                    'Are the unit economics viable with AI handling the coordination layer?',
                    f'What competitive density exists now ({years_since} years post-failure)?',
                    'Is the failure pattern structural (market doesn\'t exist) or operational (too hard to execute)?',
                ],
                'next_step': 'Unit economics remodel with AI cost structure',
            })

        # Filter out saturated sectors for primary ranking, keep them flagged
        candidates.sort(
            key=lambda c: (not c['sector_now_saturated'], c['archaeology_score']),
            reverse=True,
        )

        return candidates[:max_candidates]

    # ------------------------------------------------------------------
    # Main rotation execution
    # ------------------------------------------------------------------

    def run_rotation(self, max_per_channel=10):
        """Execute all 6 channels and compile results.

        Returns:
            dict with channel results and summary statistics
        """
        logger.info('Running Business Rotation Engine — 6 channels...')
        now = datetime.now().isoformat()

        results = {}
        total_candidates = 0

        channel_methods = {
            'baumol_inversion': self.channel_baumol_inversion,
            'kill_rescan': self.channel_kill_rescan,
            'physical_ops': self.channel_physical_ops,
            'vc_anti_portfolio': self.channel_vc_anti_portfolio,
            'regulatory_deexclusivity': self.channel_regulatory_deexclusivity,
            'failure_archaeology': self.channel_failure_archaeology,
        }

        for channel_id in self.CHANNEL_IDS:
            method = channel_methods[channel_id]
            try:
                candidates = method(max_candidates=max_per_channel)
                results[channel_id] = {
                    'channel_name': self.CHANNEL_NAMES[channel_id],
                    'candidates_found': len(candidates),
                    'candidates': candidates,
                }
                total_candidates += len(candidates)
                logger.info('  Channel %s: %d candidates', channel_id, len(candidates))
            except Exception as exc:
                logger.error('  Channel %s FAILED: %s', channel_id, exc)
                results[channel_id] = {
                    'channel_name': self.CHANNEL_NAMES[channel_id],
                    'candidates_found': 0,
                    'candidates': [],
                    'error': str(exc),
                }

        # Cross-channel deduplication and scoring
        all_candidates = []
        seen_names = set()
        for channel_id, channel_result in results.items():
            for candidate in channel_result['candidates']:
                name_key = candidate.get('name', '').lower().strip()
                naics_key = candidate.get('naics_code', '')
                dedup_key = naics_key or name_key
                if dedup_key and dedup_key not in seen_names:
                    seen_names.add(dedup_key)
                    all_candidates.append(candidate)

        output = {
            'rotation_id': f'rotation_{now[:10]}',
            'generated_at': now,
            'engine_cycle': self.state.get('current_cycle', 0),
            'channels': results,
            'summary': {
                'total_candidates_raw': total_candidates,
                'total_candidates_deduped': len(all_candidates),
                'by_channel': {
                    cid: r['candidates_found']
                    for cid, r in results.items()
                },
                'channels_successful': sum(
                    1 for r in results.values() if r['candidates_found'] > 0
                ),
                'channels_failed': sum(
                    1 for r in results.values() if 'error' in r
                ),
            },
            'top_candidates': sorted(
                all_candidates,
                key=lambda c: c.get('disruption_potential',
                                    c.get('anti_portfolio_score',
                                          c.get('ops_opportunity_score',
                                                c.get('archaeology_score',
                                                      c.get('deexclusivity_score', 0))))),
                reverse=True,
            )[:20],
        }

        logger.info('Rotation complete: %d raw, %d deduped candidates from %d channels.',
                     total_candidates, len(all_candidates),
                     output['summary']['channels_successful'])

        return output

    def save_candidates(self, rotation_output, path=None):
        """Write rotation results to JSON."""
        out_path = Path(path) if path else OUTPUT_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(rotation_output, f, indent=2, default=str)
        logger.info('Rotation candidates saved to %s', out_path)
        return str(out_path)

    def format_summary(self, rotation_output):
        """Human-readable summary of rotation results."""
        lines = []
        lines.append('=' * 72)
        lines.append('BUSINESS ROTATION ENGINE — Candidate Discovery Report')
        lines.append(f'Generated: {rotation_output.get("generated_at", "?")}')
        lines.append(f'Engine Cycle: {rotation_output.get("engine_cycle", "?")}')
        lines.append('=' * 72)

        summary = rotation_output.get('summary', {})
        lines.append(f'\nTotal candidates: {summary.get("total_candidates_raw", 0)} raw, '
                     f'{summary.get("total_candidates_deduped", 0)} after dedup')
        lines.append(f'Channels successful: {summary.get("channels_successful", 0)}/6')
        lines.append('')

        for channel_id, channel_data in rotation_output.get('channels', {}).items():
            name = channel_data.get('channel_name', channel_id)
            count = channel_data.get('candidates_found', 0)
            lines.append(f'--- {name} ({count} candidates) ---')

            for i, c in enumerate(channel_data.get('candidates', [])[:5], 1):
                cname = c.get('name', c.get('failed_company', '?'))
                score_keys = ['disruption_potential', 'anti_portfolio_score',
                              'ops_opportunity_score', 'archaeology_score',
                              'deexclusivity_score']
                score = next((c[k] for k in score_keys if k in c), 0)
                lines.append(f'  {i}. {cname} (score: {score})')
                lines.append(f'     {c.get("rationale", "")[:120]}')

            if count > 5:
                lines.append(f'  ... and {count - 5} more')
            lines.append('')

        # Top 10 overall
        lines.append('=' * 72)
        lines.append('TOP 10 CANDIDATES (cross-channel)')
        lines.append('=' * 72)
        for i, c in enumerate(rotation_output.get('top_candidates', [])[:10], 1):
            channel = c.get('channel', '?')
            cname = c.get('name', c.get('failed_company', '?'))
            lines.append(f'\n{i}. [{channel}] {cname}')
            lines.append(f'   {c.get("rationale", "")[:160]}')
            lines.append(f'   Next: {c.get("next_step", "N/A")}')

        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Run the rotation engine and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    engine = BusinessRotationEngine()
    rotation = engine.run_rotation(max_per_channel=10)
    engine.save_candidates(rotation)
    print(engine.format_summary(rotation))


if __name__ == '__main__':
    main()
