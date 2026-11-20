"""SessionEnd — close every Claude Code session, the way Cursor's sessionEnd does.

Cursor's ``sessionEnd`` runs two things for every conversation: it parks the
paths this conversation authored on ``refs/l9/preserved/session/<sid>``
(``ops/scripts/session_end_preserve.py``) and it closes the session's
continuation through the memory control plane (``close_session``). Claude Code
had neither: its only close was the post-publish Stop hook
(``memory_writeback.py``), so a session that never published was never closed
and nothing preserved what it wrote. This hook is that parity.

Order matters. Claude Code gives SessionEnd hooks a 1.5 s budget by default,
raised to the highest registered ``timeout`` and capped at 60 s, and the hook
cannot block exit. The local, fast preserve therefore runs first; the network
close runs second under a bounded budget. A close the host kills leaves its
obligation receipt as ``close_incomplete``, which the next SessionStart reports
as ``CLOSE_GAP`` with ``REPAIR: /end-session``.

Never pushes, never stages, never touches the worktree (rules/49 item 8;
CANONICAL_LAW §5.1). A subagent or background run closes nothing. Identity is
derived from host markers (``ops/memory/agent_identity.py``), never configured.
Fail-open: always exits 0; Claude Code discards SessionEnd stdout.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

MEM = Path(__file__).resolve().parent.parent / "memory"
DEFAULT_TOTAL_BUDGET = 50.0
MIN_ROOT_BUDGET = 5.0


def _governance_root() -> Path:
    """The governance checkout this hook lives in (walk up, never count parents)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "ops" / "scripts" / "session_end_preserve.py").is_file():
            return parent
    raise ModuleNotFoundError("ops/scripts/session_end_preserve.py not found above this hook")


_GOV = _governance_root()
for _path in (_GOV / "ops" / "scripts" / "lib", _GOV / "ops" / "scripts", MEM):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memory_bridge as mb  # noqa: E402
import memory_state as st  # noqa: E402
import post_publish as pp  # noqa: E402
from workspace_roots import workspace_roots as _shared_workspace_roots  # noqa: E402


def _log(message: str) -> None:
    # SessionEnd output is discarded by the host; stderr reaches the debug log.
    print(f"session-end-close: {message}", file=sys.stderr)


def _event() -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        return {}
    if not data.get("cwd") and os.environ.get("CLAUDE_PROJECT_DIR"):
        data["cwd"] = os.environ["CLAUDE_PROJECT_DIR"]
    return data


def preserve(event: dict[str, Any], *, ledger_home: Path | None = None) -> dict[str, Any]:
    """Park this session's authored paths; never a mutation of the worktree."""
    try:
        from session_end_preserve import run as preserve_run

        return preserve_run(event, ledger_home=ledger_home)
    except Exception as exc:  # noqa: BLE001 - fail-open, reported
        return {"applied": False, "skipped": f"error:{type(exc).__name__}"}


def close_roots(event: dict[str, Any], session_id: str) -> list[Path]:
    """The repositories this session put in scope, else the shared workspace roots."""
    try:
        contract = st.load_contract()
        receipt_id = st.resolve_receipt_id(event=event)
    except (OSError, ValueError):
        contract, receipt_id = {}, ""
    del session_id
    workspace = Path(str(event.get("cwd") or st.workspace_root()))
    return list(pp.session_roots(contract, receipt_id, _shared_workspace_roots, workspace))


def close(event: dict[str, Any], session_id: str) -> list[str]:
    agent_id = st.bind_identity_env()
    if not agent_id:
        return [f"identity_unresolved ({st.unresolved_identity_reason()})"]
    mb.ensure_importable()
    try:
        from ops.graphiti.hydration.close_session import close_session
    except Exception as exc:  # noqa: BLE001 - fail-open, reported
        return [f"runtime_failure:{type(exc).__name__}"]
    try:
        total = float(os.environ.get("L9_SESSION_END_BUDGET", DEFAULT_TOTAL_BUDGET))
    except ValueError:
        total = DEFAULT_TOTAL_BUDGET
    deadline = time.monotonic() + total
    reason = str(event.get("reason") or "other")
    statuses: list[str] = []
    for root in close_roots(event, session_id):
        left = deadline - time.monotonic()
        if left < MIN_ROOT_BUDGET:
            statuses.append(f"{root.name}=deferred_budget")
            continue
        try:
            report = close_session(
                project_dir=root,
                session_id=session_id,
                reason=f"session_end:{reason}",
                transcript_path=event.get("transcript_path") or event.get("transcriptPath"),
                agent_id=agent_id,
                budget=left,
                surface="claude-session-end",
            )
        except Exception as exc:  # noqa: BLE001 - fail-open, reported
            report = {"status": f"error:{type(exc).__name__}"}
        statuses.append(f"{root.name}={report.get('status')}")
    return statuses


def main() -> int:
    event = _event()
    session_id = str(event.get("session_id") or "")
    if not session_id:
        _log("no session_id in the SessionEnd payload; nothing closed")
        return 0
    if pp.is_subagent(event):
        _log(f"subagent {session_id}: closes nothing (the parent owns its continuation)")
        return 0
    kept = preserve(event)
    _log(
        f"preserve {session_id}: "
        + (f"parked {kept.get('ref')}" if kept.get("applied") else f"skipped {kept.get('skipped')}")
    )
    _log(f"close {session_id}: " + (", ".join(close(event, session_id)) or "no roots"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - SessionEnd never fails the host
        _log(f"unexpected {type(exc).__name__}; nothing further done")
        raise SystemExit(0) from None
