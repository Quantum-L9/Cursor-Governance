L9 Subagent-Generated Data Law

doctrine_id: l9.subagent_generated_data_law.v1
status: canonical_draft
artifact_type: operational_governance_law
title: L9 Subagent-Generated Data Law

Prime Commandment

Every deployed subagent produces more than a terminal answer.

Its inspections, evidence, discovered boundaries, rejected hypotheses, dependency maps, implementation notes, test knowledge, failure classifications, context gaps, reusable procedures, and unresolved unknowns are generated platform data.

No high-value subagent-generated data may be discarded merely because the immediate action completed.

Subagent work must either:

* contribute directly to the active task;
* improve a future task;
* strengthen a reusable control or artifact;
* remain preserved as traceable execution evidence;
* or be explicitly rejected as non-reusable residue.

Unexamined disposal of subagent-generated data is loss of platform leverage.

⸻

1. Purpose

The purpose of this law is to ensure that every subagent deployment increases not only immediate execution capacity, but also the future intelligence, speed, precision, and reliability of the L9 autonomy system.

Subagents are not disposable inference calls.

They are distributed discovery and execution instruments whose outputs must become reusable platform assets when reuse is justified.

This law governs:

* recon agents;
* synthesis agents;
* execution agents;
* verification agents;
* review agents;
* poll agents;
* remediation agents;
* context-compilation agents;
* drift sentinels;
* evidence agents;
* any future specialized subagent role.

⸻

2. Governing Principle

A subagent task has two possible outputs:

primary output:
  the artifact required to complete the assigned action
secondary output:
  reusable knowledge generated while producing the primary output

Both outputs are first-class.

The primary output advances the current execution graph.

The secondary output may improve:

* future context packs;
* future execution briefs;
* task contracts;
* validation gates;
* reusable procedures;
* architecture maps;
* dependency maps;
* failure classifiers;
* routing rules;
* policy candidates;
* test inventories;
* evidence requirements;
* autonomy scheduling;
* risk scoring;
* recovery procedures.

A campaign that captures only primary outputs is operationally complete but strategically wasteful.

⸻

3. Scope of Subagent-Generated Data

Subagent-generated data includes all structured or unstructured material created during an authorized action.

3.1 Direct task artifacts

Examples:

* recon reports;
* execution briefs;
* patches;
* verification reports;
* review verdicts;
* remediation briefs;
* poll reports;
* context packs;
* evidence receipts.

3.2 Supporting discoveries

Examples:

* ownership boundaries;
* implementation surfaces;
* dependency relationships;
* file and module maps;
* schema relationships;
* integration seams;
* configuration conflicts;
* hidden prerequisites;
* operational assumptions;
* validation requirements;
* rollback constraints;
* environment requirements;
* branch or worktree constraints.

3.3 Negative knowledge

Examples:

* hypotheses disproven;
* files inspected but found irrelevant;
* approaches attempted and rejected;
* commands that fail in the current environment;
* false-positive validation methods;
* stale documentation;
* misleading names;
* invalid assumptions;
* unsafe shortcuts;
* dead integration paths.

Negative knowledge is valuable when it prevents repeated investigation or repeated failure.

3.4 Execution intelligence

Examples:

* most efficient inspection order;
* minimum sufficient context;
* commands that provide authoritative answers;
* reliable test sequences;
* high-value search terms;
* reusable decision trees;
* action decomposition patterns;
* effective parallelization boundaries;
* known contention points;
* high-risk mutation surfaces.

3.5 Unresolved data

Examples:

* blocking unknowns;
* validation unknowns;
* ownership ambiguity;
* conflicting evidence;
* stale sources;
* incomplete environmental facts;
* questions requiring human authority.

Unknowns must not disappear when the producing agent terminates.

⸻

4. Mandatory Data Lifecycle

Every subagent-generated data item must pass through the following lifecycle:

