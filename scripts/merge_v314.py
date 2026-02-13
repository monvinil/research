#!/usr/bin/env python3
"""
v3-14 Merge: Integrate frontier tech + cascade/structural model cards.

Inputs:
  - data/verified/v314_frontier_coverage_2026-02-12.json (16 models)
  - data/verified/v314_cascade_coverage_2026-02-12.json (20 models)
  - data/verified/v3-12_normalized_2026-02-12.json (508 models)

Adds CLA (heuristic) and VCR (heuristic) scores via the existing scoring engines,
plus enrichment fields (confidence_tier, evidence_quality, falsification_criteria,
polanyi, architecture normalization).

Output: Updated normalized file with 508 + 36 = 544 models.
"""

import json
import sys
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

DEEP_DIVE_FILES = [
    BASE / "v314_frontier_coverage_2026-02-12.json",
    BASE / "v314_cascade_coverage_2026-02-12.json",
]


def clamp(v, lo=1, hi=10):
    return max(lo, min(hi, round(v, 1)))


# ── Lightweight CLA Heuristic (matches cla_scoring.py logic) ──
ARCH_CLA = {
    "full_service_replacement": (6, 6, 5, 7),
    "vertical_saas": (7, 7, 5, 7),
    "platform_infrastructure": (5, 5, 7, 6),
    "data_compounding": (6, 5, 6, 6),
    "acquire_and_modernize": (8, 7, 4, 6),
    "marketplace_network": (7, 6, 6, 7),
    "rollup_consolidation": (8, 7, 4, 5),
    "service_platform": (7, 6, 5, 6),
    "regulatory_moat_builder": (5, 4, 5, 7),
    "arbitrage_window": (8, 8, 3, 8),
    "physical_production_ai": (5, 5, 5, 5),
    "hardware_ai": (4, 4, 5, 5),
    "robotics_automation": (5, 5, 5, 5),
    "ai_copilot": (7, 7, 4, 7),
    "compliance_automation": (6, 5, 5, 7),
}

SECTOR_CLA_ADJ = {
    "11": (1, 0, 0, 0), "21": (0, -1, 0, 0), "22": (-1, -1, 0, -1),
    "23": (1, 0, 1, 0), "31": (0, 0, 0, 0), "32": (0, 0, 0, 0), "33": (0, 0, 0, 0),
    "42": (1, 0, 0, 0), "44": (0, 0, 1, 0), "45": (0, 0, 1, 0),
    "48": (0, 0, 0, 0), "49": (0, 0, 0, 0), "51": (0, 0, 0, 0),
    "52": (-1, 0, 1, 0), "53": (1, 0, 0, 0), "54": (0, 0, 0, 0),
    "55": (-1, 0, 0, 0), "56": (1, 0, 0, 0), "61": (0, 0, 0, 0),
    "62": (-1, 0, 1, 0), "71": (1, 0, 0, 0), "72": (1, 0, 0, 0),
    "81": (1, 0, 0, 0), "92": (-2, -1, 0, -1),
}

# Apply v3-14 MO/MA differentiation
SECTOR_MO_MA_DIFF = {
    "21": (1, -2), "22": (0, -2), "23": (2, -1), "42": (1, -1),
    "48": (1, -2), "52": (-2, 1), "53": (2, -1), "61": (-1, 1),
    "62": (-2, 0), "72": (2, 0), "81": (2, -1), "92": (-2, -1),
}
ARCH_MA_ADJ = {
    "vertical_saas": 1, "ai_copilot": 1, "arbitrage_window": 2,
    "data_compounding": -1, "platform_infrastructure": -1,
    "hardware_ai": -2, "robotics_automation": -1, "regulatory_moat_builder": -2,
}
SECTOR_VD_ADJ = {
    "11": -1, "21": -1, "23": 1, "31": 1, "32": 1, "33": 1,
    "44": 1, "45": 1, "49": 1, "51": 1, "52": 2, "53": 1,
    "56": -1, "62": 1, "81": -1,
}


def score_cla(model):
    arch = model.get("architecture", "vertical_saas")
    base = list(ARCH_CLA.get(arch, (5, 5, 5, 5)))

    naics2 = (model.get("sector_naics") or "")[:2]
    if naics2 in SECTOR_CLA_ADJ:
        adj = SECTOR_CLA_ADJ[naics2]
        for i in range(4):
            base[i] += adj[i]

    # v3-14 differentiation
    if naics2 in SECTOR_MO_MA_DIFF:
        base[0] += SECTOR_MO_MA_DIFF[naics2][0]
        base[1] += SECTOR_MO_MA_DIFF[naics2][1]
    if arch in ARCH_MA_ADJ:
        base[1] += ARCH_MA_ADJ[arch]
    if naics2 in SECTOR_VD_ADJ:
        base[2] += SECTOR_VD_ADJ[naics2]

    mo, ma, vd, dv = [clamp(v) for v in base]
    composite = round((mo * 30 + ma * 25 + vd * 20 + dv * 25) / 10, 2)

    if composite >= 75: cat = "WIDE_OPEN"
    elif composite >= 60: cat = "ACCESSIBLE"
    elif composite >= 45: cat = "CONTESTED"
    elif composite >= 30: cat = "FORTIFIED"
    else: cat = "LOCKED"

    return {
        "scores": {"MO": mo, "MA": ma, "VD": vd, "DV": dv},
        "composite": composite,
        "category": cat,
        "rationale": f"Heuristic v3-14: arch={arch}, NAICS={naics2}, with MO/MA differentiation and VD sector adjustment"
    }


