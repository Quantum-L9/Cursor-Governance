"""Typed contracts for bounded concurrent Claude Code workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Literal

LockMode = Literal["read", "write"]
BarrierPolicy = Literal["all", "any", "threshold"]


class ActionStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    CLAIMED = "claimed"
    RUNNING = "running"
    WAITING_EXTERNAL = "waiting_external"
    VALIDATING = "validating"
    VALIDATED = "validated"
    COMPLETED = "completed"
    RETRYABLE = "retryable"
    REPAIR_REQUIRED = "repair_required"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


TERMINAL_SUCCESS = {ActionStatus.VALIDATED, ActionStatus.COMPLETED}
LOCK_HOLDING = {
    ActionStatus.CLAIMED,
    ActionStatus.RUNNING,
    ActionStatus.WAITING_EXTERNAL,
    ActionStatus.VALIDATING,
}


@dataclass(frozen=True, slots=True)
class ResourceLock:
    """A declared read/write claim over a canonical resource key."""

    key: str
    mode: LockMode
    isolation_key: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ResourceLock:
        key = str(raw.get("key", "")).strip()
        mode = raw.get("mode")
        isolation_key = raw.get("isolation_key")
        if not key:
            raise ValueError("resource lock key is required")
        if mode not in {"read", "write"}:
            raise ValueError(f"invalid resource lock mode for {key!r}: {mode!r}")
        return cls(
            key=key,
            mode=mode,
            isolation_key=str(isolation_key).strip() if isolation_key else None,
        )


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """Immutable execution definition used by readiness and scheduling."""

    action_id: str
    objective: str
    depends_on: tuple[str, ...] = ()
    resources: tuple[ResourceLock, ...] = ()
    mutation: bool = False
    preconditions_satisfied: bool = True
    priority: int = 0
    critical_path_weight: int = 0
    downstream_unlocks: int = 0
    reversibility_score: int = 0
    validation_strength: int = 0
    blast_radius: int = 0
    operation_id: str | None = None
    join_group: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ActionSpec:
        action_id = str(raw.get("action_id", "")).strip()
        objective = str(raw.get("objective", "")).strip()
        if not action_id:
            raise ValueError("action_id is required")
        if not objective:
            raise ValueError(f"objective is required for action {action_id!r}")
        resources = tuple(ResourceLock.from_dict(item) for item in raw.get("resources", []))
        mutation = bool(raw.get("mutation", False))
        if mutation and not any(resource.mode == "write" for resource in resources):
            raise ValueError(f"mutation action {action_id!r} must declare at least one write lock")
        return cls(
            action_id=action_id,
            objective=objective,
            depends_on=tuple(str(item) for item in raw.get("depends_on", [])),
            resources=resources,
            mutation=mutation,
            preconditions_satisfied=bool(raw.get("preconditions_satisfied", True)),
            priority=int(raw.get("priority", 0)),
            critical_path_weight=int(raw.get("critical_path_weight", 0)),
            downstream_unlocks=int(raw.get("downstream_unlocks", 0)),
            reversibility_score=int(raw.get("reversibility_score", 0)),
            validation_strength=int(raw.get("validation_strength", 0)),
            blast_radius=int(raw.get("blast_radius", 0)),
            operation_id=str(raw["operation_id"]) if raw.get("operation_id") else None,
            join_group=str(raw["join_group"]) if raw.get("join_group") else None,
        )

    def score(self) -> int:
        """Deterministic priority score for critical-path reduction."""

        return (
            self.priority
            + self.critical_path_weight
            + self.downstream_unlocks
            + self.reversibility_score
            + self.validation_strength
            - self.blast_radius
        )


@dataclass(slots=True)
class ActionRuntime:
    status: ActionStatus = ActionStatus.PENDING
    lease_holder: str | None = None
    exact_commit_sha: str | None = None
    retries: int = 0
    blocker: str | None = None
    resume_cursor: str | None = None
    proof_bundle: dict[str, Any] = field(default_factory=dict)
    checkpoint: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> ActionRuntime:
        data = raw or {}
        return cls(
            status=ActionStatus(data.get("status", ActionStatus.PENDING)),
            lease_holder=data.get("lease_holder"),
            exact_commit_sha=data.get("exact_commit_sha"),
            retries=int(data.get("retries", 0)),
            blocker=data.get("blocker"),
            resume_cursor=data.get("resume_cursor"),
            proof_bundle=dict(data.get("proof_bundle", {})),
            checkpoint=dict(data.get("checkpoint", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass(slots=True)
class CampaignState:
    campaign_id: str
    objective: str
    action_specs: dict[str, ActionSpec]
    action_runtime: dict[str, ActionRuntime]
    authority_profile: str = "pr-convergence"
    completed_operations: set[str] = field(default_factory=set)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    state_digest: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignState:
        campaign_id = str(raw.get("campaign_id", "")).strip()
        objective = str(raw.get("objective", "")).strip()
        if not campaign_id or not objective:
            raise ValueError("campaign_id and objective are required")
        specs = {
            item.action_id: item
            for item in (ActionSpec.from_dict(value) for value in raw.get("actions", []))
        }
        if len(specs) != len(raw.get("actions", [])):
            raise ValueError("duplicate action_id in campaign")
        runtime_raw = raw.get("runtime", {})
        runtime = {
            action_id: ActionRuntime.from_dict(runtime_raw.get(action_id)) for action_id in specs
        }
        unknown_runtime = set(runtime_raw) - set(specs)
        if unknown_runtime:
            raise ValueError(f"runtime contains unknown actions: {sorted(unknown_runtime)}")
        return cls(
            campaign_id=campaign_id,
            objective=objective,
            action_specs=specs,
            action_runtime=runtime,
            authority_profile=str(raw.get("authority_profile", "pr-convergence")),
            completed_operations=set(str(item) for item in raw.get("completed_operations", [])),
            checkpoints=list(raw.get("checkpoints", [])),
            state_digest=str(raw.get("state_digest", "")),
        )

    def to_dict(self, include_digest: bool = True) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        for action_id in sorted(self.action_specs):
            spec = self.action_specs[action_id]
            payload = asdict(spec)
            payload["resources"] = [asdict(resource) for resource in spec.resources]
            payload["depends_on"] = list(spec.depends_on)
            actions.append(payload)
        result: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "objective": self.objective,
            "authority_profile": self.authority_profile,
            "actions": actions,
            "runtime": {
                action_id: self.action_runtime[action_id].to_dict()
                for action_id in sorted(self.action_runtime)
            },
            "completed_operations": sorted(self.completed_operations),
            "checkpoints": self.checkpoints,
        }
        if include_digest:
            result["state_digest"] = self.state_digest
        return result


@dataclass(frozen=True, slots=True)
class ConcurrencyBudget:
    total_lanes: int = 4
    mutation_lanes: int = 2

    def __post_init__(self) -> None:
        if self.total_lanes < 1:
            raise ValueError("total_lanes must be at least 1")
        if self.mutation_lanes < 0 or self.mutation_lanes > self.total_lanes:
            raise ValueError("mutation_lanes must be between 0 and total_lanes")


@dataclass(frozen=True, slots=True)
class SchedulePlan:
    selected: tuple[str, ...]
    deferred: dict[str, str]
    ready: tuple[str, ...]
    available_total_lanes: int
    available_mutation_lanes: int


@dataclass(frozen=True, slots=True)
class JoinBarrier:
    join_id: str
    member_actions: tuple[str, ...]
    policy: BarrierPolicy = "all"
    threshold: int | None = None
    required_proof_keys: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> JoinBarrier:
        join_id = str(raw.get("join_id", "")).strip()
        members = tuple(str(item) for item in raw.get("member_actions", []))
        policy = raw.get("policy", "all")
        if not join_id or not members:
            raise ValueError("join_id and member_actions are required")
        if policy not in {"all", "any", "threshold"}:
            raise ValueError(f"invalid join policy: {policy!r}")
        threshold = raw.get("threshold")
        if policy == "threshold":
            if threshold is None or int(threshold) < 1 or int(threshold) > len(members):
                raise ValueError("threshold must be between 1 and member count")
            threshold = int(threshold)
        else:
            threshold = None
        return cls(
            join_id=join_id,
            member_actions=members,
            policy=policy,
            threshold=threshold,
            required_proof_keys=tuple(str(item) for item in raw.get("required_proof_keys", [])),
        )
