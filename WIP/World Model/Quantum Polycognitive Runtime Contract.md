from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Protocol, Sequence
from pydantic import BaseModel, Field


# =====================================================================
# EXTERNAL WORLD MODEL TYPES
# =====================================================================
#
# These already belong to quantum.world and are referenced here.
#
# WorldCoordinate
# WorldSnapshot
# WorldEvent
# WorldEventDraft
# Branch
# WorldRuleViolation
#
# =====================================================================


# =====================================================================
# FUNDAMENTAL ENUMS
# =====================================================================

class CognitiveDomain(str, Enum):
    NARRATIVE = "narrative"
    CHARACTER = "character"
    EPISTEMIC = "epistemic"
    CINEMATIC = "cinematic"
    PERFORMANCE = "performance"
    ACOUSTIC = "acoustic"
    PRODUCTION = "production"
    QUALITY = "quality"
    META = "meta"


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
    STORYLINE = "storyline"
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


class CognitiveResultStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


class DecisionState(str, Enum):
    FORMING = "forming"
    DELIBERATING = "deliberating"
    SIMULATING = "simulating"
    READY = "ready"
    SELECTED = "selected"
    COMMITTED = "committed"
    ABANDONED = "abandoned"


class ProposalState(str, Enum):
    PROPOSED = "proposed"
    VALIDATING = "validating"
    SIMULATING = "simulating"
    VALID = "valid"
    INVALID = "invalid"
    SELECTED = "selected"
    REJECTED = "rejected"
    COMMITTED = "committed"
    STALE = "stale"


class SignalLifecycle(str, Enum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class DisagreementState(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ACCEPTED_UNCERTAINTY = "accepted_uncertainty"


class MergePolicy(str, Enum):
    APPEND = "append"
    REPLACE = "replace"
    UPSERT = "upsert"
    MAX = "max"
    MIN = "min"
    INCREMENT = "increment"
    REMOVE = "remove"


# =====================================================================
# GENERIC REFERENCES / EVIDENCE
# =====================================================================

class Ref(BaseModel):
    kind: str
    id: str
    version: str | None = None


class EvidenceRef(Ref):
    """
    Stable reference to evidence supporting a conclusion.
    """

    source: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class WorldRevisionRef(BaseModel):
    snapshot_id: str
    revision: int
    coordinate: WorldCoordinate
    state_hash: str


# =====================================================================
# AUTHORITY
# =====================================================================

class AuthorityEnvelope(BaseModel):
    """
    Hard capability boundary for cognition.

    Shared intelligence does NOT imply unrestricted mutation.
    """

    envelope_id: str

    granted_to: str

    allowed_domains: tuple[CognitiveDomain, ...]

    allowed_scope_kinds: tuple[ScopeKind, ...]

    allowed_read_planes: tuple[str, ...]
    allowed_write_domains: tuple[str, ...]

    allowed_operator_ids: tuple[str, ...] = ()

    protected_refs: tuple[Ref, ...] = ()

    maximum_authority_rank: int

    may_create_hypothetical_branches: bool = True

    may_propose_world_events: bool = False

    may_propose_canon_change: bool = False

    # Should effectively always remain False for cognition modules.
    may_commit_world_state: bool = False

    requires_escalation_above_rank: int | None = None

    expires_at: str | None = None


# =====================================================================
# COGNITIVE SCOPE
# =====================================================================

class CognitiveScope(BaseModel):
    """
    Defines what a cognitive operation is thinking about.

    Read scope may be much larger than write scope.
    """

    scope_id: str

    kind: ScopeKind
    parent_scope_id: str | None = None

    coordinate: WorldCoordinate

    universe_id: str
    continuity_id: str
    branch_id: str

    entity_refs: tuple[Ref, ...] = ()
    artifact_refs: tuple[Ref, ...] = ()

    read_planes: tuple[str, ...]
    write_domains: tuple[str, ...]

    isolation: IsolationMode

    # Semantic level above which this process cannot propose change.
    mutation_ceiling_rank: int

    # Used to detect incompatible concurrent operations.
    concurrency_keys: tuple[str, ...] = ()

    # Optional time span inside the world/story.
    start_coordinate: WorldCoordinate | None = None
    end_coordinate: WorldCoordinate | None = None


# =====================================================================
# WORLD SIGNAL
# =====================================================================

class SignalMetrics(BaseModel):
    severity: float = Field(ge=0.0, le=1.0)
    salience: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)

    estimated_downstream_impact: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )


