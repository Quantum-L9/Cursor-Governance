from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import run_argv


def push_branch(
    repository_path: str | Path,
    *,
    remote: str,
    local_branch: str,
    remote_branch: str,
) -> dict[str, Any]:
    result = run_argv(
        ["git", "push", remote, f"{local_branch}:refs/heads/{remote_branch}"],
        cwd=repository_path,
        timeout_seconds=300,
    )
    if result.exit_code != 0:
        raise RuntimeError(result.stderr or "git push failed")
    return result.to_evidence()
