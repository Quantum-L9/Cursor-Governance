L9 Subagent-Generated Data Law

law_id: l9.subagent_generated_data_law.v1
title: L9 Subagent-Generated Data Law
status: canonical_draft
artifact_type: operational_governance_law
authority_domain: subagent_generated_data
applies_to:
  - cursor
  - claude_code
  - bounded_autonomy_runtime
  - all_l9_repositories
  - all_governed_project_repositories
  - all_deployed_subagent_roles

⸻

1. Prime Commandment

Every governed subagent execution produces two classes of output:

1. the primary artifact required by the assigned action; and
2. generated data created while producing that artifact.

Generated data includes observations, evidence, discovered structure, implementation intelligence, rejected hypotheses, validation knowledge, context requirements, failure patterns, unresolved unknowns, reusable procedures, and follow-on opportunities.

No high-value subagent-generated data may be discarded solely because the immediate action has completed.

Every completed subagent action must either:

* preserve generated data as execution evidence;
* route reusable generated data into an approved downstream system;
* defer generated data pending further evidence or authority;
* or explicitly reject it as non-reusable residue.

Unexamined disposal of subagent-generated data is a failure of leverage.

⸻

2. Purpose

This law ensures that deployed subagents increase both:

* immediate execution capacity; and
* future platform capability.

The objective is not maximal storage.

The objective is to convert useful by-products of subagent work into trusted, scoped, reusable, invalidatable, and measurable platform assets.

A successful implementation causes future agents to:

* rediscover less;
* receive better task context;
* execute with stronger contracts;
* avoid previously identified failures;
* use proven procedures;
* validate more effectively;
* identify ownership and architecture faster;
* preserve unresolved unknowns;
* and make better next-action decisions.

⸻

3. Authority and Ownership

3.1 Cursor-Governance owns

Cursor-Governance is the owner of:

* this law;
* mandatory packet emission;
* role-specific generated-data obligations;
* generated-data schemas;
* packet validation;
* harvesting;
* classification;
* routing;
* promotion eligibility;
* learning closure;
* IDE enforcement;
* adapter conformance;
* and campaign-level generated-data audit.

3.2 Destination systems own their domains

This law may route generated data into systems that own:

* durable memory;
* task contracts;
* validation controls;
* reusable patterns;
* architecture records;
* opportunity planning;
* unknown tracking;
* policy review;
* or evidence retention.

Routing data to a destination does not transfer governance authority to the producing subagent.

3.3 Producing agents are not promotion authorities

A producing subagent may:

* identify candidate reusable data;
* estimate its value;
* propose routes;
* identify evidence;
* and state confidence.

A producing subagent may not independently promote its own output into:

* canonical memory;
* canonical architecture;
* policy;
* task-contract law;
* validation law;
* reusable pattern canon;
* or cross-repository authority.

Promotion requires an independent compiler, validator, reviewer, or designated authority gate.

⸻

4. Scope

This law applies to every governed subagent role, including:

* coordinator;
* context compiler;
* recon;
* synthesis;
* executor;
* verifier;
* reviewer;
* poller;
* failure classifier;
* remediator;
* sentinel;
* evidence writer;
* and future specialized roles.

It applies whether the subagent:

* mutates code;
* reads repositories;
* analyzes architecture;
* runs validation;
* monitors CI;
* reviews a patch;
* prepares context;
* classifies failures;
* or produces evidence.

It applies to subagents deployed by:

* Cursor;
* Claude Code;
* the L9 autonomy runtime;
* or any future IDE or orchestration adapter.

⸻

5. Definitions

5.1 Primary artifact

The typed artifact required to satisfy the action’s completion predicate.

Examples:

* ReconReport;
* ExecutionBrief;
* ExecutionResult;
* VerificationReport;
* ReviewVerdict;
* PollReport;
* RemediationBrief;
* RemediationResult;
* ContextPack;
* SentinelReport.

5.2 Subagent-generated data

