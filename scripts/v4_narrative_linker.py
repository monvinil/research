#!/usr/bin/env python3
"""
v4 Narrative Linker: Link 650 business models to transformation narratives.

Reads:
  - data/v4/narratives.json
  - data/verified/v3-12_normalized_2026-02-12.json (650 models)

Writes:
  - data/v4/models.json (650 models with narrative_ids + narrative_role)
  - Updates data/v4/narratives.json (outputs.what_works/whats_needed/what_dies)

Linking logic:
  1. Match models to narratives by sector_naics overlap
  2. Match by forces_v3 overlap with narrative's forces
  3. Assign narrative_role based on category + architecture heuristics
"""

import json
from pathlib import Path
from collections import Counter

BASE = Path("/Users/mv/Documents/research")
NORMALIZED_FILE = BASE / "data/verified/v3-12_normalized_2026-02-12.json"
V4_DIR = BASE / "data/v4"
NARRATIVES_FILE = V4_DIR / "narratives.json"

# Architecture → narrative role mapping
NEEDS_ARCHITECTURES = {
    "platform_infrastructure", "coordination_protocol", "open_core_ecosystem",
    "compliance_automation", "regulatory_moat_builder",
}

DIES_CATEGORIES = {
    "PARKED",
}

# Models with these primary_category are strong evidence for "what works"
WORKS_CATEGORIES = {
    "STRUCTURAL_WINNER", "TIMING_ARBITRAGE", "CAPITAL_MOAT",
}


def naics_match(model_naics, narrative_naics_list):
    """Check if a model's sector matches any narrative sector.
    Handles prefix matching: model 5415 matches narrative 54.
    """
    if not model_naics:
        return False
    for n_naics in narrative_naics_list:
        if not n_naics:
            continue
        # Exact match
        if model_naics == n_naics:
            return True
        # Prefix match: model 5415 matches narrative 54
        if model_naics.startswith(n_naics):
            return True
        # Prefix match: narrative 5415 matches model 54
        if n_naics.startswith(model_naics):
            return True
        # Handle range NAICS like "31-33" or "44-45"
        if "-" in n_naics:
            parts = n_naics.split("-")
            try:
                lo, hi = int(parts[0]), int(parts[1])
                model_prefix = int(model_naics[:2])
                if lo <= model_prefix <= hi:
                    return True
            except (ValueError, IndexError):
                pass
    return False


def force_overlap(model_forces, narrative_forces):
    """Count how many forces overlap between model and narrative."""
    if not model_forces or not narrative_forces:
        return 0
    return len(set(model_forces) & set(narrative_forces))


def assign_role(model, matched_narratives):
    """Assign narrative_role based on model characteristics."""
    primary_cat = model.get("primary_category", "")
    categories = model.get("category", [])
    if isinstance(categories, str):
        categories = [categories]
    arch = model.get("architecture", "")

    # What dies: PARKED models
    if primary_cat in DIES_CATEGORIES or "PARKED" in categories:
        return "what_dies"

    # What's needed: infrastructure/platform architectures
    if arch in NEEDS_ARCHITECTURES:
        return "whats_needed"

    # What works: structural winners, timing plays, high composite
    if primary_cat in WORKS_CATEGORIES or any(c in WORKS_CATEGORIES for c in categories):
        return "what_works"

    # Default based on composite
    composite = model.get("composite", 0)
    if composite >= 70:
        return "what_works"
    elif composite >= 55:
        return "what_works"  # Most models are evidence of what works
    else:
        return "what_dies"


