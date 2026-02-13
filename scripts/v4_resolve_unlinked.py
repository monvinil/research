#!/usr/bin/env python3
"""
v4.1 Phase 3D: Resolve 53 unlinked models by assigning narrative_ids.

Strategy:
- Extend TN-005 (Admin Services) to cover NAICS 81 (Other Services) + 48-49 (Transportation)
- Extend TN-003 (Manufacturing) to cover agriculture (11) + defense MRO
- Extend TN-008 (Defense AI) to cover defense logistics + government tech
- Extend TN-010 (IT Services) to cover broader NAICS 51 (Information)
- Extend TN-014 (Retail) to cover NAICS 72 (Accommodation/Food)
- Extend TN-002 (Professional Services) to cover NAICS 71 (Arts/Entertainment)
- Create TN-015 (Energy & Resources) for NAICS 22 (Utilities) + 21 (Mining)
"""

import json
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data/v4"

# Mapping: model_id → (narrative_id, narrative_role)
ASSIGNMENTS = {
    # === TN-005 (Admin Services) — extend to NAICS 81, 48-49 ===
    # NAICS 81 - Other Services
    "PC8-AM-AUTO-01":           ("TN-005", "what_works"),
    "PC8-AM-AUTOBODY-01":       ("TN-005", "what_works"),
    "PC8-RC-AUTO-01":           ("TN-005", "what_works"),
    "PC8-DC-AUTO-01":           ("TN-005", "what_works"),
    "PC8-AM-COMMER-01":         ("TN-005", "what_works"),
    "PC8-FSR-COMMEQREP-01":     ("TN-005", "what_works"),
    "PC8-DC-COMMEQREP-01":      ("TN-005", "what_works"),
    "PC8-AM-ELECREPAIR-01":     ("TN-005", "what_works"),
    "PC8-AM-BEAUT-01":          ("TN-005", "what_works"),
    "PC8-PI-BEAUT-01":          ("TN-005", "whats_needed"),
    "PC8-FSR-PRIVHH-01":        ("TN-005", "what_works"),
    "PC8-FSR-BIZASSOC-01":      ("TN-005", "what_works"),
    "PC8-FSR-CHARITY-01":       ("TN-005", "what_works"),
    # NAICS 48-49 - Transportation/Warehousing
    "C7-PI-TRUCKING-01":        ("TN-005", "whats_needed"),
    "PC8-FSR-LOCALTRUCK-01":    ("TN-005", "what_works"),
    "PC8-FSR-AIRLINE-01":       ("TN-005", "what_works"),
    "PC8-DC-FREIGHT-01":        ("TN-005", "what_works"),
    "PC8-EXT-FAILSTUDY-CONVOY-01": ("TN-005", "what_works"),
    "PC8-MN-TOWING-01":         ("TN-005", "what_works"),
    "PC8-FSR-COURIER-01":       ("TN-005", "what_works"),
    "PC8-PI-WAREHOUSE-01":      ("TN-005", "whats_needed"),

    # === TN-003 (Manufacturing) — extend to agriculture (11) + defense MRO ===
    "V3-DEF-010":               ("TN-003", "what_works"),   # Defense Predictive Maintenance AI
    "C7-PI-AGRICULTURE-01":     ("TN-003", "what_works"),   # Precision Agriculture Platform
    "PC8-EXT-AIBENE-FARMOPS-01":("TN-003", "what_works"),   # Smart Small Farm Operations
    "C7-NR-09":                 ("TN-003", "what_works"),   # AG Irrigation Tech

    # === TN-008 (Defense AI) — add defense logistics + government ===
    "V3-DEF-004":               ("TN-008", "what_works"),   # Defense Logistics Optimizer
    "PC8-SC-GOVTECH-01":        ("TN-008", "what_works"),   # Gov Tech
    "C7-NR-08":                 ("TN-008", "what_works"),   # Platform Government AI

    # === TN-010 (IT Services) — extend to broader NAICS 51 (Information) ===
    "V3-FEAR-006":              ("TN-010", "what_works"),   # Deepfake Detection
    "V3-FEAR-007":              ("TN-010", "what_works"),   # Watermarking/Provenance
    "V3-FEAR-002":              ("TN-010", "what_works"),   # Content Authenticity
    "PC8-FSR-MOTIONPIC-01":     ("TN-010", "what_works"),   # Autonomous Video Production
    "PC8-AW-MEDIA-01":          ("TN-010", "what_works"),   # Distressed Media Acquisition
    "PC8-EXT-DEADBIZ-PHOTOLAB-01": ("TN-010", "what_works"), # Photo/Video Post-Production
    "PC8-FSR-PERIODORIG-01":    ("TN-010", "what_works"),   # Autonomous Publishing
    "PC8-EXT-DEADBIZ-LOCALCONTENT-01": ("TN-010", "what_works"), # Local News Revival
    "PC8-FSR-TELECOM-01":       ("TN-010", "what_works"),   # Regional Telecom Automation
    "C7-NR-11":                 ("TN-010", "what_works"),   # General Writing Tool
    "C7-NR-12":                 ("TN-010", "what_works"),   # Automated Code Generation
    "V3-GEO-001":               ("TN-010", "what_works"),   # Gulf/MENA AI Infrastructure
    "V3-GEO-007":               ("TN-010", "what_works"),   # Africa/South Asia Compute

    # === TN-014 (Retail) — extend to NAICS 72 (Accommodation/Food) ===
    "PC8-FSR-HOTEL-01":         ("TN-014", "what_works"),   # Autonomous Hotel Operations
    "PC8-DC-HOTEL-01":          ("TN-014", "what_works"),   # Hospitality Revenue Intelligence

    # === TN-002 (Professional Services) — extend to NAICS 71 (Arts/Entertainment) ===
    "PC8-FSR-TALENT-01":        ("TN-002", "what_works"),   # Automated Talent Agent
    "PC8-FSR-INDARTIST-01":     ("TN-002", "what_works"),   # Full-Service Creative Ops
    "PC8-FSR-SPORTSTCH-01":     ("TN-002", "what_works"),   # Sports Analytics

    # === TN-015 (Energy & Resources — NEW) ===
    "PC8-FSR-GASUTIL-01":       ("TN-015", "what_works"),   # Automated Gas Distribution
    "PC8-FSR-POWERUTIL-01":     ("TN-015", "what_works"),   # Automated Grid Operations
    "PC8-SC-ENERGYSVC-01":      ("TN-015", "whats_needed"), # Energy Services Platform
    "V3-ENERGY-002":            ("TN-015", "what_works"),   # Behind-the-Meter Power
    "V3-ENERGY-008":            ("TN-015", "what_works"),   # Virtual Power Plant
    "V3-ENERGY-006":            ("TN-015", "what_works"),   # Critical Minerals Platform
    "PC8-SC-OILFIELD-01":       ("TN-015", "what_works"),   # Oilfield Services Automation
}