Any data created, discovered, inferred, tested, rejected, or organized by a subagent while fulfilling an authorized action.

5.3 Generated data unit

The smallest independently classifiable and routable generated-data item.

A generated data unit must represent one coherent claim, procedure, unknown, opportunity, or evidence-backed observation.

5.4 Subagent data packet

The canonical typed envelope containing:

* the primary result;
* generated data units;
* provenance;
* unresolved unknowns;
* proposed routes;
* and reuse assessment.

5.5 Harvesting

The process of extracting generated data units from a validated subagent result.

5.6 Distillation

The process of reducing validated generated data into a reusable target-specific representation without losing provenance, scope, epistemic status, or invalidation conditions.

5.7 Promotion

The controlled transition of generated data into a destination where it may affect future execution.

5.8 Learning closure

The campaign-level condition that confirms all required subagent-generated data has been captured, validated, classified, routed, retained, deferred, or rejected.

5.9 Reuse

A later governed action consuming a promoted generated-data unit in a way that affects execution, validation, routing, planning, or decision quality.

Storage alone is not reuse.

Retrieval alone is not reuse.

⸻

6. Dual-Output Law

Every governed subagent action has two output obligations:

output_obligations:
  primary:
    purpose: satisfy_current_action
    required: true
  generated_data:
    purpose: preserve_and_route_reusable_execution_value
    required: true

A subagent may produce no reusable generated data.

It may not omit the generated-data assessment.

The valid result in that case is an explicit declaration:

generated_data_assessment:
  reusable_data_found: false
  reason: task_produced_only_transient_or_duplicate_information

Silence is not equivalent to “nothing reusable was found.”

⸻

7. Generated Data Classes

Every generated data unit must have exactly one primary class.

generated_data_classes:
  repository_fact:
    definition: directly observed repository or environment fact
  architecture_boundary:
    definition: discovered ownership, responsibility, or must_not_own boundary
  ownership_finding:
    definition: finding about the authoritative owner of data, behavior, schema, or policy
  dependency_finding:
    definition: discovered dependency, integration edge, prerequisite, or ordering relationship
  implementation_surface:
    definition: files, modules, interfaces, migrations, tests, or runtime surfaces relevant to implementation
  execution_procedure:
    definition: reusable ordered procedure for completing a class of action
  validation_procedure:
    definition: reusable method for establishing correctness or evidence
  failure_pattern:
    definition: recurring or reusable description of a failure condition and its causes
  rejected_approach:
    definition: examined or attempted approach that should not be repeated under equivalent conditions
  context_requirement:
    definition: context required for a role or action to execute correctly
  context_waste:
    definition: context loaded but not useful, or context shown to cause confusion or excess cost
  task_contract_gap:
    definition: missing or ambiguous field, boundary, input, output, stop condition, or evidence requirement
  policy_candidate:
    definition: observation indicating a potential governance or permission rule change
  invariant_candidate:
    definition: condition that may deserve continuous machine enforcement
  regression_candidate:
    definition: discovered behavior suitable for conversion into a test or guard
  reusable_pattern_candidate:
    definition: repeatable execution or reasoning pattern supported by evidence
  artifact_lineage:
    definition: relationship between source, derived, current, superseded, or invalidated artifacts
  unresolved_unknown:
    definition: unanswered question requiring ownership, evidence, or a next action
  follow_on_opportunity:
    definition: bounded future action that may increase leverage, safety, quality, or autonomy
  evidence_only:
    definition: useful provenance that should be retained but not normally injected into future execution

Secondary tags may be added, but the primary class controls routing.

⸻

8. Epistemic Status Law

Every generated data unit must state how it is known.

epistemic_statuses:
  observed:
    definition: directly supported by inspected evidence
  derived:
    definition: reasoned from one or more observed facts
  hypothesized:
    definition: plausible but not yet validated
  disproven:
    definition: tested or inspected and found invalid
  contested:
    definition: contradicted by another credible source or finding
  unresolved:
    definition: insufficient evidence to determine truth or applicability

