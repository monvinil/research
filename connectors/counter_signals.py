"""
Proactive counter-signal search module.

For every high-scoring signal, this module actively searches for
evidence that CONTRADICTS the signal. This prevents confirmation bias
and catches risks early (before Agent B verification).

Usage:
    from connectors.counter_signals import CounterSignalSearcher
    searcher = CounterSignalSearcher(web_connector)
    counter_evidence = searcher.search_against(signal)
"""
import json


class CounterSignalSearcher:
    """Searches for evidence against high-scoring signals."""

    def __init__(self, web_connector):
        """
        Args:
            web_connector: An initialized WebSearchConnector instance
        """
        self.web = web_connector

    def search_against(self, signal: dict, num_results: int = 8) -> dict:
        """
        Given a signal dict, search for counter-evidence.

        Args:
            signal: Signal dict with at least 'headline', 'signal_type',
                   'affected_industries' fields
            num_results: Results per query

        Returns:
            dict with counter-evidence organized by category
        """
        headline = signal.get('headline', '')
        industries = signal.get('affected_industries', [])
        signal_type = signal.get('signal_type', '')
        signal_id = signal.get('signal_id', 'unknown')

        counter_evidence = {
            'parent_signal_id': signal_id,
            'signal_headline': headline,
            'counter_categories': {}
        }

        # 1. Search for incumbent resilience
        if industries:
            industry = industries[0] if isinstance(industries, list) else industries
            queries = [
                f"{industry} industry growth strong 2025 2026",
                f"{industry} companies thriving despite AI",
                f"{industry} incumbent advantage moat",
            ]
            results = self.web.search_custom(queries, num_results=num_results)
            counter_evidence['counter_categories']['incumbent_resilience'] = results

        # 2. Search for regulatory barriers
        if industries:
            industry = industries[0] if isinstance(industries, list) else industries
            results = self.web.search_regulatory(industry, num_results=num_results)
            counter_evidence['counter_categories']['regulatory_barriers'] = results

        # 3. Search for failed precedents
        if signal_type in ('liquidation_cascade', 'dead_business_revival', 'infrastructure_overhang'):
            queries = [
                f"{headline} startup failed",
                f"{headline} not working challenges",
            ]
            results = self.web.search_custom(queries, num_results=num_results)
            counter_evidence['counter_categories']['failed_precedents'] = results

        # 4. Search for competitive saturation
        if industries:
            industry = industries[0] if isinstance(industries, list) else industries
            results = self.web.search_competitors(industry, num_results=num_results)
            counter_evidence['counter_categories']['competitive_landscape'] = results

        # 5. Search for contradicting data
        queries = [
            f"{headline} wrong misleading overstated",
            f"{headline} criticism skepticism",
        ]
        results = self.web.search_custom(queries, num_results=num_results)
        counter_evidence['counter_categories']['contradicting_analysis'] = results

        # Summarize
        total_results = sum(
            len(v.get('results', [])) if isinstance(v, dict) else 0
            for v in counter_evidence['counter_categories'].values()
        )
        counter_evidence['total_counter_results'] = total_results

        return counter_evidence

    def batch_search(self, signals: list, score_threshold: float = 7.0, num_results: int = 5) -> list:
        """
        Search for counter-evidence against all signals above threshold.

        Args:
            signals: List of signal dicts
            score_threshold: Only search against signals scoring above this
            num_results: Results per query (lower for batch to manage volume)

        Returns:
            List of counter-evidence dicts
        """
        results = []
        for signal in signals:
            score = signal.get('relevance_score', 0)
            if isinstance(score, (int, float)) and score >= score_threshold:
                counter = self.search_against(signal, num_results=num_results)
                results.append(counter)
        return results