class WorldSignal(BaseModel):
    """
    First-class nervous-system event.

    Examples:
        NARRATIVE.GOAL_BLOCKED
        EPISTEMIC.KNOWLEDGE_ASYMMETRY
        NARRATIVE.PROMISE_PAYOFF_READY
        CHARACTER.FALSE_BELIEF_ACTIVE
        QUALITY.CRITIC_DISAGREEMENT
        PRODUCTION.RENDER_FAILURE_CLUSTER
    """

    signal_id: str

    signal_type: str
    signal_version: str

    source_detector_id: str

    observed_at: WorldCoordinate

    scope: CognitiveScope

    subject_refs: tuple[Ref, ...]

    metrics: SignalMetrics

    payload: dict[str, Any]

    evidence_refs: tuple[EvidenceRef, ...]

    causal_parent_signal_ids: tuple[str, ...] = ()

    # Allows equivalent discoveries to collapse into one signal.
    deduplication_key: str | None = None

    lifecycle: SignalLifecycle = SignalLifecycle.ACTIVE

    suggested_operator_tags: tuple[str, ...] = ()

    expires_on_event_types: tuple[str, ...] = ()

    expires_at: WorldCoordinate | None = None

    created_at: str


# =====================================================================
# SIGNAL DETECTION / SIGNAL BUS
# =====================================================================

class WorldChangeSet(BaseModel):
    from_revision: int
    to_revision: int

    changed_entity_refs: tuple[Ref, ...]
    changed_state_addresses: tuple[str, ...]
    committed_event_refs: tuple[Ref, ...]


class WorldSignalDetectorSpec(BaseModel):
    detector_id: str
    version: str

    description: str

    subscribed_event_types: tuple[str, ...] = ()
    subscribed_state_paths: tuple[str, ...] = ()

    deterministic: bool

    output_signal_types: tuple[str, ...]


class WorldSignalDetector(Protocol):

    @property
    def spec(self) -> WorldSignalDetectorSpec:
        ...

    async def detect(
        self,
        previous: WorldSnapshot,
        current: WorldSnapshot,
        changes: WorldChangeSet,
    ) -> tuple[WorldSignal, ...]:
        ...


class SignalSubscription(BaseModel):
    subscription_id: str

    signal_types: tuple[str, ...]

    minimum_salience: float = 0.0
    minimum_confidence: float = 0.0

    scope_kinds: tuple[ScopeKind, ...] = ()


class WorldSignalBus(Protocol):
    """
    Transport/distribution mechanism.

    It does not decide what is important.
    Salience + Executive do that.
    """

    async def publish(
        self,
        signal: WorldSignal,
    ) -> None:
        ...

    async def publish_many(
        self,
        signals: Sequence[WorldSignal],
    ) -> None:
        ...

    async def subscribe(
        self,
        subscription: SignalSubscription,
        handler: Callable[[WorldSignal], Awaitable[None]],
    ) -> str:
        ...

    async def acknowledge(
        self,
        signal_id: str,
        consumer_id: str,
    ) -> None:
        ...


# =====================================================================
# ATTENTION / SALIENCE
# =====================================================================

class AttentionTarget(BaseModel):
    """
    Something Quantum should currently care about.
    """

    target_id: str

    ref: Ref

    scope_id: str

    salience: float = Field(ge=0.0, le=1.0)

    urgency: float = Field(ge=0.0, le=1.0)

    reason: str

    supporting_signal_ids: tuple[str, ...] = ()

    decay_rate: float = Field(default=0.0, ge=0.0)

    pinned: bool = False

    created_at: str


class SalienceContext(BaseModel):
    objective_refs: tuple[Ref, ...]

    current_scope: CognitiveScope

    active_signal_ids: tuple[str, ...]

    current_attention: tuple[AttentionTarget, ...]

    world_revision: int

    reasoning_level: ReasoningLevel


