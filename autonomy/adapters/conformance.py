from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
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


_PEER_BINDINGS_REL = "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
_PEER_BINDINGS_SCHEMA_REL = "environment/agents/schemas/peer-runtime-bindings.schema.json"
_ROOT_AUTONOMY_PROVIDER_ID = "root-autonomy-control-plane"


def _require_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class PeerBinding:
    agent_ref: str
    surface: str
    provider_ref: str
    execution_profile_ref: str
    autonomy_provider_ref: str


def _load_peer_bindings(repository_root: Path) -> dict[str, Any]:
    import yaml
    from jsonschema import Draft202012Validator

    bindings_path = repository_root / _PEER_BINDINGS_REL
    schema_path = repository_root / _PEER_BINDINGS_SCHEMA_REL
    value = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {bindings_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError(f"peer runtime bindings schema must be an object: {schema_path}")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        rendered = [
            f"{'.'.join(str(part) for part in item.path) or '<root>'}: {item.message}"
            for item in errors
        ]
        raise ValueError(f"peer runtime bindings schema errors: {rendered}")
    return value


def resolve_peer_binding(
    repository_root: Path,
    agent_ref: str,
    surface: str,
    provider_ref: str | None = None,
    execution_profile_ref: str | None = None,
) -> PeerBinding:
    """Resolve one canonical peer execution/autonomy tuple or fail closed.

    The tuple is declared in environment/agents/PEER_RUNTIME_BINDINGS.yaml.
    Root autonomy resolves it itself rather than loading an external execution
    subsystem: a caller may omit provider/profile only when the remaining keys
    resolve uniquely.
    """
    agent_ref = _require_string("agent_ref", agent_ref)
    surface = _require_string("surface", surface)
    if provider_ref is not None:
        provider_ref = _require_string("provider_ref", provider_ref)
    if execution_profile_ref is not None:
        execution_profile_ref = _require_string("execution_profile_ref", execution_profile_ref)

    doc = _load_peer_bindings(repository_root)
    peer = (doc.get("peers") or {}).get(agent_ref)
    if not isinstance(peer, dict):
        raise ValueError(f"unknown peer agent_ref: {agent_ref}")
    declared_agent = peer.get("agent_ref")
    if declared_agent != agent_ref:
        raise ValueError(
            f"peer key and agent_ref differ: key={agent_ref} declared={declared_agent!r}"
        )
    autonomy = peer.get("autonomy")
    if not isinstance(autonomy, dict) or autonomy.get("required") is not True:
        raise ValueError(f"peer root autonomy binding missing or not required: {agent_ref}")
    autonomy_provider = _require_string("autonomy.provider_id", autonomy.get("provider_id"))
    if autonomy_provider != _ROOT_AUTONOMY_PROVIDER_ID:
        raise ValueError(
            f"peer root autonomy provider mismatch: {agent_ref} -> {autonomy_provider}"
        )

    candidates = [
        dict(binding)
        for binding in (peer.get("execution") or {}).get("bindings") or []
        if binding.get("surface") == surface
        and (provider_ref is None or binding.get("provider_ref") == provider_ref)
        and (
            execution_profile_ref is None
            or binding.get("execution_profile_ref") == execution_profile_ref
        )
    ]
    if len(candidates) != 1:
        refs = sorted(
            f"{item.get('provider_ref')}:{item.get('execution_profile_ref')}" for item in candidates
        )
        raise ValueError(
            "peer binding must resolve uniquely: "
            f"agent_ref={agent_ref} surface={surface} provider_ref={provider_ref!r} "
            f"execution_profile_ref={execution_profile_ref!r} candidates={refs}"
        )
    binding = candidates[0]
    return PeerBinding(
        agent_ref=agent_ref,
        surface=surface,
        provider_ref=_require_string("provider_ref", binding.get("provider_ref")),
        execution_profile_ref=_require_string(
            "execution_profile_ref", binding.get("execution_profile_ref")
        ),
        autonomy_provider_ref=autonomy_provider,
    )


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
            binding = resolve_peer_binding(
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
