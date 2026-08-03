from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from adapters.github.common.gh_transport import GhTransport


def probe(cwd: str | Path) -> dict[str, Any]:
    executable = shutil.which("gh")
    if executable is None:
        return {"status": "BLOCKED", "reason": "gh executable unavailable"}
    result = GhTransport(cwd).run(
        ["auth", "status", "--hostname", "github.com"],
        30,
    )
    return {
        "status": "PASS" if result.exit_code == 0 else "BLOCKED",
        "executable": executable,
        "stdout_digest": result.stdout_digest,
        "stderr_digest": result.stderr_digest,
        "reason": (None if result.exit_code == 0 else "gh authentication unavailable"),
    }
