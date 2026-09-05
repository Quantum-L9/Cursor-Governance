"""Compile SessionHydrationPacket for sessionStart additional_context."""

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

from group_resolver import resolve_group_id  # noqa: E402

from ops.graphiti.hydration.identity import resolve_write_identity  # noqa: E402
from ops.graphiti.hydration.session_latches import (  # noqa: E402
    close_gap_reason,
    prior_session_id,
    resolve_session_id,
)


def _read_groups(group_id: str) -> list[str]:
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        import graphiti_memory_client as gmc

        return list(gmc.resolve_read_groups(group_id))
    except Exception:  # noqa: BLE001
        return [group_id]


_RULES_PATH = Path(__file__).resolve().parent / "promotion_rules.yaml"


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


class SearchFactsError(RuntimeError):
    """Graphiti search did not complete. This is not an empty-graph result."""


def _search_facts(group_id: str, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Search via graphiti client helpers.

    A completed search with no rows returns ``[]``. Transport, auth, import, and
    env failures raise ``SearchFactsError`` so callers can report
    ``PICKUP search unreachable`` instead of ``empty PICKUP search``.
    """
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


_PICKUP_RESTATEMENTS = (
    "continue from the latest graphiti pickup",
    "resuming from the latest graphiti pickup",
    "resume prior work from graphiti pickup",
    "the next action involves resuming from the latest graphiti pickup",
    "claude-code agent requested to continue from the latest graphiti pickup",
)


def _is_pickup_restatement(text: str) -> bool:
    """True when the fact only restates the hydrate ritual, not a task."""
    lowered = text.lower()
    return any(marker in lowered for marker in _PICKUP_RESTATEMENTS)


def _parse_pickup_pipe(text: str) -> tuple[str, str]:
    """Parse ``PICKUP|objective=…|next=…`` search lines from close Phase A."""
    if "PICKUP|" not in text.upper() and not text.upper().startswith("PICKUP|"):
        # still try loose pipe form anywhere in the fact
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
    # Graphiti often paraphrases Phase A PICKUP into prose.
    if not next_action:
        m_resume = re.search(
            r"((?:resume|resuming|continue)\s+from\s+.+)", pickup_text, re.IGNORECASE
        )
        if m_resume:
            next_action = m_resume.group(1).strip().split("\n")[0][:1000]
    if objective and re.search(r"\sby\s", objective, re.IGNORECASE):
        # e.g. "continue work in X by resuming from Y"
        tail = re.split(r"\s+\bby\b\s+", objective, maxsplit=1, flags=re.IGNORECASE)
        if len(tail) == 2 and tail[1].strip():
            if not next_action:
                next_action = tail[1].strip()[:1000]
            objective = tail[0].strip()[:500]
    # JSON pickup bodies (may follow a PICKUP| pipe line)
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
            # pickup_text may be prose/mixed; ignore malformed JSON and keep pipe/defaults.
            pass
    return {
        "active_objective": objective or "Resume prior work from Graphiti PICKUP",
        "next_action": next_action or "Search Graphiti for latest PICKUP and continue",
        "context_slice": pickup_text[:2000],
    }


def compile_session_packet(
    *,
    project_dir: str | Path,
    conversation_id: str = "default",
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Build a SessionHydrationPacket dict (fail-open when Graphiti is down)."""
    project = Path(project_dir).expanduser().resolve()
    conversation_id = resolve_session_id(explicit=conversation_id)
    close_gap = False
    close_gap_text = close_gap_reason(project, conversation_id)
    if close_gap_text:
        close_gap = True
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        identity = resolve_write_identity(explicit_agent_id=agent_id, surface="cursor")
    except Exception:  # noqa: BLE001
        identity = {
            "agent_id": (agent_id or os.environ.get("L9_MEMORY_AGENT_ID") or "cursor").strip(),
            "user_id": os.environ.get("USER_ID") or "cursor_agent",
        }

    resolved = resolve_group_id(project)
    group_id = str(resolved.get("group_id") or "")
    packet_id = hashlib.sha256(f"{conversation_id}:{group_id}:{project}".encode()).hexdigest()[:16]

    degraded = False
    degrade_reason = ""
    facts: list[dict[str, Any]] = []
    search_queries_used = 0
    if not group_id or resolved.get("readonly"):
        degraded = True
        degrade_reason = str(
            resolved.get("error") or resolved.get("warning") or "group unresolved/readonly"
        )
    else:
        try:
            prior = prior_session_id(project, conversation_id)
            if prior:
                search_queries_used += 1
                facts = _search_facts(group_id, f"PICKUP session={prior}", limit=8)
                if facts and not any(prior in _fact_text(f) for f in facts):
                    close_gap = True
                    close_gap_text = close_gap_text or (f"prior session {prior} has no PICKUP fact")
                elif not facts:
                    close_gap = True
                    close_gap_text = close_gap_text or (
                        f"empty PICKUP search for prior session {prior}"
                    )
            if not facts:
                search_queries_used += 1
                facts = _search_facts(group_id, "PICKUP|objective= next= agent=", limit=8)
            if not facts:
                search_queries_used += 1
                facts = _search_facts(group_id, "PICKUP next_action session resume", limit=8)
            if not facts:
                search_queries_used += 1
                facts = _search_facts(group_id, "session start pickup", limit=6)
        except SearchFactsError as exc:
            degraded = True
            degrade_reason = f"PICKUP search unreachable: {exc}"[:500]
        except Exception as exc:  # noqa: BLE001
            degraded = True
            degrade_reason = f"PICKUP search unreachable: {exc}"[:500]

    pickup_parsed = False
    pickup = {
        "active_objective": "No PICKUP found — start fresh or search when Graphiti is online",
        "next_action": "Proceed from user request; hydrate when memory is available",
        "context_slice": "",
    }
    if facts:
        pickup = _extract_pickup(facts)
        # Structured extraction succeeded when we got more than the generic fallbacks
        # or when a PICKUP/objective/next signal was present in raw facts.
        raw_joined = " ".join(_fact_text(f) for f in facts[:3]).upper()
        pickup_parsed = (
            "PICKUP" in raw_joined
            or "OBJECTIVE=" in raw_joined
            or "NEXT=" in raw_joined
            or "ACTIVE_OBJECTIVE" in raw_joined
            or bool(pickup.get("context_slice"))
        )
    if close_gap:
        degraded = True
        degrade_reason = close_gap_text or "prior session close-gap"
    if not facts and not degraded:
        degraded = True
        degrade_reason = degrade_reason or "empty PICKUP search"

    task_facts = [fact for fact in facts if not _is_pickup_restatement(_fact_text(fact))]
    empty_task_state = bool(facts) and not task_facts

    budget = _hydration_budget()
    if empty_task_state:
        context_slice = ""
        pickup_parsed = False
        pickup = {
            "active_objective": "PICKUP-only hydrate — no task-bearing facts",
            "next_action": "Proceed from user request; treat memory as empty",
            "context_slice": "",
        }
    else:
        context_parts = [pickup.get("context_slice") or ""]
        for fact in task_facts[:5]:
            context_parts.append(_fact_text(fact)[:400])
        context_slice = "\n---\n".join(p for p in context_parts if p)[:budget]

    fact_previews: list[dict[str, str]] = []
    for fact in task_facts[:3]:
        text = _fact_text(fact)[:120]
        uuid = str(fact.get("uuid") or fact.get("id") or "")[:64]
        fact_previews.append({"uuid": uuid, "text_head": text})

    hydrate_stats = {
        "facts_returned": len(task_facts),
        "raw_facts": len(facts),
        "empty_task_state": empty_task_state,
        "pickup_parsed": pickup_parsed,
        "context_chars": len(context_slice),
        "search_queries_used": max(1, search_queries_used) if group_id else search_queries_used,
        "budget_chars": budget,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "close_gap": close_gap,
    }

    packet = {
        "packet_id": packet_id,
        "active_objective": pickup["active_objective"],
        "context_slice": context_slice,
        "next_action_contract": {
            "next_action": "/end-session" if close_gap else pickup["next_action"],
            "rationale": (
                "Close-gap — repair via /end-session (ADR-0028)"
                if close_gap
                else "Compiled from Graphiti PICKUP/facts at sessionStart"
            ),
            "blockers": ["/end-session"] if close_gap else [],
        },
        "group_id": group_id or "unresolved",
        "agent_id": identity["agent_id"],
        "anchors": [],
        "artifacts": [],
        "blockers": [],
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "close_gap": close_gap,
        "conversation_id": conversation_id,
        "fact_count": len(facts),
        "hydrate_stats": hydrate_stats,
        "fact_previews": fact_previews,
    }
    return packet


def format_additional_context(packet: dict[str, Any]) -> str:
    """Markdown + compact JSON for Cursor additional_context."""
    budget = _hydration_budget()
    next_action = (packet.get("next_action_contract") or {}).get("next_action") or ""
    stats = packet.get("hydrate_stats") or {}
    pickup_yes = "yes" if stats.get("pickup_parsed") else "no"
    close_gap = bool(packet.get("close_gap") or stats.get("close_gap"))
    lines: list[str] = []
    if close_gap:
        lines.extend(["DEGRADED", "REPAIR: /end-session"])
    lines.append("### Graphiti hydrate")
    lines.append(
        f"graphiti hydrate: group_id={packet.get('group_id')} "
        f"agent_id={packet.get('agent_id')} packet={packet.get('packet_id')}"
        + (" DEGRADED" if packet.get("degraded") else "")
    )
    if packet.get("degraded") and packet.get("degrade_reason"):
        lines.append(f"hydration degraded: {packet['degrade_reason']}")
    lines.append(f"objective: {packet.get('active_objective', '')}")
    lines.append(f"next={next_action}")
    lines.append(
        "stats: "
        f"facts_returned={stats.get('facts_returned', packet.get('fact_count', 0))} | "
        f"pickup_parsed={pickup_yes} | "
        f"context_chars={stats.get('context_chars', 0)} | "
        f"search_queries_used={stats.get('search_queries_used', 0)} | "
        f"budget_chars={stats.get('budget_chars', budget)}"
    )
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
