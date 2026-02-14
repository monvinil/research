#!/usr/bin/env python3
"""
v5.2 Projection Promotion — Converts projected models into real corpus models.

Takes 93 algorithmically projected models from v5_model_projector.py and promotes
them into the v4 model corpus with:
- Specific business model names (not generic "Projected X for Y")
- Narrative linkage (NAICS → narrative mapping)
- Full v4 schema compliance
- Ranking integration

Usage: python3 scripts/v5_promote_projections.py
"""

import json
import sys
import statistics
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
V4_DIR = BASE / "data/v4"
V5_DIR = BASE / "data/v5"

# ──────────────────────────────────────────────────────────────────────
# Architecture → Name Templates
# ──────────────────────────────────────────────────────────────────────

# {sector} is replaced with the cleaned sector name
ARCH_NAME_TEMPLATES = {
    "vertical_saas": "AI-Native {sector} Operations Platform",
    "data_compounding": "{sector} Data Intelligence Engine",
    "marketplace_network": "AI {sector} Marketplace & Network",
    "full_service_replacement": "AI-Powered {sector} Service Platform",
    "platform_infrastructure": "{sector} AI Infrastructure Platform",
    "acquire_and_modernize": "{sector} Acquisition & AI Modernization",
    "rollup_consolidation": "{sector} AI-Enabled Consolidation Play",
    "regulatory_moat_builder": "{sector} Compliance Intelligence Platform",
    "service_platform": "{sector} AI Service Delivery Platform",
    "physical_production_ai": "AI {sector} Production Automation",
    "arbitrage_window": "{sector} Transformation Arbitrage",
    "hardware_ai": "AI-Embedded {sector} Hardware",
    "robotics_automation": "{sector} Autonomous Robotics Platform",
    "compliance_automation": "{sector} Regulatory Automation Engine",
    "ai_copilot": "{sector} AI Copilot",
    "open_core_ecosystem": "{sector} Open-Core AI Platform",
    "outcome_based": "{sector} Outcome-Based AI Service",
    "coordination_protocol": "{sector} Multi-Party Coordination Protocol",
    "enabling_infrastructure": "{sector} Enabling Infrastructure",
}

ARCH_ONELINER_TEMPLATES = {
    "vertical_saas": "AI-native vertical SaaS purpose-built for {sector_lower} — automating core workflows with sector-specific data models, compliance, and operational intelligence",
    "data_compounding": "Proprietary data engine for {sector_lower} — each transaction deepens the moat, enabling predictive analytics and competitive intelligence that compounds over time",
    "marketplace_network": "Two-sided AI marketplace connecting {sector_lower} buyers and sellers — network effects create defensibility, AI matching reduces friction and increases transaction velocity",
    "full_service_replacement": "End-to-end AI replacement for traditional {sector_lower} workflows — replaces manual processes with automated intelligence, capturing the full value chain",
    "platform_infrastructure": "Foundational AI platform enabling the {sector_lower} ecosystem — other products build on top, creating lock-in through developer adoption and integration depth",
    "acquire_and_modernize": "Acquire fragmented {sector_lower} operators from retiring owners, deploy AI operations stack, achieve 2-3x EBITDA improvement through technology modernization",
    "rollup_consolidation": "Systematic consolidation of fragmented {sector_lower} market — AI-driven integration playbook reduces post-acquisition costs and accelerates synergy realization",
    "regulatory_moat_builder": "Compliance-first AI platform for {sector_lower} — regulatory complexity becomes the moat, certified solutions command premium pricing and long retention",
    "service_platform": "AI-augmented service delivery platform for {sector_lower} — standardizes variable-quality services while preserving human judgment where it matters",
    "physical_production_ai": "AI-driven automation for {sector_lower} physical production — computer vision, robotics integration, and predictive maintenance reducing unit costs and defects",
    "arbitrage_window": "Time-limited market inefficiency in {sector_lower} transformation — early movers capture outsized returns before incumbents adapt or market matures",
    "hardware_ai": "Integrated hardware-software platform for {sector_lower} — proprietary AI embedded in purpose-built devices, creating switching costs through physical deployment",
    "robotics_automation": "Autonomous robotics platform for {sector_lower} — combining manipulation, navigation, and AI decision-making to automate physical tasks at scale",
    "compliance_automation": "Automated regulatory compliance engine for {sector_lower} — monitors rule changes, generates filings, and maintains audit trails without manual intervention",
    "ai_copilot": "AI copilot augmenting {sector_lower} professionals — enhances human expertise rather than replacing it, capturing institutional knowledge and scaling best practices",
    "open_core_ecosystem": "Open-core AI platform for {sector_lower} — free tier drives adoption, commercial features (enterprise security, SLA, integrations) capture willingness-to-pay",
    "outcome_based": "Outcome-based AI service for {sector_lower} — charges for measurable results rather than software licenses, aligning vendor and customer incentives",
    "coordination_protocol": "Multi-party coordination protocol for {sector_lower} — enables complex workflows across organizational boundaries with shared state and automated settlements",
    "enabling_infrastructure": "Low-level enabling infrastructure for {sector_lower} AI adoption — provides foundational capabilities that higher-level applications depend on",
}

