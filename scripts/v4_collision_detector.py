#!/usr/bin/env python3
"""
v4 Collision Detector: Algorithmic collision detection from graded signals.

Takes graded signals (Agent C output) and:
1. Groups signals by force pair (F1×F2, F1×F3, etc.)
2. Matches to existing collisions in data/v4/collisions.json
3. Creates new collision hypotheses when force pairs have 2+ signals
4. Updates collision strength based on evidence accumulation
5. Detects cascade transmission signals (collision→collision propagation)

Input:  Graded signals (list of dicts with force_categories, collision_pair, etc.)
Output: collision_updates dict with strengthened/weakened/new collisions

Usage:
    from scripts.v4_collision_detector import detect_collisions
    updates = detect_collisions(graded_signals)

    # Or standalone:
    python scripts/v4_collision_detector.py data/signals/2026-02-12.json
"""

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data/v4"
COLLISIONS_FILE = V4_DIR / "collisions.json"
NARRATIVES_FILE = V4_DIR / "narratives.json"
STATE_FILE = V4_DIR / "state.json"

# Force IDs
FORCES = ["F1_technology", "F2_demographics", "F3_geopolitics",
          "F4_capital", "F5_psychology", "F6_energy"]

# Collision type inference rules
OPPOSING_PAIRS = {
    frozenset({"F1_technology", "F5_psychology"}),  # AI advances vs fear/resistance
    frozenset({"F1_technology", "F3_geopolitics"}),  # tech capability vs regulation
}


def load_collisions():
    """Load existing collisions from v4 data."""
    with open(COLLISIONS_FILE) as f:
        return json.load(f)


def load_narratives():
    """Load existing narratives from v4 data."""
    with open(NARRATIVES_FILE) as f:
        return json.load(f)


def extract_force_pairs(signal):
    """Extract force pair(s) from a signal.

    Checks explicit collision_pair first, then infers from force_categories.
    Returns list of frozensets, each a pair of force IDs.
    """
    pairs = []

    # Explicit collision pair
    cp = signal.get("collision_pair", [])
    if isinstance(cp, list) and len(cp) >= 2:
        # Validate force IDs
        valid = [f for f in cp if f in FORCES]
        if len(valid) >= 2:
            pairs.append(frozenset(valid[:2]))

    # Infer from force_categories (generate all pairs)
    fc = signal.get("force_categories", [])
    if isinstance(fc, list) and len(fc) >= 2:
        valid = [f for f in fc if f in FORCES]
        for pair in combinations(sorted(set(valid)), 2):
            p = frozenset(pair)
            if p not in pairs:
                pairs.append(p)

    return pairs


def pair_key(pair):
    """Convert a frozenset pair to a stable string key."""
    return " × ".join(sorted(pair))


def match_collision(pair, sectors, existing_collisions):
    """Match a force pair + sector to an existing collision.

    Returns collision_id if matched, None otherwise.
    """
    pair_set = frozenset(pair) if not isinstance(pair, frozenset) else pair

    for coll in existing_collisions:
        coll_forces = frozenset(f["force_id"] for f in coll.get("forces", []))
        if pair_set == coll_forces:
            # Force pair matches — check sector overlap
            coll_sectors = set(coll.get("sectors_affected", []))
            if not sectors or not coll_sectors:
                return coll["collision_id"]
            if set(sectors) & coll_sectors:
                return coll["collision_id"]

    return None


def infer_collision_type(pair):
    """Infer collision type from force pair."""
    if pair in OPPOSING_PAIRS:
        return "opposing"
    return "amplifying"


