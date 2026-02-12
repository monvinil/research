#!/usr/bin/env python3
"""
Master Synthesis: Merge all v3-3 rated model batches into unified ranked output.

Sources:
1. v3-3_rated_top40 — 40 deeply rated v2 top models
2. v3-3_rated_41to112 — 72 compact rated v2 models
3. v3-3_rated_expansion — 123 programmatically rated expansion models
4. v3-3_new_models — 45 new macro-derived models (defense, education, fear, energy, geo, emerging)
5. v3-3_rated_summary287 — 287 algorithmically estimated (distribution only, no individual models)
6. v3-2_rated_models — 15 hand-rated models from v3-2 cycle (different IDs, may overlap conceptually)

Output: data/verified/v3-3_unified_models_2026-02-11.json
"""

import json
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")

def load_json(path):
    with open(path) as f:
        return json.load(f)

# ============================================================
# LOAD ALL BATCHES
# ============================================================

# Batch 1: Top 40 (deep analysis)
top40 = load_json(BASE / "v3-3_rated_top40_2026-02-11.json")
top40_models = top40["rated_models"]

# Batch 2: Models 41-112 (compact)
mid = load_json(BASE / "v3-3_rated_41to112_2026-02-11.json")
mid_models = mid["rated_models"]

# Batch 3: Expansion (123 programmatic)
exp = load_json(BASE / "v3-3_rated_expansion_2026-02-11.json")
exp_models = exp["rated_models"]

# Batch 4: New macro models (45)
new = load_json(BASE / "v3-3_new_models_2026-02-11.json")
new_models = new["models"]

# Batch 5: Summary 287 (no individual models — distribution only)
summary287 = load_json(BASE / "v3-3_rated_summary287_2026-02-11.json")

# Batch 6: v3-2 rated models (15) — different format
v32 = load_json(BASE / "v3-2_rated_models_2026-02-11.json")
v32_raw = v32["rated_models"]

# ============================================================
# NORMALIZE FORMATS
# ============================================================

def normalize_top40(m):
    """Top 40 models have: id, name, scores.{SN,FA,GG,TG,CE}, composite, category"""
    return {
        "id": m["id"],
        "name": m["name"],
        "v2_score": m.get("v2_score"),
        "v2_rank": m.get("v2_rank"),
        "sector_naics": m.get("sector_naics", ""),
        "sector_name": m.get("sector_name", ""),
        "architecture": m.get("architecture", ""),
        "forces_v3": m.get("forces_v3", []),
        "scores": m["scores"],
        "composite": m["composite"],
        "category": m["category"],
        "one_liner": m.get("one_liner", ""),
        "key_v3_context": m.get("key_v3_context", ""),
        "source_batch": "top_40_deep"
    }

def normalize_mid(m):
    """41-112 models have same format as top 40"""
    return {
        "id": m["id"],
        "name": m["name"],
        "v2_score": m.get("v2_score"),
        "v2_rank": m.get("v2_rank"),
        "sector_naics": m.get("sector_naics", ""),
        "sector_name": m.get("sector_name", ""),
        "architecture": m.get("architecture", ""),
        "forces_v3": m.get("forces_v3", []),
        "scores": m["scores"],
        "composite": m["composite"],
        "category": m["category"],
        "one_liner": m.get("one_liner", ""),
        "key_v3_context": m.get("key_v3_context", ""),
        "source_batch": "mid_41to112"
    }

def normalize_expansion(m):
    """Expansion models from Python rating script"""
    return {
        "id": m["id"],
        "name": m["name"],
        "v2_score": m.get("v2_score"),
        "v2_rank": None,
        "sector_naics": m.get("sector_naics", ""),
        "sector_name": m.get("sector_name", ""),
        "architecture": m.get("architecture", ""),
        "forces_v3": m.get("forces_v3", []),
        "scores": m["scores"],
        "composite": m["composite"],
        "category": m["category"],
        "one_liner": m.get("one_liner", ""),
        "key_v3_context": m.get("key_v3_context", ""),
        "source_batch": "expansion_123"
    }

