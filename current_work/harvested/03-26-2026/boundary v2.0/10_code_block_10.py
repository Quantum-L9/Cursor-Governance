# path: engine/boundary/failure_factory.py
# filename: failure_factory.py
# purpose: Structured boundary failures and failure payload generation
# dependencies/interfaces: Consumes TransportPacket context for sanitized failure objects

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .transport_codec import TransportPacket


class L9BoundaryError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        client_message: str,
        detail: str,
        retryable: bool = False,
        failed_stage: str = "runtime",
        http_status: int = 500,
    ) -> None:
        super().__init__(detail)
        self.error_code = error_code
        self.client_message = client_message
        self.detail = detail
        self.retryable = retryable
        self.failed_stage = failed_stage
        self.http_status = http_status


class FailurePayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error_id: UUID = Field(default_factory=uuid4)
    error_code: str
    client_message: str
    retryable: bool
    failed_stage: str
    detail_ref: UUID | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("error_code", "client_message", "failed_stage")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("failure field must not be empty")
        return normalized


class FailureContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: str
    tenant_id: str
    trace_id: str | None = None
    request_id: UUID | None = None
    source_node: str | None = None
    destination_node: str | None = None


class FailureFactory:
    def from_exception(self, exc: Exception, *, context: FailureContext) -> FailurePayload:
        if isinstance(exc, L9BoundaryError):
            return FailurePayload(
                error_code=exc.error_code,
                client_message=exc.client_message,
                retryable=exc.retryable,
                failed_stage=exc.failed_stage,
                diagnostics={
                    "detail": exc.detail,
                    "tenant_id": context.tenant_id,
                    "action": context.action,
                    "trace_id": context.trace_id,
                    "request_id": str(context.request_id) if context.request_id else None,
                    "source_node": context.source_node,
                    "destination_node": context.destination_node,
                },
            )
        return FailurePayload(
            error_code="internal_error",
            client_message="Request failed",
            retryable=False,
            failed_stage="runtime",
            diagnostics={
                "exception_type": exc.__class__.__name__,
                "detail": str(exc),
                "tenant_id": context.tenant_id,
                "action": context.action,
                "trace_id": context.trace_id,
                "request_id": str(context.request_id) if context.request_id else None,
                "source_node": context.source_node,
                "destination_node": context.destination_node,
            },
        )

    def context_from_packet(self, packet: TransportPacket) -> FailureContext:
        return FailureContext(
            action=packet.header.action,
            tenant_id=packet.tenant.org_id,
            trace_id=packet.header.trace_id,
            request_id=packet.header.packet_id,
            source_node=packet.address.source_node,
            destination_node=packet.address.destination_node,
        )


DEFAULT_FAILURE_FACTORY = FailureFactory()

__all__ = [
    "DEFAULT_FAILURE_FACTORY",
    "FailureContext",
    "FailureFactory",
    "FailurePayload",
    "L9BoundaryError",
]
