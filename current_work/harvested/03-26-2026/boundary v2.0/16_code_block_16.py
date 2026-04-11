# path: tests/test_ingress_validator.py
# filename: test_ingress_validator.py
# purpose: Unit coverage for ingress validation behavior
# dependencies/interfaces: pytest, engine.boundary.ingress_validator

from __future__ import annotations

import pytest

from engine.boundary.ingress_validator import IngressValidationError, IngressValidator
from engine.boundary.transport_codec import (
    PacketAddress,
    PacketGovernance,
    PacketHeader,
    PacketLineage,
    PacketSecurity,
    TenantContext,
    TransportPacket,
    compute_content_hash,
    compute_envelope_hash,
)


def _make_packet() -> TransportPacket:
    header = PacketHeader(packet_type="request", action="match")
    address = PacketAddress(source_node="source", destination_node="gate", reply_to="source")
    tenant = TenantContext(actor="actor", originator="actor", org_id="org_1")
    governance = PacketGovernance(intent="match")
    security = PacketSecurity(content_hash="0" * 64, envelope_hash="0" * 64)
    provisional = TransportPacket.model_construct(
        header=header,
        address=address,
        tenant=tenant,
        payload={"x": 1},
        security=security,
        governance=governance,
        delegation_chain=(),
        hop_trace=(),
        lineage=PacketLineage(root_id=header.packet_id, generation=0),
        attachments=(),
    )
    content_hash = compute_content_hash(provisional)
    provisional_security = security.model_copy(update={"content_hash": content_hash})
    provisional_packet = provisional.model_copy(update={"security": provisional_security})
    envelope_hash = compute_envelope_hash(provisional_packet)
    return TransportPacket(
        header=header,
        address=address,
        tenant=tenant,
        payload={"x": 1},
        security=PacketSecurity(content_hash=content_hash, envelope_hash=envelope_hash),
        governance=governance,
        delegation_chain=(),
        hop_trace=(),
        lineage=PacketLineage(root_id=header.packet_id, generation=0),
        attachments=(),
    )


def test_validator_accepts_valid_request() -> None:
    packet = _make_packet()
    validator = IngressValidator(local_node="gate", allowed_actions={"match"})
    result = validator.validate(packet)
    assert result.packet.address.destination_node == "gate"
    assert result.packet.hop_trace[-1].status == "validated"


def test_validator_rejects_wrong_destination() -> None:
    packet = _make_packet().model_copy(
        update={"address": PacketAddress(source_node="source", destination_node="other", reply_to="source")}
    )
    validator = IngressValidator(local_node="gate", allowed_actions={"match"})
    with pytest.raises(IngressValidationError) as exc:
        validator.validate(packet)
    assert exc.value.error_code == "packet_routed_to_wrong_node"
