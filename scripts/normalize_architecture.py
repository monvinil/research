#!/usr/bin/env python3
"""v3-13: Normalize architecture taxonomy from 54 types to 15 canonical.

Fixes:
- 15 blank architecture fields (inferred from sector + one_liner)
- 44 non-canonical types mapped to 15 canonical
- Preserves original architecture in `architecture_original` field
"""

import json
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

# ── 15 Canonical Architecture Types ──────────────────────────────────
CANONICAL = {
    # Original 10 from enumerate_models.py
    'acquire_and_modernize',
    'rollup_consolidation',
    'full_service_replacement',
    'data_compounding',
    'platform_infrastructure',
    'vertical_saas',
    'marketplace_network',
    'regulatory_moat_builder',
    'physical_production_ai',
    'arbitrage_window',
    # 5 new canonical types
    'ai_copilot',
    'robotics_automation',
    'compliance_automation',
    'service_platform',
    'hardware_ai',
}

# ── Mapping: non-canonical → canonical ───────────────────────────────
ARCH_MAPPING = {
    # Vague catch-alls
    'platform': 'platform_infrastructure',
    'saas': 'vertical_saas',
    'automation': 'vertical_saas',
    'workflow_automation': 'vertical_saas',
    'service': 'service_platform',

    # Marketplace variants
    'marketplace': 'marketplace_network',
    'marketplace_platform': 'marketplace_network',
    'platform_marketplace': 'marketplace_network',
    'marketplace_optimizer': 'marketplace_network',

    # Rollup variants
    'rollup': 'rollup_consolidation',
    'roll_up_modernize': 'rollup_consolidation',

    # Platform variants
    'network_platform': 'platform_infrastructure',
    'infrastructure_platform': 'platform_infrastructure',
    'product_platform': 'platform_infrastructure',
    'product': 'platform_infrastructure',
    'platform_saas': 'vertical_saas',
    'horizontal_saas': 'vertical_saas',

    # Service/advisory cluster → service_platform
    'managed_service': 'service_platform',
    'advisory': 'service_platform',
    'advisory_platform': 'service_platform',
    'academy_platform': 'service_platform',
    'hybrid_service': 'service_platform',
    'platform_service': 'service_platform',

    # Hardware/IoT cluster → hardware_ai
    'hardware_plus_saas': 'hardware_ai',
    'iot_platform': 'hardware_ai',
    'digital_twin': 'hardware_ai',
    'physical_product_platform': 'hardware_ai',

    # Robotics cluster → robotics_automation
    'autonomous_systems': 'robotics_automation',

    # Specialized → closest canonical
    'project_developer': 'full_service_replacement',
    'project_development': 'full_service_replacement',
    'distress_operator': 'acquire_and_modernize',
    'geographic_arbitrage': 'arbitrage_window',
    'fear_economy_capture': 'regulatory_moat_builder',

    # Analytics/intelligence → data_compounding or vertical_saas
    'predictive_analytics': 'data_compounding',
    'logistics_optimization': 'vertical_saas',
    'supply_chain_optimization': 'vertical_saas',
    'decision_intelligence': 'data_compounding',
    'simulation_modeling': 'data_compounding',

    # Fintech/insurtech → vertical_saas or regulatory
    'embedded_fintech': 'platform_infrastructure',
    'insurtech': 'vertical_saas',
    'regtech': 'compliance_automation',

    # Sector-specific → vertical_saas
    'cybersecurity': 'vertical_saas',
    'edtech': 'vertical_saas',
    'healthtech': 'vertical_saas',
    'proptech': 'vertical_saas',
    'climate_tech': 'vertical_saas',
    'agritech': 'vertical_saas',
    'content_automation': 'ai_copilot',
    'creator_economy': 'platform_infrastructure',
    'micro_firm_os': 'vertical_saas',
}


