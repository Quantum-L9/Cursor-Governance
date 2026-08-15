I built this as a Program Execution Blueprint v2 overlay for an instantiated Cursor-Governance Program Execution pair. It operationalizes the remediation we identified in the uploaded l9-devpack-compiler v1.2.0: authority-order correction, provenance-backed defaults, honest proof semantics, scoped Unknowns, and a first-class Program Execution v2 projection. gitingest_l9_devpack_compiler_v1_2_0.md

The pack follows the current Blueprint’s canonical authority order and immutable Blueprint→Controller boundary, and keeps all repo-mutating tasks at local_write: true with commit/push/PR/merge/release/deploy all false. 

One blocker is intentional: the uploaded artifact doesn’t establish the actual mutable git repository/base SHA. UNK-001 makes W1+ mutation wait until the Controller binds repository_id=l9-devpack-compiler to an exact base SHA. That’s the right place for that fact because repository HEAD/runtime state belongs to the Controller, not the Blueprint. 

Program Execution overlay

Copy each # FILE: section into the instantiated Blueprint directory.

# =====================================================================
# FILE: PROGRAM.yaml
# =====================================================================
schema: program-execution-blueprint.program.v2
schema_version: 2.0.0
program:
  id: l9-devpack-program-execution-hardening
  name: L9 Devpack Compiler Program Execution v2 Hardening
  version: 1.0.0
  owner: igor_beylin
  definition_status: accepted
  snapshot_at: "2026-08-10"
  objective: >
    Make l9-devpack-compiler a provenance-safe compiler and intermediate
    representation that emits Program Execution Blueprint v2 authority
    without becoming a competing runtime authority.
  problem_statement: >
    l9-devpack-compiler v1.2.0 contains an authority-order mismatch with
    Program Execution v2, implicit ownership and rollback defaulting that
    can create authority without provenance, structural readiness checks
    that can overstate runtime operability, globally oriented Unknown/STOP
    semantics, and no lossless Program Execution v2 projection carrying
    provenance, authorization ceilings, scoped blockers, and independent
    verification obligations.
  target_state: >
    The compiler owns evidence extraction, DPK intermediate representation,
    structural compile-readiness, and versioned Blueprint generation only.
    Program Execution Blueprint owns design-time execution authority and the
    Controller exclusively owns runtime state, exact repository bindings,
    attempts, verification, recovery, and gate evaluation. Task Contracts
    narrow authority and never override accepted architecture or contracts.
    Defaults affecting authority require explicit provenance. Structural
    validation never claims runtime proof. A program-execution-v2 compile
    target emits a validator-clean Blueprint source set.
  scope:
    include:
      - l9-devpack-compiler SKILL.md and expertise/intelligence model
      - DPK authority-order and layer contracts
      - execution-package and quality-gate semantics
      - validate_devpack.py scoring and proof semantics
      - build-spec schema where generally applicable
      - versioned Program Execution v2 projection adapter
      - projection schema, emitter, fixtures, negative tests, and documentation
      - backward-compatibility tests for non-Program-Execution consumers
    exclude:
      - modifications to Cursor-Governance Program Execution core
      - creation of a second runtime controller or runtime state store
      - remote repository mutation
      - merge, release, or deployment
      - credential values or persistent remote credentials
      - weakening DPK red-lines or existing tests merely to pass validation
  contracts:
    blueprint: program-execution-blueprint.v2
    controller_minimum: program-execution-controller.v2
    pair: program-execution-system.v2
  authority_order:
    - applicable_safety_legal_security_requirements
    - latest_accepted_program_decision
    - accepted_architecture_and_contracts
    - verified_current_state_evidence
    - approved_task_card
    - implementation
    - documentation
    - historical_material
    - UNKNOWN
  operating_rules:
    - one_authority_per_responsibility
    - controller_may_narrow_never_widen
    - unknown_blocks_only_named_dependencies
    - promotion_requires_evidence_backed_gates
    - no_silent_scope_expansion
    - no_irreversible_action_without_exact_authority
    - worker_claim_is_not_verification
    - compiler_output_must_not_create_runtime_authority
    - policy_derived_defaults_require_provenance
    - structural_readiness_is_not_runtime_operability
  terminal_verdicts:
    - CONVERGED
    - CONVERGED_WITH_NON_BLOCKING_RISKS
    - NOT_CONVERGED
    - INCONCLUSIVE
# =====================================================================
# FILE: EXECUTION_INDEX.yaml
# =====================================================================
schema: program-execution-blueprint.index.v2
schema_version: 2.0.0
blueprint_contract: program-execution-blueprint.v2
required_sources:
  - PROGRAM.yaml
  - EXECUTION_TARGETS.yaml
  - AUTHORITY_REGISTRY.yaml
  - DECISION_REGISTER.yaml
  - UNKNOWN_REGISTER.yaml
  - RISK_REGISTER.yaml
  - WAIVER_REGISTER.yaml
  - EVIDENCE_CATALOG.yaml
  - DO_NOT_BUILD.yaml
  - CURRENT_STATE_DELTA.yaml
  - WORKSTREAMS.yaml
  - DEPENDENCY_GRAPH.yaml
  - EXECUTION_WAVES.yaml
  - TASK_CARDS.yaml
  - CONVERGENCE_GATES.yaml
  - OBSERVABILITY_PLAN.yaml
  - CUTOVER_AND_ROLLBACK.yaml
  - SOURCE_TRACEABILITY.yaml
canonical_owners:
  task_dependencies: DEPENDENCY_GRAPH.yaml
  wave_dependencies: EXECUTION_WAVES.yaml
  gate_definitions: CONVERGENCE_GATES.yaml
  runtime_gate_results: Program Execution Controller
  task_definition_state: TASK_CARDS.yaml
  task_runtime_state: Program Execution Controller
  final_program_verdict: program_owner_acceptance
controller_import:
  immutable: true
  digest_algorithm: sha256
  unknown_contract: reject
  source_change: mark_runtime_stale
# =====================================================================
# FILE: EXECUTION_TARGETS.yaml
# =====================================================================
schema: program-execution-blueprint.execution-targets.v2
schema_version: 2.0.0
targets:
  - id: TARGET-001
    name: l9-devpack-compiler
    kind: git_repository
    authority_owner: igor_beylin
    execution_mode: repo_local
    repository_id: l9-devpack-compiler
    source_of_truth: >
      Program Execution Controller repository registration for
      repository_id=l9-devpack-compiler
    environments:
      - local
    mutability: reversible
    expected_revision: controller_binds_exact_base_sha_at_program_lock
    adapter: git
# =====================================================================
# FILE: AUTHORITY_REGISTRY.yaml
# =====================================================================
schema: program-execution-blueprint.authority-registry.v2
schema_version: 2.0.0
policy:
  one_owner_per_responsibility: true
  projection_does_not_transfer_authority: true
  unresolved_conflict_result: BLOCKED
responsibilities:
  - id: AUTH-001
    responsibility: >
      DPK compiler role boundary between repository compilation,
      design-time projection, and Program Execution runtime authority
    owner_target_id: TARGET-001
    source_of_truth: SKILL.md
    consumers:
      - DPK compiler workflow
      - Program Execution v2 projection
      - execution-package generation
    allowed_roles:
      - authority
      - projection
    prohibited_owner_target_ids: []
    enforcement:
      - SKILL.md states that DPK compiles authority but does not own runtime state
      - Program Execution adapter emits Blueprint definitions only
      - tests reject generation of Controller runtime state or receipts
    validation_gate_ids:
      - GATE-002
      - GATE-004
    definition_status: active
  - id: AUTH-002
    responsibility: >
      DPK authority precedence and Task Contract narrowing semantics
    owner_target_id: TARGET-001
    source_of_truth: references/dpk-layer-contract.md
    consumers:
      - SKILL.md
      - expertise_model.yaml
      - skill_intelligence_report.yaml
      - Program Execution projection
    allowed_roles:
      - authority
      - projection
    prohibited_owner_target_ids: []
    enforcement:
      - accepted architecture and contracts outrank approved task scope
      - Task Contracts may narrow but never widen upstream authority
      - tests reject legacy Task-Contract-over-architecture precedence
    validation_gate_ids:
      - GATE-002
    definition_status: active
  - id: AUTH-003
    responsibility: >
      Provenance requirements for ownership, rollback, and other policy-derived defaults
    owner_target_id: TARGET-001
    source_of_truth: references/quality-gates.md
    consumers:
      - scripts/validate_devpack.py
      - compiler envelope emission
      - Program Execution projection
    allowed_roles:
      - authority
      - projection
    prohibited_owner_target_ids: []
    enforcement:
      - no missing authority fact becomes passing solely through an implicit default
      - policy-derived values identify their governing source
      - Program Execution target operates fail-closed when provenance is absent
    validation_gate_ids:
      - GATE-002
    definition_status: active
  - id: AUTH-004
    responsibility: >
      Meaning and evidence boundary of validate_devpack structural readiness results
    owner_target_id: TARGET-001
    source_of_truth: scripts/validate_devpack.py
    consumers:
      - references/quality-gates.md
      - compiler package mode
      - CI consumers
    allowed_roles:
      - authority
      - projection
    prohibited_owner_target_ids: []
    enforcement:
      - structural presence cannot be represented as executed runtime proof
      - test and rollback execution state is explicit
      - validator output declares its evidence scope
    validation_gate_ids:
      - GATE-003
    definition_status: active
  - id: AUTH-005
    responsibility: >
      Program Execution Blueprint v2 projection contract and emitter
    owner_target_id: TARGET-001
    source_of_truth: references/program-execution-v2-projection.md
    consumers:
      - scripts/emit_program_execution_v2.py
      - schemas/program-execution-v2-target.schema.json
      - Program Execution Blueprint v2
    allowed_roles:
      - authority
      - projection
    prohibited_owner_target_ids: []
    enforcement:
      - emitted sources conform to program-execution-blueprint.v2
      - provenance is retained from input facts to emitted authority
      - every emitted Task Card has the exact canonical authorization ceiling
      - no runtime state or gate result is emitted
    validation_gate_ids:
      - GATE-004
    definition_status: active
