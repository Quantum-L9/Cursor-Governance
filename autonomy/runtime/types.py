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


@dataclass(frozen=True)
class SchedulingCycle:
    """One saturation cycle: what was admitted and, when short, why.

    Silent underutilization is a scheduler defect, so every action that was
    READY but not selected is attributed to exactly one blocking reason.
    """

    selected: tuple[ScheduledAction, ...]
    ready: int
    running: int
    available_global_slots: int
    blocked_dependency: int
    blocked_claim: int
    blocked_resource_capacity: int
    blocked_campaign_budget: int
    blocked_role_cardinality: int
    blocked_global_capacity: int
    blocked_unknown_resource_class: int
    blocked_human_gate: int
    caller_limit: int | None = None
    caller_limit_applied: bool = False

    @property
    def selected_count(self) -> int:
        return len(self.selected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "running": self.running,
            "selected": self.selected_count,
            "available_global_slots": self.available_global_slots,
            "blocked_dependency": self.blocked_dependency,
            "blocked_claim": self.blocked_claim,
            "blocked_resource_capacity": self.blocked_resource_capacity,
            "blocked_campaign_budget": self.blocked_campaign_budget,
            "blocked_role_cardinality": self.blocked_role_cardinality,
            "blocked_global_capacity": self.blocked_global_capacity,
            "blocked_unknown_resource_class": self.blocked_unknown_resource_class,
            "blocked_human_gate": self.blocked_human_gate,
            "caller_limit": self.caller_limit,
            "caller_limit_applied": self.caller_limit_applied,
        }

    def render(self) -> str:
        payload = self.to_dict()
        ordered = [
            "ready",
            "running",
            "selected",
            "available_global_slots",
            "blocked_dependency",
            "blocked_claim",
            "blocked_resource_capacity",
            "blocked_campaign_budget",
            "blocked_role_cardinality",
            "blocked_global_capacity",
            "blocked_unknown_resource_class",
            "blocked_human_gate",
        ]
        return " ".join(f"{name}={payload[name]}" for name in ordered)

    def underutilized(self) -> bool:
        """True when READY work was left idle while global capacity remained."""

        idle_ready = self.ready - self.selected_count
        return idle_ready > 0 and self.available_global_slots > self.selected_count
