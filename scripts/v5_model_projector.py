#!/usr/bin/env python3
"""
v5.2 Model Projection Engine: Predict new business models from existing patterns.

Reads:
  - data/v4/models.json (695 models with T/CLA/VCR scores)
  - data/v4/narratives.json (16 narratives with model links)
  - data/v4/collisions.json (66 force collisions)
  - data/v5/tensions.json (26 active tensions)
  - data/v5/state.json (engine version)

Writes:
  - data/v5/projections.json (projected model candidates)

5 projection methods:
  AT - Architecture Transfer: proven architectures applied to new transforming sectors
  FR - FUND_RETURNER Template: high-ROI patterns projected to uncovered sectors
  NC - Narrative Coverage Gap: under-represented architectures in DEFINING narratives
  FC - Force Convergence Hotspot: multi-force sectors with low model density
  TD - Tension-Derived: converts system gaps (T>>O, architecture spread) to predictions
"""

import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"

# Import scoring engines
sys.path.insert(0, str(Path(__file__).parent))
from cla_scoring import score_model as cla_score_model
from vcr_scoring import score_model as vcr_score_model, SECTOR_FRAGMENTATION


# ──────────────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_all_data():
    """Load all source data for projection."""
    models = load_json(V4_DIR / "models.json")["models"]
    narratives = load_json(V4_DIR / "narratives.json")["narratives"]
    collisions = load_json(V4_DIR / "collisions.json")["collisions"]

    tensions = []
    if (V5_DIR / "tensions.json").exists():
        tensions = load_json(V5_DIR / "tensions.json").get("tensions", [])

    state = {}
    if (V5_DIR / "state.json").exists():
        state = load_json(V5_DIR / "state.json")

    return models, narratives, collisions, tensions, state


# ──────────────────────────────────────────────────────────────────────
# Force Normalization
# ──────────────────────────────────────────────────────────────────────

FORCE_CANONICAL = {
    "F1": "F1_technology", "F1_technology": "F1_technology",
    "F2": "F2_demographics", "F2_demographics": "F2_demographics",
    "F3": "F3_geopolitics", "F3_geopolitics": "F3_geopolitics",
    "F4": "F4_capital", "F4_capital": "F4_capital",
    "F5": "F5_psychology", "F5_psychology": "F5_psychology",
    "F6": "F6_energy", "F6_energy": "F6_energy",
}


def normalize_forces(forces):
    """Normalize force IDs to canonical long form, deduplicated."""
    seen = set()
    result = []
    for f in forces:
        canon = FORCE_CANONICAL.get(f, f)
        if canon not in seen:
            seen.add(canon)
            result.append(canon)
    return result


# ──────────────────────────────────────────────────────────────────────
# Matrix Builders
# ──────────────────────────────────────────────────────────────────────

def naics2(model):
    """Extract 2-digit NAICS from model."""
    n = str(model.get("sector_naics", ""))
    # Handle ranges like "31-33"
    if "-" in n:
        return n.split("-")[0]
    return n[:2] if len(n) >= 2 else n


def build_arch_sector_matrix(models):
    """Build architecture × NAICS-2 matrix with score aggregates."""
    matrix = defaultdict(lambda: defaultdict(lambda: {
        "count": 0, "t_scores": [], "o_scores": [], "vcr_scores": [],
        "models": [], "forces": Counter(),
    }))

    for m in models:
        arch = m.get("architecture", "")
        n2 = naics2(m)
        if not arch or not n2:
            continue

        cell = matrix[arch][n2]
        cell["count"] += 1
        cell["t_scores"].append(m.get("composite", 0))
        cell["o_scores"].append(m.get("cla", {}).get("composite", 0))
        cell["vcr_scores"].append(m.get("vcr", {}).get("composite", 0))
        cell["models"].append(m["id"])
        for f in normalize_forces(m.get("forces_v3", [])):
            cell["forces"][f] += 1

    return matrix


def build_sector_stats(models):
    """Compute per-sector average scores and common forces."""
    sectors = defaultdict(lambda: {
        "t_scores": [], "o_scores": [], "vcr_scores": [],
        "sn": [], "fa": [], "ec": [], "tg": [], "ce": [],
        "forces": Counter(), "count": 0, "names": set(),
    })

    for m in models:
        n2 = naics2(m)
        if not n2:
            continue
        s = sectors[n2]
        s["count"] += 1
        s["t_scores"].append(m.get("composite", 0))
        s["o_scores"].append(m.get("cla", {}).get("composite", 0))
        s["vcr_scores"].append(m.get("vcr", {}).get("composite", 0))
        scores = m.get("scores", {})
        for k in ("sn", "fa", "ec", "tg", "ce"):
            s[k].append(scores.get(k.upper(), scores.get(k, 6.0)))
        for f in normalize_forces(m.get("forces_v3", [])):
            s["forces"][f] += 1
        s["names"].add(m.get("sector_name", ""))

    return sectors


