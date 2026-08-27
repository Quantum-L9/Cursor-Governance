from __future__ import annotations

from pathlib import Path
from typing import Any


class AutonomyControlPlaneBridge:
    """Provider-neutral probe of the canonical root autonomy control plane.

    Surface/provider rendering belongs to Peer Execution Core and its thin
    adapters. This bridge only answers whether the shared authorization plane
    exists and is structurally available.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()

    def probe(self) -> dict[str, Any]:
        required = [
            self.root / "autonomy/runtime/engine.py",
            self.root / "autonomy/adapters/protocol.py",
            self.root / "autonomy/adapters/orchestrator.py",
        ]
        missing = [str(path.relative_to(self.root)) for path in required if not path.is_file()]
        return {
            "status": "PASS" if not missing else "BLOCKED",
            "missing": missing,
            "provider": "root_autonomy",
        }
