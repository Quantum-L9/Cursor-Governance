#!/usr/bin/env python3
"""Shared deterministic primitives for L9 Idea Foundry scripts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment gate
    raise SystemExit(
        "PyYAML is required for L9 Idea Foundry contract validation; "
        "install the repository's declared Python dependencies before running Foundry scripts"
    ) from exc


class FoundryContractError(ValueError):
    """Raised when a Foundry machine contract is malformed."""


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    return all(c in "0123456789abcdef" for c in value[7:])


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def semantic_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FoundryContractError(f"cannot read YAML {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise FoundryContractError(f"YAML is not UTF-8 {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise FoundryContractError(f"invalid YAML {path}: {exc}") from exc


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    value = load_yaml(path)
    if not isinstance(value, dict):
        raise FoundryContractError(f"YAML root must be a mapping: {path}")
    return value


def semantic_yaml_digest(path: Path) -> str:
    return semantic_digest(load_yaml(path))


def require_schema(mapping: dict[str, Any], expected: str, label: str) -> None:
    observed = mapping.get("schema")
    if observed != expected:
        raise FoundryContractError(
            f"{label} schema mismatch: expected {expected!r}, observed {observed!r}"
        )


def git_output(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def git_require(root: Path, *args: str) -> str:
    rc, out = git_output(root, *args)
    if rc != 0:
        raise FoundryContractError(f"git {' '.join(args)} failed: {out}")
    return out


def tracked_tree_records(root: Path) -> list[dict[str, object]]:
    raw = git_require(root, "ls-files", "-z")
    paths = [p for p in raw.split("\0") if p]
    records: list[dict[str, object]] = []
    for rel in sorted(paths):
        path = root / rel
        if path.is_symlink():
            data = path.readlink().as_posix().encode("utf-8")
            digest = sha256_bytes(data)
            size = len(data)
        else:
            digest = sha256_file(path)
            size = path.stat().st_size
        records.append({"path": rel, "size": size, "sha256": digest})
    return records


def tracked_tree_digest(root: Path) -> tuple[list[dict[str, object]], str]:
    records = tracked_tree_records(root)
    return records, semantic_digest(records)
