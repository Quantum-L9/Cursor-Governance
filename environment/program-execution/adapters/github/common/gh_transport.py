from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import CommandResult, run_argv


class GhTransport:
    def __init__(self, cwd: str | Path) -> None:
        self.cwd = Path(cwd).resolve()

    def run(self, argv: list[str], timeout_seconds: int = 120) -> CommandResult:
        return run_argv(
            ["gh", *argv],
            cwd=self.cwd,
            timeout_seconds=timeout_seconds,
        )

    def json(self, argv: list[str], timeout_seconds: int = 120) -> Any:
        result = self.run(argv, timeout_seconds)
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or "gh command failed")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def api(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        fields: dict[str, str] | None = None,
        timeout_seconds: int = 120,
    ) -> Any:
        argv = ["api", endpoint, "--method", method]
        for key, value in sorted((fields or {}).items()):
            argv.extend(["-f", f"{key}={value}"])
        return self.json(argv, timeout_seconds)
