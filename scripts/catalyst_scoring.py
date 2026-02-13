#!/usr/bin/env python3
"""
v3-16 Catalyst Scoring: Domain-specific trigger algorithms for speculative models.

The catalyst layer identifies PARKED/CONDITIONAL models with asymmetric upside —
models that would dramatically re-rank if specific binary triggers fire.

7 Catalyst Clusters, each with domain-specific mechanics:
  1. Quantum Computing — error correction threshold
  2. BCI/Neurotech — FDA consumer pathway or accuracy threshold
  3. Space/Orbital — launch cost threshold
  4. Agriculture x Macro — commodity crash or labor curtailment
  5. Healthcare x Discovery — clinical trial + FDA + CMS coverage chain
  6. Energy/Fusion — LCOE parity or storage cost threshold
  7. Professional Services Cascade — Big 4/AmLaw100 headcount signal

Qualifying criteria:
  - Primary category: PARKED or CONDITIONAL
  - TG ≤ 6 (not already in near-term timing window)
  - Matches a cluster via keyword/NAICS/architecture
  - Asymmetry ratio > 1.2 (conditional composite 20%+ above current)

Input:  data/verified/v3-12_normalized_2026-02-12.json
Output: data/verified/v3-12_normalized_2026-02-12.json (catalyst_scenario added)
"""

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"


def clamp(v, lo=1.0, hi=10.0):
    return round(max(lo, min(hi, v)), 1)


# ──────────────────────────────────────────────────────────────────────
# Cluster Definitions
# ──────────────────────────────────────────────────────────────────────

