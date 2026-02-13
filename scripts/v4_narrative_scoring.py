#!/usr/bin/env python3
"""
v4 Narrative Scoring: Score transformation narratives on 5 TNS axes.

TNS Axes (Transformation Narrative Score):
  EM (Economic Magnitude, 25%): GDP/employment impact
  FC (Force Convergence, 25%):  Force count × velocity × alignment
  ES (Evidence Strength, 20%):  Data confirming direction
  TC (Timing Confidence, 15%):  Timeline reliability
  IR (Irreversibility, 15%):    Once started, can this reverse?

Composite: (EM*25 + FC*25 + ES*20 + TC*15 + IR*15) / 10 → 0-100

Categories: DEFINING (>=80), MAJOR (>=65), MODERATE (>=50), EMERGING (>=35), SPECULATIVE (<35)
"""

import json
import statistics
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data/v4"
NARRATIVES_FILE = V4_DIR / "narratives.json"
MODELS_FILE = V4_DIR / "models.json"
STATE_FILE = V4_DIR / "state.json"

# QCEW employment data by NAICS (approximate, from cache/state)
SECTOR_EMPLOYMENT = {
    "52": 7_000_000,
    "54": 10_000_000,
    "31-33": 12_870_000,
    "62": 21_300_000,
    "56": 9_400_000,
    "23": 8_200_000,
    "42": 6_000_000,
    "928110": 800_000,
    "61": 3_500_000,
    "5415": 2_460_000,
    "55": 2_550_000,
    "53": 2_390_000,
    "523": 1_070_000,
    "44-45": 15_530_000,
    "44-45/cross": 15_530_000,
    "N/A-MICRO": 33_900_000,
    "51": 3_200_000,
    "22": 550_000,
}

# Total US private employment for scaling
US_TOTAL_EMPLOYMENT = 158_000_000

# Velocity weights
VELOCITY_WEIGHTS = {
    "accelerating": 1.0,
    "shifting": 0.7,
    "steady": 0.5,
    "decelerating": 0.3,
    "reversing": 0.1,
}

# Phase → timing confidence mapping
PHASE_TC = {
    "acceleration": 8.5,
    "early_disruption": 6.5,
    "pre_disruption": 4.5,
    "monitoring": 3.0,
}

TNS_WEIGHTS = {"EM": 25, "FC": 25, "ES": 20, "TC": 15, "IR": 15}

CATEGORIES = [
    ("DEFINING", 80),
    ("MAJOR", 65),
    ("MODERATE", 50),
    ("EMERGING", 35),
    ("SPECULATIVE", 0),
]


def score_economic_magnitude(narrative):
    """EM: How large is the GDP/employment impact?"""
    sectors = narrative.get("sectors", [])
    total_employment = 0
    for s in sectors:
        naics = s.get("naics", "")
        emp = SECTOR_EMPLOYMENT.get(naics, 500_000)
        total_employment += emp

    # Scale: log of employment share
    share = total_employment / US_TOTAL_EMPLOYMENT
    if share >= 0.10:
        return 10.0
    elif share >= 0.05:
        return 9.0
    elif share >= 0.03:
        return 8.0
    elif share >= 0.02:
        return 7.0
    elif share >= 0.01:
        return 6.0
    elif share >= 0.005:
        return 5.0
    elif share >= 0.002:
        return 4.0
    else:
        return 3.0


def score_force_convergence(narrative, force_velocities):
    """FC: How many forces drive this, how aligned, how accelerating?"""
    forces = narrative.get("forces_acting", [])
    if not forces:
        return 3.0

    # Base: force count (2 forces = 5, 3 = 7, 4 = 8, 5+ = 9)
    count_score = min(3 + len(forces) * 1.5, 9.5)

    # Velocity bonus: average velocity of acting forces
    velocities = []
    for f in forces:
        fv = force_velocities.get(f, {})
        vel = fv.get("velocity", "steady")
        velocities.append(VELOCITY_WEIGHTS.get(vel, 0.5))

    avg_velocity = sum(velocities) / len(velocities) if velocities else 0.5

    # Scale: count_score adjusted by velocity
    score = count_score * (0.6 + 0.4 * avg_velocity)
    return round(min(max(score, 1.0), 10.0), 1)


def score_evidence_strength(narrative, models_data):
    """ES: How much hard data confirms the direction?"""
    # Count evidence sources
    model_count = sum(
        len(narrative["outputs"].get(bucket, []))
        for bucket in ["what_works", "whats_needed", "what_dies"]
    )
    pattern_count = len(narrative.get("supporting_patterns", []))
    has_deep_dive = narrative.get("v3_models_rated", 0) >= 10
    has_evidence_summary = len(narrative.get("summary", "")) > 200

    # Check model evidence quality
    narrative_model_ids = set()
    for bucket in ["what_works", "whats_needed", "what_dies"]:
        narrative_model_ids.update(narrative["outputs"].get(bucket, []))

    high_eq_count = 0
    deep_dive_count = 0
    models = models_data.get("models", [])
    for m in models:
        if m["id"] in narrative_model_ids:
            if m.get("evidence_quality", 0) >= 7:
                high_eq_count += 1
            if m.get("deep_dive_evidence") and isinstance(m.get("deep_dive_evidence"), str):
                deep_dive_count += 1

    # Scoring
    score = 3.0  # baseline
    score += min(model_count / 10, 2.5)   # up to 2.5 for model count
    score += min(pattern_count / 3, 1.5)   # up to 1.5 for pattern refs
    score += 1.5 if has_deep_dive else 0   # 1.5 for deep dive
    score += 0.5 if has_evidence_summary else 0
    score += min(high_eq_count / 5, 1.0)   # up to 1.0 for high-EQ models
    score += min(deep_dive_count / 3, 0.5) # up to 0.5 for deep dive evidence

    return round(min(max(score, 1.0), 10.0), 1)