# =====================================================================
# FILE: DECISION_REGISTER.yaml
# =====================================================================
schema: program-execution-blueprint.decision-register.v2
schema_version: 2.0.0
policy: No blocked decision may be silently defaulted.
decisions:
  - id: DEC-001
    question: What role does DPK own relative to Program Execution?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          DPK is an upstream compiler/IR and Program Execution owns
          executable design-time authority and runtime execution.
        benefits:
          - single runtime authority
          - clean compiler boundary
          - deterministic handoff
        risks:
          - requires terminology and contract changes
      - id: B
        description: DPK remains an independent execution control plane.
        benefits:
          - fewer immediate code changes
        risks:
          - duplicate authority
          - ambiguous runtime ownership
    selected_option: A
    rationale: >
      A single runtime authority prevents DPK and the Program Execution
      Controller from competing for execution state and proof ownership.
    evidence_ids:
      - EVID-001
      - EVID-003
    blocks: []
    required_by: before W1
    supersedes: null
  - id: DEC-002
    question: What authority order governs Program Execution-targeted DPK output?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          Use Program Execution v2 precedence and treat a Task Contract
          as a narrowing approved task definition below accepted architecture
          and contracts.
        benefits:
          - no downstream authority widening
          - direct Program Execution compatibility
        risks:
          - changes existing DPK precedence wording
      - id: B
        description: Keep explicit Task Contract above architecture and public contracts.
        benefits:
          - preserves v1.2 wording
        risks:
          - permits downstream scope to override upstream authority
    selected_option: A
    rationale: >
      Program Execution v2 explicitly forbids a downstream artifact from
      widening or overriding upstream authority.
    evidence_ids:
      - EVID-001
      - EVID-002
      - EVID-003
    blocks: []
    required_by: before TASK-002
    supersedes: null
  - id: DEC-003
    question: How may missing ownership or rollback facts be defaulted?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          A default may be derived only from an explicit governing policy
          with recorded provenance; otherwise the fact remains Unknown or fails.
        benefits:
          - prevents invented authority
          - preserves auditability
          - supports organizational policy safely
        risks:
          - stricter configuration requirements
      - id: B
        description: Continue unconditional quantum-ai and library rollback autofix.
        benefits:
          - lower operator friction
        risks:
          - implicit authority creation
          - false readiness
    selected_option: A
    rationale: >
      A value is safe to derive only when its authority source is itself explicit.
    evidence_ids:
      - EVID-001
      - EVID-003
    blocks: []
    required_by: before TASK-003
    supersedes: null
  - id: DEC-004
    question: What may validate_devpack claim from structural inspection alone?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          Claim structural compile-readiness only; runtime operability,
          executed tests, and rollback proof require independent evidence.
        benefits:
          - honest proof semantics
          - compatible with Controller verification model
        risks:
          - downstream callers may need output migration
      - id: B
        description: Preserve operable/conditional labels from artifact presence.
        benefits:
          - backward-compatible labels
        risks:
          - presence can be mistaken for proof
    selected_option: A
    rationale: >
      File existence cannot prove command success, rollback dry-run success,
      or runtime behavior.
    evidence_ids:
      - EVID-001
      - EVID-003
      - EVID-004
    blocks: []
    required_by: before TASK-004
    supersedes: null
  - id: DEC-005
    question: How should Unknowns block Program Execution-targeted work?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: Unknowns block only explicitly named dependent tasks.
        benefits:
          - preserves safe parallel progress
          - matches Program Execution v2
        risks:
          - requires dependency-aware projection
      - id: B
        description: Any required Unknown stops the whole execution package.
        benefits:
          - simpler implementation
        risks:
          - unnecessary global blocking
    selected_option: A
    rationale: >
      Fail-closed behavior should stop the work that depends on the missing
      fact without blocking unrelated safe work.
    evidence_ids:
      - EVID-001
      - EVID-002
    blocks: []
    required_by: before TASK-006
    supersedes: null
  - id: DEC-006
    question: How should DPK feed Program Execution v2?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          Emit the complete Blueprint v2 indexed authority source set with
          provenance edges, scoped blockers, gates, and authorization ceilings.
        benefits:
          - lossless Program Execution ingestion
          - Controller can import immutable Blueprint authority directly
        risks:
          - larger projection surface
      - id: B
        description: Emit only an ad-hoc execution-package handoff file.
        benefits:
          - smaller implementation
        risks:
          - lossy authority mapping
          - Controller-specific interpretation required
    selected_option: A
    rationale: >
      The Blueprint is the canonical design-time authority contract and should
      be generated directly rather than reconstructed by the Controller.
    evidence_ids:
      - EVID-002
      - EVID-003
      - EVID-004
    blocks: []
    required_by: before W2
    supersedes: null
  - id: DEC-007
    question: Where should Program Execution-specific projection fields live?
    status: accepted
    owner: igor_beylin
    options:
      - id: A
        description: >
          Keep the generic DPK IR stable and add a versioned
          program-execution-v2 target overlay, promoting only generally useful
          provenance concepts into the core spec.
        benefits:
          - preserves non-Program-Execution consumers
          - clean adapter architecture
          - independent versioning
        risks:
          - requires an additional target schema
      - id: B
        description: Add all Program Execution-specific fields directly to the core DPK spec.
        benefits:
          - single schema
        risks:
          - couples generic DPK semantics to one execution system
    selected_option: A
    rationale: >
      Program Execution is a compile target. Target-specific authority fields
      should not distort the generic repository-operability IR.
    evidence_ids:
      - EVID-001
      - EVID-002
    blocks: []
    required_by: before TASK-005
    supersedes: null
# =====================================================================
# FILE: UNKNOWN_REGISTER.yaml
# =====================================================================
schema: program-execution-blueprint.unknown-register.v2
schema_version: 2.0.0
policy: Unknowns remain explicit and block only named dependent work.
unknowns:
  - id: UNK-001
    topic: >
      Exact Controller repository registration, base SHA, and clean working-tree
      state for repository_id=l9-devpack-compiler at execution start.
    owner: igor_beylin
    blocks:
      - TASK-002
      - TASK-003
      - TASK-004
      - TASK-005
      - TASK-006
      - TASK-007
    safe_state: >
      Permit W0 inspection only. Do not authorize repository local_write
      until the Controller binds the exact target state.
    resolution_requirements:
      - Controller resolves repository_id=l9-devpack-compiler to one local git target
      - Controller records the exact base SHA in Program Lock/runtime evidence
      - working tree is clean or pre-existing changes are explicitly excluded
      - target files described by EVID-001 are reconciled against the bound repository
    resolution_evidence_ids: []
    status: open
    resolved_at: null
