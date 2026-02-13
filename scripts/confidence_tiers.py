#!/usr/bin/env python3
"""v3-13: Add confidence_tier and evidence_quality fields to all models.

Maps source_batch → confidence tier (HIGH/MODERATE/LOW).
Computes evidence_quality score (0-10) from available data fields.
"""

import json
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

# ── Source Batch → Confidence Tier ──────────────────────────────────
BATCH_TIER = {
    # HIGH: Dedicated sector deep dives with real analysis
    'v310_decomposition': 'HIGH',
    'v39_deep_dive_manufacturing': 'HIGH',
    'v39_deep_dive_micro_firm': 'HIGH',
    'v38_deep_dive_retail': 'HIGH',
    'v38_deep_dive_healthcare': 'HIGH',
    'v37_deep_dive_it_services': 'HIGH',
    'v37_deep_dive_management': 'HIGH',
    'v37_deep_dive_real_estate': 'HIGH',
    'v37_deep_dive_securities': 'HIGH',
    'v37_healthcare_monoculture': 'HIGH',
    'v36_deep_dive_defense_deep_dive': 'HIGH',
    'v36_deep_dive_education_deep_dive': 'HIGH',
    'v36_deep_dive_information_deep_dive': 'HIGH',
    'v36_deep_dive_utilities_deep_dive': 'HIGH',
    'v36_deep_dive_v35_model_cards': 'HIGH',
    # MODERATE: Manual curation but not full deep dive
    'new_macro_45': 'MODERATE',
    'top_40_deep': 'MODERATE',
    # LOW: Batch-generated or legacy
    'expansion_123': 'LOW',
    'mid_41to112': 'LOW',
    'v3-2_cycle': 'LOW',
}


def get_confidence_tier(source_batch):
    """Determine confidence tier from source_batch string."""
    if not source_batch:
        return 'LOW'

    # Exact match first
    if source_batch in BATCH_TIER:
        return BATCH_TIER[source_batch]

    # v3-12_* prefix → HIGH (new deep dives)
    if source_batch.startswith('v3-12_'):
        return 'HIGH'

    # v3-13_* prefix → HIGH (this cycle's deep dives)
    if source_batch.startswith('v3-13_'):
        return 'HIGH'

    # Any deep_dive in name → HIGH
    if 'deep_dive' in source_batch:
        return 'HIGH'

    # Any decomposition → HIGH
    if 'decomposition' in source_batch:
        return 'HIGH'

    # Default
    return 'MODERATE'


def compute_evidence_quality(model):
    """Compute evidence quality score (0-10) from available data fields."""
    score = 0

    # Has deep_dive_evidence (most important signal)
    dde = model.get('deep_dive_evidence')
    if dde:
        if isinstance(dde, dict):
            score += 4
        elif isinstance(dde, str) and len(dde) > 50:
            score += 4
        elif dde:
            score += 2

    # Has macro_source with specifics
    ms = model.get('macro_source', '') or ''
    if len(ms) > 10:
        score += 2
    elif ms:
        score += 1

    # Has VCR evidence
    if model.get('vcr_evidence'):
        score += 1

    # One-liner quality (length as proxy for specificity)
    one_liner = model.get('one_liner', '') or ''
    if len(one_liner) > 100:
        score += 2
    elif len(one_liner) > 50:
        score += 1

    # Has falsification criteria
    fc = model.get('falsification_criteria')
    if fc and isinstance(fc, list) and len(fc) > 0:
        score += 1

    return min(score, 10)


def main():
    print("=" * 70)
    print("v3-13 Confidence Tiers & Evidence Quality")
    print("=" * 70)

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)

    models = data['models']
    print(f"\nLoaded {len(models)} models")

    tier_counts = {'HIGH': 0, 'MODERATE': 0, 'LOW': 0}
    eq_scores = []

    for m in models:
        sb = m.get('source_batch', '')
        tier = get_confidence_tier(sb)
        m['confidence_tier'] = tier
        tier_counts[tier] += 1

        eq = compute_evidence_quality(m)
        m['evidence_quality'] = eq
        eq_scores.append(eq)

    print(f"\n  Confidence Tier Distribution:")
    for tier, count in tier_counts.items():
        pct = count / len(models) * 100
        print(f"    {tier}: {count} ({pct:.1f}%)")

    import statistics
    print(f"\n  Evidence Quality (0-10):")
    print(f"    Mean: {statistics.mean(eq_scores):.1f}")
    print(f"    Median: {statistics.median(eq_scores):.1f}")
    print(f"    Min: {min(eq_scores)}, Max: {max(eq_scores)}")

    # Distribution buckets
    from collections import Counter
    eq_dist = Counter(eq_scores)
    print(f"    Distribution: {dict(sorted(eq_dist.items()))}")

    with open(NORMALIZED_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  Saved to {NORMALIZED_FILE}")


if __name__ == '__main__':
    main()
