from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from autonomy.adapters.protocol import (
    ADAPTER_PROTOCOL_VERSION,
    AdapterConfig,
    ConformanceCheck,
    ConformanceReport,
    ConformanceStatus,
)
from autonomy.errors import CompatibilityError
from autonomy.versioning import Version

_CHECK_IDS = {
    "tool_mediation_mode": "ADAPTER-003",
    "direct_tool_access": "ADAPTER-004",
    "autonomous_merge": "ADAPTER-005",
    "supports_background_agents": "ADAPTER-006",
    "supports_agent_identity": "ADAPTER-007",
    "supports_lease_propagation": "ADAPTER-008",
    "supports_heartbeat": "ADAPTER-009",
    "supports_typed_artifacts": "ADAPTER-010",
    "supports_independent_review": "ADAPTER-011",
    "supports_human_gate": "ADAPTER-012",
}


_BINDING_RESOLVER_MODULE = "l9_peer_binding_resolver"


def _load_binding_resolver(repository_root: Path):
    """Bind the one canonical peer-binding resolver owned by Peer Execution.

    Root autonomy cannot import it as a package (the subsystem path is not a
    Python identifier), so it is loaded by path with the same semantics as
    peer_execution.imports.load_module: registered in sys.modules before
    execution (dataclass construction reads it back) and unregistered if the
    module fails to execute.
    """
    path = repository_root / "environment/program-execution/peer_execution/bindings.py"
    cached = sys.modules.get(_BINDING_RESOLVER_MODULE)
    if cached is not None and getattr(cached, "__file__", None) == str(path):
        return cached.resolve_peer_binding
    spec = importlib.util.spec_from_file_location(_BINDING_RESOLVER_MODULE, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load canonical peer binding resolver: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_BINDING_RESOLVER_MODULE] = module
    try:
        spec.loader.exec_module(module)
    # BaseException, not Exception: a partially executed module must be
    # unregistered even when the load is interrupted, or the next import
    # silently gets the broken half. The block re-raises.
    except BaseException:
        sys.modules.pop(_BINDING_RESOLVER_MODULE, None)
        raise
    return module.resolve_peer_binding


