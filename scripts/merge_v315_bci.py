#!/usr/bin/env python3
"""
v3-15 Merge: Add 4 BCI frontier models to normalized inventory.

Uses same CLA/VCR heuristic scoring as merge_v314.py.
All BCI models get LOW confidence, evidence_quality 2-4.
"""

import json
import statistics
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
BCI_FILE = BASE / "v315_bci_models.json"


def clamp(v, lo=1, hi=10):
    return max(lo, min(hi, round(v, 1)))


# ── CLA Heuristic (from cla_scoring.py defaults) ──
ARCH_CLA = {
    "hardware_ai":             {"MO": 4, "MA": 3, "VD": 5, "DV": 4},
    "platform_infrastructure": {"MO": 5, "MA": 5, "VD": 6, "DV": 5},
    "ai_copilot":              {"MO": 6, "MA": 7, "VD": 4, "DV": 6},
    "data_compounding":        {"MO": 5, "MA": 4, "VD": 5, "DV": 5},
}


def score_cla(model):
    arch = model.get("architecture", "platform_infrastructure")
    base = dict(ARCH_CLA.get(arch, {"MO": 5, "MA": 5, "VD": 5, "DV": 5}))

    # BCI is early-stage — market is wide open but demand is unproven
    base["MO"] = clamp(base["MO"] + 2)  # No incumbents in BCI
    base["DV"] = clamp(base["DV"] - 2)  # Demand not yet visible

    composite = round((base["MO"] * 30 + base["MA"] * 25 + base["VD"] * 20 + base["DV"] * 25) / 10, 2)
    if composite >= 75: cat = "WIDE_OPEN"
    elif composite >= 60: cat = "ACCESSIBLE"
    elif composite >= 45: cat = "CONTESTED"
    elif composite >= 30: cat = "FORTIFIED"
    else: cat = "LOCKED"

    return {
        "scores": base,
        "composite": composite,
        "category": cat,
        "rationale": f"BCI frontier — early market ({arch}), no incumbent moats but unproven demand"
    }


# ── VCR Heuristic (from vcr_scoring.py) ──
ARCH_VCR = {
    "hardware_ai":             {"MKT": 4, "CAP": 5, "ECO": 3, "VEL": 2, "MOA": 6},
    "platform_infrastructure": {"MKT": 5, "CAP": 4, "ECO": 6, "VEL": 4, "MOA": 7},
    "ai_copilot":              {"MKT": 4, "CAP": 5, "ECO": 7, "VEL": 5, "MOA": 4},
    "data_compounding":        {"MKT": 4, "CAP": 4, "ECO": 6, "VEL": 4, "MOA": 8},
}


def score_vcr(model):
    arch = model.get("architecture", "platform_infrastructure")
    base = dict(ARCH_VCR.get(arch, {"MKT": 4, "CAP": 4, "ECO": 5, "VEL": 4, "MOA": 5}))

    # BCI market is small now — reduce MKT
    base["MKT"] = clamp(base["MKT"] - 1)
    # BCI has slow sales cycles — reduce VEL
    base["VEL"] = clamp(base["VEL"] - 1)

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
        "rationale": f"BCI frontier v3-15: arch={arch}, early market, constrained TAM"
    }


def classify_model(scores, forces_v3):
    s = scores
    cats = []
    if s["SN"] >= 8.0 and s["FA"] >= 8.0:
        cats.append("STRUCTURAL_WINNER")
    if s["FA"] >= 7.0 and "STRUCTURAL_WINNER" not in cats:
        cats.append("FORCE_RIDER")
    if s["TG"] >= 8.0 and s["SN"] >= 6.0:
        cats.append("TIMING_ARBITRAGE")
    if s["CE"] >= 8.0 and s["SN"] >= 6.0:
        cats.append("CAPITAL_MOAT")
    if any("psychology" in str(f).lower() for f in (forces_v3 or [])):
        cats.append("FEAR_ECONOMY")
    if not cats:
        composite = (s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10
        if composite >= 60:
            cats.append("CONDITIONAL")
        else:
            cats.append("PARKED")
    return cats


def build_normalized_model(card):
    s = card["scores"]
    composite = round((s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 + s["TG"] * 15 + s["CE"] * 15) / 10, 2)
    cla = score_cla(card)
    vcr = score_vcr(card)
    forces = card.get("forces_v3", [])
    cats = classify_model(s, forces)

    return {
        "id": card["id"],
        "name": card["name"],
        "one_liner": card.get("one_liner"),
        "composite": composite,
        "scores": s,
        "source_batch": card.get("source_batch", "v315_bci_frontier"),
        "macro_source": None,
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": card.get("sector_naics"),
        "sector_name": card.get("sector_name"),
        "architecture": card.get("architecture"),
        "forces_v3": forces,
        "key_v3_context": None,
        "deep_dive_evidence": card.get("deep_dive_evidence"),
        "category": cats,
        "primary_category": cats[0],
        "cla": cla,
        "vcr": vcr,
        "vcr_evidence": None,
        "falsification_criteria": card.get("falsification_criteria", []),
        "confidence_tier": card.get("confidence_tier", "LOW"),
        "evidence_quality": card.get("evidence_quality", 3),
        "architecture_original": card.get("architecture"),
        "composite_stated": composite,
    }


def main():
    print("=" * 70)
    print("v3-15 MERGE: BCI Frontier Models")
    print("=" * 70)

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    existing_ids = {m["id"] for m in models}
    print(f"Existing models: {len(models)}")

    with open(BCI_FILE) as f:
        bci = json.load(f)
    cards = bci["model_cards"]

    added = 0
    for card in cards:
        if card["id"] in existing_ids:
            print(f"  SKIP (duplicate): {card['id']}")
            continue
        normalized = build_normalized_model(card)
        models.append(normalized)
        existing_ids.add(card["id"])
        added += 1
        print(f"  ADDED: {card['id']} — {card['name']}")

    print(f"\nAdded {added} BCI models. New total: {len(models)}")

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
    data["summary"]["total_models"] = len(models)

    print(f"Writing {len(models)} models...")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Written: {NORMALIZED_FILE}")

    # Summary
    for m in models:
        if m["id"].startswith("V3-BCI"):
            print(f"  {m['id']:<14s} T={m['composite']:>5.1f} O={m['cla']['composite']:>5.1f} "
                  f"VCR={m['vcr']['composite']:>5.1f} Cat={m['primary_category']:<18s} {m['name']}")
    print("\nDone.")


if __name__ == "__main__":
    main()
