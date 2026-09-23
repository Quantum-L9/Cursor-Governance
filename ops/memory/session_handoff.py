"""Agent-authored post-publish handoff — the comprehensive end-of-contract brief.

After a publication the agent writes ``.l9/memory/handoff.json`` (schema
``l9.session_handoff.v1``). The Stop write-back reads it once per publication,
binds it to that publication, and carries it losslessly inside the session's
continuation capsule for the IN-SCOPE repository — the one record the close
already writes — so a later session hydrates where things stand, not a generic
"Continue work in <repo>".

Hooks prepare material and never author it (CANONICAL_LAW §8.6, INV-03b): this
module validates, normalizes and caps what the agent wrote; it never infers,
summarizes or scores. Environment, bootstrap and governance friction is NOT part
of this brief: it is its own handoff (``ops/memory/governance_handoff.py``,
``.l9/memory/governance-handoff.json``), written by its own Stop hook to the
Cursor-Governance namespace alone.

Machine form: ``ops/memory/schemas/l9.session_handoff.v1.schema.json``;
contract: ``ops/memory/HANDOFF_CONTRACT.md``.
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
}

#: Every top-level key the brief may carry. Anything else is refused, loudly: a
#: section the hook silently dropped would be a write the operator believes
#: happened and did not.
KEYS = frozenset({"schema", "pr_number", "objective", "status", *TEXT_LISTS, *STRUCTURED})

#: Keys that belong to the governance handoff, named in the refusal.
MISPLACED = {
    "governance_friction": ".l9/memory/governance-handoff.json",
    "environment_friction": ".l9/memory/governance-handoff.json",
    "degraded_bootstrap": ".l9/memory/governance-handoff.json",
}


class HandoffError(ValueError):
    """The handoff file is absent, malformed, or not for this publication."""


def clean_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{field} must be a non-empty string")
    text = " ".join(value.split())
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


def clean_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise HandoffError(f"{key} must be a list")
    if len(value) > MAX_ITEMS:
        raise HandoffError(f"{key} has {len(value)} items; at most {MAX_ITEMS}")
    return value


def check_keys(
    payload: dict[str, Any], allowed: frozenset[str], *, misplaced: dict[str, str]
) -> None:
    """Refuse unknown top-level keys, naming the file a misplaced one belongs in."""
    unknown = sorted(set(payload) - allowed)
    if not unknown:
        return
    hints = [f"{k} belongs in {misplaced[k]}" for k in unknown if k in misplaced]
    detail = f" ({'; '.join(hints)})" if hints else ""
    raise HandoffError(f"unknown section(s) {', '.join(unknown)}{detail}")


def clean_structured(
    payload: dict[str, Any], key: str, spec: dict[str, tuple[str, tuple[str, ...]]] = STRUCTURED
) -> list[dict[str, str]]:
    """A list of {required, optional...} objects; a bare string is the required field."""
    required, optional = spec[key]
    out: list[dict[str, str]] = []
    for index, entry in enumerate(clean_list(payload, key)):
        where = f"{key}[{index}]"
        if isinstance(entry, str):
            entry = {required: entry}
        if not isinstance(entry, dict):
            raise HandoffError(f"{where} must be an object with {required!r}")
        item = {required: clean_text(entry.get(required), f"{where}.{required}")}
        for name in optional:
            if entry.get(name):
                item[name] = clean_text(entry[name], f"{where}.{name}")
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
    check_keys(payload, KEYS, misplaced=MISPLACED)
    number = payload.get("pr_number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise HandoffError("pr_number must be the published PR's number (a positive integer)")
    if pr_number is not None and payload.get("pr_number") != pr_number:
        raise HandoffError(
            f"pr_number {payload.get('pr_number')!r} is not this publication (#{pr_number})"
        )
    brief: dict[str, Any] = {
        "schema": HANDOFF_SCHEMA,
        "pr_number": payload.get("pr_number"),
        "objective": clean_text(payload.get("objective"), "objective"),
        "status": clean_text(payload.get("status"), "status"),
    }
    for key in TEXT_LISTS:
        brief[key] = [clean_text(v, f"{key}[{i}]") for i, v in enumerate(clean_list(payload, key))]
    for key in STRUCTURED:
        brief[key] = clean_structured(payload, key)
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


def example(pr_number: int) -> dict[str, Any]:
    """The shape the agent is asked to write — every section, for this publication."""
    return {
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
    }


def request_reason(
    *,
    pr_label: str,
    pr_number: int,
    missing: dict[str, str],
    governance: tuple[str, str, dict[str, Any]] | None = None,
) -> str:
    """What the Stop hook hands the agent, ONCE, when a post-publish handoff is missing.

    ONE request covers both handoffs: Claude Code runs every Stop hook in parallel
    and does not document how two concurrent ``decision: block`` outputs combine,
    so only the repository write-back ever blocks. ``missing`` maps each missing
    file to why it was not accepted; ``governance`` is (path, schema, example)
    of the governance handoff when that one is missing.
    """
    parts = [
        f"L9 post-publish handoffs required for {pr_label}. Write the file(s) below, "
        "then stop. Each is written ONCE to memory. Empty sections are []."
    ]
    if str(HANDOFF_REL) in missing:
        parts.append(
            f"\n1) {HANDOFF_REL} (schema {HANDOFF_SCHEMA}) — the comprehensive brief of "
            "where this contract stands, for the IN-SCOPE repository's memory. No "
            "environment/bootstrap/governance friction here. Not accepted because: "
            f"{missing[str(HANDOFF_REL)]}.\nShape:\n{json.dumps(example(pr_number), indent=2)}"
        )
    if governance is not None and governance[0] in missing:
        path, schema, shape = governance
        parts.append(
            f"\n2) {path} (schema {schema}) — ONLY environment friction, environment/"
            "governance blockers, degraded bootstrap items, workarounds and governance "
            "actions; written to the cursor-governance namespace, never the repository. "
            f"Not accepted because: {missing[path]}.\nShape:\n{json.dumps(shape, indent=2)}"
        )
    return "\n".join(parts)


__all__ = [
    "HANDOFF_REL",
    "HANDOFF_SCHEMA",
    "MAX_HANDOFF_BYTES",
    "MAX_ITEMS",
    "MAX_TEXT",
    "STRUCTURED",
    "TEXT_LISTS",
    "KEYS",
    "MISPLACED",
    "HandoffError",
    "check_keys",
    "clean_list",
    "clean_structured",
    "clean_text",
    "example",
    "load",
    "normalize",
    "render",
    "request_reason",
]
