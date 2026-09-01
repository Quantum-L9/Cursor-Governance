#!/usr/bin/env python3
"""Stop-hook write-back — thin wrap of shared close_session (Cursor-primary).

Multi-repository by construction, because hydration is. A cloud container puts
several repositories side by side and ``WORKSPACE`` then names the *container*,
not a checkout. ``memory_prefetch.py`` learned that and fans out;
``close_session`` was still called once, on the container root, where
``resolve_group_id`` matches every repository and therefore returns none. The
observed result was ``status=skipped writes=0`` on a healthy Graphiti: the
session read six repositories' memory and wrote back to zero, so nothing a
session learned survived it.

The repository set comes from ``ops/scripts/lib/workspace_roots.py`` — the same
one answer prefetch uses — but the *preferred* source is the prefetch receipt
this session already wrote. ``hydrated_roots`` records the roots whose identity
actually resolved at hydrate time, so reusing it makes close symmetric with
hydrate by construction rather than by re-deriving a set that could drift
between the two ends of one session.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"


def _governance_lib() -> Path:
    """Locate ops/scripts/lib by walking up, not by counting parents.

    Same resolution as ``memory_prefetch.py``: a hard-coded ``parents[N]``
    silently binds to the wrong directory the moment this hook is moved.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "scripts" / "lib"
        if (candidate / "workspace_roots.py").is_file():
            return candidate
    raise ModuleNotFoundError("ops/scripts/lib/workspace_roots.py not found above this hook")


_GOV_LIB = _governance_lib()
if str(_GOV_LIB) not in sys.path:
    sys.path.insert(0, str(_GOV_LIB))

from workspace_roots import workspace_roots as _shared_workspace_roots  # noqa: E402

sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402

#: Receipt key suffix. Reuses st.write_receipt (the existing mechanism) under a
#: distinct id so this never overwrites the SessionStart prefetch receipt that
#: memory_gate reads to authorise governed writes.
WRITEBACK_RECEIPT_SUFFIX = ".writeback"

#: Wall-clock this hook may spend in total. The Stop hook registration owns the
#: real ceiling; this stays safely under it so the loop chooses which roots go
#: unclosed instead of being killed mid-write with no record of how far it got.
DEFAULT_TOTAL_BUDGET = 75.0

#: Whether to START another root, never whether to start the first one. Below
#: this there is not enough left for a useful close (close_session's
#: PHASE_A_BUDGET alone is 8.0), so the remaining roots are deferred and NAMED
#: rather than attempted and silently truncated by the hook timeout.
MIN_ROOT_BUDGET = 9.0


def _record(contract: dict, session_id: str, **fields: object) -> None:
    """Persist the write-back outcome. Never the gate's prefetch receipt."""
    try:
        st.write_receipt(contract, f"{session_id}{WRITEBACK_RECEIPT_SUFFIX}", dict(fields))
    except OSError as exc:
        print(
            f"memory-writeback: could not persist status ({type(exc).__name__})",
            file=sys.stderr,
        )


def _writeback_roots(contract: dict, session_id: str, workspace: Path) -> list[Path]:
    """Repositories to close, preferring the ones this session hydrated.

    Falling back to ``workspace_roots`` matters for a session whose prefetch
    receipt is missing or unreadable: without it the fallback would be the
    container root again, which is the exact defect this function exists to
    remove.
    """
    try:
        data = json.loads(st.receipt_path(contract, session_id).read_text(encoding="utf-8"))
        roots = [Path(r) for r in (data.get("hydrated_roots") or []) if r]
        roots = [r for r in roots if r.is_dir()]
        if roots:
            return roots
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return _shared_workspace_roots(workspace)


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
    roots = _writeback_roots(contract, session_id, workspace)
    os.environ.setdefault("L9_MEMORY_AGENT_ID", "claude-code")
    os.environ.setdefault("USER_ID", "claude_code_agent")

    root = gb.find_governance_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from ops.graphiti.hydration.close_session import close_session
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
        return 0

    try:
        total_budget = float(os.environ.get("L9_MEMORY_WRITEBACK_BUDGET", DEFAULT_TOTAL_BUDGET))
    except ValueError:
        total_budget = DEFAULT_TOTAL_BUDGET
    deadline = time.monotonic() + total_budget

    statuses: list[str] = []
    deferred: list[str] = []
    writes = 0
    warnings = 0

    for index, repo in enumerate(roots):
        left = deadline - time.monotonic()
        # `index > 0` is load-bearing: the FIRST root is always attempted, however
        # little time remains. Guarding it too meant a budget below the threshold
        # closed nothing at all and recorded four deferrals — reproducing the
        # writes=0 outcome this hook exists to remove, from the other direction.
        # Phase A (the PICKUP write) is not bounded by this budget; only Phase B
        # is. So a starved root still writes its PICKUP and merely skips
        # distillation, which is the correct degradation.
        if index > 0 and left < MIN_ROOT_BUDGET:
            # Name what was not closed. A truncated loop that reports only its
            # successes is the same lie as a skipped write that reports "ran".
            deferred.extend(str(r) for r in roots[index:])
            break
        # An even split of what is actually left, recomputed per iteration so a
        # fast root hands its unused time to the roots after it rather than to a
        # fixed slice that expires unused.
        per_root = max(0.0, left) / max(1, len(roots) - index)
        try:
            report = close_session(
                project_dir=repo,
                session_id=session_id,
                reason=str(event.get("reason") or "completed"),
                transcript_path=event.get("transcript_path") or event.get("transcriptPath"),
                agent_id="claude-code",
                is_background_agent=bool(event.get("is_background_agent")),
                dry_run=False,
                budget=per_root,
            )
            statuses.append(f"{repo.name}={report.get('status')}")
            writes += len(report.get("writes") or [])
            warnings += len(report.get("warnings") or [])
        except Exception as exc:  # noqa: BLE001 - one bad root must not lose the rest
            print(
                f"memory-writeback: {repo.name} FAILED ({type(exc).__name__}); continuing",
                file=sys.stderr,
            )
            statuses.append(f"{repo.name}=error")
            warnings += 1

    # Do not echo warning text — may carry secret-adjacent skip reasons
    # (CodeQL clear-text-logging).
    print(
        f"memory-writeback: roots={len(roots)} closed={len(statuses)} "
        f"deferred={len(deferred)} writes={writes} warnings={warnings}",
        file=sys.stderr,
    )
    _record(
        contract,
        session_id,
        status="ran",
        close_status=";".join(statuses) or "none",
        writes=writes,
        warnings=warnings,
        roots=[str(r) for r in roots],
        deferred_roots=deferred,
    )
    # Exit 0 either way: the Stop hook contract is fail-open and must not block
    # session termination. Observability lives in the receipt, not the exit code.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
