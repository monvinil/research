#!/usr/bin/env python3
"""
v4 Migration: Generate v4 entities from existing v3 data.

Reads:
  - data/context/state.json (sector_transformations, geographic_profiles, fear_friction_index, force_velocities)
  - data/verified/v3-7_fs_cre_cascade_2026-02-12.json
  - data/verified/v3-7_entry_level_extinction_cascade_2026-02-12.json
  - data/verified/v314_cascade_coverage_2026-02-12.json

Generates:
  - data/v4/collisions.json (~30-50 force collisions)
  - data/v4/narratives.json (~20-30 transformation narratives)
  - data/v4/cascades.json (~3-5 cascade chains)
  - data/v4/geographies.json (8 region profiles)
  - data/v4/state.json (v4 engine state)

Non-destructive: no v3 files are modified.
"""

import json
from itertools import combinations
from pathlib import Path
from collections import Counter

BASE = Path("/Users/mv/Documents/research")
STATE_FILE = BASE / "data/context/state.json"
CASCADE_FILES = [
    BASE / "data/verified/v3-7_fs_cre_cascade_2026-02-12.json",
    BASE / "data/verified/v3-7_entry_level_extinction_cascade_2026-02-12.json",
    BASE / "data/verified/v314_cascade_coverage_2026-02-12.json",
]
V4_DIR = BASE / "data/v4"

# Force collision type heuristics based on force pair interactions
COLLISION_TYPE_MAP = {
    frozenset({"F1_technology", "F2_demographics"}): "amplifying",
    frozenset({"F1_technology", "F3_geopolitics"}): "sequential",
    frozenset({"F1_technology", "F4_capital"}): "amplifying",
    frozenset({"F1_technology", "F5_psychology"}): "opposing",
    frozenset({"F1_technology", "F6_energy"}): "conditional",
    frozenset({"F2_demographics", "F3_geopolitics"}): "sequential",
    frozenset({"F2_demographics", "F4_capital"}): "amplifying",
    frozenset({"F2_demographics", "F5_psychology"}): "opposing",
    frozenset({"F2_demographics", "F6_energy"}): "conditional",
    frozenset({"F3_geopolitics", "F4_capital"}): "amplifying",
    frozenset({"F3_geopolitics", "F5_psychology"}): "opposing",
    frozenset({"F3_geopolitics", "F6_energy"}): "conditional",
    frozenset({"F4_capital", "F5_psychology"}): "opposing",
    frozenset({"F4_capital", "F6_energy"}): "conditional",
    frozenset({"F5_psychology", "F6_energy"}): "conditional",
}

# Theory lens mapping based on force pairs
FORCE_THEORY_MAP = {
    "F1_technology": ["T1_schumpeter", "T6_jevons", "T21_polanyi", "T22_prediction_machines"],
    "F2_demographics": ["T8_demographics", "T3_baumol", "T10_coase"],
    "F3_geopolitics": ["T5_perez", "T24_robotics_ai"],
    "F4_capital": ["T4_minsky", "T15_minsky_extended", "T18_real_options"],
    "F5_psychology": ["T25_fear_economics", "T14_prospect_theory"],
    "F6_energy": ["T20_complexity_economics"],
}

