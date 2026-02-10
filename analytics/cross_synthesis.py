"""Cross-domain theory synthesis — combine methodologies into novel composite frameworks.

The research engine's biggest breakthroughs come from combining methods across
categories. Baumol stored energy alone is useful; Baumol x Bass diffusion x
Geographic arbitrage produces a much sharper question: "Where is stored energy
highest AND adoption in 10-20% phase AND geographic wage gap exploitable?"

This module systematically generates, scores, and tracks cross-domain
methodology combinations to accelerate discovery of novel research questions.

Uses the MethodologyTracker's success rate data to weight toward proven methods
while reserving exploration capacity for untested combinations.
"""

import json
import math
import random
import hashlib
import itertools
from pathlib import Path
from datetime import datetime


DEFAULT_TRACKER_PATH = Path(__file__).parent.parent / 'data' / 'context' / 'methodology_tracker.json'
DEFAULT_SYNTHESIS_PATH = Path(__file__).parent.parent / 'data' / 'context' / 'cross_synthesis_tracker.json'

# Known data connectors — used to score feasibility of combinations.
# If a combination requires data we can actually pull, it scores higher.
AVAILABLE_DATA_CONNECTORS = {
    'fred', 'bls_qcew', 'bls_oes', 'census_cbp', 'bea_io_tables',
    'edgar_sec', 'eurostat', 'oecd', 'world_bank', 'web_search',
    'equity_prices', 'naics_lookup',
}

# Built-in combination templates — seed the system with proven cross-domain ideas.
BUILTIN_TEMPLATES = {
    'baumol_x_bass_x_geo': {
        'name': 'Baumol stored energy x Bass adoption phase x Geographic arbitrage',
        'methods': ['baumol_cost_disease', 'bass_diffusion_scurve', 'geographic_arbitrage'],
        'cross_domain_question': (
            'Where is stored energy highest AND adoption in 10-20% phase '
            'AND geographic wage gap exploitable?'
        ),
        'falsifiable_prediction': (
            'Sectors with Baumol >1.5x, Bass adoption 5-20%, and >3x international '
            'wage gap will produce the best risk-adjusted AI startup opportunities.'
        ),
        'data_needed': ['fred', 'bls_qcew', 'bls_oes', 'eurostat', 'world_bank'],
        'sectors_to_test': [
            'professional_services', 'veterinary', 'wholesale_brokerage',
            'management_consulting',
        ],
    },
    'coase_x_minsky_x_pe': {
        'name': 'Coasean collapse x Minsky moment x PE vulnerability',
        'methods': ['baumol_cost_disease', 'equity_market_signals', 'edgar_filing_analysis'],
        'cross_domain_question': (
            'Which PE roll-ups overpaid for coordination labor that AI is eliminating? '
            'Where is the Minsky moment — the point where debt-financed acquisitions '
            'of human-labor firms become unserviceable as AI collapses the value?'
        ),
        'falsifiable_prediction': (
            'PE-backed professional services roll-ups with >4x leverage and >60% '
            'labor cost share will underperform market by >20% within 24 months.'
        ),
        'data_needed': ['edgar_sec', 'equity_prices', 'fred'],
        'sectors_to_test': [
            'accounting_firms', 'staffing_agencies', 'insurance_brokerages',
            'consulting_firms',
        ],
    },
    'sir_adoption_x_density': {
        'name': 'Epidemiological SIR adoption x Competitive density',
        'methods': ['bass_diffusion_scurve', 'competitive_density_scan'],
        'cross_domain_question': (
            'Model AI adoption as infection: which firm-size segments are most '
            '"susceptible" to AI, and where is the R0 highest? Cross with '
            'competitive density to find where the infection is spreading '
            'fastest but startups haven NOT arrived yet.'
        ),
        'falsifiable_prediction': (
            'Firm-size segments with 10-49 employees in low-density sectors will '
            'show the highest "R0" (peer-to-peer adoption rate) because they are '
            'large enough to benefit but small enough to switch fast.'
        ),
        'data_needed': ['census_cbp', 'web_search', 'bls_qcew'],
        'sectors_to_test': [
            'veterinary', 'wholesale_brokerage', 'property_management',
            'dental_practices',
        ],
    },
    'beveridge_x_equity_x_timing': {
        'name': 'Beveridge structural mismatch x Equity market signals x Timing arbitrage windows',
        'methods': ['macro_indicator_screening', 'equity_market_signals', 'timing_arbitrage_analysis'],
        'cross_domain_question': (
            'Where does the Beveridge Curve show structural mismatch (jobs unfilled '
            'despite unemployment), equity markets are already pricing labor depreciation, '
            'AND companies are prematurely cutting humans (creating a vacuum)?'
        ),
        'falsifiable_prediction': (
            'Sectors where Beveridge mismatch is above-average, sector ETFs declined >15%, '
            'and companies publicly cut staff will show a 12-month vacuum where '
            'service quality degrades — creating entry windows.'
        ),
        'data_needed': ['fred', 'equity_prices', 'web_search'],
        'sectors_to_test': [
            'customer_support', 'staffing', 'professional_services',
            'government_services',
        ],
    },
    'io_propagation_x_screener': {
        'name': 'IO table disruption propagation x Bottom-up NAICS screener',
        'methods': ['io_table_propagation', 'bottom_up_screener'],
        'cross_domain_question': (
            'If the bottom-up screener identifies high-Baumol sectors being disrupted, '
            'which DOWNSTREAM industries (via IO linkages) will be affected next? '
            'Can we find second-order opportunities before the market prices them?'
        ),
        'falsifiable_prediction': (
            'Industries with >5% input dependency on disrupted sectors will show '
            'employment declines with a 6-12 month lag after the upstream disruption.'
        ),
        'data_needed': ['bea_io_tables', 'bls_qcew', 'census_cbp'],
        'sectors_to_test': [
            'office_supplies', 'commercial_real_estate', 'business_travel',
            'corporate_training',
        ],
    },
    'shift_share_x_international': {
        'name': 'Shift-share decomposition x International comparison',
        'methods': ['shift_share_decomposition', 'international_comparison'],
        'cross_domain_question': (
            'Use shift-share to decompose US employment changes into national, '
            'industry, and regional effects. Then compare with international data: '
            'is the industry effect US-specific or global? If US-specific, why?'
        ),
        'falsifiable_prediction': (
            'Industries where the US "competitive share" component is negative '
            '(underperforming the global industry trend) are being disrupted by '
            'AI faster domestically — these are the leading-edge opportunities.'
        ),
        'data_needed': ['bls_qcew', 'eurostat', 'oecd', 'world_bank'],
        'sectors_to_test': [
            'translation_services', 'customer_support', 'accounting',
            'legal_services',
        ],
    },
}


