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

#: Receipt key suffix. Reuses st.write_receipt (the existing mechanism) under a
#: distinct id so this never overwrites the SessionStart prefetch receipt that
#: memory_gate reads to authorise governed writes.
WRITEBACK_RECEIPT_SUFFIX = ".writeback"


def _record(contract: dict, session_id: str, **fields: object) -> None:
    """Persist the write-back outcome. Never the gate's prefetch receipt."""
    try:
        st.write_receipt(contract, f"{session_id}{WRITEBACK_RECEIPT_SUFFIX}", dict(fields))
    except OSError as exc:
        print(
            f"memory-writeback: could not persist status ({type(exc).__name__})",
            file=sys.stderr,
        )


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
        # A policy skip: this session never prefetched, so there is nothing to
        # close. Recorded so it stays distinguishable from a runtime failure.
        _record(contract, session_id, status="skipped_no_prefetch")
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
        writes = len(report.get("writes") or [])
        warn_n = len(report.get("warnings") or [])
        print(
            f"memory-writeback: status={status} writes={writes} warnings={warn_n}",
            file=sys.stderr,
        )
        # Do not echo warning text — may carry secret-adjacent skip reasons
        # (CodeQL clear-text-logging).
        _record(
            contract,
            session_id,
            status="ran",
            close_status=str(status),
            writes=writes,
            warnings=warn_n,
        )
    except ModuleNotFoundError as exc:
        # The F-13 failure: the hook reached this line on an interpreter without
        # the locked dependencies, so write-back never ran. Previously this was
        # printed as "skipped" and was indistinguishable from a healthy policy
        # skip, which is how a permanently dead PICKUP path stayed invisible.
        print(
            f"memory-writeback: RUNTIME FAILURE — missing module {exc.name!r}; "
            "write-back did NOT run (expected the locked governance interpreter)",
            file=sys.stderr,
        )
        _record(
            contract,
            session_id,
            status="runtime_error",
            error="ModuleNotFoundError",
            missing_module=str(exc.name),
            interpreter=sys.executable,
        )
    except Exception as exc:  # noqa: BLE001 - hook contract is fail-open
        print(
            f"memory-writeback: RUNTIME FAILURE ({type(exc).__name__}); write-back did NOT run",
            file=sys.stderr,
        )
        _record(
            contract,
            session_id,
            status="runtime_error",
            error=type(exc).__name__,
            interpreter=sys.executable,
        )
    # Exit 0 either way: the Stop hook contract is fail-open and must not block
    # session termination. Observability lives in the receipt, not the exit code.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
