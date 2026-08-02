from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ActionStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
    SKIPPED = "SKIPPED"


class LeaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class CampaignRuntimeState(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    LOCKED = "LOCKED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Lease:
    lease_id: str
    campaign_id: str
    graph_id: str
    action_id: str
    agent_id: str
    role: str
    status: LeaseStatus
    issued_at: str
    expires_at: str
    last_heartbeat_at: str
    capability_id: str
    base_sha: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    code: str
    message: str
    lease_id: str | None = None
    capability: str | None = None
    resource: str | None = None

    def require_allowed(self) -> None:
        if not self.allowed:
            from autonomy.errors import PolicyViolation

            raise PolicyViolation(f"{self.code}: {self.message}")


@dataclass(frozen=True)
class ScheduledAction:
    action_id: str
    role: str
    resource_class: str
    score: float
    mutation: bool