def infer_architecture(model):
    """Infer architecture for models with blank/missing architecture field."""
    mid = model.get('id', '')
    naics = model.get('sector_naics', '')[:2]
    one_liner = (model.get('one_liner', '') or '').lower()
    name = (model.get('name', '') or '').lower()

    # Defense with robotics/drone keywords
    if ('DEF' in mid or 'defense' in one_liner) and any(w in one_liner for w in ['drone', 'robot', 'autonomous', 'uav']):
        return 'robotics_automation'

    # Compliance keywords
    if any(w in one_liner for w in ['compliance', 'regulatory', 'cmmc', 'hipaa', 'gdpr']):
        return 'compliance_automation'

    # Acquisition/rollup keywords
    if any(w in one_liner for w in ['acquire', 'roll-up', 'rollup', 'consolidat']):
        return 'acquire_and_modernize'

    # SaaS/platform keywords
    if any(w in one_liner for w in ['saas', 'subscription', 'platform']):
        return 'vertical_saas'

    # Marketplace keywords
    if any(w in one_liner for w in ['marketplace', 'matching', 'two-sided']):
        return 'marketplace_network'

    # Data keywords
    if any(w in one_liner for w in ['data flywheel', 'data compound', 'intelligence']):
        return 'data_compounding'

    # Manufacturing/hardware
    if naics in ('31', '32', '33') and any(w in one_liner for w in ['robot', 'cobot', 'hardware']):
        return 'physical_production_ai'

    # Default: most common type
    return 'full_service_replacement'


def main():
    print("=" * 70)
    print("v3-13 Architecture Taxonomy Normalization")
    print("=" * 70)

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)

    models = data['models']
    print(f"\nLoaded {len(models)} models")

    # Count before
    from collections import Counter
    before = Counter(m.get('architecture', '') for m in models)
    print(f"Architecture types BEFORE: {len(before)}")
    print(f"  Canonical (in 15): {sum(v for k, v in before.items() if k in CANONICAL)}")
    print(f"  Non-canonical: {sum(v for k, v in before.items() if k and k not in CANONICAL)}")
    print(f"  Blank: {before.get('', 0)}")

    # Apply normalization
    changes = 0
    blanks_fixed = 0
    unmapped = Counter()

    for m in models:
        old_arch = m.get('architecture', '') or ''

        if not old_arch:
            # Blank → infer
            new_arch = infer_architecture(m)
            m['architecture_original'] = ''
            m['architecture'] = new_arch
            blanks_fixed += 1
            changes += 1
        elif old_arch in CANONICAL:
            # Already canonical → no change
            pass
        elif old_arch in ARCH_MAPPING:
            # Known mapping
            m['architecture_original'] = old_arch
            m['architecture'] = ARCH_MAPPING[old_arch]
            changes += 1
        else:
            # Unknown type — flag it
            unmapped[old_arch] += 1
            # Default to vertical_saas as safest catch-all
            m['architecture_original'] = old_arch
            m['architecture'] = 'vertical_saas'
            changes += 1

    # Count after
    after = Counter(m.get('architecture', '') for m in models)
    print(f"\nArchitecture types AFTER: {len(after)}")
    print(f"  Changes made: {changes}")
    print(f"  Blanks fixed: {blanks_fixed}")

    if unmapped:
        print(f"\n  WARNING: {len(unmapped)} unmapped types (defaulted to vertical_saas):")
        for k, v in unmapped.most_common():
            print(f"    {k}: {v}")

    print(f"\n  Distribution:")
    for arch, count in after.most_common():
        marker = " *NEW*" if arch in CANONICAL and arch not in {
            'acquire_and_modernize', 'rollup_consolidation', 'full_service_replacement',
            'data_compounding', 'platform_infrastructure', 'vertical_saas',
            'marketplace_network', 'regulatory_moat_builder', 'physical_production_ai',
            'arbitrage_window'
        } else ""
        print(f"    {arch}: {count}{marker}")

    # Verify all canonical
    non_canonical = [m['id'] for m in models if m.get('architecture', '') not in CANONICAL]
    if non_canonical:
        print(f"\n  ERROR: {len(non_canonical)} models still non-canonical!")
    else:
        print(f"\n  All {len(models)} models have canonical architecture types")

    # Save
    with open(NORMALIZED_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  Saved to {NORMALIZED_FILE}")


if __name__ == '__main__':
    main()
