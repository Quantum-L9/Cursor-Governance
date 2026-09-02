#!/usr/bin/env python3
"""Spawn a campaign child process.

`run_campaign.py` is too large for Semgrep taint rules
(`dangerous-subprocess-use-tainted-env-args`,
`dangerous-system-call-tainted-env-args`): they time out and required
Analyze (central Core) fails incomplete with zero findings. This module
is the only place a campaign process is spawned.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_PREFIX",
    ):
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    env["GCM_INTERACTIVE"] = "never"
    return env


def run_child(
    cmd: list[str],
    *,
    timeout: int,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy() if env is None else dict(env)
    child_env.setdefault("L9_CAMPAIGN_TUNNEL", "1")
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd is not None else None,
        env=child_env,
    )
