from __future__ import annotations

import hashlib
import json
from pathlib import Path

from adapters.common.subprocess_runner import CommandResult

_EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def candidate_snapshot(root: str | Path) -> dict[str, object]:
    candidate = Path(root).resolve()
    files = []
    for path in sorted(candidate.rglob("*")):
        relative = path.relative_to(candidate)
        if any(part in _EXCLUDED_PARTS for part in relative.parts):
            continue
        if not path.is_file() or path.suffix in _EXCLUDED_SUFFIXES:
            continue
        files.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "digest": "sha256:" + hashlib.sha256(payload.encode()).hexdigest(),
        "files": files,
    }


def validation_evidence(
    command: list[str],
    result: CommandResult,
) -> dict[str, object]:
    evidence = result.to_evidence()
    return {
        "command": " ".join(command),
        "status": "PASS" if result.exit_code == 0 else "FAIL",
        "exit_code": result.exit_code,
        "evidence": str(evidence["stdout_digest"]),
        "command_evidence": evidence,
    }
