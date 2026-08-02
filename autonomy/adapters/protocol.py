from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

ADAPTER_PROTOCOL_VERSION = "1.0.0"


class AdapterType(str, Enum):
    CURSOR = "cursor"
    CLAUDE_CODE = "claude-code"


class ConformanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class AdapterConfig:
    adapter_id: str
    adapter_type: AdapterType
    protocol_version: str
    executable: str
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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdapterConfig":
        required_strings = (
            "adapter_id",
            "adapter_type",
            "protocol_version",
            "executable",
            "tool_mediation_mode",
        )
        for field_name in required_strings:
            raw = value.get(field_name)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(
                    f"Adapter field {field_name!r} must be a non-empty string"
                )
        try:
            adapter_type = AdapterType(value["adapter_type"])
        except ValueError as exc:
            raise ValueError(
                f"Unsupported adapter type: {value['adapter_type']!r}"
            ) from exc
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Adapter metadata must be an object")
        return cls(
            adapter_id=value["adapter_id"].strip(),
            adapter_type=adapter_type,
            protocol_version=value["protocol_version"].strip(),
            executable=value["executable"].strip(),
            tool_mediation_mode=value["tool_mediation_mode"].strip(),
            direct_tool_access=bool(value.get("direct_tool_access", True)),
            autonomous_merge=bool(value.get("autonomous_merge", True)),
            supports_background_agents=bool(
                value.get("supports_background_agents", False)
            ),
            supports_agent_identity=bool(
                value.get("supports_agent_identity", False)
            ),
            supports_lease_propagation=bool(
                value.get("supports_lease_propagation", False)
            ),
            supports_heartbeat=bool(value.get("supports_heartbeat", False)),
            supports_typed_artifacts=bool(
                value.get("supports_typed_artifacts", False)
            ),
            supports_independent_review=bool(
                value.get("supports_independent_review", False)
            ),
            supports_human_gate=bool(value.get("supports_human_gate", False)),
            metadata=dict(metadata),
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
    protocol_version: str
    status: ConformanceStatus
    checks: tuple[ConformanceCheck, ...]

    @property
    def blocking_failures(self) -> tuple[ConformanceCheck, ...]:
        return tuple(
            check for check in self.checks if check.blocking and not check.passed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
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