CAPTURED
→ VALIDATED
→ CLASSIFIED
→ DISTILLED
→ ROUTED
→ PROMOTED | RETAINED | DEFERRED | REJECTED
→ REUSED
→ MEASURED

No item may move directly from raw generation into canonical memory or policy.

No item may be discarded before classification unless it is demonstrably transient operational noise.

⸻

5. Capture Law

Every subagent must return a structured terminal artifact.

Natural-language completion alone is invalid.

The terminal artifact must contain:

subagent_result:
  action_id:
  agent_id:
  role:
  lease_id:
  campaign_id:
  graph_id:
  base_sha:
  primary_artifact:
    kind:
    status:
    location:
    validation_state:
  generated_data:
    discoveries: []
    reusable_procedures: []
    evidence_items: []
    rejected_hypotheses: []
    context_gaps: []
    failure_patterns: []
    validation_insights: []
    architecture_findings: []
    unresolved_unknowns: []
    follow_on_opportunities: []
  reuse_assessment:
    immediate_task_value:
    future_task_value:
    cross_campaign_value:
    cross_repository_value:
    confidence:
  provenance:
    inspected_paths: []
    commands_executed: []
    source_artifacts: []
    generated_at:

An agent may return empty categories, but it may not omit the generated-data assessment.

⸻

6. Separation of Raw Data and Promoted Knowledge

Raw subagent output is not memory.

Raw output is execution evidence.

The system must preserve the following distinctions:

raw observation:
  what the agent saw
derived finding:
  what the agent concluded
distilled knowledge:
  what remains useful after validation and deduplication
promoted control:
  what now changes future execution

These categories must not be collapsed.

For example:

raw observation:
  three files declare similar schema fields
derived finding:
  the consumer may be duplicating the owner schema
distilled knowledge:
  this consumer must derive schema definitions from the owner contract
promoted control:
  future execution briefs require owner-schema comparison

⸻

7. Validation Law

No subagent-generated data may be reused as durable knowledge unless its provenance and validity can be assessed.

Validation must consider:

* source path;
* source commit SHA;
* producing action;
* producing agent role;
* observed versus inferred status;
* evidence completeness;
* confidence;
* freshness;
* scope;
* contradiction with current repository state;
* contradiction with canonical law;
* contradiction with active task contracts;
* supersession status.

Every retained item must be classified as one of:

evidence_class:
  - observed_fact
  - derived_finding
  - execution_procedure
  - hypothesis
  - rejected_hypothesis
  - unresolved_unknown
  - recommendation
  - candidate_control

Recommendations and hypotheses must never be retrieved as facts.

⸻

8. Distillation Law

The memory compiler or distillation pipeline must not summarize every subagent report indiscriminately.

It must extract only reusable units.

A valid distilled unit must answer:

distilled_unit:
  what_was_learned:
  why_it_matters:
  where_it_applies:
  where_it_does_not_apply:
  supporting_evidence:
  confidence:
  freshness:
  reuse_target:
  invalidation_condition:

Distillation must remove:

* conversational filler;
* duplicate observations;
* temporary task narration;
* redundant path listings;
* unsupported interpretation;
* low-value implementation trivia;
* agent self-commentary;
* transient state with no future use;
* conclusions superseded by final evidence.

The goal is not smaller text.

The goal is concentrated future utility.

⸻

9. Routing Law

Subagent-generated data must be routed according to the form of leverage it provides.

9.1 Memory compiler

Receives:

* durable factual knowledge;
* recurring environmental knowledge;
* reusable architecture understanding;
* stable ownership knowledge;
* validated operational lessons;
* historical decisions with provenance.

Memory must remain advisory unless separately promoted into canonical authority.

9.2 Context compiler

Receives:

* minimum required facts for a role;
* high-value task-specific discoveries;
* recently validated execution constraints;
* relevant prior failures;
* known unknowns;
* applicable reusable procedures.

Its purpose is to inject the smallest useful slice into future agents.