# ── Lightweight VCR Heuristic ──
ARCH_VCR = {
    "full_service_replacement": {"MKT": 6, "CAP": 6, "ECO": 7, "VEL": 6, "MOA": 6},
    "vertical_saas": {"MKT": 6, "CAP": 7, "ECO": 8, "VEL": 7, "MOA": 7},
    "platform_infrastructure": {"MKT": 7, "CAP": 5, "ECO": 7, "VEL": 6, "MOA": 7},
    "data_compounding": {"MKT": 6, "CAP": 5, "ECO": 7, "VEL": 6, "MOA": 8},
    "acquire_and_modernize": {"MKT": 7, "CAP": 7, "ECO": 5, "VEL": 4, "MOA": 5},
    "marketplace_network": {"MKT": 7, "CAP": 5, "ECO": 8, "VEL": 7, "MOA": 7},
    "rollup_consolidation": {"MKT": 6, "CAP": 7, "ECO": 5, "VEL": 4, "MOA": 5},
    "service_platform": {"MKT": 6, "CAP": 6, "ECO": 6, "VEL": 6, "MOA": 6},
    "regulatory_moat_builder": {"MKT": 5, "CAP": 5, "ECO": 7, "VEL": 5, "MOA": 8},
    "arbitrage_window": {"MKT": 5, "CAP": 8, "ECO": 6, "VEL": 8, "MOA": 3},
    "physical_production_ai": {"MKT": 6, "CAP": 5, "ECO": 4, "VEL": 4, "MOA": 5},
    "hardware_ai": {"MKT": 6, "CAP": 5, "ECO": 4, "VEL": 3, "MOA": 5},
    "robotics_automation": {"MKT": 6, "CAP": 5, "ECO": 5, "VEL": 4, "MOA": 5},
    "ai_copilot": {"MKT": 6, "CAP": 7, "ECO": 8, "VEL": 7, "MOA": 6},
    "compliance_automation": {"MKT": 5, "CAP": 6, "ECO": 7, "VEL": 5, "MOA": 7},
}

# v3-14 CAP/VEL decoupling
ARCH_CAP_VEL = {
    "acquire_and_modernize": (2, -2), "rollup_consolidation": (2, -2),
    "platform_infrastructure": (-1, 1), "marketplace_network": (-1, 2),
    "vertical_saas": (0, 1), "robotics_automation": (1, -2),
    "hardware_ai": (1, -3), "physical_production_ai": (1, -2),
    "data_compounding": (-1, 1), "compliance_automation": (0, -1),
    "regulatory_moat_builder": (-1, -1),
}


def score_vcr(model):
    arch = model.get("architecture", "vertical_saas")
    base = dict(ARCH_VCR.get(arch, ARCH_VCR["vertical_saas"]))

    # v3-14 CAP/VEL decoupling
    cap_adj, vel_adj = ARCH_CAP_VEL.get(arch, (0, 0))
    base["CAP"] = clamp(base["CAP"] + cap_adj)
    base["VEL"] = clamp(base["VEL"] + vel_adj)

    composite = round(
        (base["MKT"] * 25 + base["CAP"] * 25 + base["ECO"] * 20 +
         base["VEL"] * 15 + base["MOA"] * 15) / 10, 2)

    if composite >= 75: cat = "FUND_RETURNER"
    elif composite >= 60: cat = "STRONG_MULTIPLE"
    elif composite >= 45: cat = "VIABLE_RETURN"
    elif composite >= 30: cat = "MARGINAL"
    else: cat = "VC_POOR"

    # Simple ROI estimate
    revenue_m = base["MKT"] * 3
    capture = base["CAP"] * 0.03
    revenue_multiple = 12 if base["ECO"] >= 7 else 8 if base["ECO"] >= 5 else 5
    exit_val = round(revenue_m * capture * revenue_multiple, 1)
    roi = round(exit_val / 10, 1)  # $10M seed

    return {
        "scores": base,
        "composite": composite,
        "category": cat,
        "roi_estimate": {
            "year5_revenue_M": round(revenue_m * capture, 1),
            "revenue_multiple": revenue_multiple,
            "exit_val_M": exit_val,
            "seed_roi_multiple": roi,
        },
        "rationale": f"Fundamental v2: arch={arch}, with v3-14 CAP/VEL decoupling"
    }