class CrossDomainSynthesizer:
    """Generate, score, and track cross-domain methodology combinations.

    Works with MethodologyTracker to read success rates and category data,
    then produces novel composite research questions by combining methods
    from different analytical categories.
    """

    def __init__(self, methodology_tracker_path=None):
        self.methodology_path = Path(methodology_tracker_path or DEFAULT_TRACKER_PATH)
        self.synthesis_path = DEFAULT_SYNTHESIS_PATH
        self.methodology_data = self._load_methodology_data()
        self.synthesis_data = self._load_synthesis_data()

    def _load_methodology_data(self):
        """Load methodology tracker data."""
        if self.methodology_path.exists():
            with open(self.methodology_path) as f:
                return json.load(f)
        return {'version': 1, 'methodologies': {}}

    def _load_synthesis_data(self):
        """Load cross-synthesis tracker data."""
        if self.synthesis_path.exists():
            with open(self.synthesis_path) as f:
                return json.load(f)
        return {
            'version': 1,
            'combinations_tested': {},
            'combination_results': [],
            'builtin_templates': list(BUILTIN_TEMPLATES.keys()),
            'created': datetime.now().isoformat(),
        }

    def save(self):
        """Persist synthesis tracker to disk."""
        self.synthesis_path.parent.mkdir(parents=True, exist_ok=True)
        self.synthesis_data['last_updated'] = datetime.now().isoformat()
        with open(self.synthesis_path, 'w') as f:
            json.dump(self.synthesis_data, f, indent=2)

    # ------------------------------------------------------------------
    # Combination generation
    # ------------------------------------------------------------------

    def _combination_id(self, method_ids):
        """Stable identifier for a set of methods, regardless of order."""
        key = '+'.join(sorted(method_ids))
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def _get_category(self, method_id):
        """Get the category for a methodology."""
        m = self.methodology_data.get('methodologies', {}).get(method_id)
        return m['category'] if m else None

    def _get_success_rate(self, method_id):
        """Estimated success rate from Beta distribution mean."""
        m = self.methodology_data.get('methodologies', {}).get(method_id)
        if not m:
            return 0.5  # Neutral prior for unknown methods
        return m['alpha'] / (m['alpha'] + m['beta'])

    def generate_combinations(self, n=10, min_categories=2):
        """Produce n candidate theory combinations from different categories.

        Uses Thompson-style weighting: proven methods are more likely to appear,
        but exploration room is preserved by giving untested methods a boost.

        Args:
            n: number of combinations to generate
            min_categories: minimum distinct categories required per combination

        Returns:
            list of combination dicts, each with:
                combination_id, methods, categories, weight_score
        """
        methods = self.methodology_data.get('methodologies', {})
        active_ids = [
            mid for mid, m in methods.items()
            if m.get('status') == 'active'
        ]

        if len(active_ids) < min_categories:
            return []

        # Build sampling weights — success rate + exploration bonus
        weights = {}
        for mid in active_ids:
            m = methods[mid]
            success = self._get_success_rate(mid)
            trials = m.get('total_applications', 0)

            # Exploration bonus for under-tested methods
            if trials < 2:
                bonus = 0.25
            elif trials < 5:
                bonus = 0.10
            else:
                bonus = 0.0

            weights[mid] = min(1.0, success + bonus)

        # Generate combinations of size 2 and 3
        candidates = []

        for size in (2, 3):
            for combo in itertools.combinations(active_ids, size):
                categories = {self._get_category(m) for m in combo}
                categories.discard(None)

                if len(categories) < min_categories:
                    continue

                # Score: product of individual weights x category diversity bonus
                weight_score = 1.0
                for mid in combo:
                    weight_score *= weights.get(mid, 0.5)

                diversity_bonus = 1.0 + 0.2 * (len(categories) - 1)
                weight_score *= diversity_bonus

                # Novelty: penalize combinations we have already tested
                cid = self._combination_id(combo)
                if cid in self.synthesis_data.get('combinations_tested', {}):
                    weight_score *= 0.3  # Strong penalty but don't exclude

                candidates.append({
                    'combination_id': cid,
                    'methods': list(combo),
                    'categories': sorted(categories),
                    'weight_score': round(weight_score, 6),
                })

        if not candidates:
            return []

        # Weighted sampling without replacement
        candidates.sort(key=lambda c: c['weight_score'], reverse=True)

        # Use weighted random selection
        selected = []
        pool = list(candidates)
        for _ in range(min(n, len(pool))):
            if not pool:
                break
            total_w = sum(c['weight_score'] for c in pool)
            if total_w == 0:
                break

            r = random.uniform(0, total_w)
            cumulative = 0
            chosen_idx = 0
            for idx, c in enumerate(pool):
                cumulative += c['weight_score']
                if cumulative >= r:
                    chosen_idx = idx
                    break

            selected.append(pool.pop(chosen_idx))

        return selected

    # ------------------------------------------------------------------
    # Hypothesis formatting
    # ------------------------------------------------------------------

    def format_hypothesis(self, combination):
        """Turn a combination into a structured research hypothesis.

        Args:
            combination: dict with 'methods' (list of method_ids) and
                         'combination_id'.  May also include pre-set fields
                         if sourced from a builtin template.

        Returns:
            dict with: name, component_methods, cross_domain_question,
            falsifiable_prediction, data_needed, sectors_to_test
        """
        method_ids = combination.get('methods', [])
        cid = combination.get('combination_id', self._combination_id(method_ids))

        # Check if this matches a builtin template
        template = self._match_builtin_template(method_ids)
        if template:
            return {
                'combination_id': cid,
                'name': template['name'],
                'component_methods': self._enrich_methods(method_ids),
                'cross_domain_question': template['cross_domain_question'],
                'falsifiable_prediction': template['falsifiable_prediction'],
                'data_needed': template['data_needed'],
                'sectors_to_test': template['sectors_to_test'],
                'source': 'builtin_template',
            }

        # Generate a hypothesis from the raw combination
        methods_info = self._enrich_methods(method_ids)
        method_names = [m['name'] for m in methods_info]
        categories = sorted({m['category'] for m in methods_info})

        name = ' x '.join(method_names)

        # Construct a cross-domain question from component descriptions
        descriptions = [m['description'] for m in methods_info]
        question = (
            f'Combining {" + ".join(method_names)}: '
            f'what happens when we apply these lenses simultaneously? '
            f'Where do they agree on high opportunity?'
        )

        # Infer data needs from method categories
        data_needed = self._infer_data_needs(method_ids)

        return {
            'combination_id': cid,
            'name': name,
            'component_methods': methods_info,
            'cross_domain_question': question,
            'falsifiable_prediction': (
                f'Sectors scoring highly on ALL of [{", ".join(method_names)}] '
                f'simultaneously will produce more actionable discoveries than '
                f'any single method applied alone.'
            ),
            'data_needed': data_needed,
            'sectors_to_test': [],  # To be filled by the researcher
            'source': 'generated',
        }

    def _match_builtin_template(self, method_ids):
        """Check if a method set matches any builtin template."""
        method_set = set(method_ids)
        for template in BUILTIN_TEMPLATES.values():
            if set(template['methods']) == method_set:
                return template
        return None

    def _enrich_methods(self, method_ids):
        """Return enriched info for a list of method IDs."""
        methods = self.methodology_data.get('methodologies', {})
        enriched = []
        for mid in method_ids:
            m = methods.get(mid, {})
            enriched.append({
                'method_id': mid,
                'name': m.get('name', mid),
                'category': m.get('category', 'unknown'),
                'description': m.get('description', ''),
                'success_rate': round(
                    m['alpha'] / (m['alpha'] + m['beta']), 3
                ) if m.get('alpha') else None,
                'total_applications': m.get('total_applications', 0),
            })
        return enriched

    def _infer_data_needs(self, method_ids):
        """Infer which data connectors a combination needs."""
        methods = self.methodology_data.get('methodologies', {})
        category_to_connectors = {
            'economic_theory': ['fred', 'bls_qcew', 'bls_oes'],
            'data_source': ['fred', 'bls_qcew', 'edgar_sec', 'eurostat'],
            'math_model': ['bls_qcew', 'census_cbp', 'bea_io_tables'],
            'analytical_lens': ['web_search', 'equity_prices', 'fred'],
            'discovery_method': ['bls_qcew', 'census_cbp', 'naics_lookup'],
        }
        connectors = set()
        for mid in method_ids:
            cat = methods.get(mid, {}).get('category', '')
            for conn in category_to_connectors.get(cat, []):
                connectors.add(conn)
        return sorted(connectors)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_combination(self, combination):
        """Score a methodology combination on multiple dimensions.

        Scoring dimensions:
            diversity:  How many distinct categories are represented (0-1)
            novelty:    Has this combination been tested before? (0-1)
            feasibility: Do we have the data connectors needed? (0-1)
            strength:   Average success rate of component methods (0-1)

        Returns:
            dict with individual scores and a composite score (0-100)
        """
        method_ids = combination.get('methods', [])
        if not method_ids:
            return {'composite': 0, 'error': 'no_methods'}

        # Diversity: distinct categories / total methods
        categories = set()
        for mid in method_ids:
            cat = self._get_category(mid)
            if cat:
                categories.add(cat)
        diversity = len(categories) / len(method_ids) if method_ids else 0

        # Novelty: 1.0 if never tested, decays with number of prior tests
        cid = self._combination_id(method_ids)
        prior = self.synthesis_data.get('combinations_tested', {}).get(cid)
        if prior is None:
            novelty = 1.0
        else:
            times_tested = prior.get('times_tested', 0)
            novelty = max(0.1, 1.0 / (1 + times_tested))

        # Feasibility: fraction of needed data connectors we actually have
        data_needed = self._infer_data_needs(method_ids)
        if data_needed:
            available = sum(1 for d in data_needed if d in AVAILABLE_DATA_CONNECTORS)
            feasibility = available / len(data_needed)
        else:
            feasibility = 0.5  # Unknown needs — neutral

        # Strength: average success rate across component methods
        rates = [self._get_success_rate(mid) for mid in method_ids]
        strength = sum(rates) / len(rates) if rates else 0.5

        # Composite: weighted combination
        composite = (
            diversity * 25 +
            novelty * 30 +
            feasibility * 20 +
            strength * 25
        )

        return {
            'combination_id': cid,
            'diversity': round(diversity, 3),
            'novelty': round(novelty, 3),
            'feasibility': round(feasibility, 3),
            'strength': round(strength, 3),
            'composite': round(composite, 1),
        }

    # ------------------------------------------------------------------
    # Untested combinations
    # ------------------------------------------------------------------

    def get_untested_combinations(self):
        """Return methodology pairs that have never been tried together.

        Focuses on pairs (size 2) for tractability, then suggests which
        third method could upgrade the most promising pairs to triples.
        """
        methods = self.methodology_data.get('methodologies', {})
        active_ids = [
            mid for mid, m in methods.items()
            if m.get('status') == 'active'
        ]

        tested = set(self.synthesis_data.get('combinations_tested', {}).keys())

        untested_pairs = []
        for pair in itertools.combinations(active_ids, 2):
            cid = self._combination_id(pair)
            if cid in tested:
                continue

            cat_a = self._get_category(pair[0])
            cat_b = self._get_category(pair[1])

            # Only include cross-category pairs
            if cat_a == cat_b:
                continue

            score = self.score_combination({'methods': list(pair)})
            untested_pairs.append({
                'combination_id': cid,
                'methods': list(pair),
                'categories': sorted({cat_a, cat_b} - {None}),
                'composite_score': score['composite'],
            })

        untested_pairs.sort(key=lambda x: x['composite_score'], reverse=True)

        # For the top pairs, suggest a third method from a new category
        for pair_info in untested_pairs[:10]:
            existing_cats = set(pair_info['categories'])
            candidates = [
                mid for mid in active_ids
                if mid not in pair_info['methods']
                and self._get_category(mid) not in existing_cats
            ]
            if candidates:
                # Pick the one with highest success rate
                best = max(candidates, key=lambda m: self._get_success_rate(m))
                pair_info['suggested_third'] = {
                    'method_id': best,
                    'name': methods.get(best, {}).get('name', best),
                    'category': self._get_category(best),
                }

        return untested_pairs

    # ------------------------------------------------------------------
    # Result tracking
    # ------------------------------------------------------------------

    def record_synthesis_result(self, combination_id, cycle, produced_insight,
                                description=None):
        """Track whether a cross-domain combination produced an insight.

        Args:
            combination_id: the combination's stable ID
            cycle: research cycle number
            produced_insight: True if the combination yielded an actionable finding
            description: what was discovered (if produced_insight is True)
        """
        now = datetime.now().isoformat()

        # Update combinations_tested
        tested = self.synthesis_data.setdefault('combinations_tested', {})
        if combination_id not in tested:
            tested[combination_id] = {
                'first_tested': now,
                'times_tested': 0,
                'insights_produced': 0,
            }

        entry = tested[combination_id]
        entry['times_tested'] += 1
        entry['last_tested'] = now
        if produced_insight:
            entry['insights_produced'] += 1

        # Append to results log
        self.synthesis_data.setdefault('combination_results', []).append({
            'combination_id': combination_id,
            'cycle': cycle,
            'produced_insight': produced_insight,
            'description': description,
            'timestamp': now,
        })

        self.save()

    # ------------------------------------------------------------------
    # Dashboard / summary
    # ------------------------------------------------------------------

    def get_dashboard(self):
        """Summary of cross-synthesis state."""
        tested = self.synthesis_data.get('combinations_tested', {})
        results = self.synthesis_data.get('combination_results', [])

        total_tested = len(tested)
        total_trials = sum(e.get('times_tested', 0) for e in tested.values())
        total_insights = sum(e.get('insights_produced', 0) for e in tested.values())

        # Score all builtin templates
        template_scores = {}
        for template_id, template in BUILTIN_TEMPLATES.items():
            combo = {'methods': template['methods']}
            score = self.score_combination(combo)
            cid = self._combination_id(template['methods'])
            template_scores[template_id] = {
                'name': template['name'],
                'composite_score': score['composite'],
                'tested': cid in tested,
                'insights': tested.get(cid, {}).get('insights_produced', 0),
            }

        return {
            'unique_combinations_tested': total_tested,
            'total_trials': total_trials,
            'total_insights': total_insights,
            'insight_rate': (
                round(total_insights / total_trials, 3) if total_trials > 0 else None
            ),
            'builtin_templates': template_scores,
            'untested_builtins': [
                tid for tid, info in template_scores.items()
                if not info['tested']
            ],
            'recent_results': results[-10:],
        }
