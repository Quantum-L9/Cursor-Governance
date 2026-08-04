"""Load prior-wave runtime and adapter modules by their real filesystem path.

The runtime and adapters are not installed packages; they bootstrap ``sys.path``
to import sibling modules. This loader makes ``runtime/`` and ``adapters/``
importable by bare module name so their internal imports resolve identically
whether they are run as scripts or loaded by the orchestration layer.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

RUNTIME_MODULES = (
    "packet_validator",
    "harvester",
    "classifier",
    "routing_engine",
    "promotion_gate",
    "learning_closure",
)
ADAPTER_SYMBOLS = {
    "graphiti_memory": (
        "GraphitiMemoryAdapter",
        "FileOutboxTransport",
        "HttpJsonTransport",
        "CommandTransport",
    ),
}
RUNTIME_SYMBOLS = {
    "packet_validator": ("PacketValidator",),
    "harvester": ("SubagentDataHarvester",),
    "classifier": ("GeneratedDataClassifier",),
    "routing_engine": ("RoutingEngine",),
    "promotion_gate": ("PromotionGate",),
    "learning_closure": ("LearningClosureEvaluator",),
}


class PriorWaveModuleError(RuntimeError):
    """Raised when a required prior-wave module or symbol cannot be loaded."""


class PriorWaveModuleLoader:
    """Import runtime/adapter modules from a Cursor-Governance checkout."""

    def __init__(self, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.base = self.repository_root / "environment" / "agents" / "generated-data"
        self.runtime_dir = self.base / "runtime"
        self.adapters_dir = self.base / "adapters"

    def _ensure_on_path(self, directory: Path) -> None:
        text = str(directory)
        if text not in sys.path:
            sys.path.insert(0, text)

    def load_runtime_module(self, name: str) -> ModuleType:
        stem = name[:-3] if name.endswith(".py") else name
        if not (self.runtime_dir / f"{stem}.py").is_file():
            raise PriorWaveModuleError(f"Runtime module is missing: {stem}.py")
        self._ensure_on_path(self.runtime_dir)
        return importlib.import_module(stem)

    def load_adapter_module(self, name: str) -> ModuleType:
        stem = name[:-3] if name.endswith(".py") else name
        if not (self.adapters_dir / f"{stem}.py").is_file():
            raise PriorWaveModuleError(f"Adapter module is missing: {stem}.py")
        self._ensure_on_path(self.adapters_dir)
        return importlib.import_module(stem)

    def validate_required_symbols(self) -> list[str]:
        """Return a list of load/attribute errors; empty when everything loads."""

        errors: list[str] = []
        for name, symbols in RUNTIME_SYMBOLS.items():
            try:
                module = self.load_runtime_module(name)
            except Exception as exc:  # noqa: BLE001 - report, do not abort health
                errors.append(f"runtime/{name}.py: {exc}")
                continue
            errors.extend(
                f"runtime/{name}.py: missing {symbol}"
                for symbol in symbols
                if not hasattr(module, symbol)
            )
        for name, symbols in ADAPTER_SYMBOLS.items():
            try:
                module = self.load_adapter_module(name)
            except Exception as exc:  # noqa: BLE001 - report, do not abort health
                errors.append(f"adapters/{name}.py: {exc}")
                continue
            errors.extend(
                f"adapters/{name}.py: missing {symbol}"
                for symbol in symbols
                if not hasattr(module, symbol)
            )
        return errors