CLUSTERS = {
    "quantum_computing": {
        "name": "Quantum Computing Breakthrough",
        "description": "Quantum error correction crosses commercial threshold, enabling drug discovery simulation, cryptographic breaks, and optimization at scale.",
        "triggers": [
            {
                "event": "Logical qubit error rate below 10^-12 per gate demonstrated",
                "probability_2yr": 0.08,
                "probability_5yr": 0.25,
                "monitoring": ["WebSearch: IBM/Google/Quantinuum error correction milestones", "EDGAR: quantum computing company 10-K filings"],
            },
            {
                "event": "NIST post-quantum standards enforcement deadline triggers enterprise migration",
                "probability_2yr": 0.40,
                "probability_5yr": 0.85,
                "monitoring": ["WebSearch: NIST PQC migration deadlines", "FRED: federal IT spending"],
            },
        ],
        "conditional_boosts": {"SN": +3.0, "FA": +2.0, "TG": +4.5, "CE": +1.0},
        "propagation_chain": ["Error correction threshold", "Commercial algorithm viability", "Enterprise migration urgency", "Platform ecosystem explosion"],
        "timeline": "3-7 years",
        "match_keywords": ["quantum", "post-quantum", "cryptograph"],
        "match_naics": [],
        "match_ids": ["MC-V314-QC"],
    },
    "bci_neurotech": {
        "name": "BCI / Neurotech Breakthrough",
        "description": "Brain-computer interfaces achieve FDA consumer pathway approval or non-invasive accuracy exceeds 90%, opening mass-market neural interfaces.",
        "triggers": [
            {
                "event": "FDA approves consumer-grade BCI device via 510(k) or De Novo pathway",
                "probability_2yr": 0.05,
                "probability_5yr": 0.20,
                "monitoring": ["EDGAR: FDA 510(k) filings for neural devices", "WebSearch: Neuralink/Synchron FDA approvals"],
            },
            {
                "event": "Non-invasive EEG classification accuracy exceeds 90% in peer-reviewed study",
                "probability_2yr": 0.15,
                "probability_5yr": 0.35,
                "monitoring": ["WebSearch: EEG BCI accuracy benchmarks", "WebSearch: Kernel Flow clinical results"],
            },
        ],
        "conditional_boosts": {"SN": +3.5, "FA": +3.0, "TG": +5.0, "EC": +1.5},
        "propagation_chain": ["FDA approval / accuracy threshold", "Device commercial availability", "Developer ecosystem forms", "Consumer applications emerge"],
        "timeline": "3-8 years",
        "match_keywords": ["bci", "brain-computer", "neural interface", "neurotech", "neurotechnology", "eeg", "brain"],
        "match_naics": [],
        "match_ids": ["V3-BCI"],
    },
    "space_orbital": {
        "name": "Space / Orbital Manufacturing",
        "description": "Launch costs drop below $100/kg and orbital manufacturing yields are proven, enabling in-space production of pharmaceuticals, semiconductors, and advanced materials.",
        "triggers": [
            {
                "event": "Fully reusable launch vehicle achieves <$100/kg to LEO",
                "probability_2yr": 0.15,
                "probability_5yr": 0.45,
                "monitoring": ["WebSearch: Starship cost per kg", "WebSearch: SpaceX reusability milestones"],
            },
            {
                "event": "Orbital manufacturing demonstrates >10x quality improvement for target product",
                "probability_2yr": 0.05,
                "probability_5yr": 0.20,
                "monitoring": ["WebSearch: Varda Space microgravity manufacturing", "EDGAR: space manufacturing startups"],
            },
        ],
        "conditional_boosts": {"SN": +3.0, "FA": +2.5, "TG": +5.0, "CE": +2.0},
        "propagation_chain": ["Launch cost threshold", "Orbital manufacturing proven", "Supply chain forms", "Platform economics viable"],
        "timeline": "5-10 years",
        "match_keywords": ["orbital", "in-space", "space manufacturing", "microgravity"],
        "match_naics": [],
        "match_ids": ["MC-V314-SP"],
    },
    "agriculture_macro": {
        "name": "Agriculture x Macro Shock",
        "description": "Commodity price crash or H-2A visa curtailment creates acute margin compression, forcing rapid adoption of precision agriculture and automation technologies.",
        "triggers": [
            {
                "event": "Corn/soy prices below breakeven for 2+ consecutive quarters",
                "probability_2yr": 0.25,
                "probability_5yr": 0.55,
                "monitoring": ["FRED: PMAIZMT (corn)", "FRED: PSOYB (soybeans)", "FRED: PWHEAMT (wheat)"],
            },
            {
                "event": "H-2A visa program curtailment or >25% fee increase",
                "probability_2yr": 0.20,
                "probability_5yr": 0.40,
                "monitoring": ["WebSearch: H-2A visa policy changes", "BLS: agricultural employment trends"],
            },
            {
                "event": "Major crop insurance payout event exceeds $20B in single year",
                "probability_2yr": 0.15,
                "probability_5yr": 0.40,
                "monitoring": ["WebSearch: USDA crop insurance payouts", "FRED: agricultural price indices"],
            },
        ],
        "conditional_boosts": {"SN": +2.0, "FA": +2.0, "TG": +3.0, "EC": +1.0},
        "propagation_chain": ["Commodity shock / labor crisis", "Farm margin compression", "Automation ROI threshold crossed", "Rapid technology adoption"],
        "timeline": "1-4 years",
        "match_keywords": ["farm", "crop", "agri", "precision ag", "harvest", "irrigation", "dairy", "livestock", "agronomic"],
        "match_naics": ["11", "111", "112", "113", "114", "115"],
        "match_ids": [],
    },
    "healthcare_discovery": {
        "name": "Healthcare x Discovery Cascade",
        "description": "Breakthrough clinical trial results + FDA approval + CMS coverage decision creates sudden demand for new care delivery models, diagnostics, and treatment platforms.",
        "triggers": [
            {
                "event": "GLP-1 or similar drug class shows >30% efficacy improvement in Phase 3",
                "probability_2yr": 0.30,
                "probability_5yr": 0.65,
                "monitoring": ["WebSearch: ClinicalTrials.gov Phase 3 results", "EDGAR: pharma 10-K pipeline disclosures"],
            },
            {
                "event": "CMS issues National Coverage Determination for AI-assisted diagnosis",
                "probability_2yr": 0.20,
                "probability_5yr": 0.50,
                "monitoring": ["WebSearch: CMS NCD announcements", "WebSearch: FDA AI/ML device approvals"],
            },
            {
                "event": "Hospital-at-home CMS waiver made permanent (post-pandemic)",
                "probability_2yr": 0.35,
                "probability_5yr": 0.70,
                "monitoring": ["WebSearch: CMS Acute Hospital Care at Home waiver", "FRED: healthcare spending"],
            },
        ],
        "conditional_boosts": {"SN": +2.0, "FA": +1.5, "TG": +2.5, "EC": +1.0},
        "propagation_chain": ["Clinical trial success", "FDA approval (12-24mo)", "CMS coverage decision (6-12mo)", "Care delivery model demand surge"],
        "timeline": "2-5 years",
        "match_keywords": ["clinical", "patient", "hospital", "nursing", "elder care", "assisted living", "home health",
                           "diagnosis", "therapeut", "pharma", "glp-1", "mental health", "telehealth", "remote patient"],
        "match_naics": ["62", "621", "622", "623", "624"],
        "match_ids": [],
    },
    "energy_fusion": {
        "name": "Energy / Fusion Breakthrough",
        "description": "Fusion achieves LCOE <$60/MWh or grid-scale battery storage drops below $50/kWh, fundamentally restructuring energy markets and unlocking new industrial applications.",
        "triggers": [
            {
                "event": "Commercial fusion prototype demonstrates net energy gain >10x (Q>10)",
                "probability_2yr": 0.05,
                "probability_5yr": 0.15,
                "monitoring": ["WebSearch: SPARC/CFS fusion milestones", "WebSearch: TAE Technologies results"],
            },
            {
                "event": "Grid-scale battery storage LCOS drops below $50/kWh",
                "probability_2yr": 0.20,
                "probability_5yr": 0.55,
                "monitoring": ["WebSearch: BNEF battery price survey", "FRED: electricity prices"],
            },
            {
                "event": "SMR (small modular reactor) receives NRC design certification",
                "probability_2yr": 0.30,
                "probability_5yr": 0.70,
                "monitoring": ["WebSearch: NRC SMR certification", "WebSearch: NuScale/X-energy regulatory status"],
            },
        ],
        "conditional_boosts": {"SN": +2.5, "FA": +2.0, "TG": +3.5, "CE": +2.0},
        "propagation_chain": ["Net energy / cost parity achieved", "LCOE competitive with gas", "Commercial deployment begins", "Grid restructuring accelerates"],
        "timeline": "3-8 years",
        "match_keywords": ["fusion", "nuclear", "smr", "reactor", "battery storage", "grid-scale",
                           "energy storage", "power plant", "electricity"],
        "match_naics": ["22", "221", "2211"],
        "match_ids": ["MC-UTL"],
    },
    "prof_services_cascade": {
        "name": "Professional Services Cascade",
        "description": "Big 4 or AmLaw100 firms announce >20% headcount reductions, signaling that AI has crossed the professional services automation threshold and triggering cascade across legal, accounting, consulting.",
        "triggers": [
            {
                "event": "Big 4 accounting firm announces >20% professional staff reduction",
                "probability_2yr": 0.15,
                "probability_5yr": 0.45,
                "monitoring": ["EDGAR: Big 4 10-K headcount disclosures", "WebSearch: Deloitte/PwC/EY/KPMG layoffs"],
            },
            {
                "event": "AmLaw100 firm demonstrates >40% revenue-per-lawyer increase via AI",
                "probability_2yr": 0.10,
                "probability_5yr": 0.35,
                "monitoring": ["WebSearch: AmLaw100 AI adoption", "WebSearch: legal AI productivity benchmarks"],
            },
            {
                "event": "Major consulting firm (McKinsey/BCG/Bain) restructures to AI-native delivery model",
                "probability_2yr": 0.20,
                "probability_5yr": 0.50,
                "monitoring": ["WebSearch: McKinsey BCG Bain AI transformation", "BLS: management consulting employment"],
            },
        ],
        "conditional_boosts": {"SN": +2.0, "FA": +2.5, "TG": +3.0, "EC": +1.5},
        "propagation_chain": ["Big firm headcount signal", "Industry-wide adoption cascade", "Revenue-per-employee restructuring", "CRE / education second-order effects"],
        "timeline": "2-5 years",
        "match_keywords": ["accounting", "legal", "consulting", "law firm", "cpa", "audit",
                           "tax", "bookkeep", "paralegal", "attorney", "management consulting"],
        "match_naics": ["54", "5411", "5412", "5413", "5416"],
        "match_ids": [],
    },
}


