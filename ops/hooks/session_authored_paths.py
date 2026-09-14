#!/usr/bin/env python3
"""postToolUse + afterShellExecution: record paths this conversation authored.

Fail-open. Never deny. The ledger is a preservation aid, not a gate, so a
failure to write it is reported on stderr and the tool result continues.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from session_authored_ledger import record_event  # noqa: E402


def main() -> int:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    try:
        record_event(event)
    except (OSError, ValueError) as exc:
        # Expected failure modes only: an unwritable ledger home, an
        # unresolvable path, or a malformed path value. Fail-open by contract —
        # name the cause so a silent ledger gap is diagnosable.
        print(f"session-authored-paths: ledger not updated: {exc}", file=sys.stderr)
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
