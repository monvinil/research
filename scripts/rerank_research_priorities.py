#!/usr/bin/env python3
"""
rerank_research_priorities.py — Re-rank research priorities by Research Priority Score (RPS)

Problem: Current dashboard research priorities are ranked by composite score alone,
putting LOW confidence models at the top. The research queue should prioritize models
where more evidence would have the BIGGEST IMPACT.

RPS = (composite_potential * 0.40) + (evidence_gap * 0.35) + (coverage_impact * 0.25)

Where:
  - composite_potential: How much could this model's score improve with better evidence?
    MODERATE conf: (10 - EQ) * 3 * max(t_composite/100, 0.5)
    LOW conf:      (10 - EQ) * 2 * max(t_composite/100, 0.5)
    HIGH conf:     (10 - EQ) * 1 * max(t_composite/100, 0.5)

  - evidence_gap: 10 - evidence_quality (raw gap)

  - coverage_impact: How many models share the same 2-digit NAICS?
    1 model = 1, 5+ = 5, 10+ = 8, 20+ = 10
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

# ── Paths ───────────────────────────────────────────────────────────────────
DATA_FILE = "/Users/mv/Documents/research/data/verified/v3-12_normalized_2026-02-12.json"
DASHBOARD_FILE = "/Users/mv/Documents/research/data/ui/dashboard.json"
OUTPUT_FILE = "/Users/mv/Documents/research/data/context/research_priorities_v317.json"


def extract_naics_2digit(naics_str: str) -> str:
    """Extract the 2-digit NAICS prefix from a sector_naics string.

    Handles ranges like '31-33' and '44-45' by taking the first number's
    2-digit prefix. For normal codes like '4841', takes first 2 digits.
    """
    if not naics_str:
        return "00"
    # Handle range format like '31-33', '44-45'
    if "-" in naics_str:
        return naics_str.split("-")[0][:2]
    return naics_str[:2]


def coverage_impact_score(count: int) -> float:
    """Scale the sector model count to a 1-10 coverage impact score."""
    if count >= 20:
        return 10.0
    elif count >= 10:
        return 8.0
    elif count >= 5:
        return 5.0
    else:
        return float(count)  # 1-4 map to 1-4


def confidence_multiplier(tier: str) -> int:
    """Return the multiplier for composite_potential based on confidence tier.

    MODERATE gets the highest multiplier (3) — these models have some evidence
    foundation and the most room for meaningful score improvement.
    LOW gets 2 — they need foundational work first, so each unit of research
    yields less immediate score movement.
    HIGH gets 1 — already well-evidenced, diminishing returns.
    """
    tier = (tier or "LOW").upper()
    if tier == "MODERATE":
        return 3
    elif tier == "LOW":
        return 2
    elif tier == "HIGH":
        return 1
    else:
        return 2  # Default to LOW-like behavior


def compute_rps(model: dict, naics_2d_counts: dict) -> dict:
    """Compute the Research Priority Score for a single model."""
    eq = model.get("evidence_quality", 0)
    conf = model.get("confidence_tier", "LOW")
    t_comp = model.get("composite", 0)
    naics = model.get("sector_naics", "")
    naics_2d = extract_naics_2digit(naics)

    # ── composite_potential ──────────────────────────────────────────────
    eq_gap = 10 - eq
    mult = confidence_multiplier(conf)
    t_factor = max(t_comp / 100.0, 0.5)
    composite_potential = eq_gap * mult * t_factor

    # ── evidence_gap ─────────────────────────────────────────────────────
    evidence_gap = float(eq_gap)

    # ── coverage_impact ──────────────────────────────────────────────────
    sector_count = naics_2d_counts.get(naics_2d, 1)
    coverage = coverage_impact_score(sector_count)

    # ── RPS ──────────────────────────────────────────────────────────────
    rps = (composite_potential * 0.40) + (evidence_gap * 0.35) + (coverage * 0.25)

    return {
        "id": model.get("id", "?"),
        "name": model.get("name", "?"),
        "evidence_quality": eq,
        "confidence_tier": conf,
        "t_composite": t_comp,
        "sector_naics": naics,
        "naics_2d": naics_2d,
        "sector_count": sector_count,
        # Components (for debugging/transparency)
        "composite_potential": round(composite_potential, 3),
        "evidence_gap": evidence_gap,
        "coverage_impact": coverage,
        # Final score
        "rps_score": round(rps, 3),
    }


def main():
    # ── Load data ────────────────────────────────────────────────────────
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE) as f:
        data = json.load(f)

    models = data.get("models", [])
    print(f"Loaded {len(models)} models from {DATA_FILE}\n")

    # ── Count models per 2-digit NAICS ───────────────────────────────────
    naics_2d_counts = Counter()
    for m in models:
        naics_2d = extract_naics_2digit(m.get("sector_naics", ""))
        naics_2d_counts[naics_2d] += 1

    print("Sector coverage (2-digit NAICS):")
    for naics, count in sorted(naics_2d_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  NAICS {naics}: {count} models -> coverage_impact = {coverage_impact_score(count)}")
    print(f"  ... ({len(naics_2d_counts)} unique 2-digit sectors total)\n")

    # ── Compute RPS for every model ──────────────────────────────────────
    scored = [compute_rps(m, naics_2d_counts) for m in models]
    scored.sort(key=lambda x: -x["rps_score"])

    # ── Print top 30 ────────────────────────────────────────────────────
    print("=" * 110)
    print(f"{'Rank':>4}  {'ID':<28} {'Name':<45} {'EQ':>2} {'Conf':<8} {'Comp':>5} {'NAICS':<6} {'RPS':>6}")
    print("-" * 110)
    for i, s in enumerate(scored[:30], 1):
        name_trunc = s["name"][:43]
        print(
            f"{i:>4}  {s['id']:<28} {name_trunc:<45} {s['evidence_quality']:>2} "
            f"{s['confidence_tier']:<8} {s['t_composite']:>5.1f} {s['sector_naics']:<6} {s['rps_score']:>6.2f}"
        )

    # ── Print bottom 10 (least need for research) ───────────────────────
    print(f"\n{'=' * 110}")
    print("BOTTOM 10 — Least need for additional research (should be HIGH confidence, high EQ)")
    print("-" * 110)
    print(f"{'Rank':>4}  {'ID':<28} {'Name':<45} {'EQ':>2} {'Conf':<8} {'Comp':>5} {'NAICS':<6} {'RPS':>6}")
    print("-" * 110)
    bottom_10 = list(reversed(scored[-10:]))
    for idx, s in enumerate(bottom_10):
        rank_num = len(scored) - idx
        name_trunc = s["name"][:43]
        print(
            f"{rank_num:>4}  {s['id']:<28} {name_trunc:<45} {s['evidence_quality']:>2} "
            f"{s['confidence_tier']:<8} {s['t_composite']:>5.1f} {s['sector_naics']:<6} {s['rps_score']:>6.2f}"
        )

    # ── Compare with current dashboard priorities ────────────────────────
    print(f"\n{'=' * 110}")
    print("COMPARISON: Current vs RPS-ranked research priorities")
    print("-" * 110)

    current_top_ids = []
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE) as f:
            dash = json.load(f)
        current_priorities = dash.get("research_priorities", [])
        current_top_ids = [p.get("id") for p in current_priorities[:10]]
        print(f"\nCurrent top 10 (from dashboard, ranked by composite):")
        for i, p in enumerate(current_priorities[:10], 1):
            print(
                f"  {i:>2}. [{p.get('confidence_tier','?'):<8}] EQ={p.get('evidence_quality','?'):<2} "
                f"comp={p.get('composite',0):>5.1f}  {p.get('id','?')}"
            )
    else:
        print("  (dashboard.json not found -- skipping comparison)")

    new_top_ids = [s["id"] for s in scored[:10]]

    print(f"\nNew RPS top 10:")
    for i, s in enumerate(scored[:10], 1):
        marker = " *NEW*" if s["id"] not in current_top_ids else ""
        print(
            f"  {i:>2}. [{s['confidence_tier']:<8}] EQ={s['evidence_quality']:<2} "
            f"comp={s['t_composite']:>5.1f}  RPS={s['rps_score']:>5.2f}  {s['id']}{marker}"
        )

    if current_top_ids:
        overlap = set(current_top_ids) & set(new_top_ids)
        changed = len(current_top_ids) - len(overlap)
        print(f"\nResult: {changed} of 10 priorities changed ({len(overlap)} overlap)")
        if overlap:
            print(f"  Kept: {', '.join(sorted(overlap))}")
        dropped = set(current_top_ids) - set(new_top_ids)
        if dropped:
            print(f"  Dropped: {', '.join(sorted(dropped))}")
        added = set(new_top_ids) - set(current_top_ids)
        if added:
            print(f"  Added: {', '.join(sorted(added))}")

    # ── Distribution stats ───────────────────────────────────────────────
    print(f"\n{'=' * 110}")
    print("RPS Distribution by Confidence Tier")
    print("-" * 110)
    tier_stats = defaultdict(list)
    for s in scored:
        tier_stats[s["confidence_tier"]].append(s["rps_score"])
    for tier in ["MODERATE", "LOW", "HIGH"]:
        vals = tier_stats.get(tier, [])
        if vals:
            avg = sum(vals) / len(vals)
            print(
                f"  {tier:<10}: n={len(vals):>3}, mean RPS={avg:>5.2f}, "
                f"max={max(vals):>5.2f}, min={min(vals):>5.2f}"
            )

    # ── Write output JSON ────────────────────────────────────────────────
    output = {
        "version": "v3-17",
        "generated": str(date.today()),
        "method": "RPS = composite_potential*0.40 + evidence_gap*0.35 + coverage_impact*0.25",
        "method_detail": {
            "composite_potential": "MODERATE: (10-EQ)*3, LOW: (10-EQ)*2, HIGH: (10-EQ)*1; all * max(t_composite/100, 0.5)",
            "evidence_gap": "10 - evidence_quality",
            "coverage_impact": "models in same 2-digit NAICS: 1->1, 5+->5, 10+->8, 20+->10",
        },
        "stats": {
            "total_models_scored": len(scored),
            "tier_distribution": {
                tier: {
                    "count": len(vals),
                    "mean_rps": round(sum(vals) / len(vals), 2),
                    "in_top_50": sum(1 for s in scored[:50] if s["confidence_tier"] == tier),
                }
                for tier, vals in tier_stats.items()
            },
        },
        "priorities": [
            {
                "rank": i,
                "id": s["id"],
                "name": s["name"],
                "evidence_quality": s["evidence_quality"],
                "confidence_tier": s["confidence_tier"],
                "t_composite": s["t_composite"],
                "sector_naics": s["sector_naics"],
                "rps_score": s["rps_score"],
            }
            for i, s in enumerate(scored[:50], 1)
        ],
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote top 50 research priorities to: {OUTPUT_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()