def detect_collisions(graded_signals, min_signals_for_new=2):
    """Main collision detection algorithm.

    Args:
        graded_signals: List of signal dicts from Agent C
        min_signals_for_new: Minimum signals to create a new collision hypothesis

    Returns:
        dict with:
            - strengthened: [{collision_id, signal_count, new_strength, signals}]
            - weakened: [{collision_id, reason}]
            - new_hypotheses: [{force_pair, sectors, signal_count, signals, suggested_name}]
            - cascade_signals: [{from_collision, to_collision, mechanism, signal}]
            - narrative_matches: [{narrative_id, signal_count, signals}]
            - stats: {total_signals, collision_signals, single_force, unmatched}
    """
    coll_data = load_collisions()
    existing = coll_data.get("collisions", [])
    narr_data = load_narratives()
    narratives = narr_data.get("narratives", [])

    # Build lookup indices
    coll_by_id = {c["collision_id"]: c for c in existing}
    narr_by_id = {n["narrative_id"]: n for n in narratives}

    # Group signals by force pair
    pair_signals = defaultdict(list)  # pair_key → [signal, ...]
    pair_sectors = defaultdict(set)    # pair_key → {naics, ...}
    cascade_signals = []
    single_force_signals = []
    unmatched = []

    stats = {
        "total_signals": len(graded_signals),
        "collision_signals": 0,
        "single_force": 0,
        "unmatched": 0,
        "cascade_detected": 0,
    }

    for signal in graded_signals:
        sig_type = signal.get("signal_type", "")

        # Handle cascade transmission signals separately
        if sig_type == "cascade_transmission":
            cascade_signals.append(signal)
            stats["cascade_detected"] += 1
            continue

        # Extract force pairs
        pairs = extract_force_pairs(signal)

        if not pairs:
            # Check if single-force signal
            fc = signal.get("force_categories", [])
            if isinstance(fc, list) and len(fc) == 1:
                single_force_signals.append(signal)
                stats["single_force"] += 1
            else:
                unmatched.append(signal)
                stats["unmatched"] += 1
            continue

        stats["collision_signals"] += 1

        # Assign to pair groups
        for pair in pairs:
            pk = pair_key(pair)
            pair_signals[pk].append(signal)

            # Extract sectors
            sector = signal.get("collision_transmission_path", {}).get("sector_naics", "")
            if sector:
                pair_sectors[pk].add(sector)
            geo_scope = signal.get("geographic_scope", [])
            if isinstance(geo_scope, list):
                for g in geo_scope:
                    if g not in ("Global", "US"):
                        pair_sectors[pk].add(g)

    # Match pairs to existing collisions
    strengthened = defaultdict(list)  # collision_id → [signal, ...]
    new_hypotheses = defaultdict(list)  # pair_key → [signal, ...]
    new_sectors = defaultdict(set)

    for pk, signals in pair_signals.items():
        pair_forces = frozenset(pk.split(" × "))
        sectors = list(pair_sectors.get(pk, []))

        coll_id = match_collision(pair_forces, sectors, existing)
        if coll_id:
            strengthened[coll_id].extend(signals)
        else:
            new_hypotheses[pk].extend(signals)
            new_sectors[pk].update(sectors)

    # Build strengthened output
    strengthened_out = []
    for coll_id, signals in strengthened.items():
        # Calculate new strength based on signal count + quality
        avg_score = sum(s.get("relevance_score", 5) for s in signals) / max(len(signals), 1)
        strength = "emerging"
        if len(signals) >= 5 and avg_score >= 7:
            strength = "strong"
        elif len(signals) >= 3 or avg_score >= 6:
            strength = "moderate"

        strengthened_out.append({
            "collision_id": coll_id,
            "collision_name": coll_by_id.get(coll_id, {}).get("name", ""),
            "signal_count": len(signals),
            "avg_signal_score": round(avg_score, 1),
            "strength": strength,
            "signal_ids": [s.get("signal_id", "") for s in signals],
            "signal_headlines": [s.get("headline", "")[:100] for s in signals[:5]],
        })

    strengthened_out.sort(key=lambda x: x["signal_count"], reverse=True)

    # Build new hypothesis output (only if enough signals)
    new_out = []
    for pk, signals in new_hypotheses.items():
        if len(signals) < min_signals_for_new:
            continue

        pair_forces = pk.split(" × ")
        sectors = list(new_sectors.get(pk, []))
        coll_type = infer_collision_type(frozenset(pair_forces))

        # Generate a name
        force_names = [f.replace("F1_", "").replace("F2_", "").replace("F3_", "")
                       .replace("F4_", "").replace("F5_", "").replace("F6_", "")
                       .replace("_", " ").title()
                       for f in sorted(pair_forces)]
        sector_hint = sectors[0] if sectors else "cross-sector"
        name = f"{force_names[0]} + {force_names[1]} in {sector_hint}"

        new_out.append({
            "force_pair": sorted(pair_forces),
            "pair_key": pk,
            "collision_type": coll_type,
            "sectors": sectors,
            "signal_count": len(signals),
            "suggested_name": name,
            "signal_ids": [s.get("signal_id", "") for s in signals],
            "signal_headlines": [s.get("headline", "")[:100] for s in signals[:5]],
        })

    new_out.sort(key=lambda x: x["signal_count"], reverse=True)

    # Process cascade signals
    cascade_out = []
    for signal in cascade_signals:
        ctp = signal.get("collision_transmission_path", {})
        downstream = ctp.get("cascade_downstream", [])
        coll_ref = signal.get("collision_id_ref", "")
        narr_ref = signal.get("narrative_id_ref", "")

        cascade_out.append({
            "from_collision": coll_ref,
            "from_narrative": narr_ref,
            "downstream": downstream,
            "mechanism": ctp.get("transformation_direction", ""),
            "signal_id": signal.get("signal_id", ""),
            "headline": signal.get("headline", ""),
        })

    # Match signals to narratives
    narrative_matches = defaultdict(list)
    for coll_id, signals in strengthened.items():
        # Find narratives that reference this collision
        for narr in narratives:
            if coll_id in narr.get("collision_ids", []):
                narrative_matches[narr["narrative_id"]].extend(signals)

    narr_match_out = []
    for narr_id, signals in narrative_matches.items():
        # Deduplicate
        seen = set()
        unique = []
        for s in signals:
            sid = s.get("signal_id", id(s))
            if sid not in seen:
                seen.add(sid)
                unique.append(s)

        narr_match_out.append({
            "narrative_id": narr_id,
            "narrative_name": narr_by_id.get(narr_id, {}).get("name", ""),
            "signal_count": len(unique),
            "signal_ids": [s.get("signal_id", "") for s in unique],
        })

    narr_match_out.sort(key=lambda x: x["signal_count"], reverse=True)

    return {
        "strengthened": strengthened_out,
        "weakened": [],  # Populated by staleness check (separate logic)
        "new_hypotheses": new_out,
        "cascade_signals": cascade_out,
        "narrative_matches": narr_match_out,
        "single_force_signals": len(single_force_signals),
        "stats": stats,
    }


