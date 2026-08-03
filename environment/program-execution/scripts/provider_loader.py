from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import yaml
from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


def subsystem_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    return subsystem_root().parents[1]


def load_registry() -> dict[str, Any]:
    path = subsystem_root() / "registry/EXECUTION_ADAPTER_REGISTRY.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("execution adapter registry must be an object")
    return value


def registry_entry(adapter_id: str) -> dict[str, Any]:
    entries = load_registry().get("adapters") or []
    matches = [item for item in entries if item.get("adapter_id") == adapter_id]
    if len(matches) != 1:
        raise ValueError(f"adapter registry entry not unique: {adapter_id}")
    return dict(matches[0])


def load_provider_class(adapter_id: str) -> type[BaseExecutionAdapter]:
    entry = registry_entry(adapter_id)
    provider_path = subsystem_root() / str(entry["provider_module"])
    module = load_module(
        provider_path,
        "pes_provider_" + adapter_id.replace("-", "_"),
    )
    candidates = []
    for value in vars(module).values():
        if not inspect.isclass(value):
            continue
        if value is BaseExecutionAdapter:
            continue
        if issubclass(value, BaseExecutionAdapter):
            candidates.append(value)
    unique = list(dict.fromkeys(candidates))
    if len(unique) != 1:
        raise ValueError(f"provider module must expose one adapter class: {provider_path}")
    return unique[0]


def instantiate(adapter_id: str, runtime_root: str | Path) -> BaseExecutionAdapter:
    provider = load_provider_class(adapter_id)
    parameters = inspect.signature(provider.__init__).parameters
    if "repository_root" in parameters:
        return provider(runtime_root, repository_root())
    return provider(runtime_root)
