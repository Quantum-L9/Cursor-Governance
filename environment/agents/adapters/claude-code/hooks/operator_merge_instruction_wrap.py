#!/usr/bin/env python3
"""Thin Claude UserPromptSubmit wrapper → ops/autonomy/operator_merge_instruction.py (§2.1).

Registered ``--class observer``. It hands the host's prompt payload to the
recorder, which appends one receipt per explicit operator merge instruction
(CANONICAL_LAW §6.2.13, operator-prompt channel) and emits ``additionalContext``
naming what was recorded. It never blocks a prompt and never merges.

Provenance lives in the event, not in this file: Claude Code runs this hook on
the prompt it delivered to the session, and an agent tool call cannot invoke a
UserPromptSubmit hook or write the receipt (``merge_gate.py`` denies that
write). A missing recorder costs the operator nothing but the shortcut: the
merge then still needs the GitHub record.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RECORDER = Path.home() / ".cursor-governance" / "ops" / "autonomy" / "operator_merge_instruction.py"


def main() -> int:
    if not RECORDER.is_file():
        return 0
    raw = sys.stdin.read()
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, str(RECORDER), "record", "--host", "claude-code"],
            input=raw,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if completed.stderr.strip():
        print(completed.stderr, end="", file=sys.stderr)
    if completed.stdout.strip():
        print(completed.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
