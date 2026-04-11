# path: engine/boundary/delegation_factory.py
# filename: delegation_factory.py
# purpose: Derives canonical delegation packets from execution side-effect declarations
# dependencies/interfaces: Consumes DelegationRequest and TransportPacket

from __future__ import annotations

from .command_factory import DelegationRequest
from .transport_codec import (
    TransportPacket,
    append_delegation,
    append_hop,
    build_delegation_proof,
    derive_packet,
)


class DelegationFactory:
    def __init__(self, *, local_node: str, signing_secret: str | None = None, signing_key_id: str | None = None) -> None:
        self.local_node = local_node.strip().lower()
        self.signing_secret = signing_secret
        self.signing_key_id = signing_key_id

    def build_packet(self, request_packet: TransportPacket, delegation: DelegationRequest) -> TransportPacket:
        delegated = derive_packet(
            request_packet,
            packet_type="delegation",
            action=delegation.action,
            payload=delegation.payload,
            source_node=self.local_node,
            destination_node=delegation.target_node,
            reply_to=self.local_node,
            intent=delegation.intent,
            priority=delegation.priority,
            expires_at=delegation.expires_at,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )

        proof = None
        if self.signing_secret:
            proof = build_delegation_proof(
                packet=delegated,
                delegator=self.local_node,
                delegatee=delegation.target_node,
                scope=delegation.permissions,
                secret=self.signing_secret,
            )

        delegated = append_delegation(
            delegated,
            delegator=self.local_node,
            delegatee=delegation.target_node,
            scope=delegation.permissions,
            proof=proof,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )
        return append_hop(
            delegated,
            node=self.local_node,
            action=delegation.action,
            status="delegated",
            detail=f"delegated to {delegation.target_node}",
        )

    def build_many(self, request_packet: TransportPacket, delegations: tuple[DelegationRequest, ...]) -> list[TransportPacket]:
        return [self.build_packet(request_packet, delegation) for delegation in delegations]


__all__ = [
    "DelegationFactory",
]
