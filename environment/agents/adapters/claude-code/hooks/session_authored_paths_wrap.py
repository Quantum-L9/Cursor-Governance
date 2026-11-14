"""PostToolUse (Write|Edit|MultiEdit|NotebookEdit): record paths this session authored.

Claude Code adapter for ``ops/hooks/session_authored_paths.py``, the same
recorder Cursor runs on ``postToolUse``. It feeds the session-scoped ledger
(``~/.cursor/l9/sessions/<session_id>/authored.json``) that the SessionEnd
preserve reads, so a Claude session parks exactly what it wrote and never
another chat's dirt (rules/49 item 8). Shell-authored writes are not
attributed on Claude: its PostToolUse Bash payload carries no execution window.

Fail-open: never denies, always exits 0.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _recorder() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "hooks" / "session_authored_paths.py"
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    recorder = _recorder()
    if recorder is None:
        print("session-authored-paths: recorder not found; nothing recorded", file=sys.stderr)
        return 0
    try:
        runpy.run_path(str(recorder), run_name="__main__")
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001 - a ledger aid never fails a tool call
        print(f"session-authored-paths: {type(exc).__name__}; not recorded", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
