from __future__ import annotations

import json
import os
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


_PEER_BINDINGS_REL = "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
_PEER_BINDINGS_SCHEMA_REL = "environment/agents/schemas/peer-runtime-bindings.schema.json"


def _load_peer_runtime_registry(repository_root: Path) -> dict[str, Any]:
    """Read the peer runtime registry and fail closed when it cannot be trusted."""
    import yaml
    from jsonschema import Draft202012Validator

    registry_path = repository_root / _PEER_BINDINGS_REL
    schema_path = repository_root / _PEER_BINDINGS_SCHEMA_REL
    registry_text = registry_path.read_text(encoding="utf-8")
    schema_text = schema_path.read_text(encoding="utf-8")
    try:
        document = yaml.safe_load(registry_text)
    except yaml.YAMLError as exc:
        raise ValueError("peer runtime registry is malformed") from exc
    if not isinstance(document, dict):
        raise ValueError("peer runtime registry is malformed")
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as exc:
        raise ValueError("peer runtime registry schema is malformed") from exc
    if not isinstance(schema, dict):
        raise ValueError("peer runtime registry schema is malformed")
    if any(Draft202012Validator(schema).iter_errors(document)):
        raise ValueError("peer runtime registry does not satisfy its schema")
    return document


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
            document = _load_peer_runtime_registry(self.repository_root)
            peers = document.get("peers")
            if not isinstance(peers, Mapping):
                raise ValueError("peer runtime registry has no peers")
            peer = peers.get(config.peer_ref)
            if not isinstance(peer, Mapping):
                raise ValueError("peer is not in the runtime registry")
            if peer.get("agent_ref") != config.peer_ref:
                raise ValueError("registered peer identity disagrees with the requested peer")
            autonomy = peer.get("autonomy")
            if not isinstance(autonomy, Mapping) or autonomy.get("required") is not True:
                raise ValueError("peer does not require root autonomy")
            provider_id = autonomy.get("provider_id")
            if provider_id != self.requirements.get("canonical_autonomy_provider"):
                raise ValueError(
                    "peer autonomy provider disagrees with the conformance requirement"
                )
            execution = peer.get("execution")
            bindings = execution.get("bindings") if isinstance(execution, Mapping) else None
            if not isinstance(bindings, list):
                raise ValueError("peer has no execution bindings")
            matched: list[Mapping[str, Any]] = []
            for row in bindings:
                if not isinstance(row, Mapping) or row.get("surface") != config.surface:
                    continue
                if (
                    config.provider_ref is not None
                    and row.get("provider_ref") != config.provider_ref
                ):
                    continue
                if (
                    config.execution_profile_ref is not None
                    and row.get("execution_profile_ref") != config.execution_profile_ref
                ):
                    continue
                matched.append(row)
            if len(matched) != 1:
                raise ValueError("peer surface does not identify exactly one binding")
            chosen = matched[0]
            provider_ref = chosen.get("provider_ref")
            profile_ref = chosen.get("execution_profile_ref")
            message = (
                "Canonical peer binding valid: "
                f"{config.peer_ref}/{config.surface}/{provider_ref}/{profile_ref}/{provider_id}"
            )
        except (OSError, ValueError, TypeError, ImportError) as exc:
            return ConformanceCheck(
                "ADAPTER-002",
                False,
                f"Canonical peer/surface binding invalid: {exc}",
            )
        return ConformanceCheck("ADAPTER-002", True, message)

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