# =====================================================================
# FILE: RISK_REGISTER.yaml
# =====================================================================
schema: program-execution-blueprint.risk-register.v2
schema_version: 2.0.0
risks:
  - id: RISK-001
    risk: >
      The new DPK integration accidentally creates a second runtime authority
      beside the Program Execution Controller.
    severity: critical
    likelihood: low
    owner: igor_beylin
    trigger: >
      DPK code begins owning mutable task state, runtime gate results,
      leases, attempts, approvals, or Controller receipts.
    preventive_controls:
      - AUTH-001 role boundary
      - DNB-001 prohibition
      - Program Execution projection emits definitions only
    contingency:
      - reject GATE-004
      - revert runtime-ownership additions
    related_tasks:
      - TASK-005
      - TASK-006
    related_gates:
      - GATE-004
    acceptance_decision_id: null
    status: open
  - id: RISK-002
    risk: >
      Authority-order and validator changes break existing non-Program-Execution
      DPK consumers.
    severity: high
    likelihood: medium
    owner: igor_beylin
    trigger: Existing supported fixtures or public CLI behavior regress unexpectedly.
    preventive_controls:
      - version Program Execution integration as an explicit target adapter
      - maintain regression fixtures for existing DPK modes
      - document any intentionally superseded output semantics
    contingency:
      - retain compatibility adapter for legacy structural output
      - narrow changes to the Program Execution target where possible
    related_tasks:
      - TASK-002
      - TASK-003
      - TASK-004
      - TASK-005
      - TASK-006
      - TASK-007
    related_gates:
      - GATE-002
      - GATE-003
      - GATE-005
    acceptance_decision_id: null
    status: open
  - id: RISK-003
    risk: Structural validator output continues to be interpreted as runtime proof.
    severity: high
    likelihood: medium
    owner: igor_beylin
    trigger: >
      A score receives full credit for unexecuted tests, rollback, reproducibility,
      architecture alignment, or operational behavior.
    preventive_controls:
      - DEC-004
      - explicit evidence scope in validator output
      - negative fixtures proving presence is not execution
    contingency:
      - block GATE-003
      - restore prior code and redesign result schema
    related_tasks:
      - TASK-004
      - TASK-007
    related_gates:
      - GATE-003
      - GATE-005
    acceptance_decision_id: null
    status: open
  - id: RISK-004
    risk: >
      Missing ownership or rollback facts regain a passing status through
      an undocumented fallback.
    severity: critical
    likelihood: low
    owner: igor_beylin
    trigger: >
      Missing authority passes validation without a source policy identifier,
      revision, or equivalent provenance.
    preventive_controls:
      - AUTH-003
      - DEC-003
      - negative policy/defaulting tests
    contingency:
      - fail the affected compile-readiness gate
      - restore Unknown/fail-closed state
    related_tasks:
      - TASK-003
      - TASK-005
    related_gates:
      - GATE-002
      - GATE-004
    acceptance_decision_id: null
    status: open
  - id: RISK-005
    risk: Program Execution emitter drifts from Blueprint v2 schemas or ownership law.
    severity: high
    likelihood: medium
    owner: igor_beylin
    trigger: >
      Official instantiated Blueprint validation fails or emitted authority
      contains unresolved/cross-file-invalid references.
    preventive_controls:
      - version target as program-execution-blueprint.v2
      - validate emitted fixture with official Blueprint validator
      - record upstream contract provenance
    contingency:
      - block GATE-004
      - update adapter only after compatibility review
    related_tasks:
      - TASK-005
      - TASK-006
      - TASK-007
    related_gates:
      - GATE-004
      - GATE-005
    acceptance_decision_id: null
    status: open
# =====================================================================
# FILE: WAIVER_REGISTER.yaml
# =====================================================================
schema: program-execution-blueprint.waiver-register.v2
schema_version: 2.0.0
policy:
  implicit_waivers_forbidden: true
  expired_waiver_non_passing: true
waivers: []
# =====================================================================
# FILE: EVIDENCE_CATALOG.yaml
# =====================================================================
schema: program-execution-blueprint.evidence-catalog.v2
schema_version: 2.0.0
evidence:
  - id: EVID-001
    type: source_snapshot
    source: user-supplied gitingest_l9_devpack_compiler_v1_2_0.md
    revision: l9-devpack-compiler-v1.2.0
    digest: null
    method: supplied artifact inspection
    environment: planning
    producer: program_author
    produced_at: "2026-08-10"
    expires_at: null
    result: INFORMATIONAL
    status: available
    supports:
      - DELTA-001
      - DELTA-002
      - DELTA-003
      - DELTA-004
      - DELTA-005
      - DELTA-006
      - DELTA-007
    contradicts: []
    notes: >
      Governs the observed v1.2.0 state for planning; W0 reconciles it
      against the exact Controller-bound repository state.
  - id: EVID-002
    type: source_snapshot
    source: >
      Quantum-L9/Cursor-Governance
      environment/program-execution/core/program-execution-blueprint-template/
      PROGRAM.yaml and EXECUTION_INDEX.yaml
    revision: main-observed-2026-08-10
    digest: null
    method: GitHub raw source inspection
    environment: planning
    producer: program_author
    produced_at: "2026-08-10"
    expires_at: null
    result: INFORMATIONAL
    status: available
    supports:
      - DEC-002
      - DEC-005
      - DEC-006
      - DEC-007
    contradicts: []
    notes: Exact revision/digest must be refreshed by EVID-006 before execution promotion.
  - id: EVID-003
    type: source_snapshot
    source: >
      Quantum-L9/Cursor-Governance
      environment/program-execution/core/shared/INTERFACE_CONTRACT.md
    revision: program-execution-system-v2-observed-2026-08-10
    digest: null
    method: GitHub raw source inspection
    environment: planning
    producer: program_author
    produced_at: "2026-08-10"
    expires_at: null
    result: INFORMATIONAL
    status: available
    supports:
      - DEC-001
      - DEC-002
      - DEC-003
      - DEC-004
      - DEC-006
    contradicts: []
    notes: Exact revision/digest must be refreshed by EVID-006 before execution promotion.
  - id: EVID-004
    type: source_snapshot
    source: >
      Quantum-L9/Cursor-Governance Program Execution Blueprint v2
      TASK_CARDS schema and validate_blueprint.py
    revision: main-observed-2026-08-10
    digest: null
    method: GitHub raw source inspection
    environment: planning
    producer: program_author
    produced_at: "2026-08-10"
    expires_at: null
    result: INFORMATIONAL
    status: available
    supports:
      - DEC-004
      - DEC-006
    contradicts: []
    notes: Exact revision/digest must be refreshed by EVID-006 before execution promotion.
  - id: EVID-005
    type: source_snapshot
    source: Controller-bound TARGET-001 repository baseline
    revision: controller-bound
    digest: null
    method: Program Lock repository inspection
    environment: local
    producer: Program Execution Controller
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-001
      - UNK-001
    contradicts: []
    notes: Must capture exact base SHA and source reconciliation before local_write.
  - id: EVID-006
    type: source_snapshot
    source: exact Program Execution v2 governing contract snapshot
    revision: controller-bound
    digest: null
    method: immutable source retrieval and SHA-256 recording
    environment: planning
    producer: Program Execution Controller
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-001
      - GATE-004
    contradicts: []
    notes: Exact upstream revision/digest used by the projection gate.
  - id: EVID-007
    type: test_result
    source: l9-devpack-compiler regression and negative test suite
    revision: controller-bound
    digest: null
    method: independent command execution against exact worktree state
    environment: local
    producer: Program Execution Controller verifier
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-002
      - GATE-003
      - GATE-005
    contradicts: []
    notes: Must include legacy regression plus new negative semantic tests.
  - id: EVID-008
    type: test_result
    source: emitted Program Execution Blueprint v2 fixture
    revision: controller-bound
    digest: null
    method: official validate_blueprint.py instantiated-mode execution
    environment: local
    producer: Program Execution Controller verifier
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-004
      - GATE-005
    contradicts: []
    notes: Must be validated against the exact EVID-006 contract revision.
  - id: EVID-009
    type: test_result
    source: scripts/validate_exemplary_skill.py
    revision: controller-bound
    digest: null
    method: independent command execution
    environment: local
    producer: Program Execution Controller verifier
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-005
    contradicts: []
    notes: Existing exemplary-tier evidence must remain valid after changes.
  - id: EVID-010
    type: inspection
    source: final diff and authority/provenance review
    revision: controller-bound
    digest: null
    method: independent changed-file and semantic inspection
    environment: local
    producer: Program Execution Controller verifier
    produced_at: "2026-08-10"
    expires_at: null
    result: UNKNOWN
    status: planned
    supports:
      - GATE-002
      - GATE-003
      - GATE-004
      - GATE-005
    contradicts: []
    notes: >
      Must confirm no scope creep, authority widening, runtime ownership,
      implicit defaults, weakened tests, or prohibited remote actions.
# =====================================================================
# FILE: DO_NOT_BUILD.yaml
# =====================================================================
schema: program-execution-blueprint.do-not-build.v2
schema_version: 2.0.0
prohibited_primary_paths:
  - id: DNB-001
    path_or_pattern: DPK-owned runtime task state, leases, attempts, gate results, or receipts
    reason: Program Execution Controller is the sole runtime authority.
    detection: semantic review plus tests rejecting runtime-state emission
    exception_authority: NONE
  - id: DNB-002
    path_or_pattern: Task Contract authority above accepted architecture or public contracts
    reason: Downstream task authority may narrow but never widen upstream authority.
    detection: authority-order fixture and forbidden-semantic scan
    exception_authority: NONE
  - id: DNB-003
    path_or_pattern: implicit owner, rollback, repository, credential, or branch facts
    reason: Authority-affecting defaults require explicit governing provenance.
    detection: negative fixtures with missing policy source
    exception_authority: NONE
  - id: DNB-004
    path_or_pattern: runtime-operable verdict derived only from artifact presence
    reason: Structural existence is not executed proof.
    detection: negative validator fixtures
    exception_authority: NONE
  - id: DNB-005
    path_or_pattern: duplicated Program Execution gate evaluation or Handoff Receipt authority
    reason: Those runtime responsibilities belong to the Controller.
    detection: emitted fixture inspection and ownership-law tests
    exception_authority: NONE
  - id: DNB-006
    path_or_pattern: remote mutation or embedded credentials
    reason: This program authorizes repo-local reversible mutation only.
    detection: changed-file inspection and authorization receipt
    exception_authority: NONE
  - id: DNB-007
    path_or_pattern: deleted or weakened tests/red-lines solely to obtain passing validation
    reason: Passing through weakened evidence violates the remediation objective.
    detection: baseline versus final test and policy inspection
    exception_authority: NONE