# New narrative: TN-015
NEW_NARRATIVE = {
    "narrative_id": "TN-015",
    "name": "Energy & Resources Transformation",
    "slug": "energy-resources",
    "collision_ids": ["FC-026", "FC-027", "FC-028"],  # F1xF6, F3xF6, F1xF3 collisions
    "sectors": [
        {"naics": "22", "role": "primary"},
        {"naics": "21", "role": "secondary"},
    ],
    "summary": "Energy sector transformation driven by AI + electrification + geopolitical energy security. Grid modernization, distributed energy, critical mineral supply chains, and autonomous field operations. $1.3T US utility sector + $200B oilfield services. Grid operators face surging AI data center demand (projected 2x by 2028) while integrating distributed renewables. Critical minerals (lithium, cobalt, rare earths) supply chain concentration creates geopolitical vulnerability and reshoring pressure. Behind-the-meter and virtual power plant models emerge as grid edge intelligence. Oilfield services face dual transition: AI automation of operations + long-term energy transition pressure.",
    "transformation_phase": "early_disruption",
    "forces_acting": ["F1_technology", "F3_geopolitics", "F6_energy"],
    "tns": {
        "economic_magnitude": 8.0,
        "force_convergence": 7.5,
        "evidence_strength": 6.0,
        "timing_confidence": 5.5,
        "irreversibility": 7.0,
        "composite": 69.75,
        "category": "MAJOR",
        "rank": 12
    },
    "year_by_year": {
        "2026": {
            "phase": "early_disruption",
            "description": "AI data center energy demand straining grids. Virtual power plants emerging. Critical minerals supply chain diversification accelerating.",
            "indicators": []
        },
        "2027": {
            "phase": "acceleration",
            "description": "Grid modernization investment surge. Behind-the-meter deployments scaling. First autonomous oilfield operations.",
            "indicators": []
        },
        "2028": {
            "phase": "acceleration",
            "description": "Grid edge intelligence platforms reach scale. Critical minerals reshoring facilities operational.",
            "indicators": []
        },
        "2029": {
            "phase": "restructuring",
            "description": "Utility business model shift from volumetric to platform. Distributed energy dominant in new construction.",
            "indicators": []
        },
        "2030_2031": {
            "phase": "new_equilibrium",
            "description": "Grid as platform model established. Energy-AI co-optimization standard.",
            "indicators": []
        }
    },
    "geographic_variation": {},
    "outputs": {
        "what_works": [],
        "whats_needed": [],
        "what_dies": []
    },
    "cascade_dependencies": {
        "depends_on": ["TN-003"],  # Manufacturing drives energy demand
        "upstream_of": ["TN-006"]  # Energy affects construction
    },
    "fear_friction": {
        "economic_readiness": 7,
        "psychological_readiness": 5,
        "gap": 2,
        "classification": "moderate_friction",
        "notes": "Grid modernization faces regulatory inertia and NIMBY resistance. Utilities are conservative by nature (rate-regulated monopolies). Critical minerals face geopolitical fear. Data center energy demand creates tension with climate goals."
    },
    "falsification_criteria": [],
    "confidence": {
        "direction": "H",
        "timing": "M",
        "magnitude": "M"
    },
    "collision_ids_detail": [
        {"id": "FC-026", "forces": ["F1_technology", "F6_energy"], "type": "amplifying"},
        {"id": "FC-027", "forces": ["F3_geopolitics", "F6_energy"], "type": "amplifying"},
        {"id": "FC-028", "forces": ["F1_technology", "F3_geopolitics"], "type": "amplifying"}
    ]
}

