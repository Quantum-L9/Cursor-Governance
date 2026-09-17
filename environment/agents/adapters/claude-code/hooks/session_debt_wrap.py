#!/usr/bin/env python3
"""Thin Claude Stop hook wrapper → ops/autonomy/session_debt.py (§2.1).

Registered `--class gate`: exit 2 blocks the turn from ending and returns
stderr to the model, so a session cannot close over unpushed commits or open
findings (rules/42-no-abandoned-work.mdc).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GATE = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "session_debt.py"


def session_roots(stdin_text: str, environ: dict[str, str] | None = None) -> list[str]:
    """The repositories this session owns: CLAUDE_PROJECT_DIR and the hook event cwd.

    Scoping the check to these roots is what keeps debt another session left in
    a sibling `~/.l9/gov-worktrees` clone from blocking this one. Unparseable
    stdin contributes nothing (fail-open on the event, never on the gate).
    """
    env = os.environ if environ is None else environ
    roots: list[str] = []

    def add(raw: object) -> None:
        text = str(raw or "").strip()
        if text and text not in roots:
            roots.append(text)

    add(env.get("CLAUDE_PROJECT_DIR"))
    try:
        event = json.loads(stdin_text) if stdin_text.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if isinstance(event, dict):
        add(event.get("cwd"))
    return roots


def main() -> int:
    if not GATE.is_file():
        # The launcher's own --class gate handling reports a missing hook.
        # Reaching here means the file vanished between checks; fail closed.
        print(f"session_debt_wrap: gate missing at {GATE} — BLOCKING", file=sys.stderr)
        return 2
    try:
        stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    except (OSError, ValueError):
        stdin_text = ""
    argv = [sys.executable, str(GATE)]
    for root in session_roots(stdin_text):
        argv.extend(["--root", root])
    argv.append("check")
    completed = subprocess.run(argv, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