def normalize_new(m):
    """New macro-derived models"""
    return {
        "id": m["id"],
        "name": m["name"],
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": m.get("sector_naics", ""),
        "sector_name": m.get("sector_name", ""),
        "architecture": m.get("architecture", ""),
        "forces_v3": m.get("forces_v3", []),
        "scores": m["scores"],
        "composite": m["composite"],
        "category": m["category"],
        "one_liner": m.get("one_liner", ""),
        "key_v3_context": m.get("key_v3_context", ""),
        "source_batch": "new_macro_45",
        "macro_source": m.get("macro_source", "")
    }

def normalize_v32(m):
    """v3-2 models have different schema: card_id, model_name, nested scores"""
    scores = m["scores"]
    sn = scores["structural_necessity"]["score"]
    fa = scores["force_alignment"]["score"]
    gg = scores["geographic_grade"]["score"]
    tg = scores["timing_grade"]["score"]
    ce = scores["capital_efficiency"]["score"]
    return {
        "id": m["card_id"],
        "name": m["model_name"],
        "v2_score": None,
        "v2_rank": None,
        "sector_naics": m.get("sector_naics", ""),
        "sector_name": "",
        "architecture": "",
        "forces_v3": [],
        "scores": {"SN": sn, "FA": fa, "GG": gg, "TG": tg, "CE": ce},
        "composite": m["composite_score"],
        "category": m["category"],
        "one_liner": "",
        "key_v3_context": "",
        "source_batch": "v3-2_cycle"
    }

# ============================================================
# MERGE ALL INDIVIDUAL MODELS
# ============================================================

all_models = []
for m in top40_models:
    all_models.append(normalize_top40(m))
for m in mid_models:
    all_models.append(normalize_mid(m))
for m in exp_models:
    all_models.append(normalize_expansion(m))
for m in new_models:
    all_models.append(normalize_new(m))
for m in v32_raw:
    all_models.append(normalize_v32(m))

# Sort by composite descending
all_models.sort(key=lambda x: x["composite"], reverse=True)

# Add unified rank
for i, m in enumerate(all_models):
    m["rank"] = i + 1

# ============================================================
# COMPUTE STATISTICS
# ============================================================

composites = [m["composite"] for m in all_models]
categories = Counter(m["category"] for m in all_models)
architectures = Counter(m["architecture"] for m in all_models if m["architecture"])
source_batches = Counter(m["source_batch"] for m in all_models)

# By sector
sectors = Counter()
for m in all_models:
    naics = m["sector_naics"]
    if naics:
        prefix = naics[:2] if len(naics) >= 2 else naics
        sectors[prefix] += 1

# Force distribution
force_counts = Counter()
for m in all_models:
    for f in m["forces_v3"]:
        force_counts[f] += 1

# Score distribution
dist = {"above_80": 0, "70_to_80": 0, "60_to_70": 0, "50_to_60": 0, "below_50": 0}
for c in composites:
    if c >= 80: dist["above_80"] += 1
    elif c >= 70: dist["70_to_80"] += 1
    elif c >= 60: dist["60_to_70"] += 1
    elif c >= 50: dist["50_to_60"] += 1
    else: dist["below_50"] += 1

# ============================================================
# BUILD OUTPUT
# ============================================================