The following are forbidden:

* storing a hypothesis as an observed fact;
* storing a recommendation as canonical authority;
* retrieving a contested unit without labeling it contested;
* using an unresolved unit as an execution premise without an explicit risk decision;
* allowing a derived finding to outrank current repository evidence.

⸻

9. Mandatory Subagent Data Packet

Every completed subagent action must emit a packet conforming to the canonical schema.

The packet must contain at least:

subagent_data_packet:
  schema_version:
  packet_id:
  identity:
    campaign_id:
    graph_id:
    repository:
    repository_class:
    base_sha:
    action_id:
    agent_id:
    role:
    lease_id:
  primary_result:
    artifact_id:
    artifact_kind:
    completion_status:
  generated_data_units: []
  unresolved_unknowns: []
  provenance:
    input_artifacts: []
    evidence_artifacts: []
    inspected_paths: []
    executed_commands: []
  reuse_assessment:
    task_local_value:
    cross_task_value:
    cross_repository_value:
    confidence:
  generated_at:

The packet may be embedded in the primary artifact or submitted as a linked artifact.

It must remain independently addressable.

⸻

10. Generated Data Unit Requirements

Every generated data unit must contain:

generated_data_unit:
  unit_id:
  primary_class:
  epistemic_status:
  statement:
  source_evidence:
  scope:
  confidence:
  freshness:
  proposed_routes:
  expected_reuse:
  invalidation_conditions:

10.1 Statement

The statement must describe one coherent reusable unit.

It must not combine unrelated claims.

10.2 Source evidence

Observed or derived units require inspectable provenance.

Evidence may reference:

* repository path;
* file hash;
* commit SHA;
* test result;
* command receipt;
* typed artifact;
* runtime probe;
* CI result;
* review finding;
* or governed external source.

10.3 Scope

Scope must specify where the unit applies.

Possible scope dimensions include:

* repository;
* repository class;
* project group;
* module;
* path;
* task type;
* role;
* environment;
* contract version;
* schema version;
* or campaign.

10.4 Confidence

Confidence must be explicit and evidence-relative.

Confidence is not authority.

10.5 Freshness

Every reusable unit must state:

* when it was observed;
* which repository state it applies to;
* and whether it has a time or change-based validity limit.

10.6 Invalidation conditions

Every unit proposed for future reuse must define what would make it stale, contested, superseded, or invalid.

⸻

11. Role-Specific Obligations

11.1 Recon agents

Recon agents must assess:

* discovered repository structure;
* relevant paths;
* irrelevant paths;
* ownership evidence;
* dependency edges;
* implementation surfaces;
* context gaps;
* unresolved ambiguity;
* and efficient future inspection methods.

Recon agents may not establish canonical ownership.

11.2 Synthesis agents

Synthesis agents must assess:

* reconciled findings;
* unresolved conflicts;
* authority used for resolution;
* ordering logic;
* assumptions removed;
* assumptions retained;
* dependency logic;
* and risk concentration.

Synthesis agents may produce candidate contract improvements but may not promote them.

11.3 Executor agents

Executor agents must assess:

* actual implementation sequence;
* deviations from the execution brief;
* hidden constraints;
* fragile code surfaces;
* reusable implementation procedures;
* required follow-on validation;
* and implementation assumptions.

Execution success does not imply generated-data validity.

11.4 Verifier agents

Verifier agents must assess:

* effective validation methods;
* ineffective or misleading validation methods;
* edge cases;
* regression candidates;
* proof gaps;
* evidence quality;
* and remaining validation unknowns.

A false-green method must be recorded as a rejected approach or failure pattern.

11.5 Reviewer agents

Reviewer agents must assess:

* recurring defect classes;
* task-contract weaknesses;
* architecture risks;
* maintainability risks;
* missing evidence;
* missing reviewer context;
* and candidate validation or governance improvements.

Reviewer observations remain review findings until separately promoted.

11.6 Poller agents

Poller agents must assess:

