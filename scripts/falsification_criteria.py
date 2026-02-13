#!/usr/bin/env python3
"""v3-13: Generate falsification criteria for all models.

Produces 2-4 criteria per model based on:
- Architecture-specific risk templates
- Sector-specific risk templates (2-digit NAICS)
- Force reversal risks (from forces_v3)
- Keyword-derived risks from one_liner/evidence
"""

import json
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

# ── Architecture-Specific Risks ─────────────────────────────────────
ARCH_RISKS = {
    'acquire_and_modernize': [
        'Acquisition multiples rise above 5x EBITDA, making roll-up economics unviable',
        'Owner retirement pace slows dramatically as succession planning programs succeed',
    ],
    'rollup_consolidation': [
        'Acquisition multiples rise above 5x EBITDA, making consolidation uneconomical',
        'Integration costs exceed 30% of acquisition price for 3+ consecutive deals',
    ],
    'full_service_replacement': [
        'Incumbent firms successfully deploy AI internally, eliminating third-party replacement demand',
        'Service quality from AI-first delivery fails to match human-delivered outcomes in key use cases',
    ],
    'vertical_saas': [
        'Horizontal platform (Salesforce/Microsoft/Google) adds vertical-specific AI features matching specialist depth',
        'Customer acquisition cost exceeds 18-month payback period in target segment',
    ],
    'data_compounding': [
        'Open-source or foundation model alternatives eliminate proprietary data moat advantages',
        'Data privacy regulations (state-level CCPA variants) restrict data aggregation business model',
    ],
    'platform_infrastructure': [
        'Cloud hyperscalers (AWS/Azure/GCP) build equivalent infrastructure as native features',
        'Market fragments into point solutions rather than consolidating onto platforms',
    ],
    'marketplace_network': [
        'Supply-side participants disintermediate the platform through direct relationships',
        'Network effects fail to materialize due to low transaction frequency in the sector',
    ],
    'regulatory_moat_builder': [
        'Regulatory framework simplifies or deregulates, eliminating compliance complexity advantage',
        'Incumbent compliance vendors add AI features faster than startups can build regulatory expertise',
    ],
    'physical_production_ai': [
        'Hardware costs fail to decline on expected trajectory, keeping ROI below adoption threshold',
        'Labor unions or workforce resistance blocks deployment at critical mass of facilities',
    ],
    'arbitrage_window': [
        'Entry window closes faster than expected as incumbents or fast-followers saturate the opportunity',
        'The structural imbalance creating the arbitrage corrects naturally before scale is achieved',
    ],
    'ai_copilot': [
        'Foundation model APIs commoditize the copilot layer, eliminating differentiation',
        'User adoption stalls as professionals resist AI-augmented workflows in daily tasks',
    ],
    'robotics_automation': [
        'Robotics hardware costs remain above adoption threshold for target customer segment',
        'Regulatory approval for autonomous operation takes 3+ years longer than projected',
    ],
    'compliance_automation': [
        'Regulatory environment simplifies, reducing demand for automated compliance',
        'Large consulting firms (Big 4) build competitive compliance automation platforms',
    ],
    'service_platform': [
        'Service delivery economics fail to improve sufficiently vs incumbent manual approaches',
        'Customer churn exceeds 5% monthly as services prove insufficiently differentiated',
    ],
    'hardware_ai': [
        'Hardware component costs fail to decline on expected trajectory',
        'Software-only solutions prove sufficient, eliminating need for specialized hardware',
    ],
}

# ── Sector-Specific Risks (2-digit NAICS) ───────────────────────────
SECTOR_RISKS = {
    '11': 'Agricultural commodity price collapse below AI ROI threshold for precision farming adoption',
    '21': 'Energy transition accelerates faster than expected, stranding fossil fuel extraction technology investments',
    '22': 'Utility regulatory commissions block AI-driven rate optimization or grid management changes',
    '23': 'Construction labor shortage resolves through immigration reform, reducing automation urgency',
    '31': 'Food safety AI regulation adds 2+ years to approval timeline, delaying deployment',
    '32': 'Chemical/materials manufacturing consolidates further, reducing addressable SMB market',
    '33': 'Reshoring momentum reverses as tariff policy changes eliminate onshoring economic rationale',
    '42': 'E-commerce direct-to-consumer growth eliminates wholesale intermediary demand',
    '44': 'Retail footprint contraction accelerates beyond AI-optimization ability to offset',
    '45': 'General merchandise retail consolidates to 3-4 dominant players, locking out new technology vendors',
    '48': 'Autonomous vehicle deployment timeline extends 5+ years beyond current projections',
    '49': 'Warehouse automation ROI fails to justify capital expenditure for mid-size operators',
    '51': 'AI-generated content quality plateau reduces willingness to pay for AI content tools',
    '52': 'Interest rate normalization eliminates distress-driven financial services opportunities',
    '53': 'Commercial real estate market stabilizes, reducing distressed asset opportunities',
    '54': 'Professional licensing bodies restrict AI-assisted service delivery in regulated professions',
    '55': 'Management holding companies resist AI adoption due to fiduciary risk concerns',
    '56': 'Gig economy regulation (AB5-like laws) disrupts staffing platform economics',
    '61': 'AI tutoring efficacy studies show no improvement over traditional methods, killing adoption',
    '62': 'FDA reverses AI device approval pathway or adds significant new regulatory barriers',
    '71': 'Live experience premium strengthens, making AI entertainment substitutes less attractive',
    '72': 'Minimum wage increases compress restaurant margins beyond AI savings capacity',
    '81': 'Local service businesses resist technology adoption at rates exceeding 70% for 3+ years',
    '92': 'Government AI procurement freeze due to bias/safety concerns extends beyond 2028',
}

