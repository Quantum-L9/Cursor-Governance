#!/usr/bin/env python3
"""Stop hook — the post-publish GOVERNANCE handoff, written to cursor-governance.

Registered as a second ``Stop`` hook beside ``memory_writeback.py``; Claude Code
runs the two IN PARALLEL. Where that hook closes the in-scope repository with
the repository brief, this one writes the governance brief
(``.l9/memory/governance-handoff.json``, schema ``l9.governance_handoff.v1``) —
environment friction, environment/governance blockers, degraded bootstrap
items, workarounds, governance actions — as ONE observation record to the
``cursor-governance`` namespace and nowhere else. The
``claude-governance-handoff`` hook surface refuses any other namespace
client-side, before a process is spawned.

WHEN: once per publication of this session, never on an ordinary turn. This
hook never blocks: the single request for both handoffs is made by
``memory_writeback.py`` (concurrent ``decision: block`` outputs have no
documented merge). So the first Stop after a publication with no governance
brief only ARMS this hook's ledger; the next Stop writes whatever exists.

What it adds without authoring anything: an ``observed`` block copied verbatim
from receipts — the bootstrap receipt when it is not READY, the SessionStart
prefetch receipt when it is degraded, and hook skips logged since this session
started. A degraded bootstrap is therefore recorded even when the agent wrote
no brief (CANONICAL_LAW §8.6: hooks prepare material, never author it).

Every outcome is ANNOUNCED to the user as a Stop-hook ``systemMessage``:
WRITTEN, PARTIAL, FAILED, NOT CAPTURED, or NOTHING TO REPORT — never silence
after a publication.
"""

from __future__ import annotations

import calendar
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

MEM = Path(__file__).resolve().parent.parent / "memory"


def _governance_lib() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "scripts" / "lib"
        if (candidate / "workspace_roots.py").is_file():
            return candidate
    raise ModuleNotFoundError("ops/scripts/lib/workspace_roots.py not found above this hook")


