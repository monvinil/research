#!/usr/bin/env python3
"""
Parallel Task Dispatcher for AI Economic Research Engine

Coordinates multiple Claude Code sessions working simultaneously on
different research tasks. Uses file-based task queue for coordination.

Usage:
    python scripts/dispatch.py --cycle
    python scripts/dispatch.py --phase scan
    python scripts/dispatch.py --status
    python scripts/dispatch.py --cleanup
    python scripts/dispatch.py --explore "veterinary" "translation" "surveying"
"""

import json
import os
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TASKS_DIR = BASE_DIR / 'data' / 'tasks'
PENDING_DIR = TASKS_DIR / 'pending'
RUNNING_DIR = TASKS_DIR / 'running'
COMPLETE_DIR = TASKS_DIR / 'complete'
FAILED_DIR = TASKS_DIR / 'failed'
RESULTS_DIR = BASE_DIR / 'data' / 'results'
CONTEXT_DIR = BASE_DIR / 'data' / 'context'
STATE_FILE = CONTEXT_DIR / 'state.json'

for d in [PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'cycle_number': 0}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def create_task(task_type, description, payload, dependencies=None, priority=5):
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    task_id = f"{task_type}-{timestamp}-{os.getpid()}"
    task = {
        'task_id': task_id,
        'task_type': task_type,
        'description': description,
        'payload': payload,
        'dependencies': dependencies or [],
        'priority': priority,
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'started_at': None,
        'completed_at': None,
    }
    with open(PENDING_DIR / f"{task_id}.json", 'w') as f:
        json.dump(task, f, indent=2)
    return task_id


def claim_task(task_id):
    src = PENDING_DIR / f"{task_id}.json"
    dst = RUNNING_DIR / f"{task_id}.json"
    with open(src) as f:
        task = json.load(f)
    task['status'] = 'running'
    task['started_at'] = datetime.now(timezone.utc).isoformat()
    with open(dst, 'w') as f:
        json.dump(task, f, indent=2)
    src.unlink()
    return task


def complete_task(task_id, result):
    src = RUNNING_DIR / f"{task_id}.json"
    dst = COMPLETE_DIR / f"{task_id}.json"
    with open(src) as f:
        task = json.load(f)
    task['status'] = 'completed'
    task['completed_at'] = datetime.now(timezone.utc).isoformat()
    with open(dst, 'w') as f:
        json.dump(task, f, indent=2)
    with open(RESULTS_DIR / f"{task_id}.json", 'w') as f:
        json.dump(result, f, indent=2)
    src.unlink()


def fail_task(task_id, error):
    src = RUNNING_DIR / f"{task_id}.json"
    dst = FAILED_DIR / f"{task_id}.json"
    if src.exists():
        with open(src) as f:
            task = json.load(f)
        task['status'] = 'failed'
        task['error'] = error
        task['completed_at'] = datetime.now(timezone.utc).isoformat()
        with open(dst, 'w') as f:
            json.dump(task, f, indent=2)
        src.unlink()


def get_status():
    def list_tasks(d):
        tasks = []
        for f in sorted(d.glob('*.json')):
            with open(f) as fh:
                t = json.load(fh)
                tasks.append({
                    'task_id': t['task_id'], 'type': t['task_type'],
                    'description': t['description'], 'status': t['status'],
                    'created': t.get('created_at', ''),
                    'started': t.get('started_at', ''),
                    'completed': t.get('completed_at', ''),
                    'error': t.get('error', ''),
                    'priority': t.get('priority', 5),
                })
        return tasks

    return {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'counts': {
            'pending': len(list(PENDING_DIR.glob('*.json'))),
            'running': len(list(RUNNING_DIR.glob('*.json'))),
            'completed': len(list(COMPLETE_DIR.glob('*.json'))),
            'failed': len(list(FAILED_DIR.glob('*.json'))),
        },
        'pending': list_tasks(PENDING_DIR),
        'running': list_tasks(RUNNING_DIR),
        'completed': list_tasks(COMPLETE_DIR)[:50],
        'failed': list_tasks(FAILED_DIR),
    }


def write_status_json():
    """Write consolidated status.json for the ops UI."""
    status = get_status()
    status_file = TASKS_DIR / 'status.json'
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)
    return status


def dispatch_scan_phase():
    state = load_state()
    cycle = state.get('cycle_number', 0) + 1
    sources = [
        ('fred', 'Fetch FRED economic data (labor, credit, profitability, stress, costs, small biz, assets)'),
        ('bls', 'Fetch BLS employment data (industry, wages, openings, occupational exposure)'),
        ('edgar', 'Fetch SEC EDGAR filings (distress, AI risk, sector distress)'),
        ('websearch', 'Fetch web search (liquidation, pain, revival, demographics, inference costs)'),
    ]
    task_ids = []
    for source, desc in sources:
        tid = create_task('scan', f"Cycle {cycle}: {desc}",
                         {'source': source, 'cycle_number': cycle}, priority=1)
        task_ids.append(tid)
        print(f"  Created: {tid}")
    write_status_json()
    return task_ids


