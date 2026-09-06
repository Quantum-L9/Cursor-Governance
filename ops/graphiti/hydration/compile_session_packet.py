"""Compile SessionHydrationPacket for sessionStart additional_context.

Since campaign stage C4 the packet's memory evidence comes from the canonical
memory control plane (``ops.memory.hydration.canonical_hydrate``): repository
identity → requested namespaces → memory.health → memory.hydrate → typed
continuation records. The packet itself stays Cursor's composition artifact
(S-01); only where its evidence originates changed.

The provider read that used to be the authority survives here only as a
**migration-only shadow** (plan §11, §13): read-only, never a write, never a
source of session context, tagged ``legacy_unverified`` when it is consulted
at all, and gone at stage C11. Two switches, both off by default:

- ``MEMORY_LEGACY_SHADOW=1`` runs the legacy read beside the canonical one
  and writes a discrepancy receipt (ids and digests, no content) under
  ``<project>/.l9/memory/shadow/<session>.json``.
- ``MEMORY_LEGACY_CONTINUATION=1`` lets a legacy PICKUP stand in as
  ``legacy_unverified`` continuation *only* when canonical memory returned no
  continuation at all, while provider-only history is being reconciled (C10).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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
    shadow_dir,
)
from ops.memory.hydration import (  # noqa: E402
    SOURCE_LEGACY_UNVERIFIED,
    STATUS_NAMESPACE_UNRESOLVED,
    CanonicalHydration,
    canonical_hydrate,
)
from ops.memory.session_state import write_session_state  # noqa: E402

_RULES_PATH = Path(__file__).resolve().parent / "promotion_rules.yaml"

HEADING = "### memory hydrate"
ENV_LEGACY_SHADOW = "MEMORY_LEGACY_SHADOW"
ENV_LEGACY_CONTINUATION = "MEMORY_LEGACY_CONTINUATION"


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


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Legacy shadow reader (migration-only; deleted at C11)
# ---------------------------------------------------------------------------


class SearchFactsError(RuntimeError):
    """The legacy provider read did not complete (not an empty result)."""


def _read_groups(group_id: str) -> list[str]:
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        import graphiti_memory_client as gmc

        return list(gmc.resolve_read_groups(group_id))
    except Exception:  # noqa: BLE001
        return [group_id]


def _search_facts(group_id: str, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Legacy provider search. Read-only; shadow and migration use only."""
    try:
        import graphiti_memory_client as gmc

        gmc.load_env()
        results: list[dict[str, Any]] = []
        errors: list[str] = []
        for gid in _read_groups(group_id):
            try:
                found = gmc.call_tool(
                    "search_memory_facts",
                    {"query": query, "group_ids": [gid], "max_facts": limit},
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{gid}: {exc}")
                continue
            if isinstance(found, dict):
                facts = found.get("facts") or found.get("results") or found.get("nodes") or []
                if isinstance(facts, list):
                    results.extend(f for f in facts if isinstance(f, dict))
            elif isinstance(found, list):
                results.extend(f for f in found if isinstance(f, dict))
        if not results and errors:
            raise SearchFactsError("; ".join(errors)[:400])
        return results[:limit]
    except SearchFactsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SearchFactsError(str(exc) or type(exc).__name__) from exc


def _fact_text(fact: dict[str, Any]) -> str:
    for key in ("fact", "content", "name", "episode_body", "summary", "text"):
        val = fact.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return json.dumps(fact, ensure_ascii=False)[:400]


def _parse_pickup_pipe(text: str) -> tuple[str, str]:
    """Parse legacy ``PICKUP|objective=…|next=…`` lines (historical format)."""
    if "PICKUP|" not in text.upper() and not text.upper().startswith("PICKUP|"):
        if "PICKUP|" not in text and "objective=" not in text.lower():
            return "", ""
    objective = ""
    next_action = ""
    for part in re.split(r"[|\n]", text):
        part = part.strip()
        low = part.lower()
        if low.startswith("objective="):
            objective = part.split("=", 1)[1].strip()[:500]
        elif low.startswith("next=") or low.startswith("next_action="):
            next_action = part.split("=", 1)[1].strip()[:1000]
    return objective, next_action


def _extract_pickup(facts: list[dict[str, Any]]) -> dict[str, str]:
    """Best-effort objective/next from legacy provider facts (historical format)."""
    pickup_text = ""
    for fact in facts:
        text = _fact_text(fact)
        if (
            "PICKUP" in text.upper()
            or "next_action" in text
            or "active_objective" in text
            or "objective=" in text.lower()
            or "next=" in text.lower()
        ):
            pickup_text = text
            break
    if not pickup_text and facts:
        pickup_text = _fact_text(facts[0])
    objective, next_action = _parse_pickup_pipe(pickup_text)
    m_obj = re.search(
        r"(?:active_objective|objective)\s*(?:[:=]|is(?:\s+to)?)\s*(.+)",
        pickup_text,
        re.IGNORECASE,
    )
    if m_obj and not objective:
        objective = m_obj.group(1).strip().split("\n")[0][:500]
    m_next = re.search(
        r"(?:next_action|next(?:\s+action)?)\s*(?:[:=]|is(?:\s+to)?)\s*(.+)",
        pickup_text,
        re.IGNORECASE,
    )
    if m_next and not next_action:
        next_action = m_next.group(1).strip().split("\n")[0][:1000]
    # The provider often paraphrased the Phase A PICKUP into prose.
    if not next_action:
        m_resume = re.search(
            r"((?:resume|resuming|continue)\s+from\s+.+)", pickup_text, re.IGNORECASE
        )
        if m_resume:
            next_action = m_resume.group(1).strip().split("\n")[0][:1000]
    if objective and re.search(r"\sby\s", objective, re.IGNORECASE):
        tail = re.split(r"\s+\bby\b\s+", objective, maxsplit=1, flags=re.IGNORECASE)
        if len(tail) == 2 and tail[1].strip():
            if not next_action:
                next_action = tail[1].strip()[:1000]
            objective = tail[0].strip()[:500]
    json_start = pickup_text.find("{")
    if json_start >= 0:
        try:
            data = json.loads(pickup_text[json_start:])
            if isinstance(data, dict):
                objective = str(data.get("active_objective") or objective)[:500]
                nested = (data.get("next_action_contract") or {}).get("next_action")
                next_action = str(data.get("next_action") or nested or next_action)[:1000]
                pipe = str(data.get("search_line") or "")
                if pipe:
                    o2, n2 = _parse_pickup_pipe(pipe)
                    objective = o2 or objective
                    next_action = n2 or next_action
        except json.JSONDecodeError:
            pass
    return {
        "active_objective": objective,
        "next_action": next_action,
        "context_slice": pickup_text[:2000],
    }


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _legacy_shadow_read(group_id: str) -> dict[str, Any]:
    """Read-only legacy PICKUP read; returns ids/digests, never writes."""
    try:
        facts = _search_facts(group_id, "PICKUP|objective= next= agent=", limit=8)
    except SearchFactsError as exc:
        return {"available": False, "error": type(exc).__name__, "detail": str(exc)[:200]}
    pickup = _extract_pickup(facts) if facts else None
    found = bool(pickup and (pickup["active_objective"] or pickup["next_action"]))
    return {
        "available": True,
        "fact_count": len(facts),
        "pickup_found": found,
        "objective": pickup["active_objective"] if found and pickup else "",
        "next_action": pickup["next_action"] if found and pickup else "",
        "next_digest": _digest(pickup["next_action"]) if found and pickup else None,
    }


def _shadow_receipt(
    project: Path,
    session_id: str,
    hydration: CanonicalHydration,
    legacy: dict[str, Any],
) -> dict[str, Any]:
    """Comparison evidence (plan §11): ids, counts, digests; no memory content."""
    canonical_next = hydration.continuation.capsule.next_action if hydration.continuation else ""
    canonical_next_digest = _digest(canonical_next) if canonical_next else None
    legacy_next_digest = legacy.get("next_digest")
    if not legacy.get("available"):
        agreement = "legacy_unreachable"
    elif canonical_next_digest and legacy_next_digest:
        agreement = "same_next" if canonical_next_digest == legacy_next_digest else "differs"
    elif canonical_next_digest:
        agreement = "canonical_only"
    elif legacy_next_digest:
        agreement = "legacy_only"
    else:
        agreement = "neither"
    receipt = {
        "session_id": session_id,
        "namespace": hydration.namespace_context.write_namespace_hint,
        "canonical": {
            "status": hydration.status,
            "record_count": len(hydration.record_ids),
            "continuation_record_id": hydration.continuation.record_id
            if hydration.continuation
            else None,
            "continuation_digest": hydration.continuation.capsule.digest()
            if hydration.continuation
            else None,
            "continuation_stale": hydration.continuation.stale if hydration.continuation else None,
            "next_digest": canonical_next_digest,
        },
        "legacy": {
            key: value for key, value in legacy.items() if key not in {"objective", "next_action"}
        },
        "agreement": agreement,
        "authority": "canonical",
    }
    try:
        directory = shadow_dir(project)
        os.makedirs(directory, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]
        with open(os.path.join(directory, f"{safe}.json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError):
        pass
    return receipt


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
    hydration = canonical_hydrate(project, task=task, session_id=conversation_id)
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
        if continuation.stale:
            rationale += (
                f" (STALE: repository moved on from {capsule.repository_state_digest[:8]}; "
                "current git state wins — verify before acting)"
            )

    # Migration-only legacy reader (plan §13): consulted only when canonical
    # memory has no continuation, and its result can never pass as canonical.
    legacy_shadow: dict[str, Any] | None = None
    if namespace != "unresolved" and (_flag(ENV_LEGACY_SHADOW) or _flag(ENV_LEGACY_CONTINUATION)):
        legacy_shadow = _legacy_shadow_read(namespace)
        if (
            continuation is None
            and hydration.ok
            and _flag(ENV_LEGACY_CONTINUATION)
            and legacy_shadow.get("pickup_found")
        ):
            objective = str(legacy_shadow.get("objective") or "")
            next_action = str(legacy_shadow.get("next_action") or "")
            continuation_source = SOURCE_LEGACY_UNVERIFIED
            rationale = "legacy_unverified PICKUP (migration window; not canonical)"
            warnings.append("continuation came from the legacy reader: legacy_unverified")

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
        "fan_in_denied": hydration.fan_in_denied,
        "projection_status": hydration.projection_status,
    }

    memory_block: dict[str, Any] = hydration.as_dict()
    if legacy_shadow is not None:
        memory_block["shadow"] = _shadow_receipt(project, conversation_id, hydration, legacy_shadow)

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
