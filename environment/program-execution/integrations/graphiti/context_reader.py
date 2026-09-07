from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import run_argv


class GraphitiContextReader:
    """Read-only memory lookup for evidence collection.

    Since realignment stage C11 the reader crosses the canonical memory
    control plane (``python -m ops.memory.cli search``) and never a provider.
    It exposes ``search`` only: no write, claim, phase-lock, or promotion.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.client = self.root / "ops/memory/cli.py"

    def search(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        if not self.client.is_file():
            raise FileNotFoundError(self.client)
        result = run_argv(
            [
                sys.executable,
                "-m",
                "ops.memory.cli",
                "search",
                query,
                "--limit",
                str(limit),
                "--workspace",
                str(self.root),
            ],
            cwd=self.root,
            timeout_seconds=30,
        )
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or result.stdout or "memory search failed")
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("memory search output must be an object")
        return value
