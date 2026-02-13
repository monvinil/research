#!/usr/bin/env python3
"""
Weight Sensitivity Test — Experiment 3
Tests how T-composite rankings change under alternative axis weight schemes.

READ-ONLY analysis. Does not modify any data files.

Current weights: SN=25%, FA=25%, EC=20%, TG=15%, CE=15%
Composite formula: (SN*w_SN + FA*w_FA + EC*w_EC + TG*w_TG + CE*w_CE) / 10
"""

import json
import statistics
from pathlib import Path

DATA_FILE = Path("/Users/mv/Documents/research/data/verified/v3-12_normalized_2026-02-12.json")

# ── Weight scenarios ───────────────────────────────────────────────────────────
SCENARIOS = {
    "1_Baseline":        {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15},
    "2_FA+5_SN-5":       {"SN": 20, "FA": 30, "EC": 20, "TG": 15, "CE": 15},
    "3_FA+5_CE-5":       {"SN": 25, "FA": 30, "EC": 20, "TG": 15, "CE": 10},
    "4_FA+5_EC-5":       {"SN": 25, "FA": 30, "EC": 15, "TG": 15, "CE": 15},
    "5_FA+10_SN-5_CE-5": {"SN": 20, "FA": 35, "EC": 20, "TG": 15, "CE": 10},
    "6_Equal":           {"SN": 20, "FA": 20, "EC": 20, "TG": 20, "CE": 20},
}

# ── Category thresholds (composite-based) ─────────────────────────────────────
def category_label(composite: float) -> str:
    if composite >= 80:
        return "STRUCTURAL_WINNER"
    elif composite >= 70:
        return "FORCE_RIDER"
    elif composite >= 60:
        return "ACCESSIBLE"
    else:
        return "PARKED"


def compute_composite(scores: dict, weights: dict) -> float:
    return (
        scores["SN"] * weights["SN"]
        + scores["FA"] * weights["FA"]
        + scores["EC"] * weights["EC"]
        + scores["TG"] * weights["TG"]
        + scores["CE"] * weights["CE"]
    ) / 10.0


