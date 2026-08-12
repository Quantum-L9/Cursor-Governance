#!/usr/bin/env python3
"""Thin Claude PreToolUse wrapper → ops/autonomy/local_execution_gate.py (§2.1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "local_execution_gate.py"


def main() -> int:
    if not GATE.is_file():
        print("local_execution_gate_wrap: ops gate missing; skip", file=sys.stderr)
        return 0
    completed = subprocess.run(
        [sys.executable, str(GATE), "claude"],
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
