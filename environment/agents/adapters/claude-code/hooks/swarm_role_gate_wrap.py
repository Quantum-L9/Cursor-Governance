#!/usr/bin/env python3
"""Thin Claude PreToolUse wrapper → ops/autonomy/swarm_role_gate.py.

Fails closed (INV-1), like merge_gate_wrap.py: the launcher ``exec``s this file, so its
exit status is the hook's. A gate that is missing or raises has not evaluated, so it
blocks with exit 2. Registered only on the cross-session tools
(``mcp__claude-code-remote__.*``), so a block costs at most those tools.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "swarm_role_gate.py"
BLOCK = 2


def main() -> int:
    if not GATE.is_file():
        print(
            f"swarm_role_gate_wrap: gate missing at {GATE} — BLOCKING (INV-1: gates fail closed)",
            file=sys.stderr,
        )
        return BLOCK
    sys.argv = [str(GATE)]
    try:
        runpy.run_path(str(GATE), run_name="__main__")
    except SystemExit as exc:
        if exc.code in (None, 0):
            return 0
        print(f"swarm_role_gate_wrap: gate exited {exc.code!r} — BLOCKING", file=sys.stderr)
        return BLOCK
    except Exception as exc:  # noqa: BLE001 - any gate fault is a block, never an allow
        print(
            f"swarm_role_gate_wrap: gate raised {type(exc).__name__}: {exc} — BLOCKING",
            file=sys.stderr,
        )
        return BLOCK
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