def build_arch_stats(models):
    """Compute per-architecture average scores."""
    archs = defaultdict(lambda: {
        "t_scores": [], "o_scores": [], "vcr_scores": [],
        "ec": [], "tg": [], "ce": [],
        "forces": Counter(), "count": 0,
        "fr_count": 0,
    })

    for m in models:
        arch = m.get("architecture", "")
        if not arch:
            continue
        a = archs[arch]
        a["count"] += 1
        a["t_scores"].append(m.get("composite", 0))
        a["o_scores"].append(m.get("cla", {}).get("composite", 0))
        a["vcr_scores"].append(m.get("vcr", {}).get("composite", 0))
        scores = m.get("scores", {})
        for k in ("ec", "tg", "ce"):
            a[k].append(scores.get(k.upper(), scores.get(k, 6.0)))
        for f in normalize_forces(m.get("forces_v3", [])):
            a["forces"][f] += 1
        if m.get("vcr", {}).get("category") == "FUND_RETURNER":
            a["fr_count"] += 1

    return archs


def build_naics_name_map(models):
    """Build NAICS code → sector name map from existing models."""
    name_map = {}
    for m in models:
        n = str(m.get("sector_naics", ""))
        sn = m.get("sector_name", "")
        if n and sn:
            name_map[n] = sn
            if len(n) >= 2:
                n2 = n[:2] if "-" not in n else n.split("-")[0]
                if n2 not in name_map:
                    name_map[n2] = sn
    return name_map


# ──────────────────────────────────────────────────────────────────────
# T-Score Projection
# ──────────────────────────────────────────────────────────────────────

def project_t_scores(arch_stats, sector_stats, arch, n2, forces):
    """Project T-scores for a new model using cross-sector patterns."""
    a = arch_stats.get(arch, {})
    s = sector_stats.get(n2, {})

    # SN, FA: from target sector (structural necessity is sector-specific)
    sn = statistics.mean(s["sn"]) if s.get("sn") else 6.5
    fa = statistics.mean(s["fa"]) if s.get("fa") else 6.5

    # EC: 50/50 blend of source arch + target sector
    arch_ec = statistics.mean(a["ec"]) if a.get("ec") else 6.0
    sect_ec = statistics.mean(s["ec"]) if s.get("ec") else 6.0
    ec = (arch_ec + sect_ec) / 2

    # TG: 60% target sector + 40% source architecture
    arch_tg = statistics.mean(a["tg"]) if a.get("tg") else 6.0
    sect_tg = statistics.mean(s["tg"]) if s.get("tg") else 6.0
    tg = sect_tg * 0.6 + arch_tg * 0.4

    # CE: from source architecture (capital efficiency is architecture-intrinsic)
    ce = statistics.mean(a["ce"]) if a.get("ce") else 6.0

    # Force alignment boost: more accelerating forces = higher FA
    if len(forces) >= 4:
        fa = min(10.0, fa + 0.5)
    elif len(forces) >= 3:
        fa = min(10.0, fa + 0.3)

    return {
        "SN": round(sn, 1),
        "FA": round(fa, 1),
        "EC": round(ec, 1),
        "TG": round(tg, 1),
        "CE": round(ce, 1),
    }


def calc_t_composite(scores):
    return round((scores["SN"] * 25 + scores["FA"] * 25 + scores["EC"] * 20 +
                  scores["TG"] * 15 + scores["CE"] * 15) / 10, 2)


# ──────────────────────────────────────────────────────────────────────
# One-liner Templates
# ──────────────────────────────────────────────────────────────────────

ARCH_ONELINER = {
    "vertical_saas": "AI-native vertical SaaS for {sector} — automating core operations with sector-specific data models",
    "data_compounding": "Data intelligence platform for {sector} — aggregating operational data for predictive analytics and decision automation",
    "full_service_replacement": "AI-powered full-service replacement for traditional {sector} operations — automation-first service delivery",
    "platform_infrastructure": "Infrastructure platform for AI-native {sector} — middleware connecting legacy systems to modern workflows",
    "acquire_and_modernize": "Acquire aging {sector} businesses at succession-driven valuations, deploy AI/automation to 3x margins",
    "rollup_consolidation": "Technology-enabled rollup of fragmented {sector} operators with centralized AI back-office",
    "marketplace_network": "AI-matched marketplace connecting {sector} buyers and sellers with intelligent pricing and fulfillment",
    "regulatory_moat_builder": "Compliance automation platform for {sector} — replacing manual regulatory processes with continuous monitoring",
    "service_platform": "AI-augmented service platform for {sector} — blending human expertise with automated workflows",
    "open_core_ecosystem": "Open-core platform for {sector} — free foundational tools with enterprise AI features as paid tier",
    "fear_economy_capture": "Trust and safety platform for {sector} — monetizing the gap between AI capability and institutional readiness",
    "arbitrage_window": "Timing arbitrage play in {sector} — capturing the window between technology readiness and market adoption",
    "outcome_based": "Outcome-based pricing model for {sector} — aligned incentives where payment tracks measurable results",
    "coordination_protocol": "Industry coordination protocol for {sector} — standard-setting platform that becomes infrastructure",
}
DEFAULT_ONELINER = "AI-native {arch} model for {sector} transformation"