# Mechanism descriptions for force collisions
FORCE_MECHANISM_TEMPLATES = {
    "F1_technology": {
        "31-33": "Cobot cost $25-60K with 6-18mo ROI; CNC/digital twin integration",
        "52": "AI automates 60-70% of routine cognitive financial tasks",
        "54": "AI coding disrupts 84% of IT workforce; legal AI at 82% ethical concern",
        "62": "FDA deregulated AI clinical decision support; invisible admin→clinical pathway",
        "56": "AI replaces staffing intermediation entirely",
        "44-45": "Self-checkout 87% adoption; warehouse automation $181B by 2031",
        "61": "AI tutoring and assessment; chatbot liability emerging",
        "928110": "DoD Maven 100% machine-generated intel by mid-2026; autonomous warfare",
        "23": "Design automation, BIM, drone inspection",
        "42": "Algorithmic sourcing and demand forecasting",
        "5415": "84% daily AI coding usage; self-disruption paradox",
        "55": "AI collapses coordination cost; middle management 20% elimination",
        "53": "AI agents replace 453K broker functions; NAR settlement",
        "523": "60-70% of junior analyst tasks automated; entry-level -24pp",
        "51": "Content creation contracts while AI infra grows",
        "22": "Grid optimization AI; data center energy management",
        "N/A-MICRO": "AI agent teams replace 10-15 human roles; micro-firm OS",
    },
    "F2_demographics": {
        "31-33": "Machinist median age 57; 392K fragmented establishments; $10T transfer",
        "52": "38% of advisors plan to retire within decade",
        "54": "CPA pipeline -33%; 42 states teacher shortage",
        "62": "Nursing 8% deficit; 250K RN gap by 2030; aging patient demand",
        "56": "Entry-level hiring collapse -67% junior devs",
        "44-45": "Entry-level displacement concentrates on young/minority workers",
        "61": "College enrollment cliff 15% decline; 400 schools at risk",
        "928110": "Veteran workforce aging; recruitment challenges",
        "23": "499K new workers needed; 6-8% trade wage inflation",
        "5415": "Entry-level developer extinction; pipeline collapse",
        "55": "Executive retirement wave; succession planning gaps",
        "53": "Silver Tsunami impacts commercial property ownership",
        "523": "38% advisor retirement; 345 M&A deals in RIA",
        "N/A-MICRO": "Silver Tsunami creates 12M business transitions; Coasean shrinkage",
    },
    "F3_geopolitics": {
        "31-33": "Reshoring + nearshoring from 47.5% China tariffs; CHIPS Act",
        "928110": "ReArm Europe EUR 800B; AUKUS; CMMC enforcement 220K+ companies",
        "23": "Data center construction boom; tariff-driven domestic demand",
        "52": "US-China financial decoupling; capital controls risk",
    },
    "F4_capital": {
        "31-33": "PE dry powder targeting Silver Tsunami at 3-5x EBITDA",
        "52": "CRE CMBS 12.3% delinquency; PE refinancing wall $930B 2026",
        "54": "PE backing AI-native professional services startups",
        "62": "PE record $190B+ healthcare deal value",
        "44-45": "Retail media networks $69B new profit layer",
        "928110": "Defense tech $17.9B equity (+145% YoY); exits $54.4B",
        "5415": "AI mega-rounds >$140B Jan-Feb 2026",
        "55": "Corporate restructuring under AI pressure",
        "53": "$936B CRE debt maturity wall 2026; extend-and-pretend exhausting",
        "523": "RIA M&A record 345 deals; $1.22T transacted",
        "N/A-MICRO": "SBA 504 + robotics financing; revenue-based financing",
    },
    "F5_psychology": {
        "62": "34-pt provider-patient trust gap; invisible AI adoption pathway",
        "44-45": "Consumer adoption 87% self-checkout but cashierless only 13.7%",
        "61": "Highest fear friction gap=5; Brookings study; chatbot liability",
        "5415": "84% AI coding but experienced devs 19% SLOWER — perception gap",
        "55": "60% anticipatory displacement; executives see cost reduction",
        "53": "NAR settlement psychological shock; broker identity crisis",
        "54": "Legal 82% ethical concern; CPA trust barriers",
    },
    "F6_energy": {
        "31-33": "Manufacturing energy transition; electrification of processes",
        "22": "Data center electricity doubling to 945 TWh; 2,600 GW grid queue",
    },
}


