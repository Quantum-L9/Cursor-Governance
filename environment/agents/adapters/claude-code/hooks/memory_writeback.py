#!/usr/bin/env python3
"""Stop-hook write-back — thin wrap of the canonical session close (stage C8).

Multi-repository by construction, because hydration is. A cloud container puts
several repositories side by side and ``WORKSPACE`` then names the *container*,
not a checkout. ``memory_prefetch.py`` learned that and fans out;
``close_session`` was still called once, on the container root, where identity
resolution matches every repository and therefore returns none. The observed
result was ``status=skipped writes=0`` on a healthy store: the session read six
repositories' memory and wrote back to zero, so nothing a session learned
survived it.

The repository set comes from ``ops/scripts/lib/workspace_roots.py`` — the same
one answer prefetch uses — but the *preferred* source is the prefetch receipt
this session already wrote. ``hydrated_roots`` records the roots whose identity
actually resolved at hydrate time, so reusing it makes close symmetric with
hydrate by construction rather than by re-deriving a set that could drift
between the two ends of one session.

Every close crosses the memory control plane (continuation capsule admitted as
a governed candidate, then ``memory.close``); nothing here writes a provider.
A subagent or background run never owns the parent session's continuation:
its Stop is recorded as ``skipped_subagent`` and closes nothing (authority
narrowing, stage C8).
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

import memory_bridge as mb  # noqa: E402
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


# --- Announcement ------------------------------------------------------------
# The close writes durable memory from a Stop hook, and a Stop hook's stderr is
# seen by no one: writes and failures alike were silent, so a dead close path
# stayed dead for weeks (the receipt-key mismatch above). Every durable write
# and every failure is now ANNOUNCED — to the user, as a Stop-hook
# ``systemMessage`` (informational; it does not continue the turn) — naming
# exactly what was written, where, and how to verify it from a later session.
# Nothing new is written to memory: the announcement describes the close's own
# writes and is kept in the local write-back receipt beside them.
#
# Noise discipline: a turn whose close was an idempotent skip announces
# nothing, and a non-write outcome (a policy skip, a failure) is announced when
# it first appears or changes, not on every turn.

_ITEM_CHARS = 200
_ITEMS = 8


def _clip(value: object) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= _ITEM_CHARS else text[: _ITEM_CHARS - 1] + "…"


def _listing(values: object) -> str:
    items = [_clip(v) for v in (values or [])][:_ITEMS]
    return "; ".join(items) if items else "none"


def _verify_line(session_id: str, repo: Path) -> str:
    return (
        "verify (any later session): ~/.cursor-governance/.venv/bin/python -m "
        f"ops.memory.cli search {session_id} --tag session_continuation "
        f"--workspace {repo}"
    )


def _writes(report: dict) -> list[dict]:
    """The report's write entries that carry fields; anything else is ignored."""
    return [w for w in report.get("writes") or [] if isinstance(w, dict)]


def _repo_block(repo: Path, report: dict, session_id: str) -> list[str]:
    status = str(report.get("status") or "unknown")
    lines = [f"• {repo.name} → namespace {report.get('group_id') or 'unresolved'}: {status}"]
    for write in _writes(report):
        state = "written" if write.get("written") else f"NOT written ({write.get('status')})"
        ident = write.get("record_id") or write.get("receipt_id") or "no id"
        lines.append(f"  - {write.get('kind')}: {state}, id {ident}")
    pickup = report.get("pickup") or {}
    if pickup:
        lines.append(f"  continuation — objective: {_clip(pickup.get('active_objective') or '')}")
        lines.append(f"    next action: {_clip(pickup.get('next_action') or '')}")
        lines.append(f"    blockers: {_listing(pickup.get('blockers'))}")
        lines.append(f"    decisions: {_listing(pickup.get('decisions'))}")
        lines.append(f"    unfinished: {_listing(pickup.get('unfinished_work'))}")
    if any(w.get("written") for w in _writes(report)):
        lines.append(f"  {_verify_line(session_id, repo)}")
    return lines


