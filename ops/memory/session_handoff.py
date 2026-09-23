"""Agent-authored post-publish handoff — the comprehensive end-of-contract brief.

After a publication the agent writes ``.l9/memory/handoff.json`` (schema
``l9.session_handoff.v1``). The Stop write-back reads it once per publication,
binds it to that publication, and carries it losslessly inside the session's
continuation capsule for the IN-SCOPE repository — the one record the close
already writes — so a later session hydrates where things stand, not a generic
"Continue work in <repo>".

Hooks prepare material and never author it (CANONICAL_LAW §8.6, INV-03b): this
module validates, normalizes and caps what the agent wrote; it never infers,
summarizes or scores. ``governance_friction`` is split off here and never enters
the repository's record: environment, bootstrap and governance friction belongs
to the Cursor-Governance namespace alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HANDOFF_SCHEMA = "l9.session_handoff.v1"
HANDOFF_REL = Path(".l9") / "memory" / "handoff.json"

#: Operator decision: the brief may use up to 32 KB of the close's record.
MAX_HANDOFF_BYTES = 32 * 1024
MAX_ITEMS = 40
MAX_TEXT = 1200

#: Sections of free-text items, in the order the brief renders them.
TEXT_LISTS = (
    "published",
    "completed",
    "next_actions",
    "open_questions",
    "risks",
    "verification",
)

#: Sections of structured items: section -> (required key, optional keys).
STRUCTURED = {
    "not_completed": ("item", ("reason",)),
    "blocked": ("item", ("blocker", "unblock")),
    "decisions": ("decision", ("rationale",)),
    "conflicts": ("conflict", ("resolution",)),
    "human_actions": ("action", ("where", "why", "then")),
    "governance_friction": ("item", ("detail",)),
}

#: Friction is governance-plane material: routed to Cursor-Governance only.
FRICTION = "governance_friction"


class HandoffError(ValueError):
    """The handoff file is absent, malformed, or not for this publication."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{field} must be a non-empty string")
    text = " ".join(value.split())
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


