schema: program-execution-blueprint.program.v2
schema_version: 2.0.0

Native Program Execution v2 Blueprint program definition.

Derived from the campaign design for the shared MCP memory adapter foundation.

This definition remains draft until current repository evidence is collected,

all blocking decisions and Unknowns are resolved or explicitly bounded, the

complete Blueprint is materialized, and native instantiated validation passes.

program:
id: shared-mcp-memory-adapter-foundation
name: Shared MCP Memory Adapter Foundation and Claude Code Reference Migration
version: 1.0.0
owner: Igor Beylin
definition_status: draft
snapshot_at: “2026-08-04”

objective: >-
Establish a canonical, peer-neutral agent memory adapter platform that uses
the shared l9-memory-mcp CLI for all memory-domain operations, proves the
platform through a hardened Claude Code reference implementation, removes
Claude Code’s bespoke memory pipeline without weakening deterministic
governance, and provides reusable contracts, runtime components,
conformance tests, end-to-end validation, and adapter scaffolding for all
current and future peers.

problem_statement: >-
Claude Code currently diverges from peer agents by operating a dedicated
memory pipeline containing Claude-specific lifecycle hooks, transport and
client behavior, local state, schemas, enforcement validation, and tests.
Although this pipeline supplies deterministic hydration, coordination,
mutation gating, and writeback behavior, its private implementation creates
duplicate authority, inconsistent integration paths, higher maintenance
cost, and a precedent for per-agent memory architectures. Existing peer
adapters reach shared memory through the common MCP service, but their
thinner integration model is not yet a sufficiently complete reference for
deterministic lifecycle enforcement, durable ingestion, capability
declaration, regression protection, or portable end-to-end certification.
A direct deletion of Claude Code’s pipeline in favor of model instructions
would remove enforceable controls and reintroduce previously observed
omission risks. The required change is therefore not merely a Claude Code
cleanup: it is the creation of a canonical adapter foundation in which the
shared CLI owns MCP transport, the memory service owns memory truth and
authorization, the shared adapter runtime owns normalized lifecycle policy
and durable delivery, and each peer-specific adapter owns only native
surface translation.

target_state: >-
Cursor-Governance contains a versioned, schema-governed, peer-neutral memory
adapter foundation under environment/agents with canonical adapter
manifests, capabilities declarations, lifecycle events, operation
classifications, policy profiles, session receipts, episode envelopes,
delivery-journal contracts, CLI response contracts, compatibility rules,
architecture fitness functions, a shared lifecycle runtime, an adapter
generator, and a reusable conformance and end-to-end test harness. Claude
Code is installed as the first certified reference adapter at
environment/agents/adapters/claude-code and performs hydration, conflict
checks, claim acquisition, claim verification, and ingestion exclusively
through the shared l9-memory-mcp CLI. Claude-specific memory transport,
local memory semantics, duplicate schemas, locally authoritative lock state,
and duplicate identity logic are removed only after shadow comparison,
canary enforcement, fault injection, rollback rehearsal, and independent
verification prove functional and governance equivalence. Deterministic
controls remain active for governed operations, claims are bound to the
authenticated principal and exact repository state, session writeback is
durable and idempotent, degraded behavior is explicit, and a second peer can
adopt the foundation without modifying the shared runtime or canonical
schemas.