def main():
    print("=" * 70)
    print("v4 NARRATIVE LINKER: Linking models to transformation narratives")
    print("=" * 70)
    print()

    # Load narratives
    print("Loading narratives...")
    with open(NARRATIVES_FILE) as f:
        narr_data = json.load(f)
    narratives = narr_data["narratives"]
    print(f"  {len(narratives)} narratives loaded")

    # Load models
    print("Loading models...")
    with open(NORMALIZED_FILE) as f:
        model_data = json.load(f)
    models = model_data["models"]
    print(f"  {len(models)} models loaded")
    print()

    # Build narrative lookup
    narrative_sectors = {}
    narrative_forces = {}
    for n in narratives:
        nid = n["narrative_id"]
        narrative_sectors[nid] = [s["naics"] for s in n.get("sectors", [])]
        narrative_forces[nid] = n.get("forces_acting", [])

    # Link models to narratives
    print("Linking models to narratives...")
    linked_count = 0
    unlinked = []
    role_dist = Counter()

    # Reset narrative outputs
    for n in narratives:
        n["outputs"] = {"what_works": [], "whats_needed": [], "what_dies": []}

    for m in models:
        model_naics = m.get("sector_naics", "")
        model_forces = m.get("forces_v3", [])
        model_id = m["id"]

        # Find matching narratives
        matches = []
        for n in narratives:
            nid = n["narrative_id"]
            n_sectors = narrative_sectors[nid]
            n_forces = narrative_forces[nid]

            sector_match = naics_match(model_naics, n_sectors)
            f_overlap = force_overlap(model_forces, n_forces)

            if sector_match and f_overlap >= 1:
                matches.append((nid, f_overlap + 2))  # sector + force match = strong
            elif sector_match:
                matches.append((nid, 1))  # sector only
            elif f_overlap >= 2:
                matches.append((nid, f_overlap))  # strong force overlap

        if matches:
            # Sort by match strength, take top matches
            matches.sort(key=lambda x: -x[1])
            m["narrative_ids"] = [mid for mid, _ in matches[:3]]  # max 3 narratives
            role = assign_role(m, matches)
            m["narrative_role"] = role
            role_dist[role] += 1

            # Add model to narrative outputs
            for nid, _ in matches[:3]:
                for n in narratives:
                    if n["narrative_id"] == nid:
                        if model_id not in n["outputs"].get(role, []):
                            n["outputs"].setdefault(role, []).append(model_id)
                        break

            linked_count += 1
        else:
            # No match — try to link to the most general narrative by force overlap
            best_force_match = None
            best_overlap = 0
            for n in narratives:
                nid = n["narrative_id"]
                f_ov = force_overlap(model_forces, narrative_forces[nid])
                if f_ov > best_overlap:
                    best_overlap = f_ov
                    best_force_match = nid

            if best_force_match:
                m["narrative_ids"] = [best_force_match]
                role = assign_role(m, [(best_force_match, best_overlap)])
                m["narrative_role"] = role
                role_dist[role] += 1

                for n in narratives:
                    if n["narrative_id"] == best_force_match:
                        n["outputs"].setdefault(role, []).append(model_id)
                        break

                linked_count += 1
            else:
                m["narrative_ids"] = []
                m["narrative_role"] = "unlinked"
                unlinked.append(model_id)
                role_dist["unlinked"] += 1

    print(f"  Linked: {linked_count}/{len(models)}")
    print(f"  Unlinked: {len(unlinked)}")
    print(f"  Roles: {dict(role_dist)}")
    print()

    # Show narrative model counts
    print("Narrative model counts:")
    for n in sorted(narratives, key=lambda x: sum(len(v) for v in x["outputs"].values()), reverse=True):
        works = len(n["outputs"].get("what_works", []))
        needed = len(n["outputs"].get("whats_needed", []))
        dies = len(n["outputs"].get("what_dies", []))
        total = works + needed + dies
        print(f"  {n['narrative_id']}  {n['name'][:45]:45s}  total={total:3d}  works={works}  needed={needed}  dies={dies}")

    if unlinked:
        print(f"\n  Unlinked models ({len(unlinked)}):")
        for mid in unlinked[:10]:
            m = next(x for x in models if x["id"] == mid)
            print(f"    {mid}: naics={m.get('sector_naics')}, forces={m.get('forces_v3')}")

    # Write updated files
    print()
    print("Writing updated files...")

    # Write models
    v4_models = {
        "models": models,
        "count": len(models),
        "linked_count": linked_count,
        "unlinked_count": len(unlinked),
        "role_distribution": dict(role_dist),
    }
    with open(V4_DIR / "models.json", "w") as f:
        json.dump(v4_models, f, indent=2, ensure_ascii=False)
    print(f"  Written: {V4_DIR / 'models.json'} ({len(models)} models)")

    # Write updated narratives
    narr_data["narratives"] = narratives
    with open(NARRATIVES_FILE, "w") as f:
        json.dump(narr_data, f, indent=2, ensure_ascii=False)
    print(f"  Written: {NARRATIVES_FILE} (updated outputs)")

    # Update v4 state
    state_file = V4_DIR / "state.json"
    with open(state_file) as f:
        state = json.load(f)
    state["entity_counts"]["models"] = len(models)
    state["entity_counts"]["models_linked"] = linked_count
    state["entity_counts"]["models_unlinked"] = len(unlinked)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  Written: {state_file} (updated counts)")

    print()
    print("=" * 70)
    print("NARRATIVE LINKING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