9.3 Contract compiler

Receives:

* missing task inputs;
* ambiguous task boundaries;
* recurring output omissions;
* missing stop conditions;
* required evidence discovered during execution;
* better decomposition patterns.

Its output modifies future task contracts.

9.4 Validation compiler

Receives:

* discovered edge cases;
* failure modes;
* false-green conditions;
* missing assertions;
* required integration proofs;
* drift patterns;
* scope-violation patterns.

Its output becomes:

* tests;
* invariants;
* CI checks;
* evidence requirements;
* regression guards;
* validation procedures.

9.5 Pattern registry

Receives:

* successful repeated procedures;
* reusable inspection sequences;
* reliable remediation sequences;
* effective decomposition strategies;
* proven parallelization patterns;
* recurring architecture-analysis methods.

Its output becomes reusable operating patterns.

9.6 Architecture and ownership registry

Receives:

* owner-of-truth findings;
* boundary discoveries;
* dependency edges;
* consumer-owner relationships;
* forbidden ownership duplication;
* module responsibility maps.

9.7 Opportunity registry

Receives:

* follow-on work;
* missing capabilities;
* unclosed loops;
* automation candidates;
* high-value unresolved problems;
* future optimization opportunities.

9.8 Evidence archive

Receives:

* full raw reports;
* exact inspected data;
* receipts;
* command outputs;
* rejected hypotheses;
* intermediate artifacts;
* campaign-local supporting material.

The archive preserves traceability without polluting active memory.

⸻

10. Promotion Decisions

Every extracted data unit receives one of the following decisions:

Promote

Use when the data is:

* validated;
* reusable;
* sufficiently stable;
* non-duplicative;
* clearly scoped;
* likely to change future execution.

Retain as evidence

Use when the data is valuable for provenance or audit but should not influence normal future execution.

Defer

Use when the data appears valuable but requires:

* additional evidence;
* conflict resolution;
* recurrence;
* human authority;
* freshness validation.

Reject

Use when the data is:

* task-local and exhausted;
* unsupported;
* duplicated;
* stale;
* misleading;
* overly speculative;
* low leverage;
* likely to create context noise.

Rejection must preserve a short reason when the same class of data may recur.

⸻

11. No Self-Promotion Law

A subagent may identify its output as potentially reusable.

It may not independently promote its own conclusion into:

* canonical memory;
* policy;
* architecture law;
* task contract law;
* validation law;
* reusable pattern canon.

Promotion must be performed by a separate compiler, distiller, reviewer, or authority gate.

This prevents an agent’s local interpretation from becoming system-wide truth without independent assessment.

⸻

12. Reuse Law

Captured data has not created leverage until it affects future behavior.

A generated-data unit is considered reused only when it contributes to at least one later action through:

* context injection;
* contract modification;
* validation execution;
* procedure invocation;
* architecture lookup;
* policy decision;
* scheduling decision;
* risk decision;
* remediation;
* avoidance of repeated discovery.

Mere storage does not count as reuse.

Mere retrieval does not count as reuse.

Reuse requires behavioral effect.

⸻

13. Reuse Feedback

Whenever a future agent consumes a promoted data unit, the system should record:

reuse_event:
  source_data_id:
  consuming_campaign:
  consuming_action:
  consuming_agent_role:
  use_type:
  outcome:
  value_observed:
  correction_required:
  still_valid:

Possible outcomes:

reuse_outcome:
  - accelerated_execution
  - prevented_error
  - improved_context
  - improved_validation
  - improved_scope_control
  - reduced_discovery
  - no_observable_value
  - caused_confusion
  - stale
  - incorrect

Promoted knowledge that repeatedly produces no value should be demoted or removed.

⸻

14. Freshness and Invalidation Law

Every reusable unit must define when it becomes stale.

Possible invalidation triggers:

