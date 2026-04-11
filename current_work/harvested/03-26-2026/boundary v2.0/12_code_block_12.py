# path: engine/boundary/memory_mapper.py
# filename: memory_mapper.py
# purpose: Maps execution results and failures into durable memory records
# dependencies/interfaces: Consumes TransportPacket, EngineResult, FailurePayload

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .command_factory import EngineResult, MemoryWriteDirective
from .failure_factory import FailurePayload
from .transport_codec import TransportPacket, sha256_hex, utc_now


class MemoryLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parent_record_ids: tuple[UUID, ...] = ()
    root_packet_id: UUID
    source_packet_id: UUID
    generation: int = Field(ge=0)


class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: UUID = Field(default_factory=uuid4)
    record_class: Literal["audit", "event", "fact", "inference", "checkpoint", "error"]
    record_type: str
    tenant_id: str
    segment: Literal["identity", "world_model", "session_context", "project_history", "governance_meta", "tool_audit"]
    created_at: datetime = Field(default_factory=utc_now)
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    payload: dict[str, Any]
    tags: tuple[str, ...] = ()
    trace_id: str | None = None
    correlation_id: str | None = None
    source_node: str
    source_action: str
    source_packet_id: UUID
    root_packet_id: UUID
    causation_id: UUID | None = None
    lineage: MemoryLineage
    content_hash: str
    schema_version: str = "memory.v1"
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    ttl: datetime | None = None
    processing_status: Literal["pending", "processing", "complete", "failed"] = "pending"

    @field_validator("record_type", "tenant_id", "source_node", "source_action", "content_hash")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("required memory field must not be empty")
        return normalized

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(tag.strip() for tag in value if tag.strip())
        if len(set(normalized)) != len(normalized):
            raise ValueError("tags must not contain duplicates")
        return normalized


class MemoryMapper:
    def __init__(self, *, local_node: str) -> None:
        self.local_node = local_node.strip().lower()

    def from_result(self, request_packet: TransportPacket, result: EngineResult) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        outcome_record = self._make_record(
            request_packet=request_packet,
            record_class="audit",
            record_type="execution_outcome",
            segment="tool_audit",
            payload={
                "status": result.status,
                "client_message": result.client_message,
                "warnings": list(result.warnings),
                "metrics": result.metrics,
            },
            tags=("execution", result.status, request_packet.header.action),
        )
        records.append(outcome_record)

        for event in result.emitted_events:
            records.append(
                self._make_record(
                    request_packet=request_packet,
                    record_class="event",
                    record_type=event.event_type,
                    segment="project_history",
                    payload=event.payload,
                    tags=event.tags,
                    parent_record_ids=(outcome_record.record_id,),
                )
            )

        for write in result.memory_writes:
            records.append(
                self._from_write_directive(
                    request_packet=request_packet,
                    write=write,
                    parent_record_ids=(outcome_record.record_id,),
                )
            )

        for delegation in result.delegations:
            records.append(
                self._make_record(
                    request_packet=request_packet,
                    record_class="audit",
                    record_type="delegation_requested",
                    segment="tool_audit",
                    payload={
                        "target_node": delegation.target_node,
                        "action": delegation.action,
                        "intent": delegation.intent,
                        "permissions": list(delegation.permissions),
                        "priority": delegation.priority,
                        "expires_at": delegation.expires_at.isoformat().replace("+00:00", "Z") if delegation.expires_at else None,
                    },
                    tags=("delegation", delegation.target_node, delegation.action),
                    parent_record_ids=(outcome_record.record_id,),
                )
            )

        return records

    def from_failure(self, request_packet: TransportPacket, failure: FailurePayload) -> list[MemoryRecord]:
        return [
            self._make_record(
                request_packet=request_packet,
                record_class="error",
                record_type="execution_failed",
                segment="tool_audit",
                payload=failure.model_dump(mode="json", exclude_none=True),
                tags=("error", failure.error_code, request_packet.header.action),
            )
        ]

    def from_rejection(self, request_packet: TransportPacket, *, error_code: str, detail: str) -> list[MemoryRecord]:
        return [
            self._make_record(
                request_packet=request_packet,
                record_class="audit",
                record_type="packet_rejected",
                segment="governance_meta",
                payload={"error_code": error_code, "detail": detail},
                tags=("rejected", error_code),
            )
        ]

    def _from_write_directive(
        self,
        *,
        request_packet: TransportPacket,
        write: MemoryWriteDirective,
        parent_record_ids: tuple[UUID, ...],
    ) -> MemoryRecord:
        return self._make_record(
            request_packet=request_packet,
            record_class=write.record_class,
            record_type=write.record_type,
            segment=write.segment,
            payload=write.payload,
            tags=write.tags,
            observed_at=write.observed_at,
            valid_from=write.valid_from,
            valid_to=write.valid_to,
            confidence_score=write.confidence_score,
            importance_score=write.importance_score,
            ttl=write.ttl,
            parent_record_ids=parent_record_ids,
        )

    def _make_record(
        self,
        *,
        request_packet: TransportPacket,
        record_class: Literal["audit", "event", "fact", "inference", "checkpoint", "error"],
        record_type: str,
        segment: Literal["identity", "world_model", "session_context", "project_history", "governance_meta", "tool_audit"],
        payload: dict[str, Any],
        tags: tuple[str, ...] = (),
        observed_at: datetime | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        confidence_score: float | None = None,
        importance_score: float | None = None,
        ttl: datetime | None = None,
        parent_record_ids: tuple[UUID, ...] = (),
    ) -> MemoryRecord:
        base = {
            "record_class": record_class,
            "record_type": record_type,
            "tenant_id": request_packet.tenant.org_id,
            "segment": segment,
            "payload": payload,
            "tags": tags,
            "trace_id": request_packet.header.trace_id,
            "correlation_id": request_packet.header.correlation_id,
            "source_node": self.local_node,
            "source_action": request_packet.header.action,
            "source_packet_id": request_packet.header.packet_id,
            "root_packet_id": request_packet.lineage.root_id,
            "causation_id": request_packet.header.causation_id,
            "parent_record_ids": tuple(str(value) for value in parent_record_ids),
        }
        content_hash = sha256_hex(base)
        return MemoryRecord(
            record_class=record_class,
            record_type=record_type,
            tenant_id=request_packet.tenant.org_id,
            segment=segment,
            observed_at=observed_at,
            valid_from=valid_from,
            valid_to=valid_to,
            payload=payload,
            tags=tags,
            trace_id=request_packet.header.trace_id,
            correlation_id=request_packet.header.correlation_id,
            source_node=self.local_node,
            source_action=request_packet.header.action,
            source_packet_id=request_packet.header.packet_id,
            root_packet_id=request_packet.lineage.root_id,
            causation_id=request_packet.header.causation_id,
            lineage=MemoryLineage(
                parent_record_ids=parent_record_ids,
                root_packet_id=request_packet.lineage.root_id,
                source_packet_id=request_packet.header.packet_id,
                generation=request_packet.lineage.generation,
            ),
            content_hash=content_hash,
            importance_score=importance_score,
            confidence_score=confidence_score,
            ttl=ttl,
            processing_status="pending",
        )


__all__ = [
    "MemoryLineage",
    "MemoryMapper",
    "MemoryRecord",
]
