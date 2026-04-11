# path: engine/boundary/transport_codec.py
# filename: transport_codec.py
# purpose: Canonical transport packet models, hashing, signing, encoding, decoding, and derivation
# dependencies/interfaces: Pydantic v2; used by all boundary factories and validators

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PacketType = Literal[
    "request",
    "response",
    "event",
    "command",
    "delegation",
    "failure",
    "compensation",
    "replay_request",
    "replay_response",
]
HopStatus = Literal["received", "validated", "processing", "delegated", "completed", "failed"]
Classification = Literal["public", "internal", "confidential", "restricted"]
EncryptionStatus = Literal["plaintext", "encrypted", "envelope-only"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _normalize_string(value: str) -> str:
    return value.strip()


def _canonicalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonicalize(value.model_dump(mode="python", exclude_none=False))
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, datetime):
        normalized = _ensure_utc(value)
        if normalized is None:
            return None
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return value


def canonical_json(value: Any) -> bytes:
    normalized = _canonicalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


class PacketHeader(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    packet_id: UUID = Field(default_factory=uuid4)
    packet_type: PacketType
    action: str
    version: str = "v1"
    schema_version: str = "transport.v1"
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    not_before: datetime | None = None
    priority: int = Field(default=5, ge=1, le=10)
    deadline_ms: int | None = Field(default=None, ge=1)
    idempotency_key: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    causation_id: UUID | None = None
    retry_count: int = Field(default=0, ge=0)
    replay_mode: bool = False

    @field_validator("action", "version", "schema_version")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("created_at", "expires_at", "not_before")
    @classmethod
    def _normalize_dt(cls, value: datetime | None) -> datetime | None:
        return _ensure_utc(value)

    @model_validator(mode="after")
    def _validate_timing(self) -> "PacketHeader":
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        if self.not_before is not None and self.not_before < self.created_at:
            raise ValueError("not_before must not be earlier than created_at")
        return self


class PacketAddress(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_node: str
    destination_node: str
    reply_to: str | None = None

    @field_validator("source_node", "destination_node")
    @classmethod
    def _validate_nodes(cls, value: str) -> str:
        normalized = _normalize_string(value).lower()
        if not normalized:
            raise ValueError("node value must not be empty")
        return normalized

    @field_validator("reply_to")
    @classmethod
    def _validate_reply_to(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value).lower()
        if not normalized:
            raise ValueError("reply_to must not be empty")
        return normalized


class TenantContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor: str
    on_behalf_of: str | None = None
    originator: str
    org_id: str
    user_id: str | None = None

    @field_validator("actor", "originator", "org_id")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("tenant field must not be empty")
        return normalized

    @field_validator("on_behalf_of", "user_id")
    @classmethod
    def _validate_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("optional tenant field must not be empty")
        return normalized


class PacketSecurity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    content_hash: str
    envelope_hash: str
    signature: str | None = None
    signing_key_id: str | None = None
    classification: Classification = "internal"
    encryption_status: EncryptionStatus = "plaintext"
    pii_fields: tuple[str, ...] = ()

    @field_validator("content_hash", "envelope_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        normalized = _normalize_string(value).lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("hash must be a 64-char lowercase sha256 hex digest")
        return normalized

    @field_validator("signature", "signing_key_id")
    @classmethod
    def _validate_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("optional security field must not be empty")
        return normalized

    @field_validator("pii_fields")
    @classmethod
    def _validate_pii_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_string(v) for v in value if _normalize_string(v))
        if len(set(normalized)) != len(normalized):
            raise ValueError("pii_fields must not contain duplicates")
        return normalized


class PacketGovernance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: str
    compliance_tags: tuple[str, ...] = ()
    retention_days: int | None = Field(default=None, ge=1)
    redaction_applied: bool = False
    audit_required: bool = False
    data_subject_id: str | None = None

    @field_validator("intent")
    @classmethod
    def _validate_intent(cls, value: str) -> str:
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("intent must not be empty")
        return normalized

    @field_validator("compliance_tags")
    @classmethod
    def _validate_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_string(v).upper() for v in value if _normalize_string(v))
        if len(set(normalized)) != len(normalized):
            raise ValueError("compliance_tags must not contain duplicates")
        return normalized

    @field_validator("data_subject_id")
    @classmethod
    def _validate_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("data_subject_id must not be empty")
        return normalized


class DelegationLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    delegator: str
    delegatee: str
    scope: tuple[str, ...]
    delegated_at: datetime = Field(default_factory=utc_now)
    proof: str | None = None

    @field_validator("delegator", "delegatee")
    @classmethod
    def _validate_nodes(cls, value: str) -> str:
        normalized = _normalize_string(value).lower()
        if not normalized:
            raise ValueError("delegation node must not be empty")
        return normalized

    @field_validator("scope")
    @classmethod
    def _validate_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_string(v) for v in value if _normalize_string(v))
        if not normalized:
            raise ValueError("delegation scope must not be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("delegation scope must not contain duplicates")
        return normalized

    @field_validator("delegated_at")
    @classmethod
    def _validate_dt(cls, value: datetime) -> datetime:
        normalized = _ensure_utc(value)
        if normalized is None:
            raise ValueError("delegated_at must not be null")
        return normalized

    @field_validator("proof")
    @classmethod
    def _validate_proof(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("delegation proof must not be empty")
        return normalized


class HopEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node: str
    action: str
    status: HopStatus
    at: datetime = Field(default_factory=utc_now)
    detail: str | None = None
    signature: str | None = None

    @field_validator("node", "action")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("hop field must not be empty")
        return normalized

    @field_validator("at")
    @classmethod
    def _validate_dt(cls, value: datetime) -> datetime:
        normalized = _ensure_utc(value)
        if normalized is None:
            raise ValueError("at must not be null")
        return normalized

    @field_validator("detail", "signature")
    @classmethod
    def _validate_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("hop optional field must not be empty")
        return normalized


class PacketLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parent_id: UUID | None = None
    root_id: UUID
    generation: int = Field(default=0, ge=0)


class PacketAttachment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attachment_id: UUID = Field(default_factory=uuid4)
    media_type: str
    uri: str
    content_hash: str
    encrypted: bool = True
    size_bytes: int = Field(ge=0)

    @field_validator("media_type", "uri")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = _normalize_string(value)
        if not normalized:
            raise ValueError("attachment field must not be empty")
        return normalized

    @field_validator("content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        normalized = _normalize_string(value).lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("attachment content_hash must be a 64-char lowercase sha256 hex digest")
        return normalized


class TransportPacket(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    header: PacketHeader
    address: PacketAddress
    tenant: TenantContext
    payload: dict[str, Any]
    security: PacketSecurity
    governance: PacketGovernance
    delegation_chain: tuple[DelegationLink, ...] = ()
    hop_trace: tuple[HopEntry, ...] = ()
    lineage: PacketLineage
    attachments: tuple[PacketAttachment, ...] = ()

    @field_validator("payload")
    @classmethod
    def _validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("payload must be a dict")
        return value

    @model_validator(mode="after")
    def _validate_integrity(self) -> "TransportPacket":
        expected_content_hash = compute_content_hash(self)
        if self.security.content_hash != expected_content_hash:
            raise ValueError("packet content_hash does not match packet body")
        expected_envelope_hash = compute_envelope_hash(self)
        if self.security.envelope_hash != expected_envelope_hash:
            raise ValueError("packet envelope_hash does not match packet envelope")
        return self


def _content_hash_payload(packet: TransportPacket | dict[str, Any]) -> dict[str, Any]:
    if isinstance(packet, TransportPacket):
        return {
            "packet_type": packet.header.packet_type,
            "action": packet.header.action,
            "payload": packet.payload,
            "tenant": packet.tenant,
            "address": packet.address,
        }
    return packet


def _envelope_hash_payload(packet: TransportPacket) -> dict[str, Any]:
    return {
        "header": packet.header,
        "address": packet.address,
        "tenant": packet.tenant,
        "payload": packet.payload,
        "governance": packet.governance,
        "delegation_chain": packet.delegation_chain,
        "lineage": packet.lineage,
        "attachments": packet.attachments,
        "content_hash": packet.security.content_hash,
    }


def compute_content_hash(packet: TransportPacket | dict[str, Any]) -> str:
    return sha256_hex(_content_hash_payload(packet))


def compute_envelope_hash(packet: TransportPacket) -> str:
    return sha256_hex(_envelope_hash_payload(packet))


def compute_signature(packet: TransportPacket, secret: str) -> str:
    if not secret:
        raise ValueError("secret must not be empty")
    return hmac.new(secret.encode("utf-8"), packet.security.envelope_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(packet: TransportPacket, secret: str) -> bool:
    if packet.security.signature is None:
        return False
    expected = compute_signature(packet, secret)
    return hmac.compare_digest(packet.security.signature, expected)


def build_delegation_proof(
    *,
    packet: TransportPacket,
    delegator: str,
    delegatee: str,
    scope: tuple[str, ...],
    secret: str,
) -> str:
    proof_payload = {
        "packet_id": packet.header.packet_id,
        "delegator": delegator,
        "delegatee": delegatee,
        "scope": scope,
        "tenant": packet.tenant,
        "intent": packet.governance.intent,
        "envelope_hash": packet.security.envelope_hash,
    }
    return hmac.new(secret.encode("utf-8"), canonical_json(proof_payload), hashlib.sha256).hexdigest()


def _refresh_security(
    packet: TransportPacket,
    *,
    signing_secret: str | None = None,
    signing_key_id: str | None = None,
    preserve_signature_when_secret_missing: bool = False,
) -> PacketSecurity:
    content_hash = compute_content_hash(packet)
    provisional_security = packet.security.model_copy(
        update={
            "content_hash": content_hash,
            "envelope_hash": "0" * 64,
            "signature": packet.security.signature if preserve_signature_when_secret_missing else None,
            "signing_key_id": signing_key_id if signing_key_id is not None else packet.security.signing_key_id,
        }
    )
    provisional_packet = packet.model_copy(update={"security": provisional_security})
    envelope_hash = compute_envelope_hash(provisional_packet)
    updated_security = provisional_security.model_copy(update={"envelope_hash": envelope_hash})
    final_packet = provisional_packet.model_copy(update={"security": updated_security})
    if signing_secret:
        updated_security = updated_security.model_copy(
            update={
                "signature": hmac.new(
                    signing_secret.encode("utf-8"),
                    updated_security.envelope_hash.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest(),
                "signing_key_id": signing_key_id,
            }
        )
    elif not preserve_signature_when_secret_missing:
        updated_security = updated_security.model_copy(update={"signature": None})
    return updated_security


def append_hop(
    packet: TransportPacket,
    *,
    node: str,
    action: str,
    status: HopStatus,
    detail: str | None = None,
    signature: str | None = None,
) -> TransportPacket:
    new_hop = HopEntry(
        node=node,
        action=action,
        status=status,
        detail=detail,
        signature=signature,
    )
    return packet.model_copy(update={"hop_trace": packet.hop_trace + (new_hop,)})


def append_delegation(
    packet: TransportPacket,
    *,
    delegator: str,
    delegatee: str,
    scope: tuple[str, ...],
    proof: str | None = None,
    sign_secret: str | None = None,
    signing_key_id: str | None = None,
) -> TransportPacket:
    link = DelegationLink(
        delegator=delegator,
        delegatee=delegatee,
        scope=scope,
        proof=proof,
    )
    updated_governance = packet.governance.model_copy(update={"audit_required": True})
    updated_packet = packet.model_copy(
        update={
            "delegation_chain": packet.delegation_chain + (link,),
            "governance": updated_governance,
        }
    )
    refreshed_security = _refresh_security(updated_packet, signing_secret=sign_secret, signing_key_id=signing_key_id)
    return updated_packet.model_copy(update={"security": refreshed_security})


def derive_packet(
    source_packet: TransportPacket,
    *,
    packet_type: PacketType,
    action: str,
    payload: dict[str, Any],
    source_node: str,
    destination_node: str,
    reply_to: str | None = None,
    intent: str | None = None,
    priority: int | None = None,
    expires_at: datetime | None = None,
    replay_mode: bool | None = None,
    sign_secret: str | None = None,
    signing_key_id: str | None = None,
    additional_attachments: tuple[PacketAttachment, ...] = (),
) -> TransportPacket:
    header = PacketHeader(
        packet_type=packet_type,
        action=action,
        version=source_packet.header.version,
        schema_version=source_packet.header.schema_version,
        created_at=utc_now(),
        expires_at=_ensure_utc(expires_at),
        priority=source_packet.header.priority if priority is None else priority,
        deadline_ms=source_packet.header.deadline_ms,
        idempotency_key=source_packet.header.idempotency_key,
        trace_id=source_packet.header.trace_id,
        correlation_id=source_packet.header.correlation_id,
        causation_id=source_packet.header.packet_id,
        retry_count=0,
        replay_mode=source_packet.header.replay_mode if replay_mode is None else replay_mode,
    )
    address = PacketAddress(
        source_node=source_node,
        destination_node=destination_node,
        reply_to=reply_to,
    )
    lineage = PacketLineage(
        parent_id=source_packet.header.packet_id,
        root_id=source_packet.lineage.root_id,
        generation=source_packet.lineage.generation + 1,
    )
    governance = source_packet.governance.model_copy(update={"intent": intent or source_packet.governance.intent})
    security = PacketSecurity(
        content_hash="0" * 64,
        envelope_hash="0" * 64,
        signature=None,
        signing_key_id=signing_key_id,
        classification=source_packet.security.classification,
        encryption_status=source_packet.security.encryption_status,
        pii_fields=source_packet.security.pii_fields,
    )
    provisional_packet = TransportPacket.model_construct(
        header=header,
        address=address,
        tenant=source_packet.tenant,
        payload=payload,
        security=security,
        governance=governance,
        delegation_chain=source_packet.delegation_chain,
        hop_trace=source_packet.hop_trace,
        lineage=lineage,
        attachments=source_packet.attachments + additional_attachments,
    )
    refreshed_security = _refresh_security(provisional_packet, signing_secret=sign_secret, signing_key_id=signing_key_id)
    return TransportPacket(
        header=provisional_packet.header,
        address=provisional_packet.address,
        tenant=provisional_packet.tenant,
        payload=provisional_packet.payload,
        security=refreshed_security,
        governance=provisional_packet.governance,
        delegation_chain=provisional_packet.delegation_chain,
        hop_trace=provisional_packet.hop_trace,
        lineage=provisional_packet.lineage,
        attachments=provisional_packet.attachments,
    )


def encode_packet(packet: TransportPacket) -> bytes:
    return canonical_json(packet.model_dump(mode="python", exclude_none=False))


def decode_packet(raw: bytes | str | dict[str, Any] | TransportPacket) -> TransportPacket:
    if isinstance(raw, TransportPacket):
        return raw
    if isinstance(raw, bytes):
        payload = json.loads(raw.decode("utf-8"))
    elif isinstance(raw, str):
        payload = json.loads(raw)
    else:
        payload = raw
    return TransportPacket.model_validate(payload)


def packet_size_bytes(packet: TransportPacket | bytes | str | dict[str, Any]) -> int:
    if isinstance(packet, TransportPacket):
        return len(encode_packet(packet))
    if isinstance(packet, bytes):
        return len(packet)
    if isinstance(packet, str):
        return len(packet.encode("utf-8"))
    return len(canonical_json(packet))


__all__ = [
    "Classification",
    "DelegationLink",
    "EncryptionStatus",
    "HopEntry",
    "HopStatus",
    "PacketAddress",
    "PacketAttachment",
    "PacketGovernance",
    "PacketHeader",
    "PacketLineage",
    "PacketSecurity",
    "PacketType",
    "TenantContext",
    "TransportPacket",
    "append_delegation",
    "append_hop",
    "build_delegation_proof",
    "canonical_json",
    "compute_content_hash",
    "compute_envelope_hash",
    "compute_signature",
    "decode_packet",
    "derive_packet",
    "encode_packet",
    "packet_size_bytes",
    "sha256_hex",
    "utc_now",
    "verify_signature",
]
