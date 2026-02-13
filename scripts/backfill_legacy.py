#!/usr/bin/env python3
"""
Backfill legacy data debt: add force tags and one-liners to models missing them.

Targets:
  - 92 models with empty forces_v3
  - 47 models with empty one_liner AND empty deep_dive_evidence

Force inference: maps sector + architecture + name keywords → forces.
One-liner generation: constructs brief descriptions from model name, sector, and architecture.
"""

import json
import re
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

# ── Force inference rules ──
# Every model gets F1 (technology) as baseline since all are transformation models.
# Additional forces inferred from sector, architecture, and name keywords.

SECTOR_FORCES = {
    "11": ["F2", "F6"],        # Agriculture: demographics (labor), energy (climate)
    "21": ["F3", "F6"],        # Mining: geopolitics (resources), energy
    "22": ["F6", "F3"],        # Utilities: energy, geopolitics (grid)
    "23": ["F2", "F4"],        # Construction: demographics (labor shortage), capital
    "31": ["F2", "F3"],        # Manufacturing: demographics, geopolitics (trade)
    "32": ["F2", "F3"],        # Manufacturing
    "33": ["F2", "F3"],        # Manufacturing
    "42": ["F4", "F3"],        # Wholesale: capital, geopolitics (supply chain)
    "44": ["F4", "F5"],        # Retail: capital, psychology (consumer)
    "45": ["F4", "F5"],        # Retail
    "48": ["F2", "F6"],        # Transportation: demographics (driver shortage), energy
    "49": ["F2", "F6"],        # Warehousing
    "51": ["F4"],              # Information: capital
    "52": ["F4", "F3"],        # Finance: capital, geopolitics (regulation)
    "53": ["F4", "F5"],        # Real Estate: capital, psychology
    "54": ["F4", "F2"],        # Professional Services: capital, demographics
    "55": ["F4"],              # Management: capital
    "56": ["F2", "F4"],        # Admin/Support: demographics (labor), capital
    "61": ["F2", "F5"],        # Education: demographics (enrollment), psychology (fear)
    "62": ["F2", "F5"],        # Healthcare: demographics (aging), psychology
    "71": ["F5", "F2"],        # Arts/Entertainment: psychology, demographics
    "72": ["F2", "F4"],        # Accommodation/Food: demographics (labor), capital
    "81": ["F2", "F4"],        # Other Services: demographics, capital
    "92": ["F3", "F4"],        # Government: geopolitics, capital
}

NAME_FORCE_KEYWORDS = {
    "F2": ["aging", "senior", "elder", "retire", "succession", "workforce", "labor", "talent",
           "demographic", "immigration", "h1b", "boomer", "silver tsunami", "population"],
    "F3": ["defense", "military", "geopolit", "tariff", "trade", "china", "reshoring",
           "sovereignty", "national security", "dod", "nato", "supply chain", "export"],
    "F4": ["capital", "invest", "pe ", "venture", "funding", "financ", "credit",
           "valuation", "ipo", "acquisition", "consolidat", "rollup", "m&a"],
    "F5": ["fear", "trust", "privacy", "compliance", "safety", "anxiety", "mental health",
           "deepfake", "misinformation", "authentication", "fraud", "cyber", "security"],
    "F6": ["energy", "solar", "battery", "grid", "nuclear", "power", "carbon",
           "climate", "emission", "renewable", "ev ", "electric vehicle", "utility"],
}

ARCH_FORCES = {
    "acquire_and_modernize": ["F2", "F4"],  # Demographics (succession) + Capital
    "regulatory_moat_builder": ["F3", "F5"],  # Geopolitics (regulation) + Psychology (compliance)
    "robotics_automation": ["F2"],  # Demographics (labor replacement)
    "hardware_ai": ["F6"],  # Energy (physical infrastructure)
    "compliance_automation": ["F3", "F5"],  # Geopolitics + Psychology
}

# ── One-liner templates by architecture ──
ARCH_TEMPLATES = {
    "full_service_replacement": "End-to-end AI platform replacing traditional {sector_short} operations with automated workflows, from client intake through delivery",
    "vertical_saas": "Specialized SaaS platform for {sector_short} that embeds AI into core workflows — scheduling, billing, compliance, and decision support",
    "platform_infrastructure": "Infrastructure layer enabling AI-powered {sector_short} transformation — APIs, data pipelines, and integration middleware for the sector",
    "data_compounding": "Data flywheel platform that compounds {sector_short} intelligence over time, building proprietary datasets that improve with every transaction",
    "acquire_and_modernize": "Acquire fragmented {sector_short} businesses at 3-5x EBITDA, modernize operations with AI, and scale through roll-up consolidation",
    "marketplace_network": "Two-sided marketplace connecting {sector_short} supply and demand with AI-driven matching, pricing, and quality assurance",
    "rollup_consolidation": "Roll-up strategy consolidating fragmented {sector_short} operators under shared AI infrastructure, back-office automation, and centralized analytics",
    "service_platform": "Managed service platform for {sector_short} that blends human expertise with AI augmentation to deliver outcomes at scale",
    "regulatory_moat_builder": "Compliance-first platform for {sector_short} that turns regulatory complexity into competitive advantage through automated monitoring and reporting",
    "arbitrage_window": "Time-limited opportunity in {sector_short} exploiting the gap between AI capability arrival and incumbent adoption — narrow entry window",
    "physical_production_ai": "AI-augmented physical production system for {sector_short} — computer vision, predictive maintenance, and automated quality control on existing lines",
    "hardware_ai": "Purpose-built hardware-software system for {sector_short} combining specialized sensors, edge compute, and AI models optimized for the physical environment",
    "robotics_automation": "Autonomous robotics platform for {sector_short} — mobile manipulation, computer vision, and fleet coordination replacing manual labor at scale",
    "ai_copilot": "AI copilot for {sector_short} professionals — augments expert judgment with real-time analysis, recommendation engines, and automated documentation",
    "compliance_automation": "Automated compliance engine for {sector_short} — continuous monitoring, audit trail generation, and regulatory filing across jurisdictions",
}