def generate_collisions(state):
    """Generate force collision entities from sector transformations."""
    sector_transforms = state.get("sector_transformations", [])
    collisions = []
    collision_id_counter = 1
    seen_pairs = {}  # track unique (force_pair, sector) to avoid duplicates

    for st in sector_transforms:
        forces = st.get("forces_acting", [])
        naics = st.get("sector_naics", "")

        # Generate collisions for each pair of forces acting on this sector
        for f1, f2 in combinations(forces, 2):
            pair_key = (frozenset({f1, f2}), naics)
            if pair_key in seen_pairs:
                # Add this sector to existing collision
                seen_pairs[pair_key]["sectors_affected"].append(naics)
                continue

            collision_type = COLLISION_TYPE_MAP.get(
                frozenset({f1, f2}), "sequential"
            )

            # Build mechanism descriptions
            mechanisms = []
            for force_id in [f1, f2]:
                mech = FORCE_MECHANISM_TEMPLATES.get(force_id, {}).get(naics)
                if mech:
                    mechanisms.append({"force_id": force_id, "mechanism": mech})
                else:
                    mechanisms.append({"force_id": force_id, "mechanism": f"{force_id} acting on {st.get('sector_name', naics)}"})

            # Collect theoretical lenses
            lenses = list(set(
                FORCE_THEORY_MAP.get(f1, []) + FORCE_THEORY_MAP.get(f2, [])
            ))

            collision = {
                "collision_id": f"FC-{collision_id_counter:03d}",
                "name": f"{f1.split('_',1)[1].title()} + {f2.split('_',1)[1].title()} in {st.get('sector_name', naics)}",
                "forces": mechanisms,
                "collision_type": collision_type,
                "sectors_affected": [naics],
                "theoretical_lenses": sorted(lenses),
                "confidence": st.get("phase_confidence", "medium"),
                "source_sector_transformation": naics,
            }
            collisions.append(collision)
            seen_pairs[pair_key] = collision
            collision_id_counter += 1

    return collisions


def generate_narratives(state, collisions, fear_friction_by_naics):
    """Generate transformation narratives from sector transformations."""
    sector_transforms = state.get("sector_transformations", [])
    narratives = []

    for i, st in enumerate(sector_transforms):
        naics = st.get("sector_naics", "")
        sector_name = st.get("sector_name", "")

        # Skip monitoring-only entries
        if st.get("transformation_phase") == "monitoring":
            continue

        # Find collisions that involve this sector
        narrative_collision_ids = [
            c["collision_id"] for c in collisions
            if naics in c.get("sectors_affected", [])
        ]

        # Get fear friction data
        ff = fear_friction_by_naics.get(naics, {})

        # Map transformation_phase to year_by_year phases
        phase = st.get("transformation_phase", "pre_disruption")
        year_by_year = _generate_year_projections(phase, sector_name, st.get("evidence_summary", ""))

        narrative = {
            "narrative_id": f"TN-{i+1:03d}",
            "name": f"{sector_name} Transformation",
            "slug": sector_name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", ""),
            "collision_ids": narrative_collision_ids,
            "sectors": [{"naics": naics, "role": "primary"}],
            "summary": st.get("evidence_summary", ""),
            "transformation_phase": phase,
            "tns": {
                "economic_magnitude": 0,  # Scored by v4_narrative_scoring.py
                "force_convergence": 0,
                "evidence_strength": 0,
                "timing_confidence": 0,
                "irreversibility": 0,
                "composite": 0,
            },
            "year_by_year": year_by_year,
            "geographic_variation": {},  # Populated from geographic profiles
            "outputs": {
                "what_works": [],
                "whats_needed": [],
                "what_dies": [],
            },
            "cascade_dependencies": {
                "upstream_of": [],
                "downstream_of": [],
                "amplified_by": [],
                "dampened_by": [],
            },
            "fear_friction": {
                "economic_readiness": ff.get("economic_readiness", 5),
                "psychological_readiness": ff.get("psychological_readiness", 5),
                "gap": ff.get("gap", 0),
                "classification": ff.get("classification", "neutral"),
                "notes": ff.get("notes"),
            },
            "falsification_criteria": [],
            "confidence": {
                "direction": st.get("phase_confidence", "medium"),
                "timing": "medium",
                "magnitude": "medium",
            },
            "forces_acting": st.get("forces_acting", []),
            "supporting_patterns": st.get("supporting_patterns", []),
            "v3_models_rated": st.get("v3_models_rated", 0),
            "v2_models_count": st.get("v2_models_count", 0),
            "last_updated": st.get("last_updated", "v3-18"),
        }
        narratives.append(narrative)

    return narratives


