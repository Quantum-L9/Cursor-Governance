# path: engine/boundary/command_factory.py
# filename: command_factory.py
# purpose: Maps transport packets into typed execution commands and result contracts
# dependencies/interfaces: Consumes TransportPacket; feeds application services

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .transport_codec import TransportPacket

RequestClass = Literal["interactive", "batch", "replay", "repair", "admin"]
OutcomeStatus = Literal[
    "accepted",
    "completed",
    "partial",
    "rejected",
    "failed_retryable",
    "failed_terminal",
    "compensated",
    "deferred",
]


class ExecutionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: UUID
    trace_id: str | None = None
    correlation_id: str | None = None
    causation_id: UUID | None = None
    tenant_id: str
    actor: str
    originator: str
    user_id: str | None = None
    source_node: str
    destination_node: str
    action: str
    domain_id: str
    request_class: RequestClass
    deadline_at: datetime | None = None
    idempotency_key: str | None = None
    classification: str
    compliance_tags: tuple[str, ...] = ()
    replay_mode: bool = False

    @field_validator(
        "tenant_id",
        "actor",
        "originator",
        "source_node",
        "destination_node",
        "action",
        "domain_id",
        "classification",
    )
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required execution context field must not be empty")
        return normalized

    @field_validator("trace_id", "correlation_id", "user_id", "idempotency_key")
    @classmethod
    def _validate_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("optional execution context field must not be empty")
        return normalized


class MemoryWriteDirective(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_class: Literal["audit", "event", "fact", "inference", "checkpoint", "error"]
    record_type: str
    segment: Literal["identity", "world_model", "session_context", "project_history", "governance_meta", "tool_audit"]
    payload: dict[str, Any]
    tags: tuple[str, ...] = ()
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    ttl: datetime | None = None

    @field_validator("record_type")
    @classmethod
    def _validate_record_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("record_type must not be empty")
        return normalized

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(tag.strip() for tag in value if tag.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("tags must not contain duplicates")
        return normalized


class EmittedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: str
    payload: dict[str, Any]
    tags: tuple[str, ...] = ()

    @field_validator("event_type")
    @classmethod
    def _validate_event_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("event_type must not be empty")
        return normalized


class DelegationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_node: str
    action: str
    payload: dict[str, Any]
    permissions: tuple[str, ...]
    intent: str
    priority: int = Field(default=5, ge=1, le=10)
    expires_at: datetime | None = None

    @field_validator("target_node", "action", "intent")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("delegation field must not be empty")
        return normalized

    @field_validator("permissions")
    @classmethod
    def _validate_permissions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(v.strip() for v in value if v.strip())
        if not normalized:
            raise ValueError("permissions must not be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("permissions must not contain duplicates")
        return normalized


class EngineResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: OutcomeStatus
    data: dict[str, Any]
    emitted_events: tuple[EmittedEvent, ...] = ()
    memory_writes: tuple[MemoryWriteDirective, ...] = ()
    delegations: tuple[DelegationRequest, ...] = ()
    metrics: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    client_message: str | None = None

    @field_validator("warnings")
    @classmethod
    def _validate_warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(v.strip() for v in value if v.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("warnings must not contain duplicates")
        return normalized


class MatchCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    context: ExecutionContext
    payload: dict[str, Any]


class SyncCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    context: ExecutionContext
    payload: dict[str, Any]


class AdminCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    context: ExecutionContext
    payload: dict[str, Any]


class ReplayCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    context: ExecutionContext
    payload: dict[str, Any]


CommandT = TypeVar("CommandT", MatchCommand, SyncCommand, AdminCommand, ReplayCommand)


class CommandFactory:
    def __init__(self) -> None:
        self._registry: dict[str, type[BaseModel]] = {}

    def register(self, action: str, command_model: type[BaseModel]) -> None:
        normalized_action = action.strip().lower()
        if not normalized_action:
            raise ValueError("action must not be empty")
        self._registry[normalized_action] = command_model

    def build(self, packet: TransportPacket) -> BaseModel:
        context = self._build_context(packet)
        model = self._resolve_model(packet.header.action, packet.header.packet_type)
        return model(context=context, payload=packet.payload)

    def _resolve_model(self, action: str, packet_type: str) -> type[BaseModel]:
        normalized_action = action.strip().lower()
        if normalized_action in self._registry:
            return self._registry[normalized_action]
        if packet_type == "replay_request" or normalized_action.startswith("replay"):
            return ReplayCommand
        if normalized_action in {"sync", "bulk_sync", "upsert", "delete"}:
            return SyncCommand
        if normalized_action in {"admin", "reload", "health", "gds", "introspect"}:
            return AdminCommand
        return MatchCommand

    def _build_context(self, packet: TransportPacket) -> ExecutionContext:
        action = packet.header.action.strip().lower()
        request_class = self._resolve_request_class(packet.header.packet_type, action)
        domain_id = self._resolve_domain_id(packet)
        return ExecutionContext(
            request_id=packet.header.packet_id,
            trace_id=packet.header.trace_id,
            correlation_id=packet.header.correlation_id,
            causation_id=packet.header.causation_id,
            tenant_id=packet.tenant.org_id,
            actor=packet.tenant.actor,
            originator=packet.tenant.originator,
            user_id=packet.tenant.user_id,
            source_node=packet.address.source_node,
            destination_node=packet.address.destination_node,
            action=action,
            domain_id=domain_id,
            request_class=request_class,
            deadline_at=packet.header.expires_at,
            idempotency_key=packet.header.idempotency_key,
            classification=packet.security.classification,
            compliance_tags=packet.governance.compliance_tags,
            replay_mode=packet.header.replay_mode,
        )

    @staticmethod
    def _resolve_request_class(packet_type: str, action: str) -> RequestClass:
        if packet_type == "replay_request" or action.startswith("replay"):
            return "replay"
        if action in {"admin", "reload", "health", "gds", "introspect"}:
            return "admin"
        if action in {"sync", "bulk_sync", "upsert", "delete"}:
            return "batch"
        return "interactive"

    @staticmethod
    def _resolve_domain_id(packet: TransportPacket) -> str:
        payload_domain = packet.payload.get("domain")
        if isinstance(payload_domain, str) and payload_domain.strip():
            return payload_domain.strip().lower()
        return packet.governance.intent.strip().lower()


DEFAULT_COMMAND_FACTORY = CommandFactory()

__all__ = [
    "AdminCommand",
    "CommandFactory",
    "DEFAULT_COMMAND_FACTORY",
    "DelegationRequest",
    "EmittedEvent",
    "EngineResult",
    "ExecutionContext",
    "MatchCommand",
    "MemoryWriteDirective",
    "ReplayCommand",
    "SyncCommand",
]