# ──────────────────────────────────────────────────────────────────────
# NAICS → Narrative Mapping (from v4/narratives.json)
# ──────────────────────────────────────────────────────────────────────

# NAICS 2-digit → narrative_id (primary mappings)
NAICS_NARRATIVE_MAP = {
    "31": "TN-003", "32": "TN-003", "33": "TN-003",  # Manufacturing
    "11": "TN-003",  # Agriculture (secondary to Manufacturing)
    "52": "TN-001",  # Financial Services
    "44": "TN-014", "45": "TN-014",  # Retail Trade
    "72": "TN-014",  # Accommodation/Food (secondary to Retail)
    "62": "TN-004",  # Healthcare
    "53": "TN-012",  # Real Estate
    "54": "TN-002", "71": "TN-002",  # Professional Services
    "51": "TN-007",  # Information/Tech
    "23": "TN-006",  # Construction
    "61": "TN-009",  # Education
    "92": "TN-008",  # Government/Defense
    "21": "TN-013",  # Mining
    "56": "TN-005", "81": "TN-005",  # Admin/Support Services
    "48": "TN-005", "49": "TN-005",  # Transportation
    "22": "TN-015",  # Utilities/Energy (TN-015 or TN-011)
    "55": "TN-011",  # Management of Companies
    "42": "TN-007",  # Wholesale Trade → Info/Tech
    "N/A": "TN-016",  # Micro-Firm AI Economy
}

# ──────────────────────────────────────────────────────────────────────
# Sector Name Cleaning
# ──────────────────────────────────────────────────────────────────────

def clean_sector_name(raw_name):
    """Clean sector name for use in model names."""
    # Remove parenthetical qualifiers and cross-sector markers
    name = raw_name
    for remove in [" (Cross-Sector)", " (Cross-sector)", " — Cross-Sector Intelligence",
                   " — Emerging Category", " (Defense MRO)", " (Public Health)"]:
        name = name.replace(remove, "")
    # Shorten long names
    replacements = {
        "Mining, Quarrying, and Oil and Gas Extraction": "Mining & Extraction",
        "Healthcare and Social Assistance": "Healthcare",
        "Accommodation and Food Services": "Hospitality",
        "Administrative Services": "Admin Services",
        "Manufacturing — Food": "Food Manufacturing",
        "Manufacturing — Chemical": "Chemical Manufacturing",
        "Manufacturing — Misc": "Industrial Manufacturing",
        "Transportation/Warehousing": "Transportation",
        "Warehousing and Storage": "Warehousing",
        "Real Estate/Business Brokerage": "Real Estate",
        "Professional Services (Veterinary)": "Veterinary Services",
        "Management of Companies": "Corporate Management",
        "Other Schools and Instruction — Career Acceleration": "Career Education",
        "Gambling Industries": "Gaming & Gambling",
        "Commercial Machinery Repair": "Industrial MRO",
        "Administration of Human Resource Programs": "Public Workforce",
        "Wholesale Trade (Cross-sector)": "Wholesale Trade",
        "Retail Trade (Cross-Sector)": "Retail Trade",
        "Financial Services": "Financial Services",
        "Micro-Firm AI Economy": "Micro-Firm Economy",
    }
    for old, new in replacements.items():
        if name == old:
            return new
    return name


