#!/usr/bin/env python3
"""
v3-14 Merge: Integrate 5 unmerged v3-13 deep dive files (60 cards).

Handles field name variations between deep dive batches:
  - agriculture/arts/wholesale: cla={scores:{},composite,category,rationale}, forces_v3=['F1','F4']
  - government/mining: competitive_landscape_assessment={MO,MA,VD,DV,rationale}, forces=['F1_technology',...]

All cards get VCR scoring (none have it) with v3-14 corrections applied.
"""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"

DEEP_DIVE_FILES = [
    BASE / "v3-13_agriculture_deep_dive_2026-02-12.json",
    BASE / "v3-13_arts_entertainment_deep_dive_2026-02-12.json",
    BASE / "v3-13_government_deep_dive_2026-02-12.json",
    BASE / "v3-13_mining_deep_dive_2026-02-12.json",
    BASE / "v3-13_wholesale_deep_dive_2026-02-12.json",
]

FORCE_MAP = {
    "F1": "F1_technology", "F2": "F2_demographics", "F3": "F3_geopolitics",
    "F4": "F4_capital", "F5": "F5_psychology", "F6": "F6_energy",
}


def clamp(v, lo=1, hi=10):
    return max(lo, min(hi, round(v, 1)))


# ── VCR Heuristic (from merge_v314.py with v3-14 corrections) ──
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

ARCH_CAP_VEL = {
    "acquire_and_modernize": (2, -2), "rollup_consolidation": (2, -2),
    "platform_infrastructure": (-1, 1), "marketplace_network": (-1, 2),
    "vertical_saas": (0, 1), "robotics_automation": (1, -2),
    "hardware_ai": (1, -3), "physical_production_ai": (1, -2),
    "data_compounding": (-1, 1), "compliance_automation": (0, -1),
    "regulatory_moat_builder": (-1, -1),
}

# v3-14 MO/MA differentiation (for cards needing CLA rebuild)
SECTOR_MO_MA_DIFF = {
    "21": (1, -2), "22": (0, -2), "23": (2, -1), "42": (1, -1),
    "48": (1, -2), "52": (-2, 1), "53": (2, -1), "61": (-1, 1),
    "62": (-2, 0), "72": (2, 0), "81": (2, -1), "92": (-2, -1),
}


def score_vcr(model):
    arch = model.get("architecture", "vertical_saas")
    base = dict(ARCH_VCR.get(arch, ARCH_VCR["vertical_saas"]))

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

    revenue_m = base["MKT"] * 3
    capture = base["CAP"] * 0.03
    revenue_multiple = 12 if base["ECO"] >= 7 else 8 if base["ECO"] >= 5 else 5
    exit_val = round(revenue_m * capture * revenue_multiple, 1)
    roi = round(exit_val / 10, 1)

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


def normalize_forces(card):
    """Normalize forces to long-form ['F1_technology', ...] format."""
    # Check both field names
    forces = card.get("forces_v3") or card.get("forces") or []
    normalized = []
    for f in forces:
        if f in FORCE_MAP:
            normalized.append(FORCE_MAP[f])
        elif f.startswith("F") and "_" in f:
            normalized.append(f)  # Already long-form
        else:
            normalized.append(f)
    return sorted(set(normalized))


def normalize_cla(card):
    """Extract CLA from whichever field format the card uses. Apply v3-14 corrections."""
    # Format 1: already has cla dict with scores/composite/category
    if "cla" in card and isinstance(card["cla"], dict) and "scores" in card["cla"]:
        cla = card["cla"]
        scores = cla["scores"]
        # Apply v3-14 MO/MA differentiation if not already applied
        naics2 = (card.get("sector_naics") or "")[:2]
        if naics2 in SECTOR_MO_MA_DIFF:
            mo_adj, ma_adj = SECTOR_MO_MA_DIFF[naics2]
            scores["MO"] = clamp(scores["MO"] + mo_adj)
            scores["MA"] = clamp(scores["MA"] + ma_adj)
        # Recompute composite
        composite = round((scores["MO"] * 30 + scores["MA"] * 25 + scores["VD"] * 20 + scores["DV"] * 25) / 10, 2)
        if composite >= 75: cat = "WIDE_OPEN"
        elif composite >= 60: cat = "ACCESSIBLE"
        elif composite >= 45: cat = "CONTESTED"
        elif composite >= 30: cat = "FORTIFIED"
        else: cat = "LOCKED"
        return {
            "scores": scores,
            "composite": composite,
            "category": cat,
            "rationale": cla.get("rationale", f"Deep dive CLA with v3-14 MO/MA correction"),
        }

    # Format 2: competitive_landscape_assessment with flat MO/MA/VD/DV
    if "competitive_landscape_assessment" in card:
        assess = card["competitive_landscape_assessment"]
        mo = clamp(assess["MO"])
        ma = clamp(assess["MA"])
        vd = clamp(assess["VD"])
        dv = clamp(assess["DV"])
        # Apply v3-14 MO/MA differentiation
        naics2 = (card.get("sector_naics") or "")[:2]
        if naics2 in SECTOR_MO_MA_DIFF:
            mo_adj, ma_adj = SECTOR_MO_MA_DIFF[naics2]
            mo = clamp(mo + mo_adj)
            ma = clamp(ma + ma_adj)
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
            "rationale": assess.get("rationale", f"Deep dive CLA (from competitive_landscape_assessment) with v3-14 correction"),
        }

    # Fallback: no CLA data at all — shouldn't happen for these files
    print(f"  WARNING: No CLA data for {card.get('id')} — using heuristic")
    return None


