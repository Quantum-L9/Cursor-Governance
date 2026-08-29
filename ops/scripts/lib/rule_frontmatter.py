"""Shared Cursor rule (.mdc) frontmatter parsing.

Used by generate_rules_manifest.py and project_llm_rules.py so there is one
parser for governance rule metadata.

Invariant (harvest C4): unparseable metadata is a named finding, never a skip.
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
            try:
                raw = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"frontmatter parse failed: {path}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"frontmatter must be a mapping: {path}")
            metadata = raw
            body = parts[2]
            has_frontmatter = True
    return ParsedRule(path=path, metadata=metadata, body=body, has_frontmatter=has_frontmatter)


def _split_glob_token(value: str) -> list[str]:
    """Split Cursor comma-separated glob strings into individual patterns."""
    return [part.strip().strip("\"'") for part in value.split(",") if part.strip()]


def normalize_globs(value: Any) -> list[str] | None:
    """Return glob patterns as a list.

    Cursor-native frontmatter uses a comma-separated string
    (`globs: tests/**, **/*_test.py`). Older rules used a YAML list. Both
    forms must round-trip to a list of individual patterns so Claude
    llm-rules `paths:` and RULES-MANIFEST entries stay per-pattern.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return _split_glob_token(value)
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            if "," in text:
                out.extend(_split_glob_token(text))
            else:
                out.append(text.strip("\"'"))
        return out
    return [str(value)]


def always_apply_is_true(metadata: dict[str, Any]) -> bool:
    value = metadata.get("alwaysApply")
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def emit_native_frontmatter(metadata: dict[str, Any]) -> str:
    """Emit Cursor-native frontmatter: description, globs, alwaysApply.

    Drops globs when alwaysApply is true (Cursor ignores them). Quotes via
    yaml.safe_dump so glob characters cannot corrupt parse_rule().
    """
    payload: dict[str, Any] = {}
    description = str(metadata.get("description") or "").strip()
    if description:
        payload["description"] = description
    aa = always_apply_is_true(metadata)
    if not aa:
        globs = normalize_globs(metadata.get("globs"))
        if globs:
            payload["globs"] = ", ".join(globs)
    payload["alwaysApply"] = aa
    dumped = yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1000,
    ).rstrip()
    return f"---\n{dumped}\n---\n"


def activation_class(metadata: dict[str, Any], globs: list[str] | None) -> str:
    """Return always | paths | agent_requested for projection decisions."""
    if always_apply_is_true(metadata):
        return "always"
    if globs:
        return "paths"
    return "agent_requested"
