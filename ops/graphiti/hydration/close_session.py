"""sessionEnd close (campaign stages C5/C6): canonical candidate + memory.close.

Close sequence (plan §15):

    1. gather session state (transcript excerpt, git HEAD, identity)
    2. construct ContinuationCapsuleV2 (heuristic gathering — Phase A)
    3. canonical serialize + digest
    4. submit it as a governed candidate through the memory control plane
    5. validate the candidate receipt (admitted / duplicate / rejected / quarantined)
    6. keep the canonical reference (record id, capsule digest)
    7. build the close summary
    8. memory.close (idempotent: one key per session + transcript head)
    9. validate the CloseReceipt
   10. only then mark the local obligation CLOSED_CANONICALLY

A rejected continuation does not falsify the close; the close still commits
with ``continuation_status=rejected``. A failed close leaves the obligation
``close_incomplete``, never ``closed``. Nothing here writes to a provider:
Graphiti receives new records only through canonical projection (plan §29,
stage 3), and no rollback path may restore a direct write (plan §30).

``budget`` stays a per-call ceiling: a caller closing several repositories in
one hook window divides its own allowance. Phase A (capsule admission + close)
is always attempted. Distillation of the redacted excerpt is a canonical
``l9-memory distill`` operation (ADR-0033); no local cognition runs here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_FILE_RE = re.compile(r"[\w./-]+\.(?:py|md|ya?ml|json|sh|ts|tsx|js|jsx)")

_GRAPHITI_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _GRAPHITI_DIR.parent.parent
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.graphiti.hydration import session_latches as _latches  # noqa: E402
from ops.graphiti.hydration.identity import IdentityError, resolve_write_identity  # noqa: E402
from ops.graphiti.hydration.transcript import load_transcript_excerpt  # noqa: E402
from ops.memory.control_plane_client import (  # noqa: E402
    MemoryControlPlaneClient,
    OperationOutcome,
    OutcomeStatus,
)
from ops.memory.namespace_context import (  # noqa: E402
    repository_state_digest,
    resolve_namespace_context,
)
from ops.memory.runtime_binding import resolve_runtime_binding  # noqa: E402
from ops.memory.session_contracts import ContinuationCapsuleV2  # noqa: E402
from ops.memory.session_state import read_session_state  # noqa: E402

PHASE_A_BUDGET = 8.0
TOTAL_BUDGET = 30.0
#: Minimum time left after the close for the canonical distill to be attempted.
DISTILL_MIN_BUDGET = 3.0

STATUS_CLOSED_CANONICALLY = _latches.STATUS_CLOSED_CANONICALLY
STATUS_CLOSE_INCOMPLETE = _latches.STATUS_CLOSE_INCOMPLETE
STATUS_CLOSE_CONFLICTED = _latches.STATUS_CLOSE_CONFLICTED
PRODUCER_VERSION = "2.0.0"


def re_safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]


def _closes_dir(project_dir: Path) -> str:
    """Real path to project_dir/.l9/memory/closes (must stay under project root)."""
    return _latches.closes_dir(project_dir)


def already_closed(project_dir: Path, session_id: str, head_hash: str) -> bool:
    try:
        path_r = _latches.receipt_path(project_dir, session_id)
    except ValueError:
        return False
    if not os.path.isfile(path_r):
        return False
    try:
        # path_r is commonpath-bounded under project_dir/.l9/memory/closes
        with open(path_r, encoding="utf-8") as handle:  # NOSONAR python:S2083
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False
    return _latches.receipt_is_successful_close(data) and (
        data.get("head_hash") == head_hash or data.get("status") == STATUS_CLOSED_CANONICALLY
    )


def write_receipt(project_dir: Path, session_id: str, payload: dict[str, Any]) -> None:
    """Persist the close obligation with taint-safe scalars only (plan §16)."""
    _latches.write_receipt(project_dir, session_id, payload)


#: Default hook-lane surface for a close (ADR-0033 B7). The Claude Stop hook
#: passes ``claude-session-end``; both envelopes live in
#: ``ops/config/memory-hook-envelopes.json``.
DEFAULT_CLOSE_SURFACE = "cursor-session-end"


def memory_client(
    session_id: str | None = None, *, surface: str | None = DEFAULT_CLOSE_SURFACE
) -> MemoryControlPlaneClient:
    """The bound memory runtime under the close surface's envelope.

    Tests substitute a scripted CLI here. ``surface=None`` is the operator
    form (no envelope) and is reserved for ``ops.memory.cli``.
    """
    return MemoryControlPlaneClient(
        resolve_runtime_binding(), session_id=session_id, surface=surface
    )


def _git_signal(project_dir: Path) -> str:
    """Project basename only — no git filesystem reads (avoids path-injection sinks)."""
    name = Path(project_dir).name
    if not _SAFE_NAME.match(name):
        name = "project"
    return f"project={name}"


def _heuristic_pickup(
    *,
    project_dir: Path,
    session_id: str,
    transcript: str,
    reason: str,
) -> dict[str, Any]:
    git = _git_signal(project_dir)
    last_lines = [ln for ln in transcript.splitlines() if ln.strip()][-8:]
    slice_text = "\n".join(last_lines)[:1500]
    objective = f"Continue work in {project_dir.name}"
    next_action = "Resume from the canonical continuation and the user request"
    for ln in reversed(last_lines):
        low = ln.lower()
        if low.startswith("user:") or "user_query" in low:
            next_action = ln.split(":", 1)[-1].strip()[:400] or next_action
            break
    files = []
    for match in _FILE_RE.findall(transcript):
        if match not in files:
            files.append(match)
        if len(files) >= 12:
            break
    return {
        "active_objective": objective,
        "next_action": next_action,
        "context_slice": f"{git}\nreason={reason}\nsession={session_id}\n{slice_text}"[:3500],
        "blockers": [],
        "active_files": files,
    }


def build_capsule(
    *,
    session_id: str,
    repository_identity: str,
    head: str | None,
    pickup: dict[str, Any],
    decisions: list[str] | None = None,
    unfinished_work: list[str] | None = None,
    task_signature: str | None = None,
) -> ContinuationCapsuleV2:
    """The Cursor-owned continuation capsule for this session (plan §12).

    ``task_signature`` is the signature the session hydrated under (its local
    session state); the capsule carries it so the next hydration of the same
    task selects this capsule and no other task's (audit P1-02). Without one
    the capsule derives its signature from its own objective.
    """
    return ContinuationCapsuleV2(
        session_id=session_id,
        repository_identity=repository_identity,
        objective=str(pickup.get("active_objective") or "").strip() or "Continue work",
        next_action=str(pickup.get("next_action") or "").strip() or "Proceed from user request",
        repository_state_digest=head or "unknown",
        producer_version=PRODUCER_VERSION,
        task_signature=str(task_signature or "").strip(),
        active_files=tuple(str(f) for f in pickup.get("active_files") or ())[:12],
        blockers=tuple(str(b) for b in pickup.get("blockers") or ())[:8],
        decisions=tuple(decisions or ())[:8],
        unfinished_work=tuple(unfinished_work or ())[:8],
    )


def session_task_signature(session_id: str) -> str | None:
    """The task signature this session hydrated under, from local session state.

    Local state is evidence, never authority: it only tells the close which
    task the continuation belongs to. Absent state means the capsule derives
    its own signature from its objective.
    """
    state = read_session_state(session_id)
    if not state:
        return None
    signature = state.get("task_signature")
    return str(signature).strip() or None if signature else None


def close_idempotency_key(namespace: str, session_id: str, head_hash: str) -> str:
    """Stable operation identity: producer, namespace, session, transcript head."""
    return f"cursor-close:{namespace}:{session_id}:{head_hash}"


def _distill_enabled() -> bool:
    return os.environ.get("L9_MEMORY_DISTILL", "1").strip() not in ("0", "false", "False")


def _canonical_distill(
    client: MemoryControlPlaneClient,
    *,
    project: Path,
    workspace: str,
    namespace: str,
    repository: str | None,
    session_id: str,
    transcript: str,
    report: dict[str, Any],
    remaining: float,
    dry_run: bool,
) -> None:
    """Hand the redacted excerpt to canonical ``l9-memory distill`` (ADR-0033).

    The hook lane prepares the excerpt (load + cap + PII redact, already done
    by ``load_transcript_excerpt``) and writes it to a bounded path under
    ``.l9/memory/distill``; memory extracts and admits every atomic candidate
    through its own ``MemoryService.write``. Nothing here reads a provider,
    scores a candidate or promotes a class, and no outcome here can turn a
    canonical close into a non-close.
    """
    if not _distill_enabled():
        report["warnings"].append("distill skipped: L9_MEMORY_DISTILL=0")
        return
    if remaining < DISTILL_MIN_BUDGET:
        report["warnings"].append("distill skipped: insufficient time budget")
        return
    excerpt = (transcript or "").strip()
    if not excerpt:
        report["warnings"].append("distill skipped: empty transcript excerpt")
        return
    try:
        source = _latches.distill_source_path(project, session_id)
        os.makedirs(os.path.dirname(source), exist_ok=True)
        with open(source, "w", encoding="utf-8") as handle:  # NOSONAR python:S2083
            handle.write(excerpt + "\n")
    except (OSError, ValueError) as exc:
        report["warnings"].append(f"distill skipped: excerpt not written ({type(exc).__name__})")
        return
    outcome = client.distill(
        workspace=workspace,
        namespace=namespace,
        source_path=source,
        repository=repository,
        dry_run=dry_run,
        timeout=remaining,
    )
    report["writes"].append(_write_entry(outcome, kind="distill"))
    receipt = outcome.receipt
    report["distill"] = {
        "status": outcome.status.value,
        "candidate_count": getattr(receipt, "candidate_count", None),
        "written_count": getattr(receipt, "written_count", None),
        "rejected_count": len(getattr(receipt, "rejected_items", ()) or ()),
        "record_ids": list(getattr(receipt, "record_ids", ()) or ()),
        "source_digest": getattr(receipt, "source_digest", None),
        "extractor": getattr(receipt, "extractor", None),
        "error": outcome.error,
    }
    if outcome.status not in {OutcomeStatus.OK, OutcomeStatus.NO_HITS, OutcomeStatus.NOT_COMMITTED}:
        report["warnings"].append(f"distill {outcome.status.value}: {outcome.error or 'no detail'}")


def _write_entry(outcome: OperationOutcome, *, kind: str) -> dict[str, Any]:
    """A canonical operation as it appears in ``report["writes"]`` (no content)."""
    receipt = outcome.receipt
    return {
        "kind": kind,
        "operation": outcome.operation,
        "status": outcome.status.value,
        "written": outcome.ok,
        "record_id": getattr(receipt, "record_id", None),
        "receipt_id": getattr(receipt, "receipt_id", None),
        "error": outcome.error,
        "latency_ms": outcome.latency_ms,
    }


def _persist_obligation(
    project: Path,
    session_id: str,
    report: dict[str, Any],
    *,
    status: str,
    dry_run: bool = False,
    **fields: Any,
) -> None:
    now = datetime.now(UTC).isoformat()
    receipt = {
        "status": status,
        "session_id": session_id,
        "head_hash": report.get("head_hash", ""),
        "phase_a": bool(report.get("phase_a")),
        "write_count": len([w for w in (report.get("writes") or []) if w.get("written")]),
        "closed_at": now,
        "attempt_timestamp": now,
        "retry_count": int(report.get("retry_count") or 0),
        **fields,
    }
    report["receipt"] = receipt
    if not dry_run:
        try:
            write_receipt(project, session_id, receipt)
        except (OSError, ValueError) as exc:
            report["warnings"].append(f"obligation write failed: {exc}")


def close_session(
    *,
    project_dir: str | Path,
    session_id: str,
    reason: str = "completed",
    transcript_path: str | None = None,
    agent_id: str | None = None,
    is_background_agent: bool = False,
    dry_run: bool = False,
    clock: Any = None,
    budget: float | None = None,
    client: MemoryControlPlaneClient | None = None,
    surface: str = DEFAULT_CLOSE_SURFACE,
) -> dict[str, Any]:
    """Canonical close. Fail-open to hooks; never raises. Never writes a provider.

    ``surface`` names the hook-lane envelope this close runs under when no
    ``client`` is injected (``cursor-session-end`` by default,
    ``claude-session-end`` from the Claude Stop hook).

    ``dry_run`` admits nothing and commits nothing: the capsule and the close
    pass memory's admission dry runs and the obligation is not persisted.
    """
    clock = clock or time.monotonic
    started = clock()
    total_budget = TOTAL_BUDGET if budget is None else max(0.0, float(budget))
    project = Path(project_dir).expanduser().resolve()
    session_id = _latches.resolve_session_id(explicit=session_id)
    report: dict[str, Any] = {
        "status": "skipped",
        "session_id": session_id,
        "reason": reason,
        "phase_a": False,
        "writes": [],
        "warnings": [],
        "continuation": None,
        "close": None,
    }

    try:
        identity = resolve_write_identity(
            explicit_agent_id=agent_id,
            surface="claude-code" if (agent_id or "").startswith("claude") else "cursor",
        )
    except IdentityError as exc:
        report["warnings"].append(str(exc))
        report["status"] = "close_failed"
        _persist_obligation(
            project,
            session_id,
            report,
            status="close_failed",
            dry_run=dry_run,
            failure_class="identity",
        )
        return report

    transcript, t_source = load_transcript_excerpt(
        transcript_path=transcript_path,
        conversation_id=session_id,
    )
    head_hash = hashlib.sha256(
        f"{session_id}:{reason}:{transcript[:2000]}:{t_source}".encode()
    ).hexdigest()[:24]
    report["head_hash"] = head_hash

    if already_closed(project, session_id, head_hash) and not dry_run:
        report["status"] = "idempotent_skip"
        return report

    context = resolve_namespace_context(project)
    namespace = context.write_namespace_hint
    if not namespace:
        msg = "; ".join(context.warnings) or "no write namespace hint"
        report["warnings"].append(f"WARN: close blocked — {msg}")
        report["status"] = "skipped"
        report["skip_reason"] = msg
        _persist_obligation(
            project,
            session_id,
            report,
            status="close_failed",
            dry_run=dry_run,
            failure_class="namespace_unresolved",
        )
        return report
    report["group_id"] = namespace
    # Memory derives the local principal (write grants) from the cwd it resolves,
    # so the CLI runs at the repository root the namespace context resolved; the
    # close obligation still lives under ``project_dir``.
    workspace = context.git_root or str(project)
    head = repository_state_digest(project)
    repository_identity = context.repository_identity or namespace

    if is_background_agent and not transcript:
        report["warnings"].append("background agent without transcript — Phase A git-only")

    client = client or memory_client(session_id, surface=surface)
    if not client.binding.ok:
        reason_text = "; ".join(client.binding.reasons) or "memory runtime unbound"
        report["warnings"].append(f"memory runtime unbound: {reason_text}")
        report["status"] = STATUS_CLOSE_INCOMPLETE
        _persist_obligation(
            project,
            session_id,
            report,
            status=STATUS_CLOSE_INCOMPLETE,
            dry_run=dry_run,
            canonical_namespace_requested=namespace,
            failure_class="BINDING_FAILED",
            last_error_code="BINDING_FAILED",
        )
        return report

    # --- Phase A: continuation capsule -> governed candidate ---
    pickup = _heuristic_pickup(
        project_dir=project, session_id=session_id, transcript=transcript, reason=reason
    )
    task_signature = session_task_signature(session_id)
    capsule = build_capsule(
        session_id=session_id,
        repository_identity=repository_identity,
        head=head,
        pickup=pickup,
        task_signature=task_signature,
    )
    candidate = capsule.to_governed_candidate(
        namespace=namespace, source_sha=head or "0" * 40, agent_id=identity["agent_id"]
    )
    admitted = client.ingest_candidate(candidate, workspace=workspace)
    report["writes"].append(_write_entry(admitted, kind="session_continuation"))
    continuation_status = (
        admitted.receipt.status if admitted.receipt is not None else admitted.status.value.lower()
    )
    continuation_reference = admitted.receipt.record_id if admitted.receipt is not None else None
    if admitted.status in {
        OutcomeStatus.CANONICAL_UNAVAILABLE,
        OutcomeStatus.TIMEOUT,
        OutcomeStatus.BINDING_FAILED,
        OutcomeStatus.INVALID_RECEIPT,
    }:
        report["warnings"].append(f"continuation not admitted: {admitted.status.value}")
    elif not admitted.ok:
        # Rejected / quarantined stays visible; the close still proceeds (plan §15).
        report["warnings"].append(
            f"continuation {continuation_status}: {admitted.error or 'no detail'}"
        )
    report["phase_a"] = admitted.ok
    report["pickup"] = {k: v for k, v in pickup.items() if k != "context_slice"}
    report["continuation"] = {
        "status": continuation_status,
        "record_id": continuation_reference,
        "capsule_digest": capsule.digest(),
        "session_id": session_id,
        "task_signature": capsule.task_signature,
    }

    key = close_idempotency_key(namespace, session_id, head_hash)
    # The obligation is on disk BEFORE the close so a kill between candidate
    # admission and memory.close leaves a visible close_incomplete, never a
    # fabricated success (adversarial test G).
    _persist_obligation(
        project,
        session_id,
        report,
        status=STATUS_CLOSE_INCOMPLETE,
        dry_run=dry_run,
        canonical_namespace_requested=namespace,
        close_idempotency_key=key,
        payload_digest=capsule.digest(),
        continuation_status=continuation_status,
        continuation_reference=continuation_reference,
        failure_class="pending_close",
    )

    elapsed_a = clock() - started
    if elapsed_a > PHASE_A_BUDGET:
        report["warnings"].append(f"Phase A over budget ({elapsed_a:.1f}s)")

    # --- memory.close: the only thing that can make this session CLOSED ---
    summary = (
        f"session {session_id} {reason}: {capsule.objective} | next: {capsule.next_action} | "
        f"continuation={continuation_status} | transcript={t_source} | {_git_signal(project)}"
    )[:2000]
    close_request = {
        "close_summary": summary,
        "close_capsule_digest": capsule.digest(),
        "close_session_id": session_id,
    }
    # The exact close request is on disk BEFORE memory.close runs, so a retry
    # of an interrupted close replays this summary and digest under this key
    # (audit P2-01) — never a synthesized "retry" summary that memory would
    # accept as an idempotent replay while the payload silently differed.
    _persist_obligation(
        project,
        session_id,
        report,
        status=STATUS_CLOSE_INCOMPLETE,
        dry_run=dry_run,
        canonical_namespace_requested=namespace,
        close_idempotency_key=key,
        payload_digest=capsule.digest(),
        continuation_status=continuation_status,
        continuation_reference=continuation_reference,
        failure_class="pending_close",
        **close_request,
    )
    closed = client.close(
        workspace=workspace,
        namespace=namespace,
        summary=summary,
        session_id=session_id,
        capsule_digest=capsule.digest(),
        idempotency_key=key,
        dry_run=dry_run,
    )
    report["writes"].append(_write_entry(closed, kind="close"))
    close_receipt = closed.receipt
    replay_matched = getattr(close_receipt, "replay_payload_matched", None)
    report["close"] = {
        "status": closed.status.value,
        "receipt_id": getattr(close_receipt, "receipt_id", None),
        "record_id": getattr(close_receipt, "record_id", None),
        "replayed": bool(getattr(close_receipt, "replayed", False)),
        "replay_payload_matched": replay_matched,
        "warnings": list(getattr(close_receipt, "warnings", ()) or ()),
        "idempotency_key": key,
        "error": closed.error,
    }
    if getattr(close_receipt, "payload_drifted", False):
        report["warnings"].append(
            "close replay payload drift: memory replayed the close under this key but the "
            "stored close differs from this request (see close.warnings)"
        )

    if closed.status is OutcomeStatus.IDEMPOTENCY_CONFLICT:
        # CG-P1-01. Ahead of the committed promotion below: memory returned a
        # committed record, but it is the *first* close under this key, not
        # this one. The obligation stays open and conflicted.
        final_status = STATUS_CLOSE_CONFLICTED
        failure_class = closed.status.value
        report["status"] = STATUS_CLOSE_CONFLICTED
        report["warnings"].append(f"close idempotency conflict: {closed.error or 'no detail'}")
    elif closed.ok and close_receipt is not None and close_receipt.committed:
        final_status = STATUS_CLOSED_CANONICALLY
        failure_class = None
        report["status"] = STATUS_CLOSED_CANONICALLY
    elif dry_run and closed.status is OutcomeStatus.NOT_COMMITTED:
        final_status = STATUS_CLOSE_INCOMPLETE
        failure_class = "dry_run"
        report["status"] = "dry_run"
    else:
        final_status = STATUS_CLOSE_INCOMPLETE
        failure_class = closed.status.value
        report["status"] = STATUS_CLOSE_INCOMPLETE
        report["warnings"].append(f"close {closed.status.value}: {closed.error or 'no detail'}")

    _persist_obligation(
        project,
        session_id,
        report,
        status=final_status,
        dry_run=dry_run,
        canonical_namespace_requested=namespace,
        close_idempotency_key=key,
        payload_digest=capsule.digest(),
        continuation_status=continuation_status,
        continuation_reference=continuation_reference,
        canonical_operation_id=getattr(close_receipt, "receipt_id", None),
        failure_class=failure_class,
        last_error_code=None if final_status == STATUS_CLOSED_CANONICALLY else closed.status.value,
        **close_request,
    )
    # --- canonical distill: supplementary lifecycle capture, after the close ---
    # The close above is what makes the session CLOSED; distillation of the
    # redacted excerpt is memory's own cognition and rides after it, bounded
    # by whatever budget is left, and never changes the close verdict.
    _canonical_distill(
        client,
        project=project,
        workspace=workspace,
        namespace=namespace,
        repository=repository_identity,
        session_id=session_id,
        transcript=transcript,
        report=report,
        remaining=total_budget - (clock() - started),
        dry_run=dry_run,
    )
    report["elapsed_s"] = round(clock() - started, 3)
    if report["elapsed_s"] > total_budget:
        report["warnings"].append(f"close over budget ({report['elapsed_s']:.1f}s)")
    return report