SECTOR_SHORT = {
    "11": "agriculture", "21": "mining and extraction", "22": "utility",
    "23": "construction", "31": "manufacturing", "32": "manufacturing", "33": "manufacturing",
    "42": "wholesale trade", "44": "retail", "45": "retail",
    "48": "transportation", "49": "warehousing and logistics",
    "51": "information and media", "52": "financial services", "53": "real estate",
    "54": "professional services", "55": "management and corporate",
    "56": "administrative and support services", "61": "education",
    "62": "healthcare", "71": "entertainment and recreation",
    "72": "hospitality and food service", "81": "personal and repair services",
    "92": "government and public administration",
}


def infer_forces(model):
    """Infer force tags from sector, architecture, and model name."""
    forces = {"F1"}  # All models are technology-driven transformations

    # Sector-based forces
    naics = (model.get("sector_naics") or "")[:2]
    if naics in SECTOR_FORCES:
        for f in SECTOR_FORCES[naics]:
            forces.add(f)

    # Architecture-based forces
    arch = model.get("architecture", "")
    if arch in ARCH_FORCES:
        for f in ARCH_FORCES[arch]:
            forces.add(f)

    # Name keyword forces
    name = (model.get("name") or "").lower()
    one_liner = (model.get("one_liner") or "").lower()
    macro = (model.get("macro_source") or "").lower()
    text = f"{name} {one_liner} {macro}"

    for force, keywords in NAME_FORCE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                forces.add(force)
                break

    # Convert to sorted long-form
    force_map = {
        "F1": "F1_technology", "F2": "F2_demographics", "F3": "F3_geopolitics",
        "F4": "F4_capital", "F5": "F5_psychology", "F6": "F6_energy"
    }
    return sorted([force_map[f] for f in forces])


def generate_one_liner(model):
    """Generate a one-liner description from model name, sector, and architecture."""
    arch = model.get("architecture", "vertical_saas")
    naics = (model.get("sector_naics") or "")[:2]
    sector_short = SECTOR_SHORT.get(naics, "the target sector")
    name = model.get("name", "")

    template = ARCH_TEMPLATES.get(arch, ARCH_TEMPLATES["vertical_saas"])
    one_liner = template.format(sector_short=sector_short)

    # If name has specific keywords, make it more specific
    name_lower = name.lower()
    if "accounting" in name_lower or "tax" in name_lower:
        one_liner = one_liner.replace("the target sector", "accounting and tax preparation")
    elif "legal" in name_lower or "law" in name_lower:
        one_liner = one_liner.replace("the target sector", "legal services")
    elif "insurance" in name_lower:
        one_liner = one_liner.replace("the target sector", "insurance")
    elif "trucking" in name_lower or "freight" in name_lower:
        one_liner = one_liner.replace("the target sector", "trucking and freight")
    elif "restaurant" in name_lower or "food" in name_lower:
        one_liner = one_liner.replace("the target sector", "food service and restaurants")

    return one_liner


def main():
    print("=" * 70)
    print("LEGACY BACKFILL: Adding force tags and one-liners to empty models")
    print("=" * 70)
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # ── Backfill forces ──
    no_forces = [m for m in models if not m.get("forces_v3")]
    print(f"\nModels without forces: {no_forces.__len__()}")

    forces_added = 0
    for m in models:
        if not m.get("forces_v3"):
            m["forces_v3"] = infer_forces(m)
            forces_added += 1

    print(f"  Forces added to {forces_added} models")

    # Verify — how many still missing?
    still_missing = sum(1 for m in models if not m.get("forces_v3"))
    print(f"  Still missing: {still_missing}")

    # ── Backfill one-liners ──
    no_liner = [m for m in models if not m.get("one_liner")]
    print(f"\nModels without one-liner: {len(no_liner)}")

    liners_added = 0
    for m in models:
        if not m.get("one_liner"):
            m["one_liner"] = generate_one_liner(m)
            liners_added += 1

    print(f"  One-liners added to {liners_added} models")

    # ── Write back ──
    print(f"\nWriting updated normalized file...")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Report ──
    print()
    print("=" * 70)
    print("BACKFILL COMPLETE")
    print("=" * 70)
    print(f"  Forces added: {forces_added}")
    print(f"  One-liners added: {liners_added}")

    # Print some examples
    print("\n  Example force backfills:")
    for m in no_forces[:5]:
        print(f"    {m['id']} ({m.get('sector_naics','?')}) {m['name'][:50]}")
        print(f"      → {m['forces_v3']}")

    print("\n  Example one-liner backfills:")
    for m in no_liner[:5]:
        print(f"    {m['id']} {m['name'][:50]}")
        print(f"      → {m['one_liner'][:80]}...")


if __name__ == "__main__":
    main()
