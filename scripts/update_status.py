#!/usr/bin/env python3
"""Write consolidated task status for the ops UI.

Scans data/tasks/{pending,running,complete,failed}/ directories
and writes data/tasks/status.json with aggregated status.

Called by dispatch.py after task state changes, or can be run standalone.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent
TASKS_DIR = BASE_DIR / 'data' / 'tasks'


def update_status():
    status = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'pending': [],
        'running': [],
        'completed': [],
        'failed': [],
        'counts': {'pending': 0, 'running': 0, 'completed': 0, 'failed': 0},
    }

    for state in ['pending', 'running', 'complete', 'failed']:
        dir_path = TASKS_DIR / state
        if not dir_path.exists():
            continue

        tasks = []
        for f in sorted(dir_path.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(f) as fh:
                    task = json.load(fh)
                    tasks.append({
                        'task_id': task.get('task_id', f.stem),
                        'task_type': task.get('task_type', 'unknown'),
                        'description': task.get('description', ''),
                        'status': task.get('status', state),
                        'created_at': task.get('created_at', ''),
                        'started_at': task.get('started_at', ''),
                        'completed_at': task.get('completed_at', ''),
                        'error': task.get('error', ''),
                        'priority': task.get('priority', 5),
                    })
            except (json.JSONDecodeError, OSError):
                continue

        # Map 'complete' dir to 'completed' key
        key = 'completed' if state == 'complete' else state
        status[key] = tasks[:50]  # Cap at 50 per category
        status['counts'][key] = len(tasks)

    # Write status file
    status_file = TASKS_DIR / 'status.json'
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

    return status


if __name__ == '__main__':
    s = update_status()
    print(f"Status updated: {s['counts']}")
