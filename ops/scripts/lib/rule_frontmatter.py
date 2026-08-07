"""Shared Cursor rule (.mdc) frontmatter parsing.

Used by generate_rules_manifest.py and project_llm_rules.py so there is one
parser for governance rule metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ParsedRule:
    path: Path
    metadata: dict[str, Any]
    body: str
    has_frontmatter: bool


def parse_rule(path: Path) -> ParsedRule:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    body = text
    has_frontmatter = False
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            raw = yaml.safe_load(parts[1]) or {}
            if not isinstance(raw, dict):
                raise ValueError(f"frontmatter must be a mapping: {path}")
            metadata = raw
            body = parts[2]
            has_frontmatter = True
    return ParsedRule(path=path, metadata=metadata, body=body, has_frontmatter=has_frontmatter)


def normalize_globs(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def activation_class(metadata: dict[str, Any], globs: list[str] | None) -> str:
    """Return always | paths | agent_requested for projection decisions."""
    if metadata.get("alwaysApply") is True:
        return "always"
    if globs:
        return "paths"
    return "agent_requested"
