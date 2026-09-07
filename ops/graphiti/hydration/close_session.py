"""sessionEnd close (campaign stages C5/C6): canonical candidate + memory.close.

Close sequence (plan §15):

    1. gather session state (transcript excerpt, git HEAD, identity)
    2. construct ContinuationCapsuleV2 (heuristic; Phase B may refine it)
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
is always attempted; a small budget only starves Phase B distillation.
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
from ops.graphiti.hydration.resume_signal_scorer import (  # noqa: E402
    should_persist_derived_episode,
    signals_from_close,
)
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
PHASE_B_BUDGET = 18.0
TOTAL_BUDGET = 30.0

STATUS_CLOSED_CANONICALLY = _latches.STATUS_CLOSED_CANONICALLY
STATUS_CLOSE_INCOMPLETE = _latches.STATUS_CLOSE_INCOMPLETE
PRODUCER_VERSION = "2.0.0"

#: Phase B promotion kinds -> canonical memory classes (write taxonomy, plan §14).
_PROMOTION_CLASSES = {"lesson": "insight", "insight": "insight", "decision": "decision"}


def re_safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]


def _closes_dir(project_dir: Path) -> str:
    """Real path to project_dir/.l9/memory/closes (must stay under project root)."""
    return _latches.closes_dir(project_dir)


def _load_rules() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "promotion_rules.yaml"
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


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


def memory_client(session_id: str | None = None) -> MemoryControlPlaneClient:
    """The bound memory runtime (tests substitute a scripted CLI here)."""
    return MemoryControlPlaneClient(resolve_runtime_binding(), session_id=session_id)


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


def _phase_b_enabled() -> bool:
    return os.environ.get("MEMORY_PHASE_B", "1").strip() not in ("0", "false", "False")


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    cleaned = text.strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned


def _distill_signal_packet(
    *,
    session_id: str,
    transcript: str,
    pickup: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any] | None, str]:
    """Return (packet, skip_reason). skip_reason empty on success.

    Uses the fixed-host OpenAI helper (``openai_fixed_host``); never builds a
    URL from caller input. Key: env or ephemeral SM resolve (opaque skip codes).
    """
    if not _phase_b_enabled():
        return None, "MEMORY_PHASE_B=0"

    from ops.graphiti.hydration.openai_fixed_host import (
        OpenAIFixedHostError,
        chat_completions,
        message_content,
    )
    from ops.graphiti.hydration.openai_key import resolve_openai_api_key

    key, key_reason = resolve_openai_api_key()
    if not key:
        return None, key_reason or "openai_key_absent"

    budget_tokens = int(os.environ.get("MEMORY_DISTILL_TOKEN_BUDGET", "300"))
    rules = _load_rules()
    system = (
        "Extract durable session signals. Output ONLY JSON with keys: "
        "promotion_decisions (list of {kind, body, decision, score}), "
        "pickup ({active_objective, next_action, context_slice, blockers}), "
        "do_not_promote (list of strings). "
        "kind in lesson|insight|decision|preference|constraint; "
        "decision in promote|defer|reject. "
        "Promote only durable facts; never dump the transcript. "
        f"Max promote items: {rules.get('max_promotions_per_close', 5)}."
    )
    user = json.dumps(
        {
            "session_id": session_id,
            "heuristic_pickup": {k: v for k, v in pickup.items() if k != "active_files"},
            "transcript_excerpt": transcript[:8000],
        },
        ensure_ascii=False,
    )
    try:
        resp = chat_completions(
            api_key=key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=budget_tokens,
            timeout=max(1.0, timeout),
        )
        data = json.loads(_strip_code_fence(message_content(resp)))
        if not isinstance(data, dict):
            return None, "distill_non_object_json"
        packet_id = hashlib.sha256(f"{session_id}:{time.time()}".encode()).hexdigest()[:16]
        return {
            "packet_id": packet_id,
            "session_id": session_id,
            "promotion_decisions": data.get("promotion_decisions") or [],
            "pickup": data.get("pickup") or pickup,
            "do_not_promote": data.get("do_not_promote") or rules.get("do_not_promote") or [],
        }, ""
    except OpenAIFixedHostError as exc:
        # Opaque codes only — never interpolate exception text (may be secret-adjacent).
        code = exc.args[0] if exc.args else "phase_b_transport"
        if code in {"openai_http_401", "openai_http_403", "openai_timeout"}:
            return None, f"phase_b_{code}"
        return None, "phase_b_transport"
    except (KeyError, json.JSONDecodeError, IndexError, OSError, TypeError) as exc:
        return None, f"phase_b_{type(exc).__name__}"


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
        "phase_b": bool(report.get("phase_b")),
        "enqueue_ok": report.get("enqueue_ok"),
        "enqueue_error": report.get("enqueue_error"),
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


def _promote(
    client: MemoryControlPlaneClient,
    *,
    workspace: str,
    namespace: str,
    session_id: str,
    decisions: list[Any],
    rules: dict[str, Any],
    report: dict[str, Any],
    dry_run: bool,
) -> int:
    """Phase B promotions through the generic canonical write (plan §14 order)."""
    promote_min = float(rules.get("promote_min_score", 0.65))
    max_promo = int(rules.get("max_promotions_per_close", 5))
    promotable = set(rules.get("promotable_kinds") or ["lesson", "insight", "decision"])
    promoted = 0
    for index, item in enumerate(decisions):
        if promoted >= max_promo:
            break
        if not isinstance(item, dict) or item.get("decision") != "promote":
            continue
        kind = str(item.get("kind") or "lesson")
        if kind not in promotable or kind not in _PROMOTION_CLASSES:
            continue
        if float(item.get("score") or 0) < promote_min:
            continue
        body = str(item.get("body") or "").strip()
        if not body:
            continue
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        outcome = client.write(
            body,
            workspace=workspace,
            namespace=namespace,
            memory_class=_PROMOTION_CLASSES[kind],
            tags=("session-close", kind),
            idempotency_key=f"cursor-promotion:{namespace}:{session_id}:{index}:{digest}",
            source_id=f"session:{session_id}",
            dry_run=dry_run,
        )
        report["writes"].append(_write_entry(outcome, kind=kind))
        if outcome.ok or outcome.status is OutcomeStatus.NOT_COMMITTED:
            promoted += 1
        else:
            report["warnings"].append(f"promote {kind} {outcome.status.value}: {outcome.error}")
    return promoted


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
) -> dict[str, Any]:
    """Canonical close. Fail-open to hooks; never raises. Never writes a provider.

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
        "phase_b": False,
        "enqueue_ok": None,
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

    client = client or memory_client(session_id)
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

    # --- Phase B: distillation may refine the capsule and promote durable facts ---
    remaining = total_budget - (clock() - started)
    rules = _load_rules()
    phase_b_budget = min(PHASE_B_BUDGET, max(0.0, remaining - 1.0))
    skip_b = False
    if not _phase_b_enabled():
        skip_b = True
        report["warnings"].append("Phase B skipped: MEMORY_PHASE_B=0")
    elif phase_b_budget < 3.0:
        skip_b = True
        report["warnings"].append("Phase B skipped: insufficient time budget")
    elif is_background_agent and not transcript:
        skip_b = True
        report["warnings"].append("Phase B skipped: background agent, no transcript")

    if not skip_b:
        signal, b_reason = _distill_signal_packet(
            session_id=session_id,
            transcript=transcript or pickup["context_slice"],
            pickup=pickup,
            timeout=phase_b_budget,
        )
        if signal is None:
            report["warnings"].append(
                f"Phase B skipped: {b_reason or 'distill failed'} — keeping Phase A"
            )
        else:
            report["phase_b"] = True
            report["signal_packet_id"] = signal.get("packet_id")
            rich = signal.get("pickup") or {}
            session_signals = signals_from_close(
                transcript=transcript,
                reason=reason,
                promotion_decisions=signal.get("promotion_decisions") or [],
            )
            persist_derived = should_persist_derived_episode(session_signals, rules)
            if not persist_derived:
                report["warnings"].append("derived continuation dropped: low resume signal")
            if rich.get("next_action") and rich.get("active_objective") and persist_derived:
                rich_capsule = build_capsule(
                    session_id=session_id,
                    repository_identity=repository_identity,
                    head=head,
                    pickup={**pickup, **rich},
                    decisions=[
                        str(d.get("body") or "")
                        for d in signal.get("promotion_decisions") or []
                        if isinstance(d, dict) and d.get("kind") == "decision"
                    ],
                    # Same task as Phase A: the refinement replaces, never forks.
                    task_signature=capsule.task_signature,
                )
                # The refinement names the Phase A record so memory supersedes
                # it on admission and one session leaves exactly one ACTIVE
                # continuation (audit P1-03). A refused supersession rejects the
                # refinement and Phase A stays ACTIVE — nothing is superseded
                # by hand here. Nothing to name when Phase A was not admitted.
                supersedes = (
                    (continuation_reference,) if admitted.ok and continuation_reference else ()
                )
                refined = client.ingest_candidate(
                    rich_capsule.to_governed_candidate(
                        namespace=namespace,
                        source_sha=head or "0" * 40,
                        agent_id=identity["agent_id"],
                        supersedes=supersedes,
                    ),
                    workspace=workspace,
                )
                report["writes"].append(_write_entry(refined, kind="session_continuation"))
                if refined.ok and refined.receipt is not None:
                    capsule = rich_capsule
                    continuation_status = refined.receipt.status
                    continuation_reference = refined.receipt.record_id
                    report["continuation"] = {
                        "status": continuation_status,
                        "record_id": continuation_reference,
                        "capsule_digest": capsule.digest(),
                        "session_id": session_id,
                        "task_signature": capsule.task_signature,
                        "refined": True,
                        "supersedes": list(supersedes),
                        "superseded_record_ids": list(refined.receipt.superseded_record_ids),
                    }
                    report["pickup"] = {k: v for k, v in rich.items() if k != "context_slice"}
                else:
                    report["warnings"].append(
                        f"Phase B continuation {refined.status.value}: {refined.error}"
                        + (" — Phase A continuation stays active" if supersedes else "")
                    )
            promoted = 0
            if persist_derived:
                promoted = _promote(
                    client,
                    workspace=workspace,
                    namespace=namespace,
                    session_id=session_id,
                    decisions=signal.get("promotion_decisions") or [],
                    rules=rules,
                    report=report,
                    dry_run=dry_run,
                )
            report["promoted"] = promoted

    # --- S3 distill enqueue (redacted excerpt; fail-loud when enabled+configured) ---
    enqueue_result: dict[str, Any] | None = None
    try:
        from ops.graphiti.distill_queue.enqueue import (
            bucket_configured,
            enqueue_enabled,
            enqueue_job,
        )

        if not enqueue_enabled():
            if os.environ.get("MEMORY_DISTILL_ENQUEUE", "1").strip() in ("0", "false", "False"):
                report["enqueue_ok"] = None
                report["warnings"].append("distill enqueue skipped: MEMORY_DISTILL_ENQUEUE=0")
            elif not bucket_configured():
                report["enqueue_ok"] = None
                report["warnings"].append("distill enqueue skipped: MEMORY_DISTILL_S3_BUCKET unset")
        elif not (transcript or "").strip():
            report["enqueue_ok"] = None
            report["warnings"].append("distill enqueue skipped: empty transcript excerpt")
        else:
            enqueue_result = enqueue_job(
                session_id=session_id,
                group_id=namespace,
                agent_id=identity["agent_id"],
                transcript_excerpt=transcript,
                heuristic_pickup=pickup,
                reason=reason,
                project_name=project.name,
                dry_run=dry_run,
            )
            report["enqueue_ok"] = True
            report["enqueue"] = {
                "key": enqueue_result.get("key"),
                "content_hash": enqueue_result.get("content_hash"),
                "dry_run": bool(enqueue_result.get("dry_run")),
            }
    except Exception as exc:  # noqa: BLE001
        report["enqueue_ok"] = False
        code = f"enqueue_{type(exc).__name__}"
        report["enqueue_error"] = code
        report["warnings"].append(f"ERROR: distill enqueue failed: {code}")
        print(f"ERROR: distill enqueue failed: {code}", file=sys.stderr)

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

    if closed.ok and close_receipt is not None and close_receipt.committed:
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
    if report.get("enqueue_ok") is False and final_status == STATUS_CLOSED_CANONICALLY:
        report["receipt"]["enqueue_error_present"] = True
    report["elapsed_s"] = round(clock() - started, 3)
    return report