def _generate_year_projections(phase, sector_name, evidence):
    """Generate initial year-by-year projections based on transformation phase."""
    phase_sequences = {
        "pre_disruption": {
            "2026": {"phase": "pre_disruption", "description": f"Early signals of structural change in {sector_name}. Cost curves shifting, technology proving feasible.", "indicators": []},
            "2027": {"phase": "early_adoption", "description": "First movers adopt new approaches. Incumbent awareness growing.", "indicators": []},
            "2028": {"phase": "early_disruption", "description": "Adoption accelerates among forward-looking firms. Evidence of business model viability.", "indicators": []},
            "2029": {"phase": "acceleration", "description": "Mainstream adoption begins. Incumbent response intensifies.", "indicators": []},
            "2030_2031": {"phase": "restructuring", "description": "Sector structure visibly changing. Employment and firm composition shifting.", "indicators": []},
        },
        "early_disruption": {
            "2026": {"phase": "early_disruption", "description": f"Disruption underway in {sector_name}. First entrants proving viability. Incumbents beginning to respond.", "indicators": []},
            "2027": {"phase": "acceleration", "description": "Adoption curves steepening. Nash equilibrium breaking for early incumbent defectors.", "indicators": []},
            "2028": {"phase": "acceleration", "description": "Mainstream disruption. Significant employment and revenue shifts.", "indicators": []},
            "2029": {"phase": "restructuring", "description": "Sector consolidation. Weak incumbents exiting. New firm structures emerging.", "indicators": []},
            "2030_2031": {"phase": "new_equilibrium", "description": "New sector structure stabilized. Dominant business models established.", "indicators": []},
        },
        "acceleration": {
            "2026": {"phase": "acceleration", "description": f"Rapid transformation in {sector_name}. Multiple disruption vectors active simultaneously.", "indicators": []},
            "2027": {"phase": "restructuring", "description": "Sector consolidation accelerating. Cascading exits among laggards.", "indicators": []},
            "2028": {"phase": "restructuring", "description": "Employment restructuring. New roles emerging, legacy roles declining.", "indicators": []},
            "2029": {"phase": "new_equilibrium", "description": "New sector structure forming. Survivors adapting to new reality.", "indicators": []},
            "2030_2031": {"phase": "new_equilibrium", "description": "Transformation largely complete. Sector operating under new economics.", "indicators": []},
        },
    }
    return phase_sequences.get(phase, phase_sequences["pre_disruption"])


def generate_cascades():
    """Generate cascade entities from existing cascade analysis files."""
    cascades = []

    for cascade_file in CASCADE_FILES:
        if not cascade_file.exists():
            print(f"  Warning: {cascade_file.name} not found, skipping")
            continue

        with open(cascade_file) as f:
            data = json.load(f)

        # Handle list-format cascade files (v314_cascade_coverage is a list)
        if isinstance(data, list):
            cascade = {
                "cascade_id": f"CASCADE-{len(cascades)+1:03d}",
                "name": f"Cascade coverage analysis ({len(data)} entries)",
                "source_file": cascade_file.name,
                "analysis_id": cascade_file.stem,
                "links": [],
                "link_count": 0,
                "narrative_ids": [],
                "confidence": "medium",
            }
            cascades.append(cascade)
            continue

        analysis_id = data.get("analysis_id", cascade_file.stem)

        # Extract cascade chain links
        chain = data.get("cascade_chain", {})
        links = []
        for key, val in chain.items():
            if key.startswith("link_") and isinstance(val, dict):
                links.append({
                    "link_name": val.get("link_name", key),
                    "position": val.get("position_in_chain", 0),
                    "status": val.get("status", "unknown"),
                    "confidence": val.get("confidence", "medium"),
                    "mechanism": val.get("transmission_mechanism", "")[:200] if val.get("transmission_mechanism") else "",
                })

        cascade = {
            "cascade_id": f"CASCADE-{len(cascades)+1:03d}",
            "name": data.get("executive_summary", analysis_id)[:120],
            "source_file": cascade_file.name,
            "analysis_id": analysis_id,
            "links": sorted(links, key=lambda x: x.get("position", 0)),
            "link_count": len(links),
            "narrative_ids": [],  # Populated after narratives are generated
            "confidence": "high" if any(l.get("status", "").startswith("ACTIVE") for l in links) else "medium",
        }
        cascades.append(cascade)

    return cascades


