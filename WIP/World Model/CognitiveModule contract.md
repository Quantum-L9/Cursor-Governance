from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class CognitiveDomain(str, Enum):
    NARRATIVE = "narrative"
    CHARACTER = "character"
    EPISTEMIC = "epistemic"
    CINEMATIC = "cinematic"
    PERFORMANCE = "performance"
    ACOUSTIC = "acoustic"
    PRODUCTION = "production"
    QUALITY = "quality"


class ReasoningLevel(str, Enum):
    REFLEX = "reflex"
    ROUTINE = "routine"
    DELIBERATIVE = "deliberative"
    STRATEGIC = "strategic"


class ScopeKind(str, Enum):
    UNIVERSE = "universe"
    SERIES = "series"
    SEASON = "season"
    EPISODE = "episode"
    SEQUENCE = "sequence"
    SCENE = "scene"
    SHOT = "shot"
    FRAME = "frame"

    PRODUCTION = "production"
    ARTIFACT = "artifact"


class IsolationMode(str, Enum):
    SNAPSHOT_READ = "snapshot_read"
    HYPOTHETICAL_BRANCH = "hypothetical_branch"
    CANONICAL_PROPOSAL = "canonical_proposal"


# ============================================================
# COGNITIVE SCOPE
# ============================================================

class CognitiveScope(BaseModel):
    scope_id: str
    kind: ScopeKind

    parent_scope_id: str | None = None

    universe_id: str
    continuity_id: str
    branch_id: str

    world_coordinate: WorldCoordinate

    entity_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()

    read_planes: tuple[str, ...]
    write_domains: tuple[str, ...]

    isolation: IsolationMode

    # Maximum semantic blast radius this cognition is allowed
    # to propose changing.
    mutation_ceiling: str

    # Useful for concurrency / conflict detection.
    concurrency_keys: tuple[str, ...] = ()


# ============================================================
# OPERATOR SPEC
# ============================================================

class OperatorTrigger(BaseModel):
    signal_types: tuple[str, ...] = ()

    requires_any: tuple[str, ...] = ()
    requires_all: tuple[str, ...] = ()

    minimum_salience: float = 0.0
    minimum_uncertainty: float = 0.0


class ResourceProfile(BaseModel):
    expected_cost_class: Literal[
        "tiny",
        "low",
        "medium",
        "high",
        "very_high",
    ]

    expected_latency_class: Literal[
        "instant",
        "short",
        "medium",
        "long",
    ]

    parallelizable: bool = True


class ReasoningOperatorSpec(BaseModel):
    operator_id: str
    version: str

    description: str

    domain: CognitiveDomain

    supported_scopes: tuple[ScopeKind, ...]

    minimum_reasoning_level: ReasoningLevel

    trigger: OperatorTrigger

    required_context_views: tuple[str, ...]

    output_schema: str

    side_effect_free: bool = True

    mandatory_when_triggered: bool = False

    safety_critical: bool = False

    may_request_cognition_from: tuple[CognitiveDomain, ...] = ()

    resource_profile: ResourceProfile


# ============================================================
# SIGNAL SUBSCRIPTION
# ============================================================

class SignalSubscription(BaseModel):
    signal_type: str

    minimum_salience: float = 0.0
    minimum_confidence: float = 0.0

    eligible_operators: tuple[str, ...]


# ============================================================
# MODULE SPECIFICATION
# ============================================================

class CognitiveModuleSpec(BaseModel):
    module_id: str
    version: str

    domain: CognitiveDomain

    description: str

    operators: tuple[ReasoningOperatorSpec, ...]

    subscriptions: tuple[SignalSubscription, ...]

    supported_scopes: tuple[ScopeKind, ...]

    # Modules don't receive arbitrary World Model data.
    required_world_views: tuple[str, ...] = ()
    optional_world_views: tuple[str, ...] = ()

    memory_classes: tuple[str, ...] = ()

    authority_envelope_id: str

    deterministic_possible: bool = False

    supports_parallel_execution: bool = True

    stateless_between_invocations: bool = True
