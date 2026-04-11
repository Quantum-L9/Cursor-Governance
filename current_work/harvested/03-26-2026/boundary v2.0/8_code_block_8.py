# path: engine/boundary/ingress_validator.py
# filename: ingress_validator.py
# purpose: Canonical ingress validation for packets entering a node boundary
# dependencies/interfaces: Uses TransportPacket from transport_codec.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from .transport_codec import (
    TransportPacket,
    append_hop,
    decode_packet,
    packet_size_bytes,
    utc_now,
    verify_signature,
)


class IngressValidationError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        client_message: str,
        detail: str,
        retryable: bool = False,
        failed_stage: str = "ingress_validation",
    ) -> None:
        super().__init__(detail)
        self.error_code = error_code
        self.client_message = client_message
        self.detail = detail
        self.retryable = retryable
        self.failed_stage = failed_stage


@dataclass(frozen=True)
class IngressValidationResult:
    packet: TransportPacket
    received_at: datetime
    raw_size_bytes: int


class IngressValidator:
    def __init__(
        self,
        *,
        local_node: str,
        signature_secret: str | None = None,
        require_signature: bool = False,
        allowed_actions: Iterable[str] | None = None,
        allowed_packet_types: Iterable[str] | None = None,
        allowed_clock_skew_seconds: int = 30,
        max_packet_bytes: int = 256 * 1024,
        max_hop_depth: int = 64,
        max_delegation_depth: int = 8,
        max_attachments: int = 32,
    ) -> None:
        self.local_node = local_node.strip().lower()
        self.signature_secret = signature_secret
        self.require_signature = require_signature
        self.allowed_actions = set(allowed_actions or ())
        self.allowed_packet_types = set(
            allowed_packet_types or {"request", "command", "delegation", "replay_request"}
        )
        self.allowed_clock_skew_seconds = allowed_clock_skew_seconds
        self.max_packet_bytes = max_packet_bytes
        self.max_hop_depth = max_hop_depth
        self.max_delegation_depth = max_delegation_depth
        self.max_attachments = max_attachments

    def validate(self, raw: bytes | str | dict[str, Any] | TransportPacket) -> IngressValidationResult:
        received_at = utc_now()
        raw_size = packet_size_bytes(raw)
        if raw_size > self.max_packet_bytes:
            raise IngressValidationError(
                error_code="packet_too_large",
                client_message="Request rejected",
                detail=f"packet size {raw_size} exceeds max {self.max_packet_bytes}",
                retryable=False,
            )

        try:
            packet = decode_packet(raw)
        except Exception as exc:  # noqa: BLE001
            raise IngressValidationError(
                error_code="packet_decode_failed",
                client_message="Request rejected",
                detail=f"packet decode failed: {exc}",
                retryable=False,
            ) from exc

        self._validate_basic(packet, received_at)
        self._validate_destination(packet)
        self._validate_allowed(packet)
        self._validate_time(packet, received_at)
        self._validate_limits(packet)
        self._validate_delegation_scope(packet)
        self._validate_signature(packet)

        packet = append_hop(
            packet,
            node=self.local_node,
            action=packet.header.action,
            status="validated",
            detail="ingress validation passed",
        )
        return IngressValidationResult(packet=packet, received_at=received_at, raw_size_bytes=raw_size)

    def _validate_basic(self, packet: TransportPacket, received_at: datetime) -> None:
        if packet.header.packet_type not in self.allowed_packet_types:
            raise IngressValidationError(
                error_code="packet_type_not_allowed",
                client_message="Request rejected",
                detail=f"packet_type {packet.header.packet_type!r} is not allowed for ingress",
            )
        if packet.header.replay_mode and packet.header.packet_type != "replay_request":
            raise IngressValidationError(
                error_code="replay_mode_invalid",
                client_message="Request rejected",
                detail="replay_mode may only be used with replay_request packets",
            )
        if packet.governance.audit_required and packet.security.classification == "restricted" and not packet.security.pii_fields:
            raise IngressValidationError(
                error_code="restricted_packet_missing_pii_metadata",
                client_message="Request rejected",
                detail="restricted packets with audit_required must declare pii_fields",
            )
        if packet.header.created_at > received_at + timedelta(seconds=self.allowed_clock_skew_seconds):
            raise IngressValidationError(
                error_code="packet_created_in_future",
                client_message="Request rejected",
                detail="packet created_at exceeds allowed clock skew",
            )

    def _validate_destination(self, packet: TransportPacket) -> None:
        if packet.address.destination_node != self.local_node:
            raise IngressValidationError(
                error_code="packet_routed_to_wrong_node",
                client_message="Request rejected",
                detail=f"destination_node {packet.address.destination_node!r} does not match local node {self.local_node!r}",
            )
        if packet.address.source_node == packet.address.destination_node and packet.header.packet_type == "delegation":
            raise IngressValidationError(
                error_code="delegation_self_loop_forbidden",
                client_message="Request rejected",
                detail="delegation packet cannot point to same node",
            )

    def _validate_allowed(self, packet: TransportPacket) -> None:
        if self.allowed_actions and packet.header.action not in self.allowed_actions:
            raise IngressValidationError(
                error_code="action_not_allowed",
                client_message="Request rejected",
                detail=f"action {packet.header.action!r} is not permitted on this node",
            )
        if packet.header.packet_type in {"delegation", "replay_request"} and packet.header.action != packet.governance.intent:
            raise IngressValidationError(
                error_code="intent_action_mismatch",
                client_message="Request rejected",
                detail="for delegation and replay packets, governance intent must match action",
            )

    def _validate_time(self, packet: TransportPacket, received_at: datetime) -> None:
        if packet.header.not_before is not None and received_at < packet.header.not_before:
            raise IngressValidationError(
                error_code="packet_not_yet_valid",
                client_message="Request rejected",
                detail="packet not_before is in the future",
                retryable=True,
            )
        if packet.header.expires_at is not None and received_at > packet.header.expires_at:
            raise IngressValidationError(
                error_code="packet_expired",
                client_message="Request rejected",
                detail="packet has expired",
                retryable=False,
            )

    def _validate_limits(self, packet: TransportPacket) -> None:
        if len(packet.hop_trace) > self.max_hop_depth:
            raise IngressValidationError(
                error_code="hop_trace_limit_exceeded",
                client_message="Request rejected",
                detail=f"hop_trace length {len(packet.hop_trace)} exceeds max {self.max_hop_depth}",
            )
        if len(packet.delegation_chain) > self.max_delegation_depth:
            raise IngressValidationError(
                error_code="delegation_depth_limit_exceeded",
                client_message="Request rejected",
                detail=f"delegation_chain length {len(packet.delegation_chain)} exceeds max {self.max_delegation_depth}",
            )
        if len(packet.attachments) > self.max_attachments:
            raise IngressValidationError(
                error_code="attachment_limit_exceeded",
                client_message="Request rejected",
                detail=f"attachment count {len(packet.attachments)} exceeds max {self.max_attachments}",
            )

    def _validate_delegation_scope(self, packet: TransportPacket) -> None:
        if packet.header.packet_type not in {"delegation", "replay_request"}:
            return
        if not packet.delegation_chain:
            raise IngressValidationError(
                error_code="delegation_chain_missing",
                client_message="Request rejected",
                detail="delegation and replay packets require a delegation chain",
            )
        last_link = packet.delegation_chain[-1]
        if last_link.delegatee != self.local_node:
            raise IngressValidationError(
                error_code="delegation_target_mismatch",
                client_message="Request rejected",
                detail=f"delegation target {last_link.delegatee!r} does not match local node {self.local_node!r}",
            )
        if packet.header.action not in last_link.scope:
            raise IngressValidationError(
                error_code="delegation_scope_violation",
                client_message="Request rejected",
                detail=f"action {packet.header.action!r} is not permitted by delegation scope {last_link.scope!r}",
            )
        if packet.governance.audit_required is not True:
            raise IngressValidationError(
                error_code="delegation_audit_flag_missing",
                client_message="Request rejected",
                detail="delegation packets must set audit_required=True",
            )

    def _validate_signature(self, packet: TransportPacket) -> None:
        if self.require_signature and packet.security.signature is None:
            raise IngressValidationError(
                error_code="signature_required",
                client_message="Request rejected",
                detail="packet signature is required on this node",
            )
        if packet.security.signature is None:
            return
        if not self.signature_secret:
            raise IngressValidationError(
                error_code="signature_secret_missing",
                client_message="Request rejected",
                detail="signature present but no verification secret configured",
            )
        if not verify_signature(packet, self.signature_secret):
            raise IngressValidationError(
                error_code="signature_invalid",
                client_message="Request rejected",
                detail="packet signature verification failed",
            )


__all__ = [
    "IngressValidationError",
    "IngressValidationResult",
    "IngressValidator",
]
