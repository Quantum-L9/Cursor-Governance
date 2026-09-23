#!/usr/bin/env python3
"""Stop-hook write-back — the post-publish handoff close (stage C8).

WHEN: once per publication of this session, after it — never on an ordinary
turn. The first Stop after ``make pr`` asks the agent (once) for the
comprehensive handoff (``.l9/memory/handoff.json``, l9.session_handoff.v1);
the next Stop closes the in-scope repository with that brief carried in its
continuation capsule, routes ``governance_friction`` to cursor-governance only,
and announces exactly what was written — or loudly, what was not.

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
memory_client: Any = None


def _bind_runtime(close_module: Any, handoff_module: Any) -> None:
    global session_handoff, memory_client  # noqa: PLW0603 - bound once per hook run
    session_handoff = handoff_module
    memory_client = close_module.memory_client


#: Per-publication ledger: one handoff request and one close per publication.
HANDOFF_LEDGER_REL = Path(".l9") / "memory" / "handoffs"
PR_SUMMARY_REL = Path(".l9") / "pr" / "pr-summary.json"
FRICTION_NAMESPACE = "cursor-governance"
FRICTION_SURFACE = "claude-governance-friction"


def _safe(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:180]


def _ledger(root: Path, key: str) -> dict:
    try:
        return json.loads((root / HANDOFF_LEDGER_REL / f"{_safe(key)}.json").read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_ledger(root: Path, key: str, fields: dict) -> None:
    path = root / HANDOFF_LEDGER_REL / f"{_safe(key)}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {**_ledger(root, key), **fields, "publication": key, "updated_at": time.time()}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")
    except OSError as exc:
        print(f"memory-writeback: ledger not written ({type(exc).__name__})", file=sys.stderr)


def _prefetch_started_at(contract: dict, receipt_id: str) -> float:
    try:
        data = json.loads(st.receipt_path(contract, receipt_id).read_text(encoding="utf-8"))
        return float(data.get("created_at") or 0)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0.0


def _pending_publication(root: Path, started_at: float) -> dict | None:
    """This session's newest publication in ``root`` that has not closed yet.

    The publish receipt (``.l9/pr/pr-summary.json``, written by make pr) must
    post-date this session's prefetch — a container can outlive a session, and
    an earlier session's publication is not this one's to hand off.
    """
    path = root / PR_SUMMARY_REL
    try:
        if path.stat().st_mtime < started_at:
            return None
        summary = json.loads(path.read_text(encoding="utf-8"))
        number = int(summary["number"])
        repo = str(summary["repo"])
        head_sha = str(summary.get("head_sha") or "")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    key = f"{repo}#{number}@{head_sha[:12]}"
    if _ledger(root, key).get("closed"):
        return None
    return {
        "key": key,
        "repo": repo,
        "number": number,
        "url": str(summary.get("url") or ""),
        "label": f"{repo}#{number}",
    }


def _record_id(outcome: object) -> str | None:
    receipt = getattr(outcome, "receipt", None)
    return getattr(receipt, "record_id", None) or getattr(receipt, "receipt_id", None)


def _write_friction(friction: list[dict], pub: dict, key: str) -> object:
    """Governance friction → Cursor-Governance ONLY, on its own hook surface."""
    gov = Path.home() / ".cursor-governance"
    try:
        client = memory_client(surface=FRICTION_SURFACE)
        return client.write(
            session_handoff.friction_text(friction, repository=pub["repo"], pr=pub["label"]),
            workspace=str(gov),
            namespace=FRICTION_NAMESPACE,
            memory_class="observation",
            tags=["governance-friction", f"repo:{pub['repo']}", "agent:claude-code"],
            idempotency_key=f"friction:{key}",
            source="claude-post-publish-handoff",
            source_id=key,
        )
    except Exception as exc:  # noqa: BLE001 - reported, never silent
        return _FrictionFailure(exc)


class _FrictionFailure:
    """An outcome stand-in for a friction write that raised, reported like one."""

    ok = False
    receipt = None

    def __init__(self, exc: Exception) -> None:
        self.status = f"error:{type(exc).__name__}"
        self.error = str(exc)[:200]


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
    friction: list[dict],
    friction_outcome: object,
    handoff_error: str,
) -> str:
    """The formal record of what the post-publish close wrote — or failed to."""
    wrote = any(w.get("written") for w in _writes(report))
    closed = str(report.get("status")) == "closed_canonically"
    friction_ok = not friction or bool(getattr(friction_outcome, "ok", False))
    if closed and brief is not None and friction_ok:
        title = "WRITTEN"
    elif wrote:
        title = "PARTIAL"
    else:
        title = "FAILED"
    lines = [
        f"L9 MEMORY HANDOFF — {title} ({pub['label']}, session {session_id}, agent claude-code)",
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
    if friction:
        state = (
            f"written, id {_record_id(friction_outcome)}"
            if getattr(friction_outcome, "ok", False)
            else f"NOT written ({getattr(friction_outcome, 'status', '?')}: "
            f"{_clip(getattr(friction_outcome, 'error', '') or '')})"
        )
        lines.append(
            f"• governance friction → namespace {FRICTION_NAMESPACE}: {len(friction)} item(s), "
            f"{state}"
        )
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
        # ``from <full.dotted.module> import name`` resolves the module through
        # sys.modules by its full name (never a stale package attribute left by
        # an earlier import) and still goes through __import__, so an import
        # failure is raised HERE and classified below.
        from ops.graphiti.hydration.close_session import close_session
        from ops.memory.session_handoff import HANDOFF_SCHEMA  # noqa: F401

        _bind_runtime(
            sys.modules["ops.graphiti.hydration.close_session"],
            sys.modules["ops.memory.session_handoff"],
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
    started_at = _prefetch_started_at(contract, receipt_id)
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
        try:
            handoff = session_handoff.load(root, pr_number=pub["number"])
        except session_handoff.HandoffError as exc:
            ledger = _ledger(root, key)
            if not ledger.get("requested") and not event.get("stop_hook_active"):
                # Ask once. Blocking this Stop hands the agent the schema and one
                # more turn to write the brief; the next Stop closes with it.
                _write_ledger(root, key, {"requested": True, "request_error": str(exc)})
                _record(contract, session_id, status="handoff_requested", publication=key)
                print(
                    json.dumps(
                        {
                            "decision": "block",
                            "reason": session_handoff.request_reason(
                                pr_label=pub["label"], pr_number=pub["number"]
                            ),
                        },
                        ensure_ascii=False,
                    )
                )
                return 0
            # Asked and still absent or invalid: close with what the session
            # has, and say LOUDLY that the handoff was not captured.
            handoff = None
            handoff_error = str(exc)
        else:
            handoff_error = ""

        repo_brief, friction = session_handoff.split(handoff) if handoff else (None, [])
        left = max(MIN_ROOT_BUDGET, deadline - time.monotonic())
        try:
            report = close_session(
                project_dir=root,
                session_id=session_id,
                reason=f"published {pub['label']}",
                transcript_path=event.get("transcript_path") or event.get("transcriptPath"),
                agent_id="claude-code",
                is_background_agent=False,
                dry_run=False,
                budget=left,
                surface="claude-session-end",
                handoff=repo_brief,
                publication=key,
            )
        except Exception as exc:  # noqa: BLE001 - fail-open, but never silent
            report = {"status": "error", "writes": [], "warnings": [type(exc).__name__]}
        friction_outcome = _write_friction(friction, pub, key) if friction else None
        text = compose_handoff_announcement(
            session_id,
            root,
            pub,
            report,
            repo_brief,
            friction,
            friction_outcome,
            handoff_error,
        )
        announcements.append(text)
        statuses.append(f"{root.name}={report.get('status')}")
        _write_ledger(
            root,
            key,
            {
                "requested": True,
                "closed": str(report.get("status")),
                "handoff_captured": handoff is not None,
                "handoff_error": handoff_error,
                "continuation": (report.get("continuation") or {}).get("record_id"),
                "friction_record": _record_id(friction_outcome),
                "announcement": text,
            },
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
