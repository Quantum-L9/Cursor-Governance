"""Typed contracts for subagent-generated data (law §5, §9, §10).

Dataclass-based, stdlib-only. ``from_dict`` classmethods parse the canonical
packet/unit JSON shapes and raise ``ValueError`` on structural problems that are
cheaper to catch here than in the validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GeneratedDataClass(StrEnum):
    REPOSITORY_FACT = "repository_fact"
    ARCHITECTURE_BOUNDARY = "architecture_boundary"
    OWNERSHIP_FINDING = "ownership_finding"
    DEPENDENCY_FINDING = "dependency_finding"
    IMPLEMENTATION_SURFACE = "implementation_surface"
    EXECUTION_PROCEDURE = "execution_procedure"
    VALIDATION_PROCEDURE = "validation_procedure"
    FAILURE_PATTERN = "failure_pattern"
    REJECTED_APPROACH = "rejected_approach"
    CONTEXT_REQUIREMENT = "context_requirement"
    CONTEXT_WASTE = "context_waste"
    TASK_CONTRACT_GAP = "task_contract_gap"
    POLICY_CANDIDATE = "policy_candidate"
    INVARIANT_CANDIDATE = "invariant_candidate"
    REGRESSION_CANDIDATE = "regression_candidate"
    REUSABLE_PATTERN_CANDIDATE = "reusable_pattern_candidate"
    ARTIFACT_LINEAGE = "artifact_lineage"
    UNRESOLVED_UNKNOWN = "unresolved_unknown"
    FOLLOW_ON_OPPORTUNITY = "follow_on_opportunity"
    EVIDENCE_ONLY = "evidence_only"


class EpistemicStatus(StrEnum):
    OBSERVED = "observed"
    DERIVED = "derived"
    HYPOTHESIZED = "hypothesized"
    DISPROVEN = "disproven"
    CONTESTED = "contested"
    UNRESOLVED = "unresolved"


class RouteName(StrEnum):
    MEMORY = "memory"
    CONTRACTS = "contracts"
    VALIDATION = "validation"
    PATTERNS = "patterns"
    ARCHITECTURE = "architecture"
    OPPORTUNITIES = "opportunities"
    UNKNOWNS = "unknowns"
    EVIDENCE = "evidence"
    REJECT = "reject"


class PromotionDecision(StrEnum):
    PROMOTE = "promote"
    RETAIN = "retain"
    DEFER = "defer"
    REJECT = "reject"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LifecycleState(StrEnum):
    VALID = "valid"
    STALE_REVALIDATABLE = "stale_revalidatable"
    STALE_RECOMPUTE_REQUIRED = "stale_recompute_required"
    CONTESTED = "contested"
    SUPERSEDED = "superseded"
    INVALID = "invalid"
    ARCHIVED = "archived"


class Visibility(StrEnum):
    CAMPAIGN_LOCAL = "campaign_local"
    REPOSITORY_LOCAL = "repository_local"
    PROJECT_GROUP = "project_group"
    CONSTELLATION_INTERNAL = "constellation_internal"
    RESTRICTED = "restricted"


# Routes that carry a unit into future execution influence. ``evidence`` and
# ``reject`` do not, so units targeting only those need no invalidation rule.
REUSE_ROUTES: frozenset[RouteName] = frozenset(
    {
        RouteName.MEMORY,
        RouteName.CONTRACTS,
        RouteName.VALIDATION,
        RouteName.PATTERNS,
        RouteName.ARCHITECTURE,
        RouteName.OPPORTUNITIES,
        RouteName.UNKNOWNS,
    }
)

# Epistemic statuses that assert a fact and therefore require provenance (§10.2).
EVIDENCE_REQUIRED_STATUSES: frozenset[EpistemicStatus] = frozenset(
    {EpistemicStatus.OBSERVED, EpistemicStatus.DERIVED}
)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ValueError(f"expected a list, got {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class GeneratedDataUnit:
    """One coherent, independently routable claim/procedure/unknown (law §10)."""

    unit_id: str
    primary_class: GeneratedDataClass
    epistemic_status: EpistemicStatus
    statement: str
    scope: dict[str, Any]
    confidence: float
    source_evidence: tuple[str, ...] = ()
    freshness: dict[str, Any] = field(default_factory=dict)
    proposed_routes: tuple[RouteName, ...] = ()
    expected_reuse: str | None = None
    invalidation_conditions: tuple[str, ...] = ()
    secondary_tags: tuple[str, ...] = ()
    visibility: Visibility = Visibility.CAMPAIGN_LOCAL

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GeneratedDataUnit:
        unit_id = str(raw.get("unit_id", "")).strip()
        if not unit_id:
            raise ValueError("generated data unit requires unit_id")
        try:
            primary_class = GeneratedDataClass(raw["primary_class"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{unit_id}: invalid primary_class") from exc
        try:
            epistemic_status = EpistemicStatus(raw["epistemic_status"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{unit_id}: invalid epistemic_status") from exc
        statement = str(raw.get("statement", "")).strip()
        if not statement:
            raise ValueError(f"{unit_id}: statement is required")
        scope = raw.get("scope") or {}
        if not isinstance(scope, dict):
            raise ValueError(f"{unit_id}: scope must be an object")
        confidence = float(raw.get("confidence", 0.0))
        routes = tuple(RouteName(r) for r in _as_tuple(raw.get("proposed_routes")))
        visibility = Visibility(raw.get("visibility", Visibility.CAMPAIGN_LOCAL))
        freshness = raw.get("freshness") or {}
        if not isinstance(freshness, dict):
            raise ValueError(f"{unit_id}: freshness must be an object")
        return cls(
            unit_id=unit_id,
            primary_class=primary_class,
            epistemic_status=epistemic_status,
            statement=statement,
            scope=dict(scope),
            confidence=confidence,
            source_evidence=_as_tuple(raw.get("source_evidence")),
            freshness=dict(freshness),
            proposed_routes=routes,
            expected_reuse=raw.get("expected_reuse"),
            invalidation_conditions=_as_tuple(raw.get("invalidation_conditions")),
            secondary_tags=_as_tuple(raw.get("secondary_tags")),
            visibility=visibility,
        )


@dataclass(frozen=True, slots=True)
class UnresolvedUnknown:
    """An open question that must outlive its producing agent (law §21)."""

    unknown_id: str
    description: str
    unknown_class: str
    owner: str
    blocking_status: str = "non_blocking"
    next_action: str | None = None
    evidence_needed: str | None = None
    source_action: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UnresolvedUnknown:
        unknown_id = str(raw.get("unknown_id", "")).strip()
        description = str(raw.get("description", "")).strip()
        unknown_class = str(raw.get("class", "")).strip()
        owner = str(raw.get("owner", "")).strip()
        if not (unknown_id and description and unknown_class and owner):
            raise ValueError("unresolved unknown requires unknown_id, description, class, owner")
        return cls(
            unknown_id=unknown_id,
            description=description,
            unknown_class=unknown_class,
            owner=owner,
            blocking_status=str(raw.get("blocking_status", "non_blocking")),
            next_action=raw.get("next_action"),
            evidence_needed=raw.get("evidence_needed"),
            source_action=raw.get("source_action"),
        )


@dataclass(frozen=True, slots=True)
class PacketIdentity:
    campaign_id: str
    repository: str
    base_sha: str
    action_id: str
    agent_id: str
    role: str
    graph_id: str | None = None
    repository_class: str | None = None
    lease_id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PacketIdentity:
        required = ("campaign_id", "repository", "base_sha", "action_id", "agent_id", "role")
        missing = [k for k in required if not str(raw.get(k, "")).strip()]
        if missing:
            raise ValueError(f"identity missing required fields: {', '.join(missing)}")
        return cls(
            campaign_id=str(raw["campaign_id"]),
            repository=str(raw["repository"]),
            base_sha=str(raw["base_sha"]),
            action_id=str(raw["action_id"]),
            agent_id=str(raw["agent_id"]),
            role=str(raw["role"]),
            graph_id=raw.get("graph_id"),
            repository_class=raw.get("repository_class"),
            lease_id=raw.get("lease_id"),
        )


@dataclass(frozen=True, slots=True)
class PrimaryResult:
    artifact_kind: str
    completion_status: str
    artifact_id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PrimaryResult:
        artifact_kind = str(raw.get("artifact_kind", "")).strip()
        completion_status = str(raw.get("completion_status", "")).strip()
        if not artifact_kind or not completion_status:
            raise ValueError("primary_result requires artifact_kind and completion_status")
        return cls(
            artifact_kind=artifact_kind,
            completion_status=completion_status,
            artifact_id=raw.get("artifact_id"),
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    input_artifacts: tuple[str, ...] = ()
    evidence_artifacts: tuple[str, ...] = ()
    inspected_paths: tuple[str, ...] = ()
    executed_commands: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> Provenance:
        raw = raw or {}
        return cls(
            input_artifacts=_as_tuple(raw.get("input_artifacts")),
            evidence_artifacts=_as_tuple(raw.get("evidence_artifacts")),
            inspected_paths=_as_tuple(raw.get("inspected_paths")),
            executed_commands=_as_tuple(raw.get("executed_commands")),
        )


@dataclass(frozen=True, slots=True)
class ReuseAssessment:
    confidence: float
    task_local_value: str | None = None
    cross_task_value: str | None = None
    cross_repository_value: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ReuseAssessment:
        if "confidence" not in raw:
            raise ValueError("reuse_assessment requires confidence")
        return cls(
            confidence=float(raw["confidence"]),
            task_local_value=raw.get("task_local_value"),
            cross_task_value=raw.get("cross_task_value"),
            cross_repository_value=raw.get("cross_repository_value"),
        )


@dataclass(frozen=True, slots=True)
class GeneratedDataAssessment:
    reusable_data_found: bool
    reason: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GeneratedDataAssessment:
        if "reusable_data_found" not in raw:
            raise ValueError("generated_data_assessment requires reusable_data_found")
        return cls(
            reusable_data_found=bool(raw["reusable_data_found"]),
            reason=raw.get("reason"),
        )


@dataclass(frozen=True, slots=True)
class SubagentDataPacket:
    """Canonical envelope emitted by every completed subagent action (law §9)."""

    schema_version: str
    packet_id: str
    identity: PacketIdentity
    primary_result: PrimaryResult
    reuse_assessment: ReuseAssessment
    generated_at: str
    generated_data_units: tuple[GeneratedDataUnit, ...] = ()
    unresolved_unknowns: tuple[UnresolvedUnknown, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)
    generated_data_assessment: GeneratedDataAssessment | None = None
    visibility: Visibility = Visibility.CAMPAIGN_LOCAL

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SubagentDataPacket:
        packet_id = str(raw.get("packet_id", "")).strip()
        if not packet_id:
            raise ValueError("packet requires packet_id")
        schema_version = str(raw.get("schema_version", "")).strip()
        if not schema_version:
            raise ValueError("packet requires schema_version")
        generated_at = str(raw.get("generated_at", "")).strip()
        if not generated_at:
            raise ValueError("packet requires generated_at")
        units = tuple(GeneratedDataUnit.from_dict(u) for u in raw.get("generated_data_units") or [])
        unknowns = tuple(
            UnresolvedUnknown.from_dict(u) for u in raw.get("unresolved_unknowns") or []
        )
        assessment_raw = raw.get("generated_data_assessment")
        assessment = GeneratedDataAssessment.from_dict(assessment_raw) if assessment_raw else None
        return cls(
            schema_version=schema_version,
            packet_id=packet_id,
            identity=PacketIdentity.from_dict(raw.get("identity") or {}),
            primary_result=PrimaryResult.from_dict(raw.get("primary_result") or {}),
            reuse_assessment=ReuseAssessment.from_dict(raw.get("reuse_assessment") or {}),
            generated_at=generated_at,
            generated_data_units=units,
            unresolved_unknowns=unknowns,
            provenance=Provenance.from_dict(raw.get("provenance")),
            generated_data_assessment=assessment,
            visibility=Visibility(raw.get("visibility", Visibility.CAMPAIGN_LOCAL)),
        )
