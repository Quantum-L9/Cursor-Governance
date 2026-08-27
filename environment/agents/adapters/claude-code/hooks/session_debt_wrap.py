#!/usr/bin/env python3
"""Thin Claude Stop hook wrapper → ops/autonomy/session_debt.py (§2.1).

Registered `--class gate`: exit 2 blocks the turn from ending and returns
stderr to the model, so a session cannot close over unpushed commits or open
findings (rules/42-no-abandoned-work.mdc).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "session_debt.py"


def main() -> int:
    if not GATE.is_file():
        # The launcher's own --class gate handling reports a missing hook.
        # Reaching here means the file vanished between checks; fail closed.
        print(f"session_debt_wrap: gate missing at {GATE} — BLOCKING", file=sys.stderr)
        return 2
    completed = subprocess.run([sys.executable, str(GATE), "check"], check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
