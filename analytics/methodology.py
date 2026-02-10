"""Methodology tracking and exploration/exploitation allocation.

Tracks which analytical approaches (economic theories, math models, data sources,
frameworks) have been applied, what they produced, and how to allocate future
cycle capacity between proven methods and speculative ones.

Uses a modified Thompson Sampling approach:
- Each methodology has a Beta(alpha, beta) distribution representing its
  success rate at producing actionable discoveries.
- alpha = number of discoveries produced
- beta = number of applications that produced no discovery
- Sample from each distribution to decide allocation.
- Exploration bonus: methodologies with fewer total trials get a boost
  (information value of reducing uncertainty).
"""

import json
import math
import random
from pathlib import Path
from datetime import datetime


DEFAULT_TRACKER_PATH = Path(__file__).parent.parent / 'data' / 'context' / 'methodology_tracker.json'

# Methodology categories
CATEGORIES = {
    'economic_theory': 'Economic theories and frameworks (Baumol, Bass, IO tables, etc.)',
    'data_source': 'Data sources and APIs (FRED, BLS, EDGAR, Eurostat, etc.)',
    'math_model': 'Mathematical/statistical models (HHI, shift-share, regression, etc.)',
    'analytical_lens': 'Analytical perspectives (competitive density, timing arbitrage, etc.)',
    'discovery_method': 'Discovery approaches (top-down macro, bottom-up screener, etc.)',
}


