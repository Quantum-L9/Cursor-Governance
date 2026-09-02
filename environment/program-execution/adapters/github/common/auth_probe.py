from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from adapters.github.common.gh_transport import GhTransport


def probe(cwd: str | Path) -> dict[str, Any]:
    executable = shutil.which("gh")
    if executable is None:
        return {"status": "BLOCKED", "reason": "gh executable unavailable"}
    # Probe the capability actually needed -- an authenticated API call --
    # never `gh auth status`: on model-controlled surfaces its exit code does
    # not agree with itself across containers while `gh api` works
    # (docs/DEGRADED_MODE_CONTRACT.md; rules/62).
    result = GhTransport(cwd).run(["api", "user"], 30)
    authenticated = result.exit_code == 0 and _names_a_login(result.stdout)
    return {
        "status": "PASS" if authenticated else "BLOCKED",
        "executable": executable,
        "stdout_digest": result.stdout_digest,
        "stderr_digest": result.stderr_digest,
        "reason": (None if authenticated else "gh authentication unavailable"),
    }


def _names_a_login(stdout: str) -> bool:
    try:
        payload = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and bool(str(payload.get("login") or "").strip())