def generate_geographies(state):
    """Generate geography profiles from state.json."""
    geo_profiles = state.get("geographic_profiles", [])
    geographies = []

    for gp in geo_profiles:
        geo = {
            "region_id": gp.get("region", ""),
            "name": gp.get("region", ""),
            "demographic_profile": gp.get("demographic_profile", {}),
            "ai_readiness": gp.get("ai_readiness", {}),
            "transformation_velocity": gp.get("transformation_velocity", {}),
            "narrative_velocities": {},  # Populated after narrative scoring
            "last_updated": gp.get("last_updated", "v3-18"),
        }
        geographies.append(geo)

    return geographies


def link_cascades_to_narratives(cascades, narratives):
    """Link cascade chains to relevant narratives based on sector overlap."""
    # Build a mapping of cascade source files to narrative sectors
    cascade_sector_hints = {
        "v3-7_fs_cre_cascade": ["52", "53", "523"],
        "v3-7_entry_level_extinction": ["5415", "54", "56", "61"],
        "v314_cascade_coverage": ["52", "53", "44-45", "31-33"],
        "v3-5_financial_services": ["52", "523"],
    }

    narrative_by_naics = {}
    for n in narratives:
        for s in n.get("sectors", []):
            narrative_by_naics.setdefault(s["naics"], []).append(n["narrative_id"])

    for cascade in cascades:
        source = cascade.get("source_file", "")
        matched_narratives = set()
        for hint_key, hint_sectors in cascade_sector_hints.items():
            if hint_key in source:
                for sector in hint_sectors:
                    for nid in narrative_by_naics.get(sector, []):
                        matched_narratives.add(nid)
        cascade["narrative_ids"] = sorted(matched_narratives)

    # Also set cascade dependencies on narratives
    for cascade in cascades:
        nids = cascade["narrative_ids"]
        if len(nids) >= 2:
            # First narrative is upstream, rest are downstream
            for n in narratives:
                if n["narrative_id"] == nids[0]:
                    n["cascade_dependencies"]["upstream_of"] = list(set(
                        n["cascade_dependencies"]["upstream_of"] + nids[1:]
                    ))
                elif n["narrative_id"] in nids[1:]:
                    n["cascade_dependencies"]["downstream_of"] = list(set(
                        n["cascade_dependencies"]["downstream_of"] + [nids[0]]
                    ))