def generate_one_liner(arch, sector_name):
    template = ARCH_ONELINER.get(arch, DEFAULT_ONELINER)
    return template.format(sector=sector_name, arch=arch.replace("_", " "))


# ──────────────────────────────────────────────────────────────────────
# Model Builder
# ──────────────────────────────────────────────────────────────────────

_seq = Counter()


def build_projected_model(method, arch, n2, forces, sector_name,
                          arch_stats, sector_stats, evidence_chain,
                          source_model_ids=None, **kwargs):
    """Build a fully-scored projected model candidate."""
    _seq[method + n2] += 1
    model_id = "PROJ-{}-{}-{:03d}".format(method, n2, _seq[method + n2])

    # T-scores
    t_scores = project_t_scores(arch_stats, sector_stats, arch, n2, forces)
    t_comp = calc_t_composite(t_scores)

    # Primary category assignment
    if t_comp >= 75:
        primary_cat = "STRUCTURAL_WINNER"
    elif t_comp >= 65:
        primary_cat = "FORCE_RIDER"
    else:
        primary_cat = "CONDITIONAL"

    # Build model dict for scoring engines
    model = {
        "id": model_id,
        "name": kwargs.get("name", "Projected {} {} Model".format(
            arch.replace("_", " ").title(), sector_name)),
        "one_liner": generate_one_liner(arch, sector_name),
        "sector_naics": n2,
        "sector_name": sector_name,
        "architecture": arch,
        "forces_v3": forces,
        "scores": t_scores,
        "composite": t_comp,
        "primary_category": primary_cat,
        "category": [primary_cat],
        "source_batch": "v5_projection",
        "status": "PROJECTED",
    }

    # Score CLA using existing heuristic engine
    model["cla"] = cla_score_model(model)

    # Score VCR using existing heuristic engine
    model["vcr"] = vcr_score_model(model)

    # Projection metadata
    model["projection"] = {
        "method": method,
        "evidence_chain": evidence_chain,
        "confidence": kwargs.get("confidence", "MEDIUM"),
        "source_models": (source_model_ids or [])[:15],
        "dedup_check": "UNIQUE",
    }

    # Triple score
    o_comp = model["cla"]["composite"]
    v_comp = model["vcr"]["composite"]
    if t_comp > 0 and o_comp > 0 and v_comp > 0:
        model["triple_score"] = round((t_comp * o_comp * v_comp) ** (1 / 3), 2)
    else:
        model["triple_score"] = 0

    return model


# ──────────────────────────────────────────────────────────────────────
# Method 1: Architecture Transfer (AT)
# ──────────────────────────────────────────────────────────────────────

def method_architecture_transfer(models, arch_matrix, arch_stats, sector_stats, name_map):
    """Project proven architectures into sectors where they don't yet exist."""
    print("\n  Method AT: Architecture Transfer")
    candidates = []

    # Only consider architectures with enough evidence
    viable_archs = {a for a, data in arch_stats.items() if data["count"] >= 5}

    for arch in sorted(viable_archs):
        # Find sectors where this architecture performs well (avg O >= 60)
        good_sectors = {}
        for n2, cell in arch_matrix[arch].items():
            if cell["count"] >= 3 and statistics.mean(cell["o_scores"]) >= 60:
                good_sectors[n2] = cell

        if not good_sectors:
            continue

        avg_source_o = statistics.mean(
            statistics.mean(c["o_scores"]) for c in good_sectors.values()
        )

        # Find sectors where this architecture is ABSENT
        all_n2 = set(sector_stats.keys())
        present_n2 = set(arch_matrix[arch].keys())
        absent_n2 = all_n2 - present_n2

        for n2 in sorted(absent_n2):
            s = sector_stats[n2]
            avg_t = statistics.mean(s["t_scores"]) if s["t_scores"] else 0
            if avg_t < 60:
                continue  # Not transforming enough

            # Common forces in this sector
            top_forces = [f for f, _ in s["forces"].most_common(3)]

            sector_name = name_map.get(n2, "NAICS " + n2)

            evidence = [
                "Architecture '{}' scores avg O={:.1f} across {} models in {} sectors".format(
                    arch, avg_source_o, sum(c["count"] for c in good_sectors.values()),
                    len(good_sectors)),
                "Sector NAICS {} ({}) has avg T={:.1f} across {} models but zero '{}' models".format(
                    n2, sector_name, avg_t, s["count"], arch),
            ]

            source_ids = []
            for c in good_sectors.values():
                source_ids.extend(c["models"][:3])

            candidate = build_projected_model(
                method="AT", arch=arch, n2=n2, forces=top_forces,
                sector_name=sector_name, arch_stats=arch_stats,
                sector_stats=sector_stats, evidence_chain=evidence,
                source_model_ids=source_ids,
                confidence="HIGH" if len(good_sectors) >= 3 else "MEDIUM",
            )
            candidates.append(candidate)

    print("    {} candidates generated".format(len(candidates)))
    return candidates


