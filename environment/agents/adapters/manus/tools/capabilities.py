"""``governance_capabilities`` — what the repository can actually do.

Surfaces the four discovery planes a session needs before planning: skills,
slash commands, protocols, and make targets. Each section is parsed from its
declared registry where one exists, and degrades to a directory scan when it
does not — never to a guess.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .base import RuntimeContext, ToolInputError, ToolSpec, read_text, truncate

NAME = "governance_capabilities"
DESCRIPTION = (
    "List the repository capability planes: skills, slash commands, protocols and make "
    "targets, with counts. Read-only."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "section": {
            "type": "string",
            "enum": ["all", "skills", "commands", "protocols", "targets"],
            "description": "Restrict output to one plane. Defaults to all.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "description": "Maximum entries per section. Defaults to 50.",
        },
    },
    "additionalProperties": False,
}

_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*):[ \t]*(?:##[ \t]*(.*))?$")
_FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)


def _frontmatter_value(text: str, key: str) -> str:
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.partition(":")[2].strip().strip("'\"")[:200]
    return ""


def _skills(context: RuntimeContext, limit: int) -> dict[str, Any]:
    root = context.governance_root
    registry = root / "ops/generated/skill-registry.json"
    entries: list[dict[str, Any]] = []
    source = "directory scan"
    if registry.is_file():
        try:
            payload = json.loads(read_text(registry))
        except (ToolInputError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            for key in ("skills", "entries", "registry", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            entries.append(
                                {
                                    "name": item.get("name") or item.get("id") or "",
                                    "description": truncate(
                                        str(item.get("description") or ""), 200
                                    ),
                                }
                            )
                    source = f"ops/generated/skill-registry.json[{key}]"
                    break
    if not entries:
        for skill in sorted((root / "skills").glob("*/SKILL.md")):
            if skill.parent.name.startswith("_"):
                continue
            text = read_text(skill)
            entries.append(
                {
                    "name": skill.parent.name,
                    "description": truncate(_frontmatter_value(text, "description"), 200),
                }
            )
    entries = [entry for entry in entries if entry.get("name")]
    return {"count": len(entries), "source": source, "items": entries[:limit]}


def _commands(context: RuntimeContext, limit: int) -> dict[str, Any]:
    root = context.governance_root
    manifest = root / "commands/COMMANDS_MANIFEST.yaml"
    items: list[dict[str, Any]] = []
    source = "commands/*.md"
    if manifest.is_file():
        text = read_text(manifest)
        current: dict[str, Any] | None = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- slash:"):
                current = {"slash": stripped.partition(":")[2].strip(), "file": "", "enabled": True}
                items.append(current)
            elif current is not None and stripped.startswith("file:"):
                current["file"] = stripped.partition(":")[2].strip()
            elif current is not None and stripped.startswith("enabled:"):
                current["enabled"] = stripped.partition(":")[2].strip().lower() != "false"
        source = "commands/COMMANDS_MANIFEST.yaml"
    if not items:
        for command in sorted((root / "commands").glob("*.md")):
            items.append(
                {"slash": f"/{command.stem}", "file": f"commands/{command.name}", "enabled": True}
            )
    return {"count": len(items), "source": source, "items": items[:limit]}


def _protocols(context: RuntimeContext, limit: int) -> dict[str, Any]:
    items = [
        {"name": path.name, "path": path.relative_to(context.governance_root).as_posix()}
        for path in sorted((context.governance_root / "protocols").glob("*.md"))
    ]
    return {"count": len(items), "source": "protocols/*.md", "items": items[:limit]}


def _targets(context: RuntimeContext, limit: int) -> dict[str, Any]:
    root = context.governance_root
    files = [root / "Makefile", root / "Repo.mk", *sorted((root / "ops/make").glob("*.mk"))]
    seen: dict[str, str] = {}
    for path in files:
        if not path.is_file():
            continue
        for line in read_text(path).splitlines():
            match = _TARGET_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            if name.startswith("."):
                continue
            seen.setdefault(name, truncate((match.group(2) or "").strip(), 160))
    items = [{"target": name, "description": seen[name]} for name in sorted(seen)]
    return {
        "count": len(items),
        "source": "Makefile + Repo.mk + ops/make/*.mk",
        "items": items[:limit],
    }


_SECTIONS = {
    "skills": _skills,
    "commands": _commands,
    "protocols": _protocols,
    "targets": _targets,
}


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    section = arguments.get("section", "all")
    if section not in {"all", *_SECTIONS}:
        raise ToolInputError("section must be one of all, skills, commands, protocols, targets")
    limit = arguments.get("limit", 50)
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ToolInputError("limit must be an integer between 1 and 200")

    selected = _SECTIONS if section == "all" else {section: _SECTIONS[section]}
    result: dict[str, Any] = {"section": section}
    for name, collector in selected.items():
        result[name] = collector(context, limit)
    return result


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
