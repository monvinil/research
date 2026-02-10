"""Composite index construction — aggregate multiple series into single indicators.

Maps directly to the Principles Engine: each principle gets a composite index
that aggregates all relevant data into a single score.
"""

import math
from .timeseries import TimeSeriesAnalyzer


class CompositeIndexBuilder:
    """Build composite indices from multiple economic series."""

    def __init__(self):
        self.ts = TimeSeriesAnalyzer()

    @staticmethod
    def _normalize(values, method='z_score'):
        """Normalize a series to comparable scale.

        z_score: standard normal (mean 0, std 1)
        min_max: scale to 0-100
        """
        if not values:
            return []

        vals = [v for _, v in values if v is not None]
        if len(vals) < 2:
            return [(d, 0) for d, _ in values]

        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((x - mean) ** 2 for x in vals) / len(vals))

        if method == 'z_score':
            if std == 0:
                return [(d, 0) for d, v in values]
            return [(d, round((v - mean) / std, 4)) for d, v in values if v is not None]
        elif method == 'min_max':
            mn, mx = min(vals), max(vals)
            rng = mx - mn if mx != mn else 1
            return [(d, round((v - mn) / rng * 100, 2)) for d, v in values if v is not None]

        return values

    def build_p2_liquidation_index(self, fred_data):
        """P2: Liquidation Cascade Pressure Index.

        Combines: unit labor costs, delinquency rate, credit tightening,
        declining job openings, HY spread widening.

        Higher = more liquidation pressure (favorable for disruption).
        """
        components = {}
        weights = {
            'ULCNFB': 0.25,       # Unit labor costs (rising = pressure)
            'DRSFRMACBS': 0.20,    # Loan delinquency (rising = pressure)
            'DRTSCILM': 0.15,     # Credit tightening (rising = pressure)
            'BAMLH0A0HYM2': 0.15, # HY spread (widening = pressure)
            'JTSJOL': -0.15,      # Job openings (falling = pressure, so negative weight)
            'BUSLOANS': -0.10,    # Commercial loans (falling = pressure)
        }

        for series_id, weight in weights.items():
            if series_id in fred_data:
                obs = self.ts.extract_observations(fred_data[series_id])
                if obs:
                    growth = self.ts.growth_rate(obs, 1)
                    if growth:
                        normalized = self._normalize(growth)
                        components[series_id] = {
                            'weight': weight,
                            'normalized': normalized,
                        }

        return self._combine_components(components, 'P2 Liquidation Pressure')

    def build_p3_cost_collapse_index(self, fred_data):
        """P3: Cost Structure Collapse Index.

        Combines: productivity growth, profit margin expansion,
        unit labor cost decline, CPI moderation.

        Higher = more cost collapse (favorable for new entrants).
        """
        components = {}
        weights = {
            'OPHNFB': 0.30,      # Productivity (rising = collapse)
            'CP': 0.25,           # Corporate profits (rising = margin expansion)
            'ULCNFB': -0.25,     # Unit labor costs (falling = collapse)
            'CPIAUCSL': -0.20,   # CPI (moderating = collapse)
        }

        for series_id, weight in weights.items():
            if series_id in fred_data:
                obs = self.ts.extract_observations(fred_data[series_id])
                if obs:
                    growth = self.ts.growth_rate(obs, 1)
                    if growth:
                        normalized = self._normalize(growth)
                        components[series_id] = {
                            'weight': weight,
                            'normalized': normalized,
                        }

        return self._combine_components(components, 'P3 Cost Collapse')

    def build_p5_labor_gap_index(self, fred_data):
        """P5: Labor Market Gap Index.

        Combines: unemployment rate, job openings, quits rate,
        average hourly earnings growth.

        Higher = tighter labor market (more opportunity for AI substitution).
        """
        components = {}
        weights = {
            'UNRATE': -0.25,         # Unemployment (low = tight)
            'JTSJOL': 0.25,          # Job openings (high = tight)
            'JTSQUL': 0.25,          # Quits (high = tight, workers confident)
            'CES0500000003': 0.25,   # Wage growth (high = tight)
        }

        for series_id, weight in weights.items():
            if series_id in fred_data:
                obs = self.ts.extract_observations(fred_data[series_id])
                if obs:
                    normalized = self._normalize(obs)
                    components[series_id] = {
                        'weight': weight,
                        'normalized': normalized,
                    }

        return self._combine_components(components, 'P5 Labor Gap')

    def build_capital_environment_index(self, fred_data):
        """Capital Environment Index — is the macro favorable for new entrants?

        Combines: fed funds rate trend, yield curve, financial stress,
        credit availability.

        Higher = more favorable environment for capital-light startups.
        """
        components = {}
        weights = {
            'FEDFUNDS': -0.20,    # Fed funds (lower = more favorable)
            'T10Y2Y': 0.25,       # Yield curve (positive = no recession)
            'STLFSI4': -0.25,     # Financial stress (lower = more favorable)
            'DRTSCLCC': -0.15,    # Credit card tightening (lower = easier credit)
            'DRTSCILM': -0.15,    # C&I loan tightening (lower = easier credit)
        }

        for series_id, weight in weights.items():
            if series_id in fred_data:
                obs = self.ts.extract_observations(fred_data[series_id])
                if obs:
                    normalized = self._normalize(obs)
                    components[series_id] = {
                        'weight': weight,
                        'normalized': normalized,
                    }

        return self._combine_components(components, 'Capital Environment')

    def build_creative_destruction_index(self, fred_data):
        """P2+P4: Creative Destruction Index.

        Combines: business applications, delinquency, business
        applications without wages (solo operators).

        Higher = more creative destruction (old dying, new forming).
        """
        components = {}
        weights = {
            'BABATOTALSAUS': 0.35,   # New business applications (births)
            'BUSAPPWNSAUS': 0.25,    # No-wage applications (solo/agentic)
            'DRSFRMACBS': 0.25,      # Delinquency (deaths)
            'NCBEILQ027S': -0.15,    # Inventory (falling = demand decline)
        }

        for series_id, weight in weights.items():
            if series_id in fred_data:
                obs = self.ts.extract_observations(fred_data[series_id])
                if obs:
                    growth = self.ts.growth_rate(obs, 1)
                    if growth:
                        normalized = self._normalize(growth)
                        components[series_id] = {
                            'weight': weight,
                            'normalized': normalized,
                        }

        return self._combine_components(components, 'Creative Destruction')

    def _combine_components(self, components, index_name):
        """Combine normalized, weighted components into a single index."""
        if not components:
            return {
                'index_name': index_name,
                'error': 'no_data',
                'components': [],
            }

        # Find common dates across all components
        date_sets = []
        for info in components.values():
            dates = {d for d, _ in info['normalized']}
            date_sets.append(dates)

        if not date_sets:
            return {'index_name': index_name, 'error': 'no_common_dates'}

        common_dates = date_sets[0]
        for ds in date_sets[1:]:
            common_dates &= ds

        if not common_dates:
            # Fall back to using all available dates with partial data
            common_dates = set()
            for ds in date_sets:
                common_dates |= ds

        # Compute weighted sum for each date
        index_values = []
        for date in sorted(common_dates, reverse=True):
            weighted_sum = 0
            total_weight = 0
            for series_id, info in components.items():
                val_dict = {d: v for d, v in info['normalized']}
                if date in val_dict:
                    weighted_sum += val_dict[date] * info['weight']
                    total_weight += abs(info['weight'])

            if total_weight > 0:
                index_values.append((date, round(weighted_sum / total_weight, 4)))

        # Rescale to 0-100 for readability
        scaled = self._normalize(index_values, method='min_max')

        return {
            'index_name': index_name,
            'values': scaled[:24],  # Last 24 periods
            'latest': scaled[0] if scaled else None,
            'component_count': len(components),
            'components': list(components.keys()),
            'date_count': len(scaled),
        }

    def build_all_indices(self, fred_data):
        """Build all principle-mapped composite indices."""
        return {
            'p2_liquidation': self.build_p2_liquidation_index(fred_data),
            'p3_cost_collapse': self.build_p3_cost_collapse_index(fred_data),
            'p5_labor_gap': self.build_p5_labor_gap_index(fred_data),
            'capital_environment': self.build_capital_environment_index(fred_data),
            'creative_destruction': self.build_creative_destruction_index(fred_data),
        }
