from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

ADAPTER_PROTOCOL_VERSION = "1.0.0"
IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


class ConformanceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


def _identifier(value: Mapping[str, Any], field_name: str) -> str:
    raw = value.get(field_name)
    if not isinstance(raw, str) or not IDENTIFIER_RE.fullmatch(raw.strip()):
        raise ValueError(
            f"Adapter field {field_name!r} must be a non-empty kebab-case identifier"
        )
    return raw.strip()


def _optional_identifier(value: Mapping[str, Any], field_name: str) -> str | None:
    raw = value.get(field_name)
    if raw is None:
        return None
    return _identifier(value, field_name)


def _required_bool(value: Mapping[str, Any], field_name: str) -> bool:
    if field_name not in value:
        raise ValueError(f"Adapter field {field_name!r} is required and must be boolean")
    raw = value[field_name]
    if type(raw) is not bool:
        raise ValueError(f"Adapter field {field_name!r} must be boolean")
    return raw


@dataclass(frozen=True)
class AdapterConfig:
    adapter_id: str
    adapter_type: str
    peer_ref: str
    surface: str
    protocol_version: str
    tool_mediation_mode: str
    direct_tool_access: bool
    autonomous_merge: bool
    supports_background_agents: bool
    supports_agent_identity: bool
    supports_lease_propagation: bool
    supports_heartbeat: bool
    supports_typed_artifacts: bool
    supports_independent_review: bool
    supports_human_gate: bool
    metadata: Mapping[str, Any]
    executable: str | None = None
    provider_ref: str | None = None
    execution_profile_ref: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AdapterConfig:
        adapter_id = _identifier(value, "adapter_id")
        adapter_type = _identifier(value, "adapter_type")
        peer_ref = _identifier(value, "peer_ref")
        surface = _identifier(value, "surface")
        provider_ref = _optional_identifier(value, "provider_ref")
        execution_profile_ref = _optional_identifier(value, "execution_profile_ref")
        for field_name in ("protocol_version", "tool_mediation_mode"):
            raw = value.get(field_name)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"Adapter field {field_name!r} must be a non-empty string")
        executable = value.get("executable")
        if executable is not None and (not isinstance(executable, str) or not executable.strip()):
            raise ValueError("Adapter field 'executable' must be a non-empty string when present")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Adapter metadata must be an object")
        return cls(
            adapter_id=adapter_id,
            adapter_type=adapter_type,
            peer_ref=peer_ref,
            surface=surface,
            provider_ref=provider_ref,
            execution_profile_ref=execution_profile_ref,
            protocol_version=str(value["protocol_version"]).strip(),
            executable=executable.strip() if isinstance(executable, str) else None,
            tool_mediation_mode=str(value["tool_mediation_mode"]).strip(),
            direct_tool_access=_required_bool(value, "direct_tool_access"),
            autonomous_merge=_required_bool(value, "autonomous_merge"),
            supports_background_agents=_required_bool(value, "supports_background_agents"),
            supports_agent_identity=_required_bool(value, "supports_agent_identity"),
            supports_lease_propagation=_required_bool(value, "supports_lease_propagation"),
            supports_heartbeat=_required_bool(value, "supports_heartbeat"),
            supports_typed_artifacts=_required_bool(value, "supports_typed_artifacts"),
            supports_independent_review=_required_bool(value, "supports_independent_review"),
            supports_human_gate=_required_bool(value, "supports_human_gate"),
            metadata=dict(metadata),
        )

    def surface_capabilities(self) -> frozenset[str]:
        return frozenset(
            name
            for name in ("supports_background_agents", "supports_independent_review")
            if getattr(self, name)
        )


@dataclass(frozen=True)
class ConformanceCheck:
    check_id: str
    passed: bool
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ConformanceReport:
    adapter_id: str
    adapter_type: str
    peer_ref: str
    surface: str
    protocol_version: str
    status: ConformanceStatus
    checks: tuple[ConformanceCheck, ...]

    @property
    def blocking_failures(self) -> tuple[ConformanceCheck, ...]:
        return tuple(check for check in self.checks if check.blocking and not check.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "peer_ref": self.peer_ref,
            "surface": self.surface,
            "protocol_version": self.protocol_version,
            "status": self.status.value,
            "checks": [
                {
                    "check_id": check.check_id,
                    "passed": check.passed,
                    "message": check.message,
                    "blocking": check.blocking,
                }
                for check in self.checks
            ],
        }
