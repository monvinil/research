"""Time series analytics — growth rates, z-scores, momentum, regime detection.

Takes raw observations from any connector and computes derived indicators
that are directly interpretable by the Principles Engine.
"""

import math
from collections import defaultdict


class TimeSeriesAnalyzer:
    """Compute derived time series indicators from raw observations."""

    @staticmethod
    def growth_rate(values, periods=1):
        """Compute period-over-period growth rate.

        Args:
            values: list of (date, value) tuples, most recent first
            periods: lookback (1 = MoM/QoQ, 4 = QoQ for monthly, 12 = YoY for monthly)

        Returns:
            list of (date, growth_rate) tuples
        """
        results = []
        for i in range(len(values) - periods):
            current = values[i][1]
            previous = values[i + periods][1]
            if previous and previous != 0:
                rate = (current - previous) / abs(previous)
                results.append((values[i][0], round(rate, 6)))
        return results

    @staticmethod
    def yoy_change(values):
        """Year-over-year change. Assumes monthly data (12 periods back)."""
        return TimeSeriesAnalyzer.growth_rate(values, periods=12)

    @staticmethod
    def qoq_change(values):
        """Quarter-over-quarter. Assumes quarterly data (1 period back)."""
        return TimeSeriesAnalyzer.growth_rate(values, periods=1)

    @staticmethod
    def mom_change(values):
        """Month-over-month. Assumes monthly data (1 period back)."""
        return TimeSeriesAnalyzer.growth_rate(values, periods=1)

    @staticmethod
    def z_score(values, window=20):
        """Compute z-score (standard deviations from rolling mean).

        Z > 2.0 = significantly above trend (overheating)
        Z < -2.0 = significantly below trend (distress)

        Args:
            values: list of (date, value) tuples
            window: rolling window for mean/std computation

        Returns:
            list of (date, z_score) tuples
        """
        results = []
        vals_only = [v[1] for v in values if v[1] is not None]

        for i in range(len(values)):
            # Use up to `window` observations ending at current position
            end = min(i + window, len(vals_only))
            start = max(0, end - window)
            window_vals = vals_only[start:end]

            if len(window_vals) < 3:
                continue

            mean = sum(window_vals) / len(window_vals)
            variance = sum((x - mean) ** 2 for x in window_vals) / len(window_vals)
            std = math.sqrt(variance) if variance > 0 else 0.001

            current = values[i][1]
            if current is not None:
                z = (current - mean) / std
                results.append((values[i][0], round(z, 4)))

        return results

    @staticmethod
    def momentum(values, short_window=3, long_window=12):
        """Momentum indicator — short MA vs long MA crossover.

        > 0 = accelerating (short-term above long-term trend)
        < 0 = decelerating (short-term below long-term trend)
        Crossover from negative to positive = inflection point.

        Args:
            values: list of (date, value) tuples
            short_window: fast moving average periods
            long_window: slow moving average periods

        Returns:
            list of (date, momentum) tuples
        """
        results = []
        vals = [v[1] for v in values if v[1] is not None]

        for i in range(len(values)):
            if i + long_window > len(vals):
                continue

            short_slice = vals[i:i + short_window]
            long_slice = vals[i:i + long_window]

            if not short_slice or not long_slice:
                continue

            short_ma = sum(short_slice) / len(short_slice)
            long_ma = sum(long_slice) / len(long_slice)

            if long_ma != 0:
                mom = (short_ma - long_ma) / abs(long_ma)
                results.append((values[i][0], round(mom, 6)))

        return results

    @staticmethod
    def rate_of_change(values, periods=1):
        """Simple rate of change — current vs N periods ago."""
        return TimeSeriesAnalyzer.growth_rate(values, periods)

    @staticmethod
    def spread(series_a, series_b):
        """Compute spread between two series (A - B) for matching dates.

        Useful for: yield curve spread, wage premium, productivity-cost gap.
        """
        b_dict = {date: val for date, val in series_b}
        results = []
        for date, val_a in series_a:
            if date in b_dict and val_a is not None and b_dict[date] is not None:
                results.append((date, round(val_a - b_dict[date], 6)))
        return results

    @staticmethod
    def ratio(series_a, series_b):
        """Compute ratio of two series (A / B) for matching dates.

        Useful for: profit margins, labor share, output per worker.
        """
        b_dict = {date: val for date, val in series_b}
        results = []
        for date, val_a in series_a:
            if date in b_dict and b_dict[date] and b_dict[date] != 0:
                results.append((date, round(val_a / b_dict[date], 6)))
        return results

    @staticmethod
    def detect_regime_change(values, window=8, threshold=2.0):
        """Detect structural breaks — points where the mean shifts significantly.

        Uses CUSUM-like approach: when z-score of the mean difference
        between consecutive windows exceeds threshold, flag a regime change.

        Returns:
            list of (date, direction, magnitude) tuples where regime changes occur
        """
        if len(values) < window * 2:
            return []

        regime_changes = []
        for i in range(window, len(values) - window):
            before = [v[1] for v in values[i - window:i] if v[1] is not None]
            after = [v[1] for v in values[i:i + window] if v[1] is not None]

            if len(before) < 3 or len(after) < 3:
                continue

            mean_before = sum(before) / len(before)
            mean_after = sum(after) / len(after)

            # Pooled standard deviation
            all_vals = before + after
            overall_mean = sum(all_vals) / len(all_vals)
            variance = sum((x - overall_mean) ** 2 for x in all_vals) / len(all_vals)
            std = math.sqrt(variance) if variance > 0 else 0.001

            diff = (mean_after - mean_before) / std

            if abs(diff) > threshold:
                direction = 'up' if diff > 0 else 'down'
                regime_changes.append((values[i][0], direction, round(diff, 4)))

        return regime_changes

    @staticmethod
    def acceleration(values, periods=1):
        """Second derivative — rate of change of rate of change.

        Positive acceleration = growth is speeding up.
        Negative acceleration = growth is slowing down.
        This catches inflection points before they show up in levels.
        """
        growth = TimeSeriesAnalyzer.growth_rate(values, periods)
        if len(growth) < periods + 1:
            return []
        return TimeSeriesAnalyzer.growth_rate(growth, periods)

    @staticmethod
    def extract_observations(connector_result, sort_desc=True):
        """Helper to extract (date, value) tuples from connector output.

        Works with FRED, BLS, BEA output formats.
        """
        obs = connector_result.get('observations', [])
        if not obs:
            # Try nested data format
            data = connector_result.get('data', {})
            if isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, dict) and 'observations' in val:
                        obs = val['observations']
                        break

        result = []
        for o in obs:
            date = o.get('date', o.get('year', o.get('time', '')))
            value = o.get('value')
            if value is not None:
                try:
                    result.append((str(date), float(value)))
                except (ValueError, TypeError):
                    continue

        if sort_desc:
            result.sort(key=lambda x: x[0], reverse=True)
        return result

    def analyze_series(self, connector_result, frequency='monthly'):
        """Full analysis of a single series — compute all derived indicators.

        Args:
            connector_result: output from any connector method
            frequency: 'monthly', 'quarterly', 'daily'

        Returns:
            dict with all computed indicators
        """
        values = self.extract_observations(connector_result)
        if len(values) < 3:
            return {'error': 'insufficient_data', 'count': len(values)}

        # Set periods based on frequency
        if frequency == 'monthly':
            short_period = 1
            yoy_period = 12
        elif frequency == 'quarterly':
            short_period = 1
            yoy_period = 4
        else:
            short_period = 1
            yoy_period = 252  # daily

        result = {
            'latest': values[0] if values else None,
            'count': len(values),
            'period_change': self.growth_rate(values, short_period),
            'z_scores': self.z_score(values),
            'momentum': self.momentum(values),
            'regime_changes': self.detect_regime_change(values),
        }

        if len(values) >= yoy_period + 1:
            result['yoy_change'] = self.growth_rate(values, yoy_period)

        if len(values) >= short_period * 2 + 1:
            result['acceleration'] = self.acceleration(values, short_period)

        return result