def staleness_check(collisions_data, state_data, max_cycles_stale=3):
    """Check for collisions that haven't received evidence in N cycles.

    Returns list of weakened collision dicts.
    """
    current_cycle = state_data.get("current_cycle", "v4-0")
    # Parse cycle number (e.g., "v4-2" → 2)
    try:
        cycle_num = int(current_cycle.split("-")[-1])
    except (ValueError, IndexError):
        cycle_num = 0

    weakened = []
    for coll in collisions_data.get("collisions", []):
        last_update = coll.get("last_evidence_cycle", "v4-0")
        try:
            last_num = int(last_update.split("-")[-1])
        except (ValueError, IndexError):
            last_num = 0

        if cycle_num - last_num >= max_cycles_stale:
            weakened.append({
                "collision_id": coll["collision_id"],
                "collision_name": coll.get("name", ""),
                "cycles_stale": cycle_num - last_num,
                "reason": f"No evidence for {cycle_num - last_num} cycles",
            })

    return weakened


def apply_collision_updates(updates, dry_run=False):
    """Apply collision updates to data/v4/collisions.json.

    Updates last_evidence_cycle for strengthened collisions.
    Does NOT create new collisions automatically (requires Agent C review).

    Returns summary of changes.
    """
    coll_data = load_collisions()
    state_data = json.loads(STATE_FILE.read_text())
    current_cycle = state_data.get("current_cycle", "v4-0")

    changes = []

    # Update strengthened collisions
    coll_by_id = {c["collision_id"]: c for c in coll_data["collisions"]}
    for s in updates.get("strengthened", []):
        coll_id = s["collision_id"]
        if coll_id in coll_by_id:
            coll = coll_by_id[coll_id]
            old_cycle = coll.get("last_evidence_cycle", "")
            coll["last_evidence_cycle"] = current_cycle
            coll["last_signal_count"] = s["signal_count"]
            coll["last_strength"] = s["strength"]
            changes.append(f"  Updated {coll_id}: {old_cycle} → {current_cycle} "
                           f"({s['signal_count']} signals, {s['strength']})")

    # Staleness check
    weakened = staleness_check(coll_data, state_data)
    for w in weakened:
        changes.append(f"  STALE {w['collision_id']}: {w['reason']}")

    if not dry_run:
        with open(COLLISIONS_FILE, "w") as f:
            json.dump(coll_data, f, indent=2, ensure_ascii=False)

    return {
        "updated_count": len(updates.get("strengthened", [])),
        "stale_count": len(weakened),
        "new_hypothesis_count": len(updates.get("new_hypotheses", [])),
        "changes": changes,
    }


