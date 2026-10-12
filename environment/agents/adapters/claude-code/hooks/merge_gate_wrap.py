#!/usr/bin/env python3
"""Thin Claude PreToolUse wrapper → ops/autonomy/merge_gate.py (§2.1).

Fails closed (INV-1). The launcher ``exec``s this file, so its exit status is
the hook's: exit 0 with no decision is an allow, and a non-2 crash is a
non-blocking error that Claude also lets through. A merge gate that is missing
or raises has not evaluated, so it blocks with exit 2 rather than silently
granting the merge authority it exists to withhold (CANONICAL_LAW §6.2.12).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "merge_gate.py"
BLOCK = 2


def main() -> int:
    if not GATE.is_file():
        print(
            f"merge_gate_wrap: governing merge gate missing at {GATE} — BLOCKING "
            "(INV-1: gates fail closed)",
            file=sys.stderr,
        )
        return BLOCK
    sys.argv = [str(GATE)]
    try:
        runpy.run_path(str(GATE), run_name="__main__")
    except SystemExit as exc:
        if exc.code in (None, 0):
            return 0
        print(f"merge_gate_wrap: merge gate exited {exc.code!r} — BLOCKING", file=sys.stderr)
        return BLOCK
    except Exception as exc:  # noqa: BLE001 - any gate fault is a block, never an allow
        print(
            f"merge_gate_wrap: merge gate raised {type(exc).__name__}: {exc} — BLOCKING",
            file=sys.stderr,
        )
        return BLOCK
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
