#!/usr/bin/env python3
"""Thin Claude PreToolUse wrapper → ops/autonomy/local_execution_gate.py (§2.1)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "local_execution_gate.py"


def main() -> int:
    if not GATE.is_file():
        print("local_execution_gate_wrap: ops gate missing; skip", file=sys.stderr)
        return 0
    sys.argv = [str(GATE), "claude"]
    runpy.run_path(str(GATE), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