def classify_model(m):
    """Assign category tags based on scores."""
    s = m["scores"]
    cats = []
    if s["SN"] >= 8.0 and s["FA"] >= 8.0:
        cats.append("STRUCTURAL_WINNER")
    if s["FA"] >= 7.0 and "STRUCTURAL_WINNER" not in cats:
        cats.append("FORCE_RIDER")
    if s["TG"] >= 8.0 and s["SN"] >= 6.0:
        cats.append("TIMING_ARBITRAGE")
    if s["CE"] >= 8.0 and s["SN"] >= 6.0:
        cats.append("CAPITAL_MOAT")

    forces = m.get("forces_v3", [])
    if any("fear" in str(f).lower() or "psychology" in str(f).lower() for f in forces):
        cats.append("FEAR_ECONOMY")

    composite = m["composite"]
    if not cats:
        if composite >= 60:
            cats.append("CONDITIONAL")
        else:
            cats.append("PARKED")
    return cats


def build_normalized_model(card):
    """Convert a model card to full normalized format."""
    # Compute composite
    s = card["scores"]
    composite = round((s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2)

    m = {
        "id": card["id"],
        "name": card["name"],
        "one_liner": card.get("one_liner"),
        "composite": composite,
        "scores": s,
        "source_batch": card.get("source_batch", "v314_coverage"),
        "macro_source": card.get("macro_source"),
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": card.get("forces_v3", []),
        "key_v3_context": None,
        "deep_dive_evidence": card.get("deep_dive_evidence"),
    }

    # Category
    m["category"] = classify_model(m)
    m["primary_category"] = m["category"][0]
    m["composite_stated"] = composite

    # CLA
    m["cla"] = score_cla(m)

    # VCR
    m["vcr"] = score_vcr(m)

    # Enrichment fields
    m["confidence_tier"] = "MODERATE"  # New models from systematic coverage, not deep-dive
    m["evidence_quality"] = 5  # Generated with structured evidence but not field-verified
    m["architecture_original"] = card.get("architecture")

    # Falsification: basic set based on architecture
    m["falsification_criteria"] = [
        "Foundation model capabilities plateau or inference costs stop declining for 18+ months",
        f"Incumbent firms in {card.get('sector_name', 'the sector')} successfully deploy equivalent AI internally",
    ]

    return m


def main():
    print("=" * 70)
    print("v3-14 MERGE: Frontier Tech + Cascade/Structural Models")
    print("=" * 70)

    # Load normalized
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    existing_ids = {m["id"] for m in models}
    print(f"Existing models: {len(models)}")

    # Load new cards
    new_cards = []
    for fp in DEEP_DIVE_FILES:
        if fp.exists():
            with open(fp) as f:
                cards = json.load(f)
            # Handle both array and dict formats
            if isinstance(cards, dict):
                cards = cards.get("model_cards", cards.get("models", []))
            print(f"  {fp.name}: {len(cards)} cards")
            new_cards.extend(cards)
        else:
            print(f"  {fp.name}: NOT FOUND")

    print(f"Total new cards: {len(new_cards)}")

    # Build and merge
    added = 0
    skipped = 0
    for card in new_cards:
        if card["id"] in existing_ids:
            print(f"  SKIP (duplicate): {card['id']}")
            skipped += 1
            continue
        normalized = build_normalized_model(card)
        models.append(normalized)
        existing_ids.add(card["id"])
        added += 1

    print(f"\nAdded: {added}, Skipped: {skipped}")
    print(f"Total models: {len(models)}")

    # Re-rank all three dimensions
    models.sort(key=lambda m: (-m["composite"], m["id"]))
    for i, m in enumerate(models, 1):
        m["rank"] = i

    models_by_opp = sorted(models, key=lambda m: (-m.get("cla", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(models_by_opp, 1):
        m["opportunity_rank"] = i

    models_by_vcr = sorted(models, key=lambda m: (-m.get("vcr", {}).get("composite", 0), m["id"]))
    for i, m in enumerate(models_by_vcr, 1):
        m["vcr_rank"] = i

    # Sort by T for file
    models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Update summary
    data["summary"]["total_models"] = len(models)

    # Write
    print(f"\nWriting updated normalized file ({len(models)} models)...")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Print new models summary
    new_models = [m for m in models if m["source_batch"] in ("v314_frontier_coverage", "v314_cascade_coverage")]
    print(f"\n{'ID':<20s} {'T':>5s} {'OPP':>5s} {'VCR':>5s} {'Cat':<18s} Name")
    for m in sorted(new_models, key=lambda x: -x["composite"]):
        print(f"{m['id']:<20s} {m['composite']:>5.1f} {m['cla']['composite']:>5.1f} "
              f"{m['vcr']['composite']:>5.1f} {m['primary_category']:<18s} {m['name'][:45]}")

    print(f"\nDone. Run update_v313_ui.py to regenerate UI.")


if __name__ == "__main__":
    main()