# ──────────────────────────────────────────────────────────────────────
# Primary Category Assignment
# ──────────────────────────────────────────────────────────────────────

def assign_primary_category(proj):
    """Assign primary_category based on scores and architecture."""
    t = proj.get("composite", 0)
    sn = proj.get("scores", {}).get("SN", 0)
    fa = proj.get("scores", {}).get("FA", 0)

    if sn >= 8 and fa >= 8:
        return "STRUCTURAL_WINNER"
    if proj.get("architecture") in ("arbitrage_window",):
        return "TIMING_ARBITRAGE"
    if proj.get("architecture") in ("regulatory_moat_builder", "compliance_automation"):
        return "FEAR_ECONOMY"
    if t >= 65:
        return "FORCE_RIDER"
    return "CONDITIONAL"


# ──────────────────────────────────────────────────────────────────────
# Category Tags
# ──────────────────────────────────────────────────────────────────────

def assign_category_tags(proj):
    """Assign multi-label category tags."""
    tags = []
    t = proj.get("composite", 0)
    sn = proj.get("scores", {}).get("SN", 0)
    fa = proj.get("scores", {}).get("FA", 0)

    if sn >= 8 and fa >= 8:
        tags.append("STRUCTURAL_WINNER")
    if t >= 65:
        tags.append("FORCE_RIDER")
    if proj.get("architecture") in ("arbitrage_window",):
        tags.append("TIMING_ARBITRAGE")
    if proj.get("architecture") in ("regulatory_moat_builder", "compliance_automation"):
        tags.append("FEAR_ECONOMY")
    if not tags:
        tags.append("CONDITIONAL")
    return tags


# ──────────────────────────────────────────────────────────────────────
# Confidence Mapping
# ──────────────────────────────────────────────────────────────────────

CONF_MAP = {
    "HIGH": "HIGH",
    "MEDIUM": "MODERATE",
    "LOW": "LOW",
}


# ──────────────────────────────────────────────────────────────────────
# Main Promotion
# ──────────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("  Written: {} ({})".format(path, type(data).__name__))


