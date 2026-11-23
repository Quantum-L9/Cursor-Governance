"""``governance_resolve`` — map a task to the law that governs it.

Deterministic lexical resolution over ``kernels/``, ``rules/``, ``contracts/``,
``protocols/`` and ``commands/``. No embeddings, no model call: the same query
returns the same ranking on every host, which is the property that makes it
citable as evidence.
"""

from __future__ import annotations

from typing import Any

from .base import (
    MAX_SEARCH_RESULTS,
    RuntimeContext,
    ToolInputError,
    ToolSpec,
    first_meaningful_line,
    iter_documents,
    read_text,
    tokenize,
    truncate,
)

NAME = "governance_resolve"
DESCRIPTION = (
    "Resolve a task description to the governing kernels, rules, contracts, protocols "
    "and commands, ranked deterministically by lexical overlap. Read-only."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Task or question to resolve against the governance corpus.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SEARCH_RESULTS,
            "description": "Maximum matches to return. Defaults to 8.",
        },
        "kinds": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["kernel", "rule", "contract", "protocol", "command"],
            },
            "description": "Restrict resolution to these document kinds.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

PREFIXES: tuple[tuple[str, str], ...] = (
    ("kernels/", "kernel"),
    ("rules/", "rule"),
    ("contracts/", "contract"),
    ("protocols/", "protocol"),
    ("commands/", "command"),
)


def _title(text: str, path_name: str) -> str:
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:160]
        if stripped.startswith("name:"):
            return stripped.partition(":")[2].strip().strip("'\"")[:160]
    return first_meaningful_line(text) or path_name


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ToolInputError("query must be a non-empty string")
    limit = arguments.get("limit", 8)
    if not isinstance(limit, int) or not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ToolInputError(f"limit must be an integer between 1 and {MAX_SEARCH_RESULTS}")
    kinds = arguments.get("kinds")
    if kinds is not None and (
        not isinstance(kinds, list) or not set(kinds).issubset({kind for _, kind in PREFIXES})
    ):
        raise ToolInputError("kinds must be a subset of kernel, rule, contract, protocol, command")

    wanted = set(kinds) if kinds else {kind for _, kind in PREFIXES}
    tokens = tokenize(query)
    if not tokens:
        raise ToolInputError("query produced no searchable tokens")

    matches: list[dict[str, Any]] = []
    for prefix, kind in PREFIXES:
        if kind not in wanted:
            continue
        for path in iter_documents(context.governance_root, (prefix,)):
            relative = path.relative_to(context.governance_root).as_posix()
            try:
                text = read_text(path)
            except ToolInputError:
                continue
            name_tokens = tokenize(relative)
            head_tokens = tokenize("\n".join(text.splitlines()[:40]))
            score = 3 * len(tokens & name_tokens) + len(tokens & head_tokens)
            if score <= 0:
                continue
            matches.append(
                {
                    "path": relative,
                    "kind": kind,
                    "title": _title(text, path.name),
                    "score": score,
                    "matched_terms": sorted(tokens & (name_tokens | head_tokens))[:12],
                    "excerpt": truncate(first_meaningful_line(text), 240),
                }
            )

    matches.sort(key=lambda item: (-item["score"], item["path"]))
    return {
        "query": query,
        "count": len(matches),
        "returned": min(limit, len(matches)),
        "matches": matches[:limit],
        "method": "deterministic lexical overlap (path weight 3, head weight 1)",
    }


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
