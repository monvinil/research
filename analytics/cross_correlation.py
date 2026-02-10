"""Cross-correlation analysis — find meaningful relationships between series.

This is how we find the "meaningful links between economic models and data"
the user asked for. Instead of looking at series in isolation, we find
which series move together, which lead/lag, and how strong the relationship is.
"""

import math
from .timeseries import TimeSeriesAnalyzer


class CrossCorrelator:
    """Find relationships between economic series."""

    @staticmethod
    def _align_series(series_a, series_b):
        """Align two series by date, returning only matching dates."""
        b_dict = {date: val for date, val in series_b}
        aligned_a = []
        aligned_b = []
        for date, val in series_a:
            if date in b_dict:
                aligned_a.append(val)
                aligned_b.append(b_dict[date])
        return aligned_a, aligned_b

    @staticmethod
    def pearson_correlation(series_a, series_b):
        """Compute Pearson correlation between two aligned series.

        Returns:
            float between -1 and 1 (None if insufficient data)
        """
        a, b = CrossCorrelator._align_series(series_a, series_b)
        n = len(a)
        if n < 5:
            return None

        mean_a = sum(a) / n
        mean_b = sum(b) / n

        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / n)
        std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / n)

        if std_a == 0 or std_b == 0:
            return None

        return round(cov / (std_a * std_b), 4)

    @staticmethod
    def lead_lag_correlation(leader, follower, max_lag=6):
        """Test if one series leads another by 1-N periods.

        This is the key analytical tool: if productivity leads
        employment decline by 3 months, we get 3 months of warning.

        Args:
            leader: list of (date, value) tuples (potential leading series)
            follower: list of (date, value) tuples (potential lagging series)
            max_lag: maximum lag periods to test

        Returns:
            dict with best_lag, correlations by lag, and interpretation
        """
        correlations = {}
        best_lag = 0
        best_corr = 0

        for lag in range(max_lag + 1):
            # Shift leader forward by `lag` periods
            if lag >= len(leader):
                break
            shifted_leader = leader[lag:]
            corr = CrossCorrelator.pearson_correlation(shifted_leader, follower)
            if corr is not None:
                correlations[lag] = corr
                if abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag

        return {
            'best_lag': best_lag,
            'best_correlation': best_corr,
            'correlations_by_lag': correlations,
            'interpretation': (
                f'Leader series leads follower by {best_lag} periods '
                f'with correlation {best_corr:.4f}. '
                f'{"Strong" if abs(best_corr) > 0.7 else "Moderate" if abs(best_corr) > 0.4 else "Weak"} '
                f'{"positive" if best_corr > 0 else "negative"} relationship.'
            ),
        }

    @staticmethod
    def correlation_matrix(named_series):
        """Compute pairwise correlations for a set of named series.

        Args:
            named_series: dict of {name: [(date, value), ...]}

        Returns:
            dict with matrix and strongest relationships
        """
        names = list(named_series.keys())
        matrix = {}
        strong_pairs = []

        for i, name_a in enumerate(names):
            matrix[name_a] = {}
            for j, name_b in enumerate(names):
                if i == j:
                    matrix[name_a][name_b] = 1.0
                elif j < i and name_b in matrix and name_a in matrix[name_b]:
                    matrix[name_a][name_b] = matrix[name_b][name_a]
                else:
                    corr = CrossCorrelator.pearson_correlation(
                        named_series[name_a], named_series[name_b]
                    )
                    matrix[name_a][name_b] = corr

                    if corr is not None and abs(corr) > 0.6 and i != j:
                        strong_pairs.append({
                            'pair': (name_a, name_b),
                            'correlation': corr,
                            'type': 'positive' if corr > 0 else 'negative',
                        })

        # Sort strongest pairs
        strong_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)

        return {
            'matrix': matrix,
            'strong_pairs': strong_pairs[:20],
            'series_count': len(names),
        }

    @staticmethod
    def divergence_detector(series_a, series_b, window=6, threshold=1.5):
        """Detect when two normally-correlated series start diverging.

        This catches structural breaks in relationships. Example:
        if employment and GDP normally move together but suddenly
        diverge, something structural is happening (AI substitution?).

        Args:
            series_a, series_b: list of (date, value) tuples
            window: lookback window for correlation computation
            threshold: z-score threshold for flagging divergence

        Returns:
            list of divergence events with dates and magnitudes
        """
        ts = TimeSeriesAnalyzer()
        growth_a = ts.growth_rate(series_a, 1)
        growth_b = ts.growth_rate(series_b, 1)

        if len(growth_a) < window * 2 or len(growth_b) < window * 2:
            return []

        # Align by date
        b_dict = {d: v for d, v in growth_b}
        aligned_pairs = []
        for d, v in growth_a:
            if d in b_dict:
                aligned_pairs.append((d, v, b_dict[d]))

        if len(aligned_pairs) < window * 2:
            return []

        # Compute rolling spread and detect anomalies
        divergences = []
        spreads = [(d, a - b) for d, a, b in aligned_pairs]

        z_scores = ts.z_score(spreads, window=window)
        for date, z in z_scores:
            if abs(z) > threshold:
                divergences.append({
                    'date': date,
                    'z_score': z,
                    'direction': 'A outpacing B' if z > 0 else 'B outpacing A',
                })

        return divergences

    def analyze_principle_relationships(self, fred_data, bls_data=None):
        """Run standard cross-correlations relevant to the Principles Engine.

        Tests relationships between:
        - Productivity vs employment (P2: substitution signal)
        - Unit labor costs vs corporate profits (P3: margin signal)
        - Job openings vs quits rate (P5: labor market tightness)
        - Credit stress vs business formation (P2/P4: creative destruction)
        - VIX vs business loan delinquency (capital stress propagation)

        Args:
            fred_data: dict of series_id -> connector output
            bls_data: optional BLS data dict

        Returns:
            dict with named relationship analyses
        """
        ts = TimeSeriesAnalyzer()
        relationships = {}

        def extract(series_id):
            if series_id in fred_data:
                return ts.extract_observations(fred_data[series_id])
            return []

        # P2: Productivity vs unit labor costs
        productivity = extract('OPHNFB')
        ulc = extract('ULCNFB')
        if productivity and ulc:
            relationships['productivity_vs_labor_costs'] = {
                'description': 'P2 — When productivity rises but ULC stays high, '
                               'firms are squeezing more output from fewer workers. '
                               'Widening gap = AI substitution accelerating.',
                **self.lead_lag_correlation(productivity, ulc),
                'divergence': self.divergence_detector(productivity, ulc),
            }

        # P3: Corporate profits vs wages
        profits = extract('CP')
        wages = extract('CES0500000003')
        if profits and wages:
            relationships['profits_vs_wages'] = {
                'description': 'P3 — Profits rising while wage growth flat = '
                               'successful cost substitution. Divergence confirms '
                               'AI is enabling margin expansion.',
                **self.lead_lag_correlation(profits, wages),
            }

        # P5: Job openings vs unemployment
        openings = extract('JTSJOL')
        unemployment = extract('UNRATE')
        if openings and unemployment:
            relationships['beveridge_curve'] = {
                'description': 'P5 — Beveridge curve shift: if openings fall while '
                               'unemployment rises, the matching function has broken. '
                               'Skills mismatch + AI substitution.',
                **self.lead_lag_correlation(openings, unemployment),
            }

        # P2/P4: Credit stress vs new business formation
        delinquency = extract('DRSFRMACBS')
        biz_apps = extract('BABATOTALSAUS')
        if delinquency and biz_apps:
            relationships['creative_destruction'] = {
                'description': 'P2+P4 — Rising delinquency + rising new business '
                               'formation = creative destruction in action. Old firms '
                               'dying, new ones forming.',
                **self.lead_lag_correlation(delinquency, biz_apps),
            }

        # Capital stress propagation
        vix = extract('VIXCLS')
        hy_spread = extract('BAMLH0A0HYM2')
        if vix and hy_spread:
            relationships['stress_propagation'] = {
                'description': 'Capital stress — VIX leads HY spread: equity fear '
                               'precedes credit stress. Time between them = warning window.',
                **self.lead_lag_correlation(vix, hy_spread),
            }

        return relationships
