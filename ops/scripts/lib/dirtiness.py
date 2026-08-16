#!/usr/bin/env python3
"""Shared classification of worktree dirtiness paths.

One definition of "generated" and "scratch", used by both
ops/scripts/classify_generated_dirtiness.sh (does this dirt fail the gate?) and
ops/scripts/attribute_tree_writers.sh (who wrote it, and does that matter?).
Keeping the prefixes in one place stops the two answers from drifting apart.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# Sacred / scratch trees: git-visible, never gate-blocking. Keep in sync with
# .pre-commit-config.yaml `exclude` and ops/scripts/resolve_changed_files.sh.
SCRATCH_PREFIXES = (
    "WIP/",
    "current_work/",
    "C_GOV_FILES/",
    "reports/",
    ".l9/",
)

_BARE_SCRATCH = {prefix.rstrip("/") for prefix in SCRATCH_PREFIXES}

# Allowlist SSOT. sync_generated_artifacts.py re-exports these names.
# Stdlib only — classify/attribute subprocesses must not require PyYAML.
GENERATED_PATH_PREFIXES = (
    "rules/RULES-MANIFEST.",
    "environment/generated/llm-rules/",
    "ops/generated/skill-registry.json",
    "environment/agents/adapters/claude-code/settings.template.json",
    "commands/COMMANDS_MANIFEST.yaml",
    "skills/AUTONOMY_MANIFEST.yaml",
    "environment/program-execution/core/MANIFEST.yaml",
    "environment/program-execution/MANIFEST.json",
)


def is_generated_path(rel: str) -> bool:
    if any(
        rel.startswith(prefix) or rel == prefix.rstrip(".") for prefix in GENERATED_PATH_PREFIXES
    ):
        return True
    if re.match(r"^skills/[^/]+/SKILL\.md$", rel):
        return True
    return False


def normalize(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_scratch_path(path: str) -> bool:
    normalized = normalize(path)
    if normalized in _BARE_SCRATCH:
        return True
    return any(normalized.startswith(prefix) for prefix in SCRATCH_PREFIXES)


@lru_cache(maxsize=8)
def protected_root_files(root: Path) -> set[str]:
    """Repository-root files registered in the append-only protection policy."""
    policy = root / "ops" / "config" / "root-file-protection.json"
    try:
        data = json.loads(policy.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    entries = data.get("protected_files") or []
    names: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path"):
            names.add(str(entry["path"]))
        elif isinstance(entry, str):
            names.add(entry)
    return names


def classify_path(root: Path, path: str) -> str:
    """One of: scratch, generated, protected, source. ``root`` is the tree being
    measured; it supplies the protected-root-file policy only."""
    normalized = normalize(path)
    if is_scratch_path(normalized):
        return "scratch"
    if is_generated_path(normalized):
        return "generated"
    if normalized in protected_root_files(root):
        return "protected"
    return "source"


def porcelain_path(line: str) -> str:
    """Extract the path from a `git status --porcelain` line, handling renames."""
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if path.startswith('"') and path.endswith('"') and len(path) > 1:
        path = path[1:-1]
    return normalize(path)