def main():
    print("=" * 70)
    print("v4 MIGRATION: Generating v4 entities from v3 data")
    print("=" * 70)
    print()

    # Ensure output directory exists
    V4_DIR.mkdir(parents=True, exist_ok=True)

    # Load state
    print("Loading state.json...")
    with open(STATE_FILE) as f:
        state = json.load(f)
    print(f"  State version: {state.get('state_version')}")
    print(f"  Sector transformations: {len(state.get('sector_transformations', []))}")
    print(f"  Geographic profiles: {len(state.get('geographic_profiles', []))}")
    print(f"  Fear friction entries: {len(state.get('fear_friction_index', []))}")
    print()

    # Build fear friction lookup
    fear_friction_by_naics = {
        ff["sector_naics"]: ff
        for ff in state.get("fear_friction_index", [])
    }

    # Step 1: Generate force collisions
    print("Step 1: Generating force collisions...")
    collisions = generate_collisions(state)
    print(f"  Generated {len(collisions)} force collisions")
    # Collision type distribution
    type_dist = Counter(c["collision_type"] for c in collisions)
    print(f"  Types: {dict(type_dist)}")
    print()

    # Step 2: Generate transformation narratives
    print("Step 2: Generating transformation narratives...")
    narratives = generate_narratives(state, collisions, fear_friction_by_naics)
    print(f"  Generated {len(narratives)} transformation narratives")
    phase_dist = Counter(n["transformation_phase"] for n in narratives)
    print(f"  Phases: {dict(phase_dist)}")
    print()

    # Step 3: Generate cascade chains
    print("Step 3: Generating cascade chains...")
    cascades = generate_cascades()
    print(f"  Generated {len(cascades)} cascade chains")
    for c in cascades:
        print(f"    {c['cascade_id']}: {c['name'][:80]}... ({c['link_count']} links)")
    print()

    # Step 4: Link cascades to narratives
    print("Step 4: Linking cascades to narratives...")
    link_cascades_to_narratives(cascades, narratives)
    for c in cascades:
        print(f"    {c['cascade_id']} → narratives: {c['narrative_ids']}")
    print()

    # Step 5: Generate geographies
    print("Step 5: Generating geography profiles...")
    geographies = generate_geographies(state)
    print(f"  Generated {len(geographies)} geography profiles")
    for g in geographies:
        print(f"    {g['region_id']}: {g['demographic_profile'].get('population_trend', '?')}")
    print()

    # Step 6: Generate v4 state
    print("Step 6: Generating v4 engine state...")
    v4_state = {
        "state_version": 1,
        "engine_version": "4.0",
        "current_cycle": "v4-0",
        "engine_mode": "transformation_narrative",
        "description": (
            "v4.0 'Economy Map': Transformation-narrative-first architecture. "
            f"{len(narratives)} narratives, {len(collisions)} force collisions, "
            f"{len(cascades)} cascade chains, {len(geographies)} geographies. "
            "Migrated from v3-18 (650 models preserved with CLA/VCR scoring)."
        ),
        "force_velocities": state.get("force_velocities", {}),
        "migration_source": {
            "v3_state_version": state.get("state_version"),
            "v3_cycle": state.get("current_cycle"),
            "v3_models_count": 650,
            "migration_date": "2026-02-12",
        },
        "entity_counts": {
            "collisions": len(collisions),
            "narratives": len(narratives),
            "cascades": len(cascades),
            "geographies": len(geographies),
            "models": 0,  # Updated by narrative_linker
        },
    }

    # Write all files
    print()
    print("Writing v4 data files...")

    files = {
        V4_DIR / "collisions.json": {"collisions": collisions, "count": len(collisions)},
        V4_DIR / "narratives.json": {"narratives": narratives, "count": len(narratives)},
        V4_DIR / "cascades.json": {"cascades": cascades, "count": len(cascades)},
        V4_DIR / "geographies.json": {"geographies": geographies, "count": len(geographies)},
        V4_DIR / "state.json": v4_state,
    }

    for path, data in files.items():
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Written: {path}")

    # Summary
    print()
    print("=" * 70)
    print("v4 MIGRATION COMPLETE")
    print("=" * 70)
    print()
    print(f"  Force Collisions: {len(collisions)}")
    print(f"  Transformation Narratives: {len(narratives)}")
    print(f"  Cascade Chains: {len(cascades)}")
    print(f"  Geography Profiles: {len(geographies)}")
    print()
    print("  Next steps:")
    print("    1. Run scripts/v4_narrative_linker.py to link models to narratives")
    print("    2. Run scripts/v4_narrative_scoring.py to score narratives (TNS)")
    print("    3. Run scripts/v4_compile_ui.py to generate UI data")


if __name__ == "__main__":
    main()
