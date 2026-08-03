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
        json_body: dict[str, Any] | None = None,
        timeout_seconds: int = 120,
    ) -> Any:
        if fields is not None and json_body is not None:
            raise ValueError("pass fields or json_body, not both")
        argv = ["api", endpoint, "--method", method]
        if json_body is not None:
            argv.extend(["--input", "-"])
            result = run_argv(
                ["gh", *argv],
                cwd=self.cwd,
                timeout_seconds=timeout_seconds,
                stdin=json.dumps(json_body),
            )
            if result.exit_code != 0:
                raise RuntimeError(result.stderr or "gh command failed")
            return json.loads(result.stdout) if result.stdout.strip() else None
        for key, value in sorted((fields or {}).items()):
            argv.extend(["-f", f"{key}={value}"])
        return self.json(argv, timeout_seconds)