# Extended sector coverage for existing narratives
SECTOR_EXTENSIONS = {
    "TN-005": [
        {"naics": "81", "role": "secondary"},
        {"naics": "48-49", "role": "secondary"},
    ],
    "TN-003": [
        {"naics": "11", "role": "secondary"},
    ],
    "TN-008": [
        {"naics": "92", "role": "secondary"},
    ],
    "TN-010": [
        {"naics": "51", "role": "secondary"},
    ],
    "TN-014": [
        {"naics": "72", "role": "secondary"},
    ],
    "TN-002": [
        {"naics": "71", "role": "secondary"},
    ],
}


def main():
    print("=" * 70)
    print("v4.1 Phase 3D: Resolve Unlinked Models")
    print("=" * 70)

    # Load data
    with open(V4_DIR / "models.json") as f:
        models_data = json.load(f)
    models = models_data["models"]

    with open(V4_DIR / "narratives.json") as f:
        narr_data = json.load(f)
    narratives = narr_data["narratives"]

    # Verify we have the right count
    unlinked_before = sum(1 for m in models if not m.get("narrative_ids"))
    print(f"\nUnlinked models before: {unlinked_before}")
    print(f"Assignments defined: {len(ASSIGNMENTS)}")

    # Apply assignments to models
    assigned = 0
    missing = []
    for m in models:
        mid = m["id"]
        if mid in ASSIGNMENTS:
            narr_id, role = ASSIGNMENTS[mid]
            m["narrative_ids"] = [narr_id]
            m["narrative_role"] = role
            assigned += 1

    # Check for assignments that didn't match any model
    model_ids = {m["id"] for m in models}
    for mid in ASSIGNMENTS:
        if mid not in model_ids:
            missing.append(mid)

    print(f"Models updated: {assigned}")
    if missing:
        print(f"WARNING: {len(missing)} assignment IDs not found in models: {missing}")

    # Add TN-015 to narratives
    narratives.append(NEW_NARRATIVE)
    print(f"\nAdded new narrative: TN-015 Energy & Resources Transformation")

    # Re-rank narratives by TNS composite
    narratives.sort(key=lambda n: n["tns"]["composite"], reverse=True)
    for i, n in enumerate(narratives):
        n["tns"]["rank"] = i + 1

    # Extend sector coverage
    narr_map = {n["narrative_id"]: n for n in narratives}
    for nid, new_sectors in SECTOR_EXTENSIONS.items():
        n = narr_map[nid]
        existing_naics = {s["naics"] for s in n.get("sectors", [])}
        for s in new_sectors:
            if s["naics"] not in existing_naics:
                n["sectors"].append(s)
                print(f"  Extended {nid} sector coverage: +NAICS {s['naics']} ({s['role']})")

    # Rebuild narrative outputs arrays from model assignments
    # First, clear existing outputs for affected narratives
    affected_narr_ids = set()
    for mid, (nid, role) in ASSIGNMENTS.items():
        affected_narr_ids.add(nid)

    # Rebuild outputs for ALL narratives from model data
    for n in narratives:
        nid = n["narrative_id"]
        n["outputs"] = {"what_works": [], "whats_needed": [], "what_dies": []}

    for m in models:
        for nid in m.get("narrative_ids", []):
            if nid in narr_map:
                role = m.get("narrative_role", "what_works")
                bucket = role if role in ("what_works", "whats_needed", "what_dies") else "what_works"
                narr_map[nid]["outputs"][bucket].append(m["id"])

    # Update counts
    linked = sum(1 for m in models if m.get("narrative_ids"))
    unlinked = sum(1 for m in models if not m.get("narrative_ids"))
    models_data["linked_count"] = linked
    models_data["unlinked_count"] = unlinked

    # Write back
    with open(V4_DIR / "models.json", "w") as f:
        json.dump(models_data, f, indent=2, ensure_ascii=False)
    print(f"\nWritten: {V4_DIR / 'models.json'}")

    with open(V4_DIR / "narratives.json", "w") as f:
        json.dump(narr_data, f, indent=2, ensure_ascii=False)
    print(f"Written: {V4_DIR / 'narratives.json'}")

    # Summary
    print(f"\n{'=' * 70}")
    print("RESOLUTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Models linked: {linked}/{len(models)} ({linked/len(models)*100:.1f}%)")
    print(f"  Models unlinked: {unlinked}")
    print(f"  Narratives: {len(narratives)} (was 15, now 16)")
    print()

    # Per-narrative model counts
    print("  Narrative model counts:")
    for n in narratives:
        outs = n["outputs"]
        total = sum(len(outs[b]) for b in ["what_works", "whats_needed", "what_dies"])
        print(f"    #{n['tns']['rank']:2d}  {n['tns']['composite']:5.1f}  {n['narrative_id']}  {n['name'][:45]:45s}  {total:3d} models")

    # Role distribution
    roles = {"what_works": 0, "whats_needed": 0, "what_dies": 0, "unlinked": 0}
    for m in models:
        role = m.get("narrative_role", "unlinked")
        if role in roles:
            roles[role] += 1
        else:
            roles["what_works"] += 1
    print(f"\n  Role distribution: {roles}")


if __name__ == "__main__":
    main()
