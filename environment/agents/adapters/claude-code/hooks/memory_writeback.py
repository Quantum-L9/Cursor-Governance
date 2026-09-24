#!/usr/bin/env python3
"""Stop-hook write-back — the post-publish handoff close (stage C8).

WHEN: once per publication of this session, after it — never on an ordinary
turn. The first Stop after ``make pr`` asks the agent (once) for the
comprehensive handoff (``.l9/memory/handoff.json``, l9.session_handoff.v1)
and, in the same single request, the governance handoff
(``.l9/memory/governance-handoff.json``, l9.governance_handoff.v1); the next
Stop closes the in-scope repository with the repository brief carried in its
continuation capsule and announces exactly what was written — or loudly, what
was not. The governance handoff is written by its own Stop hook,
``governance_handoff_writeback.py``, running in parallel with this one, to the
cursor-governance namespace only.

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
from typing import Any

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
import post_publish as pp  # noqa: E402

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

_ITEM_CHARS = 600
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


#: Bound by main() after the governance tree is importable (ops.* is not on the
#: path at import time of this hook).
session_handoff: Any = None
governance_handoff: Any = None


def _bind_runtime(handoff_module: Any, governance_module: Any) -> None:
    global session_handoff, governance_handoff  # noqa: PLW0603 - bound once per hook run
    session_handoff = handoff_module
    governance_handoff = governance_module


#: Per-publication ledger: one handoff request and one close per publication.
#: The governance hook keeps its own (``.l9/memory/governance-handoffs``).
HANDOFF_LEDGER_REL = Path(".l9") / "memory" / "handoffs"


def _pending_publication(root: Path, started_at: float) -> dict | None:
    """This session's newest publication in ``root`` that has not closed yet."""
    pub = pp.publication(root, started_at)
    if pub is None or pp.ledger(root, HANDOFF_LEDGER_REL, pub["key"]).get("closed"):
        return None
    return pub


def _section(title: str, items: list, render) -> list[str]:
    if not items:
        return [f"  {title}: none"]
    return [f"  {title}:"] + [f"    - {render(i)}" for i in items]


def compose_handoff_announcement(
    session_id: str,
    root: Path,
    pub: dict,
    report: dict,
    brief: dict | None,
    handoff_error: str,
) -> str:
    """The formal record of what the post-publish close wrote — or failed to."""
    wrote = any(w.get("written") for w in _writes(report))
    closed = str(report.get("status")) == "closed_canonically"
    if closed and brief is not None:
        title = "WRITTEN"
    elif wrote:
        title = "PARTIAL"
    else:
        title = "FAILED"
    lines = [
        f"L9 MEMORY HANDOFF — {title} ({pub['label']}, session {session_id}, "
        f"agent {os.environ.get('L9_MEMORY_AGENT_ID') or 'unknown-agent'})",
        f"publication: {pub['url'] or pub['label']}",
    ]
    lines.extend(_repo_block(root, {**report, "pickup": {}}, session_id))
    if report.get("supersedes"):
        lines.append(f"  superseded earlier continuation {report['supersedes']}")
    if brief is None:
        lines.append(
            f"  HANDOFF NOT CAPTURED: {handoff_error or 'no handoff'} — the continuation "
            "carries only the generic session capsule"
        )
    else:
        lines.append(f"  objective: {_clip(brief['objective'])}")
        lines.append(f"  status: {_clip(brief['status'])}")
        for key in (
            "published",
            "completed",
            "next_actions",
            "open_questions",
            "risks",
            "verification",
        ):
            lines.extend(_section(key.replace("_", " "), brief.get(key) or [], _clip))
        lines.extend(
            _section(
                "not completed",
                brief.get("not_completed") or [],
                lambda i: _clip(f"{i['item']} — {i.get('reason', '')}"),
            )
        )
        lines.extend(
            _section(
                "blocked",
                brief.get("blocked") or [],
                lambda i: _clip(
                    f"{i['item']} — {i.get('blocker', '')} (unblock: {i.get('unblock', '?')})"
                ),
            )
        )
        lines.extend(
            _section(
                "decisions",
                brief.get("decisions") or [],
                lambda i: _clip(f"{i['decision']} — {i.get('rationale', '')}"),
            )
        )
        lines.extend(
            _section(
                "conflicts",
                brief.get("conflicts") or [],
                lambda i: _clip(f"{i['conflict']} — {i.get('resolution', '')}"),
            )
        )
        lines.extend(
            _section(
                "YOUR ACTIONS ELSEWHERE",
                brief.get("human_actions") or [],
                lambda i: _clip(
                    f"{i['action']} @ {i.get('where', '?')} — "
                    f"{i.get('why', '')}; then {i.get('then', '')}"
                ),
            )
        )
    lines.append(
        "• governance handoff → namespace cursor-governance: written separately by "
        "governance_handoff_writeback.py (its own announcement)"
    )
    return "\n".join(lines)