scope:
include:
- >-
Define the canonical peer-neutral adapter manifest and capabilities
contracts, including adapter identity, lifecycle support, enforcement
strength, writeback guarantees, compatibility requirements, failure
semantics, observability obligations, and native integration mode.
- >-
Add environment/agents/adapters/claude-code as the canonical Claude Code
adapter directory aligned with the claude-code registry identity.
- >-
Add adapter.yaml and capabilities.yaml for Claude Code and establish
their reusable schemas for all peers.
- >-
Standardize all memory-domain operations on the shared l9-memory-mcp CLI
commands: hydrate, conflicts check, claim acquire, claim verify, claim
release, ingest, doctor, capabilities, and version where supported by
the verified CLI contract.
- >-
Define a stable automation-grade CLI contract with structured JSON
envelopes, typed errors, documented exit codes, request identifiers,
non-interactive operation, timeouts, protocol negotiation, identity
confirmation, and idempotency.
- >-
Build a shared lifecycle runtime that normalizes native agent events,
collects repository context, classifies operations, evaluates shared
policy profiles, invokes l9-memory-mcp, validates responses, stores
minimal receipts, manages durable ingestion, emits structured audit
events, and applies explicit failure modes.
- >-
Define peer-neutral lifecycle events and state transitions covering
session initialization, hydration, operation proposal, governed
mutation proposal, irreversible boundary proposal, session finalization,
aborted sessions, delivery retry, degraded read-only operation,
coordination unavailability, claim expiry, identity failure, protocol
incompatibility, ingest queuing, and break-glass operation.
- >-
Preserve deterministic governance for protected-root edits, canonical
policy edits, commits, pushes, merges, pull-request creation and merge,
memory namespace promotion, destructive memory operations, and other
policy-classified governed boundaries.
- >-
Bind claims and verification to the authenticated agent principal,
canonical repository identity, branch, base revision, governed path
scope or scope digest, allowed operation classes, server-issued lease,
and exact candidate state.
- >-
Prevent local receipt or state files from independently granting
authority by requiring server-issued evidence or live claim
verification before governed boundaries.
- >-
Implement automatic, idempotent MCP ingestion with a durable local
delivery journal, bounded retry, crash recovery, secret redaction,
acknowledgement handling, and replay before subsequent hydration.
- >-
Separate harness-produced provenance from model-produced semantic
summaries in memory episode envelopes.
- >-
Define reusable policy profiles for observer, reviewer, implementer,
maintainer, orchestrator, and administrator responsibilities rather than
encoding governance rules per adapter.
- >-
Define deterministic effect-based operation classifications, including
read-only, local non-governed mutation, governed file mutation, commit,
push, merge, pull-request operations, authority promotion, destructive
memory operations, and unknown potentially mutating behavior.
- >-
Build adapter schemas, schema validation, cross-reference validation,
identity consistency checks, architecture fitness functions, forbidden
dependency checks, and direct-memory-transport prevention.
- >-
Build a peer-neutral conformance suite whose required tests are selected
from each adapter’s declared capabilities.
- >-
Build an end-to-end harness using temporary repositories, temporary Git
remotes, multiple agent identities, the real shared CLI, a controlled
MCP test service, native surface simulation, structured event capture,
and fault injection.
- >-
Validate hydration continuity, overlapping claims, non-overlapping
concurrency, claim expiry, claim revocation, scope expansion, identity
spoofing, MCP outages, protocol incompatibility, ingestion
idempotency, crash recovery, installation, upgrade, rollback, and
bypass attempts.
- >-
Capture behavioral fixtures from the existing Claude Code pipeline and
compare legacy and shared-CLI behavior before deleting the legacy
implementation.
- >-
Support legacy, MCP shadow, and MCP enforced migration modes with
measurable equivalence criteria and reversible cutover.
- >-
Execute a controlled Claude Code canary sequence before broad
enforcement and before deletion of legacy memory components.
- >-
Remove Claude Code-specific memory transport, memory-domain schemas,
conflict algorithms, locally authoritative lock state, duplicate
identity handling, obsolete validation targets, and obsolete tests only
after replacement controls pass all cutover gates.
- >-
Update agent registry integration, adapter validation, adapter contract,
memory topology documentation, relevant governance documentation,
architecture decisions, setup paths, installer behavior, and CI without
weakening protected-root controls.
- >-
Provide a generator and implementation guide enabling new peer adapters
to be created from canonical contracts without copying Claude-specific
implementation.
- >-
Prove platform reuse by onboarding or validating at least one second
peer without changing the shared runtime, canonical lifecycle model, or
foundational schemas.