* repository SHA changes in relevant paths;
* schema version changes;
* policy revision;
* task-contract revision;
* architecture ownership change;
* dependency upgrade;
* environment change;
* failed reuse;
* contradictory evidence;
* superseding decision.

Reusable data without an invalidation rule risks becoming durable misinformation.

⸻

15. Subagent Data Packet

Each completed subagent action must emit or contribute to a packet:

subagent_data_packet:
  packet_id:
  campaign_id:
  graph_id:
  action_id:
  agent_id:
  role:
  lease_id:
  base_sha:
  primary_result:
    artifact_id:
    artifact_kind:
    completion_status:
  extracted_data:
    - data_id:
      data_class:
      statement:
      evidence:
      confidence:
      scope:
      freshness:
      proposed_routes:
      proposed_reuse:
      invalidation_conditions:
  unresolved_unknowns:
    - unknown_id:
      description:
      blocking_status:
      owner:
      next_action:
      evidence_needed:
  rejected_data:
    - description:
      rejection_reason:
  routing_decisions: []
  promotion_decisions: []
  reuse_candidates: []
  validation_status:

This packet is mandatory for campaign learning closure.

⸻

16. Agent-Role-Specific Extraction

Different subagents produce different high-value data.

Recon agents

Must expose:

* discovered structure;
* ownership;
* dependencies;
* relevant paths;
* irrelevant paths;
* evidence gaps;
* implementation candidates;
* search strategies;
* unresolved ambiguity.

Synthesis agents

Must expose:

* reconciled conflicts;
* authority decisions;
* ordering logic;
* dependency logic;
* risk concentration;
* assumptions removed;
* assumptions still active.

Execution agents

Must expose:

* actual edit sequence;
* deviations from the execution brief;
* hidden implementation constraints;
* reusable implementation procedures;
* code surfaces more fragile than expected;
* required follow-on validation.

Verification agents

Must expose:

* reliable validation methods;
* invalid validation methods;
* edge cases;
* regression candidates;
* evidence quality;
* remaining proof gaps.

Review agents

Must expose:

* recurring defect classes;
* contract weaknesses;
* architecture risks;
* maintainability patterns;
* missing reviewer context;
* candidate policy or validation improvements.

Poll and remediation agents

Must expose:

* CI failure categories;
* recurring bot feedback;
* flaky checks;
* successful remediation procedures;
* failed remediation attempts;
* convergence cost;
* escalation triggers.

Context agents

Must expose:

* loaded but unused context;
* missing context;
* high-value context fragments;
* context causing confusion;
* minimum sufficient context.

Sentinels

Must expose:

* drift patterns;
* stale assumptions;
* invalidated outputs;
* recurring policy conflicts;
* high-centrality change surfaces.

⸻

17. Campaign Closure Law

A campaign may reach execution completion before generated-data processing completes.

However, a campaign may not be sealed until:

campaign_learning_closure:
  subagent_packets_complete: true
  high_value_data_extracted: true
  promotion_candidates_routed: true
  unresolved_unknowns_owned: true
  reusable_patterns_recorded: true
  validation_candidates_recorded: true
  context_candidates_recorded: true
  evidence_archive_complete: true

Low-value items may be batch-rejected.

High-value unresolved items must have an owner and next action.

⸻

18. Storage Tiers

Subagent-generated data must be stored in three tiers.

Tier 1 — Raw execution evidence

Characteristics:

* immutable;
* complete;
* high volume;
* campaign scoped;
* retrieved only when needed.

Examples:

* full reports;
* logs;
* tool outputs;
* exact diffs;
* receipts;
* intermediate notes.

Tier 2 — Validated reusable data

Characteristics:

* structured;
* classified;
* scored;
* deduplicated;
* provenance linked;
* not yet canonical.

Examples:

* validated findings;
* procedures;
* unknowns;
* opportunities;
* candidate context fragments;
* candidate guards.

Tier 3 — Promoted platform assets

Characteristics:

* low volume;
* high confidence;
* actively consumed;
* versioned;
* invalidatable;
* behavior changing.

