"""Graph-backed session restore (replaces JSON load in show_context.sh).

Queries the L9 graph for currently-valid, task-relevant context instead of
loading the last 7-day JSON blob. Cold-start becomes relational, not narrative.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

_MAX_TASK_TYPE_LEN = 500
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _validate_task_type(task_type: str) -> str:
    """Validate untrusted CLI input before it reaches a subprocess argument.

    Rejects non-string input, oversized input, and control/null bytes so a
    malformed argv[1] can't smuggle unexpected bytes into the downstream
    `l9_ops_mcp.cli` process.
    """
    if not isinstance(task_type, str):
        raise ValueError(f"task_type must be a string, got {type(task_type).__name__}")
    if not task_type.strip():
        raise ValueError("task_type must not be empty")
    if len(task_type) > _MAX_TASK_TYPE_LEN:
        raise ValueError(f"task_type exceeds {_MAX_TASK_TYPE_LEN} characters")
    if _CONTROL_CHARS.search(task_type):
        raise ValueError("task_type contains control characters")
    return task_type


def restore(task_type: str = "current active projects and open decisions") -> None:
    try:
        task_type = _validate_task_type(task_type)
    except ValueError as exc:
        print(f"Invalid task_type: {exc}")
        return

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
