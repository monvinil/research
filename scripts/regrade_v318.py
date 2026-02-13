#!/usr/bin/env python3
"""
v3-18 Systematic Regrading: 5 pattern-based corrections across all 608 models.

Corrections:
  1. SN Skepticism Discount — dampen high-SN, low-EQ claims (70 models)
  2. Flat Profile Differentiation — architecture-based axis emphasis (34 models)
  3. FA Validation Gate — cap FA at 7.5 if no evidence supports >8 (23 models)
  4. FEAR_ECONOMY Trust Reclassification — flag trust compounders (29 models)
  5. PARKED Revalidation — move qualifying PARKEDs to CONDITIONAL (109 models)

After corrections: recompute composites, re-rank, log all changes.
"""

import json
import statistics
import copy
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
CHANGELOG = Path("/Users/mv/Documents/research/data/analysis/v318_regrade_changelog.md")

# ── Architecture axis emphasis for flat profiles (Correction 2) ──
# Format: {axis: delta}
ARCH_AXIS_EMPHASIS = {
    "acquire_and_modernize":     {"SN": 0.5, "TG": 1.0, "CE": -0.5},
    "vertical_saas":             {"FA": 0.5, "SN": -0.5},
    "platform_infrastructure":   {"SN": 0.5, "CE": 0.5},
    "data_compounding":          {"SN": 1.0, "TG": -0.5},
    "rollup_consolidation":      {"SN": 0.5, "TG": 0.5, "CE": -0.5},
    "marketplace_network":       {"FA": 0.5, "SN": -0.5},
    "full_service_replacement":  {"FA": 0.5, "EC": 0.5, "SN": -0.5},
    "regulatory_moat_builder":   {"EC": 1.0, "SN": -0.5},
    "service_platform":          {"FA": 0.5, "SN": -1.0},
    "physical_production_ai":    {"SN": 1.0, "TG": 0.5, "CE": -0.5},
    "hardware_ai":               {"SN": 1.0, "CE": -0.5},
    "robotics_automation":       {"SN": 1.0, "TG": 0.5, "CE": -1.0},
    "ai_copilot":                {"FA": 1.0, "SN": -1.0},
    "compliance_automation":     {"EC": 0.5, "FA": 0.5, "SN": -0.5},
    "arbitrage_window":          {"TG": 1.0, "SN": -1.0, "CE": 0.5},
    # v3-18 new
    "open_core_ecosystem":       {"SN": 0.5, "CE": 0.5, "TG": -0.5},
    "outcome_based":             {"FA": 0.5, "CE": 0.5, "SN": -0.5},
    "coordination_protocol":     {"SN": 0.5, "EC": 0.5, "TG": -0.5},
}

# Forces that are currently "accelerating" (from state.json v27)
ACCELERATING_FORCES = {"F1", "F2", "F3", "F4", "F5", "F6"}


def compute_composite(scores):
    """(SN*25 + FA*25 + EC*20 + TG*15 + CE*15) / 10"""
    return round(
        (scores["SN"] * 25 + scores["FA"] * 25 + scores["EC"] * 20 +
         scores["TG"] * 15 + scores["CE"] * 15) / 10, 2
    )


def clamp(val, lo=1.0, hi=10.0):
    return max(lo, min(hi, round(val, 1)))


