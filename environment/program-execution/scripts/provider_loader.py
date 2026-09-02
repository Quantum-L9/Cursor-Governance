from __future__ import annotations

import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from peer_execution.driver_execution import DriverExecutionAdapter
from peer_execution.execution import PeerExecutionAdapter
from peer_execution.imports import load_module
from peer_execution.profiles import resolve_profile_for_provider
from peer_execution.schema_registry import SchemaRegistry


def subsystem_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    return subsystem_root().parents[1]


def _required_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _subsystem_path(value: object, *, label: str) -> Path:
    relative = Path(_required_string(label, value))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must stay inside Program Execution: {relative}")
    root = subsystem_root().resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"{label} escapes Program Execution: {relative}")
    if not target.is_file():
        raise ValueError(f"{label} does not exist: {relative}")
    return target


def load_registry() -> dict[str, Any]:
    path = subsystem_root() / "registry/EXECUTION_ADAPTER_REGISTRY.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("execution adapter registry must be an object")
    if value.get("schema") != "program-execution-adapter.registry.v1":
        raise ValueError("unsupported execution adapter registry schema")
    entries = value.get("adapters")
    if not isinstance(entries, list) or not entries:
        raise ValueError("execution adapter registry requires adapters")
    adapter_ids: list[str] = []
    priorities: list[int] = []
    for item in entries:
        if not isinstance(item, Mapping):
            raise ValueError("execution adapter registry entries must be objects")
        adapter_ids.append(_required_string("adapter_id", item.get("adapter_id")))
        _subsystem_path(item.get("descriptor"), label="adapter descriptor")
        _subsystem_path(item.get("provider_module"), label="provider module")
        priority = item.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
            raise ValueError("adapter priority must be a positive integer")
        priorities.append(priority)
    if len(set(adapter_ids)) != len(adapter_ids):
        raise ValueError("execution adapter registry contains duplicate adapter_id values")
    if len(set(priorities)) != len(priorities):
        raise ValueError("execution adapter registry contains duplicate priorities")
    return value


def registry_entry(adapter_id: str) -> dict[str, Any]:
    adapter_id = _required_string("adapter_id", adapter_id)
    entries = load_registry()["adapters"]
    matches = [item for item in entries if item.get("adapter_id") == adapter_id]
    if len(matches) != 1:
        raise ValueError(f"adapter registry entry not unique: {adapter_id}")
    return dict(matches[0])


def descriptor_for(adapter_id: str) -> dict[str, Any]:
    entry = registry_entry(adapter_id)
    path = _subsystem_path(entry.get("descriptor"), label="adapter descriptor")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"adapter descriptor must be an object: {path}")
    errors = SchemaRegistry(subsystem_root()).validate_adapter_spec(value)
    if errors:
        raise ValueError(f"adapter descriptor schema errors: {errors}")
    if value.get("adapter_id") != adapter_id:
        raise ValueError(
            f"adapter descriptor identity mismatch: registry={adapter_id} "
            f"descriptor={value.get('adapter_id')!r}"
        )
    if value.get("adapter_kind") != entry.get("adapter_kind"):
        raise ValueError(f"adapter kind mismatch for {adapter_id}")
    return value


def _instantiate_class(provider: type, runtime_root: str | Path):
    parameters = inspect.signature(provider.__init__).parameters
    kwargs: dict[str, object] = {}
    if "runtime_root" in parameters:
        kwargs["runtime_root"] = runtime_root
    if "repository_root" in parameters:
        kwargs["repository_root"] = repository_root()
    if kwargs:
        return provider(**kwargs)
    return provider()


def _load_module(adapter_id: str):
    entry = registry_entry(adapter_id)
    provider_path = _subsystem_path(entry.get("provider_module"), label="provider module")
    return load_module(
        provider_path,
        "pes_provider_" + adapter_id.replace("-", "_"),
    )


def _load_thin_component(
    adapter_id: str,
    runtime_root: str | Path,
    module: object | None = None,
):
    loaded = module if module is not None else _load_module(adapter_id)
    provider_class = getattr(loaded, "PROVIDER_CLASS", None)
    if not inspect.isclass(provider_class):
        raise ValueError(f"thin execution module must expose PROVIDER_CLASS: {adapter_id}")
    provider = _instantiate_class(provider_class, runtime_root)
    if getattr(provider, "provider_id", None) != adapter_id:
        raise ValueError(f"thin execution component identity mismatch: {adapter_id}")
    for method in ("probe", "invoke", "poll", "cancel"):
        if not callable(getattr(provider, method, None)):
            raise ValueError(
                f"thin execution component missing required hook {method}: {adapter_id}"
            )
    return provider


def default_execution_profile_ref(adapter_id: str, entry: Mapping[str, Any]) -> str:
    """The profile a peer adapter falls back to when nothing names one.

    Precedence is explicit ref, then the provider's unique peer binding, then
    this. It used to be inferred in code from the descriptor (verifier ->
    reviewer-default, no local_write -> worker-read-only). An adapter's
    permission ceiling is registry data: EXECUTION_ADAPTER_REGISTRY.yaml names
    it per adapter, and validate_execution_adapters.py checks it exists and
    does not exceed the descriptor's capabilities.
    """
    ref = entry.get("default_execution_profile_ref")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            f"adapter {adapter_id} declares no default_execution_profile_ref in "
            "EXECUTION_ADAPTER_REGISTRY.yaml; a peer adapter needs one or an explicit profile"
        )
    return ref


def instantiate(
    adapter_id: str,
    runtime_root: str | Path,
    *,
    execution_profile_ref: str | None = None,
    binding_context: Mapping[str, Any] | None = None,
):
    entry = registry_entry(adapter_id)
    if entry.get("status") == "non_routable":
        raise ValueError(f"adapter is explicitly non-routable: {adapter_id}")
    descriptor = descriptor_for(adapter_id)
    identity = descriptor.get("identity") or {}
    module = _load_module(adapter_id)
    component = _load_thin_component(adapter_id, runtime_root, module)
    if identity.get("binding") == "peer_runtime_binding":
        profile = resolve_profile_for_provider(
            subsystem_root(),
            repository_root(),
            adapter_id,
            execution_profile_ref,
            fallback_profile_ref=default_execution_profile_ref(adapter_id, entry),
        )
        return PeerExecutionAdapter(
            runtime_root,
            descriptor=descriptor,
            provider=component,
            execution_profile=profile,
            binding_context=binding_context,
        )
    if descriptor.get("adapter_kind") in {
        "verifier",
        "remote_action",
        "deployment_record",
        "worker_host",
    }:
        return DriverExecutionAdapter(
            runtime_root,
            descriptor=descriptor,
            driver=component,
        )
    raise ValueError(f"unsupported routable adapter kind: {descriptor.get('adapter_kind')}")