def _items(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise HandoffError(f"{key} must be a list")
    if len(value) > MAX_ITEMS:
        raise HandoffError(f"{key} has {len(value)} items; at most {MAX_ITEMS}")
    return value


def _structured(payload: dict[str, Any], key: str) -> list[dict[str, str]]:
    required, optional = STRUCTURED[key]
    out: list[dict[str, str]] = []
    for index, entry in enumerate(_items(payload, key)):
        where = f"{key}[{index}]"
        if isinstance(entry, str):
            entry = {required: entry}
        if not isinstance(entry, dict):
            raise HandoffError(f"{where} must be an object with {required!r}")
        item = {required: _text(entry.get(required), f"{where}.{required}")}
        for name in optional:
            if entry.get(name):
                item[name] = _text(entry[name], f"{where}.{name}")
        out.append(item)
    return out


def normalize(payload: Any, *, pr_number: int | None = None) -> dict[str, Any]:
    """Validate and normalize a handoff; raise HandoffError when it is unusable.

    When ``pr_number`` is given the handoff must name that publication — a
    brief written for an earlier PR is not this publication's handoff.
    """
    if not isinstance(payload, dict):
        raise HandoffError("handoff must be a JSON object")
    if payload.get("schema") != HANDOFF_SCHEMA:
        raise HandoffError(f"schema must be {HANDOFF_SCHEMA!r}")
    if pr_number is not None and payload.get("pr_number") != pr_number:
        raise HandoffError(
            f"pr_number {payload.get('pr_number')!r} is not this publication (#{pr_number})"
        )
    brief: dict[str, Any] = {
        "schema": HANDOFF_SCHEMA,
        "pr_number": payload.get("pr_number"),
        "objective": _text(payload.get("objective"), "objective"),
        "status": _text(payload.get("status"), "status"),
    }
    for key in TEXT_LISTS:
        brief[key] = [_text(v, f"{key}[{i}]") for i, v in enumerate(_items(payload, key))]
    for key in STRUCTURED:
        brief[key] = _structured(payload, key)
    size = len(json.dumps(brief, ensure_ascii=False).encode("utf-8"))
    if size > MAX_HANDOFF_BYTES:
        raise HandoffError(f"handoff is {size} bytes; the cap is {MAX_HANDOFF_BYTES}")
    return brief


def load(workspace: Path, *, pr_number: int | None = None) -> dict[str, Any]:
    path = Path(workspace) / HANDOFF_REL
    if not path.is_file():
        raise HandoffError(f"no handoff file at {HANDOFF_REL}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"{HANDOFF_REL} is not readable JSON ({type(exc).__name__})") from exc
    return normalize(payload, pr_number=pr_number)


def split(brief: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """(repository brief, governance friction) — friction never stays in the brief."""
    repo = {k: v for k, v in brief.items() if k != FRICTION}
    return repo, list(brief.get(FRICTION) or [])


def friction_text(friction: list[dict[str, str]], *, repository: str, pr: str) -> str:
    lines = [f"Governance friction reported from {repository} ({pr}):"]
    for entry in friction:
        detail = f" — {entry['detail']}" if entry.get("detail") else ""
        lines.append(f"- {entry['item']}{detail}")
    return "\n".join(lines)


def render(brief: dict[str, Any]) -> str:
    """The brief as the next session reads it — every section, verbatim."""

    def items(key: str, fmt: Any) -> list[str]:
        values = brief.get(key) or []
        head = key.replace("_", " ")
        if not values:
            return [f"{head}: none"]
        return [f"{head}:"] + [f"  - {fmt(v)}" for v in values]

    def opt(entry: dict[str, str], name: str, prefix: str) -> str:
        return f"{prefix}{entry[name]}" if entry.get(name) else ""

    lines = [
        f"publication: {brief.get('publication') or brief.get('pr_number')}",
        f"objective: {brief.get('objective', '')}",
        f"status: {brief.get('status', '')}",
    ]
    for key in ("published", "completed"):
        lines += items(key, str)
    lines += items("not_completed", lambda e: e["item"] + opt(e, "reason", " — "))
    lines += items(
        "blocked",
        lambda e: e["item"] + opt(e, "blocker", " — ") + opt(e, "unblock", " | unblock: "),
    )
    lines += items("decisions", lambda e: e["decision"] + opt(e, "rationale", " — "))
    lines += items("conflicts", lambda e: e["conflict"] + opt(e, "resolution", " — "))
    lines += items(
        "human_actions",
        lambda e: (
            e["action"]
            + opt(e, "where", " @ ")
            + opt(e, "why", " — ")
            + opt(e, "then", " | then: ")
        ),
    )
    for key in ("next_actions", "open_questions", "risks", "verification"):
        lines += items(key, str)
    return "\n".join(lines)


def request_reason(*, pr_label: str, pr_number: int) -> str:
    """What the Stop hook hands the agent when the handoff is missing (once)."""
    example = {
        "schema": HANDOFF_SCHEMA,
        "pr_number": pr_number,
        "objective": "what this contract set out to do",
        "status": "where things stand right now, in one or two sentences",
        "published": ["what shipped in this PR"],
        "completed": ["what is done and verified"],
        "not_completed": [{"item": "…", "reason": "why not"}],
        "blocked": [{"item": "…", "blocker": "what blocks it", "unblock": "what unblocks it"}],
        "decisions": [{"decision": "…", "rationale": "why"}],
        "conflicts": [{"conflict": "…", "resolution": "how it was resolved, or open"}],
        "human_actions": [
            {
                "action": "what the human must do",
                "where": "system/URL",
                "why": "…",
                "then": "what to do when coming back",
            }
        ],
        "next_actions": ["the next concrete step for the next session"],
        "open_questions": ["…"],
        "risks": ["…"],
        "verification": ["commands run and their results"],
        "governance_friction": [
            {"item": "environment/bootstrap/governance friction only", "detail": "…"}
        ],
    }
    return (
        f"L9 post-publish handoff required for {pr_label}. Write {HANDOFF_REL} "
        f"(schema {HANDOFF_SCHEMA}) — the comprehensive brief of where this contract "
        "stands — then stop. It is written once to the in-scope repository's memory. "
        "Put environment/bootstrap/governance friction ONLY under governance_friction "
        "(routed to Cursor-Governance, never the repository). Empty sections are []. "
        f"Shape:\n{json.dumps(example, indent=2)}"
    )


__all__ = [
    "FRICTION",
    "HANDOFF_REL",
    "HANDOFF_SCHEMA",
    "MAX_HANDOFF_BYTES",
    "HandoffError",
    "friction_text",
    "load",
    "normalize",
    "render",
    "request_reason",
    "split",
]
