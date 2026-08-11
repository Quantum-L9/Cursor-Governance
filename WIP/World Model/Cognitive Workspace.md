class AttentionTarget(BaseModel):
    ref_type: str
    ref_id: str

    salience: float
    reason: str


class OpenQuestion(BaseModel):
    question_id: str

    question: str

    importance: float
    uncertainty: float

    relevant_refs: tuple[EvidenceRef, ...]

    status: Literal[
        "open",
        "investigating",
        "resolved",
        "deferred",
    ]


class CognitiveDisagreement(BaseModel):
    disagreement_id: str

    result_ids: tuple[str, ...]

    proposition: str

    severity: float

    requires_adjudication: bool


class BudgetLedger(BaseModel):
    allocated_units: float
    consumed_units: float

    operator_calls_used: int
    simulations_used: int


class DecisionFrame(BaseModel):
    decision_id: str

    question: str

    decision_type: str

    candidate_refs: tuple[str, ...]

    constraints: tuple[str, ...]

    success_criteria: tuple[str, ...]

    state: Literal[
        "forming",
        "deliberating",
        "ready",
        "selected",
        "committed",
        "abandoned",
    ]


class CognitiveWorkspace(BaseModel):

    workspace_id: str
    revision: int

    objective_stack: tuple[str, ...]

    active_scope_ids: tuple[str, ...]

    world_snapshot_id: str
    world_revision: int

    # --------------------------------------------------
    # ATTENTION
    # --------------------------------------------------

    attention: tuple[AttentionTarget, ...]

    active_signal_ids: tuple[str, ...]

    # --------------------------------------------------
    # ACTIVE INTERPRETATION
    # --------------------------------------------------

    salient_fact_refs: tuple[str, ...]

    salient_entity_refs: tuple[str, ...]

    active_intent_refs: tuple[str, ...]

    active_conflict_refs: tuple[str, ...]

    active_promise_refs: tuple[str, ...]

    narrative_opportunity_refs: tuple[str, ...]

    # --------------------------------------------------
    # TEMPORARY THOUGHT
    # --------------------------------------------------

    hypotheses: tuple[dict[str, Any], ...]

    open_questions: tuple[OpenQuestion, ...]

    assumptions_under_test: tuple[dict[str, Any], ...]

    # --------------------------------------------------
    # CURRENT POSSIBILITIES
    # --------------------------------------------------

    proposal_refs: tuple[str, ...]

    branch_refs: tuple[str, ...]

    decision_frames: tuple[DecisionFrame, ...]

    # --------------------------------------------------
    # CROSS-COGNITIVE INTEGRATION
    # --------------------------------------------------

    cognitive_result_refs: tuple[str, ...]

    disagreements: tuple[CognitiveDisagreement, ...]

    pending_cognitive_requests: tuple[str, ...]

    # --------------------------------------------------
    # METACOGNITION
    # --------------------------------------------------

    current_reasoning_level: ReasoningLevel

    uncertainty: float

    confidence: float

    budget: BudgetLedger

    stopping_conditions: tuple[str, ...]

    # --------------------------------------------------
    # TRACEABILITY
    # --------------------------------------------------

    trace_id: str

    status: Literal[
        "active",
        "waiting",
        "ready_for_decision",
        "closed",
    ]
