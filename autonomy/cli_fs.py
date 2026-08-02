"""CLI-only filesystem helpers for argv paths (Sonar S8707 residual class).

Library code must use ``autonomy.io`` with trusted ``pathlib.Path`` values
derived from repository roots / ``__file__``, never raw CLI strings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def under_root(root: str | Path, rel: str, *, label: str = "path") -> Path:
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    if os.path.isabs(rel) or rel.startswith("~") or ".." in Path(rel).parts:
        raise ValueError(f"{label} must be relative with no '..' or '~': {rel}")
    base = os.path.realpath(str(root))
    if not os.path.isdir(base):
        raise ValueError(f"trusted root is not a directory: {root}")
    target = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, target]) != base:
        raise ValueError(f"{label} escapes trusted root {base}: {rel}")
    return Path(target)


def confined_cli_path(
    path: str | Path,
    *,
    root: str | Path | None = None,
    label: str = "path",
) -> Path:
    requested = Path(path)
    if root is not None:
        base = Path(root).resolve()
    elif requested.is_absolute():
        base = requested.parent.resolve()
        return under_root(base, requested.name, label=label)
    else:
        base = Path.cwd().resolve()
    if requested.is_absolute():
        try:
            rel = str(requested.resolve().relative_to(base))
        except ValueError as exc:
            raise ValueError(f"{label} escapes trusted root {base}: {path}") from exc
    else:
        rel = str(requested)
    return under_root(base, rel, label=label)


def load_json_cli(path: str | Path, *, root: str | Path | None = None) -> Any:
    source = confined_cli_path(path, root=root, label="json path")
    with open(source, encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc


def write_json_cli(path: str | Path, value: Any, *, root: str | Path | None = None) -> None:
    target = confined_cli_path(path, root=root, label="json path")
    base = target.parent
    base.mkdir(parents=True, exist_ok=True)
    temporary = under_root(base, target.name + ".tmp", label="json temp path")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, target)


def read_jsonl_cli(path: str | Path, *, root: str | Path | None = None) -> list[dict[str, Any]]:
    source = confined_cli_path(path, root=root, label="events path")
    events: list[dict[str, Any]] = []
    with open(source, encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return events
