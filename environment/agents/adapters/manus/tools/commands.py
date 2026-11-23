"""``governance_commands`` — the slash-command catalog.

Resolves a command name to its file and reads its opening lines, so a session
invokes the repository's own procedure instead of reconstructing one from
memory.
"""

from __future__ import annotations

from typing import Any

from .base import RuntimeContext, ToolInputError, ToolSpec, read_text, truncate

NAME = "governance_commands"
DESCRIPTION = (
    "List the repository slash commands, or read one command's definition by name. "
    "Read-only; reads only from commands/."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Command name with or without the leading slash, e.g. 'architect'.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "description": "Maximum catalog entries when no name is given. Defaults to 100.",
        },
        "excerpt_lines": {
            "type": "integer",
            "minimum": 1,
            "maximum": 120,
            "description": (
                "Lines of the command file to return when a name is given. Defaults to 40."
            ),
        },
    },
    "additionalProperties": False,
}


def _catalog(context: RuntimeContext) -> list[dict[str, Any]]:
    root = context.governance_root
    manifest = root / "commands/COMMANDS_MANIFEST.yaml"
    items: list[dict[str, Any]] = []
    if manifest.is_file():
        current: dict[str, Any] | None = None
        for line in read_text(manifest).splitlines():
            stripped = line.strip()
            if stripped.startswith("- slash:"):
                current = {
                    "slash": stripped.partition(":")[2].strip(),
                    "file": "",
                    "enabled": True,
                }
                items.append(current)
            elif current is not None and stripped.startswith("file:"):
                current["file"] = stripped.partition(":")[2].strip()
            elif current is not None and stripped.startswith("enabled:"):
                current["enabled"] = stripped.partition(":")[2].strip().lower() != "false"
    if not items:
        for path in sorted((root / "commands").glob("*.md")):
            items.append(
                {"slash": f"/{path.stem}", "file": f"commands/{path.name}", "enabled": True}
            )
    return items


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    catalog = _catalog(context)
    name = arguments.get("name")

    if name is None:
        limit = arguments.get("limit", 100)
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ToolInputError("limit must be an integer between 1 and 200")
        return {
            "count": len(catalog),
            "commands": catalog[:limit],
            "source": "commands/COMMANDS_MANIFEST.yaml",
        }

    if not isinstance(name, str) or not name.strip():
        raise ToolInputError("name must be a non-empty string when provided")
    wanted = name.strip().lstrip("/").lower()
    match = next((item for item in catalog if item["slash"].lstrip("/").lower() == wanted), None)
    if match is None:
        available = sorted(item["slash"] for item in catalog)[:40]
        raise ToolInputError(
            f"unknown command: {name}. Known commands include: {', '.join(available)}"
        )

    excerpt_lines = arguments.get("excerpt_lines", 40)
    if not isinstance(excerpt_lines, int) or not 1 <= excerpt_lines <= 120:
        raise ToolInputError("excerpt_lines must be an integer between 1 and 120")

    target = context.path(match["file"]) if match.get("file") else None
    body = ""
    if target is not None and target.is_file():
        body = "\n".join(read_text(target).splitlines()[:excerpt_lines])
    return {
        "command": match,
        "path": match.get("file"),
        "excerpt": truncate(body),
        "truncated": bool(body) and len(body.splitlines()) >= excerpt_lines,
    }


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
