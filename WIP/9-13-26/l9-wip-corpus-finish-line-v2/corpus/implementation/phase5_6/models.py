"""Reference models for Phase 5–6. Stdlib-only, provider-neutral."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import StrEnum
from typing import Any

class Disposition(StrEnum):
    REQUIRED = "REQUIRED"
    SUPPORTING = "SUPPORTING"
    OPTIONAL = "OPTIONAL"
    CONFLICTING = "CONFLICTING"
    SUPERSEDED = "SUPERSEDED"
    EXCLUDED = "EXCLUDED"
    UNRESOLVED = "UNRESOLVED"

class PriorityClass(StrEnum):
    FOUNDATIONAL_UNLOCK = "FOUNDATIONAL_UNLOCK"
    QUICK_HIGH_LEVERAGE = "QUICK_HIGH_LEVERAGE"
    DEPENDENCY_REQUIRED = "DEPENDENCY_REQUIRED"
    READY_VALUE = "READY_VALUE"
    STRATEGIC_BET = "STRATEGIC_BET"
    WAITING = "WAITING"
    LOW_RETURN = "LOW_RETURN"
    OBSOLETE = "OBSOLETE"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class CandidateRecord:
    record_id: str
    entity_id: str
    title: str
    relation_to_task: str
    authority: int = 0
    relevance: int = 0
    dependency_necessity: int = 0
    evidence_quality: int = 0
    estimated_tokens: int = 0
    lifecycle: str = "active"
    supersedes: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ContextItem:
    record: CandidateRecord
    disposition: Disposition
    reason: str

@dataclass(frozen=True)
class WorkContextPacket:
    objective: str
    focal_entities: tuple[str, ...]
    items: tuple[ContextItem, ...]
    exclusions: tuple[ContextItem, ...]
    graph_snapshot_id: str
    budget_tokens: int
    used_tokens: int
    status: str = "READY"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class LeverageDimensions:
    dependency_centrality: int
    unblock_fanout: int
    capability_unlock: int
    reuse_potential: int
    strategic_alignment: int
    readiness: int
    effort: int
    risk: int
    unknown_burden: int

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not 0 <= value <= 5:
                raise ValueError(f"{name} must be 0..5")

@dataclass(frozen=True)
class WorkUnit:
    work_unit_id: str
    title: str
    objective: str
    artifact_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    capabilities_unlocked: tuple[str, ...] = ()
    completion_evidence: tuple[str, ...] = ()
    dimensions: LeverageDimensions | None = None
    priority_class: PriorityClass = PriorityClass.UNKNOWN

@dataclass(frozen=True)
class BuildWave:
    wave_id: str
    purpose: str
    work_unit_ids: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    expected_unlocks: tuple[str, ...] = ()

@dataclass(frozen=True)
class BuildWavePlan:
    objective: str
    waves: tuple[BuildWave, ...]
    deferred: tuple[str, ...]
    graph_snapshot_id: str
    reconsideration_triggers: tuple[str, ...] = ()