allowed_experiments: []
# =====================================================================
# FILE: CURRENT_STATE_DELTA.yaml
# =====================================================================
schema: program-execution-blueprint.current-state-delta.v2
schema_version: 2.0.0
snapshot_at: "2026-08-10"
freshness_policy:
  maximum_age: until TARGET-001 Program Lock is created
  stale_result: BLOCKED
sources:
  - source_id: SRC-001
    evidence_id: EVID-001
    revision: l9-devpack-compiler-v1.2.0
    freshness: planning_snapshot
  - source_id: SRC-002
    evidence_id: EVID-002
    revision: main-observed-2026-08-10
    freshness: refresh_in_W0
  - source_id: SRC-003
    evidence_id: EVID-003
    revision: program-execution-system-v2-observed-2026-08-10
    freshness: refresh_in_W0
  - source_id: SRC-004
    evidence_id: EVID-004
    revision: main-observed-2026-08-10
    freshness: refresh_in_W0
deltas:
  - id: DELTA-001
    target_id: TARGET-001
    expected_state: >
      Task authority is subordinate to accepted architecture/contracts and
      may only narrow upstream authority.
    observed_state: >
      DPK v1.2.0 places explicit Task Contract above architecture invariants
      and public interface schemas.
    classification: authority_conflict
    impact: Program Execution-targeted work could widen or override upstream authority.
    required_action: Implement DEC-002.
    evidence_ids:
      - EVID-001
      - EVID-002
      - EVID-003
  - id: DELTA-002
    target_id: TARGET-001
    expected_state: Authority-affecting defaults require explicit governing provenance.
    observed_state: >
      Missing operational_owner may be auto-filled as quantum-ai without a
      source policy artifact.
    classification: provenance_gap
    impact: Missing authority can be converted into an apparently valid fact.
    required_action: Implement DEC-003.
    evidence_ids:
      - EVID-001
      - EVID-003
  - id: DELTA-003
    target_id: TARGET-001
    expected_state: Rollback evidence is explicit and attributable.
    observed_state: >
      Library rollback may be auto-passed through a generic version-pin/yank default.
    classification: provenance_gap
    impact: A repository-specific rollback fact may be inferred without evidence.
    required_action: Implement DEC-003 for rollback derivation.
    evidence_ids:
      - EVID-001
  - id: DELTA-004
    target_id: TARGET-001
    expected_state: Structural inspection reports structural compile-readiness only.
    observed_state: >
      validate_devpack awards categories from file/directory presence and may
      emit operable/conditional labels without executing the represented proof.
    classification: proof_semantics_mismatch
    impact: Consumers can interpret presence as runtime verification.
    required_action: Implement DEC-004.
    evidence_ids:
      - EVID-001
      - EVID-003
      - EVID-004
  - id: DELTA-005
    target_id: TARGET-001
    expected_state: Unknowns block only explicitly dependent work.
    observed_state: >
      DPK execution-package doctrine uses broad STOP semantics for required Unknowns.
    classification: execution_semantics_mismatch
    impact: Independent safe work can be unnecessarily blocked.
    required_action: Implement DEC-005 in the Program Execution target adapter.
    evidence_ids:
      - EVID-001
      - EVID-002
  - id: DELTA-006
    target_id: TARGET-001
    expected_state: >
      A versioned Program Execution v2 target emits the complete indexed
      Blueprint authority source set.
    observed_state: >
      DPK v1.2.0 emits its own six-layer envelope and execution package but
      has no lossless Blueprint v2 projection.
    classification: missing_capability
    impact: A downstream system would need to reconstruct authority heuristically.
    required_action: Implement DEC-006 and DEC-007.
    evidence_ids:
      - EVID-001
      - EVID-002
      - EVID-004
  - id: DELTA-007
    target_id: TARGET-001
    expected_state: DPK terminology describes compilation/design-time authority.
    observed_state: DPK describes itself as a fully programmatic execution/control plane.
    classification: responsibility_collision
    impact: Ownership language collides with Program Execution Controller runtime authority.
    required_action: Implement DEC-001.
    evidence_ids:
      - EVID-001
      - EVID-003
next_blocking_action: >
  Bind TARGET-001 and exact Program Execution v2 governing sources in W0,
  produce EVID-005 and EVID-006, resolve UNK-001, then reseal before W1.
# =====================================================================
# FILE: WORKSTREAMS.yaml
# =====================================================================
schema: program-execution-blueprint.workstreams.v2
schema_version: 2.0.0
workstreams:
  - id: WS-01
    name: Authority and provenance semantics
    objective: >
      Correct authority precedence and eliminate unproven authority-affecting defaults.
    owner: igor_beylin
    target_ids:
      - TARGET-001
    scope:
      include:
        - SKILL.md
        - expertise_model.yaml
        - skill_intelligence_report.yaml
        - references/dpk-layer-contract.md
        - references/quality-gates.md
        - references/spec-schema.md
        - scripts/validate_devpack.py
      exclude:
        - Program Execution Controller code
        - remote repository operations
    inputs:
      - DEC-001
      - DEC-002
      - DEC-003
      - EVID-001
      - EVID-003
    outputs:
      - corrected authority hierarchy
      - provenance-backed default policy
      - negative policy tests
    entry_gate_ids:
      - GATE-001
    exit_gate_ids:
      - GATE-002
    rollback_boundary: Restore WS-01 files from TARGET-001 Program Lock base SHA.
    definition_status: active
  - id: WS-02
    name: Validator proof semantics
    objective: >
      Make compile-readiness reporting accurately distinguish structural
      evidence from independently executed proof.
    owner: igor_beylin
    target_ids:
      - TARGET-001
    scope:
      include:
        - scripts/validate_devpack.py
        - references/quality-gates.md
        - validator regression fixtures
      exclude:
        - runtime gate evaluation
        - Program Execution Controller verification code
    inputs:
      - DEC-004
      - EVID-001
      - EVID-003
      - EVID-004
    outputs:
      - structural-readiness result semantics
      - execution-aware evidence fields
      - negative presence-only fixtures
    entry_gate_ids:
      - GATE-001
    exit_gate_ids:
      - GATE-003
    rollback_boundary: Restore WS-02 files from TARGET-001 Program Lock base SHA.
    definition_status: active
  - id: WS-03
    name: Program Execution v2 projection
    objective: >
      Add a versioned, provenance-preserving Blueprint v2 compile target.
    owner: igor_beylin
    target_ids:
      - TARGET-001
    scope:
      include:
        - references/program-execution-v2-projection.md
        - schemas/program-execution-v2-target.schema.json
        - scripts/emit_program_execution_v2.py
        - Program Execution projection fixtures
        - generic spec changes proven generally reusable
      exclude:
        - Controller runtime state
        - Program Lock mutation
        - remote action adapters
    inputs:
      - DEC-005
      - DEC-006
      - DEC-007
      - EVID-006
    outputs:
      - Program Execution v2 target schema
      - Blueprint v2 emitter
      - provenance mapping
      - scoped Unknown mapping
      - canonical authorization ceilings
    entry_gate_ids:
      - GATE-002
      - GATE-003
    exit_gate_ids:
      - GATE-004
    rollback_boundary: Remove new projection files and restore modified core files to base SHA.
    definition_status: active
  - id: WS-04
    name: Integration verification and handoff
    objective: >
      Prove compatibility, exemplary-skill integrity, and Blueprint v2 conformance.
    owner: igor_beylin
    target_ids:
      - TARGET-001
    scope:
      include:
        - tests
        - fixtures
        - documentation
        - final changed-file set
      exclude:
        - merge
        - release
        - deployment
    inputs:
      - EVID-007
      - EVID-008
      - EVID-009
      - EVID-010
    outputs:
      - independently verified local worktree
      - Controller Handoff Receipt inputs
    entry_gate_ids:
      - GATE-004
    exit_gate_ids:
      - GATE-005
    rollback_boundary: Discard the isolated target worktree and recreate it from the Program Lock base SHA.
    definition_status: active
# =====================================================================
# FILE: DEPENDENCY_GRAPH.yaml
# =====================================================================
schema: program-execution-blueprint.dependency-graph.v2
schema_version: 2.0.0
direction: predecessor_to_successor
nodes:
  - id: TASK-001
    entity_type: task
    owner: igor_beylin
  - id: TASK-002
    entity_type: task
    owner: igor_beylin
  - id: TASK-003
    entity_type: task
    owner: igor_beylin
  - id: TASK-004
    entity_type: task
    owner: igor_beylin
  - id: TASK-005
    entity_type: task
    owner: igor_beylin
  - id: TASK-006
    entity_type: task
    owner: igor_beylin
  - id: TASK-007
    entity_type: task
    owner: igor_beylin
edges:
  - id: EDGE-001
    from: TASK-001
    to: TASK-002
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-001]
  - id: EDGE-002
    from: TASK-001
    to: TASK-003
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-001]
  - id: EDGE-003
    from: TASK-001
    to: TASK-004
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-001]
  - id: EDGE-004
    from: TASK-002
    to: TASK-005
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-002]
  - id: EDGE-005
    from: TASK-003
    to: TASK-005
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-002]
  - id: EDGE-006
    from: TASK-004
    to: TASK-005
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-003]
  - id: EDGE-007
    from: TASK-002
    to: TASK-006
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-002]
  - id: EDGE-008
    from: TASK-003
    to: TASK-006
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-002]
  - id: EDGE-009
    from: TASK-004
    to: TASK-006
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-003]
  - id: EDGE-010
    from: TASK-005
    to: TASK-007
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-004]
  - id: EDGE-011
    from: TASK-006
    to: TASK-007
    relation: requires
    blocking: true
    proof_gate_ids: [GATE-004]