output = {
    "cycle": "v3-3",
    "date": "2026-02-11",
    "engine_version": "3.3",
    "description": "Unified model inventory: 522 v2 models migrated through 5-axis rating + 45 new macro-derived models + 15 v3-2 models. 287 of 522 v2 models are algorithmically estimated (distribution only). This file contains 295 individually rated models.",

    "rating_system": {
        "axes": {
            "SN": {"name": "Structural Necessity", "weight": 0.25, "description": "Must this business exist given structural forces?"},
            "FA": {"name": "Force Alignment", "weight": 0.25, "description": "How many F1-F6 forces drive it, weighted by velocity?"},
            "GG": {"name": "Geographic Grade", "weight": 0.20, "description": "Composite viability across 8 regions"},
            "TG": {"name": "Timing Grade", "weight": 0.15, "description": "Perez-aware entry window + crash resilience"},
            "CE": {"name": "Capital Efficiency", "weight": 0.15, "description": "Revenue-per-dollar, time-to-cashflow, crash survivability"}
        },
        "composite_formula": "(SN*25 + FA*25 + GG*20 + TG*15 + CE*15) / 10",
        "categories": {
            "STRUCTURAL_WINNER": "SN >= 8 AND FA >= 8 — must-exist business with multi-force convergence",
            "FORCE_RIDER": "FA >= 7 — rides 3+ converging macro forces",
            "GEOGRAPHIC_PLAY": "GG variance > 4 across regions",
            "TIMING_ARBITRAGE": "TG >= 8, narrow entry window",
            "CAPITAL_MOAT": "CE >= 8, cash-flow positive within 6 months",
            "FEAR_ECONOMY": "Arises from fear friction gap > 3",
            "EMERGING_CATEGORY": "Doesn't map to existing NAICS",
            "CONDITIONAL": "Composite >= 60 but key assumptions uncertain",
            "PARKED": "Composite < 60 or timing not yet right"
        }
    },

    "summary": {
        "total_individually_rated": len(all_models),
        "total_with_algorithmic_estimation": len(all_models) + 287,
        "algorithmic_models_note": "287 models (v2 ranks 101-387) rated by distribution only — see v3-3_rated_summary287 for architecture/force breakdown",
        "composite_stats": {
            "max": max(composites),
            "min": min(composites),
            "mean": round(sum(composites) / len(composites), 1),
            "median": round(sorted(composites)[len(composites) // 2], 1)
        },
        "composite_distribution": dist,
        "category_distribution": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "architecture_distribution": dict(sorted(architectures.items(), key=lambda x: -x[1])),
        "source_batch_counts": dict(source_batches),
        "force_alignment": dict(sorted(force_counts.items())),
        "sector_distribution": dict(sorted(sectors.items(), key=lambda x: -x[1]))
    },

    "algorithmic_estimation_287": {
        "description": summary287["methodology"],
        "estimated_distribution": summary287["estimated_distribution"],
        "composite_distribution": summary287["composite_distribution"],
        "upgrade_candidates": summary287["upgrade_candidates"]
    },

    "top_50": [
        {
            "rank": m["rank"],
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "category": m["category"],
            "scores": m["scores"],
            "architecture": m["architecture"],
            "source_batch": m["source_batch"]
        }
        for m in all_models[:50]
    ],

    "models": all_models
}

# Write output
outpath = BASE / "v3-3_unified_models_2026-02-11.json"
with open(outpath, "w") as f:
    json.dump(output, f, indent=2)

# ============================================================
# PRINT SUMMARY
# ============================================================

print(f"=== MASTER SYNTHESIS v3-3 ===")
print(f"Total individually rated models: {len(all_models)}")
print(f"Total with algorithmic estimation: {len(all_models) + 287}")
print(f"Composite range: {min(composites):.1f} - {max(composites):.1f}")
print(f"Mean: {sum(composites)/len(composites):.1f}")
print()
print("Category distribution:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat:25s}: {count:4d}")
print()
print("Source batches:")
for src, count in sorted(source_batches.items(), key=lambda x: -x[1]):
    print(f"  {src:25s}: {count:4d}")
print()
print("Score distribution:")
for bucket, count in dist.items():
    print(f"  {bucket:15s}: {count:4d}")
print()
print("Top 20 by composite:")
for m in all_models[:20]:
    print(f"  {m['rank']:3d}. {m['composite']:5.1f} | {m['category']:22s} | {m['id']:25s} | {m['name'][:60]}")
print()
print(f"Force alignment across all models:")
for f, count in sorted(force_counts.items()):
    print(f"  {f}: {count} models")