def classify_model(m):
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
    if any("psychology" in str(f).lower() for f in forces):
        cats.append("FEAR_ECONOMY")

    if not cats:
        if m["composite"] >= 60:
            cats.append("CONDITIONAL")
        else:
            cats.append("PARKED")
    return cats


def build_normalized_model(card, source_file):
    """Convert a deep dive card to full normalized format."""
    s = card["scores"]
    composite = round((s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2)

    forces_v3 = normalize_forces(card)
    cla = normalize_cla(card)
    vcr = score_vcr(card)

    m = {
        "id": card["id"],
        "name": card["name"],
        "one_liner": card.get("one_liner"),
        "composite": composite,
        "scores": s,
        "source_batch": card.get("source_batch", f"v313_{source_file}_deep_dive"),
        "macro_source": card.get("macro_source"),
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": forces_v3,
        "key_v3_context": None,
        "deep_dive_evidence": card.get("deep_dive_evidence"),
        "category": classify_model({"scores": s, "composite": composite, "forces_v3": forces_v3}),
        "cla": cla,
        "vcr": vcr,
        "vcr_evidence": card.get("vcr_evidence"),
        "falsification_criteria": card.get("falsification_criteria", [
            "Foundation model capabilities plateau or inference costs stop declining for 18+ months",
            f"Incumbent firms in {card.get('sector_name', 'the sector')} successfully deploy equivalent AI internally",
        ]),
        "confidence_tier": "HIGH",  # Deep dives with sector context and evidence
        "evidence_quality": 7,  # Deep dive with structured vcr_evidence
        "architecture_original": card.get("architecture"),
        "composite_stated": composite,
    }
    m["primary_category"] = m["category"][0]

    return m


def main():
    print("=" * 70)
    print("v3-14 MERGE: 5 Deep Dive Files (60 cards)")
    print("=" * 70)

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    existing_ids = {m["id"] for m in models}
    print(f"Existing models: {len(models)}")

    added = 0
    skipped = 0
    new_models = []

    source_labels = ["agriculture", "arts_entertainment", "government", "mining", "wholesale"]

    for fp, label in zip(DEEP_DIVE_FILES, source_labels):
        with open(fp) as f:
            dd = json.load(f)
        cards = dd["model_cards"]
        file_added = 0
        for card in cards:
            if card["id"] in existing_ids:
                print(f"  SKIP (duplicate): {card['id']}")
                skipped += 1
                continue
            normalized = build_normalized_model(card, label)
            models.append(normalized)
            new_models.append(normalized)
            existing_ids.add(card["id"])
            added += 1
            file_added += 1
        print(f"  {fp.name}: {len(cards)} cards, {file_added} added")

    print(f"\nTotal: {added} added, {skipped} skipped")
    print(f"New total: {len(models)} models")

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
    print(f"\n{'ID':<22s} {'T':>5s} {'OPP':>5s} {'VCR':>5s} {'Cat':<18s} Name")
    print("-" * 100)
    for m in sorted(new_models, key=lambda x: -x["composite"]):
        print(f"{m['id']:<22s} {m['composite']:>5.1f} {m['cla']['composite']:>5.1f} "
              f"{m['vcr']['composite']:>5.1f} {m['primary_category']:<18s} {m['name'][:45]}")

    # Stats
    t_scores = [m["composite"] for m in new_models]
    opp_scores = [m["cla"]["composite"] for m in new_models]
    vcr_scores = [m["vcr"]["composite"] for m in new_models]
    print(f"\nNew card stats:")
    print(f"  T-rank:  mean={statistics.mean(t_scores):.1f}, min={min(t_scores):.1f}, max={max(t_scores):.1f}")
    print(f"  OPP:     mean={statistics.mean(opp_scores):.1f}, min={min(opp_scores):.1f}, max={max(opp_scores):.1f}")
    print(f"  VCR:     mean={statistics.mean(vcr_scores):.1f}, min={min(vcr_scores):.1f}, max={max(vcr_scores):.1f}")
    print(f"\nDone. Run update_v313_ui.py to regenerate UI.")


if __name__ == "__main__":
    main()
