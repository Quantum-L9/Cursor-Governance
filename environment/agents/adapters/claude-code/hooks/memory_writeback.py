#!/usr/bin/env python3
"""Stop-hook write-back — thin wrap of shared close_session (Cursor-primary)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session_id = str(event.get("session_id", "")) or "unknown-session"

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0
    if not st.fresh_receipt(contract, session_id):
        return 0

    workspace = st.workspace_root()
    os.environ.setdefault("L9_MEMORY_AGENT_ID", "claude-code")
    os.environ.setdefault("USER_ID", "claude_code_agent")

    root = gb.find_governance_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from ops.graphiti.hydration.close_session import close_session

        report = close_session(
            project_dir=workspace,
            session_id=session_id,
            reason=str(event.get("reason") or "completed"),
            transcript_path=event.get("transcript_path") or event.get("transcriptPath"),
            agent_id="claude-code",
            is_background_agent=bool(event.get("is_background_agent")),
            dry_run=False,
        )
        status = report.get("status")
        warn_n = len(report.get("warnings") or [])
        print(
            f"memory-writeback: status={status} writes={len(report.get('writes') or [])} "
            f"warnings={warn_n}",
            file=sys.stderr,
        )
        # Do not echo warning text — may carry secret-adjacent skip reasons
        # (CodeQL clear-text-logging).
    except Exception as exc:  # fail-open
        print(f"memory-writeback: skipped ({type(exc).__name__})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