def main():
    # ── Load data ──────────────────────────────────────────────────────────────
    with open(DATA_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models from {DATA_FILE.name}\n")

    # Validate weights sum to 100
    for name, w in SCENARIOS.items():
        assert sum(w.values()) == 100, f"{name} weights sum to {sum(w.values())}, not 100"

    # ── Compute composites & rankings for every scenario ───────────────────────
    scenario_results = {}  # scenario -> {model_idx: entry_dict}

    for sc_name, weights in SCENARIOS.items():
        entries = []
        for i, m in enumerate(models):
            comp = compute_composite(m["scores"], weights)
            entries.append({
                "idx": i,
                "id": m["id"],
                "name": m["name"],
                "composite": comp,
            })
        # Rank: highest composite = rank 1
        entries.sort(key=lambda e: -e["composite"])
        for rank, e in enumerate(entries, 1):
            e["rank"] = rank
            e["category"] = category_label(e["composite"])
        scenario_results[sc_name] = {e["idx"]: e for e in entries}

    baseline = scenario_results["1_Baseline"]
    n = len(models)

    # ── Per-scenario comparison ────────────────────────────────────────────────
    print("=" * 100)
    print("PER-SCENARIO COMPARISON vs BASELINE")
    print("=" * 100)

    # Store rank changes per model across scenarios for stability/volatility
    all_rank_changes = {i: {} for i in range(n)}

    for sc_name, sc_data in scenario_results.items():
        rank_changes = []
        cat_changes = 0
        max_up = (0, None)   # (magnitude, entry)  — negative delta = rose
        max_down = (0, None) # positive delta = dropped

        composites = []

        for idx in range(n):
            bl = baseline[idx]
            sc = sc_data[idx]
            delta = sc["rank"] - bl["rank"]  # positive = dropped, negative = rose
            rank_changes.append(abs(delta))
            all_rank_changes[idx][sc_name] = delta
            composites.append(sc["composite"])

            if bl["category"] != sc["category"]:
                cat_changes += 1

            if delta < max_up[0]:
                max_up = (delta, sc)
            if delta > max_down[0]:
                max_down = (delta, sc)

        mean_abs = statistics.mean(rank_changes)
        moved_10 = sum(1 for r in rank_changes if r >= 10)
        moved_20 = sum(1 for r in rank_changes if r >= 20)

        # Pearson correlation of new rank vs baseline rank
        bl_ranks = [baseline[i]["rank"] for i in range(n)]
        sc_ranks = [sc_data[i]["rank"] for i in range(n)]
        mean_bl = statistics.mean(bl_ranks)
        mean_sc = statistics.mean(sc_ranks)
        cov = sum((bl_ranks[i] - mean_bl) * (sc_ranks[i] - mean_sc) for i in range(n)) / n
        std_bl = (sum((r - mean_bl) ** 2 for r in bl_ranks) / n) ** 0.5
        std_sc = (sum((r - mean_sc) ** 2 for r in sc_ranks) / n) ** 0.5
        pearson = cov / (std_bl * std_sc) if std_bl * std_sc > 0 else 1.0

        comp_mean = statistics.mean(composites)
        comp_stdev = statistics.stdev(composites) if len(composites) > 1 else 0
        comp_min = min(composites)
        comp_max = max(composites)

        print(f"\n{'─' * 100}")
        w = SCENARIOS[sc_name]
        print(f"Scenario: {sc_name}")
        print(f"  Weights: SN={w['SN']}  FA={w['FA']}  EC={w['EC']}  TG={w['TG']}  CE={w['CE']}")
        print(f"  Mean absolute rank change:  {mean_abs:.2f}")
        if max_up[1]:
            e = max_up[1]
            print(f"  Max rank RISE:              {-max_up[0]} positions — {e['id']} ({e['name']})")
        if max_down[1]:
            e = max_down[1]
            print(f"  Max rank DROP:              {max_down[0]} positions — {e['id']} ({e['name']})")
        print(f"  Models moving >= 10 ranks:  {moved_10}")
        print(f"  Models moving >= 20 ranks:  {moved_20}")
        print(f"  Category boundary crossers: {cat_changes}")
        print(f"  Pearson r (rank vs baseline):{pearson:.6f}")
        print(f"  Composite stats:  mean={comp_mean:.2f}  stdev={comp_stdev:.2f}  range=[{comp_min:.2f}, {comp_max:.2f}]")

    # ── Stability analysis ─────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("STABILITY ANALYSIS: Models rank-stable across ALL scenarios (move <= 3 ranks in every scenario)")
    print("=" * 100)

    non_baseline_scenarios = [s for s in SCENARIOS if s != "1_Baseline"]
    stable_models = []
    for idx in range(n):
        max_change = max(abs(all_rank_changes[idx][s]) for s in non_baseline_scenarios)
        if max_change <= 3:
            stable_models.append((idx, baseline[idx]["rank"], baseline[idx]["id"], baseline[idx]["name"]))

    stable_models.sort(key=lambda x: x[1])
    print(f"\nCount: {len(stable_models)} / {n} models are rank-stable (move <= 3 in ALL scenarios)")
    print(f"That is {len(stable_models)/n*100:.1f}% of models\n")

    if len(stable_models) <= 50:
        print(f"  {'Rank':<6} {'ID':<25} {'Name'}")
        for _, rank, mid, mname in stable_models:
            print(f"  {rank:<6} {mid:<25} {mname}")
    else:
        print(f"  (Showing first 30 and last 10)")
        print(f"  {'Rank':<6} {'ID':<25} {'Name'}")
        for _, rank, mid, mname in stable_models[:30]:
            print(f"  {rank:<6} {mid:<25} {mname}")
        print(f"  ...")
        for _, rank, mid, mname in stable_models[-10:]:
            print(f"  {rank:<6} {mid:<25} {mname}")

    # ── Volatility analysis ────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("VOLATILITY ANALYSIS: Models moving >= 15 ranks in >= 3 scenarios")
    print("=" * 100)

    volatile_models = []
    for idx in range(n):
        big_moves = sum(1 for s in non_baseline_scenarios if abs(all_rank_changes[idx][s]) >= 15)
        if big_moves >= 3:
            changes = {s: all_rank_changes[idx][s] for s in non_baseline_scenarios}
            volatile_models.append((
                baseline[idx]["id"],
                baseline[idx]["name"],
                baseline[idx]["rank"],
                changes,
            ))

    volatile_models.sort(key=lambda x: x[2])
    print(f"\nCount: {len(volatile_models)} volatile models\n")

    if volatile_models:
        sc_short = {
            "2_FA+5_SN-5": "FA+5/SN-5",
            "3_FA+5_CE-5": "FA+5/CE-5",
            "4_FA+5_EC-5": "FA+5/EC-5",
            "5_FA+10_SN-5_CE-5": "FA+10",
            "6_Equal": "Equal",
        }
        header_labels = [sc_short.get(s, s) for s in non_baseline_scenarios]
        header = f"  {'BL Rk':<7} {'ID':<25} {'Name':<42} " + "  ".join(f"{l:>10}" for l in header_labels)
        print(header)
        print("  " + "─" * (len(header) - 2))
        for mid, mname, rank, changes in volatile_models:
            deltas = "  ".join(f"{changes[s]:>+10d}" for s in non_baseline_scenarios)
            print(f"  {rank:<7} {mid:<25} {mname[:41]:<42} {deltas}")

    # ── Top 20 baseline models across scenarios ────────────────────────────────
    print("\n" + "=" * 100)
    print("TOP 20 BASELINE MODELS: Rank across all 6 scenarios")
    print("=" * 100)

    top20_indices = [idx for idx in range(n) if baseline[idx]["rank"] <= 20]
    top20_indices.sort(key=lambda idx: baseline[idx]["rank"])

    sc_names = list(SCENARIOS.keys())
    sc_short_all = {
        "1_Baseline": "Baseline",
        "2_FA+5_SN-5": "FA+5/SN-5",
        "3_FA+5_CE-5": "FA+5/CE-5",
        "4_FA+5_EC-5": "FA+5/EC-5",
        "5_FA+10_SN-5_CE-5": "FA+10",
        "6_Equal": "Equal",
    }
    header_labels = [sc_short_all.get(s, s) for s in sc_names]
    header = f"\n  {'BL Rk':<7} {'ID':<25} {'Name':<38}"
    for l in header_labels:
        header += f" {l:>10}"
    print(header)
    print("  " + "─" * (len(header.strip()) + 2))

    for idx in top20_indices:
        bl = baseline[idx]
        row = f"  {bl['rank']:<7} {bl['id']:<25} {bl['name'][:37]:<38}"
        for sc_name in sc_names:
            row += f" {scenario_results[sc_name][idx]['rank']:>10}"
        print(row)

    # ── Category sensitivity ───────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("CATEGORY SENSITIVITY")
    print("=" * 100)

    # PARKED models (composite < 60 in baseline) that become non-PARKED in any scenario
    parked_baseline = [idx for idx in range(n) if baseline[idx]["composite"] < 60]
    parked_escaped = []
    for idx in parked_baseline:
        escaped_in = []
        for sc_name in non_baseline_scenarios:
            if scenario_results[sc_name][idx]["composite"] >= 60:
                escaped_in.append(sc_name)
        if escaped_in:
            parked_escaped.append((
                baseline[idx]["id"],
                baseline[idx]["name"],
                baseline[idx]["composite"],
                escaped_in,
                {s: scenario_results[s][idx]["composite"] for s in escaped_in},
            ))

    print(f"\nPARKED models (baseline composite < 60): {len(parked_baseline)} total")
    print(f"PARKED models that escape (composite >= 60 in any scenario): {len(parked_escaped)}")
    if parked_escaped:
        print(f"\n  {'ID':<25} {'Name':<40} {'BL Comp':>8}  Escapes in (new composite)")
        for mid, mname, bl_comp, scenarios_list, comps in parked_escaped:
            esc_str = ", ".join(f"{s}={comps[s]:.1f}" for s in scenarios_list)
            print(f"  {mid:<25} {mname[:39]:<40} {bl_comp:>8.2f}  {esc_str}")

    # STRUCTURAL_WINNER (>= 80) that lose status in any scenario
    sw_baseline = [idx for idx in range(n) if baseline[idx]["composite"] >= 80]
    sw_lost = []
    for idx in sw_baseline:
        lost_in = []
        for sc_name in non_baseline_scenarios:
            if scenario_results[sc_name][idx]["composite"] < 80:
                lost_in.append(sc_name)
        if lost_in:
            sw_lost.append((
                baseline[idx]["id"],
                baseline[idx]["name"],
                baseline[idx]["composite"],
                lost_in,
                {s: scenario_results[s][idx]["composite"] for s in lost_in},
            ))

    print(f"\nSTRUCTURAL_WINNER models (baseline composite >= 80): {len(sw_baseline)} total")
    print(f"STRUCTURAL_WINNER models that LOSE status in any scenario: {len(sw_lost)}")
    if sw_lost:
        sw_lost.sort(key=lambda x: x[2])
        print(f"\n  {'ID':<25} {'Name':<40} {'BL Comp':>8}  Loses in (new composite)")
        for mid, mname, bl_comp, scenarios_list, comps in sw_lost:
            loss_str = ", ".join(f"{s}={comps[s]:.1f}" for s in scenarios_list)
            print(f"  {mid:<25} {mname[:39]:<40} {bl_comp:>8.2f}  {loss_str}")

    # FORCE_RIDER gains (models below 70 that reach >= 70)
    below_fr_baseline = [idx for idx in range(n) if baseline[idx]["composite"] < 70]
    fr_gained = []
    for idx in below_fr_baseline:
        gained_in = []
        for sc_name in non_baseline_scenarios:
            if scenario_results[sc_name][idx]["composite"] >= 70:
                gained_in.append(sc_name)
        if gained_in:
            fr_gained.append((
                baseline[idx]["id"],
                baseline[idx]["name"],
                baseline[idx]["composite"],
                gained_in,
                {s: scenario_results[s][idx]["composite"] for s in gained_in},
            ))

    print(f"\nModels below FORCE_RIDER (baseline < 70): {len(below_fr_baseline)} total")
    print(f"Models that GAIN FORCE_RIDER status (>= 70) in any scenario: {len(fr_gained)}")
    if fr_gained:
        fr_gained.sort(key=lambda x: -x[2])
        print(f"\n  {'ID':<25} {'Name':<40} {'BL Comp':>8}  Gains in (new composite)")
        for mid, mname, bl_comp, scenarios_list, comps in fr_gained[:30]:
            gain_str = ", ".join(f"{s}={comps[s]:.1f}" for s in scenarios_list)
            print(f"  {mid:<25} {mname[:39]:<40} {bl_comp:>8.2f}  {gain_str}")
        if len(fr_gained) > 30:
            print(f"  ... and {len(fr_gained) - 30} more")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(f"\n  Total models analyzed: {n}")
    print(f"  Rank-stable models (<=3 in all scenarios): {len(stable_models)} ({len(stable_models)/n*100:.1f}%)")
    print(f"  Volatile models (>=15 ranks in >=3 scenarios): {len(volatile_models)}")
    print(f"  PARKED models escaping in any scenario: {len(parked_escaped)} / {len(parked_baseline)}")
    print(f"  STRUCTURAL_WINNERs losing status in any scenario: {len(sw_lost)} / {len(sw_baseline)}")
    print(f"  Models gaining FORCE_RIDER in any scenario: {len(fr_gained)} / {len(below_fr_baseline)}")

    # Mean absolute rank change per scenario (excluding baseline)
    print(f"\n  Mean absolute rank change by scenario:")
    for sc_name in non_baseline_scenarios:
        changes = [abs(all_rank_changes[idx][sc_name]) for idx in range(n)]
        print(f"    {sc_name:<25} {statistics.mean(changes):>6.2f}")

    print()


if __name__ == "__main__":
    main()
