"""Structural economic analysis — HHI, shift-share, Bass diffusion, sector dependency.

These are the deeper economic models that connect raw data to the
Principles Engine's theoretical framework.
"""

import math
from .timeseries import TimeSeriesAnalyzer


class StructuralAnalyzer:
    """Deep structural economic analysis tools."""

    def __init__(self):
        self.ts = TimeSeriesAnalyzer()

    @staticmethod
    def herfindahl_hirschman_index(market_shares):
        """Compute HHI — market concentration measure.

        Args:
            market_shares: list of (name, share) where share is 0-100 percent

        Returns:
            dict with HHI score, interpretation, and concentration level

        HHI < 1500 = unconcentrated (competitive, hard to disrupt)
        HHI 1500-2500 = moderate concentration (some opportunity)
        HHI > 2500 = highly concentrated (incumbent power, hard entry)
        """
        if not market_shares:
            return {'hhi': 0, 'level': 'unknown', 'count': 0}

        total = sum(s for _, s in market_shares)
        if total == 0:
            return {'hhi': 0, 'level': 'unknown', 'count': 0}

        # Normalize to percentages
        normalized = [(n, s / total * 100) for n, s in market_shares]
        hhi = sum(s ** 2 for _, s in normalized)

        if hhi < 1500:
            level = 'unconcentrated'
            interpretation = (
                'Fragmented market — many small players. Disruption is easier '
                'but so is competition. Best for platform/aggregation plays.'
            )
        elif hhi < 2500:
            level = 'moderate'
            interpretation = (
                'Moderate concentration — a few significant players but room for entry. '
                'Target the long tail of smaller firms for initial traction.'
            )
        else:
            level = 'concentrated'
            interpretation = (
                'Highly concentrated — dominated by few players with structural moats. '
                'Direct competition is expensive. Look for underserved niches or '
                'complementary positions.'
            )

        return {
            'hhi': round(hhi, 1),
            'level': level,
            'interpretation': interpretation,
            'top_players': sorted(normalized, key=lambda x: x[1], reverse=True)[:10],
            'count': len(market_shares),
        }

    @staticmethod
    def shift_share_analysis(region_data, national_data):
        """Shift-share decomposition — separate national, industry, and regional effects.

        Answers: is this region/sector declining because the whole economy is
        declining, because the industry is declining nationally, or because
        this specific region/sector has unique problems?

        Args:
            region_data: dict of {industry: {t0: employment_t0, t1: employment_t1}}
            national_data: dict of {industry: {t0: employment_t0, t1: employment_t1}}

        Returns:
            dict with national_share, industry_mix, competitive_share per industry
        """
        # Total national growth rate
        nat_total_t0 = sum(d['t0'] for d in national_data.values())
        nat_total_t1 = sum(d['t1'] for d in national_data.values())
        if nat_total_t0 == 0:
            return {'error': 'no_national_data'}
        nat_growth = (nat_total_t1 - nat_total_t0) / nat_total_t0

        results = {}
        for industry in region_data:
            reg = region_data[industry]
            if industry not in national_data:
                continue

            nat = national_data[industry]
            reg_t0 = reg['t0']

            if reg_t0 == 0 or nat['t0'] == 0:
                continue

            # National share: what would've happened if region grew at national rate
            national_share = reg_t0 * nat_growth

            # Industry mix: industry-specific growth vs national average
            ind_growth = (nat['t1'] - nat['t0']) / nat['t0']
            industry_mix = reg_t0 * (ind_growth - nat_growth)

            # Competitive share: region's deviation from national industry growth
            reg_growth = (reg['t1'] - reg['t0']) / reg_t0
            competitive_share = reg_t0 * (reg_growth - ind_growth)

            results[industry] = {
                'national_share': round(national_share, 2),
                'industry_mix': round(industry_mix, 2),
                'competitive_share': round(competitive_share, 2),
                'total_change': round(reg['t1'] - reg['t0'], 2),
                'interpretation': (
                    'positive competitive_share = region outperforming national '
                    'industry trend (unique local advantage). Negative = region '
                    'has unique problems beyond national/industry trends.'
                ),
            }

        return results

    @staticmethod
    def bass_diffusion_position(current_adoption, total_addressable,
                                 innovation_coeff=0.03, imitation_coeff=0.38):
        """Bass diffusion S-curve — where is AI adoption in this sector?

        The Bass model predicts technology adoption follows an S-curve.
        Knowing WHERE on the curve we are determines strategy:
        - Pre-takeoff (< 10%): high risk, high reward, need evangelism
        - Takeoff (10-50%): growth phase, ride the wave
        - Late majority (50-84%): competition intensifies, need differentiation
        - Laggards (> 84%): market mature, commodity pricing

        Args:
            current_adoption: current adopter count or percentage
            total_addressable: total potential market
            innovation_coeff: p in Bass model (external influence)
            imitation_coeff: q in Bass model (word-of-mouth)

        Returns:
            dict with position, phase, growth_rate, time_to_peak
        """
        if total_addressable == 0:
            return {'error': 'zero_market'}

        adoption_pct = current_adoption / total_addressable * 100

        if adoption_pct < 2.5:
            phase = 'innovators'
            strategy = (
                'Very early — only innovators adopting. High risk but first-mover '
                'advantage. Need to evangelize and prove concept. Timing risk is highest.'
            )
        elif adoption_pct < 16:
            phase = 'early_adopters'
            strategy = (
                'Early adopter phase — market is real but small. This is the optimal '
                'entry window for a startup: enough proof of demand, not yet crowded.'
            )
        elif adoption_pct < 50:
            phase = 'early_majority'
            strategy = (
                'Early majority — growth is accelerating. Competition is real. '
                'Need clear differentiation. Best for well-funded entrants or '
                'those with unique distribution.'
            )
        elif adoption_pct < 84:
            phase = 'late_majority'
            strategy = (
                'Late majority — market is maturing. Price competition intensifies. '
                'Consolidation phase — look for acquisition targets, not new entry.'
            )
        else:
            phase = 'laggards'
            strategy = (
                'Market saturated. Only laggards remain. Commodity pricing. '
                'Not attractive for new entry unless you have radical cost advantage.'
            )

        # Estimate instantaneous growth rate from Bass model
        p, q = innovation_coeff, imitation_coeff
        f = adoption_pct / 100  # fraction adopted
        if f < 1:
            instant_growth = (p + q * f) * (1 - f)
        else:
            instant_growth = 0

        # Time to peak adoption rate
        if q > p and q > 0:
            time_to_peak = math.log(q / p) / (p + q) if p > 0 else float('inf')
        else:
            time_to_peak = 0

        return {
            'adoption_pct': round(adoption_pct, 2),
            'phase': phase,
            'strategy': strategy,
            'instantaneous_growth_rate': round(instant_growth, 4),
            'time_to_peak_periods': round(time_to_peak, 1),
            'bass_parameters': {'p': p, 'q': q},
        }

    @staticmethod
    def baumol_stored_energy(sector_wage, economy_avg_wage,
                              sector_productivity_growth,
                              economy_productivity_growth):
        """Compute Baumol's cost disease "stored energy" for a sector.

        Sectors where wages have risen with the economy but productivity
        has NOT have the most "stored energy" for AI disruption.

        Stored energy = (wage_premium) * (1 / relative_productivity_growth)

        Higher stored energy = more potential for AI cost collapse.
        """
        if economy_avg_wage == 0 or economy_productivity_growth == 0:
            return {'error': 'zero_denominator'}

        wage_premium = sector_wage / economy_avg_wage
        relative_productivity = (
            sector_productivity_growth / economy_productivity_growth
            if economy_productivity_growth != 0 else 0
        )

        if relative_productivity == 0:
            stored_energy = wage_premium * 10  # Cap at 10x for zero-productivity sectors
        else:
            stored_energy = wage_premium / relative_productivity

        return {
            'wage_premium': round(wage_premium, 4),
            'relative_productivity_growth': round(relative_productivity, 4),
            'stored_energy': round(stored_energy, 4),
            'interpretation': (
                f'Wage premium: {wage_premium:.2f}x economy average. '
                f'Relative productivity growth: {relative_productivity:.2f}x economy average. '
                f'Stored energy: {stored_energy:.2f} — '
                f'{"HIGH" if stored_energy > 2 else "MODERATE" if stored_energy > 1 else "LOW"} '
                f'disruption potential.'
            ),
        }

    @staticmethod
    def input_output_propagation(io_table, shocked_industry, shock_pct=0.20):
        """Trace disruption propagation through input-output linkages.

        If industry X's output drops by shock_pct, which downstream
        industries are affected and by how much?

        Args:
            io_table: dict of {industry: {input_industry: share}}
                      (share = proportion of inputs from that industry)
            shocked_industry: the industry being disrupted
            shock_pct: magnitude of disruption (0.0 to 1.0)

        Returns:
            dict with first-order and second-order impacts
        """
        first_order = {}
        second_order = {}

        for industry, inputs in io_table.items():
            if shocked_industry in inputs:
                share = inputs[shocked_industry]
                impact = share * shock_pct
                first_order[industry] = round(impact, 6)

                # Second-order: industries that depend on first-order affected
                for ind2, inputs2 in io_table.items():
                    if industry in inputs2:
                        share2 = inputs2[industry]
                        impact2 = share2 * impact
                        if ind2 not in second_order:
                            second_order[ind2] = 0
                        second_order[ind2] += impact2

        # Round second-order
        second_order = {k: round(v, 6) for k, v in second_order.items()}

        # Sort by impact
        first_sorted = sorted(first_order.items(), key=lambda x: x[1], reverse=True)
        second_sorted = sorted(second_order.items(), key=lambda x: x[1], reverse=True)

        return {
            'shocked_industry': shocked_industry,
            'shock_magnitude': shock_pct,
            'first_order_impacts': first_sorted[:20],
            'second_order_impacts': second_sorted[:20],
            'total_first_order_impact': round(sum(first_order.values()), 6),
            'total_second_order_impact': round(sum(second_order.values()), 6),
        }

    @staticmethod
    def sector_vulnerability_score(employment, wage_premium, productivity_lag,
                                    competitive_density, regulatory_friction,
                                    tech_readiness):
        """Compute composite vulnerability score for a sector.

        This is the scoring function that should replace the current
        flat 0-100 scoring. Each component is 0-10, weighted.

        Args:
            employment: total employment in sector (market size signal)
            wage_premium: sector wage / economy average (Baumol stored energy)
            productivity_lag: 1 - (sector productivity growth / economy avg)
            competitive_density: 0-10, higher = more crowded
            regulatory_friction: 0-10, higher = harder to enter
            tech_readiness: 0-10, higher = more AI-ready

        Returns:
            dict with score, components, and interpretation
        """
        # Opportunity score components
        baumol_score = min(10, wage_premium * 3)
        productivity_score = min(10, productivity_lag * 10)
        size_score = min(10, math.log10(max(employment, 1)) - 3)  # log scale

        # Barrier score components (negative = harder)
        density_penalty = competitive_density
        regulatory_penalty = regulatory_friction

        # Net score: opportunity minus barriers
        opportunity = (
            baumol_score * 0.25 +
            productivity_score * 0.20 +
            size_score * 0.15 +
            tech_readiness * 0.15
        )

        barriers = (
            density_penalty * 0.15 +
            regulatory_penalty * 0.10
        )

        raw_score = (opportunity - barriers) * 10
        final_score = max(0, min(100, raw_score))

        return {
            'score': round(final_score, 1),
            'components': {
                'baumol_stored_energy': round(baumol_score, 2),
                'productivity_lag': round(productivity_score, 2),
                'market_size': round(size_score, 2),
                'tech_readiness': tech_readiness,
                'competitive_density_penalty': round(density_penalty, 2),
                'regulatory_friction_penalty': round(regulatory_penalty, 2),
            },
            'opportunity_raw': round(opportunity, 2),
            'barriers_raw': round(barriers, 2),
        }