def compose_announcement(
    session_id: str, reports: list[tuple[Path, dict]], deferred: list[str]
) -> str | None:
    """The formal announcement for this Stop, or None when nothing happened.

    Written when at least one root wrote durably or did not close cleanly.
    A Stop where every root was an idempotent skip announces nothing.
    """
    wrote = any(any(w.get("written") for w in _writes(r)) for _, r in reports)
    failed = [
        (repo, r)
        for repo, r in reports
        if str(r.get("status")) not in {"closed_canonically", "idempotent_skip"}
    ]
    if not wrote and not failed and not deferred:
        return None
    title = "FAILED" if (failed or deferred) and not wrote else "WRITTEN"
    if wrote and (failed or deferred):
        title = "PARTIAL"
    lines = [f"L9 MEMORY WRITE-BACK — {title} (session {session_id}, agent claude-code)"]
    for repo, report in reports:
        if str(report.get("status")) == "idempotent_skip":
            continue
        lines.extend(_repo_block(repo, report, session_id))
    for root in deferred:
        lines.append(f"• {Path(root).name}: NOT closed — hydration budget exhausted this turn")
    return "\n".join(lines)


def _previous(contract: dict, session_id: str) -> dict:
    try:
        path = st.receipt_path(contract, f"{session_id}{WRITEBACK_RECEIPT_SUFFIX}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _emit(message: str) -> None:
    """Stop-hook output: a user-visible message that does not continue the turn."""
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


def _announce_state(contract: dict, session_id: str, status: str, message: str) -> str | None:
    """Announce a non-write outcome once, when it first appears or changes."""
    if _previous(contract, session_id).get("status") == status:
        return None
    _emit(message)
    return message


def _record(contract: dict, session_id: str, **fields: object) -> None:
    """Persist the write-back outcome. Never the gate's prefetch receipt."""
    try:
        st.write_receipt(contract, f"{session_id}{WRITEBACK_RECEIPT_SUFFIX}", dict(fields))
    except OSError as exc:
        print(
            f"memory-writeback: could not persist status ({type(exc).__name__})",
            file=sys.stderr,
        )


def _runtime_failure(contract: dict, session_id: str, **fields: object) -> None:
    """Announce (once) that the close could not run, then record it."""
    announced = _announce_state(
        contract,
        session_id,
        "runtime_error",
        f"L9 MEMORY WRITE-BACK — FAILED (session {session_id}): the close could not load "
        f"({fields.get('error')}); nothing was written to memory this turn.",
    )
    _record(
        contract,
        session_id,
        status="runtime_error",
        announcement=announced or _previous(contract, session_id).get("announcement"),
        **fields,
    )


def _is_subagent(event: dict) -> bool:
    """A subagent / background run never closes the parent session's memory."""
    if event.get("is_background_agent") or event.get("isBackgroundAgent"):
        return True
    return str(event.get("agent_type") or event.get("agentType") or "").lower() == "subagent"


def _writeback_roots(contract: dict, receipt_id: str, workspace: Path) -> list[Path]:
    """Repositories to close, preferring the ones this session hydrated.

    Falling back to ``workspace_roots`` matters for a session whose prefetch
    receipt is missing or unreadable: without it the fallback would be the
    container root again, which is the exact defect this function exists to
    remove.
    """
    try:
        data = json.loads(st.receipt_path(contract, receipt_id).read_text(encoding="utf-8"))
        roots = [Path(r) for r in (data.get("hydrated_roots") or []) if r]
        roots = [r for r in roots if r.is_dir()]
        if roots:
            return roots
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        # Deliberately swallowed, and the fallback below is the whole point: an
        # absent, truncated or malformed prefetch receipt is an ordinary state
        # (a session that never hydrated, a container reaped mid-write), not an
        # error to propagate out of a fail-open Stop hook.
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
    if _is_subagent(event):
        # Authority narrowing: the parent session owns its continuation and its
        # close. A subagent inherits read evidence only and writes nothing.
        _record(contract, session_id, status="skipped_subagent")
        return 0
    # The prefetch receipt is keyed by the writer-scoped id
    # (``<writer_agent>__<chat>``, memory_state.resolve_receipt_id), the one
    # key prefetch stamps and the write gate reads. This hook looked it up by
    # the raw session id, found nothing, recorded skipped_no_prefetch on every
    # Stop, and never reached close_session — so no Claude session ever wrote
    # its continuation, and nothing on disk or in memory said so.
    try:
        receipt_id = st.resolve_receipt_id(event=event)
    except ValueError:
        receipt_id = ""
    if not receipt_id or not st.fresh_receipt(contract, receipt_id):
        # A policy skip: this session never prefetched, so there is nothing to
        # close. Recorded so it stays distinguishable from a runtime failure.
        announced = _announce_state(
            contract,
            session_id,
            "skipped_no_prefetch",
            f"L9 MEMORY WRITE-BACK — NOT WRITTEN (session {session_id}): no SessionStart "
            "prefetch receipt for this session, so its continuation was not closed. "
            "Repair: memory_prefetch.py --session-id <id>, or /end-session.",
        )
        _record(
            contract,
            session_id,
            status="skipped_no_prefetch",
            receipt_id=receipt_id,
            announcement=announced or _previous(contract, session_id).get("announcement"),
        )
        return 0

    workspace = st.workspace_root()
    roots = _writeback_roots(contract, receipt_id, workspace)
    os.environ.setdefault("L9_MEMORY_AGENT_ID", "claude-code")
    os.environ.setdefault("USER_ID", "claude_code_agent")

    mb.ensure_importable()

    try:
        from ops.graphiti.hydration.close_session import close_session
    except ModuleNotFoundError as exc:
        # The F-13 failure: the hook reached this line on an interpreter without
        # the locked dependencies, so write-back never ran. Previously this was
        # printed as "skipped" and was indistinguishable from a healthy policy
        # skip, which is how a permanently dead close path stayed invisible.
        print(
            f"memory-writeback: RUNTIME FAILURE — missing module {exc.name!r}; "
            "write-back did NOT run (expected the locked governance interpreter)",
            file=sys.stderr,
        )
        _runtime_failure(
            contract,
            session_id,
            error="ModuleNotFoundError",
            missing_module=str(exc.name),
            interpreter=sys.executable,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - Stop-hook contract is fail-open
        # Narrowing the import guard to ModuleNotFoundError alone would leave a
        # SyntaxError, a circular ImportError, or an exception raised at module
        # scope inside close_session uncaught — and an uncaught exception on a
        # Stop hook is a traceback, not a receipt.
        print(
            f"memory-writeback: RUNTIME FAILURE ({type(exc).__name__}); write-back did NOT run",
            file=sys.stderr,
        )
        _runtime_failure(contract, session_id, error=type(exc).__name__, interpreter=sys.executable)
        return 0

    try:
        total_budget = float(os.environ.get("L9_MEMORY_WRITEBACK_BUDGET", DEFAULT_TOTAL_BUDGET))
    except ValueError:
        total_budget = DEFAULT_TOTAL_BUDGET
    deadline = time.monotonic() + total_budget

    statuses: list[str] = []
    reports: list[tuple[Path, dict]] = []
    deferred: list[str] = []
    writes = 0
    warnings = 0

    for index, repo in enumerate(roots):
        left = deadline - time.monotonic()
        # `index > 0` is load-bearing: the FIRST root is always attempted, however
        # little time remains. Guarding it too meant a budget below the threshold
        # closed nothing at all and recorded four deferrals — reproducing the
        # writes=0 outcome this hook exists to remove, from the other direction.
        # Phase A (capsule + close) is not bounded by this budget; only Phase B
        # is. So a starved root still closes canonically and merely skips
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
                is_background_agent=False,
                dry_run=False,
                budget=per_root,
                surface="claude-session-end",
            )
            statuses.append(f"{repo.name}={report.get('status')}")
            reports.append((repo, report))
            writes += len(report.get("writes") or [])
            warnings += len(report.get("warnings") or [])
        except Exception as exc:  # noqa: BLE001 - one bad root must not lose the rest
            print(
                f"memory-writeback: {repo.name} FAILED ({type(exc).__name__}); continuing",
                file=sys.stderr,
            )
            statuses.append(f"{repo.name}=error")
            reports.append((repo, {"status": "error", "writes": [], "error": type(exc).__name__}))
            warnings += 1

    # Do not echo warning text — may carry secret-adjacent skip reasons
    # (CodeQL clear-text-logging).
    print(
        f"memory-writeback: roots={len(roots)} closed={len(statuses)} "
        f"deferred={len(deferred)} writes={writes} warnings={warnings}",
        file=sys.stderr,
    )
    try:
        announcement = compose_announcement(session_id, reports, deferred)
    except Exception as exc:  # noqa: BLE001 - the announcement must never lose the receipt
        announcement = (
            f"L9 MEMORY WRITE-BACK — ran (session {session_id}) but the announcement "
            f"could not be composed ({type(exc).__name__}); see the write-back receipt."
        )
    if announcement:
        _emit(announcement)
    _record(
        contract,
        session_id,
        announcement=announcement or _previous(contract, session_id).get("announcement"),
        status="ran",
        transport="memory-control-plane/v1",
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