# ──────────────────────────────────────────────────────────────────────
# Method 2: FUND_RETURNER Template (FR)
# ──────────────────────────────────────────────────────────────────────

FR_ARCHS = ["vertical_saas", "data_compounding"]
FR_FORCES = ["F1_technology", "F4_capital"]


def method_fund_returner_template(models, arch_matrix, arch_stats, sector_stats, name_map):
    """Project FUND_RETURNER pattern to sectors where it's absent."""
    print("\n  Method FR: FUND_RETURNER Template")
    candidates = []

    # Find existing FR models per (arch, naics2) cell
    fr_cells = set()
    for m in models:
        if m.get("vcr", {}).get("category") == "FUND_RETURNER":
            fr_cells.add((m.get("architecture", ""), naics2(m)))

    for arch in FR_ARCHS:
        for n2, s in sorted(sector_stats.items()):
            if (arch, n2) in fr_cells:
                continue  # FR already exists here

            avg_t = statistics.mean(s["t_scores"]) if s["t_scores"] else 0
            if avg_t < 60:
                continue

            frag = SECTOR_FRAGMENTATION.get(n2, 5)
            if frag < 6:
                continue  # Need reasonable fragmentation

            # FR likelihood scoring
            likelihood = 0
            likelihood += 3.0 if frag >= 8 else (2.0 if frag >= 6 else 0)
            likelihood += 2.0 if avg_t >= 70 else (1.0 if avg_t >= 65 else 0)

            # Check if architecture already exists in sector (just not as FR)
            existing_count = arch_matrix[arch][n2]["count"] if n2 in arch_matrix[arch] else 0
            if existing_count > 0:
                likelihood += 1.0  # Architecture proven here, just not yet FR

            if likelihood < 4.0:
                continue

            # Augment forces with sector's top forces
            sector_forces = [f for f, _ in s["forces"].most_common(3)]
            forces = list(set(FR_FORCES + sector_forces))

            sector_name = name_map.get(n2, "NAICS " + n2)

            evidence = [
                "FUND_RETURNER template: {} + {} in fragmented sector (frag={})".format(
                    arch, "+".join(FR_FORCES), frag),
                "Sector {} ({}) has avg T={:.1f}, {} existing models, zero {} FUND_RETURNERs".format(
                    n2, sector_name, avg_t, s["count"], arch),
                "FR likelihood score: {:.1f} (threshold: 4.0)".format(likelihood),
            ]

            candidate = build_projected_model(
                method="FR", arch=arch, n2=n2, forces=forces,
                sector_name=sector_name, arch_stats=arch_stats,
                sector_stats=sector_stats, evidence_chain=evidence,
                confidence="HIGH" if likelihood >= 6 else "MEDIUM",
            )
            candidates.append(candidate)

    print("    {} candidates generated".format(len(candidates)))
    return candidates


# ──────────────────────────────────────────────────────────────────────
# Method 3: Narrative Coverage Gap (NC)
# ──────────────────────────────────────────────────────────────────────