* CI failure categories;
* review-thread patterns;
* flaky checks;
* convergence time;
* repeated remediation causes;
* escalation triggers;
* and remote-state assumptions.

Pollers remain read-only unless a separately authorized remediation lease is issued.

⸻

12. Validation Law

A subagent data packet must be validated before harvesting.

Validation must confirm:

* schema correctness;
* registered campaign identity;
* registered action identity;
* correct agent identity;
* correct role;
* valid lease association;
* correct graph;
* correct repository;
* authorized base SHA;
* valid primary artifact reference;
* required role fields;
* evidence-reference integrity;
* valid generated-data classes;
* valid epistemic statuses;
* no forbidden self-promotion;
* no missing reuse assessment;
* and no unclassified unknowns.

A packet that fails validation must not enter downstream routing.

Failure must produce a typed rejection result and an orchestration receipt.

⸻

13. Capture Before Distillation

Raw subagent output must be retained as execution evidence before distillation.

The system must preserve the difference between:

raw execution evidence
→ validated generated data
→ distilled reusable unit
→ promoted platform asset

Distillation must not destroy the ability to trace a promoted unit to its source.

Raw reports must not be loaded wholesale into future context by default.

⸻

14. Classification Law

The classifier must determine:

* primary generated-data class;
* epistemic status;
* authority sensitivity;
* scope;
* confidence;
* expected reuse;
* potential destination;
* and risk of incorrect promotion.

Classification must be deterministic where the packet already provides sufficient information.

Model-assisted classification may be used when deterministic classification is insufficient, but its output must remain a proposal until validated.

⸻

15. Routing Law

Each validated generated data unit must receive one or more explicit routing decisions.

Permitted routes include:

canonical_routes:
  memory:
    purpose: durable advisory knowledge and temporal retrieval
  contracts:
    purpose: future task inputs, outputs, boundaries, stop conditions, or evidence requirements
  validation:
    purpose: tests, invariants, CI checks, evidence requirements, and regression guards
  patterns:
    purpose: reusable execution, inspection, validation, or remediation procedures
  architecture:
    purpose: ownership, responsibility, dependency, and boundary candidates
  opportunities:
    purpose: follow-on work, missing capabilities, open loops, and next-action planning
  unknowns:
    purpose: unresolved questions requiring owner, next action, and evidence path
  evidence:
    purpose: provenance retention without normal future-context injection
  reject:
    purpose: explicit disposal of non-reusable residue

A unit without a route is invalid unless its routing decision is reject.

⸻

16. Route Ownership

16.1 Memory route

The memory route may receive:

* stable repository facts;
* validated operational lessons;
* durable architecture context;
* reusable environment knowledge;
* and historical decisions with provenance.

Memory remains advisory unless promoted separately into an authoritative artifact.

16.2 Contracts route

The contracts route may receive:

* missing task inputs;
* missing output fields;
* unclear boundaries;
* missing stop conditions;
* missing evidence requirements;
* and repeated execution ambiguity.

16.3 Validation route

The validation route may receive:

* failure patterns;
* edge cases;
* false-green methods;
* missing checks;
* regression candidates;
* and evidence gaps.

16.4 Patterns route

The patterns route may receive:

* proven inspection sequences;
* reusable execution procedures;
* reliable remediation flows;
* successful decomposition strategies;
* and validated parallelization patterns.

16.5 Architecture route

The architecture route may receive:

* ownership candidates;
* dependency relationships;
* responsibility boundaries;
* must-not-own findings;
* and integration edges.

Architecture promotion requires designated architecture authority.

16.6 Opportunities route

The opportunities route may receive:

* missing capabilities;
* follow-on tasks;
* unclosed loops;
* automation opportunities;
* and bounded optimization candidates.

⸻

17. Promotion Decisions

Every routed unit must receive one promotion decision.

