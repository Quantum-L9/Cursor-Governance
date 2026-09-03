#!/usr/bin/env python3
"""Executable proof for the l9-wire-into-repo validation seam."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_wiring_fixture.py"
PASS_FIXTURE = ROOT / "fixtures" / "wiring_pass.json"
FAIL_FIXTURE = ROOT / "fixtures" / "wiring_fail_unreachable.json"


def run(fixture: Path) -> int:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(fixture)],
        cwd=ROOT,
        check=False,
    ).returncode


def main() -> int:
    if run(PASS_FIXTURE) != 0:
        print("self-test FAIL: valid upstream wiring fixture was rejected", file=sys.stderr)
        return 1
    if run(FAIL_FIXTURE) == 0:
        print("self-test FAIL: unreachable consumer fixture was accepted", file=sys.stderr)
        return 1
    print("self-test PASS: positive and negative wiring fixtures behave as required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
