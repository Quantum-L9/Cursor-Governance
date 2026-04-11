# path: tests/test_transport_codec.py
# filename: test_transport_codec.py
# purpose: Unit coverage for packet derivation, hashing, and signature behavior
# dependencies/interfaces: pytest, engine.boundary.transport_codec

from __future__ import annotations

from engine.boundary.transport_codec import (
    PacketAddress,
    PacketGovernance,
    PacketHeader,
    PacketLineage,
    PacketSecurity,
    TenantContext,
    TransportPacket,
    append_hop,
    compute_content_hash,
    compute_envelope_hash,
    compute_signature,
    derive_packet,
    verify_signature,
)


def _make_packet() -> TransportPacket:
    header = PacketHeader(packet_type="request", action="match")
    address = PacketAddress(source_node="source", destination_node="gate", reply_to="source")
    tenant = TenantContext(actor="actor", originator="actor", org_id="org_1")
    governance = PacketGovernance(intent="match")
    security = PacketSecurity(
        content_hash="0" * 64,
        envelope_hash="0" * 64,
    )
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
    security = security.model_copy(
        update={
            "content_hash": compute_content_hash(provisional),
            "envelope_hash": compute_envelope_hash(provisional.model_copy(update={"security": security.model_copy(update={"content_hash": compute_content_hash(provisional)})})),
        }
    )
    packet = TransportPacket(
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
    signature = compute_signature(packet, "secret")
    return packet.model_copy(update={"security": packet.security.model_copy(update={"signature": signature})})


def test_derive_packet_increments_generation() -> None:
    packet = _make_packet()
    derived = derive_packet(
        packet,
        packet_type="response",
        action="match",
        payload={"ok": True},
        source_node="gate",
        destination_node="source",
        sign_secret="secret",
        signing_key_id="k1",
    )
    assert derived.lineage.parent_id == packet.header.packet_id
    assert derived.lineage.root_id == packet.lineage.root_id
    assert derived.lineage.generation == packet.lineage.generation + 1
    assert verify_signature(derived, "secret") is True


def test_append_hop_preserves_content_hash() -> None:
    packet = _make_packet()
    before = packet.security.content_hash
    updated = append_hop(packet, node="gate", action="match", status="validated", detail="ok")
    after = updated.security.content_hash
    assert before == after
    assert len(updated.hop_trace) == 1