# ──────────────────────────────────────────────────────────────────────
# Cluster Matching
# ──────────────────────────────────────────────────────────────────────

def match_cluster(model):
    """Match a model to the best-fitting catalyst cluster. Returns cluster_id or None."""
    mid = model.get("id", "")
    name = (model.get("name", "") or "").lower()
    one_liner = (model.get("one_liner", "") or "").lower()
    naics = model.get("sector_naics", "") or ""
    text = name + " " + one_liner

    best_cluster = None
    best_score = 0

    for cid, cluster in CLUSTERS.items():
        score = 0

        # ID prefix match (strongest signal)
        for prefix in cluster["match_ids"]:
            if mid.startswith(prefix):
                score += 10

        # Keyword match
        for kw in cluster["match_keywords"]:
            if kw.lower() in text:
                score += 3

        # NAICS match
        for naics_prefix in cluster["match_naics"]:
            if naics.startswith(naics_prefix):
                score += 2

        if score > best_score:
            best_score = score
            best_cluster = cid

    return best_cluster if best_score >= 2 else None


# ──────────────────────────────────────────────────────────────────────
# Conditional Scoring
# ──────────────────────────────────────────────────────────────────────

def compute_conditional_scores(current_scores, boosts):
    """Apply conditional score boosts and return new scores + composite."""
    cond = {}
    for axis in ["SN", "FA", "EC", "TG", "CE"]:
        base = current_scores.get(axis, 5.0)
        boost = boosts.get(axis, 0.0)
        cond[axis] = clamp(base + boost)

    composite = round(
        (cond["SN"] * 25 + cond["FA"] * 25 + cond["EC"] * 20 +
         cond["TG"] * 15 + cond["CE"] * 15) / 10, 2
    )
    return cond, composite


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    apply_mode = "--apply" in sys.argv

    print("=" * 70)
    print("v3-16 CATALYST SCORING: Domain-Specific Trigger Algorithms")
    print("=" * 70)
    print(f"Mode: {'APPLY (writing changes)' if apply_mode else 'ANALYZE (read-only)'}")
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"Loaded {len(models)} models")

    # Phase 1: Identify candidates
    candidates = []
    cluster_counts = Counter()
    rejected = {"not_parked_conditional": 0, "tg_too_high": 0, "no_cluster": 0, "low_asymmetry": 0}

    for m in models:
        # Must be PARKED, CONDITIONAL, or FEAR_ECONOMY (primary category only)
        primary_cat = m.get("primary_category", "")
        qualifying_cats = {"PARKED", "CONDITIONAL", "FEAR_ECONOMY"}
        if primary_cat not in qualifying_cats:
            rejected["not_parked_conditional"] += 1
            continue

        # TG must be ≤ 6
        tg = m.get("scores", {}).get("TG", 5)
        if tg > 6:
            rejected["tg_too_high"] += 1
            continue

        # Must match a cluster
        cluster_id = match_cluster(m)
        if not cluster_id:
            rejected["no_cluster"] += 1
            continue

        # Compute conditional scores
        cluster = CLUSTERS[cluster_id]
        current_scores = m.get("scores", {})
        current_composite = m.get("composite", 50)
        cond_scores, cond_composite = compute_conditional_scores(current_scores, cluster["conditional_boosts"])

        # Asymmetry ratio must be > 1.2
        asymmetry = round(cond_composite / current_composite, 3) if current_composite > 0 else 0
        if asymmetry < 1.2:
            rejected["low_asymmetry"] += 1
            continue

        candidates.append({
            "model": m,
            "cluster_id": cluster_id,
            "cluster": cluster,
            "current_composite": current_composite,
            "conditional_scores": cond_scores,
            "conditional_composite": cond_composite,
            "asymmetry_ratio": asymmetry,
        })
        cluster_counts[cluster_id] += 1

    print(f"\nCandidates found: {len(candidates)}")
    print(f"Rejected: {rejected}")
    print(f"\nCluster distribution:")
    for cid, count in sorted(cluster_counts.items(), key=lambda x: -x[1]):
        print(f"  {CLUSTERS[cid]['name']:<40s}: {count}")

    # Phase 2: Build catalyst scenarios
    print(f"\n{'='*70}")
    print("CATALYST SCENARIOS")
    print(f"{'='*70}")

    scenarios_by_cluster = {}
    for cand in sorted(candidates, key=lambda c: -c["asymmetry_ratio"]):
        m = cand["model"]
        cluster_id = cand["cluster_id"]
        cluster = cand["cluster"]

        scenario = {
            "cluster": cluster_id,
            "cluster_name": cluster["name"],
            "triggers": cluster["triggers"],
            "conditional_scores": cand["conditional_scores"],
            "current_composite": cand["current_composite"],
            "conditional_composite": cand["conditional_composite"],
            "asymmetry_ratio": cand["asymmetry_ratio"],
            "propagation_chain": cluster["propagation_chain"],
            "timeline": cluster["timeline"],
        }

        if cluster_id not in scenarios_by_cluster:
            scenarios_by_cluster[cluster_id] = []
        scenarios_by_cluster[cluster_id].append({
            "id": m["id"],
            "name": m["name"],
            "current": cand["current_composite"],
            "conditional": cand["conditional_composite"],
            "ratio": cand["asymmetry_ratio"],
            "primary_category": m.get("primary_category"),
        })

        if apply_mode:
            m["catalyst_scenario"] = scenario

    # Print detailed results
    for cluster_id in sorted(scenarios_by_cluster.keys()):
        cluster = CLUSTERS[cluster_id]
        models_in = scenarios_by_cluster[cluster_id]
        print(f"\n  {cluster['name']} ({len(models_in)} models)")
        print(f"  {'─'*60}")
        print(f"  Triggers:")
        for t in cluster["triggers"]:
            print(f"    • {t['event']}")
            print(f"      P(2yr)={t['probability_2yr']:.0%}, P(5yr)={t['probability_5yr']:.0%}")
        print(f"  Propagation: {' → '.join(cluster['propagation_chain'])}")
        print(f"  Timeline: {cluster['timeline']}")
        print(f"  Conditional boosts: {cluster['conditional_boosts']}")
        print()
        print(f"  {'ID':<20s}  {'Current':>7s}  {'Cond':>7s}  {'Ratio':>6s}  {'Cat':<15s}  Name")
        for mi in sorted(models_in, key=lambda x: -x["ratio"]):
            print(f"  {mi['id']:<20s}  {mi['current']:7.1f}  {mi['conditional']:7.1f}  "
                  f"{mi['ratio']:5.2f}x  {mi['primary_category']:<15s}  {mi['name'][:40]}")

    # Summary statistics
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    all_ratios = [c["asymmetry_ratio"] for c in candidates]
    print(f"  Total catalyst models: {len(candidates)}")
    print(f"  Asymmetry ratio: min={min(all_ratios):.2f}x, max={max(all_ratios):.2f}x, "
          f"mean={statistics.mean(all_ratios):.2f}x")
    print(f"  Cluster count: {len(scenarios_by_cluster)}")

    # Would-be category changes
    upgrades = Counter()
    for cand in candidates:
        m = cand["model"]
        old_cat = m.get("primary_category", "PARKED")
        cond_comp = cand["conditional_composite"]
        if cond_comp >= 75:
            new_cat = "STRUCTURAL_WINNER"
        elif cond_comp >= 65:
            new_cat = "FORCE_RIDER"
        elif cond_comp >= 55:
            new_cat = "CONDITIONAL"
        else:
            new_cat = "PARKED"
        if new_cat != old_cat:
            upgrades[f"{old_cat} → {new_cat}"] += 1
    print(f"\n  Conditional category shifts:")
    for shift, count in sorted(upgrades.items(), key=lambda x: -x[1]):
        print(f"    {shift}: {count}")

    if apply_mode:
        print(f"\n{'='*70}")
        print("APPLYING CATALYST SCENARIOS")
        print(f"{'='*70}")

        # Write normalized file
        with open(NORMALIZED_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Written: {NORMALIZED_FILE}")
        print(f"  {len(candidates)} models now have catalyst_scenario metadata")
    else:
        print(f"\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