promotion_decisions:
  promote:
    meaning: eligible to affect future behavior through the target system
  retain:
    meaning: preserve as evidence without normal future execution influence
  defer:
    meaning: potentially reusable but missing evidence, recurrence, freshness, or authority
  reject:
    meaning: non-reusable, duplicate, stale, unsupported, misleading, or excessively noisy

Promotion must consider:

* evidence strength;
* confidence;
* recurrence;
* authority sensitivity;
* scope clarity;
* freshness;
* duplication;
* conflict;
* expected leverage;
* and cost of incorrect reuse.

⸻

18. Promotion Risk Classes

promotion_risk_classes:
  low:
    examples:
      - campaign_local_evidence
      - inspected_path_inventory
      - rejected_task_local_hypothesis
      - task_local_context_fragment
    authority_required: runtime_validation
  medium:
    examples:
      - reusable_procedure
      - cross_task_context_fragment
      - contract_delta
      - regression_candidate
      - failure_pattern
    authority_required:
      - independent_validation
      - or_recurrence
  high:
    examples:
      - architecture_ownership
      - policy_change
      - permission_boundary
      - security_rule
      - cross_repository_canonical_claim
    authority_required:
      - designated_human_or_canonical_authority

No high-risk unit may be promoted automatically.

⸻

19. Deduplication Law

The system must detect:

* exact duplicates;
* semantic duplicates;
* narrower restatements;
* broader restatements;
* stronger-evidence replacements;
* superseding findings;
* and repository-specific exceptions.

Duplicate generated data must not create parallel active truths.

A duplicate may:

* strengthen existing evidence;
* increase confidence;
* expand scope;
* narrow scope;
* or establish recurrence.

The deduplication result must preserve source lineage.

⸻

20. Conflict Law

Conflicting units must be explicitly represented.

A conflict record must contain:

generated_data_conflict:
  conflict_id:
  unit_ids:
  conflict_type:
  authority_sources:
  current_resolution:
  unresolved:
  blocking_effect:
  next_action:

The system must not silently resolve conflicts involving:

* canonical policy;
* architecture ownership;
* security boundaries;
* task authority;
* current repository state;
* or contradictory observed facts.

Unresolved high-impact conflicts must block promotion.

⸻

21. Unknown Preservation Law

Every unresolved unknown must have:

unresolved_unknown:
  unknown_id:
  description:
  class:
  blocking_status:
  owner:
  next_action:
  evidence_needed:
  source_action:

Unknown classes include:

* blocking;
* validation;
* harmless;
* stale;
* and evidence-available-but-uninspected.

No unknown may disappear solely because its producing agent terminated.

⸻

22. Freshness and Invalidation Law

Every promoted reusable unit must support one or more invalidation conditions.

Examples:

invalidation_conditions:
  - relevant_path_changed
  - repository_base_changed
  - schema_version_changed
  - contract_version_changed
  - policy_version_changed
  - architecture_owner_changed
  - dependency_upgraded
  - contradictory_evidence_accepted
  - failed_reuse_reported
  - expiration_reached

Reusable units may have the following lifecycle states:

lifecycle_states:
  - valid
  - stale_revalidatable
  - stale_recompute_required
  - contested
  - superseded
  - invalid
  - archived

Invalid, superseded, or archived units must not enter normal future context.

Contested units must be labeled and excluded unless the consuming action explicitly requests contested evidence.

⸻

23. Retrieval and Context Law

Generated data creates leverage only when it is retrieved under appropriate conditions.

Future-context retrieval must filter by:

* repository;
* repository class;
* task type;
* agent role;
* paths;
* base SHA;
* contract version;
* confidence;
* authority;
* freshness;
* invalidation state;
* and context budget.

Retrieval must prefer:

* promoted;
* valid;
* scoped;
* high-confidence;
* high-reuse;
* and recently validated units.

Full raw packet loading is forbidden by default.

⸻

24. Reuse Law

A generated data unit counts as reused only when a later governed action consumes it and it changes behavior.

Valid reuse effects include:

* reduced discovery;
* accelerated execution;
* improved scope control;
* improved validation;
* prevented failure;
* prevented repeated rejected work;
* improved context;
* improved routing;
* improved architecture understanding;
* improved contract precision;
* or improved next-action selection.

Every reuse event should record:

reuse_event:
  unit_id:
  consuming_campaign:
  consuming_action:
  consuming_agent_role:
  injection_method:
  outcome:
  value_observed:
  correction_required:
  validity_confirmed:

⸻

25. Learning Closure Law

Execution completion and learning closure are separate.

completion_dimensions:
  execution_completion:
    meaning: current action or campaign completed correctly
  learning_closure:
    meaning: generated data was processed according to this law

A campaign may continue executing while low-risk generated-data processing runs.

A campaign may not seal until learning closure passes.

Learning closure requires:

learning_closure_requirements:
  required_packets_received: true
  packets_schema_valid: true
  provenance_validated: true
  generated_units_classified: true
  routing_decisions_recorded: true
  promotion_decisions_recorded: true
  unresolved_unknowns_registered: true
  high_value_conflicts_routed: true
  rejected_residue_has_reason: true
  evidence_archive_complete: true

⸻

26. Storage Tiers

Tier 1 — Raw execution evidence

Properties:

* immutable;
* complete;
* high volume;
* campaign scoped;
* provenance preserving;
* not normally injected into future context.

Tier 2 — Validated generated data

Properties:

* structured;
* classified;
* deduplicated;
* evidence linked;
* scoped;
* freshness aware;
* not automatically canonical.

Tier 3 — Promoted platform assets

Properties:

* low volume;
* high utility;
* destination owned;
* versioned;
* invalidatable;
* actively retrievable;
* behavior changing.

Future agents should normally consume Tier 3.

Tier 2 may be consumed for targeted analysis.

Tier 1 requires explicit evidence or audit retrieval.

⸻

27. Security and Visibility

Every packet and generated data unit must declare visibility.

visibility_levels:
  - campaign_local
  - repository_local
  - project_group
  - constellation_internal
  - restricted

Before durable retention, packets must be checked for:

* secrets;
* credentials;
* private keys;
* sensitive environment values;
* customer information;
* personally identifiable information;
* restricted URLs;
* and protected operational details.

Sensitive raw evidence must not enter ordinary memory or context retrieval.

Cross-repository retrieval must respect visibility and authorization.

⸻

28. Repository-Class Adaptation

The canonical packet contract is shared across repositories.

Repository interpretation may vary by repository class.

Adapters may provide:

* file-structure knowledge;
* validation authority;
* package conventions;
* framework-specific ownership;
* test conventions;
* migration semantics;
* and context-selection rules.

Adapters may not weaken:

* packet emission;
* provenance;
* classification;
* routing;
* promotion authority;
* or learning closure.

⸻

29. Runtime Enforcement

The autonomy runtime must enforce this sequence:

subagent artifact submitted
→ primary artifact validated
→ subagent data packet validated
→ packet persisted as evidence
→ generated units harvested
→ units classified
→ duplicates and conflicts checked
→ routes selected
→ promotion decisions made
→ destination adapters invoked
→ learning state updated

A packet validation failure must:

* reject generated-data processing;
* record a typed failure;
* preserve the primary artifact decision independently;
* and prevent campaign learning closure.

A generated-data failure must not falsely invalidate a correct primary artifact unless the active campaign explicitly makes packet validity part of action completion.

⸻

30. Observability

The system must measure:

generated_data_metrics:
  packet_capture_rate:
  packet_validation_rate:
  generated_units_per_action:
  high_value_unit_rate:
  rejection_rate:
  duplicate_rate:
  conflict_rate:
  routing_success_rate:
  promotion_rate:
  reuse_rate:
  effective_reuse_rate:
  rediscovery_reduction:
  context_reduction:
  validation_conversion_rate:
  contract_improvement_rate:
  stale_unit_rate:
  failed_reuse_rate:
  unprocessed_high_value_rate:

The objective is not a high generated-unit count.

