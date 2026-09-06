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
    resolve_session_id,
)
from ops.memory.hydration import (  # noqa: E402
    STATUS_NAMESPACE_UNRESOLVED,
    canonical_hydrate,
)
from ops.memory.session_state import write_session_state  # noqa: E402

_RULES_PATH = Path(__file__).resolve().parent / "promotion_rules.yaml"

HEADING = "### memory hydrate"


def _hydration_budget() -> int:
    raw = os.environ.get("MEMORY_HYDRATION_CHAR_BUDGET", "").strip()
    if raw.isdigit():
        return max(500, int(raw))
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        import yaml

        rules = yaml.safe_load(_RULES_PATH.read_text(encoding="utf-8")) or {}
        return int(rules.get("hydration_char_budget_default", 4000))
    except Exception:  # noqa: BLE001
        return 4000


# ---------------------------------------------------------------------------
# Packet composition (S-06)
# ---------------------------------------------------------------------------

_DEGRADED_OBJECTIVE = {
    STATUS_NAMESPACE_UNRESOLVED: (
        "Repository identity unresolved — no memory namespace to request"
    ),
    "BINDING_FAILED": "Memory runtime unbound — proceed without resume memory",
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


def compile_session_packet(
    *,
    project_dir: str | Path,
    conversation_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Build a SessionHydrationPacket dict (fail-open; never raises to hooks)."""
    project = Path(project_dir).expanduser().resolve()
    conversation_id = resolve_session_id(explicit=conversation_id)
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

    task = f"Resume session in {project.name}"
    # SessionStart has no task yet, so a task-signature match is impossible
    # here by construction; the packet asks for the explicit repository
    # fallback and reports it (audit P1-02). A task-bearing caller keeps the
    # default ``task`` policy and never inherits another task's capsule.
    hydration = canonical_hydrate(
        project,
        task=task,
        session_id=conversation_id,
        continuation_policy="repository_fallback",
    )
    namespace = hydration.namespace_context.write_namespace_hint or "unresolved"
    packet_id = hashlib.sha256(f"{conversation_id}:{namespace}:{project}".encode()).hexdigest()[:16]

    continuation = hydration.continuation
    continuation_source = continuation.source if continuation else None
    objective = ""
    next_action = ""
    rationale = ""
    warnings = list(hydration.warnings)

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

    degraded = hydration.degraded or close_gap
    degrade_reason = ""
    if hydration.degraded:
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
    if close_gap:
        degrade_reason = close_gap_text or "prior session close-gap"

    budget = _hydration_budget()
    context_parts: list[str] = []
    if continuation is not None:
        capsule = continuation.capsule
        details = []
        if capsule.active_files:
            details.append("files: " + ", ".join(capsule.active_files[:8]))
        if capsule.blockers:
            details.append("blockers: " + "; ".join(capsule.blockers[:4]))
        if capsule.decisions:
            details.append("decisions: " + "; ".join(capsule.decisions[:4]))
        if capsule.unfinished_work:
            details.append("unfinished: " + "; ".join(capsule.unfinished_work[:4]))
        if details:
            context_parts.append("\n".join(details))
    for memory_class, content in hydration.context_sections[:6]:
        context_parts.append(f"[{memory_class}]\n{content[:900]}")
    context_slice = "\n---\n".join(p for p in context_parts if p)[:budget]

    fact_previews = [
        {"uuid": record_id[:64], "text_head": content[:120].replace("\n", " ")}
        for (record_id, (_cls, content)) in zip(
            hydration.record_ids[:3], hydration.context_sections[:3], strict=False
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
        "anchors": list(continuation.capsule.active_files[:12]) if continuation else [],
        "artifacts": [],
        "blockers": list(continuation.capsule.blockers[:8]) if continuation else [],
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "close_gap": close_gap,
        "conversation_id": conversation_id,
        "fact_count": len(hydration.record_ids),
        "hydrate_stats": hydrate_stats,
        "fact_previews": fact_previews,
        "memory": memory_block,
        "warnings": warnings,
    }


def format_additional_context(packet: dict[str, Any]) -> str:
    """Markdown + compact JSON for Cursor additional_context."""
    budget = _hydration_budget()
    contract = packet.get("next_action_contract") or {}
    next_action = contract.get("next_action") or ""
    stats = packet.get("hydrate_stats") or {}
    close_gap = bool(packet.get("close_gap") or stats.get("close_gap"))
    status = str(stats.get("memory_status") or ("DEGRADED" if packet.get("degraded") else "OK"))
    lines: list[str] = []
    if close_gap:
        lines.extend(["DEGRADED", "REPAIR: /end-session"])
    lines.append(HEADING)
    lines.append(
        f"memory hydrate: namespace={packet.get('group_id')} "
        f"agent_id={packet.get('agent_id')} packet={packet.get('packet_id')} "
        f"status={status}" + (" DEGRADED" if packet.get("degraded") else "")
    )
    if packet.get("degraded") and packet.get("degrade_reason"):
        lines.append(f"hydration degraded: {packet['degrade_reason']}")
    lines.append(f"objective: {packet.get('active_objective', '')}")
    lines.append(f"next={next_action}")
    if contract.get("rationale"):
        lines.append(f"rationale: {contract['rationale']}")
    record = stats.get("continuation_record_id")
    if record:
        stale = " STALE" if stats.get("continuation_stale") else ""
        source = stats.get("continuation_source")
        lines.append(f"continuation: record={str(record)[:8]} source={source}{stale}")
    elif stats.get("continuation_source"):
        lines.append(f"continuation: source={stats.get('continuation_source')}")
    else:
        lines.append("continuation: none")
    lines.append(
        "stats: "
        f"facts_returned={stats.get('facts_returned', packet.get('fact_count', 0))} | "
        f"pickup_parsed={'yes' if stats.get('pickup_parsed') else 'no'} | "
        f"context_chars={stats.get('context_chars', 0)} | "
        f"search_queries_used={stats.get('search_queries_used', 0)} | "
        f"budget_chars={stats.get('budget_chars', budget)}"
    )
    if stats.get("fan_in_denied"):
        lines.append(f"fan-in: denied by memory ({str(stats['fan_in_denied'])[:160]})")
    previews = packet.get("fact_previews") or []
    if previews:
        lines.append("facts_preview:")
        for prev in previews[:3]:
            head = str(prev.get("text_head") or "").replace("\n", " ")[:120]
            lines.append(f"- {head}")
    slice_text = (packet.get("context_slice") or "")[: max(200, budget - 400)]
    if slice_text:
        lines.append("facts:")
        lines.append(slice_text)
    compact = {
        "packet_id": packet.get("packet_id"),
        "group_id": packet.get("group_id"),
        "agent_id": packet.get("agent_id"),
        "active_objective": packet.get("active_objective"),
        "next_action_contract": packet.get("next_action_contract"),
        "degraded": packet.get("degraded", False),
        "hydrate_stats": stats,
    }
    fence = "```json\n" + json.dumps(compact, ensure_ascii=False) + "\n```"
    text = "\n".join(lines) + "\n" + fence
    if len(text) > budget:
        text = text[: budget - 20] + "\n…[truncated]"
    return text


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