# ── Force Reversal Risks ────────────────────────────────────────────
FORCE_RISKS = {
    'F1': 'Foundation model capabilities plateau or inference costs stop declining for 18+ months',
    'F2': 'Immigration policy reversal fills labor gaps, reducing demographic pressure on automation',
    'F3': 'US-China trade normalization reduces geopolitical urgency for reshoring and supply chain redundancy',
    'F4': 'Interest rate cuts to sub-3% re-liquefy capital markets, eliminating distressed asset opportunities',
    'F5': 'Consumer and enterprise AI trust rises above 70% (Edelman), eliminating fear-friction demand',
    'F6': 'Grid capacity expands ahead of data center demand, eliminating energy constraint premiums',
}


def generate_criteria(model):
    """Generate 2-4 falsification criteria for a model."""
    arch = model.get('architecture', '')
    naics = model.get('sector_naics', '')[:2]
    forces = model.get('forces_v3', [])
    one_liner = (model.get('one_liner', '') or '').lower()

    criteria = []

    # 1. Architecture-specific risks (1-2)
    arch_risks = ARCH_RISKS.get(arch, ARCH_RISKS.get('full_service_replacement', []))
    criteria.extend(arch_risks[:2])

    # 2. Sector-specific risk (1)
    if naics in SECTOR_RISKS:
        criteria.append(SECTOR_RISKS[naics])

    # 3. Force reversal risk (1) — pick the first/strongest force
    if forces:
        primary_force = forces[0] if isinstance(forces, list) else str(forces)
        # Normalize force ID
        force_key = primary_force.replace('_technology', '').replace('_demographics', '') \
                                  .replace('_geopolitics', '').replace('_capital', '') \
                                  .replace('_psychology', '').replace('_energy', '')
        if force_key in FORCE_RISKS:
            criteria.append(FORCE_RISKS[force_key])

    # 4. Keyword-derived risks
    if 'defense' in one_liner or 'military' in one_liner:
        criteria.append('Defense budget priorities shift away from AI/autonomy toward conventional systems')
    elif 'healthcare' in one_liner or 'clinical' in one_liner:
        if not any('FDA' in c for c in criteria):
            criteria.append('Medical liability frameworks hold AI-assisted care to higher standards than human-only care')
    elif 'autonomous' in one_liner or 'self-driving' in one_liner:
        criteria.append('Fatal autonomous system incident triggers regulatory moratorium across the sector')

    # Deduplicate and cap at 4
    seen = set()
    unique = []
    for c in criteria:
        c_norm = c.lower().strip()
        if c_norm not in seen:
            seen.add(c_norm)
            unique.append(c)
    return unique[:4]


def main():
    print("=" * 70)
    print("v3-13 Falsification Criteria Generation")
    print("=" * 70)

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)

    models = data['models']
    print(f"\nLoaded {len(models)} models")

    already_have = 0
    generated = 0
    criteria_counts = []

    for m in models:
        existing = m.get('falsification_criteria')
        if existing and isinstance(existing, list) and len(existing) > 0:
            already_have += 1
            criteria_counts.append(len(existing))
            continue

        criteria = generate_criteria(m)
        m['falsification_criteria'] = criteria
        generated += 1
        criteria_counts.append(len(criteria))

    print(f"\n  Already had criteria: {already_have}")
    print(f"  Generated criteria: {generated}")
    print(f"  Total with criteria: {already_have + generated}/{len(models)}")

    import statistics
    print(f"\n  Criteria per model:")
    print(f"    Mean: {statistics.mean(criteria_counts):.1f}")
    print(f"    Min: {min(criteria_counts)}, Max: {max(criteria_counts)}")

    # Verify none are empty
    empty = [m['id'] for m in models if not m.get('falsification_criteria')]
    if empty:
        print(f"\n  WARNING: {len(empty)} models still have no criteria!")
    else:
        print(f"  All {len(models)} models have falsification criteria")

    # Sample output
    print(f"\n  Sample (first 3 models):")
    for m in models[:3]:
        print(f"    {m['id']} ({m.get('architecture', '?')}):")
        for c in m.get('falsification_criteria', []):
            print(f"      - {c}")

    with open(NORMALIZED_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  Saved to {NORMALIZED_FILE}")


if __name__ == '__main__':
    main()