def main():
    print("=" * 70)
    print("v3-18 SYSTEMATIC REGRADING: 5 Pattern-Based Corrections")
    print("=" * 70)
    print()

    # Load
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # Deep copy for before/after comparison
    originals = {m["id"]: copy.deepcopy(m["scores"]) for m in models}
    original_cats = {m["id"]: m.get("primary_category") for m in models}
    original_composites = {m["id"]: m["composite"] for m in models}

    changes = {
        "sn_discount": [],
        "flat_differentiation": [],
        "fa_gate": [],
        "trust_reclassification": [],
        "parked_revalidation": [],
    }

    # ── Correction 1: SN Skepticism Discount ──
    print("\n--- Correction 1: SN Skepticism Discount ---")
    sn_center = 5.5  # mean SN, dampen toward this
    for m in models:
        sn = m["scores"]["SN"]
        eq = m.get("evidence_quality", 0)
        if sn > 7 and eq < 6:
            has_real_polanyi = (
                m.get("polanyi") and
                m["polanyi"].get("source") != "sector_proxy_v317"
            )
            if has_real_polanyi:
                # Lighter discount: 90% of distance from center preserved
                new_sn = clamp(sn_center + (sn - sn_center) * 0.90)
            else:
                # Stronger discount: 80% of distance from center preserved
                new_sn = clamp(sn_center + (sn - sn_center) * 0.80)

            if abs(new_sn - sn) > 0.05:
                changes["sn_discount"].append({
                    "id": m["id"],
                    "name": m["name"],
                    "old_sn": sn,
                    "new_sn": new_sn,
                    "eq": eq,
                    "polanyi_real": has_real_polanyi,
                })
                m["scores"]["SN"] = new_sn

    print(f"  Adjusted: {len(changes['sn_discount'])} models")

    # ── Correction 2: Flat Profile Differentiation ──
    print("\n--- Correction 2: Flat Profile Differentiation ---")
    for m in models:
        scores = m["scores"]
        vals = [scores["SN"], scores["FA"], scores["EC"], scores["TG"], scores["CE"]]
        score_range = max(vals) - min(vals)
        if score_range <= 1.0:
            arch = m.get("architecture", "")
            emphasis = ARCH_AXIS_EMPHASIS.get(arch)
            if emphasis:
                old_scores = dict(scores)
                for axis, delta in emphasis.items():
                    scores[axis] = clamp(scores[axis] + delta)
                new_range = max(scores[a] for a in ["SN", "FA", "EC", "TG", "CE"]) - \
                           min(scores[a] for a in ["SN", "FA", "EC", "TG", "CE"])
                changes["flat_differentiation"].append({
                    "id": m["id"],
                    "name": m["name"],
                    "old_range": round(score_range, 1),
                    "new_range": round(new_range, 1),
                    "arch": arch,
                    "adjustments": emphasis,
                })

    print(f"  Differentiated: {len(changes['flat_differentiation'])} models")

    # ── Correction 3: FA Validation Gate ──
    print("\n--- Correction 3: FA Validation Gate ---")
    for m in models:
        fa = m["scores"]["FA"]
        if fa > 8.0:
            has_dd = bool(m.get("deep_dive_evidence"))
            if has_dd:
                continue  # validated, keep high FA
            # Check if model has sufficient evidence to justify FA > 8
            forces = m.get("forces_v3", [])
            has_real_polanyi = (
                m.get("polanyi") and
                m["polanyi"].get("source") != "sector_proxy_v317"
            )
            naics = m.get("sector_naics", "")
            has_4digit = len(naics) >= 4

            if len(forces) >= 3 and has_real_polanyi and has_4digit:
                continue  # has enough evidence signals, keep

            old_fa = fa
            m["scores"]["FA"] = 7.5
            changes["fa_gate"].append({
                "id": m["id"],
                "name": m["name"],
                "old_fa": old_fa,
                "new_fa": 7.5,
                "forces_count": len(forces),
                "polanyi_real": has_real_polanyi,
                "naics_4digit": has_4digit,
            })

    print(f"  Capped: {len(changes['fa_gate'])} models")

    # ── Correction 4: FEAR_ECONOMY Trust Reclassification ──
    print("\n--- Correction 4: FEAR_ECONOMY Trust Reclassification ---")
    for m in models:
        if m.get("primary_category") != "FEAR_ECONOMY":
            continue
        moa = m.get("vcr", {}).get("scores", {}).get("MOA", 0)
        if moa >= 7:
            m["trust_compounder"] = True
            old_moa = moa
            if moa < 10:
                m["vcr"]["scores"]["MOA"] = clamp(moa + 0.5)
                # Recompute VCR composite
                vs = m["vcr"]["scores"]
                m["vcr"]["composite"] = round(
                    (vs["MKT"] * 25 + vs["CAP"] * 25 + vs["ECO"] * 20 +
                     vs["VEL"] * 15 + vs["MOA"] * 15) / 10, 2
                )
            changes["trust_reclassification"].append({
                "id": m["id"],
                "name": m["name"],
                "old_moa": old_moa,
                "new_moa": m["vcr"]["scores"]["MOA"],
            })

    print(f"  Trust compounders flagged: {len(changes['trust_reclassification'])} models")

    # ── Correction 5: PARKED Revalidation ──
    print("\n--- Correction 5: PARKED Revalidation ---")
    for m in models:
        if m.get("primary_category") != "PARKED":
            continue
        sn = m["scores"]["SN"]
        if sn <= 4:
            continue  # too low to revalidate

        # Check if any tagged force is accelerating
        forces = m.get("forces_v3", [])
        has_accelerating = any(
            f[:2] in ACCELERATING_FORCES for f in forces
        )
        if not has_accelerating:
            continue

        # Move to CONDITIONAL
        old_cat = m.get("primary_category")
        m["primary_category"] = "CONDITIONAL"
        if isinstance(m.get("category"), list):
            if "PARKED" in m["category"]:
                m["category"].remove("PARKED")
            if "CONDITIONAL" not in m["category"]:
                m["category"].append("CONDITIONAL")
        m["revalidated_v318"] = True
        # Bump TG slightly
        old_tg = m["scores"]["TG"]
        m["scores"]["TG"] = clamp(old_tg + 0.5)

        changes["parked_revalidation"].append({
            "id": m["id"],
            "name": m["name"],
            "old_cat": old_cat,
            "new_cat": "CONDITIONAL",
            "sn": sn,
            "forces": forces,
            "old_tg": old_tg,
            "new_tg": m["scores"]["TG"],
        })

    print(f"  Revalidated PARKED → CONDITIONAL: {len(changes['parked_revalidation'])} models")

    # ── Recompute composites and re-rank ──
    print("\n--- Recomputing composites and re-ranking ---")
    changed_count = 0
    for m in models:
        old_comp = m["composite"]
        new_comp = compute_composite(m["scores"])
        if abs(new_comp - old_comp) > 0.01:
            m["composite"] = new_comp
            changed_count += 1

    # Re-rank by composite
    models.sort(key=lambda m: (-m["composite"], m["id"]))
    for i, m in enumerate(models, 1):
        m["rank"] = i

    print(f"  Composites changed: {changed_count}")

    # ── Validation checks ──
    print("\n--- Validation ---")
    composites = [m["composite"] for m in models]
    sn_vals = [m["scores"]["SN"] for m in models]
    fa_vals = [m["scores"]["FA"] for m in models]

    t_stdev = statistics.stdev(composites)
    sn_stdev = statistics.stdev(sn_vals)
    t_mean = statistics.mean(composites)

    # Correlation check (Pearson r)
    def pearson_r(x, y):
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        den = (sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)) ** 0.5
        return num / den if den > 0 else 0

    r_sn_fa = pearson_r(sn_vals, fa_vals)
    cla_vals = [m.get("cla", {}).get("composite", 0) for m in models]
    r_t_cla = pearson_r(composites, cla_vals)
    vcr_vals = [m.get("vcr", {}).get("composite", 0) for m in models]
    r_t_vcr = pearson_r(composites, vcr_vals)

    print(f"  T-composite: mean={t_mean:.1f}, stdev={t_stdev:.1f} (target >7.5, was 7.2)")
    print(f"  SN stdev: {sn_stdev:.2f}")
    print(f"  r(SN,FA): {r_sn_fa:.3f} (target <0.35)")
    print(f"  r(T,CLA): {r_t_cla:.3f} (target <0.20)")
    print(f"  r(T,VCR): {r_t_vcr:.3f} (target <0.20)")

    # Max rank change
    max_rank_change = 0
    max_rank_model = None
    old_rank_map = {m["id"]: i + 1 for i, m in enumerate(
        sorted(models, key=lambda m: (-original_composites[m["id"]], m["id"]))
    )}
    for m in models:
        old_r = old_rank_map[m["id"]]
        delta = abs(m["rank"] - old_r)
        if delta > max_rank_change:
            max_rank_change = delta
            max_rank_model = m["id"]

    print(f"  Max rank change: {max_rank_change} ({max_rank_model})")

    # Category distribution after
    cat_dist = Counter(m.get("primary_category") for m in models)
    print(f"\n  Category distribution:")
    for cat, count in sorted(cat_dist.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

    within_1sd = sum(1 for c in composites if abs(c - t_mean) <= t_stdev)
    print(f"\n  Within ±1σ: {within_1sd}/{len(models)} ({within_1sd * 100 / len(models):.1f}%)")

    # ── Update summary stats ──
    data["summary"]["composite_stats"] = {
        "max": max(composites),
        "min": min(composites),
        "mean": round(t_mean, 2),
        "median": round(statistics.median(composites), 2),
    }
    data["summary"]["primary_category_distribution"] = dict(
        sorted(cat_dist.items(), key=lambda x: -x[1])
    )

    # ── Write back ──
    print("\n--- Writing normalized file ---")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Written: {NORMALIZED_FILE}")

    # ── Write changelog ──
    print("--- Writing changelog ---")
    lines = [
        "# v3-18 Regrade Changelog\n",
        f"\nTotal models: {len(models)}",
        f"Composites changed: {changed_count}",
        f"T-composite stdev: 7.2 → {t_stdev:.1f}",
        f"r(SN,FA): {r_sn_fa:.3f}",
        f"r(T,CLA): {r_t_cla:.3f}",
        f"r(T,VCR): {r_t_vcr:.3f}",
        f"Max rank change: {max_rank_change} ({max_rank_model})\n",
    ]

    lines.append(f"\n## Correction 1: SN Skepticism Discount ({len(changes['sn_discount'])} models)\n")
    for c in sorted(changes["sn_discount"], key=lambda x: x["old_sn"] - x["new_sn"], reverse=True)[:20]:
        lines.append(f"- **{c['id']}** ({c['name'][:50]}): SN {c['old_sn']:.1f}→{c['new_sn']:.1f} (EQ={c['eq']}, polanyi={'real' if c['polanyi_real'] else 'proxy/none'})")

    lines.append(f"\n## Correction 2: Flat Profile Differentiation ({len(changes['flat_differentiation'])} models)\n")
    for c in changes["flat_differentiation"]:
        lines.append(f"- **{c['id']}** ({c['name'][:50]}): range {c['old_range']}→{c['new_range']} ({c['arch']})")

    lines.append(f"\n## Correction 3: FA Validation Gate ({len(changes['fa_gate'])} models)\n")
    for c in changes["fa_gate"]:
        lines.append(f"- **{c['id']}** ({c['name'][:50]}): FA {c['old_fa']}→{c['new_fa']} (forces={c['forces_count']}, polanyi={'real' if c['polanyi_real'] else 'no'}, 4digit={'yes' if c['naics_4digit'] else 'no'})")

    lines.append(f"\n## Correction 4: FEAR_ECONOMY Trust Reclassification ({len(changes['trust_reclassification'])} models)\n")
    for c in changes["trust_reclassification"]:
        lines.append(f"- **{c['id']}** ({c['name'][:50]}): MOA {c['old_moa']}→{c['new_moa']} → trust_compounder=true")

    lines.append(f"\n## Correction 5: PARKED Revalidation ({len(changes['parked_revalidation'])} models)\n")
    for c in changes["parked_revalidation"]:
        lines.append(f"- **{c['id']}** ({c['name'][:50]}): {c['old_cat']}→{c['new_cat']} (SN={c['sn']:.1f}, forces={c['forces']}, TG {c['old_tg']}→{c['new_tg']})")

    # Top 20 biggest rank movers
    lines.append(f"\n## Biggest Rank Changes (Top 20)\n")
    rank_changes = []
    for m in models:
        old_r = old_rank_map[m["id"]]
        delta = m["rank"] - old_r
        if delta != 0:
            rank_changes.append((m["id"], m["name"], old_r, m["rank"], delta))
    rank_changes.sort(key=lambda x: abs(x[4]), reverse=True)
    for rid, rname, old_r, new_r, delta in rank_changes[:20]:
        direction = "↑" if delta < 0 else "↓"
        lines.append(f"- **{rid}** ({rname[:50]}): #{old_r}→#{new_r} ({direction}{abs(delta)})")

    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANGELOG, "w") as f:
        f.write("\n".join(lines))
    print(f"  Written: {CHANGELOG}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("v3-18 REGRADING COMPLETE")
    print("=" * 70)
    total_changes = sum(len(v) for v in changes.values())
    print(f"\n  Total corrections applied: {total_changes}")
    print(f"  SN discount: {len(changes['sn_discount'])}")
    print(f"  Flat differentiated: {len(changes['flat_differentiation'])}")
    print(f"  FA gated: {len(changes['fa_gate'])}")
    print(f"  Trust compounders: {len(changes['trust_reclassification'])}")
    print(f"  PARKED → CONDITIONAL: {len(changes['parked_revalidation'])}")


if __name__ == "__main__":
    main()
