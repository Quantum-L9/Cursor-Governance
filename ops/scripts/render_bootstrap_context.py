#!/usr/bin/env python3
"""Render the sessionStart hook JSON payload as human-readable lines.

The hook's stdout is a machine payload for Cursor. `make start` runs the exact same
hook and pipes it here so a human sees the same context Cursor would receive.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("bootstrap: no output (hook produced nothing)")
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        return 1

    env = payload.get("env", {})
    if env:
        print("env:")
        for key, value in env.items():
            print(f"  {key}={value}")

    context = payload.get("additional_context", "")
    if not context:
        print("context: (empty)")
        return 0

    # additional_context is sectioned markdown (Governance / Runtime / Graphiti /
    # Code-graph / Plan audit). Do not split on " | " — wiring and plan-audit
    # headers use pipes as field separators, and a 300-char chop hid Plan audit.
    print("context:")
    print(context.rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