def _previous(contract: dict, session_id: str) -> dict:
    try:
        path = st.receipt_path(contract, f"{session_id}{WRITEBACK_RECEIPT_SUFFIX}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


_emit = pp.emit


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


def _writeback_roots(contract: dict, receipt_id: str, workspace: Path) -> list[Path]:
    """Repositories to close, preferring the ones this session hydrated.

    Falling back to ``workspace_roots`` matters for a session whose prefetch
    receipt is missing or unreadable: without it the fallback would be the
    container root again, which is the exact defect this function exists to
    remove.
    """
    return pp.session_roots(contract, receipt_id, _shared_workspace_roots, workspace)


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
    if pp.is_subagent(event):
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
    # usable, not fresh: fresh_receipt() is False for a DEGRADED hydration, which
    # made a degraded session indistinguishable from one that never started —
    # it was never closed and was announced as "no prefetch receipt". The write
    # gate made the same move for the same reason (memory_state.usable_receipt).
    if not st.usable_receipt(contract, receipt_id):
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
    agent_id = st.bind_identity_env()

    mb.ensure_importable()

    try:
        # ``from <full.dotted.module> import name`` resolves the module through
        # sys.modules by its full name (never a stale package attribute left by
        # an earlier import) and still goes through __import__, so an import
        # failure is raised HERE and classified below.
        from ops.graphiti.hydration.close_session import close_session
        from ops.memory.governance_handoff import GOVERNANCE_SCHEMA  # noqa: F401
        from ops.memory.session_handoff import HANDOFF_SCHEMA  # noqa: F401

        _bind_runtime(
            sys.modules["ops.memory.session_handoff"],
            sys.modules["ops.memory.governance_handoff"],
        )
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

    # --- Post-publish only ---------------------------------------------------
    # The close fires ONCE per publication, after it, carrying the agent's
    # comprehensive handoff — never on an ordinary turn. It used to fire on the
    # first Stop of a session, freeze a generic "Continue work in <repo>"
    # capsule from turn one, and idempotent-skip every turn after.
    started_at = pp.prefetch_started_at(contract, receipt_id)
    pending = [
        (root, pub) for root in roots if (pub := _pending_publication(root, started_at)) is not None
    ]
    if not pending:
        _record(contract, session_id, status="no_publication", roots=[str(r) for r in roots])
        return 0

    try:
        total_budget = float(os.environ.get("L9_MEMORY_WRITEBACK_BUDGET", DEFAULT_TOTAL_BUDGET))
    except ValueError:
        total_budget = DEFAULT_TOTAL_BUDGET
    deadline = time.monotonic() + total_budget

    announcements: list[str] = []
    statuses: list[str] = []
    for root, pub in pending:
        key = pub["key"]
        handoff, handoff_error = None, ""
        missing: dict[str, str] = {}
        try:
            handoff = session_handoff.load(root, pr_number=pub["number"])
        except session_handoff.HandoffError as exc:
            handoff_error = str(exc)
            missing[str(session_handoff.HANDOFF_REL)] = handoff_error
        try:
            governance_handoff.load(root, pr_number=pub["number"])
        except session_handoff.HandoffError as exc:
            missing[str(governance_handoff.GOVERNANCE_REL)] = str(exc)
        ledger_rel = HANDOFF_LEDGER_REL
        if (
            missing
            and not pp.ledger(root, ledger_rel, key).get("requested")
            and not event.get("stop_hook_active")
        ):
            # Ask ONCE, for both handoffs in one reason: this is the only hook
            # that blocks (the governance hook runs in parallel and never does).
            # Blocking hands the agent the schemas and one more turn; the next
            # Stop closes with what exists and each hook announces the rest.
            pp.write_ledger(
                root,
                ledger_rel,
                key,
                {"requested": True, "request_missing": missing},
                who="memory-writeback",
            )
            _record(contract, session_id, status="handoff_requested", publication=key)
            gov_rel = str(governance_handoff.GOVERNANCE_REL)
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": session_handoff.request_reason(
                            pr_label=pub["label"],
                            pr_number=pub["number"],
                            missing=missing,
                            governance=(
                                gov_rel,
                                governance_handoff.GOVERNANCE_SCHEMA,
                                governance_handoff.example(pub["number"]),
                            ),
                        ),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        # Asked and the repository brief is still absent or invalid: close with
        # what the session has, and say LOUDLY that the handoff was not captured.

        left = max(MIN_ROOT_BUDGET, deadline - time.monotonic())
        try:
            report = close_session(
                project_dir=root,
                session_id=session_id,
                reason=f"published {pub['label']}",
                transcript_path=event.get("transcript_path") or event.get("transcriptPath"),
                agent_id=agent_id,
                is_background_agent=False,
                dry_run=False,
                budget=left,
                surface="claude-session-end",
                handoff=handoff,
                publication=key,
            )
        except Exception as exc:  # noqa: BLE001 - fail-open, but never silent
            report = {"status": "error", "writes": [], "warnings": [type(exc).__name__]}
        text = compose_handoff_announcement(session_id, root, pub, report, handoff, handoff_error)
        announcements.append(text)
        statuses.append(f"{root.name}={report.get('status')}")
        pp.write_ledger(
            root,
            ledger_rel,
            key,
            {
                "requested": True,
                "closed": str(report.get("status")),
                "handoff_captured": handoff is not None,
                "handoff_error": handoff_error,
                "continuation": (report.get("continuation") or {}).get("record_id"),
                "announcement": text,
            },
            who="memory-writeback",
        )

    announcement = "\n\n".join(announcements)
    _emit(announcement)
    _record(
        contract,
        session_id,
        announcement=announcement,
        status="ran",
        transport="memory-control-plane/v1",
        close_status=";".join(statuses) or "none",
        publications=[pub["key"] for _, pub in pending],
    )
    # Exit 0 either way: the Stop hook contract is fail-open and must not block
    # session termination. Observability lives in the announcement and receipt.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