_GOV_LIB = _governance_lib()
for _p in (str(_GOV_LIB), str(MEM)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import memory_bridge as mb  # noqa: E402
import memory_state as st  # noqa: E402
import post_publish as pp  # noqa: E402
from workspace_roots import workspace_roots as _shared_workspace_roots  # noqa: E402

#: Hook-lane surface (ops/config/memory-hook-envelopes.json): write, 1 observation
#: record, 16 KiB, namespaces [cursor-governance].
GOVERNANCE_SURFACE = "claude-governance-handoff"
GOVERNANCE_LEDGER_REL = Path(".l9") / "memory" / "governance-handoffs"
RECEIPT_SUFFIX = ".governance-handoff"
SKIP_LOG_LINES = 20

#: Bound by main() once the governance tree is importable.
governance_handoff: Any = None


def _record(contract: dict, session_id: str, **fields: object) -> None:
    try:
        st.write_receipt(contract, f"{session_id}{RECEIPT_SUFFIX}", dict(fields))
    except OSError as exc:
        print(f"governance-handoff: status not persisted ({type(exc).__name__})", file=sys.stderr)


def _previous(contract: dict, session_id: str) -> dict:
    try:
        path = st.receipt_path(contract, f"{session_id}{RECEIPT_SUFFIX}")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


# --- Observed: verbatim copies of receipts, never inference -----------------


def _observe_bootstrap() -> dict | None:
    """The bootstrap receipt through its single reader (ops/scripts), when not READY."""
    path = _GOV_LIB.parent / "claude_bootstrap_receipt.py"
    spec = importlib.util.spec_from_file_location("l9_claude_bootstrap_receipt", path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"bootstrap receipt reader not loadable at {path}")
    cbr = importlib.util.module_from_spec(spec)
    # The reader imports its sibling governance_refresh_receipt by bare name.
    scripts = str(path.parent)
    added = scripts not in sys.path
    if added:
        sys.path.insert(0, scripts)
    try:
        spec.loader.exec_module(cbr)
    finally:
        if added:
            sys.path.remove(scripts)
    return bootstrap_observation(cbr.read(), ready=cbr.READY)


def bootstrap_observation(verdict: dict, *, ready: str) -> dict | None:
    """The reader's verdict, copied, when it is not ready.

    ``ready`` is the reader's own constant: its verdict states are lowercase
    ("ready") while component values in the receipt are uppercase ("READY").
    Comparing against a literal "READY" recorded every healthy bootstrap as
    degraded.
    """
    if str(verdict.get("state")) == ready:
        return None
    components = verdict.get("components") or {}
    reasons = verdict.get("reasons") or {}
    return {
        "state": verdict.get("state"),
        "reason": verdict.get("reason"),
        "not_ready": {k: v for k, v in components.items() if str(v).upper() != "READY"},
        "reasons": {k: v for k, v in reasons.items() if v},
        "generated_at": verdict.get("generated_at"),
    }


def _observe_prefetch(contract: dict, receipt_id: str) -> dict | None:
    data = pp.prefetch_receipt(contract, receipt_id)
    if not data.get("degraded"):
        return None
    return {"status": data.get("status"), "memory_statuses": data.get("memory_statuses")}


def _observe_hook_skips(started_at: float) -> list[str]:
    log = Path(os.environ.get("L9_HOOK_SKIP_LOG") or Path.home() / ".l9/claude/hook-skips.log")
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    since: list[str] = []
    for line in lines:
        stamp = line.split(" ", 1)[0]
        try:
            epoch = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            continue
        if epoch >= started_at:
            since.append(line.strip())
    return since[-SKIP_LOG_LINES:]


def collect_observed(contract: dict, receipt_id: str, started_at: float) -> dict[str, Any]:
    """Only what is NOT healthy; a collector that fails is itself observed."""
    observed: dict[str, Any] = {}
    probes = (
        ("bootstrap_receipt", _observe_bootstrap),
        ("memory_prefetch", lambda: _observe_prefetch(contract, receipt_id)),
        ("hook_skips_this_session", lambda: _observe_hook_skips(started_at)),
    )
    for name, probe in probes:
        try:
            value = probe()
        except Exception as exc:  # noqa: BLE001 - reported inside the record, never silent
            value = f"collector failed: {type(exc).__name__}: {str(exc)[:160]}"
        if value:
            observed[name] = value
    return observed


# --- Announcement --------------------------------------------------------------


def _outcome_line(outcome: object) -> tuple[bool, str]:
    if getattr(outcome, "ok", False):
        receipt = getattr(outcome, "receipt", None)
        ident = getattr(receipt, "record_id", None) or getattr(receipt, "receipt_id", None)
        return True, f"written, id {ident or 'no id'}"
    status = getattr(outcome, "status", "?")
    error = " ".join(str(getattr(outcome, "error", "") or "").split())[:300]
    return False, f"NOT written ({status}: {error})"


def compose_announcement(
    pub: dict,
    session_id: str,
    brief: dict | None,
    brief_error: str,
    observed: dict,
    outcome: object | None,
) -> str:
    gh = governance_handoff
    namespace = gh.GOVERNANCE_NAMESPACE
    if outcome is None:
        title = "NOTHING TO REPORT" if brief is not None else "NOT CAPTURED"
    else:
        ok, _ = _outcome_line(outcome)
        title = ("WRITTEN" if brief is not None else "PARTIAL") if ok else "FAILED"
    lines = [
        f"L9 GOVERNANCE HANDOFF — {title} ({pub['label']}, session {session_id}, "
        f"agent {os.environ.get('L9_MEMORY_AGENT_ID') or 'unknown-agent'})",
        f"target: namespace {namespace} ONLY (never the repository's)",
    ]
    if outcome is not None:
        lines.append(f"• observation record: {_outcome_line(outcome)[1]}")
    else:
        lines.append("• no record written")
    if brief is None:
        lines.append(
            f"  AGENT GOVERNANCE HANDOFF NOT CAPTURED: {brief_error or 'no file'} "
            f"({gh.GOVERNANCE_REL})"
        )
    else:
        lines.extend(f"  {line}" for line in gh.render_sections(brief))
    lines.extend(f"  {line}" for line in gh.render_observed(observed))
    if outcome is not None and getattr(outcome, "ok", False):
        lines.append(
            "  verify (any later session): ~/.cursor-governance/.venv/bin/python -m "
            f'ops.memory.cli search "{pub["key"]}" --workspace ~/.cursor-governance'
        )
    return "\n".join(lines)


# --- Hook ------------------------------------------------------------------------


def _write(text: str, pub: dict, session_id: str) -> object:
    gov = mb.find_governance_root()
    try:
        client = mb.memory_client(session_id, surface=GOVERNANCE_SURFACE)
        return client.write(
            text,
            workspace=str(gov),
            namespace=governance_handoff.GOVERNANCE_NAMESPACE,
            memory_class="observation",
            tags=[
                "governance-handoff",
                f"repo:{pub['repo']}",
                f"publication:{pub['key']}",
                f"agent:{os.environ.get('L9_MEMORY_AGENT_ID') or 'unknown-agent'}",
            ],
            idempotency_key=f"governance-handoff:{pub['key']}",
            source="claude-post-publish-governance-handoff",
            source_id=pub["key"],
        )
    except Exception as exc:  # noqa: BLE001 - reported, never silent
        return _Failure(exc)


class _Failure:
    ok = False
    receipt = None

    def __init__(self, exc: Exception) -> None:
        self.status = f"error:{type(exc).__name__}"
        self.error = str(exc)[:200]


def _runtime_failure(contract: dict, session_id: str, error: str) -> None:
    """Announce (once per state) that the hook could not load, then record it."""
    message = (
        f"L9 GOVERNANCE HANDOFF — FAILED (session {session_id}): the hook could not load "
        f"({error}); no governance handoff can be written until this is repaired."
    )
    if _previous(contract, session_id).get("status") != "runtime_error":
        pp.emit(message)
    _record(contract, session_id, status="runtime_error", error=error, interpreter=sys.executable)


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
        return 0
    try:
        receipt_id = st.resolve_receipt_id(event=event)
    except ValueError:
        receipt_id = ""
    if not st.usable_receipt(contract, receipt_id):
        # memory_writeback announces the missing prefetch; with no session
        # start there is no publication window to hand off. usable, not fresh:
        # a DEGRADED hydration is exactly the session this hook must report.
        return 0

    roots = pp.session_roots(contract, receipt_id, _shared_workspace_roots, st.workspace_root())
    started_at = pp.prefetch_started_at(contract, receipt_id)
    pending = []
    for root in roots:
        pub = pp.publication(root, started_at)
        if pub and not pp.ledger(root, GOVERNANCE_LEDGER_REL, pub["key"]).get("done"):
            pending.append((root, pub))
    if not pending:
        _record(contract, session_id, status="no_publication")
        return 0

    if not st.bind_identity_env():
        reason = st.unresolved_identity_reason()
        if _previous(contract, session_id).get("status") != "identity_unresolved":
            pp.emit(
                f"L9 GOVERNANCE HANDOFF — FAILED (session {session_id}): no memory identity "
                f"for this surface ({reason}); nothing was written."
            )
        _record(contract, session_id, status="identity_unresolved", reason=reason)
        return 0
    mb.ensure_importable()
    global governance_handoff  # noqa: PLW0603 - bound once per hook run
    try:
        from ops.memory.governance_handoff import GOVERNANCE_SCHEMA  # noqa: F401

        governance_handoff = sys.modules["ops.memory.governance_handoff"]
    except Exception as exc:  # noqa: BLE001 - fail-open, but never silent
        _runtime_failure(contract, session_id, f"{type(exc).__name__}: {exc}")
        return 0

    announcements: list[str] = []
    for root, pub in pending:
        key = pub["key"]
        ledger = pp.ledger(root, GOVERNANCE_LEDGER_REL, key)
        try:
            brief, brief_error = governance_handoff.load(root, pr_number=pub["number"]), ""
        except governance_handoff.HandoffError as exc:
            brief, brief_error = None, str(exc)
            if not ledger.get("armed"):
                # First Stop after the publication: memory_writeback is asking
                # for both handoffs in parallel right now. Arm, stay silent.
                pp.write_ledger(
                    root,
                    GOVERNANCE_LEDGER_REL,
                    key,
                    {"armed": True, "arm_error": brief_error},
                    who="governance-handoff",
                )
                continue

        observed = collect_observed(contract, receipt_id, started_at)
        reported = brief is not None and not governance_handoff.is_empty(brief)
        outcome = None
        if reported or observed:
            text = governance_handoff.record_text(
                brief,
                observed,
                repository=pub["repo"],
                agent_id=os.environ.get("L9_MEMORY_AGENT_ID") or "unknown-agent",
                pr_label=pub["label"],
                session_id=session_id,
            )
            outcome = _write(text, pub, session_id)
        message = compose_announcement(pub, session_id, brief, brief_error, observed, outcome)
        announcements.append(message)
        pp.write_ledger(
            root,
            GOVERNANCE_LEDGER_REL,
            key,
            {
                "armed": True,
                "done": True,
                "captured": brief is not None,
                "brief_error": brief_error,
                "written": bool(getattr(outcome, "ok", False)),
                "record": getattr(getattr(outcome, "receipt", None), "record_id", None),
                "announcement": message,
            },
            who="governance-handoff",
        )

    if not announcements:
        _record(contract, session_id, status="armed", publications=[p["key"] for _, p in pending])
        return 0
    announcement = "\n\n".join(announcements)
    pp.emit(announcement)
    _record(
        contract,
        session_id,
        status="ran",
        announcement=announcement,
        publications=[p["key"] for _, p in pending],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