Examples:

* memory entries;
* contract updates;
* context fragments;
* regression guards;
* reusable patterns;
* architecture boundaries;
* policy candidates approved through authority.

Future agents should primarily consume Tier 3.

Tier 1 must never be loaded wholesale by default.

⸻

19. Metrics

The system must measure leverage from subagent-generated data.

Capture rate

percentage of completed subagent actions with valid data packets

Distillation rate

percentage of captured high-value data converted into reusable units

Reuse rate

percentage of promoted units consumed by later actions

Effective reuse rate

percentage of reused units that measurably improve an outcome

Rediscovery reduction

reduction in repeated exploration of already-known surfaces

Context efficiency

less context required because prior findings were distilled correctly

Contract improvement

future tasks receiving better inputs, boundaries, and completion conditions

Validation conversion

number of discoveries converted into executable tests or guards

Stale knowledge rate

promoted units later invalidated because freshness controls failed

Waste rate

high-value generated data discarded or never routed

The objective is not maximal retention.

The objective is maximal useful reuse with minimal context pollution.

⸻

20. Non-Negotiable Invariants

subagent_data_invariants:
  - no_subagent_completion_without_structured_generated_data_assessment
  - no_raw_output_directly_promoted_to_canonical_memory
  - no_agent_self_promotes_its_own_findings
  - no_reusable_finding_without_provenance
  - no_reusable_finding_without_scope
  - no_reusable_finding_without_invalidation_conditions
  - no_unknown_disappears_without_classification
  - no_high_value_data_discarded_without_rejection_reason
  - no_campaign_seal_without_generated_data_harvest
  - no_full_raw_transcript_loaded_into_future_context_by_default
  - no_stored_data_claimed_as_leverage_without_observed_reuse
  - no_memory_entry_overrides_current_repository_state_or_canonical_authority

⸻

21. Failure Conditions

This law is violated when:

* an agent report is discarded after its immediate fields are consumed;
* a useful discovery must be rediscovered by another agent;
* negative knowledge is lost and failed approaches are repeated;
* a recurring validation insight never becomes a guard;
* a stable procedure remains buried in a campaign report;
* raw reports are loaded wholesale into future prompts;
* an agent’s inference is stored as fact;
* stale generated data influences a future execution;
* generated knowledge has no provenance;
* the system measures storage volume instead of future behavioral gain.

⸻

22. Runtime Integration

The autonomy runtime must add the following mandatory actions after relevant agent completion:

agent artifact accepted
→ generated-data extractor
→ provenance validator
→ reusable-data classifier
→ deduplication
→ route selection
→ distillation
→ promotion decision
→ archive and reuse registration

For high-volume campaigns, these actions may run asynchronously relative to the next safe execution step, but they must complete before campaign seal.

The extraction pipeline must not block critical execution for low-value material.

It must block campaign closure when high-value data remains unprocessed.

⸻

23. Relationship to Other L9 Laws

This law owns:

* subagent-generated data;
* capture obligations;
* extraction obligations;
* generated-data lifecycle;
* reuse tracking;
* campaign learning closure.

It does not replace:

* signal governance;
* canonical memory governance;
* policy authority;
* architecture authority;
* validation authority;
* task contract authority;
* evidence retention law.

It routes qualified data into those systems.

The subagent-generated data law answers:

What must happen to the valuable information created by deployed subagents?

Other systems answer:

How should that information be interpreted, promoted, enforced, or retrieved?

⸻

Wall Version

Every subagent produces task output and platform data.

Capture both.

Validate what was observed.

Separate fact from inference.

Distill only reusable value.

Route each useful unit to memory, context, contracts, validation, patterns, architecture, opportunities, or evidence.

Measure whether future behavior improved.

A subagent’s work is not complete when its answer is consumed.

It is complete when its reusable value has either compounded or been deliberately rejected.

Discarded intelligence is failed leverage.