def method_narrative_coverage_gap(models, narratives, arch_stats, sector_stats, name_map):
    """Fill under-represented architectures in high-TNS narratives."""
    print("\n  Method NC: Narrative Coverage Gap")
    candidates = []

    total_models = len(models)
    overall_arch_dist = Counter(m.get("architecture", "") for m in models)

    for narr in narratives:
        tns_comp = narr.get("tns", {}).get("composite", 0)
        tns_cat = narr.get("tns", {}).get("category", "")

        if tns_cat not in ("DEFINING", "MAJOR"):
            continue

        # Expected model share
        expected_pct = 0.15 if tns_cat == "DEFINING" else 0.07
        expected_count = int(total_models * expected_pct)

        # Current model count
        linked_ids = set()
        for bucket in ("what_works", "whats_needed", "what_dies"):
            linked_ids.update(narr.get("outputs", {}).get(bucket, []))
        current_count = len(linked_ids)

        gap = expected_count - current_count
        if gap <= 10:
            continue

        # Get architectures represented in this narrative
        narr_models = [m for m in models if m["id"] in linked_ids]
        narr_archs = Counter(m.get("architecture", "") for m in narr_models)

        # Get NAICS sectors for this narrative
        narr_sectors = [s["naics"] for s in narr.get("sectors", [])]
        if not narr_sectors:
            continue

        primary_naics = narr_sectors[0]
        primary_n2 = primary_naics.split("-")[0] if "-" in primary_naics else primary_naics[:2]

        # Find under-represented architectures (top 6 overall that are sparse here)
        top_archs = [a for a, _ in overall_arch_dist.most_common(10) if a]
        for arch in top_archs:
            overall_share = overall_arch_dist[arch] / total_models
            narr_count = narr_archs.get(arch, 0)
            expected_narr = int(gap * overall_share)

            if expected_narr - narr_count < 3:
                continue

            sector_name = name_map.get(primary_n2, narr["name"].replace(" Transformation", ""))
            forces = narr.get("forces_acting", [])[:3]
            if not forces:
                forces = ["F1_technology"]

            evidence = [
                "Narrative {} (TNS={:.1f}, {}) has {} models, expected ~{}".format(
                    narr["narrative_id"], tns_comp, tns_cat, current_count, expected_count),
                "Architecture '{}' has {} models here vs expected ~{} (gap={})".format(
                    arch, narr_count, expected_narr, expected_narr - narr_count),
            ]

            candidate = build_projected_model(
                method="NC", arch=arch, n2=primary_n2, forces=forces,
                sector_name=sector_name, arch_stats=arch_stats,
                sector_stats=sector_stats, evidence_chain=evidence,
                source_model_ids=[m["id"] for m in narr_models if m.get("architecture") == arch][:5],
                confidence="MEDIUM",
            )
            candidates.append(candidate)

    print("    {} candidates generated".format(len(candidates)))
    return candidates


# ──────────────────────────────────────────────────────────────────────
# Method 4: Force Convergence Hotspot (FC)
# ──────────────────────────────────────────────────────────────────────

# All forces are currently accelerating or shifting
ACCELERATING_FORCES = {
    "F1_technology", "F2_demographics", "F3_geopolitics",
    "F4_capital", "F5_psychology", "F6_energy"
}