class MethodologyTracker:
    """Track methodology applications, outcomes, and allocate future capacity."""

    def __init__(self, tracker_path=None):
        self.path = tracker_path or DEFAULT_TRACKER_PATH
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {
            'version': 1,
            'methodologies': {},
            'cycle_log': [],
            'allocation_history': [],
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def register_methodology(self, method_id, name, category, description,
                              confidence_prior='neutral'):
        """Register a new methodology for tracking.

        Args:
            method_id: unique identifier (e.g., 'baumol_cost_disease')
            name: human-readable name
            category: one of CATEGORIES keys
            description: what this methodology does
            confidence_prior: 'optimistic', 'neutral', 'pessimistic'
                             Sets initial alpha/beta for Thompson Sampling.
        """
        priors = {
            'optimistic': (2, 1),    # Expect it to work ~67% of the time
            'neutral': (1, 1),       # Uniform prior — no opinion
            'pessimistic': (1, 2),   # Expect it to fail ~67% of the time
        }
        alpha, beta = priors.get(confidence_prior, (1, 1))

        self.data['methodologies'][method_id] = {
            'name': name,
            'category': category,
            'description': description,
            'alpha': alpha,
            'beta': beta,
            'total_applications': 0,
            'discoveries': [],        # List of discovery records
            'null_results': [],       # List of null-result records
            'first_used': None,
            'last_used': None,
            'status': 'active',       # active, paused, retired
        }
        self.save()

    def record_application(self, method_id, cycle, produced_discovery,
                            discovery_description=None, discovery_score=None,
                            notes=None):
        """Record that a methodology was applied in a cycle.

        Args:
            method_id: which methodology
            cycle: cycle number
            produced_discovery: True if it produced an actionable finding
            discovery_description: what was found (if produced_discovery)
            discovery_score: 0-100 quality of discovery (optional)
            notes: free-text notes
        """
        m = self.data['methodologies'].get(method_id)
        if not m:
            raise ValueError(f'Unknown methodology: {method_id}')

        now = datetime.now().isoformat()
        m['total_applications'] += 1
        m['last_used'] = now
        if m['first_used'] is None:
            m['first_used'] = now

        record = {
            'cycle': cycle,
            'timestamp': now,
            'notes': notes,
        }

        if produced_discovery:
            m['alpha'] += 1
            record['description'] = discovery_description
            record['score'] = discovery_score
            m['discoveries'].append(record)
        else:
            m['beta'] += 1
            m['null_results'].append(record)

        # Log to cycle log
        self.data['cycle_log'].append({
            'cycle': cycle,
            'method_id': method_id,
            'produced_discovery': produced_discovery,
            'description': discovery_description,
            'timestamp': now,
        })

        self.save()

    def get_success_rate(self, method_id):
        """Get estimated success rate (mean of Beta distribution)."""
        m = self.data['methodologies'].get(method_id)
        if not m:
            return None
        return m['alpha'] / (m['alpha'] + m['beta'])

    def get_confidence_interval(self, method_id, width=0.90):
        """Get credible interval for success rate.

        More trials → narrower interval → more confidence in the estimate.
        """
        m = self.data['methodologies'].get(method_id)
        if not m:
            return None

        alpha, beta = m['alpha'], m['beta']
        # Use normal approximation for Beta distribution
        mean = alpha / (alpha + beta)
        n = alpha + beta
        if n < 3:
            return {'mean': mean, 'low': 0.0, 'high': 1.0, 'width': 1.0,
                    'confidence': 'very_low'}

        std = math.sqrt(alpha * beta / (n * n * (n + 1)))
        z = 1.645  # 90% interval
        low = max(0, mean - z * std)
        high = min(1, mean + z * std)

        if high - low > 0.5:
            confidence = 'low'
        elif high - low > 0.3:
            confidence = 'moderate'
        elif high - low > 0.15:
            confidence = 'good'
        else:
            confidence = 'high'

        return {
            'mean': round(mean, 3),
            'low': round(low, 3),
            'high': round(high, 3),
            'width': round(high - low, 3),
            'confidence': confidence,
        }

    def thompson_sample(self, method_id):
        """Draw a Thompson sample for this methodology.

        Higher sample = higher priority for allocation.
        Naturally balances exploration/exploitation.
        """
        m = self.data['methodologies'].get(method_id)
        if not m or m['status'] != 'active':
            return 0.0

        # Thompson sample from Beta(alpha, beta)
        sample = random.betavariate(m['alpha'], m['beta'])

        # Exploration bonus: methodologies with fewer trials get a boost
        # This is the information gain from reducing uncertainty
        n = m['total_applications']
        if n < 3:
            exploration_bonus = 0.2  # Strong boost for untested methods
        elif n < 6:
            exploration_bonus = 0.1
        elif n < 10:
            exploration_bonus = 0.05
        else:
            exploration_bonus = 0.0

        return min(1.0, sample + exploration_bonus)

    def allocate_capacity(self, total_slots, seed=None):
        """Allocate cycle capacity across methodologies using Thompson Sampling.

        Args:
            total_slots: how many methodology applications to allocate
            seed: random seed for reproducibility

        Returns:
            dict of {method_id: allocated_slots}
        """
        if seed is not None:
            random.seed(seed)

        active = {k: v for k, v in self.data['methodologies'].items()
                  if v['status'] == 'active'}

        if not active:
            return {}

        # Draw Thompson samples
        samples = {k: self.thompson_sample(k) for k in active}

        # Normalize to allocation
        total_sample = sum(samples.values())
        if total_sample == 0:
            # Equal allocation
            per_method = max(1, total_slots // len(active))
            return {k: per_method for k in active}

        allocation = {}
        remaining = total_slots
        sorted_methods = sorted(samples.items(), key=lambda x: x[1], reverse=True)

        for method_id, sample in sorted_methods:
            if remaining <= 0:
                break
            # Proportional allocation, minimum 1 if sampled above threshold
            share = sample / total_sample
            slots = max(1, round(share * total_slots))
            slots = min(slots, remaining)
            allocation[method_id] = slots
            remaining -= slots

        # Record allocation
        self.data['allocation_history'].append({
            'timestamp': datetime.now().isoformat(),
            'total_slots': total_slots,
            'samples': {k: round(v, 4) for k, v in samples.items()},
            'allocation': allocation,
        })
        self.save()

        return allocation

    def get_dashboard(self):
        """Generate a summary dashboard of all methodologies."""
        dashboard = {
            'total_methodologies': len(self.data['methodologies']),
            'total_applications': sum(
                m['total_applications']
                for m in self.data['methodologies'].values()
            ),
            'total_discoveries': sum(
                len(m['discoveries'])
                for m in self.data['methodologies'].values()
            ),
            'by_category': {},
            'rankings': [],
        }

        # Group by category
        for method_id, m in self.data['methodologies'].items():
            cat = m['category']
            if cat not in dashboard['by_category']:
                dashboard['by_category'][cat] = {
                    'count': 0,
                    'total_discoveries': 0,
                    'total_applications': 0,
                }
            dashboard['by_category'][cat]['count'] += 1
            dashboard['by_category'][cat]['total_discoveries'] += len(m['discoveries'])
            dashboard['by_category'][cat]['total_applications'] += m['total_applications']

        # Rank by success rate (with enough data) or exploration priority
        for method_id, m in self.data['methodologies'].items():
            ci = self.get_confidence_interval(method_id)
            dashboard['rankings'].append({
                'method_id': method_id,
                'name': m['name'],
                'category': m['category'],
                'applications': m['total_applications'],
                'discoveries': len(m['discoveries']),
                'success_rate': ci['mean'] if ci else None,
                'confidence': ci['confidence'] if ci else 'none',
                'status': m['status'],
            })

        dashboard['rankings'].sort(
            key=lambda x: (x['discoveries'], x['success_rate'] or 0),
            reverse=True,
        )

        return dashboard

    def get_exploration_candidates(self, min_uncertainty=0.4):
        """Find methodologies that need more testing.

        Returns methods where the confidence interval is wide enough
        that we can't reliably estimate their value.
        """
        candidates = []
        for method_id, m in self.data['methodologies'].items():
            if m['status'] != 'active':
                continue
            ci = self.get_confidence_interval(method_id)
            if ci and ci['width'] >= min_uncertainty:
                candidates.append({
                    'method_id': method_id,
                    'name': m['name'],
                    'applications': m['total_applications'],
                    'interval_width': ci['width'],
                    'current_estimate': ci['mean'],
                    'recommendation': (
                        f"Need {max(1, 5 - m['total_applications'])} more trials "
                        f"to narrow confidence interval."
                    ),
                })

        candidates.sort(key=lambda x: x['interval_width'], reverse=True)
        return candidates
