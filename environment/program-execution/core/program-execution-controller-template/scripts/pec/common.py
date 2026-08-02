from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    path_r = os.path.realpath(str(path))
    with open(path_r, encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> Any:
    path_r = os.path.realpath(str(path))
    with open(path_r, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_json(path: Path, value: Any) -> None:
    path_r = os.path.realpath(str(path))
    parent = os.path.dirname(path_r)
    os.makedirs(parent, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=parent, delete=False) as handle:
        handle.write(payload)
        temp = handle.name
    os.replace(temp, path_r)


def resolve_within(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {candidate}") from exc
    return resolved


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip() or completed.stdout.strip() or f"git command failed: {args}"
        )
    return completed
