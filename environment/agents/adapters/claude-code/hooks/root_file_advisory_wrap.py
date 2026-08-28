#!/usr/bin/env python3
"""Thin Claude UserPromptSubmit wrapper → ops/autonomy/root_file_advisory.py (§2.1).

Registered `--class observer`: it emits `additionalContext` when a protected
root file is being overwritten without its `ALLOW-ROOT-DELETION` marker, and
says nothing otherwise. A missing advisory must never cost a turn, so every
failure path here exits 0 — the real gate still runs at `make pr` and in CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ADVISORY = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "root_file_advisory.py"


def main() -> int:
    if not ADVISORY.is_file():
        return 0
    raw = sys.stdin.read()
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, str(ADVISORY)],
            input=raw,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if completed.stdout.strip():
        print(completed.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