critical_path:
  - TASK-001
  - TASK-002
  - TASK-005
  - TASK-007
parallelizable_groups:
  - [TASK-002, TASK-003, TASK-004]
  - [TASK-005, TASK-006]
hard_rule: >
  No successor may bypass a predecessor by reproducing its output elsewhere.
# =====================================================================
# FILE: EXECUTION_WAVES.yaml
# =====================================================================
schema: program-execution-blueprint.execution-waves.v2
schema_version: 2.0.0
promotion_rule: >
  A wave starts only when prior waves and all blocking entry gates pass.
waves:
  - id: W0
    name: authority_and_current_state_lock
    sequence: 0
    depends_on: []
    workstream_ids:
      - WS-01
      - WS-02
      - WS-03
      - WS-04
    task_ids:
      - TASK-001
    entry_gate_ids: []
    exit_gate_ids:
      - GATE-001
    rollback_boundary: >
      Discard planning/runtime binding artifacts; repository mutation is forbidden.
    definition_status: active
  - id: W1
    name: authority_and_proof_semantics
    sequence: 1
    depends_on:
      - W0
    workstream_ids:
      - WS-01
      - WS-02
    task_ids:
      - TASK-002
      - TASK-003
      - TASK-004
    entry_gate_ids:
      - GATE-001
    exit_gate_ids:
      - GATE-002
      - GATE-003
    rollback_boundary: Restore W1 changed files to Program Lock base SHA.
    definition_status: active
  - id: W2
    name: program_execution_projection
    sequence: 2
    depends_on:
      - W1
    workstream_ids:
      - WS-03
    task_ids:
      - TASK-005
      - TASK-006
    entry_gate_ids:
      - GATE-002
      - GATE-003
    exit_gate_ids:
      - GATE-004
    rollback_boundary: >
      Remove new projection artifacts and restore modified core files to base SHA.
    definition_status: active
  - id: W3
    name: regression_and_handoff
    sequence: 3
    depends_on:
      - W2
    workstream_ids:
      - WS-04
    task_ids:
      - TASK-007
    entry_gate_ids:
      - GATE-004
    exit_gate_ids:
      - GATE-005
    rollback_boundary: >
      Discard the isolated worktree and recreate it from Program Lock base SHA.
    definition_status: active
