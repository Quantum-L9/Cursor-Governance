"""Compile SessionHydrationPacket for sessionStart additional_context.

Since campaign stage C4 the packet's memory evidence comes from the canonical
memory control plane (``ops.memory.hydration.canonical_hydrate``): repository
identity → requested namespaces → memory.health → memory.hydrate → typed
continuation records. The packet itself stays Cursor's composition artifact
(S-01); only where its evidence originates changed.

Stage C11 removed the migration-only provider shadow read: this module has no
provider path left, and a session with no canonical continuation starts from
the user request. Provider-only history is reconciled offline through
``ops/memory/legacy_reconciliation.py``, never read from here.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

_GRAPHITI_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _GRAPHITI_DIR.parent.parent
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.graphiti.hydration.identity import resolve_write_identity  # noqa: E402
from ops.graphiti.hydration.session_latches import (  # noqa: E402
    close_gap_reason,
    resolve_session_lifecycle,
)
from ops.memory.hydration import (  # noqa: E402
    STATUS_NAMESPACE_UNRESOLVED,
    canonical_hydrate,
)
from ops.memory.session_contracts import session_task_objective  # noqa: E402
from ops.memory.session_state import write_session_state  # noqa: E402

#: Default hydration budget (chars). Formerly read from promotion_rules.yaml,
#: which was Cursor-local memory cognition and is gone (ADR-0033).
HYDRATION_CHAR_BUDGET_DEFAULT = 4000
#: Hook-lane surface this compiler hydrates under (ADR-0033 B7): read-only
#: envelope, ``ops/config/memory-hook-envelopes.json``.
HOOK_SURFACE = "cursor-session-start"

HEADING = "### memory hydrate"


def _hydration_budget() -> int:
    raw = os.environ.get("MEMORY_HYDRATION_CHAR_BUDGET", "").strip()
    if raw.isdigit():
        return max(500, int(raw))
    return HYDRATION_CHAR_BUDGET_DEFAULT


# ---------------------------------------------------------------------------
# Packet composition (S-06)
# ---------------------------------------------------------------------------

_DEGRADED_OBJECTIVE = {
    STATUS_NAMESPACE_UNRESOLVED: (
        "Repository identity unresolved — no memory namespace to request"
    ),
    "BINDING_FAILED": "Memory runtime unbound (environment fault) — proceed without resume memory",
    "CANONICAL_UNAVAILABLE": "Canonical memory unavailable — proceed without resume memory",
    "UNAUTHORIZED_NAMESPACE": (
        "Memory refused the requested namespace — proceed without resume memory"
    ),
    "TIMEOUT": "Canonical memory timed out — proceed without resume memory",
    "INVALID_RECEIPT": (
        "Canonical memory returned an invalid receipt — proceed without resume memory"
    ),
    "PARTIAL_PROJECTION_DEGRADED": "Canonical memory ready; projection degraded",
}

# Three conditions a packet can carry, and the three lead lines they produce.
# They are typed and independent (ADR-0032): only ``memory_degraded`` means
# canonical memory ran and did not answer.
LEAD_DEGRADED = "DEGRADED"
LEAD_ENVIRONMENT_FAULT = "ENVIRONMENT_FAULT"
LEAD_CLOSE_GAP = "CLOSE_GAP"
REPAIR_CLOSE_GAP = "REPAIR: /end-session"
_REPAIR_READINESS = "REPAIR: make -C ~/.cursor-governance memory-readiness"


def environment_fault_reason(status: str, error: str | None, environment_heal: str | None) -> str:
    """One line naming the bootstrap fault; never calls it memory degradation."""

    if status == STATUS_NAMESPACE_UNRESOLVED:
        return f"{status}: {error or 'repository identity unresolved'}"[:500]
    detail = f"{status}: {error or 'memory runtime unbound'}"
    if environment_heal:
        detail += f" (heal={environment_heal})"
    return detail[:500]


def environment_fault_repair(status: str) -> str:
    if status == STATUS_NAMESPACE_UNRESOLVED:
        return "REPAIR: resolve the repository identity (git remote / ops.memory.namespace)"
    return _REPAIR_READINESS


def compile_session_packet(
    *,
    project_dir: str | Path,
    conversation_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Build a SessionHydrationPacket dict (fail-open; never raises to hooks)."""
    project = Path(project_dir).expanduser().resolve()
    # The orchestrator resolved the lifecycle id once, before `cli open`, and
    # passes it here explicitly; this reuses it. Only a caller that supplied
    # none falls through to the persisted pointer. Persistence itself is
    # fail-open (audit P573-F3): a fault is a warning on the packet, never a
    # raise into the SessionStart hook.
    conversation_id, pointer_error = resolve_session_lifecycle(project, explicit=conversation_id)
    close_gap_text = close_gap_reason(project, conversation_id)
    close_gap = bool(close_gap_text)
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        identity = resolve_write_identity(explicit_agent_id=agent_id, surface="cursor")
    except Exception:  # noqa: BLE001
        identity = {
            "agent_id": (agent_id or os.environ.get("L9_MEMORY_AGENT_ID") or "cursor").strip(),
            "user_id": os.environ.get("USER_ID") or "cursor_agent",
        }

    task = session_task_objective(project.name)
    # SessionStart has no task yet, so a task-signature match is impossible
    # here by construction; the packet asks for the explicit repository
    # fallback and reports it (audit P1-02). A task-bearing caller keeps the
    # default ``task`` policy and never inherits another task's capsule.
    hydration = canonical_hydrate(
        project,
        task=task,
        session_id=conversation_id,
        continuation_policy="repository_fallback",
        surface=HOOK_SURFACE,
    )
    namespace = hydration.namespace_context.write_namespace_hint or "unresolved"
    packet_id = hashlib.sha256(f"{conversation_id}:{namespace}:{project}".encode()).hexdigest()[:16]

    continuation = hydration.continuation
    continuation_source = continuation.source if continuation else None
    objective = ""
    next_action = ""
    rationale = ""
    warnings = list(hydration.warnings)
    if pointer_error:
        warnings.append(f"session id not persisted: {pointer_error}")

    if continuation is not None:
        capsule = continuation.capsule
        objective = capsule.objective
        next_action = capsule.next_action
        rationale = (
            f"canonical continuation {continuation.record_id[:8]} from session {capsule.session_id}"
        )
        if continuation.fallback:
            rationale += (
                " (REPOSITORY FALLBACK: no continuation for this task; newest repository "
                "continuation shown — confirm it is this task before acting)"
            )
        if continuation.stale:
            rationale += (
                f" (STALE: repository moved on from {capsule.repository_state_digest[:8]}; "
                "current git state wins — verify before acting)"
            )

    # Three typed conditions (ADR-0032). ``degraded`` mirrors ``memory_degraded``
    # for consumers that predate the split; it is no longer ORed with the
    # session lifecycle or with a runtime that never reached memory.
    memory_degraded = hydration.memory_degraded
    environment_fault = hydration.environment_fault
    degraded = memory_degraded
    degrade_reason = ""
    environment_fault_text = ""
    if environment_fault:
        environment_fault_text = environment_fault_reason(
            hydration.status, hydration.error, hydration.environment_heal
        )
        objective = objective or _DEGRADED_OBJECTIVE.get(
            hydration.status, "Memory runtime unreachable — proceed without resume memory"
        )
        next_action = next_action or "Proceed from user request; memory runtime not bound"
        rationale = rationale or f"memory status {hydration.status} (environment fault)"
    elif memory_degraded:
        degrade_reason = f"{hydration.status}: {hydration.error or 'no detail'}"[:500]
        objective = objective or _DEGRADED_OBJECTIVE.get(
            hydration.status, "Canonical memory degraded — proceed without resume memory"
        )
        next_action = next_action or "Proceed from user request; memory evidence unavailable"
        rationale = rationale or f"memory status {hydration.status}"
    elif not objective:
        objective = "No continuation in canonical memory — start from the user request"
        next_action = next_action or "Proceed from user request"
        rationale = rationale or (
            f"canonical memory answered {hydration.status} with no continuation"
        )
    close_gap_reason_text = (close_gap_text or "prior session close-gap") if close_gap else ""

    budget = _hydration_budget()
    context_parts: list[str] = []
    if continuation is not None:
        capsule = continuation.capsule
        details = []
        if capsule.active_files:
            details.append("files: " + ", ".join(capsule.active_files))
        if capsule.blockers:
            details.append("blockers: " + "; ".join(capsule.blockers))
        if capsule.decisions:
            details.append("decisions: " + "; ".join(capsule.decisions))
        if capsule.unfinished_work:
            details.append("unfinished: " + "; ".join(capsule.unfinished_work))
        if details:
            context_parts.append("\n".join(details))
    for memory_class, content in hydration.context_sections:
        context_parts.append(f"[{memory_class}]\n{content}")
    context_slice = "\n---\n".join(p for p in context_parts if p)

    fact_previews = [
        {"uuid": record_id[:64], "text_head": content.replace("\n", " ")}
        for (record_id, (_cls, content)) in zip(
            hydration.record_ids, hydration.context_sections, strict=False
        )
    ]

    hydrate_stats = {
        # Legacy-compatible keys (bootstrap and classifier read these).
        "facts_returned": len(hydration.record_ids),
        "raw_facts": len(hydration.record_ids),
        "empty_task_state": False,
        "pickup_parsed": continuation is not None or continuation_source is not None,
        "context_chars": len(context_slice),
        "search_queries_used": hydration.calls,
        "budget_chars": budget,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "close_gap": close_gap,
        # Typed conditions (ADR-0032).
        "memory_degraded": memory_degraded,
        "environment_fault": environment_fault,
        "environment_fault_reason": environment_fault_text,
        "environment_heal": hydration.environment_heal,
        "fault_class": hydration.fault_class,
        "close_gap_reason": close_gap_reason_text,
        # Canonical evidence (plan §31).
        "memory_status": hydration.status,
        "transport": "cli",
        "latency_ms": hydration.latency_ms,
        "continuation_record_id": continuation.record_id if continuation else None,
        "continuation_stale": continuation.stale if continuation else None,
        "continuation_source": continuation_source,
        "continuation_candidates": hydration.continuation_candidates,
        "continuation_excluded": hydration.continuation_excluded,
        "continuation_policy": hydration.continuation_policy,
        "continuation_selection": continuation.selection if continuation else None,
        "fan_in_denied": hydration.fan_in_denied,
        "projection_status": hydration.projection_status,
        "agent_lane_records": len(hydration.agent_lane_record_ids),
        "agent_lane_window_hours": hydration.agent_lane_window_hours,
    }

    memory_block: dict[str, Any] = hydration.as_dict()

    try:
        write_session_state(conversation_id, hydration)
    except OSError as exc:
        warnings.append(f"session state not written: {type(exc).__name__}")

    return {
        "packet_id": packet_id,
        "active_objective": objective[:500],
        "context_slice": context_slice,
        "next_action_contract": {
            "next_action": "/end-session" if close_gap else next_action[:1000],
            "rationale": (
                "Close-gap — repair via /end-session (ADR-0028)" if close_gap else rationale[:1000]
            ),
            "blockers": ["/end-session"] if close_gap else [],
        },
        "group_id": namespace,
        "agent_id": identity["agent_id"],
        "handoff": (continuation.capsule.handoff if continuation else None),
        "anchors": list(continuation.capsule.active_files[:12]) if continuation else [],
        "artifacts": [],
        "blockers": list(continuation.capsule.blockers[:8]) if continuation else [],
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "memory_degraded": memory_degraded,
        "environment_fault": environment_fault,
        "close_gap": close_gap,
        "close_gap_reason": close_gap_reason_text,
        "conversation_id": conversation_id,
        "fact_count": len(hydration.record_ids),
        "hydrate_stats": hydrate_stats,
        "fact_previews": fact_previews,
        "memory": memory_block,
        "warnings": warnings,
    }


