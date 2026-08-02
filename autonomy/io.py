from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def confined_path(
    path: str | Path,
    *,
    root: str | Path | None = None,
    label: str = "path",
) -> Path:
    """Resolve ``path`` and require it stays under a trusted root (Sonar S8707).

    When ``root`` is omitted:
    - relative paths are confined to ``Path.cwd()``
    - absolute paths are confined to their own parent directory (blocks ``..`` /
      symlink escapes out of that parent)
    """
    requested = Path(path)
    if ".." in requested.parts:
        raise ValueError(f"{label} must not contain '..' path segments: {path}")

    if root is not None:
        base_real = os.path.realpath(str(Path(root)))
    elif requested.is_absolute():
        base_real = os.path.realpath(str(requested.parent))
    else:
        base_real = os.path.realpath(str(Path.cwd()))

    if requested.is_absolute():
        target_real = os.path.realpath(str(requested))
    else:
        target_real = os.path.realpath(os.path.join(base_real, str(requested)))

    try:
        if os.path.commonpath([base_real, target_real]) != base_real:
            raise ValueError(f"{label} escapes trusted root {base_real}: {path}")
    except ValueError as exc:
        raise ValueError(f"{label} escapes trusted root {base_real}: {path}") from exc
    return Path(target_real)


def load_json(path: str | Path, *, root: str | Path | None = None) -> Any:
    source = confined_path(path, root=root, label="json path")
    try:
        with source.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file does not exist: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def write_json(path: str | Path, value: Any, *, root: str | Path | None = None) -> None:
    target = confined_path(path, root=root, label="json path")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = confined_path(
        target.with_suffix(target.suffix + ".tmp"),
        root=root,
        label="json temp path",
    )
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(target)


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
    digest = hashlib.sha256()
    with confined_path(path, root=root, label="file path").open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