def print_report(updates):
    """Print a human-readable collision detection report."""
    stats = updates["stats"]

    print("=" * 70)
    print("v4 COLLISION DETECTOR REPORT")
    print("=" * 70)
    print()
    print(f"  Total signals processed: {stats['total_signals']}")
    print(f"  Collision signals (2+ forces): {stats['collision_signals']}")
    print(f"  Single-force signals: {stats['single_force']}")
    print(f"  Cascade transmission: {stats['cascade_detected']}")
    print(f"  Unmatched: {stats['unmatched']}")
    print()

    # Strengthened
    strengthened = updates["strengthened"]
    if strengthened:
        print(f"  STRENGTHENED COLLISIONS ({len(strengthened)}):")
        for s in strengthened:
            print(f"    {s['collision_id']:>8}  {s['signal_count']:2d} signals  "
                  f"[{s['strength']:>8}]  {s['collision_name'][:50]}")
        print()

    # New hypotheses
    new = updates["new_hypotheses"]
    if new:
        print(f"  NEW COLLISION HYPOTHESES ({len(new)}):")
        for n in new:
            print(f"    {n['pair_key']:<35}  {n['signal_count']:2d} signals  "
                  f"[{n['collision_type']}]")
            for h in n["signal_headlines"][:2]:
                print(f"      - {h}")
        print()

    # Cascade
    cascades = updates["cascade_signals"]
    if cascades:
        print(f"  CASCADE TRANSMISSIONS ({len(cascades)}):")
        for c in cascades:
            print(f"    {c['from_collision'] or c['from_narrative']} → "
                  f"{', '.join(c['downstream'][:3])}")
            print(f"      {c['headline'][:80]}")
        print()

    # Narrative matches
    narr_matches = updates["narrative_matches"]
    if narr_matches:
        print(f"  NARRATIVE EVIDENCE ({len(narr_matches)} narratives with new signals):")
        for nm in narr_matches[:10]:
            print(f"    {nm['narrative_id']:>8}  {nm['signal_count']:2d} signals  "
                  f"{nm['narrative_name'][:50]}")
        print()


def main():
    """Standalone mode: process a signals JSON file."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/v4_collision_detector.py <signals_file.json>")
        print("       python scripts/v4_collision_detector.py --demo")
        sys.exit(1)

    if sys.argv[1] == "--demo":
        # Demo with synthetic signals
        demo_signals = [
            {
                "signal_id": "A-2026-02-12-001",
                "force_categories": ["F1_technology", "F2_demographics"],
                "collision_pair": ["F1_technology", "F2_demographics"],
                "signal_type": "collision_evidence",
                "headline": "Cobot deployments surge 40% in aging-workforce manufacturing plants",
                "relevance_score": 8,
                "collision_transmission_path": {"sector_naics": "31-33"},
            },
            {
                "signal_id": "A-2026-02-12-002",
                "force_categories": ["F1_technology", "F4_capital"],
                "collision_pair": ["F1_technology", "F4_capital"],
                "signal_type": "collision_evidence",
                "headline": "PE-backed accounting firms face margin squeeze from AI competitors",
                "relevance_score": 7,
                "collision_transmission_path": {"sector_naics": "52"},
            },
            {
                "signal_id": "A-2026-02-12-003",
                "force_categories": ["F1_technology"],
                "signal_type": "force_velocity",
                "headline": "Inference costs drop another 3x in Q1 2026",
                "relevance_score": 9,
            },
            {
                "signal_id": "A-2026-02-12-004",
                "force_categories": ["F1_technology", "F2_demographics"],
                "signal_type": "collision_evidence",
                "headline": "Silver Tsunami: 15% of manufacturing owners retired in 2025",
                "relevance_score": 8,
                "collision_transmission_path": {"sector_naics": "31-33"},
            },
            {
                "signal_id": "A-2026-02-12-005",
                "signal_type": "cascade_transmission",
                "headline": "Financial services AI adoption cascading to CRE vacancy rates",
                "collision_id_ref": "FC-001",
                "narrative_id_ref": "TN-001",
                "collision_transmission_path": {
                    "cascade_downstream": ["TN-012"],
                    "transformation_direction": "AI reduces headcount → office demand drops",
                },
            },
        ]
        signals = demo_signals
    else:
        signals_path = Path(sys.argv[1])
        if not signals_path.exists():
            print(f"File not found: {signals_path}")
            sys.exit(1)
        with open(signals_path) as f:
            data = json.load(f)
        signals = data if isinstance(data, list) else data.get("graded_signals", data.get("signals", []))

    updates = detect_collisions(signals)
    print_report(updates)

    # Apply updates if not demo
    if sys.argv[1] != "--demo":
        result = apply_collision_updates(updates, dry_run=True)
        print(f"\n  DRY RUN: Would update {result['updated_count']} collisions, "
              f"{result['stale_count']} stale, {result['new_hypothesis_count']} new hypotheses")
        print("  Run with --apply to write changes.")

        if len(sys.argv) > 2 and sys.argv[2] == "--apply":
            result = apply_collision_updates(updates, dry_run=False)
            print(f"\n  APPLIED: {result['updated_count']} collisions updated.")
            for c in result["changes"]:
                print(c)


if __name__ == "__main__":
    main()
