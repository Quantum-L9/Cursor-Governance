"""``governance_diff`` — the actual delta, not just a dirty flag.

``governance_status`` reports porcelain counts. This reports what changed:
working-tree state, the stat summary, distance from ``origin/main``, and a
bounded unified diff. It is how a session proves it left the checkout clean.
"""

from __future__ import annotations

from typing import Any

from .base import RuntimeContext, ToolInputError, ToolSpec, truncate

NAME = "governance_diff"
DESCRIPTION = (
    "Report the governance checkout's working-tree state, diff stat, distance from "
    "origin/main and a bounded unified diff. Read-only."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_lines": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "description": "Maximum unified-diff lines to return. Defaults to 120.",
        },
        "include_patch": {
            "type": "boolean",
            "description": "Include the unified diff body. Defaults to true.",
        },
    },
    "additionalProperties": False,
}


def _lines(text: str, limit: int) -> list[str]:
    return text.splitlines()[:limit]


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    max_lines = arguments.get("max_lines", 120)
    if not isinstance(max_lines, int) or not 1 <= max_lines <= 500:
        raise ToolInputError("max_lines must be an integer between 1 and 500")
    include_patch = arguments.get("include_patch", True)
    if not isinstance(include_patch, bool):
        raise ToolInputError("include_patch must be a boolean")

    root = context.governance_root
    status = context.run(["git", "status", "--porcelain=v1", "--branch"], cwd=root, timeout=60)
    stat = context.run(["git", "diff", "--stat"], cwd=root, timeout=60)
    ahead = context.run(["git", "log", "--oneline", "origin/main..HEAD"], cwd=root, timeout=60)

    status_lines = (status.get("stdout") or "").splitlines()
    branch_line = status_lines[0] if status_lines else ""
    changes = [line for line in status_lines[1:] if line.strip()]

    result: dict[str, Any] = {
        "branch": branch_line,
        "dirty_count": len(changes),
        "changes": changes[:200],
        "diff_stat": (stat.get("stdout") or "").strip()[:4000],
        "ahead_of_origin_main": len((ahead.get("stdout") or "").splitlines())
        if ahead.get("status") == "completed" and ahead.get("exit_code") == 0
        else None,
        "ahead_commits": _lines(ahead.get("stdout") or "", 25),
    }

    if include_patch and changes:
        patch = context.run(["git", "diff", "--unified=1"], cwd=root, timeout=90)
        result["patch"] = truncate("\n".join(_lines(patch.get("stdout") or "", max_lines)))
        result["patch_truncated"] = len((patch.get("stdout") or "").splitlines()) > max_lines
    elif include_patch:
        result["patch"] = ""
        result["patch_truncated"] = False

    result["clean"] = result["dirty_count"] == 0
    return result


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