class SaliencePolicy(Protocol):
    """
    Determines what deserves attention.

    This policy can eventually be learned.
    """

    policy_id: str
    version: str

    async def score_signal(
        self,
        signal: WorldSignal,
        context: SalienceContext,
    ) -> float:
        ...

    async def rank_targets(
        self,
        candidates: Sequence[AttentionTarget],
        context: SalienceContext,
    ) -> tuple[AttentionTarget, ...]:
        ...

    async def decay(
        self,
        targets: Sequence[AttentionTarget],
        world_time_delta: float,
    ) -> tuple[AttentionTarget, ...]:
        ...


# =====================================================================
# REASONING BUDGET / POLICY
# =====================================================================

class ReasoningBudget(BaseModel):
    """
    Concrete meaning of "think harder".
    """

    level: ReasoningLevel

    max_operator_calls: int

    max_cross_domain_requests: int

    branch_width: int
    simulation_depth: int

    critic_count: int

    retrieval_token_budget: int

    max_parallel_cognitive_jobs: int

    compute_budget_units: float | None = None

    wall_clock_budget_ms: int | None = None

    allow_branch_simulation: bool = True
    allow_cross_domain_cognition: bool = True


class ReasoningPolicyContext(BaseModel):
    scope: CognitiveScope

    signal_ids: tuple[str, ...]

    uncertainty: float
    novelty: float
    irreversibility: float
    downstream_blast_radius: float
    critic_disagreement: float
    historical_failure_probability: float

    decision_type: str | None = None

    current_budget: ReasoningBudget | None = None


class ReasoningPolicyDecision(BaseModel):
    budget: ReasoningBudget

    rationale: str

    confidence: float

    policy_version: str


class ReasoningPolicy(Protocol):
    """
    Learns how much cognition a problem deserves.
    """

    policy_id: str
    version: str

    async def allocate(
        self,
        context: ReasoningPolicyContext,
    ) -> ReasoningPolicyDecision:
        ...


# =====================================================================
# REASONING OPERATORS
# =====================================================================

class ResourceProfile(BaseModel):
    expected_cost_class: str
    expected_latency_class: str

    parallelizable: bool = True
    cacheable: bool = True


class OperatorTrigger(BaseModel):
    signal_types_any: tuple[str, ...] = ()
    signal_types_all: tuple[str, ...] = ()

    minimum_salience: float = 0.0
    minimum_uncertainty: float = 0.0

    world_predicate_ids: tuple[str, ...] = ()


class ReasoningOperatorSpec(BaseModel):
    """
    A reusable cognitive primitive.

    Examples:
        narrative.blocked_intents
        narrative.promise_intersection
        epistemic.information_split
        character.policy_evaluation
    """

    operator_id: str
    version: str

    domain: CognitiveDomain

    description: str

    supported_scopes: tuple[ScopeKind, ...]

    minimum_reasoning_level: ReasoningLevel

    trigger: OperatorTrigger

    required_world_views: tuple[str, ...] = ()
    required_workspace_views: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()

    output_contract: str

    mandatory_when_triggered: bool = False

    side_effect_free: bool = True

    safety_or_correctness_critical: bool = False

    may_request_domains: tuple[CognitiveDomain, ...] = ()

    may_create_hypothetical_branch: bool = False

    resource_profile: ResourceProfile

    tags: tuple[str, ...] = ()


# =====================================================================
# COGNITIVE MODULE
# =====================================================================

class CognitiveModuleSpec(BaseModel):
    """
    Static declaration of one specialized cognitive faculty.
    """

    module_id: str
    version: str

    domain: CognitiveDomain

    description: str

    operators: tuple[ReasoningOperatorSpec, ...]

    signal_subscriptions: tuple[SignalSubscription, ...]

    supported_scopes: tuple[ScopeKind, ...]

    required_world_views: tuple[str, ...] = ()
    optional_world_views: tuple[str, ...] = ()

    memory_classes: tuple[str, ...] = ()

    authority_envelope_id: str

    stateless_between_invocations: bool = True

    supports_parallel_execution: bool = True

    deterministic_operators_possible: bool = True


# =====================================================================
# PROPOSALS / DECISIONS
# =====================================================================