class AdapterConformance:
    def __init__(
        self,
        requirements: Mapping[str, Any],
        repository_root: str | Path = ".",
    ) -> None:
        self.requirements = dict(requirements)
        self.repository_root = Path(repository_root).resolve()

    def run(self, config: AdapterConfig) -> ConformanceReport:
        checks = (
            self._protocol_version(config),
            self._peer_surface_binding(config),
            *self._policy_checks(config),
            self._runtime_installed(),
            self._gateway_installed(),
            self._policy_installed(),
            self._database_parent_writable(config),
        )
        status = (
            ConformanceStatus.FAIL
            if any(check.blocking and not check.passed for check in checks)
            else ConformanceStatus.PASS
        )
        return ConformanceReport(
            adapter_id=config.adapter_id,
            adapter_type=config.adapter_type,
            peer_ref=config.peer_ref,
            surface=config.surface,
            protocol_version=config.protocol_version,
            status=status,
            checks=checks,
        )

    def _protocol_version(self, config: AdapterConfig) -> ConformanceCheck:
        configured = str(self.requirements.get("protocol_version") or ADAPTER_PROTOCOL_VERSION)
        try:
            actual = Version.parse(config.protocol_version)
            required = Version.parse(configured)
            passed = actual.major == required.major and actual >= required
        except CompatibilityError:
            passed = False
        return ConformanceCheck(
            "ADAPTER-001",
            passed,
            "Adapter protocol is compatible"
            if passed
            else f"Adapter protocol must be compatible with {configured}",
        )

    def _peer_surface_binding(self, config: AdapterConfig) -> ConformanceCheck:
        try:
            resolve = _load_binding_resolver(self.repository_root)
            binding = resolve(
                self.repository_root,
                config.peer_ref,
                config.surface,
                config.provider_ref,
                config.execution_profile_ref,
            )
            expected_autonomy = self.requirements.get("canonical_autonomy_provider")
            if expected_autonomy and binding.autonomy_provider_ref != expected_autonomy:
                raise ValueError(
                    f"autonomy provider {binding.autonomy_provider_ref!r} != {expected_autonomy!r}"
                )
        except (OSError, ValueError, TypeError, ImportError) as exc:
            return ConformanceCheck(
                "ADAPTER-002",
                False,
                f"Canonical peer/surface binding invalid: {exc}",
            )
        return ConformanceCheck(
            "ADAPTER-002",
            True,
            "Canonical peer binding valid: "
            f"{binding.agent_ref}/{binding.surface}/{binding.provider_ref}/"
            f"{binding.execution_profile_ref}/{binding.autonomy_provider_ref}",
        )

    def _policy_checks(self, config: AdapterConfig) -> tuple[ConformanceCheck, ...]:
        checks: list[ConformanceCheck] = []
        mandatory = self.requirements.get("mandatory") or {}
        if not isinstance(mandatory, Mapping):
            raise ValueError("adapter requirements mandatory policy must be an object")
        for field_name, expected in mandatory.items():
            if field_name not in _CHECK_IDS:
                raise ValueError(
                    f"adapter requirements contains unknown mandatory field: {field_name}"
                )
            actual = getattr(config, field_name)
            passed = actual == expected and type(actual) is type(expected)
            checks.append(
                ConformanceCheck(
                    _CHECK_IDS[field_name],
                    passed,
                    f"Mandatory policy {field_name}={expected!r}; observed {actual!r}",
                    blocking=True,
                )
            )
        optional = self.requirements.get("optional_capabilities") or {}
        if not isinstance(optional, Mapping):
            raise ValueError("adapter requirements optional_capabilities must be an object")
        for field_name, capability_name in optional.items():
            if field_name not in _CHECK_IDS:
                raise ValueError(
                    f"adapter requirements contains unknown optional field: {field_name}"
                )
            actual = getattr(config, field_name)
            checks.append(
                ConformanceCheck(
                    _CHECK_IDS[field_name],
                    bool(actual),
                    f"Optional surface capability {capability_name}: "
                    f"{'available' if actual else 'unavailable'}",
                    blocking=False,
                )
            )
        return tuple(sorted(checks, key=lambda item: item.check_id))

    def required_surface_capability_fields(self) -> dict[str, str]:
        optional = self.requirements.get("optional_capabilities") or {}
        if not isinstance(optional, Mapping):
            raise ValueError("adapter requirements optional_capabilities must be an object")
        return {str(capability): str(field) for field, capability in optional.items()}

    def assert_surface_capabilities(
        self,
        config: AdapterConfig,
        required_capabilities: list[str] | tuple[str, ...],
    ) -> None:
        capability_fields = self.required_surface_capability_fields()
        unknown = sorted(set(required_capabilities) - set(capability_fields))
        if unknown:
            raise ValueError(f"unknown required surface capabilities: {unknown}")
        missing = sorted(
            capability
            for capability in set(required_capabilities)
            if getattr(config, capability_fields[capability]) is not True
        )
        if missing:
            raise ValueError(f"required surface capabilities unavailable: {missing}")

    def _runtime_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/runtime/engine.py"
        return ConformanceCheck("ADAPTER-013", path.is_file(), f"Runtime present: {path}")

    def _gateway_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/runtime/capability_gateway.py"
        return ConformanceCheck(
            "ADAPTER-014", path.is_file(), f"Capability gateway present: {path}"
        )

    def _policy_installed(self) -> ConformanceCheck:
        path = self.repository_root / "autonomy/policies/role-capabilities.json"
        return ConformanceCheck("ADAPTER-015", path.is_file(), f"Role policy present: {path}")

    def _database_parent_writable(self, config: AdapterConfig) -> ConformanceCheck:
        database_path = Path(
            config.metadata.get(
                "database_path",
                self.repository_root / ".l9/autonomy/runtime.sqlite3",
            )
        )
        if not database_path.is_absolute():
            database_path = self.repository_root / database_path
        parent = database_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        passed = os.access(parent, os.W_OK)
        return ConformanceCheck(
            "ADAPTER-016",
            passed,
            f"Runtime database directory is writable: {parent}",
        )
