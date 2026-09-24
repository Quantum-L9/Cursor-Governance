"""Agent-authored post-publish GOVERNANCE handoff — environment and bootstrap only.

The second of the two post-publish handoffs. The repository handoff
(``ops/memory/session_handoff.py``) says where the contract stands for the
in-scope repository; this one carries only what belongs to Cursor-Governance:
environment friction, environment/governance blockers, degraded bootstrap
items, the workarounds used, and the governance actions a human must take.

After a publication the agent writes ``.l9/memory/governance-handoff.json``
(schema ``l9.governance_handoff.v1``). Its own Stop hook
(``governance_handoff_writeback.py``), running in parallel with the repository
close, writes it as ONE observation record to the ``cursor-governance``
namespace — never to the repository's — through the namespace-restricted
``claude-governance-handoff`` hook surface.

Hooks prepare material and never author it (CANONICAL_LAW §8.6, INV-03b): this
module validates, normalizes, caps and renders what the agent wrote. The hook
may attach an ``observed`` block, but only as verbatim copies of receipts
(bootstrap state, prefetch status, hook skips) — never an inference.

Machine form: ``ops/memory/schemas/l9.governance_handoff.v1.schema.json``;
contract: ``ops/memory/HANDOFF_CONTRACT.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ops.memory.session_handoff import (
    HandoffError,
    check_keys,
    clean_pr_number,
    clean_structured,
)

GOVERNANCE_SCHEMA = "l9.governance_handoff.v1"
GOVERNANCE_REL = Path(".l9") / "memory" / "governance-handoff.json"
GOVERNANCE_NAMESPACE = "cursor-governance"

#: The brief's own cap. The record adds a header and the hook-observed block and
#: must fit the surface's 16 KiB ``max_bytes``; ``render`` enforces that bound.
MAX_GOVERNANCE_BYTES = 12 * 1024
MAX_RECORD_BYTES = 16 * 1024

#: section -> (required key, optional keys), in render order.
SECTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "environment_friction": ("item", ("detail", "impact")),
    "blockers": ("item", ("blocker", "unblock")),
    "degraded_bootstrap": ("component", ("detail",)),
    "workarounds": ("item", ("workaround",)),
    "governance_actions": ("action", ("where", "why")),
}

KEYS = frozenset({"schema", "pr_number", *SECTIONS})

#: Repository-handoff sections, named in the refusal when they land here.
MISPLACED = {
    key: ".l9/memory/handoff.json"
    for key in (
        "objective",
        "status",
        "published",
        "completed",
        "not_completed",
        "blocked",
        "decisions",
        "conflicts",
        "human_actions",
        "next_actions",
        "open_questions",
        "risks",
        "verification",
    )
}


def normalize(payload: Any, *, pr_number: int | None = None) -> dict[str, Any]:
    """Validate and normalize a governance handoff; raise HandoffError when unusable."""
    if not isinstance(payload, dict):
        raise HandoffError("governance handoff must be a JSON object")
    if payload.get("schema") != GOVERNANCE_SCHEMA:
        raise HandoffError(f"schema must be {GOVERNANCE_SCHEMA!r}")
    check_keys(payload, KEYS, misplaced=MISPLACED)
    number = clean_pr_number(payload.get("pr_number"))
    if pr_number is not None and number != pr_number:
        raise HandoffError(f"pr_number {number!r} is not this publication (#{pr_number})")
    brief: dict[str, Any] = {"schema": GOVERNANCE_SCHEMA, "pr_number": number}
    for key in SECTIONS:
        brief[key] = clean_structured(payload, key, SECTIONS)
    size = len(json.dumps(brief, ensure_ascii=False).encode("utf-8"))
    if size > MAX_GOVERNANCE_BYTES:
        raise HandoffError(f"governance handoff is {size} bytes; the cap is {MAX_GOVERNANCE_BYTES}")
    return brief


def load(workspace: Path, *, pr_number: int | None = None) -> dict[str, Any]:
    path = Path(workspace) / GOVERNANCE_REL
    if not path.is_file():
        raise HandoffError(f"no governance handoff file at {GOVERNANCE_REL}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"{GOVERNANCE_REL} is not readable JSON ({type(exc).__name__})") from exc
    return normalize(payload, pr_number=pr_number)


def is_empty(brief: dict[str, Any] | None) -> bool:
    """True when the agent reported nothing in any section."""
    return not brief or not any(brief.get(key) for key in SECTIONS)


def _line(key: str, entry: dict[str, str]) -> str:
    required, optional = SECTIONS[key]
    extra = [f"{name}: {entry[name]}" for name in optional if entry.get(name)]
    return entry[required] + (f" — {'; '.join(extra)}" if extra else "")


def render_sections(brief: dict[str, Any]) -> list[str]:
    """Every section, verbatim, one line per item."""
    lines: list[str] = []
    for key in SECTIONS:
        values = brief.get(key) or []
        head = key.replace("_", " ")
        if not values:
            lines.append(f"{head}: none")
            continue
        lines.append(f"{head}:")
        lines.extend(f"  - {_line(key, v)}" for v in values)
    return lines


def render_observed(observed: dict[str, Any]) -> list[str]:
    """The hook-copied receipts, labelled as such — never authored content."""
    if not observed:
        return []
    lines = ["observed by the hook (verbatim from receipts, not agent-authored):"]
    for name, value in observed.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        lines.append(f"  - {name}: {text}")
    return lines


def record_text(
    brief: dict[str, Any] | None,
    observed: dict[str, Any],
    *,
    repository: str,
    pr_label: str,
    session_id: str,
) -> str:
    """The ONE record written to cursor-governance, bounded by MAX_RECORD_BYTES."""
    head = [
        f"Governance handoff from {repository} ({pr_label}), session {session_id}, "
        "agent claude-code."
    ]
    body = render_sections(brief) if brief else ["agent governance handoff: NOT CAPTURED"]
    text = "\n".join(head + body + render_observed(observed))
    raw = text.encode("utf-8")
    if len(raw) <= MAX_RECORD_BYTES:
        return text
    marker = "\n… [truncated to the 16 KiB record cap]"
    keep = MAX_RECORD_BYTES - len(marker.encode("utf-8"))
    return raw[:keep].decode("utf-8", errors="ignore") + marker


def example(pr_number: int) -> dict[str, Any]:
    """The shape the agent is asked to write."""
    return {
        "schema": GOVERNANCE_SCHEMA,
        "pr_number": pr_number,
        "environment_friction": [
            {
                "item": "what got in the way",
                "detail": "evidence: command, message, receipt",
                "impact": "time lost / what it prevented",
            }
        ],
        "blockers": [
            {"item": "…", "blocker": "the environment/governance cause", "unblock": "the fix"}
        ],
        "degraded_bootstrap": [
            {"component": "bootstrap component or hook", "detail": "state and reason observed"}
        ],
        "workarounds": [{"item": "…", "workaround": "what was done instead"}],
        "governance_actions": [
            {"action": "what a human must change", "where": "setting/file/URL", "why": "…"}
        ],
    }


__all__ = [
    "GOVERNANCE_NAMESPACE",
    "GOVERNANCE_REL",
    "GOVERNANCE_SCHEMA",
    "KEYS",
    "MAX_GOVERNANCE_BYTES",
    "MAX_RECORD_BYTES",
    "MISPLACED",
    "SECTIONS",
    "HandoffError",
    "example",
    "is_empty",
    "load",
    "normalize",
    "record_text",
    "render_observed",
    "render_sections",
]