class WorldRationale(BaseModel):
    supported_by_intent_refs: tuple[Ref, ...] = ()

    enabled_by_affordance_refs: tuple[Ref, ...] = ()

    conflict_refs: tuple[Ref, ...] = ()

    promise_refs: tuple[Ref, ...] = ()

    belief_refs: tuple[Ref, ...] = ()

    rule_refs: tuple[Ref, ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    explanation: str


class Proposal(BaseModel):
    """
    Candidate action or semantic decision.

    Proposal != commit.
    """

    proposal_id: str

    proposal_type: str

    created_by_result_id: str

    objective: str

    scope: CognitiveScope

    based_on_world_revision: int
    based_on_workspace_revision: int

    payload: dict[str, Any]

    rationale: WorldRationale | None = None

    precondition_refs: tuple[Ref, ...] = ()

    expected_effects: tuple[dict[str, Any], ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    required_authority_rank: int

    requires_simulation: bool = False

    estimated_blast_radius: float = 0.0
    estimated_irreversibility: float = 0.0

    confidence: float = Field(ge=0.0, le=1.0)

    state: ProposalState = ProposalState.PROPOSED


class DecisionCriterion(BaseModel):
    criterion_id: str
    description: str

    weight: float

    hard_constraint: bool = False

    minimum_score: float | None = None


class DecisionFrame(BaseModel):
    """
    Explicit cognitive problem Quantum is currently trying to solve.
    """

    decision_id: str

    question: str

    decision_type: str

    objective: str

    scope: CognitiveScope

    created_at_world_revision: int
    created_at_workspace_revision: int

    criteria: tuple[DecisionCriterion, ...]

    constraint_refs: tuple[Ref, ...] = ()

    candidate_proposal_ids: tuple[str, ...] = ()

    required_domains: tuple[CognitiveDomain, ...] = ()

    required_operator_ids: tuple[str, ...] = ()

    selected_proposal_id: str | None = None

    confidence: float = 0.0
    uncertainty: float = 1.0

    stopping_conditions: tuple[str, ...] = ()

    state: DecisionState = DecisionState.FORMING


# =====================================================================
# COGNITIVE DISAGREEMENT
# =====================================================================

class CognitiveClaim(BaseModel):
    result_id: str
    module_id: str

    claim: str

    confidence: float

    evidence_refs: tuple[EvidenceRef, ...]


class CognitiveDisagreement(BaseModel):
    disagreement_id: str

    scope: CognitiveScope

    subject: str

    claims: tuple[CognitiveClaim, ...]

    severity: float
    decision_impact: float

    requires_adjudication: bool = True

    state: DisagreementState = DisagreementState.OPEN

    resolution_result_id: str | None = None

    created_at: str


# =====================================================================
# COGNITIVE REQUEST / INVOCATION / RESULT
# =====================================================================

class CognitiveRequest(BaseModel):
    """
    One cognitive subsystem asking the Executive for another type
    of cognition.

    It does not directly spawn it.
    """

    request_id: str

    requested_domain: CognitiveDomain

    suggested_operator_id: str | None = None

    objective: str
    reason: str

    scope: CognitiveScope

    triggered_by_result_id: str | None = None
    triggered_by_signal_ids: tuple[str, ...] = ()

    urgency: float
    expected_value: float

    suggested_reasoning_level: ReasoningLevel | None = None

    evidence_refs: tuple[EvidenceRef, ...] = ()

    deduplication_key: str | None = None


class CognitiveInvocation(BaseModel):
    """
    Immutable execution request sent to a cognitive module.
    """

    invocation_id: str

    module_id: str
    module_version: str

    operator_id: str
    operator_version: str

    objective: str

    scope: CognitiveScope

    world_revision_ref: WorldRevisionRef

    workspace_id: str
    workspace_revision: int

    signal_ids: tuple[str, ...]

    context_view_ids: tuple[str, ...]

    reasoning_budget: ReasoningBudget

    authority: AuthorityEnvelope

    trace_id: str

    deterministic_seed: int | None = None

    deadline_at: str | None = None


class WorkspacePatchOperation(BaseModel):
    op: MergePolicy

    collection: str

    key: str | None = None

    value: Any | None = None


class WorkspacePatch(BaseModel):
    """
    Cognitive modules patch temporary thought.

    They never patch World Model state.
    """

    patch_id: str

    workspace_id: str
    based_on_revision: int

    operations: tuple[WorkspacePatchOperation, ...]

    created_by_result_id: str

    conflict_keys: tuple[str, ...] = ()

    created_at: str


class CognitiveResult(BaseModel):
    """
    Normalized output of every cognitive operation.
    """

    result_id: str

    invocation_id: str

    module_id: str
    operator_id: str

    status: CognitiveResultStatus

    based_on_world_revision: int
    based_on_workspace_revision: int

    observations: tuple[dict[str, Any], ...] = ()

    hypotheses: tuple[dict[str, Any], ...] = ()

    constraints: tuple[dict[str, Any], ...] = ()

    opportunity_refs: tuple[Ref, ...] = ()

    proposals: tuple[Proposal, ...] = ()

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    workspace_patch: WorkspacePatch | None = None

    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)

    reasoning_cost_units: float = 0.0
    latency_ms: int = 0

    created_at: str


class CognitiveContext(BaseModel):
    """
    Materialized runtime context supplied to a module.

    This is already filtered/projected for that module.
    """

    world_view: dict[str, Any]

    workspace_view: WorkspaceView

    memory_view: dict[str, Any] | None = None

    tool_handles: tuple[str, ...] = ()


class CognitiveModule(Protocol):

    @property
    def spec(self) -> CognitiveModuleSpec:
        ...

    async def execute(
        self,
        invocation: CognitiveInvocation,
        context: CognitiveContext,
    ) -> CognitiveResult:
        ...


# =====================================================================
# COGNITIVE WORKSPACE
# =====================================================================

class ObjectiveFrame(BaseModel):
    objective_id: str
    objective: str

    priority: float

    scope_id: str

    parent_objective_id: str | None = None

    status: str


class Hypothesis(BaseModel):
    hypothesis_id: str

    statement: str

    probability: float

    evidence_for: tuple[EvidenceRef, ...] = ()
    evidence_against: tuple[EvidenceRef, ...] = ()

    status: str = "active"


class OpenQuestion(BaseModel):
    question_id: str

    question: str

    importance: float
    uncertainty: float

    relevant_refs: tuple[EvidenceRef, ...] = ()

    status: str = "open"


class BudgetLedger(BaseModel):
    allocated_compute_units: float
    consumed_compute_units: float

    operator_calls_used: int
    simulations_used: int

    cognitive_jobs_started: int
    cognitive_jobs_completed: int


class StalenessRecord(BaseModel):
    result_id: str

    dependency_refs: tuple[Ref, ...]

    stale: bool

    changed_dependency_refs: tuple[Ref, ...] = ()


class CognitiveWorkspace(BaseModel):
    """
    Quantum's active working memory / global cognitive blackboard.

    EPHEMERAL and reconstructable.

    Not canonical fictional truth.
    """

    workspace_id: str
    revision: int

    world_revision_ref: WorldRevisionRef

    objective_stack: tuple[ObjectiveFrame, ...]

    active_scope_ids: tuple[str, ...]

    # ----------------------------
    # ATTENTION / NERVOUS SYSTEM
    # ----------------------------

    attention_targets: tuple[AttentionTarget, ...]

    active_signal_ids: tuple[str, ...]

    # ----------------------------
    # CURRENT SALIENT REALITY
    # ----------------------------

    salient_entity_refs: tuple[Ref, ...]
    salient_fact_refs: tuple[Ref, ...]

    active_intent_refs: tuple[Ref, ...]
    active_conflict_refs: tuple[Ref, ...]
    active_promise_refs: tuple[Ref, ...]

    narrative_opportunity_refs: tuple[Ref, ...]

    # ----------------------------
    # ACTIVE THOUGHT
    # ----------------------------

    hypotheses: tuple[Hypothesis, ...]

    open_questions: tuple[OpenQuestion, ...]

    assumptions_under_test: tuple[Hypothesis, ...]

    # ----------------------------
    # POSSIBILITIES / DECISIONS
    # ----------------------------

    proposal_ids: tuple[str, ...]

    branch_portfolio_ids: tuple[str, ...]

    decision_frames: tuple[DecisionFrame, ...]

    # ----------------------------
    # CROSS-COGNITIVE INTEGRATION
    # ----------------------------

    cognitive_result_ids: tuple[str, ...]

    disagreements: tuple[CognitiveDisagreement, ...]

    pending_cognitive_requests: tuple[CognitiveRequest, ...]

    # ----------------------------
    # VALIDITY
    # ----------------------------

    staleness_records: tuple[StalenessRecord, ...]

    # ----------------------------
    # METACOGNITION
    # ----------------------------

    current_reasoning_level: ReasoningLevel

    confidence: float
    uncertainty: float

    budget: BudgetLedger

    stopping_conditions: tuple[str, ...]

    # ----------------------------
    # TRACE
    # ----------------------------

    active_trace_ids: tuple[str, ...]

    status: str


class WorkspaceView(BaseModel):
    """
    Role/scope-specific projection of the Workspace.

    Cognitive modules should almost never receive the entire Workspace.
    """

    workspace_id: str
    workspace_revision: int

    scope: CognitiveScope

    objective_stack: tuple[ObjectiveFrame, ...]

    attention_targets: tuple[AttentionTarget, ...]

    signals: tuple[WorldSignal, ...]

    salient_entity_refs: tuple[Ref, ...]
    salient_fact_refs: tuple[Ref, ...]

    hypotheses: tuple[Hypothesis, ...]

    relevant_questions: tuple[OpenQuestion, ...]

    relevant_decisions: tuple[DecisionFrame, ...]

    relevant_result_ids: tuple[str, ...]

    relevant_disagreements: tuple[CognitiveDisagreement, ...]

    view_hash: str


class WorkspaceService(Protocol):

    async def get(
        self,
        workspace_id: str,
    ) -> CognitiveWorkspace:
        ...

    async def project(
        self,
        workspace_id: str,
        scope: CognitiveScope,
        module_spec: CognitiveModuleSpec,
    ) -> WorkspaceView:
        ...

    async def apply_patch(
        self,
        patch: WorkspacePatch,
    ) -> CognitiveWorkspace:
        ...

    async def mark_stale(
        self,
        changed_refs: Sequence[Ref],
    ) -> tuple[str, ...]:
        ...


# =====================================================================
# BRANCH PORTFOLIO / SIMULATION
# =====================================================================

class BranchScorecard(BaseModel):
    narrative_value: float = 0.0
    causal_strength: float = 0.0
    character_integrity: float = 0.0
    epistemic_quality: float = 0.0
    thematic_value: float = 0.0
    emotional_value: float = 0.0
    future_option_value: float = 0.0
    production_feasibility: float = 0.0

    rule_violations: int = 0

    confidence: float = 0.0


class BranchCandidate(BaseModel):
    branch_id: str

    originating_proposal_id: str

    base_world_revision: int

    depth_reached: int

    simulated_event_refs: tuple[Ref, ...]

    terminal_snapshot_ref: Ref | None = None

    scorecard: BranchScorecard | None = None

    uncertainty: float = 1.0

    pruned: bool = False
    prune_reason: str | None = None


class BranchPortfolio(BaseModel):
    """
    Active set of counterfactual futures for one decision.
    """

    portfolio_id: str

    decision_id: str

    base_world_revision: int
    base_branch_id: str

    candidates: tuple[BranchCandidate, ...]

    branch_width_limit: int
    simulation_depth_limit: int

    best_branch_id: str | None = None

    confidence_gap: float | None = None

    status: str

    created_at: str
    updated_at: str


class SimulationRequest(BaseModel):
    proposal: Proposal

    base_world_revision_ref: WorldRevisionRef

    depth: int

    width: int

    reasoning_budget: ReasoningBudget

    scope: CognitiveScope


class SimulationResult(BaseModel):
    branch: BranchCandidate

    generated_signals: tuple[WorldSignal, ...]

    predicted_quality: dict[str, float]

    created_at: str


class BranchSimulator(Protocol):
    """
    Counterfactual reality engine.

    Simulation never mutates canon.
    """

    async def simulate(
        self,
        request: SimulationRequest,
    ) -> SimulationResult:
        ...

    async def extend(
        self,
        branch_id: str,
        additional_depth: int,
        budget: ReasoningBudget,
    ) -> SimulationResult:
        ...

    async def compare(
        self,
        portfolio: BranchPortfolio,
    ) -> BranchPortfolio:
        ...


# =====================================================================
# ARBITRATION
# =====================================================================

class ArbitrationRequest(BaseModel):
    decision: DecisionFrame

    proposals: tuple[Proposal, ...]

    branch_portfolio: BranchPortfolio | None

    disagreements: tuple[CognitiveDisagreement, ...]

    workspace_view: WorkspaceView

    reasoning_budget: ReasoningBudget


class ArbitrationResult(BaseModel):
    arbitration_id: str

    decision_id: str

    selected_proposal_id: str | None

    rejected_proposal_ids: tuple[str, ...]

    requires_more_cognition: bool

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    confidence: float
    uncertainty: float

    rationale: str

    evidence_refs: tuple[EvidenceRef, ...]


class CognitiveArbitrator(Protocol):
    """
    Decides between competing cognitive conclusions/proposals.

    It is distinct from QC:
      arbitration = "which option?"
      QC          = "is this option good enough?"
    """

    async def arbitrate(
        self,
        request: ArbitrationRequest,
    ) -> ArbitrationResult:
        ...


# =====================================================================
# COGNITIVE EXECUTIVE
# =====================================================================

class ExecutiveInput(BaseModel):
    workspace_id: str

    new_signal_ids: tuple[str, ...] = ()

    completed_result_ids: tuple[str, ...] = ()

    completed_simulation_ids: tuple[str, ...] = ()

    world_revision_ref: WorldRevisionRef

    reason: str


class PlannedInvocation(BaseModel):
    invocation: CognitiveInvocation

    priority: float

    dependencies: tuple[str, ...] = ()

    may_run_parallel: bool = True


class ExecutivePlan(BaseModel):
    plan_id: str

    workspace_id: str

    reasoning_policy_decision: ReasoningPolicyDecision

    planned_invocations: tuple[PlannedInvocation, ...]

    simulation_requests: tuple[SimulationRequest, ...]

    cognitive_requests_deferred: tuple[str, ...]

    cognitive_requests_rejected: tuple[str, ...]

    ready_for_arbitration: tuple[str, ...]

    ready_for_commit_validation: tuple[str, ...]

    rationale: str


class CognitiveExecutive(Protocol):
    """
    Executive function of Quantum.

    Owns:
        attention
        reasoning depth
        cognitive activation
        escalation
        stopping
        metacognition

    Does NOT:
        render
        write canonical world state
        schedule GPU workers directly
    """

    async def plan(
        self,
        input: ExecutiveInput,
    ) -> ExecutivePlan:
        ...

    async def integrate_result(
        self,
        result: CognitiveResult,
    ) -> WorkspacePatch:
        ...

    async def evaluate_cognitive_request(
        self,
        request: CognitiveRequest,
        workspace: CognitiveWorkspace,
    ) -> bool:
        ...

    async def should_continue_reasoning(
        self,
        decision: DecisionFrame,
        workspace: CognitiveWorkspace,
    ) -> bool:
        ...

    async def escalate_reasoning(
        self,
        decision: DecisionFrame,
        reason: str,
    ) -> ReasoningBudget:
        ...


# =====================================================================
# EXECUTION ORCHESTRATOR
# =====================================================================

class ExecutionHandle(BaseModel):
    execution_id: str

    invocation_id: str

    state: str

    worker_id: str | None = None

    started_at: str | None = None
    completed_at: str | None = None


class ExecutionBatchResult(BaseModel):
    handles: tuple[ExecutionHandle, ...]

    results: tuple[CognitiveResult, ...]

    failed_invocation_ids: tuple[str, ...]


class ExecutionOrchestrator(Protocol):
    """
    Systems/runtime layer.

    Executive says WHAT should execute.
    Orchestrator makes execution happen.
    """

    async def execute(
        self,
        invocation: CognitiveInvocation,
    ) -> CognitiveResult:
        ...

    async def execute_batch(
        self,
        invocations: Sequence[CognitiveInvocation],
    ) -> ExecutionBatchResult:
        ...

    async def cancel(
        self,
        execution_id: str,
    ) -> None:
        ...

    async def status(
        self,
        execution_id: str,
    ) -> ExecutionHandle:
        ...


# =====================================================================
# COMMIT MANAGER
# =====================================================================

class CommitRequest(BaseModel):
    proposal: Proposal

    selected_by_arbitration_id: str

    expected_world_revision: int

    authority: AuthorityEnvelope

    qc_certification_ref: Ref

    trace_id: str


class CommitValidation(BaseModel):
    valid: bool

    current_world_revision: int

    stale: bool

    authority_valid: bool

    preconditions_valid: bool

    rules_valid: bool

    qc_valid: bool

    violations: tuple[dict[str, Any], ...]

    requires_rebase: bool


class CommitReceipt(BaseModel):
    commit_id: str

    proposal_id: str

    world_event_refs: tuple[Ref, ...]

    previous_world_revision: int
    new_world_revision: int

    new_snapshot_ref: Ref

    emitted_signal_ids: tuple[str, ...]

    commit_hash: str

    committed_at: str


class CommitManager(Protocol):
    """
    ONLY normal gateway from cognition into canonical World State.
    """

    async def validate(
        self,
        request: CommitRequest,
    ) -> CommitValidation:
        ...

    async def rebase(
        self,
        proposal: Proposal,
        onto_world_revision: int,
    ) -> Proposal:
        ...

    async def commit(
        self,
        request: CommitRequest,
    ) -> CommitReceipt:
        ...


# =====================================================================
# COGNITIVE TRACE / LEARNING
# =====================================================================

class CognitiveTrace(BaseModel):
    """
    Complete provenance of how Quantum reached a decision.
    """

    trace_id: str

    originating_signal_ids: tuple[str, ...]

    initial_world_revision: int

    scope: CognitiveScope

    decision_ids: tuple[str, ...]

    invocation_ids: tuple[str, ...]

    operator_ids: tuple[str, ...]

    cognitive_result_ids: tuple[str, ...]

    branch_portfolio_ids: tuple[str, ...]

    proposal_ids: tuple[str, ...]

    selected_proposal_id: str | None = None

    arbitration_ids: tuple[str, ...] = ()

    commit_id: str | None = None

    total_reasoning_cost: float = 0.0
    total_latency_ms: int = 0

    downstream_quality: dict[str, float] = {}

    repair_count: int = 0
    downstream_invalidation_cost: float = 0.0

    final_reward: float | None = None

    created_at: str
    closed_at: str | None = None


class OperatorExperience(BaseModel):
    """
    Learning record answering:

        Under conditions X,
        operator O was used,
        costing C,
        and produced eventual value V.
    """

    experience_id: str

    trace_id: str

    invocation_id: str

    operator_id: str
    operator_version: str

    domain: CognitiveDomain

    signal_types: tuple[str, ...]

    scope_kind: ScopeKind

    decision_type: str | None

    world_feature_fingerprint: str

    reasoning_level: ReasoningLevel

    prior_uncertainty: float
    posterior_uncertainty: float

    direct_quality_delta: float | None = None

    downstream_quality_delta: float | None = None

    failure_probability_delta: float | None = None

    repair_cost_avoided: float | None = None

    future_option_value: float | None = None

    reasoning_cost: float
    latency_ms: int

    was_selected_by_policy: bool

    was_shadow_execution: bool = False

    counterfactual_baseline_ref: Ref | None = None

    estimated_marginal_utility: float | None = None

    final_reward: float | None = None

    created_at: str


# =====================================================================
# OPERATOR SELECTION LEARNING
# =====================================================================

class OperatorSelectionContext(BaseModel):
    signal_types: tuple[str, ...]

    scope_kind: ScopeKind

    decision_type: str | None

    salient_entity_types: tuple[str, ...]

    uncertainty: float
    novelty: float
    blast_radius: float
    irreversibility: float

    current_reasoning_level: ReasoningLevel

    already_invoked_operator_ids: tuple[str, ...]

    world_feature_fingerprint: str

    workspace_feature_fingerprint: str


class OperatorUtilityPrediction(BaseModel):
    operator_id: str

    expected_quality_delta: float

    expected_failure_risk_reduction: float

    expected_repair_cost_avoided: float

    expected_future_option_value: float

    expected_reasoning_cost: float
    expected_latency_ms: int

    expected_utility: float

    confidence: float


class OperatorSelectionPolicy(Protocol):
    """
    Learns which OPTIONAL reasoning operators are worth invoking
    under a particular world-state / signal constellation.

    Hard correctness operators are outside learned control.
    """

    policy_id: str
    version: str

    async def rank(
        self,
        context: OperatorSelectionContext,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[OperatorUtilityPrediction, ...]:
        ...

    async def record_experience(
        self,
        experience: OperatorExperience,
    ) -> None:
        ...

    async def should_explore(
        self,
        context: OperatorSelectionContext,
    ) -> bool:
        ...

    async def select_shadow_operator(
        self,
        context: OperatorSelectionContext,
        candidate_operator_ids: Sequence[str],
    ) -> str | None:
        ...