def score_timing_confidence(narrative):
    """TC: How confident are we in the timeline?"""
    phase = narrative.get("transformation_phase", "pre_disruption")
    base = PHASE_TC.get(phase, 4.0)

    # Bonus for having year-by-year projections with content
    yby = narrative.get("year_by_year", {})
    has_detail = sum(1 for y in yby.values() if len(y.get("indicators", [])) > 0)
    bonus = min(has_detail * 0.3, 1.5)

    # Bonus for confidence.timing being "high"
    if narrative.get("confidence", {}).get("timing") == "high":
        bonus += 1.0

    return round(min(max(base + bonus, 1.0), 10.0), 1)


def score_irreversibility(narrative):
    """IR: Once started, can this be reversed?"""
    forces = narrative.get("forces_acting", [])
    score = 4.0  # baseline

    # F2 demographics is irreversible
    if "F2_demographics" in forces:
        score += 2.5

    # F3 geopolitics creates structural lock-in (tariffs, regulations)
    if "F3_geopolitics" in forces:
        score += 1.0

    # Acceleration phase = more committed
    phase = narrative.get("transformation_phase", "pre_disruption")
    if phase == "acceleration":
        score += 1.5
    elif phase == "early_disruption":
        score += 0.5

    # Low fear friction = easier adoption = harder to reverse
    ff = narrative.get("fear_friction", {})
    gap = ff.get("gap", 2)
    if gap <= 1:
        score += 1.0
    elif gap >= 4:
        score -= 1.0

    return round(min(max(score, 1.0), 10.0), 1)


def compute_composite(tns):
    """(EM*25 + FC*25 + ES*20 + TC*15 + IR*15) / 10"""
    return round(
        (tns["economic_magnitude"] * 25 +
         tns["force_convergence"] * 25 +
         tns["evidence_strength"] * 20 +
         tns["timing_confidence"] * 15 +
         tns["irreversibility"] * 15) / 10,
        2
    )


def categorize(composite):
    for cat, threshold in CATEGORIES:
        if composite >= threshold:
            return cat
    return "SPECULATIVE"


def main():
    print("=" * 70)
    print("v4 NARRATIVE SCORING: Transformation Narrative Score (TNS)")
    print("=" * 70)
    print()

    # Load data
    print("Loading data...")
    with open(NARRATIVES_FILE) as f:
        narr_data = json.load(f)
    narratives = narr_data["narratives"]

    with open(MODELS_FILE) as f:
        models_data = json.load(f)

    with open(STATE_FILE) as f:
        state = json.load(f)

    force_velocities = state.get("force_velocities", {})
    print(f"  {len(narratives)} narratives, {models_data.get('count', 0)} models")
    print()

    # Score each narrative
    print("Scoring narratives...")
    print(f"{'ID':<10} {'Name':<45} {'EM':>4} {'FC':>4} {'ES':>4} {'TC':>4} {'IR':>4} {'Comp':>6} {'Cat':<12}")
    print("-" * 100)

    composites = []
    for n in narratives:
        em = score_economic_magnitude(n)
        fc = score_force_convergence(n, force_velocities)
        es = score_evidence_strength(n, models_data)
        tc = score_timing_confidence(n)
        ir = score_irreversibility(n)

        tns = {
            "economic_magnitude": em,
            "force_convergence": fc,
            "evidence_strength": es,
            "timing_confidence": tc,
            "irreversibility": ir,
        }
        tns["composite"] = compute_composite(tns)
        tns["category"] = categorize(tns["composite"])

        n["tns"] = tns
        composites.append(tns["composite"])

        print(f"{n['narrative_id']:<10} {n['name'][:44]:<45} {em:4.1f} {fc:4.1f} {es:4.1f} {tc:4.1f} {ir:4.1f} {tns['composite']:6.1f} {tns['category']:<12}")

    # Rank narratives by composite
    narratives.sort(key=lambda n: -n["tns"]["composite"])
    for rank, n in enumerate(narratives, 1):
        n["tns"]["rank"] = rank

    print()
    print(f"Composite stats: mean={statistics.mean(composites):.1f}, stdev={statistics.stdev(composites):.1f}, "
          f"min={min(composites):.1f}, max={max(composites):.1f}")

    cat_dist = {}
    for n in narratives:
        cat = n["tns"]["category"]
        cat_dist[cat] = cat_dist.get(cat, 0) + 1
    print(f"Categories: {cat_dist}")

    # Write updated narratives
    print()
    print("Writing scored narratives...")
    narr_data["narratives"] = narratives
    with open(NARRATIVES_FILE, "w") as f:
        json.dump(narr_data, f, indent=2, ensure_ascii=False)
    print(f"  Written: {NARRATIVES_FILE}")

    # Show final ranking
    print()
    print("=" * 70)
    print("FINAL NARRATIVE RANKING (by TNS Composite)")
    print("=" * 70)
    print()
    for n in narratives:
        tns = n["tns"]
        models_total = sum(len(n["outputs"].get(b, [])) for b in ["what_works", "whats_needed", "what_dies"])
        print(f"  #{tns['rank']:2d}  {tns['composite']:5.1f}  [{tns['category']:<12s}]  {n['name'][:50]:50s}  ({models_total} models)")


if __name__ == "__main__":
    main()