exclude:
  - >-
    Replacing, redesigning, or migrating the separate legacy self-hosted
    Graphiti or SSH-tunnel memory system outside the accepted shared MCP
    adapter scope.
  - >-
    Modifying the internal storage architecture, graph model, ranking
    algorithms, or unrelated domain behavior of the shared memory service
    unless a verified incompatibility blocks the adapter contract.
  - >-
    Creating a new Claude-specific MCP protocol client, HTTP client,
    conflict algorithm, authorization layer, memory schema, or independent
    source of memory truth.
  - >-
    Reducing deterministic governance to bootstrap prose, optional model
    instructions, voluntary conflict checks, or voluntary session
    writeback.
  - >-
    Treating visual directory parity as requiring all agent surfaces to
    discard stronger native lifecycle enforcement capabilities.
  - >-
    Allowing an adapter to select or spoof identity through unverified
    headers, command arguments, mutable workspace files, or locally
    editable receipts.
  - >-
    Persisting bearer tokens, hydrated memory contents, prompts, arbitrary
    environment variables, or secrets in session receipts, audit events, or
    delivery journals.
  - >-
    Placing mutable runtime state, gate verdicts, task attempts, leases,
    Program Lock state, or Controller state in immutable campaign sources,
    the accepted Blueprint, Cursor-Governance source directories, or target
    repository worktrees.
  - >-
    Granting autonomous authority to push branches, create or merge pull
    requests, publish packages, create releases, modify repository rules,
    deploy, migrate, cut over production traffic, perform destructive
    actions, or send external stakeholder communications.
  - >-
    Deleting the legacy Claude Code memory implementation before shadow
    equivalence, negative-path testing, rollback rehearsal, canary
    enforcement, and independent cutover verification pass.
  - >-
    Declaring every peer production-certified solely because the reference
    contracts and Claude Code implementation exist.
  - >-
    Widening the campaign into unrelated agent orchestration, general IDE
    configuration, model selection, prompt optimization, or repository
    modernization work.
  - >-
    Treating local command success, worker completion, or model statements
    as proof of remote mutation, independent verification, durable memory
    ingestion, or server-side authorization.
  - >-
    Executing campaign tasks, mutating the target repository, committing,
    pushing, opening a pull request, merging, releasing, publishing, or
    deploying as part of campaign artifact preparation.

contracts:
blueprint: program-execution-blueprint.v2
controller_minimum: program-execution-controller.v2
pair: program-execution-system.v2

authority_order:
- applicable_safety_legal_security_requirements
- cursor_governance_canonical_law
- program_execution_v2_interface_contract
- latest_explicit_operator_instruction
- latest_accepted_program_decision
- accepted_architecture_and_contracts
- verified_current_state_evidence
- approved_task_card
- exact_rendered_source_contract
- repository_local_governance
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
- passing_local_command_is_not_remote_event_proof
- tag_release_and_package_publication_are_distinct_events
- runtime_state_remains_outside_source_and_target_worktrees
- shared_cli_is_the_only_adapter_memory_transport
- memory_service_is_the_authority_for_identity_claims_conflicts_and_ingestion
- adapter_runtime_may_translate_and_enforce_but_may_not_reimplement_memory_semantics
- native_surface_strength_may_be_preserved_but_not_weakened_for_visual_parity
- governed_boundaries_require_current_server_verifiable_authority
- unknown_potentially_mutating_operations_follow_profile_failure_policy
- local_receipts_never_independently_grant_mutation_authority
- authenticated_principal_must_match_registry_manifest_and_effective_adapter_identity
- claim_scope_must_cover_the_exact_candidate_diff_and_operation
- irreversible_boundaries_require_fresh_claim_verification
- memory_outage_never_silently_grants_mutation_authority
- session_ingestion_is_automatic_durable_idempotent_and_recoverable
- writeback_failure_queues_evidence_and_does_not_fabricate_delivery
- model_generated_semantics_are_separate_from_harness_generated_provenance
- declared_adapter_capabilities_require_passing_conformance_evidence
- legacy_behavior_is_removed_only_after_proven_replacement_equivalence
- shadow_execution_must_not_duplicate_claims_ingestion_or_authority
- rollback_must_restore_operational_safety_not_only_source_files
- adapter_contract_runtime_cli_and_service_versions_are_explicitly_compatible
- secrets_are_never_persisted_or_emitted_in_adapter_state_or_logs
- break_glass_is_human_controlled_time_bounded_reasoned_and_audited
- architecture_fitness_functions_continuously_prevent_adapter_divergence
- foundational_reuse_is_not_proven_until_a_second_peer_adopts_without_core_changes

terminal_verdicts:
- CONVERGED
- CONVERGED_WITH_NON_BLOCKING_RISKS
- NOT_CONVERGED
- INCONCLUSIVE