def dispatch_agent_a():
    state = load_state()
    cycle = state.get('cycle_number', 0) + 1
    tid = create_task('agent-a', f"Cycle {cycle}: Extract signals from raw data",
                     {'cycle_number': cycle, 'agent_prompt_path': 'agents/agent_a_trends_scanner.md'}, priority=2)
    print(f"  Created: {tid}")
    write_status_json()
    return tid


def dispatch_counter_signals(signals_path):
    full_path = BASE_DIR / signals_path
    if not full_path.exists():
        print(f"  Warning: {signals_path} not found")
        return []
    with open(full_path) as f:
        data = json.load(f)
    high = [s for s in (data if isinstance(data, list) else [])
            if isinstance(s, dict) and s.get('relevance_score', 0) >= 7.0]
    task_ids = []
    for i in range(0, len(high), 3):
        batch = high[i:i+3]
        tid = create_task('counter-signal',
                         f"Counter-evidence for {len(batch)} signals (batch {i//3+1})",
                         {'signals': batch}, priority=3)
        task_ids.append(tid)
        print(f"  Created: {tid}")
    write_status_json()
    return task_ids


def dispatch_agent_b_parallel(opportunities_path=None):
    opportunities = []
    if opportunities_path:
        p = BASE_DIR / opportunities_path
        if p.exists():
            with open(p) as f:
                d = json.load(f)
                opportunities = d if isinstance(d, list) else d.get('opportunities', d.get('opportunity_clusters', []))
    task_ids = []
    for i, opp in enumerate(opportunities):
        name = opp.get('name', opp.get('headline', f'opp_{i+1}'))
        tid = create_task('agent-b', f"Verify: {name}",
                         {'opportunity': opp, 'index': i}, priority=4)
        task_ids.append(tid)
        print(f"  Created: {tid} -- {name}")
    write_status_json()
    return task_ids


def dispatch_sector_exploration(sectors):
    task_ids = []
    for sector in sectors:
        tid = create_task('explore', f"Deep-dive: {sector}",
                         {'sector': sector}, priority=6)
        task_ids.append(tid)
        print(f"  Created: {tid}")
    write_status_json()
    return task_ids


def dispatch_full_cycle():
    state = load_state()
    cycle = state.get('cycle_number', 0) + 1
    print(f"\n{'='*60}")
    print(f"  DISPATCHING CYCLE {cycle}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    print("Phase 1: Data Fetch (4 parallel tasks)")
    scan_ids = dispatch_scan_phase()

    print(f"\nPhase 2: Agent A (depends on Phase 1)")
    a_id = dispatch_agent_a()

    print(f"\nPhase 3: Agent C Grading (depends on Phase 2)")
    c_id = create_task('agent-c', f"Cycle {cycle}: Grade and cluster signals",
                      {'cycle_number': cycle}, dependencies=[a_id], priority=3)
    print(f"  Created: {c_id}")

    print(f"\nPhase 5: Master Synthesis (depends on all)")
    m_id = create_task('master', f"Cycle {cycle}: Master synthesis",
                      {'cycle_number': cycle}, dependencies=[c_id], priority=5)
    print(f"  Created: {m_id}")

    state['cycle_number'] = cycle
    state['last_dispatch'] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    write_status_json()

    print(f"\n{'='*60}")
    print(f"  Cycle {cycle} dispatched. {len(scan_ids) + 3} tasks created.")
    print(f"{'='*60}\n")


def cleanup(max_age_hours=72):
    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for d in [COMPLETE_DIR, FAILED_DIR]:
        for f in d.glob('*.json'):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
    print(f"Cleaned up {removed} old task files")
    write_status_json()


def main():
    parser = argparse.ArgumentParser(description='Parallel Task Dispatcher')
    parser.add_argument('--cycle', action='store_true', help='Dispatch full cycle')
    parser.add_argument('--phase', choices=['scan', 'agent-a', 'agent-b-parallel', 'counter-signals'])
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--cleanup', action='store_true', help='Clean old tasks')
    parser.add_argument('--explore', nargs='+', help='Sector exploration')
    args = parser.parse_args()

    if args.status:
        s = get_status()
        print(f"\nTask Queue: P:{s['counts']['pending']} R:{s['counts']['running']} "
              f"C:{s['counts']['completed']} F:{s['counts']['failed']}")
        for t in s['pending']:
            print(f"  [pending] [{t['type']}] {t['description']}")
        for t in s['running']:
            print(f"  [running] [{t['type']}] {t['description']}")
        write_status_json()
    elif args.cycle:
        dispatch_full_cycle()
    elif args.phase == 'scan':
        dispatch_scan_phase()
    elif args.phase == 'agent-a':
        dispatch_agent_a()
    elif args.explore:
        dispatch_sector_exploration(args.explore)
    elif args.cleanup:
        cleanup()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
