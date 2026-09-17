from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import run_argv


class GraphitiContextReader:
    """Read-only memory lookup for evidence collection — agent lane (ADR-0033).

    A Program Execution worker reading memory for its own task is an *agent*,
    not an automatic hook. Since realignment stage C15 it therefore calls the
    memory package's public ``l9-memory search`` directly and never crosses
    ``MemoryControlPlaneClient`` (the hook lane) or a provider. Cursor-Governance
    is consulted only to *locate* the bound interpreter
    (``ops.memory.runtime_binding``); it interposes nothing on the read.

    It exposes ``search`` only: no write, claim, phase-lock, or promotion.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.binding_module = self.root / "ops/memory/runtime_binding.py"

    def _memory_cli(self) -> str:
        """The bound ``l9-memory`` console script, or raise with the binding's reasons."""
        if not self.binding_module.is_file():
            raise FileNotFoundError(self.binding_module)
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from ops.memory.runtime_binding import resolve_runtime_binding

        binding = resolve_runtime_binding()
        if not (binding.ok and binding.memory_cli):
            raise RuntimeError(
                "memory runtime unbound: " + ("; ".join(binding.reasons) or "no reason recorded")
            )
        return str(binding.memory_cli)

    def search(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        result = run_argv(
            [self._memory_cli(), "search", query, "--limit", str(limit), "--include-workspace"],
            cwd=self.root,
            timeout_seconds=30,
        )
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or result.stdout or "memory search failed")
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("memory search output must be an object")
        return value
