# path: engine/boundary/response_factory.py
# filename: response_factory.py
# purpose: Derives response and failure packets plus client-facing egress envelope
# dependencies/interfaces: Consumes EngineResult and FailurePayload; produces TransportPacket

from __future__ import annotations

from typing import Any

from .command_factory import EngineResult
from .failure_factory import FailurePayload
from .transport_codec import TransportPacket, append_hop, derive_packet


class ResponseFactory:
    def __init__(self, *, local_node: str, signing_secret: str | None = None, signing_key_id: str | None = None) -> None:
        self.local_node = local_node.strip().lower()
        self.signing_secret = signing_secret
        self.signing_key_id = signing_key_id

    def build_response_packet(self, request_packet: TransportPacket, result: EngineResult) -> TransportPacket:
        packet_type = "response"
        if result.status in {"failed_retryable", "failed_terminal", "rejected"}:
            packet_type = "failure"
        payload = {
            "status": result.status,
            "data": result.data,
            "warnings": list(result.warnings),
            "client_message": result.client_message,
            "metrics": result.metrics,
        }
        response_packet = derive_packet(
            request_packet,
            packet_type=packet_type,
            action=request_packet.header.action,
            payload=payload,
            source_node=self.local_node,
            destination_node=request_packet.address.reply_to or request_packet.address.source_node,
            reply_to=self.local_node,
            intent=request_packet.governance.intent,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )
        return append_hop(
            response_packet,
            node=self.local_node,
            action=request_packet.header.action,
            status="completed" if result.status in {"accepted", "completed", "partial", "compensated", "deferred"} else "failed",
            detail=result.client_message or result.status,
        )

    def build_failure_packet(self, request_packet: TransportPacket, failure: FailurePayload) -> TransportPacket:
        failure_packet = derive_packet(
            request_packet,
            packet_type="failure",
            action=request_packet.header.action,
            payload={
                "status": "failed_retryable" if failure.retryable else "failed_terminal",
                "error": failure.model_dump(mode="json", exclude_none=True),
            },
            source_node=self.local_node,
            destination_node=request_packet.address.reply_to or request_packet.address.source_node,
            reply_to=self.local_node,
            intent=request_packet.governance.intent,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )
        return append_hop(
            failure_packet,
            node=self.local_node,
            action=request_packet.header.action,
            status="failed",
            detail=failure.error_code,
        )

    @staticmethod
    def build_client_envelope(packet: TransportPacket) -> dict[str, Any]:
        payload = dict(packet.payload)
        status = payload.get("status", "completed")
        data = payload.get("data")
        error = payload.get("error")
        warnings = payload.get("warnings") or []
        meta = {
            "trace_id": packet.header.trace_id,
            "correlation_id": packet.header.correlation_id,
            "version": packet.header.version,
            "schema_version": packet.header.schema_version,
            "timestamp": packet.header.created_at.isoformat().replace("+00:00", "Z"),
            "packet_id": str(packet.header.packet_id),
            "generation": packet.lineage.generation,
            "source_node": packet.address.source_node,
            "destination_node": packet.address.destination_node,
            "classification": packet.security.classification,
            "audit_required": packet.governance.audit_required,
            "warnings": warnings,
        }
        envelope: dict[str, Any] = {
            "status": status,
            "action": packet.header.action,
            "tenant": packet.tenant.org_id,
            "data": data,
            "meta": meta,
        }
        if error is not None:
            envelope["error"] = error
        if payload.get("client_message") is not None:
            envelope["message"] = payload["client_message"]
        return envelope


__all__ = [
    "ResponseFactory",
]
