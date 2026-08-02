from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def under_root(root: str | Path, rel: str, *, label: str = "path") -> Path:
    """Join a relative path under trusted ``root`` (Sonar-recognized sanitizer)."""
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    if os.path.isabs(rel) or rel.startswith("~") or ".." in Path(rel).parts:
        raise ValueError(f"{label} must be relative with no '..' or '~': {rel}")
    base = os.path.realpath(str(root))
    if not os.path.isdir(base):
        raise ValueError(f"trusted root is not a directory: {root}")
    # Construct from base + relative only — never trust a free-form absolute CLI path.
    target = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, target]) != base:
        raise ValueError(f"{label} escapes trusted root {base}: {rel}")
    return Path(target)


def confined_path(
    path: str | Path,
    *,
    root: str | Path | None = None,
    label: str = "path",
) -> Path:
    """Resolve ``path`` under ``root`` via ``under_root``.

    Absolute paths must stay under ``root`` (default cwd). Absolute destinations
    outside cwd are allowed only when ``root`` is set to their parent (CLI outputs).
    """
    requested = Path(path)
    if root is not None:
        base = Path(root).resolve()
    elif requested.is_absolute():
        # Allow absolute paths by confining to their parent directory.
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


def load_json(path: str | Path, *, root: str | Path | None = None) -> Any:
    source = confined_path(path, root=root, label="json path")
    # open after join+realpath+commonpath sanitizer (under_root).
    try:
        with open(source, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file does not exist: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def write_json(path: str | Path, value: Any, *, root: str | Path | None = None) -> None:
    target = confined_path(path, root=root, label="json path")
    base = target.parent
    base.mkdir(parents=True, exist_ok=True)
    temporary = under_root(base, target.name + ".tmp", label="json temp path")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, target)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path, *, root: str | Path | None = None) -> str:
    source = confined_path(path, root=root, label="file path")
    digest = hashlib.sha256()
    with open(source, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
