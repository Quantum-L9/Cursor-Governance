# path: engine/boundary/replay_factory.py
# filename: replay_factory.py
# purpose: Canonical replay request and replay response derivation
# dependencies/interfaces: Consumes TransportPacket and replay policy

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .transport_codec import TransportPacket, append_hop, derive_packet


class ReplayPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["audit_replay", "state_replay", "logic_replay", "repair_replay"]
    side_effect_policy: Literal["none", "idempotent_allowed", "disabled_in_replay", "manual_approval_required"] = "disabled_in_replay"
    max_records: int = Field(default=1000, ge=1, le=100000)
    replay_after: datetime | None = None

    @field_validator("replay_after")
    @classmethod
    def _validate_dt(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("replay_after must be timezone-aware")
        return value


class ReplayFactory:
    def __init__(self, *, local_node: str, signing_secret: str | None = None, signing_key_id: str | None = None) -> None:
        self.local_node = local_node.strip().lower()
        self.signing_secret = signing_secret
        self.signing_key_id = signing_key_id

    def build_replay_request(
        self,
        source_packet: TransportPacket,
        *,
        target_node: str,
        policy: ReplayPolicy,
        reason: str,
    ) -> TransportPacket:
        payload = {
            "source_packet_id": str(source_packet.header.packet_id),
            "root_packet_id": str(source_packet.lineage.root_id),
            "source_action": source_packet.header.action,
            "reason": reason,
            "mode": policy.mode,
            "side_effect_policy": policy.side_effect_policy,
            "max_records": policy.max_records,
        }
        replay_packet = derive_packet(
            source_packet,
            packet_type="replay_request",
            action="replay",
            payload=payload,
            source_node=self.local_node,
            destination_node=target_node.strip().lower(),
            reply_to=self.local_node,
            intent="replay",
            expires_at=policy.replay_after,
            replay_mode=True,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )
        return append_hop(
            replay_packet,
            node=self.local_node,
            action="replay",
            status="delegated",
            detail=f"{policy.mode}:{policy.side_effect_policy}",
        )

    def build_replay_response(
        self,
        replay_request: TransportPacket,
        *,
        replay_status: Literal["completed", "partial", "failed_terminal", "failed_retryable"],
        replay_summary: dict[str, object],
    ) -> TransportPacket:
        response = derive_packet(
            replay_request,
            packet_type="replay_response",
            action="replay",
            payload={
                "status": replay_status,
                "data": replay_summary,
            },
            source_node=self.local_node,
            destination_node=replay_request.address.reply_to or replay_request.address.source_node,
            reply_to=self.local_node,
            intent="replay",
            replay_mode=True,
            sign_secret=self.signing_secret,
            signing_key_id=self.signing_key_id,
        )
        return append_hop(
            response,
            node=self.local_node,
            action="replay",
            status="completed" if replay_status in {"completed", "partial"} else "failed",
            detail=replay_status,
        )


__all__ = [
    "ReplayFactory",
    "ReplayPolicy",
]