# =====================================================================
# FILE: TASK_CARDS.yaml
# =====================================================================
schema: program-execution-blueprint.task-cards.v2
schema_version: 2.0.0
tasks:
  - id: TASK-001
    title: Bind exact target and governing Program Execution contract
    definition_status: ready
    workstream_id: WS-01
    wave_id: W0
    target_id: TARGET-001
    execution_kind: program_control
    objective: >
      Establish exact current-state and governing-contract evidence before
      any repository mutation is authorized.
    authority_basis_ids:
      - AUTH-001
      - AUTH-002
      - AUTH-003
      - AUTH-004
      - AUTH-005
    required_decision_ids: []
    blocking_unknown_ids: []
    input_evidence_ids:
      - EVID-001
      - EVID-002
      - EVID-003
      - EVID-004
    actions:
      - resolve TARGET-001 through Controller repository registration
      - record exact base SHA and working-tree state
      - reconcile EVID-001 source snapshot with the bound repository
      - capture exact Program Execution v2 governing source revision and SHA-256
      - produce resolution evidence for UNK-001
    outputs:
      - id: OUT-001
        type: evidence
        location: controller://evidence/EVID-005
        required: true
      - id: OUT-002
        type: evidence
        location: controller://evidence/EVID-006
        required: true
    acceptance:
      - id: AC-001
        statement: >
          TARGET-001 is bound to one exact base SHA and the relevant source
          state is reconciled.
        required_evidence_types:
          - source_snapshot
      - id: AC-002
        statement: >
          Program Execution v2 authority sources used by this program have
          an exact immutable revision or digest.
        required_evidence_types:
          - source_snapshot
    validation:
      - id: VAL-001
        method: inspection
        command_or_inspection: >
          Inspect Controller repository registration, Program Lock base SHA,
          working-tree status, source reconciliation, and governing-source digest.
        environment: planning
        expected_result: PASS
    negative_cases:
      - repository_id resolves to no repository or multiple repositories
      - working tree has unexplained pre-existing mutation
      - uploaded source snapshot materially differs from bound target without reconciliation
      - Program Execution governing source cannot be bound to an exact revision
    rollback:
      strategy: discard_unaccepted_program_control_evidence
      trigger: target_or_authority_lock_failure
      validation: No repository local_write occurred.
    risk:
      tier: T0
      reversibility: fully_reversible
      blast_radius: program_definition
    authorization_ceiling:
      inspect: true
      local_write: false
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-001
  - id: TASK-002
    title: Align DPK authority hierarchy and role boundary
    definition_status: ready
    workstream_id: WS-01
    wave_id: W1
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Make DPK authority ordering and terminology compatible with Program
      Execution's upstream-authority and runtime-ownership laws.
    authority_basis_ids:
      - AUTH-001
      - AUTH-002
    required_decision_ids:
      - DEC-001
      - DEC-002
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-001
      - EVID-003
      - EVID-005
      - EVID-006
    actions:
      - update SKILL.md role language from runtime control plane to compiler/design-time authority
      - place accepted architecture and contracts above approved Task Contract authority
      - define Task Contract as a narrowing scope projection
      - align expertise_model.yaml and skill_intelligence_report.yaml
      - update reference contracts and examples containing the superseded precedence
      - add regression checks for forbidden authority widening
    outputs:
      - id: OUT-003
        type: artifact
        location: SKILL.md
        required: true
      - id: OUT-004
        type: artifact
        location: references/dpk-layer-contract.md
        required: true
    acceptance:
      - id: AC-003
        statement: >
          No Program Execution-targeted DPK rule permits Task Contract authority
          to override accepted architecture or contracts.
        required_evidence_types:
          - test_result
          - inspection
      - id: AC-004
        statement: >
          DPK explicitly disclaims Controller-owned runtime state and verification authority.
        required_evidence_types:
          - inspection
    validation:
      - id: VAL-002
        method: command_and_inspection
        command_or_inspection: >
          python3 scripts/validate_exemplary_skill.py . ; then inspect all
          authority-order and control-plane terminology occurrences.
        environment: local
        expected_result: PASS
    negative_cases:
      - legacy Task Contract precedence remains in an active authority model
      - DPK still claims ownership of mutable runtime execution state
      - an example contradicts the canonical authority order
    rollback:
      strategy: restore_TASK-002_files_from_program_lock_base
      trigger: validation_failure_or_scope_drift
      validation: Restored files match base SHA content.
    risk:
      tier: T2
      reversibility: reversible
      blast_radius: DPK semantic contract
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-002
  - id: TASK-003
    title: Replace implicit authority autofix with provenance-backed derivation
    definition_status: ready
    workstream_id: WS-01
    wave_id: W1
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Ensure owner and rollback defaults are applied only from explicit
      governing policy and never materialized from an undocumented fallback.
    authority_basis_ids:
      - AUTH-003
    required_decision_ids:
      - DEC-003
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-001
      - EVID-003
      - EVID-005
    actions:
      - remove unconditional missing-owner pass behavior
      - remove unconditional library rollback pass behavior
      - introduce explicit policy-derived default provenance
      - record governing source identity in validator/compiler output
      - make Program Execution target fail closed when policy provenance is absent
      - add negative fixtures for missing owner, rollback, and policy source
    outputs:
      - id: OUT-005
        type: artifact
        location: scripts/validate_devpack.py
        required: true
      - id: OUT-006
        type: artifact
        location: references/quality-gates.md
        required: true
    acceptance:
      - id: AC-005
        statement: >
          A missing operational owner cannot pass solely because the validator
          contains a hard-coded organization default.
        required_evidence_types:
          - test_result
      - id: AC-006
        statement: >
          Any derived authority-affecting value records its governing provenance.
        required_evidence_types:
          - test_result
          - inspection
    validation:
      - id: VAL-003
        method: command
        command_or_inspection: >
          python3 -m unittest discover -s tests -p 'test_*policy*.py'
        environment: local
        expected_result: PASS
    negative_cases:
      - missing owner passes with no governing policy source
      - missing rollback passes with no repository or policy evidence
      - provenance source is recorded only in human prose and absent from machine output
    rollback:
      strategy: restore_TASK-003_files_from_program_lock_base
      trigger: regression_or_policy_semantics_failure
      validation: Legacy files restored exactly; no partial policy migration remains.
    risk:
      tier: T2
      reversibility: reversible
      blast_radius: DPK readiness and policy semantics
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-002
  - id: TASK-004
    title: Separate structural compile-readiness from runtime operability proof
    definition_status: ready
    workstream_id: WS-02
    wave_id: W1
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Make validate_devpack report only what its static checks actually prove.
    authority_basis_ids:
      - AUTH-004
    required_decision_ids:
      - DEC-004
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-001
      - EVID-003
      - EVID-004
      - EVID-005
    actions:
      - define validator evidence scope as structural compile-readiness
      - distinguish artifact presence from executed validation
      - prevent test-directory presence from proving test success
      - prevent rollback-command presence from proving dry-run success
      - prevent repository-map presence from proving architecture alignment
      - version or migrate output labels that currently imply runtime operability
      - add presence-only negative fixtures
    outputs:
      - id: OUT-007
        type: artifact
        location: scripts/validate_devpack.py
        required: true
      - id: OUT-008
        type: artifact
        location: references/quality-gates.md
        required: true
    acceptance:
      - id: AC-007
        statement: >
          Structural-only evidence is never represented as executed test,
          rollback, reproducibility, or runtime proof.
        required_evidence_types:
          - test_result
          - inspection
      - id: AC-008
        statement: >
          Validator output declares the evidence level behind every readiness result.
        required_evidence_types:
          - test_result
    validation:
      - id: VAL-004
        method: command
        command_or_inspection: >
          python3 -m unittest discover -s tests -p 'test_*validate_devpack*.py'
        environment: local
        expected_result: PASS
    negative_cases:
      - empty tests directory receives full test/eval proof
      - rollback command string receives dry-run proof without execution
      - repository-map file existence receives 100 percent architecture alignment proof
      - structural result is labeled runtime operable
    rollback:
      strategy: restore_TASK-004_files_from_program_lock_base
      trigger: compatibility_or_semantic_failure
      validation: Restored validator behavior matches the Program Lock baseline.
    risk:
      tier: T2
      reversibility: reversible
      blast_radius: validator consumers and readiness reporting
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-003
  - id: TASK-005
    title: Implement versioned Program Execution Blueprint v2 emitter
    definition_status: ready
    workstream_id: WS-03
    wave_id: W2
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Compile DPK facts into the complete Program Execution Blueprint v2
      indexed design-time authority set.
    authority_basis_ids:
      - AUTH-001
      - AUTH-005
    required_decision_ids:
      - DEC-006
      - DEC-007
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-005
      - EVID-006
    actions:
      - add references/program-execution-v2-projection.md
      - add schemas/program-execution-v2-target.schema.json
      - add scripts/emit_program_execution_v2.py
      - map DPK IR to all EXECUTION_INDEX required sources
      - preserve source evidence and authority provenance
      - emit Blueprint definitions only and no Controller runtime records
      - create deterministic complete fixture with no placeholders
    outputs:
      - id: OUT-009
        type: artifact
        location: references/program-execution-v2-projection.md
        required: true
      - id: OUT-010
        type: artifact
        location: schemas/program-execution-v2-target.schema.json
        required: true
      - id: OUT-011
        type: artifact
        location: scripts/emit_program_execution_v2.py
        required: true
    acceptance:
      - id: AC-009
        statement: >
          Emitter produces every source required by Blueprint v2 EXECUTION_INDEX.
        required_evidence_types:
          - test_result
      - id: AC-010
        statement: >
          Emitted output contains no Controller-owned runtime state, gate result,
          attempt result, lease, or Handoff Receipt.
        required_evidence_types:
          - inspection
    validation:
      - id: VAL-005
        method: command
        command_or_inspection: >
          python3 -m unittest discover -s tests -p 'test_*program_execution*emitter*.py'
        environment: local
        expected_result: PASS
    negative_cases:
      - one required Blueprint source is omitted
      - emitter invents an owner or repository URL
      - emitter includes runtime task state or gate evaluation
      - emitted source has unresolved cross-file references
    rollback:
      strategy: remove_projection_additions_and_restore_modified_core_files
      trigger: emitter_contract_failure
      validation: TARGET-001 matches the pre-TASK-005 state.
    risk:
      tier: T2
      reversibility: reversible
      blast_radius: new Program Execution compile target
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-004
  - id: TASK-006
    title: Add provenance, scoped Unknown, and authorization-ceiling projection
    definition_status: ready
    workstream_id: WS-03
    wave_id: W2
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Make Program Execution projection lossless for the authority and blocker
      semantics that cannot safely be inferred downstream.
    authority_basis_ids:
      - AUTH-002
      - AUTH-003
      - AUTH-005
    required_decision_ids:
      - DEC-005
      - DEC-006
      - DEC-007
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-005
      - EVID-006
    actions:
      - define stable source-evidence to emitted-field provenance edges
      - map unresolved DPK facts to named UNKNOWN_REGISTER records
      - map Unknowns only to dependent Task Cards
      - require explicit canonical ten-action authorization ceiling per emitted task
      - prohibit downstream inference of commit, push, PR, merge, release, deployment, destruction, or messaging authority
      - keep Program Execution-specific fields in the versioned target overlay unless generally reusable
      - add negative authorization-widening and blocker-scope tests
    outputs:
      - id: OUT-012
        type: artifact
        location: schemas/program-execution-v2-target.schema.json
        required: true
      - id: OUT-013
        type: artifact
        location: Program Execution projection tests and fixtures
        required: true
    acceptance:
      - id: AC-011
        statement: >
          Every emitted mutable Task Card contains exactly the canonical
          ten-action authorization ceiling and never gains authority by omission.
        required_evidence_types:
          - test_result
      - id: AC-012
        statement: >
          Each emitted Unknown blocks only tasks that consume the missing fact.
        required_evidence_types:
          - test_result
      - id: AC-013
        statement: >
          Material emitted authority can be traced to source evidence,
          accepted decision, or explicit governing policy.
        required_evidence_types:
          - inspection
    validation:
      - id: VAL-006
        method: command
        command_or_inspection: >
          python3 -m unittest discover -s tests -p 'test_*program_execution*projection*.py'
        environment: local
        expected_result: PASS
    negative_cases:
      - omitted authorization action defaults to allowed
      - an Unknown globally blocks unrelated tasks
      - owner or rollback is emitted without provenance
      - task scope widens an upstream contract
    rollback:
      strategy: restore_TASK-006_files_from_program_lock_base
      trigger: projection_semantics_failure
      validation: No partial target-overlay schema remains.
    risk:
      tier: T2
      reversibility: reversible
      blast_radius: Program Execution projection contract
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-004
  - id: TASK-007
    title: Run full regression, official Blueprint validation, and handoff review
    definition_status: ready
    workstream_id: WS-04
    wave_id: W3
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >
      Independently prove the remediated compiler remains valid and emits
      a Program Execution v2 Blueprint accepted by the official validator.
    authority_basis_ids:
      - AUTH-001
      - AUTH-002
      - AUTH-003
      - AUTH-004
      - AUTH-005
    required_decision_ids:
      - DEC-001
      - DEC-002
      - DEC-003
      - DEC-004
      - DEC-005
      - DEC-006
      - DEC-007
    blocking_unknown_ids:
      - UNK-001
    input_evidence_ids:
      - EVID-005
      - EVID-006
      - EVID-007
      - EVID-008
      - EVID-009
      - EVID-010
    actions:
      - compile all Python sources
      - execute complete local regression suite independently
      - execute validate_exemplary_skill.py independently
      - emit representative Program Execution v2 Blueprint fixture
      - run official Blueprint v2 validator in instantiated mode against the fixture
      - inspect final diff for scope creep, weakened tests, authority widening, and runtime ownership
      - preserve exact receipts for owner handoff
    outputs:
      - id: OUT-014
        type: evidence
        location: controller://evidence/EVID-007
        required: true
      - id: OUT-015
        type: evidence
        location: controller://evidence/EVID-008
        required: true
      - id: OUT-016
        type: evidence
        location: controller://evidence/EVID-009
        required: true
      - id: OUT-017
        type: evidence
        location: controller://evidence/EVID-010
        required: true
    acceptance:
      - id: AC-014
        statement: All deterministic local regression tests pass independently.
        required_evidence_types:
          - test_result
      - id: AC-015
        statement: Exemplary-skill validation still passes.
        required_evidence_types:
          - test_result
      - id: AC-016
        statement: >
          Representative emitted Blueprint passes the exact Program Execution
          v2 instantiated validator.
        required_evidence_types:
          - test_result
      - id: AC-017
        statement: >
          Final diff contains no unauthorized remote action, runtime-authority
          duplication, implicit authority creation, or weakened evidence.
        required_evidence_types:
          - inspection
    validation:
      - id: VAL-007
        method: command
        command_or_inspection: python3 -m py_compile scripts/*.py
        environment: local
        expected_result: PASS
      - id: VAL-008
        method: command
        command_or_inspection: >
          python3 -m unittest discover -s tests -p 'test_*.py'
        environment: local
        expected_result: PASS
      - id: VAL-009
        method: command
        command_or_inspection: python3 scripts/validate_exemplary_skill.py .
        environment: local
        expected_result: PASS
      - id: VAL-010
        method: external_adapter
        command_or_inspection: >
          Program Execution verifier runs the EVID-006 revision of
          program-execution-blueprint-template/scripts/validate_blueprint.py
          against the emitted fixture with --mode instantiated.
        environment: local
        expected_result: PASS
    negative_cases:
      - worker-reported PASS differs from independent Controller execution
      - Blueprint validator passes only after removing a required source
      - exemplary validator is weakened instead of fixing the skill
      - final diff contains files outside declared remediation scope
      - any remote mutation action is attempted
    rollback:
      strategy: discard_isolated_worktree_and_recreate_from_program_lock_base_sha
      trigger: any_blocking_validation_or_scope_failure
      validation: Recreated worktree exactly matches Program Lock base SHA.
    risk:
      tier: T2
      reversibility: fully_reversible
      blast_radius: complete local remediation worktree
    authorization_ceiling:
      inspect: true
      local_write: true
      commit: true
      push: true
      pull_request: true
      merge: false
      publish_or_release: false
      deploy_or_migrate: false
      destructive_change: false
      external_message: false
    completion_gate_ids:
      - GATE-005
# =====================================================================
# FILE: CONVERGENCE_GATES.yaml
# =====================================================================
schema: program-execution-blueprint.convergence-gates.v2
schema_version: 2.0.0
result_values:
  - PASS
  - FAIL
  - BLOCKED
  - UNKNOWN
  - NOT_APPLICABLE_WITH_REASON
unknown_is_non_passing: true
gates:
  - id: GATE-001
    name: authority_and_current_state_lock
    definition_status: active
    owner: igor_beylin
    class: authority
    scope:
      wave_ids:
        - W0
      task_ids:
        - TASK-001
    method:
      type: inspection
      steps:
        - Bind TARGET-001 to one exact repository and base SHA.
        - Confirm working-tree preconditions.
        - Reconcile uploaded v1.2.0 source with the target.
        - Capture exact Program Execution v2 governing revision/digest.
        - Produce evidence sufficient to resolve UNK-001.
    pass_condition: >
      EVID-005 and EVID-006 are independently available, target identity is
      unambiguous, no unexplained source drift exists, and UNK-001 has an
      evidence-backed resolution path.
    fail_condition: >
      Repository identity is ambiguous, base state is unsafe, source evidence
      materially conflicts without reconciliation, or governing Program
      Execution authority cannot be bound exactly.
    blocking: true
    required_evidence_ids:
      - EVID-005
      - EVID-006
    waiver_allowed: false
  - id: GATE-002
    name: authority_and_provenance_contract_correct
    definition_status: active
    owner: igor_beylin
    class: contract
    scope:
      wave_ids:
        - W1
      task_ids:
        - TASK-002
        - TASK-003
    method:
      type: command_and_inspection
      steps:
        - Run authority/defaulting regression and negative tests independently.
        - Inspect active authority-order definitions for legacy precedence.
        - Inspect every derived owner/rollback path for governing provenance.
        - Confirm DPK does not claim Controller-owned runtime authority.
    pass_condition: >
      Task Contracts narrow rather than widen authority, all authority-affecting
      defaults require provenance, and regression/negative tests pass.
    fail_condition: >
      Legacy authority precedence remains, an undocumented default can pass,
      DPK claims runtime ownership, or any required test fails.
    blocking: true
    required_evidence_ids:
      - EVID-007
      - EVID-010
    waiver_allowed: false
  - id: GATE-003
    name: structural_proof_semantics_correct
    definition_status: active
    owner: igor_beylin
    class: validation
    scope:
      wave_ids:
        - W1
      task_ids:
        - TASK-004
    method:
      type: command_and_inspection
      steps:
        - Execute validator regression and presence-only negative fixtures.
        - Inspect result schema and user-visible verdict semantics.
        - Verify structural presence is not represented as executed proof.
    pass_condition: >
      validate_devpack reports structural compile-readiness honestly and all
      presence-only false-proof cases remain non-passing for executed evidence.
    fail_condition: >
      Any unexecuted test, rollback, reproducibility, or architecture-alignment
      claim receives executed-proof semantics.
    blocking: true
    required_evidence_ids:
      - EVID-007
      - EVID-010
    waiver_allowed: false
  - id: GATE-004
    name: program_execution_v2_projection_complete
    definition_status: active
    owner: igor_beylin
    class: contract
    scope:
      wave_ids:
        - W2
      task_ids:
        - TASK-005
        - TASK-006
    method:
      type: command_and_inspection
      steps:
        - Emit representative complete Blueprint v2 source set.
        - Validate it with the exact EVID-006 official instantiated validator.
        - Inspect provenance, Unknown scoping, authority order, and authorization ceilings.
        - Confirm absence of Controller-owned runtime state.
    pass_condition: >
      The emitted Blueprint passes official instantiated validation, every
      material authority has provenance, every task authorization ceiling is
      complete and non-widening, and runtime state is absent.
    fail_condition: >
      Official validation fails, authority is invented, an Unknown blocks
      unrelated work, a permission can widen by omission, or DPK emits
      Controller-owned state.
    blocking: true
    required_evidence_ids:
      - EVID-008
      - EVID-010
    waiver_allowed: false
  - id: GATE-005
    name: full_regression_and_handoff_ready
    definition_status: active
    owner: igor_beylin
    class: validation
    scope:
      wave_ids:
        - W3
      task_ids:
        - TASK-007
    method:
      type: command_and_inspection
      steps:
        - Independently run complete local regression.
        - Run exemplary-skill validation.
        - Re-run official Blueprint validation.
        - Compare actual changed files with declared scope.
        - Inspect residual risks and rollback path.
    pass_condition: >
      EVID-007, EVID-008, EVID-009, and EVID-010 all PASS and no unresolved
      blocking risk, scope violation, weakened evidence, or unauthorized action remains.
    fail_condition: >
      Any required independent validation fails, actual changes exceed scope,
      rollback is not reproducible, or a blocking semantic defect remains.
    blocking: true
    required_evidence_ids:
      - EVID-007
      - EVID-008
      - EVID-009
      - EVID-010
    waiver_allowed: false
# =====================================================================
# FILE: OBSERVABILITY_PLAN.yaml
# =====================================================================
schema: program-execution-blueprint.observability-plan.v2
schema_version: 2.0.0
signals:
  - id: OBS-001
    name: dpk_regression_suite_result
    owner: igor_beylin
    source_target_id: TARGET-001
    collection_method: independent Controller command receipt
    expected_range: PASS
    alert_condition: result != PASS
    retention: through program-owner terminal verdict
    related_gate_ids:
      - GATE-002
      - GATE-003
      - GATE-005
    status: planned
  - id: OBS-002
    name: program_execution_blueprint_v2_validation
    owner: igor_beylin
    source_target_id: TARGET-001
    collection_method: official instantiated Blueprint validator receipt
    expected_range: PASS
    alert_condition: result != PASS
    retention: through program-owner terminal verdict
    related_gate_ids:
      - GATE-004
      - GATE-005
    status: planned
  - id: OBS-003
    name: exemplary_skill_validation
    owner: igor_beylin
    source_target_id: TARGET-001
    collection_method: validate_exemplary_skill.py independent receipt
    expected_range: PASS
    alert_condition: result != PASS
    retention: through program-owner terminal verdict
    related_gate_ids:
      - GATE-005
    status: planned
  - id: OBS-004
    name: authority_widening_or_runtime_ownership_findings
    owner: igor_beylin
    source_target_id: TARGET-001
    collection_method: independent semantic diff inspection
    expected_range: zero blocking findings
    alert_condition: blocking finding count > 0
    retention: through program-owner terminal verdict
    related_gate_ids:
      - GATE-002
      - GATE-004
      - GATE-005
    status: planned
incident_routing:
  - condition: blocking_signal_breach
    owner: igor_beylin
    action: pause_affected_wave_and_preserve_evidence
# =====================================================================
# FILE: CUTOVER_AND_ROLLBACK.yaml
# =====================================================================
schema: program-execution-blueprint.cutover-and-rollback.v2
schema_version: 2.0.0
cutover:
  required_gate_ids:
    - GATE-005
  approval_action: program_owner_acceptance
  steps:
    - preserve final Program Lock digest and all Verification/Gate receipts
    - generate Controller Handoff Receipt
    - present verified local worktree and residual risks to program owner
    - do not commit, push, open a PR, merge, publish, or deploy under this Blueprint
  abort_conditions:
    - any blocking gate is not PASS
    - unresolved authority or provenance conflict exists
    - official Blueprint v2 validation is not PASS
    - rollback cannot recreate the Program Lock base state
  observation_window: until explicit program-owner terminal verdict
rollback:
  trigger_conditions:
    - blocking_gate_failure
    - material_scope_or_authority_breach
    - program_owner_rejects_local_result
  steps:
    - preserve failure evidence and receipts
    - discard the isolated TARGET-001 worktree
    - recreate TARGET-001 from the exact Program Lock base SHA
  data_reconciliation: >
    Not applicable; program authorizes repository-local source changes only
    and no external persistent mutation.
  validation:
    - recreated worktree HEAD equals Program Lock base SHA
    - working tree contains no program-created mutation
  owner: Program Execution Controller
# =====================================================================
# FILE: SOURCE_TRACEABILITY.yaml
# =====================================================================
schema: program-execution-blueprint.source-traceability.v2
schema_version: 2.0.0
authority_classes:
  - governing
  - supporting
  - contradicting
  - example
  - historical
  - inferred
sources:
  - id: SRC-001
    source: user-supplied l9-devpack-compiler v1.2.0 source snapshot
    revision: l9-devpack-compiler-v1.2.0
    authority_class: supporting
    evidence_id: EVID-001
    claims:
      - current DPK authority order
      - current autofix/default policy
      - current validator scoring implementation
      - current execution-package and Unknown semantics
      - absence of a Program Execution v2 emitter
    target_ids:
      - TARGET-001
    workstream_ids:
      - WS-01
      - WS-02
      - WS-03
      - WS-04
    task_ids:
      - TASK-001
      - TASK-002
      - TASK-003
      - TASK-004
      - TASK-005
      - TASK-006
      - TASK-007
    gate_ids:
      - GATE-001
      - GATE-002
      - GATE-003
      - GATE-004
      - GATE-005
    status: active
  - id: SRC-002
    source: >
      Quantum-L9/Cursor-Governance Program Execution Blueprint v2
      PROGRAM.yaml and EXECUTION_INDEX.yaml
    revision: exact revision captured by EVID-006
    authority_class: governing
    evidence_id: EVID-002
    claims:
      - canonical Program Execution authority order
      - indexed Blueprint source ownership
      - scoped Unknown operating rule
    target_ids:
      - TARGET-001
    workstream_ids:
      - WS-01
      - WS-03
    task_ids:
      - TASK-001
      - TASK-002
      - TASK-005
      - TASK-006
    gate_ids:
      - GATE-001
      - GATE-002
      - GATE-004
    status: active
  - id: SRC-003
    source: >
      Quantum-L9/Cursor-Governance
      environment/program-execution/core/shared/INTERFACE_CONTRACT.md
    revision: exact revision captured by EVID-006
    authority_class: governing
    evidence_id: EVID-003
    claims:
      - Blueprint owns design-time authority
      - Controller owns runtime state and gate evaluation
      - downstream authority may narrow but never widen
      - worker claims require independent verification
      - final convergence belongs to the program owner
    target_ids:
      - TARGET-001
    workstream_ids:
      - WS-01
      - WS-02
      - WS-03
      - WS-04
    task_ids:
      - TASK-001
      - TASK-002
      - TASK-003
      - TASK-004
      - TASK-005
      - TASK-006
      - TASK-007
    gate_ids:
      - GATE-001
      - GATE-002
      - GATE-003
      - GATE-004
      - GATE-005
    status: active
  - id: SRC-004
    source: >
      Quantum-L9/Cursor-Governance Program Execution Blueprint v2
      TASK_CARDS schema and validate_blueprint.py
    revision: exact revision captured by EVID-006
    authority_class: governing
    evidence_id: EVID-004
    claims:
      - canonical ten-action authorization ceiling
      - Task Cards contain definition rather than runtime state
      - cross-file references and task-wave alignment are validator-enforced
      - instantiated Blueprint requires accepted program definition and resolved placeholders
    target_ids:
      - TARGET-001
    workstream_ids:
      - WS-02
      - WS-03
      - WS-04
    task_ids:
      - TASK-001
      - TASK-004
      - TASK-005
      - TASK-006
      - TASK-007
    gate_ids:
      - GATE-001
      - GATE-003
      - GATE-004
      - GATE-005
    status: active

The required indexed source set above matches the current v2 EXECUTION_INDEX.yaml; the current validator checks those files, their schemas, cross-file IDs, DAG acyclicity, task/wave agreement, authorization-ceiling keys, placeholder removal, and manifest integrity. 

Supplemental narrative patch

The stock template’s EXECUTIVE_DECISION.md still contains REPLACE_WITH_* markers, which instantiated-mode validation explicitly rejects.  Replace it with:

# Executive Decision: L9 Devpack Compiler Program Execution v2 Hardening
## Decision
Refactor l9-devpack-compiler so that DPK is the evidence/compiler and
intermediate-representation layer upstream of Program Execution Blueprint v2.
DPK may emit design-time authority but must not own Program Execution runtime
state, gate evaluation, attempts, approvals, leases, or receipts.
## Problem being resolved
EVID-001 identifies five material incompatibilities with Program Execution v2:
authority precedence, implicit authority-affecting defaults, structural evidence
being presented as operability, global STOP semantics for Unknowns, and the
absence of a lossless Blueprint v2 projection.
EVID-002 through EVID-004 define the governing Program Execution v2 boundary.
## Target state
l9-devpack-compiler:
1. extracts and normalizes repository evidence into generic DPK IR;
2. treats approved task scope as a narrowing authority;
3. derives authority-affecting defaults only from explicit governing policy;
4. reports structural compile-readiness separately from runtime proof;
5. maps Unknowns only to named dependent tasks;
6. emits a complete program-execution-blueprint.v2 source set through a
   versioned target adapter;
7. never emits or owns Controller runtime state.
TARGET-001 remains the sole mutable target. Program Execution Controller remains
the runtime authority.
## Authority assignment
`AUTHORITY_REGISTRY.yaml` is canonical.
## Forbidden end states
- DPK and the Controller both own runtime task or gate state.
- A Task Contract can override accepted architecture or public contracts.
- Missing owners, rollback paths, credentials, repositories, or branches become
  valid facts without provenance.
- File presence is represented as executed runtime proof.
- Program Execution permissions are widened by omission or downstream inference.
- Unknowns block work that does not depend on the missing fact.
- Existing tests or red-lines are weakened merely to obtain PASS.
## Failure behavior
Any authority conflict, missing provenance, official Blueprint validation
failure, unexpected scope expansion, or independent validation failure blocks
promotion of the affected wave. The Controller preserves evidence and the
isolated repository worktree is recoverable to its Program Lock base SHA.
No remote mutation is authorized by this Blueprint.
## Safe execution order
1. W0 binds TARGET-001 and the exact governing Program Execution contract.
2. W1 corrects authority/default/proof semantics.
3. W2 builds the versioned Program Execution v2 projection.
4. W3 independently executes regression, exemplary, and official Blueprint validation.
5. The Controller produces a Handoff Receipt.
6. Only the program owner accepts a terminal verdict or authorizes a superseding program.
## Supersession rule
Any change to the accepted decisions, authority assignments, authorization
ceilings, or completion gates requires a superseding Blueprint and a new
immutable Program Lock.

I’d also replace the template HANDOFF.md with this initial state so it doesn’t incorrectly say there are no accepted decisions:

# Program Handoff: L9 Devpack Compiler Program Execution v2 Hardening
This document describes definition state only. Runtime facts come from the
active Program Execution Controller and its Handoff Receipt.
## Program revision
- Program version: `1.0.0`
- Blueprint contract: `program-execution-blueprint.v2`
- Snapshot: `2026-08-10`
- Accepted Controller Handoff Receipt: `NONE`
## Definition state
- Current wave authorized for admission: `W0`
- Accepted decisions: `DEC-001` through `DEC-007`
- Blocking decisions: `NONE`
- Blocking Unknowns: `UNK-001` for `TASK-002` through `TASK-007`
## Exact next action
Execute `TASK-001`: bind `repository_id=l9-devpack-compiler` to the exact
Controller-managed local repository/base SHA, reconcile the supplied v1.2.0
source snapshot, and capture the exact Program Execution v2 governing revision.
After evidence-backed resolution of `UNK-001`, reseal the accepted Blueprint
before admitting W1.
## Authorization status
This Blueprint permits inspection in W0. W1-W3 permit reversible local writes
only after their dependencies and gates pass.
Commit, push, pull request, merge, release, deployment, destructive change,
and external messaging are not authorized.
## Controller return path
Consume only a Handoff Receipt bound to the active Program Lock digest.
The Controller may report verified tasks and evaluated gates but does not
declare this program converged. The program owner owns the terminal verdict.

Bootstrap/run sequence

The current distribution supplies instantiate_pair.py, which creates aligned Blueprint and Controller instances, while instantiated Blueprint validation explicitly checks the complete source set and manifest. 

From Cursor-Governance/environment/program-execution/core:

python3 scripts/instantiate_pair.py \
  --program-name "L9 Devpack Compiler Program Execution v2 Hardening" \
  --program-id l9-devpack-program-execution-hardening \
  --program-version 1.0.0 \
  --program-owner igor_beylin \
  --controller-name "L9 Devpack Hardening Controller" \
  --controller-id l9-devpack-hardening-controller \
  --controller-owner igor_beylin \
  --date 2026-08-10 \
  --target /path/to/l9-devpack-hardening-program

Overlay the files above into program-execution-blueprint/. Because the Blueprint manifest hashes every file, regenerate it after the overlay; instantiate.py exposes the manifest writer used by the template. 

cd /path/to/l9-devpack-hardening-program/program-execution-blueprint
python3 -c \
  "from pathlib import Path; from scripts.instantiate import write_manifest; write_manifest(Path('.').resolve())"
python3 scripts/validate_blueprint.py . --mode instantiated

Then register the actual l9-devpack-compiler repository with the Controller as repository_id=l9-devpack-compiler and admit TASK-001 only. After W0 produces the exact repo/base-SHA and Program Execution contract evidence, resolve UNK-001, reseal/regenerate the manifest, and let the Controller advance into W1. That preserves the current v2 rule that the Controller imports Blueprint authority immutably and marks runtime stale whenever imported authority changes. 