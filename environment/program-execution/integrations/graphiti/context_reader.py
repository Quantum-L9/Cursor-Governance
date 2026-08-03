from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import run_argv


class GraphitiContextReader:
    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.client = self.root / "ops/graphiti/graphiti_memory_client.py"

    def search(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        if not self.client.is_file():
            raise FileNotFoundError(self.client)
        result = run_argv(
            ["python3", str(self.client), "search", query, "--limit", str(limit)],
            cwd=self.root,
            timeout_seconds=30,
        )
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or "Graphiti search failed")
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("Graphiti search output must be an object")
        return value
