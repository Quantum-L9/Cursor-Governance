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
        [sys.executable, "-m", "l9_ops_mcp.cli", "query", json.dumps(payload)],
        capture_output=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode != 0:
        print(f"Graph query failed (rc={proc.returncode}): {proc.stderr.strip()}")
        print("Falling back to JSON session cache.")
        return

    try:
        facts = json.loads(proc.stdout).get("facts", [])
    except json.JSONDecodeError:
        print("No graph context available — MCP returned non-JSON. Falling back to JSON session cache.")
        return

    if not facts:
        print("No graph context episodes found. Falling back to JSON session cache.")
        return

    print("=" * 60)
    print("LAST SESSION CONTEXT (graph-derived)")
    print("=" * 60)
    for f in facts:
        fact_text = f.get("fact", f.get("body", str(f)))
        print(f"  - {fact_text}")
    print("=" * 60)


if __name__ == "__main__":
    restore(sys.argv[1] if len(sys.argv) > 1 else "current active projects and open decisions")