def format_additional_context(packet: dict[str, Any]) -> str:
    """Human-readable hydrate block: one field=value per line, then JSON."""
    budget = _hydration_budget()
    contract = packet.get("next_action_contract") or {}
    next_action = contract.get("next_action") or ""
    stats = packet.get("hydrate_stats") or {}
    close_gap = bool(packet.get("close_gap") or stats.get("close_gap"))
    memory_degraded = bool(
        packet.get("memory_degraded")
        if "memory_degraded" in packet
        else stats.get("memory_degraded", packet.get("degraded"))
    )
    environment_fault = bool(packet.get("environment_fault") or stats.get("environment_fault"))
    memory_status = str(stats.get("memory_status") or "")
    status = memory_status or (LEAD_DEGRADED if memory_degraded else "OK")
    lines: list[str] = []
    # Lead by class, environment first: a runtime that never reached memory
    # outranks a lifecycle gap, and neither is canonical degradation.
    if environment_fault:
        lines.extend([LEAD_ENVIRONMENT_FAULT, environment_fault_repair(memory_status)])
    if close_gap:
        lines.extend([LEAD_CLOSE_GAP, REPAIR_CLOSE_GAP])
    if memory_degraded:
        lines.append(LEAD_DEGRADED)
    lines.append(HEADING)
    lines.append(f"namespace={packet.get('group_id')}")
    lines.append(f"agent_id={packet.get('agent_id')}")
    lines.append(f"packet={packet.get('packet_id')}")
    lines.append(f"status={status}")
    if memory_degraded:
        lines.append(f"memory_degraded={LEAD_DEGRADED}")
    if environment_fault:
        lines.append(f"environment_fault={LEAD_ENVIRONMENT_FAULT}")
    if close_gap:
        lines.append(f"close_gap={LEAD_CLOSE_GAP}")
    if memory_degraded and packet.get("degrade_reason"):
        lines.append(f"degrade_reason={packet['degrade_reason']}")
    if environment_fault:
        detail = stats.get("environment_fault_reason") or memory_status or "runtime unbound"
        lines.append(f"environment_fault_detail={detail}")
    if close_gap:
        detail = packet.get("close_gap_reason") or stats.get("close_gap_reason") or ""
        lines.append(f"close_gap_reason={detail or 'prior session did not close'}")
    lines.append(f"objective={packet.get('active_objective', '')}")
    lines.append(f"next={next_action}")
    if contract.get("rationale"):
        lines.append(f"rationale={contract['rationale']}")
    record = stats.get("continuation_record_id")
    if record:
        lines.append(f"continuation_record={str(record)[:8]}")
        lines.append(f"continuation_source={stats.get('continuation_source')}")
        lines.append(f"continuation_stale={'yes' if stats.get('continuation_stale') else 'no'}")
    elif stats.get("continuation_source"):
        lines.append(f"continuation_source={stats.get('continuation_source')}")
    else:
        lines.append("continuation=none")
    lines.append(f"facts_returned={stats.get('facts_returned', packet.get('fact_count', 0))}")
    lines.append(f"pickup_parsed={'yes' if stats.get('pickup_parsed') else 'no'}")
    lines.append(f"context_chars={stats.get('context_chars', 0)}")
    lines.append(f"search_queries_used={stats.get('search_queries_used', 0)}")
    lines.append(f"budget_chars={stats.get('budget_chars', budget)}")
    if stats.get("fan_in_denied"):
        lines.append(f"fan-in: denied by memory ({str(stats['fan_in_denied'])[:160]})")
    previews = packet.get("fact_previews") or []
    if previews:
        lines.append(f"facts_preview ({len(previews)}):")
        for prev in previews:
            uid = str(prev.get("uuid") or "")[:8]
            head = str(prev.get("text_head") or "").replace("\n", " ")
            lines.append(f"- {uid}: {head}" if uid else f"- {head}")
    handoff = packet.get("handoff")
    if isinstance(handoff, dict) and handoff:
        # The last post-publish handoff, in full. Not subject to the fact
        # budget: it is already capped (32 KB) at write time, and a truncated
        # brief would drop exactly the blocked items and human actions it
        # exists to carry.
        from ops.memory.session_handoff import render as render_handoff

        lines.append("### last handoff (post-publish brief)")
        lines.append(render_handoff(handoff))
    slice_text = packet.get("context_slice") or ""
    if slice_text:
        lines.append("facts:")
        lines.append(slice_text)
    fence = "```json\n" + json.dumps(packet, ensure_ascii=False, default=str) + "\n```"
    return "\n".join(lines) + "\n" + fence


def compile_and_format(
    *,
    project_dir: str | Path,
    conversation_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    packet = compile_session_packet(
        project_dir=project_dir,
        conversation_id=conversation_id,
        agent_id=agent_id,
    )
    return {
        "packet": packet,
        "additional_context": format_additional_context(packet),
    }
