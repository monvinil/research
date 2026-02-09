#!/usr/bin/env python3
"""Research cycle runner.

This script orchestrates a single research cycle by coordinating
agent prompts and data flow. It reads the current state, prepares
agent inputs, and manages the data pipeline.

Designed to be called by the Master Agent or run manually.

Usage:
    python scripts/run_cycle.py --phase [scan|grade|verify|compile|full]
    python scripts/run_cycle.py --phase scan --directive "focus on healthcare"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


def load_state():
    path = os.path.join(DATA_DIR, 'context', 'state.json')
    with open(path) as f:
        return json.load(f)


def save_state(state):
    path = os.path.join(DATA_DIR, 'context', 'state.json')
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)


def load_json(subdir, filename):
    path = os.path.join(DATA_DIR, subdir, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_json(subdir, filename, data):
    path = os.path.join(DATA_DIR, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def update_ui(state, signals=None, opportunities=None):
    """Push current state to UI data files."""
    now = datetime.now(timezone.utc).isoformat()

    dashboard = {
        "last_updated": now,
        "current_cycle": state['current_cycle'],
        "total_signals_scanned": state['agent_performance']['agent_a']['signals_produced'],
        "total_opportunities_verified": state['agent_performance']['agent_b']['verifications_completed'],
        "active_opportunities": len(state['opportunity_pipeline'].get('verified', [])),
        "top_opportunities": opportunities or [],
        "sector_heatmap": {},
        "geography_heatmap": {},
        "cycle_history": []
    }
    save_json('ui', 'dashboard.json', dashboard)

    if signals:
        save_json('ui', 'signals_feed.json', {"recent_signals": signals[-50:]})


def init_cycle(state, directive=None):
    """Initialize a new research cycle."""
    state['current_cycle'] += 1
    cycle = state['current_cycle']
    now = datetime.now(timezone.utc).isoformat()

    print(f"=== CYCLE {cycle} INITIATED — {now} ===")
    print(f"Focus: {state['active_research_focus']}")
    if directive:
        print(f"Directive: {directive}")

    # Create cycle-specific signal file
    date_str = datetime.now().strftime('%Y-%m-%d')
    save_json('signals', f'{date_str}.json', {
        "cycle": cycle,
        "initiated": now,
        "directive": directive,
        "signals": []
    })

    save_state(state)
    update_ui(state)
    return state


def phase_scan(state, directive=None):
    """Prepare scanning phase — output the prompt for Agent A."""
    cycle = state['current_cycle']
    focus = state['active_research_focus']

    scan_directive = f"""SCAN DIRECTIVE [{cycle}]
Focus: {', '.join(focus.get('themes', []))}
Horizons: {', '.join(focus.get('horizons', []))}
Geographies: {', '.join(focus.get('geographies', []))}
Sources Priority: All 6 categories — broad initial scan
Keywords: agentic cost reduction, incumbent disruption, labor shortage, infrastructure overhang, dead business model, demographic gap
Exclusions: Pure SaaS tools, developer tooling, AI model training companies
"""
    if directive:
        scan_directive += f"\nAdditional Direction: {directive}\n"

    print("\n--- AGENT A SCANNING DIRECTIVE ---")
    print(scan_directive)
    print("--- END DIRECTIVE ---")
    print(f"\nAgent A should execute this directive and output signals to data/signals/{datetime.now().strftime('%Y-%m-%d')}.json")

    return scan_directive


def phase_grade(state):
    """Grade signals from the current cycle."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    signals_file = load_json('signals', f'{date_str}.json')

    if not signals_file or not signals_file.get('signals'):
        print("No signals to grade. Run scan phase first.")
        return

    signals = signals_file['signals']
    print(f"\n--- GRADING {len(signals)} SIGNALS ---")
    print("Agent C should grade these signals using the relevance scoring framework.")
    print(f"Signals file: data/signals/{date_str}.json")
    print(f"Output grades to: data/grades/{date_str}.json")


def phase_verify(state):
    """Prepare verification phase — select top signals for Agent B."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    grades_file = load_json('grades', f'{date_str}.json')

    if not grades_file:
        print("No graded signals. Run grade phase first.")
        return

    print("\n--- VERIFICATION PHASE ---")
    print("Agent B should verify top-graded signals.")
    print(f"Grades file: data/grades/{date_str}.json")
    print(f"Output to: data/verified/{date_str}.json")


def phase_compile(state):
    """Compile results and update UI."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    verified_file = load_json('verified', f'{date_str}.json')

    if not verified_file:
        print("No verified opportunities. Run verify phase first.")
        return

    print("\n--- COMPILATION PHASE ---")
    print("Agent C compiles final rankings and updates UI.")
    update_ui(state)
    save_state(state)
    print(f"Cycle {state['current_cycle']} complete.")


def main():
    parser = argparse.ArgumentParser(description='Run a research cycle phase')
    parser.add_argument('--phase', required=True,
                        choices=['init', 'scan', 'grade', 'verify', 'compile', 'full'],
                        help='Which phase to run')
    parser.add_argument('--directive', type=str, default=None,
                        help='Optional scanning directive override')
    args = parser.parse_args()

    state = load_state()

    if args.phase == 'init':
        init_cycle(state, args.directive)
    elif args.phase == 'scan':
        if state['current_cycle'] == 0:
            state = init_cycle(state, args.directive)
        phase_scan(state, args.directive)
    elif args.phase == 'grade':
        phase_grade(state)
    elif args.phase == 'verify':
        phase_verify(state)
    elif args.phase == 'compile':
        phase_compile(state)
    elif args.phase == 'full':
        state = init_cycle(state, args.directive)
        phase_scan(state, args.directive)
        phase_grade(state)
        phase_verify(state)
        phase_compile(state)


if __name__ == '__main__':
    main()