def method_force_convergence(models, collisions, arch_stats, sector_stats, name_map):
    """Find sectors with multi-force convergence but low model density."""
    print("\n  Method FC: Force Convergence Hotspot")
    candidates = []

    # Build force coverage per sector from models + collisions
    sector_forces = defaultdict(set)
    sector_count = Counter()

    for m in models:
        n2 = naics2(m)
        sector_count[n2] += 1
        for f in normalize_forces(m.get("forces_v3", [])):
            sector_forces[n2].add(f)

    for coll in collisions:
        coll_forces = set()
        for f in coll.get("forces", []):
            fid = f.get("force_id", f) if isinstance(f, dict) else f
            coll_forces.add(FORCE_CANONICAL.get(fid, fid))
        for sector in coll.get("sectors_affected", []):
            s2 = sector.split("-")[0] if "-" in sector else sector[:2]
            sector_forces[s2].update(coll_forces)

    # Median model density
    counts = sorted(sector_count.values())
    median_density = counts[len(counts) // 2] if counts else 30

    # Find hotspots
    for n2 in sorted(sector_stats.keys()):
        accel = sector_forces[n2] & ACCELERATING_FORCES
        count = sector_count.get(n2, 0)

        if len(accel) < 3 or count >= median_density:
            continue

        avg_t = statistics.mean(sector_stats[n2]["t_scores"]) if sector_stats[n2]["t_scores"] else 0
        if avg_t < 55:
            continue

        # Find best architectures for these specific forces
        force_arch_scores = defaultdict(float)
        for m in models:
            m_forces = set(normalize_forces(m.get("forces_v3", [])))
            overlap = len(m_forces & accel)
            if overlap >= 2:
                arch = m.get("architecture", "")
                if arch:
                    force_arch_scores[arch] += overlap

        top_archs = sorted(force_arch_scores, key=force_arch_scores.get, reverse=True)[:3]

        sector_name = name_map.get(n2, "NAICS " + n2)
        forces = list(accel)

        for arch in top_archs:
            evidence = [
                "Sector {} ({}) has {} accelerating forces ({}) but only {} models (median={})".format(
                    n2, sector_name, len(accel), ", ".join(sorted(accel)),
                    count, median_density),
                "Architecture '{}' has highest force-alignment score ({:.0f}) for these forces".format(
                    arch, force_arch_scores[arch]),
            ]

            candidate = build_projected_model(
                method="FC", arch=arch, n2=n2, forces=forces,
                sector_name=sector_name, arch_stats=arch_stats,
                sector_stats=sector_stats, evidence_chain=evidence,
                confidence="MEDIUM" if len(accel) >= 4 else "LOW",
            )
            candidates.append(candidate)

    print("    {} candidates generated".format(len(candidates)))
    return candidates


# ──────────────────────────────────────────────────────────────────────
# Method 5: Tension-Derived (TD)
# ──────────────────────────────────────────────────────────────────────

def method_tension_derived(models, tensions, narratives, arch_stats, sector_stats, name_map):
    """Convert system tensions into model predictions."""
    print("\n  Method TD: Tension-Derived")
    candidates = []

    narr_map = {n["narrative_id"]: n for n in narratives}

    for t in tensions:
        tt = t.get("tension_type", "")

        if tt == "architecture_cross_sector_gap":
            # Project proven architecture into worst-performing sector
            arch = t.get("architecture", "")
            worst_nid = t.get("worst_narrative_id", t.get("worst_narrative", ""))
            best_o = t.get("best_avg_o", 65)

            narr = narr_map.get(worst_nid)
            if not narr or not arch:
                continue

            narr_sectors = [s["naics"] for s in narr.get("sectors", [])]
            if not narr_sectors:
                continue

            primary_n2 = narr_sectors[0].split("-")[0] if "-" in narr_sectors[0] else narr_sectors[0][:2]
            sector_name = name_map.get(primary_n2, narr["name"].replace(" Transformation", ""))
            forces = narr.get("forces_acting", [])[:3]

            evidence = [
                "Tension {}: architecture '{}' has 20+ pt O-score spread across sectors".format(
                    t["tension_id"], arch),
                "Best sector avg O={:.1f}, worst narrative: {} ({})".format(
                    best_o, narr["name"], worst_nid),
                "Projecting architecture into worst sector with damped O expectation",
            ]

            candidate = build_projected_model(
                method="TD", arch=arch, n2=primary_n2, forces=forces or ["F1_technology"],
                sector_name=sector_name, arch_stats=arch_stats,
                sector_stats=sector_stats, evidence_chain=evidence,
                confidence="HIGH",
            )
            candidates.append(candidate)

        elif tt == "t_o_extreme_divergence":
            direction = t.get("direction", "")
            if direction != "transformation_certain_door_closed":
                continue

            model_id = t.get("model_id", "")
            model = next((m for m in models if m["id"] == model_id), None)
            if not model:
                continue

            parent_t = model.get("composite", 0)
            parent_o = model.get("cla", {}).get("composite", 0)
            gap = parent_t - parent_o

            if gap < 25:
                continue

            n2 = naics2(model)
            sector_name = model.get("sector_name", name_map.get(n2, ""))
            forces = model.get("forces_v3", ["F1_technology"])

            # Project accessible sub-layer architectures
            for sub_arch in ["vertical_saas", "data_compounding"]:
                if sub_arch == model.get("architecture"):
                    continue  # Don't project same architecture as parent

                evidence = [
                    "Tension {}: model {} has T={:.1f}, O={:.1f} (gap={:.1f})".format(
                        t["tension_id"], model_id, parent_t, parent_o, gap),
                    "Parent architecture '{}' is locked; projecting accessible '{}' sub-layer".format(
                        model.get("architecture", ""), sub_arch),
                ]

                candidate = build_projected_model(
                    method="TD", arch=sub_arch, n2=n2, forces=forces,
                    sector_name=sector_name, arch_stats=arch_stats,
                    sector_stats=sector_stats, evidence_chain=evidence,
                    source_model_ids=[model_id],
                    confidence="MEDIUM",
                    name="Accessible {} Layer — {}".format(
                        sub_arch.replace("_", " ").title(),
                        model.get("name", "")[:50]),
                )
                candidates.append(candidate)

    print("    {} candidates generated".format(len(candidates)))
    return candidates


# ──────────────────────────────────────────────────────────────────────
# Deduplication
# ──────────────────────────────────────────────────────────────────────

def deduplicate(candidates, existing_models):
    """Remove candidates that duplicate existing models or each other."""
    # Build existing (arch, naics2) set
    existing = set()
    for m in existing_models:
        existing.add((m.get("architecture", ""), naics2(m)))

    unique = []
    seen = {}  # (arch, naics2) -> best candidate

    for c in candidates:
        key = (c.get("architecture", ""), str(c.get("sector_naics", ""))[:2])

        # Skip if exists in corpus
        if key in existing:
            continue

        # Keep highest triple score per key
        if key in seen:
            if c["triple_score"] > seen[key]["triple_score"]:
                seen[key] = c
        else:
            seen[key] = c

    unique = sorted(seen.values(), key=lambda c: -c["triple_score"])
    return unique


# ──────────────────────────────────────────────────────────────────────
# Confidence Assignment
# ──────────────────────────────────────────────────────────────────────

def assign_confidence(candidates):
    """Assign confidence tiers based on projection quality."""
    METHOD_QUALITY = {"AT": 3, "FR": 3, "TD": 2, "FC": 2, "NC": 1}

    for c in candidates:
        proj = c.get("projection", {})
        method = proj.get("method", "")
        source_count = len(proj.get("source_models", []))

        score = METHOD_QUALITY.get(method, 1)

        if source_count >= 10:
            score += 3
        elif source_count >= 5:
            score += 2
        elif source_count >= 2:
            score += 1

        tri = c.get("triple_score", 0)
        if tri >= 70:
            score += 2
        elif tri >= 60:
            score += 1

        if score >= 7:
            c["confidence_tier"] = "HIGH"
        elif score >= 4:
            c["confidence_tier"] = "MEDIUM"
        else:
            c["confidence_tier"] = "LOW"

        # Update projection confidence to match
        c["projection"]["confidence"] = c["confidence_tier"]


# ──────────────────────────────────────────────────────────────────────
# Verification
# ──────────────────────────────────────────────────────────────────────

def verify_projections(projections, existing_models):
    """Verify projected models pass quality checks."""
    errors = []

    for p in projections:
        pid = p["id"]

        # Score bounds
        for axis in ("SN", "FA", "EC", "TG", "CE"):
            v = p["scores"].get(axis, 0)
            if v < 1 or v > 10:
                errors.append("{}: T.{}={} out of [1,10]".format(pid, axis, v))

        # T composite check
        s = p["scores"]
        expected_t = (s["SN"] * 25 + s["FA"] * 25 + s["EC"] * 20 +
                      s["TG"] * 15 + s["CE"] * 15) / 10
        if abs(p["composite"] - expected_t) > 0.1:
            errors.append("{}: T composite {:.2f} != expected {:.2f}".format(
                pid, p["composite"], expected_t))

        # CLA composite check
        cs = p["cla"]["scores"]
        expected_o = (cs["MO"] * 30 + cs["MA"] * 25 + cs["VD"] * 20 + cs["DV"] * 25) / 10
        if abs(p["cla"]["composite"] - expected_o) > 0.1:
            errors.append("{}: CLA composite {:.2f} != expected {:.2f}".format(
                pid, p["cla"]["composite"], expected_o))

        # VCR composite check
        vs = p["vcr"]["scores"]
        expected_v = (vs["MKT"] * 25 + vs["CAP"] * 25 + vs["ECO"] * 20 +
                      vs["VEL"] * 15 + vs["MOA"] * 15) / 10
        if abs(p["vcr"]["composite"] - expected_v) > 0.1:
            errors.append("{}: VCR composite {:.2f} != expected {:.2f}".format(
                pid, p["vcr"]["composite"], expected_v))

    # Distribution check
    if projections:
        proj_t = [p["composite"] for p in projections]
        proj_o = [p["cla"]["composite"] for p in projections]
        proj_v = [p["vcr"]["composite"] for p in projections]

        exist_t = [m.get("composite", 0) for m in existing_models if m.get("composite")]
        exist_o = [m.get("cla", {}).get("composite", 0) for m in existing_models
                   if m.get("cla", {}).get("composite")]
        exist_v = [m.get("vcr", {}).get("composite", 0) for m in existing_models
                   if m.get("vcr", {}).get("composite")]

        print("\n  Distribution Comparison (Projected vs Existing):")
        for name, pvals, evals in [("T-Score", proj_t, exist_t),
                                    ("CLA/O", proj_o, exist_o),
                                    ("VCR", proj_v, exist_v)]:
            pm, em = statistics.mean(pvals), statistics.mean(evals)
            ps = statistics.stdev(pvals) if len(pvals) > 1 else 0
            es = statistics.stdev(evals) if len(evals) > 1 else 0
            print("    {}: Proj mean={:.1f} (sd={:.1f}) vs Exist mean={:.1f} (sd={:.1f})".format(
                name, pm, ps, em, es))

        # T vs CLA correlation check
        if len(projections) >= 5:
            t_mean = statistics.mean(proj_t)
            o_mean = statistics.mean(proj_o)
            cov = sum((t - t_mean) * (o - o_mean) for t, o in zip(proj_t, proj_o)) / len(proj_t)
            t_std = statistics.stdev(proj_t) if len(proj_t) > 1 else 1
            o_std = statistics.stdev(proj_o) if len(proj_o) > 1 else 1
            r = cov / (t_std * o_std) if t_std > 0 and o_std > 0 else 0
            print("    T vs CLA correlation: r={:.3f} (existing: 0.146, should be <=0.3)".format(r))

    return errors


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("v5.2 MODEL PROJECTION ENGINE")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    models, narratives, collisions, tensions, state = load_all_data()
    print("  {} models, {} narratives, {} collisions, {} tensions".format(
        len(models), len(narratives), len(collisions), len(tensions)))

    # Build matrices
    print("\nBuilding pattern matrices...")
    arch_matrix = build_arch_sector_matrix(models)
    sector_stats = build_sector_stats(models)
    arch_stats = build_arch_stats(models)
    name_map = build_naics_name_map(models)

    print("  {} architecture types, {} NAICS-2 sectors".format(
        len(arch_stats), len(sector_stats)))

    # Run all 5 projection methods
    print("\nRunning projection methods...")

    at = method_architecture_transfer(models, arch_matrix, arch_stats, sector_stats, name_map)
    fr = method_fund_returner_template(models, arch_matrix, arch_stats, sector_stats, name_map)
    nc = method_narrative_coverage_gap(models, narratives, arch_stats, sector_stats, name_map)
    fc = method_force_convergence(models, collisions, arch_stats, sector_stats, name_map)
    td = method_tension_derived(models, tensions, narratives, arch_stats, sector_stats, name_map)

    all_candidates = at + fr + nc + fc + td
    print("\n  Total raw candidates: {}".format(len(all_candidates)))

    # Deduplicate
    print("\nDeduplicating against {} existing models...".format(len(models)))
    unique = deduplicate(all_candidates, models)
    print("  {} unique projections after dedup".format(len(unique)))

    # Assign confidence
    assign_confidence(unique)

    # Rank by triple score
    for i, c in enumerate(unique, 1):
        c["projection_rank"] = i

    # Verify
    print("\nVerification...")
    errors = verify_projections(unique, models)
    if errors:
        print("  ERRORS:")
        for e in errors[:10]:
            print("    " + e)
    else:
        print("  All checks passed")

    # Summary stats
    method_dist = Counter(c["projection"]["method"] for c in unique)
    conf_dist = Counter(c.get("confidence_tier", "LOW") for c in unique)
    vcr_dist = Counter(c["vcr"]["category"] for c in unique)
    opp_dist = Counter(c["cla"]["category"] for c in unique)

    print("\n" + "=" * 70)
    print("PROJECTION SUMMARY")
    print("=" * 70)
    print("\n  Total projections: {}".format(len(unique)))
    print("  By method: {}".format(dict(method_dist)))
    print("  By confidence: {}".format(dict(conf_dist)))
    print("  By VCR category: {}".format(dict(vcr_dist)))
    print("  By OPP category: {}".format(dict(opp_dist)))

    if unique:
        triples = [c["triple_score"] for c in unique]
        print("\n  Triple Score: max={:.1f}, mean={:.1f}, median={:.1f}".format(
            max(triples), statistics.mean(triples), statistics.median(triples)))

        print("\n  Top 15 Projected Models:")
        print("  {:>4}  {:>5}  {:>5}  {:>5}  {:>6}  {:>6}  {:<25}  {:<20}  {}".format(
            "Rank", "T", "O", "VCR", "Triple", "Conf", "Architecture", "Sector", "Method"))
        print("  " + "-" * 115)
        for c in unique[:15]:
            print("  {:>4}  {:>5.1f}  {:>5.1f}  {:>5.1f}  {:>6.1f}  {:>6}  {:<25}  {:<20}  {}".format(
                c["projection_rank"],
                c["composite"],
                c["cla"]["composite"],
                c["vcr"]["composite"],
                c["triple_score"],
                c.get("confidence_tier", ""),
                c["architecture"][:25],
                c["sector_name"][:20],
                c["projection"]["method"]))

    # Write output
    cycle_id = state.get("current_cycle", "v5-1")
    eng_ver = state.get("engine_version", "5.1")

    output = {
        "cycle": cycle_id,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "engine_version": eng_ver + "-projector",
        "source_data": {
            "models": len(models),
            "narratives": len(narratives),
            "collisions": len(collisions),
            "tensions": len(tensions),
        },
        "projection_methods": {
            "AT": {"name": "Architecture Transfer", "candidates": method_dist.get("AT", 0),
                   "description": "Proven architectures applied to new transforming sectors"},
            "FR": {"name": "FUND_RETURNER Template", "candidates": method_dist.get("FR", 0),
                   "description": "High-ROI patterns projected to uncovered fragmented sectors"},
            "NC": {"name": "Narrative Coverage Gap", "candidates": method_dist.get("NC", 0),
                   "description": "Under-represented architectures in DEFINING/MAJOR narratives"},
            "FC": {"name": "Force Convergence Hotspot", "candidates": method_dist.get("FC", 0),
                   "description": "Multi-force sectors with below-median model density"},
            "TD": {"name": "Tension-Derived", "candidates": method_dist.get("TD", 0),
                   "description": "System tensions converted to model predictions"},
        },
        "summary": {
            "total_projected": len(unique),
            "by_method": dict(method_dist),
            "by_confidence": dict(conf_dist),
            "by_vcr_category": dict(vcr_dist),
            "by_opp_category": dict(opp_dist),
            "triple_score_stats": {
                "max": round(max(triples), 1) if unique else 0,
                "mean": round(statistics.mean(triples), 1) if unique else 0,
                "median": round(statistics.median(triples), 1) if unique else 0,
            } if unique else {},
            "verification_errors": len(errors),
        },
        "projections": unique,
    }

    V5_DIR.mkdir(parents=True, exist_ok=True)
    with open(V5_DIR / "projections.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\n  Written: {}".format(V5_DIR / "projections.json"))


if __name__ == "__main__":
    main()
