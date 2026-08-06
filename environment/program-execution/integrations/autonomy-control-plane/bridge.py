from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from adapters.common.imports import load_module


class AutonomyControlPlaneBridge:
    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()

    def probe(self) -> dict[str, Any]:
        required = [
            self.root / "autonomy/runtime/engine.py",
            self.root / "autonomy/adapters/orchestrator.py",
            self.root / "autonomy/adapters/cursor/adapter.py",
            self.root / "autonomy/adapters/claude_code/adapter.py",
        ]
        missing = [str(path.relative_to(self.root)) for path in required if not path.is_file()]
        return {
            "status": "PASS" if not missing else "BLOCKED",
            "missing": missing,
            "provider": "root_autonomy",
        }

    def build_cursor_task(self, deployment: Mapping[str, Any]) -> dict[str, Any]:
        module = load_module(
            self.root / "autonomy/adapters/cursor/adapter.py",
            "l9_root_autonomy_cursor_adapter",
        )
        return dict(module.build_cursor_task(deployment))

    def build_claude_task(self, deployment: Mapping[str, Any]) -> dict[str, Any]:
        module = load_module(
            self.root / "autonomy/adapters/claude_code/adapter.py",
            "l9_root_autonomy_claude_adapter",
        )
        return dict(module.build_claude_task(deployment))