def promote_projections():
    print("=" * 70)
    print("v5.2 PROJECTION PROMOTION")
    print("=" * 70)

    # Load data
    projections = load_json(V5_DIR / "projections.json")
    models_data = load_json(V4_DIR / "models.json")
    narratives = load_json(V4_DIR / "narratives.json")
    state = load_json(V5_DIR / "state.json")

    projs = projections.get("projections", [])
    models = models_data.get("models", models_data) if isinstance(models_data, dict) else models_data
    existing_ids = {m["id"] for m in models}
    print("\n  Existing models: {}".format(len(models)))
    print("  Projections to promote: {}".format(len(projs)))

    # Build narrative lookup for updating outputs
    narr_lookup = {}
    for n in narratives["narratives"]:
        narr_lookup[n["narrative_id"]] = n

    # Track new IDs per NAICS for sequential numbering
    naics_seq = {}
    promoted = []
    skipped = 0

    for proj in projs:
        # Generate new ID: MC-V52-{naics2}-{seq}
        n2 = str(proj.get("sector_naics", "99"))
        if n2 not in naics_seq:
            naics_seq[n2] = 1
        seq = naics_seq[n2]
        naics_seq[n2] += 1

        new_id = "MC-V52-{}-{:03d}".format(n2, seq)

        # Skip if somehow already exists
        if new_id in existing_ids:
            skipped += 1
            continue

        # Clean sector name and generate specific model name
        raw_sector = proj.get("sector_name", "Unknown")
        clean_sector = clean_sector_name(raw_sector)
        arch = proj.get("architecture", "vertical_saas")

        name_template = ARCH_NAME_TEMPLATES.get(arch, "AI {sector} Platform")
        model_name = name_template.format(sector=clean_sector)

        liner_template = ARCH_ONELINER_TEMPLATES.get(
            arch,
            "AI-native solution for {sector_lower} — automating core operations with sector-specific intelligence"
        )
        one_liner = liner_template.format(sector_lower=clean_sector.lower())

        # Narrative linkage
        narrative_id = NAICS_NARRATIVE_MAP.get(n2, "TN-016")
        narrative_role = "what_works"  # Projected models are opportunities

        # Build full v4 model object
        model = {
            "id": new_id,
            "name": model_name,
            "one_liner": one_liner,
            "architecture": arch,
            "sector_naics": proj.get("sector_naics", n2),
            "sector_name": raw_sector,
            "scores": proj.get("scores", {}),
            "composite": proj.get("composite", 0),
            "cla": {
                "scores": proj.get("cla", {}).get("scores", {}),
                "composite": proj.get("cla", {}).get("composite", 0),
                "category": proj.get("cla", {}).get("category", "CONTESTED"),
                "rationale": proj.get("cla", {}).get("rationale", "Heuristic: projection-derived from architecture and sector patterns"),
            },
            "vcr": {
                "scores": proj.get("vcr", {}).get("scores", {}),
                "composite": proj.get("vcr", {}).get("composite", 0),
                "category": proj.get("vcr", {}).get("category", "VIABLE_RETURN"),
                "rationale": proj.get("vcr", {}).get("rationale", "Heuristic: projection-derived from architecture defaults"),
                "roi_estimate": proj.get("vcr", {}).get("roi_estimate", {}),
            },
            "forces_v3": proj.get("forces_v3", []),
            "narrative_ids": [narrative_id],
            "narrative_role": narrative_role,
            "primary_category": assign_primary_category(proj),
            "category": assign_category_tags(proj),
            "confidence_tier": CONF_MAP.get(proj.get("confidence_tier", "MEDIUM"), "MODERATE"),
            "evidence_quality": "projection_derived",
            "source_batch": "v52_projection_promotion",
            "projection_source": {
                "original_id": proj.get("id", ""),
                "method": proj.get("projection", {}).get("method", ""),
                "confidence": proj.get("projection", {}).get("confidence", ""),
                "evidence_chain": proj.get("projection", {}).get("evidence_chain", []),
                "source_models": proj.get("projection", {}).get("source_models", []),
                "triple_score": proj.get("triple_score", 0),
                "projection_rank": proj.get("projection_rank", 0),
            },
            # Ranks will be recomputed below
            "rank": 0,
            "opportunity_rank": 0,
            "vcr_rank": 0,
        }

        promoted.append(model)
        existing_ids.add(new_id)

    print("  Promoted: {}".format(len(promoted)))
    if skipped:
        print("  Skipped (ID collision): {}".format(skipped))

    # Merge into models
    all_models = models + promoted

    # Recompute all ranks
    print("\n  Recomputing ranks for {} models...".format(len(all_models)))

    # T-rank (highest composite = rank 1)
    sorted_t = sorted(range(len(all_models)), key=lambda i: all_models[i].get("composite", 0), reverse=True)
    for rank_pos, idx in enumerate(sorted_t):
        all_models[idx]["rank"] = rank_pos + 1

    # Opportunity rank (highest CLA composite = rank 1)
    sorted_o = sorted(range(len(all_models)), key=lambda i: all_models[i].get("cla", {}).get("composite", 0), reverse=True)
    for rank_pos, idx in enumerate(sorted_o):
        all_models[idx]["opportunity_rank"] = rank_pos + 1

    # VCR rank (highest VCR composite = rank 1)
    sorted_v = sorted(range(len(all_models)), key=lambda i: all_models[i].get("vcr", {}).get("composite", 0), reverse=True)
    for rank_pos, idx in enumerate(sorted_v):
        all_models[idx]["vcr_rank"] = rank_pos + 1

    # Update narrative outputs
    print("  Updating narrative model lists...")
    for model in promoted:
        narr_id = model["narrative_ids"][0]
        if narr_id in narr_lookup:
            narr = narr_lookup[narr_id]
            outputs = narr.get("outputs", {})
            role_key = model["narrative_role"]
            if role_key not in outputs:
                outputs[role_key] = []
            if model["id"] not in outputs[role_key]:
                outputs[role_key].append(model["id"])

    # Stats
    promoted_t = [m["composite"] for m in promoted]
    promoted_o = [m["cla"]["composite"] for m in promoted]
    promoted_v = [m["vcr"]["composite"] for m in promoted]

    print("\n  Promoted model stats:")
    print("    T-Score:  mean={:.1f}, median={:.1f}, range=[{:.1f}, {:.1f}]".format(
        statistics.mean(promoted_t), statistics.median(promoted_t),
        min(promoted_t), max(promoted_t)))
    print("    O-Score:  mean={:.1f}, median={:.1f}, range=[{:.1f}, {:.1f}]".format(
        statistics.mean(promoted_o), statistics.median(promoted_o),
        min(promoted_o), max(promoted_o)))
    print("    VCR:      mean={:.1f}, median={:.1f}, range=[{:.1f}, {:.1f}]".format(
        statistics.mean(promoted_v), statistics.median(promoted_v),
        min(promoted_v), max(promoted_v)))

    # Rank distribution of promoted models
    promoted_ranks = [m["rank"] for m in promoted]
    print("    T-Rank:   best={}, worst={}, median={}".format(
        min(promoted_ranks), max(promoted_ranks),
        sorted(promoted_ranks)[len(promoted_ranks) // 2]))

    # Top 5 promoted
    top5 = sorted(promoted, key=lambda m: m.get("composite", 0), reverse=True)[:5]
    print("\n  Top 5 promoted models:")
    for m in top5:
        print("    {} T={:.1f} O={:.1f} VCR={:.1f} rank=#{} — {}".format(
            m["id"], m["composite"],
            m["cla"]["composite"], m["vcr"]["composite"],
            m["rank"], m["name"]))

    # Save
    print("\n  Saving...")
    if isinstance(models_data, dict):
        models_data["models"] = all_models
        models_data["count"] = len(all_models)
        models_data["linked_count"] = len(all_models)
        models_data["unlinked_count"] = 0
        # Update role distribution
        role_dist = {}
        for m in all_models:
            role = m.get("narrative_role", "NONE")
            role_dist[role] = role_dist.get(role, 0) + 1
        models_data["role_distribution"] = role_dist
        save_json(V4_DIR / "models.json", models_data)
    else:
        save_json(V4_DIR / "models.json", all_models)
    save_json(V4_DIR / "narratives.json", narratives)

    # Update state
    state["entity_counts"]["models"] = len(all_models)
    state["engine_version"] = "5.2"
    state["description"] = "v5.2: {} models ({} projected models promoted from gap analysis). {}".format(
        len(all_models), len(promoted), state.get("description", ""))

    # Add promotion cycle
    promotion_entry = {
        "cycle_id": "v5-2-promotion",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "models_before": len(models),
        "models_after": len(all_models),
        "promoted_count": len(promoted),
        "projection_methods": {
            "AT": sum(1 for m in promoted if m["projection_source"]["method"] == "AT"),
            "FR": sum(1 for m in promoted if m["projection_source"]["method"] == "FR"),
            "NC": sum(1 for m in promoted if m["projection_source"]["method"] == "NC"),
            "FC": sum(1 for m in promoted if m["projection_source"]["method"] == "FC"),
            "TD": sum(1 for m in promoted if m["projection_source"]["method"] == "TD"),
        },
        "narratives_updated": len(set(m["narrative_ids"][0] for m in promoted)),
    }
    state["cycles"].append(promotion_entry)
    save_json(V5_DIR / "state.json", state)

    print("\n" + "=" * 70)
    print("PROMOTION COMPLETE: {} → {} models".format(len(models), len(all_models)))
    print("=" * 70)

    return len(promoted)


if __name__ == "__main__":
    promote_projections()
