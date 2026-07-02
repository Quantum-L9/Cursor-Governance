"""Graph-backed session restore (replaces JSON load in show_context.sh).

Queries the L9 graph for currently-valid, task-relevant context instead of
loading the last 7-day JSON blob. Cold-start becomes relational, not narrative.
"""
from __future__ import annotations

import json
import subprocess
import sys


def restore(task_type: str = "current active projects and open decisions") -> None:
    payload = {"query": task_type, "group_ids": None, "limit": 10}
    proc = subprocess.run(
        ["python", "-m", "l9_ops_mcp.cli", "query", json.dumps(payload)],
        capture_output=True, text=True,
    )
    try:
        facts = json.loads(proc.stdout).get("facts", [])
    except json.JSONDecodeError:
        print("No graph context available (fallback to JSON).")
        return
    print("=" * 60)
    print("LAST SESSION CONTEXT (graph-derived)")
    print("=" * 60)
    for f in facts:
        print(f"  - {f['fact']}")
    print("=" * 60)


if __name__ == "__main__":
    restore(sys.argv[1] if len(sys.argv) > 1 else "current active projects and open decisions")