The objective is increased future capability with controlled information volume.

⸻

31. Non-Negotiable Invariants

subagent_generated_data_invariants:
  - id: SGD-001
    law: no_subagent_completion_without_generated_data_assessment
  - id: SGD-002
    law: no_raw_output_directly_promoted_to_canonical_authority
  - id: SGD-003
    law: no_agent_self_promotes_its_own_findings
  - id: SGD-004
    law: no_reusable_unit_without_provenance
  - id: SGD-005
    law: no_reusable_unit_without_explicit_scope
  - id: SGD-006
    law: no_reusable_unit_without_epistemic_status
  - id: SGD-007
    law: no_promoted_unit_without_invalidation_conditions
  - id: SGD-008
    law: no_unknown_disappears_without_classification_and_owner
  - id: SGD-009
    law: no_high_value_data_discarded_without_rejection_reason
  - id: SGD-010
    law: no_campaign_seal_without_learning_closure
  - id: SGD-011
    law: no_full_raw_packet_loaded_into_future_context_by_default
  - id: SGD-012
    law: no_stored_unit_counted_as_leverage_without_behavioral_reuse
  - id: SGD-013
    law: no_memory_unit_overrides_current_repository_state_or_canonical_authority
  - id: SGD-014
    law: no_high_risk_promotion_without_designated_authority
  - id: SGD-015
    law: no_cross_repository_reuse_without_visibility_authorization
  - id: SGD-016
    law: no_invalid_or_superseded_unit_in_normal_context
  - id: SGD-017
    law: no_routing_decision_without_a_declared_destination_or_rejection
  - id: SGD-018
    law: no_conflicting_high_impact_units_silently_merged

⸻

32. Failure Conditions

This law is violated when:

* a subagent report is discarded after its immediate fields are consumed;
* a future agent must rediscover validated information without justification;
* rejected approaches are repeatedly investigated because negative knowledge was lost;
* a recurring failure never reaches a validation or pattern route;
* a useful procedure remains buried in a campaign report;
* raw reports are loaded wholesale into future prompts;
* an inference is stored as an observed fact;
* stale generated data influences execution without warning;
* generated data lacks provenance;
* a producing agent promotes its own conclusion;
* a campaign seals with unprocessed high-value packets;
* storage volume is presented as leverage without measured reuse;
* or generated data creates a cross-repository information leak.

⸻

33. Required Implementation Components

A conformant implementation must provide:

required_components:
  - canonical_subagent_data_packet_schema
  - canonical_generated_data_unit_schema
  - canonical_routing_decision_schema
  - canonical_learning_closure_schema
  - role_specific_generated_data_profiles
  - packet_validator
  - harvester
  - classifier
  - deduplicator
  - conflict_handler
  - routing_engine
  - promotion_gate
  - learning_closure_validator
  - destination_route_definitions
  - repository_class_adapters
  - memory_adapter
  - evidence_archive
  - invalidation_support
  - reuse_event_tracking
  - conformance_tests
  - routing_tests
  - negative_tests
  - golden_tests

⸻

34. Relationship to Other L9 Authority

This law owns:

* the lifecycle of data produced by deployed subagents;
* packet emission;
* generated-data capture;
* generated-data validation;
* classification;
* routing;
* promotion eligibility;
* and learning closure.

It does not own:

* canonical memory representation;
* semantic memory storage;
* policy authority;
* architecture authority;
* validation implementation;
* task contract authority;
* or repository-specific business correctness.

It routes qualified data into those authority domains.

⸻

35. Wall Version

Every subagent produces a task result and generated platform data.

Capture both.

Preserve raw evidence.

Separate observation from inference.

Classify every reusable unit.

Route it to the system that owns its future value.

Require independent promotion.

Define when it becomes stale.

Measure whether it improves later execution.

A subagent’s strategic work is not complete when its immediate answer is consumed.

It is complete when its reusable value has been promoted, retained, deferred, or deliberately rejected.

Discarded intelligence is failed leverage.
