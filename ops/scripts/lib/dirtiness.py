#!/usr/bin/env python3
"""Shared classification of worktree dirtiness paths.

One definition of "generated" and "scratch", used by both
ops/scripts/classify_generated_dirtiness.sh (does this dirt fail the gate?) and
ops/scripts/attribute_tree_writers.sh (who wrote it, and does that matter?).
Keeping the prefixes in one place stops the two answers from drifting apart.
"""

from __future__ import annotations

import json
import sys
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


def _load_is_generated_path():
    # Resolve the allowlist next to this file, not under the tree being
    # measured: the measured tree may be a consumer repo or a test fixture.
    scripts = str(Path(__file__).resolve().parent.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from sync_generated_artifacts import is_generated_path  # noqa: PLC0415

    return is_generated_path


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
    if _load_is_generated_path()(normalized):
        return "generated"
    if normalized in protected_root_files(root):
        return "protected"
    return "source"


def decode_git_quoted_path(path: str) -> str:
    """Decode C-style escapes in git status quoted paths (octal + \\n \\t \\\" \\\\)."""
    raw = bytearray()
    i = 0
    while i < len(path):
        ch = path[i]
        if ch != "\\" or i + 1 >= len(path):
            raw.extend(ch.encode("utf-8"))
            i += 1
            continue
        nxt = path[i + 1]
        if nxt == "n":
            raw.append(0x0A)
            i += 2
            continue
        if nxt == "t":
            raw.append(0x09)
            i += 2
            continue
        if nxt == "r":
            raw.append(0x0D)
            i += 2
            continue
        if nxt == "b":
            raw.append(0x08)
            i += 2
            continue
        if nxt == '"':
            raw.extend(b'"')
            i += 2
            continue
        if nxt == "\\":
            raw.extend(b"\\")
            i += 2
            continue
        if nxt in "01234567":
            j = i + 1
            while j < len(path) and j < i + 4 and path[j] in "01234567":
                j += 1
            raw.append(int(path[i + 1 : j], 8))
            i = j
            continue
        raw.extend(ch.encode("utf-8"))
        i += 1
    return raw.decode("utf-8")


def porcelain_path(line: str) -> str:
    """Extract the path from a `git status --porcelain` line, handling renames."""
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if path.startswith('"') and path.endswith('"') and len(path) > 1:
        path = decode_git_quoted_path(path[1:-1])
    return normalize(path)
