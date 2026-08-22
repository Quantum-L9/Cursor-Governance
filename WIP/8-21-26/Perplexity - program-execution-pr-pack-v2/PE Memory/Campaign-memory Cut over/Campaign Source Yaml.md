schema: l9.program-execution.campaign-source.v2
schema_version: 2.0.0

CANONICAL ROLE

This file is the immutable, campaign-specific authority seed for the shared

MCP memory adapter foundation and Claude Code reference migration.

The admitted source must be preserved byte-for-byte outside target worktrees.

Cursor-Governance compiles this source into the native Program Execution v2

Blueprint, Controller Program Lock, adapter contracts, and runtime receipts.

This file contains program definition only. It never stores mutable task

status, gate verdicts, leases, attempts, claims, runtime receipts, or

Controller state.

metadata:
campaign_id: shared-mcp-memory-adapter-foundation
title: Shared MCP Memory Adapter Foundation and Claude Code Reference Migration
version: 1.0.0
created_at: “2026-08-04T22:03:00Z”
status: operator_intake
owner: UNKNOWN
intended_host: Quantum-L9/Cursor-Governance
intended_drop_path: >-
environment/program-execution/campaigns/shared-mcp-memory-adapter-foundation/CAMPAIGN_SOURCE.yaml
runtime_root: “$HOME/.l9/programs/shared-mcp-memory-adapter-foundation”
worktree_root: “$HOME/.l9/program-worktrees/shared-mcp-memory-adapter-foundation”
source_is_immutable: true
remote_mutation_during_admission: false

integrity:
digest_algorithm: sha256
canonical_encoding: utf-8
canonical_line_endings: lf
digest_record_location: controller/admission/source-integrity-receipt.json
generated_counts_or_digests_may_be_hand_edited: false

pipeline_contract:
pair: program-execution-system.v2
blueprint: program-execution-blueprint.v2
controller: program-execution-controller.v2

required_host_surfaces:
- environment/program-execution/core
- environment/program-execution/adapters
- environment/program-execution/conformance
- environment/program-execution/registry
- environment/program-execution/integrations
- environment/agents
- environment/agents/adapters
- environment/agents/contracts
- environment/agents/runtime
- environment/agents/conformance
- environment/agents/policy
- environment/agents/tools
- environment/agents/docs

compilation_sequence:
- preserve_immutable_campaign_source
- instantiate_native_blueprint_and_controller
- compile_source_into_complete_native_blueprint
- collect_and_bind_current_state_evidence
- validate_blueprint_in_template_mode
- resolve_or_explicitly_bound_material_decisions_and_unknowns
- accept_blueprint_only_after_evidence_and_authority_resolution
- validate_blueprint_in_instantiated_mode
- bootstrap_controller_and_create_program_lock
- reconcile_exact_targets
- probe_adapters_and_validate_conformance
- execute_foundation_contract_and_runtime_tasks
- execute_claude_code_reference_adapter_tasks
- run_legacy_and_shared_cli_shadow_comparison
- run_canary_enforcement_and_fault_injection
- certify_reference_adapter
- validate_second_peer_reuse_without_core_changes
- remove_superseded_claude_specific_memory_pipeline
- record_attempt_and_verification_receipts
- evaluate_evidence_backed_gates
- prepare_exact_remote_approval_packets
- export_controller_handoff_receipt
- obtain_program_owner_terminal_verdict

authority_boundaries:
campaign_source_owns: operator_intent_and_campaign_semantics
blueprint_owns: accepted_program_definition
controller_owns: mutable_runtime_state_and_gate_results
adapters_own: native_surface_translation_and_execution_receipts
shared_adapter_runtime_owns: lifecycle_normalization_policy_evaluation_and_local_delivery_mechanics
shared_cli_owns: MCP_transport_protocol_negotiation_authentication_retries_and_machine_readable_results
memory_service_owns: memory_truth_identity_binding_claims_conflicts_authorization_and_ingestion
activation_prompt_owns: launch_mechanics_only

operator_directive:
objective: >-
Establish a canonical peer-neutral memory adapter platform that uses the
shared l9-memory-mcp CLI for all memory-domain operations, proves the
platform through a hardened Claude Code reference implementation, removes
Claude Code’s bespoke memory pipeline without weakening deterministic
governance, and makes the resulting contracts, runtime, tooling, and tests
reusable by all current and future peers.

mode: controlled_autonomous_until_material_boundary

auto_continue:
- read_only_inspection
- campaign_source_preservation
- evidence_collection
- blueprint_materialization
- schema_materialization
- reversible_repo_local_work
- local_validation
- independent_verification
- shadow_mode_execution_without_duplicate_authority_or_side_effects
- local_commits_when_explicitly_authorized
- bounded_retry_of_transient_failures
- read_only_remote_observation
- unrelated_ready_work_when_one_subgraph_is_blocked
- preparation_of_exact_approval_packets
- generation_of_reversible_adapter_scaffolding
- execution_of_ephemeral_test_environments
- temporary_test_repository_and_remote_creation
- non_production_fault_injection

pause_only_for:
- missing_or_conflicting_semantic_authority
- unresolved_program_owner_identity
- material_scope_expansion
- stale_or_invalid_program_lock
- unresolved_blocking_unknown
- failed_blocking_gate
- security_secret_or_privacy_boundary
- unsupported_or_incompatible_shared_cli_contract
- memory_service_identity_binding_failure
- architectural_equivalence_failure
- any_unsafe_shadow_or_canary_divergence
- exact_remote_mutation_approval
- exact_push_pull_request_merge_tag_release_publish_deploy_or_migration_approval
- exact_destructive_action_approval
- deletion_of_legacy_pipeline_before_all_cutover_gates_pass
- broad_peer_rollout_before_reference_adapter_certification
- release_or_activation_of_adapter_contract_as_canonical_standard

program:
id: shared-mcp-memory-adapter-foundation
name: Shared MCP Memory Adapter Foundation and Claude Code Reference Migration
version: 1.0.0
owner: UNKNOWN
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
declaration, regression prevention, or portable end-to-end certification.
Direct deletion of Claude Code’s pipeline in favor of model instructions
would remove enforceable controls and restore omission risks. The campaign
must therefore establish a canonical platform in which the shared CLI owns
MCP transport, the memory service owns memory truth and authorization, the
shared runtime owns lifecycle normalization and enforcement mechanics, and
each peer adapter owns only native surface translation.

target_state: >-
Cursor-Governance contains a versioned, schema-governed, peer-neutral memory
adapter foundation under environment/agents with canonical manifests,
capabilities declarations, lifecycle events, operation classifications,
policy profiles, session receipts, memory episode contracts, delivery
journal contracts, CLI response contracts, compatibility rules,
architecture fitness functions, a shared lifecycle runtime, adapter
generation tooling, and reusable conformance and end-to-end test harnesses.
Claude Code is the first certified reference adapter at
environment/agents/adapters/claude-code and performs hydration, conflict
checks, claim acquisition, claim verification, claim release, and ingestion
exclusively through the shared l9-memory-mcp CLI. Claude-specific memory
transport, local memory semantics, duplicate schemas, locally authoritative
lock state, and duplicate identity logic are removed only after behavioral
fixtures, shadow comparison, canary enforcement, fault injection, rollback
rehearsal, and independent verification prove functional and governance
equivalence. Deterministic controls remain active for governed operations,
claims are bound to authenticated identity and exact repository state,
session ingestion is durable and idempotent, degraded behavior is explicit,
and at least one second peer can adopt the foundation without changing the
shared runtime or canonical schemas.

scope:
include:
- Canonical peer-neutral adapter manifest schema and validation.
- Canonical capabilities.yaml schema and capability-derived conformance obligations.
- Claude Code adapter.yaml and capabilities.yaml implementation.
- Shared l9-memory-mcp CLI integration for hydrate, conflicts check, claim acquire, claim verify, claim release, ingest, doctor, capabilities, and version where verified available.
- Stable machine-readable CLI response envelope and typed error contract.
- Shared CLI exit-code, timeout, request-ID, idempotency, protocol-negotiation, and non-interactive behavior.
- Shared adapter lifecycle runtime.
- Peer-neutral lifecycle event model.
- Explicit adapter session state machine and failure states.
- Deterministic operation classifier.
- Reusable policy profiles for observer, reviewer, implementer, maintainer, orchestrator, and administrator roles.
- Authenticated identity binding across registry, adapter manifest, runtime configuration, CLI response, and memory-service principal.
- Repository, branch, base revision, candidate revision, operation, scope, and lease binding for claims.
- Server-side conflict truth and claim authorization.
- Fresh claim verification before governed mutation and irreversible boundaries.
- Explicit degraded read-only behavior during memory or coordination unavailability.
- Durable local ingestion journal outside repositories and target worktrees.
- Idempotent session ingestion and crash recovery.
- Separation of harness-generated provenance from model-generated semantic summaries.
- Secret redaction and bounded memory episode payload validation.
- Architecture fitness functions preventing direct adapter memory transport or duplicated memory semantics.
- Shared adapter generator and implementation guide.
- Shared conformance suite selected from declared adapter capabilities.
- Real-CLI contract tests against a controlled MCP test service.
- Multi-agent end-to-end harness with temporary repositories and remotes.
- Concurrent overlapping and non-overlapping claim scenarios.
- Stale lease, claim expiry, claim revocation, and scope-expansion tests.
- Identity spoofing and authorization-boundary tests.
- Network outage, timeout, malformed response, protocol mismatch, and rate-limit tests.
- Ingestion idempotency, replay, acknowledgement-loss, and crash-recovery tests.
- Installation, upgrade, downgrade, rollback, and repeated-setup tests.
- Command and integration bypass tests across shell, Git, GitHub CLI, native tools, and nested execution.
- Behavioral regression fixtures from the existing Claude Code pipeline.
- Legacy, MCP-shadow, and MCP-enforced migration modes.
- Canary activation and explicit rollback rehearsal.
- Deletion of the legacy Claude-specific pipeline only after all replacement gates pass.
- Registry, contract, validator, CI, setup, documentation, ADR, topology, and protected-root updates.
- Second-peer adoption proof without changing the shared runtime or canonical schemas.
- Evidence-backed campaign closeout and human terminal verdict.

exclude:
  - Redesign of the shared memory service internal storage model.
  - Replacement or migration of unrelated self-hosted Graphiti or SSH-tunnel systems.
  - Creation of a new Claude-specific HTTP or MCP protocol client.
  - Creation of Claude-specific conflict, claim, authorization, or ingestion semantics.
  - Model-only hydration, voluntary conflict checking, or optional writeback as substitutes for deterministic controls.
  - Removal of stronger surface-native enforcement solely for visual directory parity.
  - Local receipt files acting as independent authorization sources.
  - Bearer token, hydrated memory content, prompt, or secret persistence in adapter state or logs.
  - Mutable runtime state inside immutable campaign sources, accepted Blueprints, governance source directories, or target repository worktrees.
  - Autonomous branch push, pull-request creation, merge, tag, package publication, release, deployment, migration, destructive action, or external stakeholder communication.
  - Deletion of the legacy Claude Code pipeline before successful shadow, canary, rollback, fault-injection, and independent verification gates.
  - Production certification of all peers solely from Claude Code certification.
  - General model-selection, prompt-optimization, IDE-modernization, or unrelated orchestration work.
  - Claims that local command success proves remote mutation or durable server-side memory acceptance.
  - Campaign execution, repository mutation, commit, push, pull-request creation, merge, release, publication, or deployment during campaign-source preparation.

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
- memory_service_is_authoritative_for_identity_claims_conflicts_and_ingestion
- adapter_runtime_may_translate_and_enforce_but_may_not_reimplement_memory_semantics
- native_surface_enforcement_strength_may_not_be_weakened_for_visual_parity
- governed_boundaries_require_current_server_verifiable_authority
- unknown_potentially_mutating_operations_follow_profile_failure_policy
- local_receipts_never_independently_grant_mutation_authority
- authenticated_principal_must_match_registry_manifest_runtime_and_service_identity
- claim_scope_must_cover_exact_candidate_diff_and_operation
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

targets:

* id: TARGET-001
    name: Cursor-Governance Repository
    kind: git_repository
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: Quantum-L9/Cursor-Governance
    environments:
    * local
    * ci
    * github
        mutability: reversible
        expected_revision: UNKNOWN
        adapter: claude-code
* id: TARGET-002
    name: Program Execution Control Plane
    kind: program_control
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: program_control
    repository_id: null
    source_of_truth: environment/program-execution
    environments:
    * local
        mutability: controlled
        expected_revision: UNKNOWN
        adapter: controller
* id: TARGET-003
    name: Agent Adapter Foundation
    kind: repository_subsystem
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/agents
    environments:
    * local
    * ci
        mutability: reversible
        expected_revision: UNKNOWN
        adapter: claude-code
* id: TARGET-004
    name: Claude Code Reference Adapter
    kind: adapter
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/agents/adapters/claude-code
    environments:
    * local
    * ci
    * claude-code
        mutability: reversible
        expected_revision: UNKNOWN
        adapter: claude-code
* id: TARGET-005
    name: Existing Claude Code Memory Pipeline
    kind: legacy_repository_subsystem
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/claude-code
    environments:
    * local
    * ci
    * claude-code
        mutability: controlled
        expected_revision: UNKNOWN
        adapter: claude-code
* id: TARGET-006
    name: Shared l9-memory-mcp CLI
    kind: external_cli
    authority_owner: UNKNOWN
    execution_mode: external_tool
    repository_id: null
    source_of_truth: installed_or_pinned_l9-memory-mcp_distribution
    environments:
    * local
    * ci
    * test
        mutability: read_only
        expected_revision: UNKNOWN
        adapter: external_cli
* id: TARGET-007
    name: Shared MCP Memory Service
    kind: external_service
    authority_owner: UNKNOWN
    execution_mode: external_service
    repository_id: null
    source_of_truth: l9-shared-memory
    environments:
    * test
    * staging_or_equivalent
    * production_or_equivalent
        mutability: controlled
        expected_revision: UNKNOWN
        adapter: mcp
* id: TARGET-008
    name: Controlled MCP Contract Test Service
    kind: ephemeral_test_service
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: local_ephemeral
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/agents/conformance
    environments:
    * local
    * ci
        mutability: ephemeral
        expected_revision: UNKNOWN
        adapter: test_harness
* id: TARGET-009
    name: Adapter Conformance and E2E Harness
    kind: repository_subsystem
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/agents/conformance
    environments:
    * local
    * ci
        mutability: reversible
        expected_revision: UNKNOWN
        adapter: claude-code
* id: TARGET-010
    name: GitHub CI and Pull Request Surfaces
    kind: external_ci_and_repository_service
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: remote_observation_and_approval_gated_mutation
    repository_id: quantum-l9-cursor-governance
    source_of_truth: GitHub
    environments:
    * github
    * ci
        mutability: approval_gated
        expected_revision: UNKNOWN
        adapter: github
* id: TARGET-011
    name: Peer Adapter Validation Target
    kind: adapter
    authority_owner: Quantum-L9/Cursor-Governance
    execution_mode: repo_local
    repository_id: quantum-l9-cursor-governance
    source_of_truth: environment/agents/adapters
    environments:
    * local
    * ci
        mutability: reversible
        expected_revision: UNKNOWN
        adapter: selected_second_peer
* id: TARGET-012
    name: External Adapter Runtime State Root
    kind: filesystem_runtime
    authority_owner: Program Execution Controller
    execution_mode: external_runtime
    repository_id: null
    source_of_truth: “$HOME/.l9”
    environments:
    * local
    * ci
        mutability: ephemeral_and_recoverable
        expected_revision: UNKNOWN
        adapter: shared_runtime

authorities:

* id: AUTH-001
    responsibility: program_ownership_and_terminal_verdict
    owner: UNKNOWN
    authority_type: human_owner
    scope:
    * whole_program
        may_delegate: false
        required_evidence:
    * explicit_owner_identity
    * controller_handoff_receipt
* id: AUTH-002
    responsibility: canonical_cursor_governance_repository_authority
    owner: Quantum-L9/Cursor-Governance
    authority_type: repository_authority
    scope:
    * TARGET-001
    * TARGET-003
    * TARGET-004
    * TARGET-005
    * TARGET-009
    * TARGET-011
        may_delegate: true
        required_evidence:
    * CANONICAL_LAW.md
    * AGENTS.md
    * CODEOWNERS
    * repository_governance
* id: AUTH-003
    responsibility: program_execution_v2_contract_authority
    owner: Quantum-L9/Cursor-Governance
    authority_type: subsystem_authority
    scope:
    * TARGET-002
        may_delegate: false
        required_evidence:
    * program_execution_interface_contract
    * current_blueprint_schema
    * current_controller_schema
    * native_validator_results
* id: AUTH-004
    responsibility: shared_adapter_architecture_and_contracts
    owner: Quantum-L9/Cursor-Governance
    authority_type: architecture_authority
    scope:
    * TARGET-003
    * TARGET-004
    * TARGET-009
    * TARGET-011
        may_delegate: true
        required_evidence:
    * accepted_architecture_decision
    * adapter_contract
    * schema_validation
    * conformance_results
* id: AUTH-005
    responsibility: claude_code_surface_integration
    owner: Quantum-L9/Cursor-Governance
    authority_type: repository_domain_owner
    scope:
    * TARGET-004
    * TARGET-005
        may_delegate: true
        required_evidence:
    * claude_code_settings_contract
    * lifecycle_mapping_contract
    * reference_adapter_tests
* id: AUTH-006
    responsibility: shared_cli_contract_and_distribution
    owner: UNKNOWN
    authority_type: external_system_owner
    scope:
    * TARGET-006
        may_delegate: false
        required_evidence:
    * cli_version_output
    * cli_capabilities_output
    * cli_contract_documentation
    * release_provenance
    * checksum_or_signature_verification
* id: AUTH-007
    responsibility: shared_memory_service_identity_claim_conflict_and_ingestion_semantics
    owner: UNKNOWN
    authority_type: external_service_owner
    scope:
    * TARGET-007
        may_delegate: false
        required_evidence:
    * service_capability_probe
    * identity_binding_test
    * claim_and_conflict_contract
    * ingestion_idempotency_test
    * audit_evidence
* id: AUTH-008
    responsibility: adapter_identity_registry_and_role_binding
    owner: Quantum-L9/Cursor-Governance
    authority_type: governance_registry_authority
    scope:
    * TARGET-003
    * TARGET-004
    * TARGET-011
        may_delegate: true
        required_evidence:
    * agent_registry
    * adapter_manifest
    * capabilities_declaration
    * identity_consistency_validation
* id: AUTH-009
    responsibility: security_secret_handling_and_identity_spoofing_controls
    owner: UNKNOWN
    authority_type: security_authority
    scope:
    * whole_program
        may_delegate: false
        required_evidence:
    * security_review
    * secret_redaction_tests
    * identity_spoofing_negative_tests
    * token_handling_inspection
* id: AUTH-010
    responsibility: independent_verification_and_conformance
    owner: Program Execution Controller
    authority_type: independent_verification_authority
    scope:
    * whole_program
        may_delegate: true
        required_evidence:
    * verification_receipts
    * exact_candidate_revision
    * conformance_test_results
    * e2e_results
    * fault_injection_results
* id: AUTH-011
    responsibility: github_remote_mutation_and_repository_promotion
    owner: UNKNOWN
    authority_type: human_remote_action_authority
    scope:
    * TARGET-010
        may_delegate: false
        required_evidence:
    * exact_candidate_revision
    * exact_remote_action_approval
    * passing_required_checks
    * rollback_packet
* id: AUTH-012
    responsibility: legacy_pipeline_removal_and_cutover
    owner: UNKNOWN
    authority_type: human_cutover_authority
    scope:
    * TARGET-004
    * TARGET-005
        may_delegate: false
        required_evidence:
    * shadow_equivalence_receipt
    * canary_receipt
    * rollback_rehearsal_receipt
    * independent_cutover_verification
    * exact_deletion_diff
* id: AUTH-013
    responsibility: second_peer_selection_and_reuse_certification
    owner: UNKNOWN
    authority_type: architecture_and_program_authority
    scope:
    * TARGET-011
        may_delegate: true
        required_evidence:
    * selected_peer_decision
    * unchanged_shared_runtime_diff
    * unchanged_canonical_schema_diff
    * second_peer_conformance_results

evidence_requirements:

* id: EVID-001
    claim: canonical_governance_host_and_program_execution_v2_surfaces_are_available
    source_type: repository_inspection
    source_location: “$HOME/.cursor-governance”
    collection_method: read_only_inspection_and_repository_owned_validation
    freshness: collect_at_admission
    producer: operator
    supports:
    * program_admission
    * authority_lock
    * blueprint_instantiation
        contradicts: []
* id: EVID-002
    claim: cursor_governance_repository_identity_revision_branch_and_worktree_state_are_known
    source_type: repository_inspection
    source_location: active_cursor_governance_workspace
    collection_method: git_status_branch_head_remote_and_worktree_inspection
    freshness: collect_at_admission_and_before_each_mutating_task
    producer: operator
    supports:
    * current_state_lock
    * source_contract_generation
    * candidate_revision_binding
        contradicts: []
* id: EVID-003
    claim: current_adapter_registry_contract_and_existing_peer_adapter_layout_are_known
    source_type: repository_inspection
    source_location: environment/agents
    collection_method: read_only_schema_contract_registry_and_adapter_inspection
    freshness: collect_at_admission
    producer: operator
    supports:
    * adapter_foundation_design
    * claude_code_adapter_materialization
    * second_peer_reuse_validation
        contradicts: []
* id: EVID-004
    claim: existing_claude_code_memory_pipeline_behavior_and_wiring_are_completely_inventoried
    source_type: repository_inspection
    source_location: environment/claude-code
    collection_method: read_only_code_settings_tests_makefile_ci_and_documentation_inspection
    freshness: collect_before_legacy_fixture_generation
    producer: operator
    supports:
    * legacy_behavioral_fixture_set
    * migration_scope
    * safe_deletion_plan
    * rollback_plan
        contradicts: []
* id: EVID-005
    claim: current_ADR_0002_invariants_and_governance_requirements_are_known
    source_type: repository_inspection
    source_location: docs/decisions
    collection_method: read_only_ADR_and_cross_reference_inspection
    freshness: collect_before_architecture_decision_update
    producer: operator
    supports:
    * deterministic_enforcement_invariant
    * ADR_supersession_or_amendment
    * regression_prevention
        contradicts: []
* id: EVID-006
    claim: shared_l9_memory_mcp_cli_is_installed_or_resolvable_with_verified_version_and_provenance
    source_type: command_and_distribution_inspection
    source_location: TARGET-006
    collection_method: cli_version_capabilities_doctor_and_release_provenance_inspection
    freshness: collect_at_admission_and_before_CLI_contract_tests
    producer: operator
    supports:
    * CLI_compatibility_lock
    * shared_transport_integration
    * supply_chain_validation
        contradicts: []
* id: EVID-007
    claim: shared_cli_supports_required_commands_and_machine_readable_automation_contract
    source_type: command_contract_probe
    source_location: TARGET-006
    collection_method: inspect_help_version_capabilities_and_execute_non_mutating_contract_probes
    freshness: collect_before_runtime_implementation
    producer: operator
    supports:
    * hydrate_integration
    * conflicts_check_integration
    * claim_acquire_integration
    * claim_verify_integration
    * claim_release_integration
    * ingest_integration
    * doctor_and_capability_checks
        contradicts: []
* id: EVID-008
    claim: shared_memory_service_endpoint_identity_binding_and_protocol_compatibility_are_verified
    source_type: external_service_probe
    source_location: TARGET-007
    collection_method: authenticated_non_mutating_MCP_probe_and_identity_mismatch_negative_test
    freshness: collect_before_reference_adapter_integration
    producer: operator
    supports:
    * service_compatibility
    * identity_security
    * claim_authorization
    * ingestion_authority
        contradicts: []
* id: EVID-009
    claim: bearer_principal_cannot_be_overridden_by_forged_agent_headers_or_mutable_adapter_fields
    source_type: security_test
    source_location: TARGET-007
    collection_method: controlled_identity_spoofing_negative_tests
    freshness: collect_before_canary_enforcement
    producer: independent_verifier
    supports:
    * identity_binding_gate
    * security_gate
        contradicts: []
* id: EVID-010
    claim: adapter_manifest_and_capabilities_schemas_validate_all_required_peer_neutral_fields
    source_type: schema_validation
    source_location: environment/agents/contracts
    collection_method: repository_owned_schema_and_cross_reference_validation
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * contract_gate
    * reference_adapter_gate
    * second_peer_gate
        contradicts: []
* id: EVID-011
    claim: shared_lifecycle_runtime_has_no_direct_memory_transport_or_duplicated_memory_semantics
    source_type: architecture_fitness_test
    source_location: environment/agents/runtime
    collection_method: static_dependency_AST_forbidden_pattern_and_network_boundary_tests
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * architecture_conformance
    * no_duplicate_authority
    * shared_CLI_only_transport
        contradicts: []
* id: EVID-012
    claim: operation_classifier_covers_governed_non_governed_and_unknown_mutating_effects
    source_type: unit_and_property_test
    source_location: environment/agents/runtime
    collection_method: command_corpus_native_event_and_effect_classification_tests
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * mutation_boundary_enforcement
    * bypass_prevention
    * policy_profile_validation
        contradicts: []
* id: EVID-013
    claim: claims_are_bound_to_authenticated_identity_repository_branch_revision_scope_operation_and_lease
    source_type: integration_test
    source_location: TARGET-007
    collection_method: controlled_claim_acquire_verify_expire_revoke_and_scope_change_tests
    freshness: collect_before_canary_enforcement
    producer: independent_verifier
    supports:
    * claim_security
    * stale_claim_rejection
    * scope_expansion_control
        contradicts: []
* id: EVID-014
    claim: local_session_receipts_cannot_independently_grant_authority
    source_type: security_and_state_test
    source_location: TARGET-012
    collection_method: receipt_tampering_symlink_owner_permission_and_live_reverification_tests
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * local_state_safety
    * claim_verification_gate
        contradicts: []
* id: EVID-015
    claim: session_ingestion_is_durable_idempotent_secret_safe_and_recoverable
    source_type: integration_and_fault_injection_test
    source_location: environment/agents/conformance
    collection_method: duplicate_timeout_crash_acknowledgement_loss_replay_redaction_and_payload_limit_tests
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * ingestion_gate
    * crash_recovery
    * memory_continuity
        contradicts: []
* id: EVID-016
    claim: controlled_MCP_test_service_and_real_CLI_contract_suite_are reproducible_in_local_and_CI_environments
    source_type: test_environment_validation
    source_location: TARGET-008
    collection_method: clean_environment_setup_and_repeated_execution
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * CLI_contract_gate
    * CI_gate
    * peer_conformance
        contradicts: []
* id: EVID-017
    claim: Claude_Code_reference_adapter_maps_native_events_to_canonical_lifecycle_events_without_semantic_drift
    source_type: adapter_integration_test
    source_location: TARGET-004
    collection_method: native_hook_event_fixture_and_state_machine_transition_tests
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * reference_adapter_certification
    * lifecycle_conformance
        contradicts: []
* id: EVID-018
    claim: existing_and_new_memory_pipeline_behaviors_have_zero_unexplained_unsafe_divergence
    source_type: shadow_comparison
    source_location: TARGET-004
    collection_method: legacy_and_shared_CLI_fixture_comparison_with_structured_equivalence_results
    freshness: collect_before_MCP_enforced_cutover
    producer: independent_verifier
    supports:
    * shadow_equivalence_gate
    * legacy_pipeline_removal
        contradicts: []
* id: EVID-019
    claim: governed_actions_are_denied_without_valid_hydration_claim_and_fresh_verification
    source_type: end_to_end_enforcement_test
    source_location: TARGET-009
    collection_method: real_hook_real_CLI_controlled_service_and_temporary_repository_scenarios
    freshness: collect_before_canary_cutover
    producer: independent_verifier
    supports:
    * deterministic_enforcement
    * protected_boundary_safety
        contradicts: []
* id: EVID-020
    claim: competing_agents_are_serialized_or_rejected_for_overlapping_scope_and_allowed_for_safe_non_overlapping_scope
    source_type: multi_agent_end_to_end_test
    source_location: TARGET-009
    collection_method: concurrent_multi_identity_claim_and_mutation_scenarios
    freshness: collect_before_reference_adapter_certification
    producer: independent_verifier
    supports:
    * concurrency_gate
    * conflict_detection
    * safe_parallelism
        contradicts: []
* id: EVID-021
    claim: memory_and_coordination_outages_produce_declared_degraded_states_without_silent_authority_widening
    source_type: fault_injection_test
    source_location: TARGET-009
    collection_method: timeout_connection_reset_rate_limit_server_error_and_protocol_failure_scenarios
    freshness: collect_before_reference_adapter_certification
    producer: independent_verifier
    supports:
    * resilience_gate
    * degraded_read_only_behavior
    * fail_closed_boundaries
        contradicts: []
* id: EVID-022
    claim: install_upgrade_downgrade_repeated_setup_and_rollback_are_idempotent_and_safe
    source_type: installation_and_migration_test
    source_location: TARGET-004
    collection_method: clean_install_legacy_upgrade_partial_install_repeat_install_and_downgrade_scenarios
    freshness: collect_before_canary_activation
    producer: independent_verifier
    supports:
    * migration_gate
    * operational_rollback
        contradicts: []
* id: EVID-023
    claim: architecture_fitness_functions_prevent_reintroduction_of_direct_memory_clients_duplicate_schemas_or_local_authority
    source_type: CI_architecture_test
    source_location: TARGET-010
    collection_method: repository_static_checks_dependency_rules_and_test_time_network_restrictions
    freshness: collect_at_exact_candidate_revision_and_required_CI_run
    producer: CI
    supports:
    * regression_gate
    * long_term_architecture_conformance
        contradicts: []
* id: EVID-024
    claim: Claude_Code_canary_runs_in_MCP_enforced_mode_without_unsafe_divergence_or_lost_ingestion
    source_type: canary_execution
    source_location: TARGET-004
    collection_method: controlled_real_session_execution_with_structured_audit_and_rollback_readiness
    freshness: collect_immediately_before_legacy_removal
    producer: operator_and_independent_verifier
    supports:
    * canary_gate
    * cutover_gate
        contradicts: []
* id: EVID-025
    claim: rollback_restores_operational_safety_and_reconciles_pending_ingestion_and_claim_state
    source_type: rollback_rehearsal
    source_location: TARGET-004
    collection_method: controlled_cutover_reversal_pending_journal_replay_and_authority_reconciliation
    freshness: collect_before_legacy_removal
    producer: independent_verifier
    supports:
    * rollback_gate
    * cutover_authorization
        contradicts: []
* id: EVID-026
    claim: second_peer_adopts_canonical_contracts_without_changes_to_shared_runtime_or_foundational_schemas
    source_type: peer_adapter_conformance
    source_location: TARGET-011
    collection_method: generated_adapter_native_mapping_conformance_and_exact_shared_core_diff_inspection
    freshness: collect_before_platform_convergence
    producer: independent_verifier
    supports:
    * reusability_gate
    * platform_foundation_claim
        contradicts: []
* id: EVID-027
    claim: all_repository_owned_local_validations_pass_at_the_exact_candidate_revision
    source_type: repository_validation
    source_location: TARGET-001
    collection_method: current_make_targets_test_commands_schema_checks_and_native_validators_discovered_from_repository_help
    freshness: collect_at_exact_candidate_revision
    producer: independent_verifier
    supports:
    * regression_gate
    * PR_readiness
        contradicts: []
* id: EVID-028
    claim: required_GitHub_CI_checks_pass_for_the_exact_candidate_revision
    source_type: remote_CI_observation
    source_location: TARGET-010
    collection_method: read_only_GitHub_workflow_and_check_run_inspection
    freshness: collect_after_exact_approved_push
    producer: CI
    supports:
    * PR_and_CI_gate
    * merge_readiness
        contradicts: []
* id: EVID-029
    claim: protected_root_changes_have_required_markers_reviews_and_authority
    source_type: governance_and_review_evidence
    source_location: TARGET-001
    collection_method: diff_marker_CODEOWNERS_and_review_inspection
    freshness: collect_before_merge_approval
    producer: independent_verifier
    supports:
    * protected_root_gate
    * governance_regression_prevention
        contradicts: []
* id: EVID-030
    claim: final_handoff_is_schema_valid_revision_bound_and_complete
    source_type: controller_handoff_receipt
    source_location: controller/handoff.json
    collection_method: controller_export_and_independent_schema_validation
    freshness: collect_at_closeout
    producer: Program Execution Controller
    supports:
    * terminal_verdict_request
    * campaign_closeout
        contradicts: []

decisions:

* id: DEC-001
    question: >-
    Should the campaign preserve deterministic lifecycle enforcement while
    replacing Claude Code’s bespoke memory transport and domain logic with the
    shared l9-memory-mcp CLI and shared adapter runtime?
    authority_id: AUTH-004
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Preserve deterministic lifecycle enforcement at native mutation
        boundaries while moving transport, protocol, identity confirmation,
        claims, conflicts, and ingestion to the shared CLI and memory service.
    * id: OPTION-B
        description: >-
        Retire deterministic lifecycle enforcement and rely on model bootstrap
        instructions and voluntary MCP tool use.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-006
    * TASK-007
    * TASK-008
    * TASK-009
    * TASK-010
    * TASK-011
    * TASK-018
    * TASK-019
    * TASK-020
    * TASK-021
        required_evidence_ids:
    * EVID-004
    * EVID-005
    * EVID-017
    * EVID-019
* id: DEC-002
    question: >-
    What exact l9-memory-mcp command, JSON envelope, exit-code, timeout,
    identity, idempotency, and compatibility contract is available and will be
    treated as the canonical automation interface?
    authority_id: AUTH-006
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Adopt the verified installed CLI contract exactly as reported by
        version, capabilities, doctor, and command help output, and encode only
        supported commands and flags in the adapter foundation.
    * id: OPTION-B
        description: >-
        Define an aspirational CLI contract first and require the CLI owner to
        implement any missing behavior before adapter integration.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-004
    * TASK-005
    * TASK-008
    * TASK-009
    * TASK-010
    * TASK-011
    * TASK-012
    * TASK-013
    * TASK-014
        required_evidence_ids:
    * EVID-006
    * EVID-007
* id: DEC-003
    question: >-
    Should claim verification be performed by live server verification before
    each governed boundary, by locally verifiable server-signed capability, or
    by a hybrid mechanism?
    authority_id: AUTH-007
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Perform live claim verification through l9-memory-mcp before each
        governed irreversible boundary and treat local receipts as non-
        authoritative hints only.
    * id: OPTION-B
        description: >-
        Use server-signed short-lived capabilities that are locally
        verifiable and periodically refreshed.
    * id: OPTION-C
        description: >-
        Use live verification by default with server-signed capabilities only
        for explicitly defined degraded operation.
        recommended_option_id: OPTION-C
        selected_option_id: null
        blocking_task_ids:
    * TASK-010
    * TASK-011
    * TASK-019
    * TASK-020
    * TASK-021
        required_evidence_ids:
    * EVID-008
    * EVID-013
    * EVID-014
* id: DEC-004
    question: >-
    What failure policy applies when the memory service or shared CLI is
    unavailable during session start, ordinary local work, governed mutation,
    irreversible boundaries, and session ingestion?
    authority_id: AUTH-004
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Enter degraded read-only mode for safe inspection and analysis, fail
        closed for governed mutation and irreversible boundaries, and queue
        ingestion durably for later replay.
    * id: OPTION-B
        description: >-
        Fail closed for all operations including reads and local analysis.
    * id: OPTION-C
        description: >-
        Continue all operations with warnings and reconcile after service
        recovery.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-009
    * TASK-010
    * TASK-011
    * TASK-014
    * TASK-020
    * TASK-021
        required_evidence_ids:
    * EVID-015
    * EVID-021
* id: DEC-005
    question: >-
    Which local state location and protection model will be canonical for
    session receipts and the durable ingestion journal?
    authority_id: AUTH-004
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Use the external L9 state root under the XDG-compatible runtime path,
        with restrictive permissions, atomic writes, symlink rejection, owner
        validation, bounded retention, and no hydrated content or secrets.
    * id: OPTION-B
        description: >-
        Store session receipts and pending ingestion under the active
        repository’s .claude directory.
    * id: OPTION-C
        description: >-
        Store all adapter state in the Program Execution Controller runtime.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-009
    * TASK-014
    * TASK-015
    * TASK-017
        required_evidence_ids:
    * EVID-014
    * EVID-015
* id: DEC-006
    question: >-
    What capability and policy model will define reusable adapter guarantees
    across Claude Code and future peers?
    authority_id: AUTH-004
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Separate adapter identity and integration metadata into adapter.yaml,
        declare behavioral guarantees in capabilities.yaml, and bind policy
        through reusable role profiles.
    * id: OPTION-B
        description: >-
        Place identity, lifecycle, policy, and implementation details into one
        adapter-specific file.
    * id: OPTION-C
        description: >-
        Infer capabilities from installed files and native hook presence.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-003
    * TASK-006
    * TASK-007
    * TASK-016
    * TASK-025
        required_evidence_ids:
    * EVID-003
    * EVID-010
    * EVID-017
    * EVID-026
* id: DEC-007
    question: >-
    Which native Claude Code events and operations map to the canonical
    lifecycle model and governed operation classes?
    authority_id: AUTH-005
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Derive mappings from verified Claude Code settings, hooks, tool
        payloads, command forms, and existing pipeline behavior, then validate
        them against reusable normalized events and effect-based operation
        categories.
    * id: OPTION-B
        description: >-
        Preserve the current Claude Code hook names as the canonical lifecycle
        model for all adapters.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-006
    * TASK-007
    * TASK-008
    * TASK-017
    * TASK-019
        required_evidence_ids:
    * EVID-004
    * EVID-012
    * EVID-017
* id: DEC-008
    question: >-
    What migration mode sequence is required before the legacy Claude Code
    memory pipeline may be removed?
    authority_id: AUTH-012
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Progress through legacy, MCP shadow, MCP enforced canary, rollback
        rehearsal, independently verified cutover, and only then legacy
        deletion.
    * id: OPTION-B
        description: >-
        Replace the legacy pipeline in a single hard cutover after local tests.
    * id: OPTION-C
        description: >-
        Keep both pipelines permanently and select at runtime.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-018
    * TASK-019
    * TASK-020
    * TASK-021
    * TASK-022
    * TASK-023
        required_evidence_ids:
    * EVID-018
    * EVID-022
    * EVID-024
    * EVID-025
* id: DEC-009
    question: >-
    Which existing peer will be used as the second-adapter proof that the
    foundation is reusable without changes to shared runtime or foundational
    schemas?
    authority_id: AUTH-013
    status: proposed
    options:
    * id: OPTION-A
        description: Use Codex as the second-peer validation target.
    * id: OPTION-B
        description: Use Gemini as the second-peer validation target.
    * id: OPTION-C
        description: Use Manus as the second-peer validation target.
    * id: OPTION-D
        description: Use the generic adapter as the second-peer validation target.
        recommended_option_id: OPTION-D
        selected_option_id: null
        blocking_task_ids:
    * TASK-025
    * TASK-026
        required_evidence_ids:
    * EVID-003
    * EVID-026
* id: DEC-010
    question: >-
    Should ADR-0002 be superseded, amended, or retained after the shared CLI
    migration?
    authority_id: AUTH-004
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Supersede ADR-0002 only after the new architecture preserves its
        deterministic enforcement invariant while replacing the implementation
        mechanism.
    * id: OPTION-B
        description: >-
        Amend ADR-0002 in place to describe the new shared CLI mechanism.
    * id: OPTION-C
        description: >-
        Retain ADR-0002 unchanged and add a separate implementation ADR without
        formal supersession.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-028
    * TASK-029
        required_evidence_ids:
    * EVID-005
    * EVID-018
    * EVID-019
    * EVID-024
* id: DEC-011
    question: >-
    What exact protected-root changes and deletion markers are required for
    AGENTS.md, CANONICAL_LAW.md, or other append-only governance files?
    authority_id: AUTH-002
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Make only evidence-backed, narrowly scoped changes with exact
        ALLOW-ROOT-DELETION markers and CODEOWNERS review where the current
        governance requires them.
    * id: OPTION-B
        description: >-
        Avoid all protected-root changes and leave outdated architecture
        references in place.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-029
    * TASK-030
        required_evidence_ids:
    * EVID-001
    * EVID-005
    * EVID-029
* id: DEC-012
    question: >-
    What exact remote promotion sequence is authorized after local and CI
    validation?
    authority_id: AUTH-011
    status: proposed
    options:
    * id: OPTION-A
        description: >-
        Create a reviewable local commit stack, request exact approval for
        push, observe CI, request exact approval for pull-request creation,
        obtain required review, then request exact approval for merge.
    * id: OPTION-B
        description: >-
        Allow the campaign operator to push and open a pull request
        automatically after local validation.
        recommended_option_id: OPTION-A
        selected_option_id: null
        blocking_task_ids:
    * TASK-031
    * TASK-032
    * TASK-033
        required_evidence_ids:
    * EVID-027
    * EVID-028
    * EVID-029

unknowns:

* id: UNK-001
    statement: The explicit human program owner and terminal-verdict authority are not established in the supplied artifacts.
    status: open
    owner: operator
    blocking_task_ids:
    * TASK-001
    * TASK-033
    * TASK-034
        resolution_method: >-
        Obtain an explicit owner identity from the operator and bind it to AUTH-001
        before Blueprint acceptance.
        resolution_evidence_ids: []
* id: UNK-002
    statement: The exact current revision, branch, remote, and dirty-state baseline of Quantum-L9/Cursor-Governance are not yet collected.
    status: open
    owner: operator
    blocking_task_ids:
    * TASK-001
    * TASK-002
    * TASK-031
        resolution_method: >-
        Inspect git status, branch, HEAD, remotes, worktrees, and upstream state at
        admission without mutating the repository.
        resolution_evidence_ids:
    * EVID-002
* id: UNK-003
    statement: The current Program Execution v2 validator interfaces and exact supported invocation syntax are not yet verified.
    status: open
    owner: operator
    blocking_task_ids:
    * TASK-001
    * TASK-002
        resolution_method: >-
        Inspect repository-owned validator help output and run only supported
        template-mode validation commands.
        resolution_evidence_ids:
    * EVID-001
* id: UNK-004
    statement: The exact installed or distributable l9-memory-mcp CLI version and release provenance are not yet verified.
    status: open
    owner: AUTH-006
    blocking_task_ids:
    * TASK-004
    * TASK-005
    * TASK-013
        resolution_method: >-
        Run the verified version, capabilities, doctor, and command help
        interfaces and inspect approved release provenance or package metadata.
        resolution_evidence_ids:
    * EVID-006
    * EVID-007
* id: UNK-005
    statement: Support for claim release, doctor, capabilities, structured JSON output, request IDs, and explicit timeout flags is not yet verified.
    status: open
    owner: AUTH-006
    blocking_task_ids:
    * TASK-004
    * TASK-005
    * TASK-008
    * TASK-010
    * TASK-011
    * TASK-013
        resolution_method: >-
        Inspect the installed CLI help and capabilities output and record exact
        supported command and flag behavior without inventing missing interfaces.
        resolution_evidence_ids:
    * EVID-007
* id: UNK-006
    statement: The canonical shared memory service endpoint and environment-specific service identities are not yet verified.
    status: open
    owner: AUTH-007
    blocking_task_ids:
    * TASK-005
    * TASK-013
    * TASK-017
    * TASK-018
        resolution_method: >-
        Resolve endpoint configuration from approved adapter and deployment
        sources and execute authenticated non-mutating probes.
        resolution_evidence_ids:
    * EVID-008
* id: UNK-007
    statement: The service’s exact principal-binding and forged-header rejection behavior is not yet verified.
    status: open
    owner: AUTH-007
    blocking_task_ids:
    * TASK-005
    * TASK-010
    * TASK-019
    * TASK-020
        resolution_method: >-
        Execute controlled token/header mismatch tests and inspect server-confirmed
        principal output and audit evidence.
        resolution_evidence_ids:
    * EVID-008
    * EVID-009
* id: UNK-008
    statement: The complete current Claude Code memory hook wiring and all indirect references to the legacy pipeline are not yet inventoried.
    status: open
    owner: AUTH-005
    blocking_task_ids:
    * TASK-002
    * TASK-017
    * TASK-018
    * TASK-023
    * TASK-028
        resolution_method: >-
        Search settings, hooks, installers, Makefiles, CI, tests, commands, rules,
        docs, ADRs, and protected-root files for legacy pipeline behavior and
        references.
        resolution_evidence_ids:
    * EVID-004
* id: UNK-009
    statement: The exact legacy behavioral contract that must be preserved or intentionally replaced is not yet encoded as regression fixtures.
    status: open
    owner: AUTH-005
    blocking_task_ids:
    * TASK-018
    * TASK-019
    * TASK-020
    * TASK-023
        resolution_method: >-
        Convert current enforcement, identity, hydration, conflict, lock, and
        writeback behavior into observable golden fixtures before cutover.
        resolution_evidence_ids:
    * EVID-004
    * EVID-018
* id: UNK-010
    statement: The final canonical set of governed operation categories and protected path scopes is not yet verified against current repository governance.
    status: open
    owner: AUTH-004
    blocking_task_ids:
    * TASK-007
    * TASK-010
    * TASK-019
    * TASK-029
        resolution_method: >-
        Reconcile current governance files, operation surfaces, existing hooks,
        command forms, GitHub operations, and policy profiles into one tested
        classification contract.
        resolution_evidence_ids:
    * EVID-001
    * EVID-005
    * EVID-012
* id: UNK-011
    statement: The exact session receipt and ingestion journal storage location and cross-platform path behavior are not yet verified.
    status: open
    owner: AUTH-004
    blocking_task_ids:
    * TASK-009
    * TASK-014
    * TASK-015
        resolution_method: >-
        Validate XDG-compatible and platform-specific state roots, ownership,
        permissions, atomic writes, retention, and worktree exclusion.
        resolution_evidence_ids:
    * EVID-014
    * EVID-015
* id: UNK-012
    statement: The exact memory episode payload schema and server payload-size limits are not yet verified.
    status: open
    owner: AUTH-007
    blocking_task_ids:
    * TASK-014
    * TASK-015
    * TASK-020
        resolution_method: >-
        Inspect verified service and CLI contracts, then execute valid, oversized,
        malformed, duplicate, and secret-bearing payload tests.
        resolution_evidence_ids:
    * EVID-007
    * EVID-015
* id: UNK-013
    statement: The repository’s exact CI workflows and required checks for the target changes are not yet verified.
    status: open
    owner: AUTH-002
    blocking_task_ids:
    * TASK-027
    * TASK-031
    * TASK-032
        resolution_method: >-
        Inspect workflow definitions, branch protection, required checks, current
        Make targets, and recent CI behavior.
        resolution_evidence_ids:
    * EVID-023
    * EVID-027
    * EVID-028
* id: UNK-014
    statement: The second peer to use for platform reuse certification is not selected.
    status: open
    owner: AUTH-013
    blocking_task_ids:
    * TASK-025
    * TASK-026
        resolution_method: >-
        Compare current peer adapter maturity, native lifecycle surfaces, test
        cost, and representativeness, then record the selected option in DEC-009.
        resolution_evidence_ids:
    * EVID-003
* id: UNK-015
    statement: The exact current CODEOWNERS requirements and root-file deletion-marker syntax are not yet verified.
    status: open
    owner: AUTH-002
    blocking_task_ids:
    * TASK-029
    * TASK-030
        resolution_method: >-
        Inspect current protected-root governance, append-only checks, repository
        validators, and CODEOWNERS mappings.
        resolution_evidence_ids:
    * EVID-001
    * EVID-029
* id: UNK-016
    statement: The exact rollback mechanism for an MCP-enforced canary in the active Claude Code environment is not yet verified.
    status: open
    owner: AUTH-012
    blocking_task_ids:
    * TASK-021
    * TASK-022
    * TASK-023
        resolution_method: >-
        Define and rehearse versioned configuration rollback, legacy runtime
        restoration, pending journal replay, claim reconciliation, and audit
        recording in a controlled environment.
        resolution_evidence_ids:
    * EVID-022
    * EVID-025
* id: UNK-017
    statement: The approved token source, secret projection mechanism, and rotation behavior for Claude Code are not yet verified.
    status: open
    owner: AUTH-009
    blocking_task_ids:
    * TASK-005
    * TASK-016
    * TASK-017
    * TASK-019
        resolution_method: >-
        Inspect agent registry, installer behavior, secret source mapping, runtime
        environment projection, and token rotation behavior without exposing token
        values.
        resolution_evidence_ids:
    * EVID-003
    * EVID-008
    * EVID-009
* id: UNK-018
    statement: Whether the shared memory service supports server-signed locally verifiable capabilities is not yet known.
    status: open
    owner: AUTH-007
    blocking_task_ids:
    * TASK-010
    * TASK-011
        resolution_method: >-
        Inspect service and CLI capabilities and test any supported capability
        issuance and verification behavior.
        resolution_evidence_ids:
    * EVID-007
    * EVID-008
    * EVID-013

risks:

* id: RISK-001
    statement: Removing deterministic gates while unifying transport could reintroduce model-omission failures and allow uncoordinated governed mutation.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-004
    mitigations:
    * Preserve native mutation-boundary enforcement.
    * Require live or server-verifiable claim evidence.
    * Block legacy deletion until E2E enforcement and canary gates pass.
        triggers:
    * model_only_hydration_or_writeback
    * governed_action_allowed_without_claim_verification
    * unsafe_shadow_divergence
        affected_task_ids:
    * TASK-006
    * TASK-007
    * TASK-010
    * TASK-019
    * TASK-020
    * TASK-023
* id: RISK-002
    statement: An unstable or underspecified shared CLI contract could move divergence from Claude-specific code into every peer adapter.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-006
    mitigations:
    * Verify the actual CLI contract before runtime implementation.
    * Pin compatible versions and validate provenance.
    * Use structured envelopes, typed failures, and contract tests.
        triggers:
    * undocumented_output_change
    * unsupported_flag_assumption
    * incompatible_major_version
    * unverified_distribution
        affected_task_ids:
    * TASK-004
    * TASK-005
    * TASK-013
    * TASK-027
* id: RISK-003
    statement: Header-controlled identity could allow one adapter to impersonate another principal.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-009
    mitigations:
    * Bind identity to authenticated token principal.
    * Reject registry, manifest, header, and server-principal mismatch.
    * Add identity spoofing E2E and audit checks.
        triggers:
    * forged_header_accepted
    * mismatched_principal_reported_as_verified
    * mutable_workspace_identity_override
        affected_task_ids:
    * TASK-005
    * TASK-010
    * TASK-016
    * TASK-019
* id: RISK-004
    statement: Locally editable receipts or cached lock state could become an unauthorized mutation authority.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-004
    mitigations:
    * Store only opaque identifiers and metadata.
    * Reverify claims before governed boundaries.
    * Use restrictive external state storage and tamper tests.
        triggers:
    * local_boolean_authorizes_mutation
    * repository_state_file_grants_authority
    * symlink_or_owner_check_bypass
        affected_task_ids:
    * TASK-009
    * TASK-010
    * TASK-014
    * TASK-019
* id: RISK-005
    statement: Time-of-check to time-of-use drift could allow a claim for one diff or scope to authorize a broader candidate state.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-007
    mitigations:
    * Bind claims to base revision, branch, scope digest, and operation class.
    * Recompute candidate scope before irreversible boundaries.
    * Reject scope expansion without a new claim.
        triggers:
    * protected_path_added_after_claim
    * branch_or_base_revision_changes
    * stale_scope_digest
        affected_task_ids:
    * TASK-010
    * TASK-011
    * TASK-019
    * TASK-020
* id: RISK-006
    statement: Session writeback could be lost during process termination, outage, or acknowledgement loss.
    tier: T2
    likelihood: likely
    impact: material
    owner: AUTH-004
    mitigations:
    * Use durable append-before-send journal semantics.
    * Require idempotency keys and acknowledgement tracking.
    * Replay pending entries before next hydration.
        triggers:
    * stop_hook_timeout
    * accepted_but_unacknowledged_ingest
    * process_crash
    * disk_or_network_failure
        affected_task_ids:
    * TASK-014
    * TASK-015
    * TASK-020
    * TASK-021
* id: RISK-007
    statement: Secret values or hydrated memory content could leak into receipts, journals, logs, tests, or CI artifacts.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-009
    mitigations:
    * Separate trusted provenance from semantic content.
    * Apply redaction and strict schemas.
    * Ban token persistence and scan generated artifacts.
        triggers:
    * bearer_token_in_log
    * environment_dump
    * prompt_or_memory_content_in_receipt
    * unredacted_test_fixture
        affected_task_ids:
    * TASK-009
    * TASK-014
    * TASK-015
    * TASK-027
* id: RISK-008
    statement: Shadow mode could accidentally create duplicate claims, ingestion events, or conflicting authority.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-012
    mitigations:
    * Use dry-run or read-only shadow operations where available.
    * Reuse request and idempotency identifiers.
    * Define one authoritative path during shadow operation.
        triggers:
    * duplicate_active_claim
    * duplicate_episode
    * competing_gate_decision
        affected_task_ids:
    * TASK-018
    * TASK-020
* id: RISK-009
    statement: Operation classification may miss alternate command forms or non-shell mutation paths.
    tier: T3
    likelihood: likely
    impact: critical
    owner: AUTH-004
    mitigations:
    * Classify effects rather than literal commands.
    * Test aliases, absolute paths, nested shells, Make targets, GitHub CLI, and native tools.
    * Fail unknown potentially mutating operations according to strict profile policy.
        triggers:
    * bypass_command_allowed
    * direct_GitHub_mutation_unclassified
    * unknown_mutating_operation_defaults_to_allow
        affected_task_ids:
    * TASK-007
    * TASK-012
    * TASK-019
    * TASK-027
* id: RISK-010
    statement: The reference runtime could accidentally encode Claude-specific assumptions and fail reuse by other peers.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-004
    mitigations:
    * Normalize lifecycle events.
    * Keep native hooks thin.
    * Require second-peer adoption without shared-runtime or schema changes.
        triggers:
    * peer_requires_core_runtime_fork
    * Claude_specific_key_in_shared_schema
    * native_event_name_in_canonical_contract
        affected_task_ids:
    * TASK-003
    * TASK-006
    * TASK-016
    * TASK-025
    * TASK-026
* id: RISK-011
    statement: Deleting the legacy pipeline before operational equivalence is proven could remove coordination and recovery safeguards.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-012
    mitigations:
    * Gate deletion on fixture equivalence, canary, rollback rehearsal, and independent verification.
    * Preserve versioned operational rollback until deletion approval.
        triggers:
    * legacy_files_deleted_before_cutover_gate
    * unexplained_shadow_difference
    * rollback_not_rehearsed
        affected_task_ids:
    * TASK-018
    * TASK-020
    * TASK-021
    * TASK-022
    * TASK-023
* id: RISK-012
    statement: Adapter contract and repository documentation may drift after implementation.
    tier: T2
    likelihood: likely
    impact: material
    owner: AUTH-002
    mitigations:
    * Add executable architecture fitness functions.
    * Validate docs and references in CI.
    * Generate adapter scaffolding from canonical schemas.
        triggers:
    * obsolete_legacy_reference
    * adapter_missing_capabilities
    * direct_memory_client_reintroduced
        affected_task_ids:
    * TASK-027
    * TASK-028
    * TASK-029
    * TASK-030
* id: RISK-013
    statement: Unsupported CLI or service behavior may be silently assumed and encoded as fact.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-006
    mitigations:
    * Keep unsupported capabilities explicit as Unknown.
    * Inspect help and capabilities before implementation.
    * Do not invent commands or flags.
        triggers:
    * undocumented_command_used
    * fabricated_exit_code
    * unsupported_protocol_version
        affected_task_ids:
    * TASK-004
    * TASK-005
    * TASK-013
* id: RISK-014
    statement: Memory-service outages could either halt harmless work unnecessarily or silently widen mutation authority.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-004
    mitigations:
    * Define operation-class-specific degraded modes.
    * Continue read-only work where safe.
    * Fail closed for governed mutation.
    * Queue writeback durably.
        triggers:
    * all_operations_blocked_without_policy
    * governed_mutation_allowed_during_outage
    * pending_ingest_discarded
        affected_task_ids:
    * TASK-009
    * TASK-010
    * TASK-014
    * TASK-021
* id: RISK-015
    statement: CI may pass structural file checks while runtime semantics remain broken.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-010
    mitigations:
    * Add real-CLI contract tests.
    * Add multi-agent E2E scenarios.
    * Add fault injection and installation tests.
        triggers:
    * adapter_files_exist_but_runtime_fails
    * mock_only_test_coverage
    * no_negative_identity_test
        affected_task_ids:
    * TASK-013
    * TASK-019
    * TASK-020
    * TASK-021
    * TASK-027
* id: RISK-016
    statement: Protected-root edits may fail append-only controls or weaken canonical law.
    tier: T3
    likelihood: possible
    impact: critical
    owner: AUTH-002
    mitigations:
    * Inspect current root-file rules.
    * Use exact markers and required review.
    * Preserve invariants while updating implementation language.
        triggers:
    * missing_root_deletion_marker
    * unauthorized_CANONICAL_LAW_change
    * stale_gate_reference_retained
        affected_task_ids:
    * TASK-029
    * TASK-030
    * TASK-031
* id: RISK-017
    statement: A second-peer proof may be superficial and fail to establish actual platform reuse.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-013
    mitigations:
    * Require native event mapping and capability-derived conformance.
    * Prohibit shared-runtime or foundational schema changes during second-peer onboarding.
    * Run common E2E scenarios.
        triggers:
    * peer_adapter_is_only_a_static_file_copy
    * shared_runtime_modified_for_second_peer
    * missing_peer_E2E
        affected_task_ids:
    * TASK-025
    * TASK-026
* id: RISK-018
    statement: Remote promotion may be inferred from local success without exact observed GitHub evidence.
    tier: T2
    likelihood: possible
    impact: material
    owner: AUTH-011
    mitigations:
    * Separate local commit, push, pull request, CI, review, and merge evidence.
    * Require exact approval for each remote transition.
        triggers:
    * local_push_command_reported_as_remote_success
    * PR_claim_without_observation
    * merge_claim_without_merge_commit_evidence
        affected_task_ids:
    * TASK-031
    * TASK-032
    * TASK-033

waivers: []

prohibited_paths:

* id: DNB-001
    statement: Do not widen authority downstream of an accepted source contract.
    rationale: Program Execution v2 authority is monotonic and may only narrow.
* id: DNB-002
    statement: Do not treat worker completion as independent verification.
    rationale: Completion and verification are separate authorities and receipts.
* id: DNB-003
    statement: Do not place mutable runtime state in Cursor-Governance or target worktrees.
    rationale: Runtime state belongs under the declared external program root.
* id: DNB-004
    statement: Do not claim remote mutation, publication, release, or deployment without observed evidence.
    rationale: Local intent or command success is not remote event proof.
* id: DNB-005
    statement: Do not create a second memory transport implementation inside any adapter.
    rationale: The shared l9-memory-mcp CLI is the sole adapter transport boundary.
* id: DNB-006
    statement: Do not implement conflict, claim, authorization, or ingestion truth in the adapter runtime.
    rationale: These semantics belong to the shared memory service.
* id: DNB-007
    statement: Do not reduce deterministic mutation controls to optional model instructions.
    rationale: Model compliance is not an enforceable governance boundary.
* id: DNB-008
    statement: Do not allow mutable headers or workspace files to select authenticated identity.
    rationale: Identity must be bound to the server-authenticated principal.
* id: DNB-009
    statement: Do not store bearer tokens, hydrated memory contents, prompts, or arbitrary environment data in receipts or journals.
    rationale: Adapter state must remain minimal and secret-safe.
* id: DNB-010
    statement: Do not use local Boolean lock state as mutation authority.
    rationale: Governed boundaries require current server-verifiable claim evidence.
* id: DNB-011
    statement: Do not allow a claim to authorize repository, branch, scope, operation, or candidate state beyond its binding.
    rationale: Claims must reject stale base, scope expansion, and time-of-check drift.
* id: DNB-012
    statement: Do not treat heartbeat or client wall-clock time as authoritative lease validity.
    rationale: Lease validity must derive from authoritative server semantics.
* id: DNB-013
    statement: Do not silently permit governed mutation when memory or coordination services are unavailable.
    rationale: Outages must enter declared degraded or fail-closed states.
* id: DNB-014
    statement: Do not treat successful local writeback execution as proof of durable server ingestion.
    rationale: Ingestion requires acknowledgement or a retained pending journal entry.
* id: DNB-015
    statement: Do not replay an external side effect with unknown outcome without idempotency or reconciliation.
    rationale: Retry safety requires bounded idempotency and outcome inspection.
* id: DNB-016
    statement: Do not create duplicate active authority during shadow mode.
    rationale: Exactly one path remains authoritative while comparison runs.
* id: DNB-017
    statement: Do not delete legacy memory components before all cutover gates pass.
    rationale: Source rollback alone cannot restore lost memory events or prevented conflicts.
* id: DNB-018
    statement: Do not encode Claude Code native event names as the canonical lifecycle model.
    rationale: Shared contracts must remain peer-neutral.
* id: DNB-019
    statement: Do not claim adapter reuse until a second peer passes conformance without foundational core changes.
    rationale: One implementation does not prove a reusable platform.
* id: DNB-020
    statement: Do not infer capabilities from file presence alone.
    rationale: Declared behavioral guarantees require executable conformance evidence.
* id: DNB-021
    statement: Do not permit unknown potentially mutating operations by default under strict policy profiles.
    rationale: Classification uncertainty must not widen authority.
* id: DNB-022
    statement: Do not modify multiple repositories from one worktree or one repository-scoped task.
    rationale: Mutating authority and rollback must remain repository-isolated.
* id: DNB-023
    statement: Do not change canonical protected-root files without current marker and review requirements.
    rationale: Root governance controls remain authoritative throughout migration.
* id: DNB-024
    statement: Do not invent unsupported CLI commands, flags, exit codes, or protocol behavior.
    rationale: The actual verified CLI contract is authoritative.
* id: DNB-025
    statement: Do not treat the memory service as available solely because configuration exists.
    rationale: Connectivity, protocol, identity, and permissions require current evidence.
* id: DNB-026
    statement: Do not allow the Controller or adapter to declare the terminal program verdict.
    rationale: Terminal verdict authority belongs to the named human program owner.

workstreams:

* id: WS-001
    name: authority_and_current_state
    owner: AUTH-001
    objective: >-
    Preserve the campaign source, establish the program owner, lock governance
    authority, inspect the current repository state, and bind admission
    evidence before implementation.
* id: WS-002
    name: canonical_adapter_contracts
    owner: AUTH-004
    objective: >-
    Define the peer-neutral adapter manifest, capabilities, lifecycle,
    operation, receipt, episode, journal, CLI envelope, compatibility, and
    policy contracts.
* id: WS-003
    name: shared_cli_and_service_contract
    owner: AUTH-006
    objective: >-
    Verify and bind the actual l9-memory-mcp CLI and shared memory service
    interfaces, identity semantics, protocol compatibility, and automation
    behavior.
* id: WS-004
    name: shared_adapter_runtime
    owner: AUTH-004
    objective: >-
    Implement the reusable lifecycle runner, event normalization, context
    collection, operation classification, policy evaluation, CLI gateway,
    state handling, diagnostics, and explicit failure behavior.
* id: WS-005
    name: identity_claims_and_enforcement
    owner: AUTH-007
    objective: >-
    Enforce authenticated principal binding, exact claim scope, conflict
    detection, lease semantics, fresh verification, and mutation-boundary
    decisions without local authority duplication.
* id: WS-006
    name: durable_ingestion_and_recovery
    owner: AUTH-004
    objective: >-
    Deliver secret-safe, idempotent, durable session ingestion with external
    state storage, crash recovery, acknowledgement handling, and replay.
* id: WS-007
    name: conformance_and_test_platform
    owner: AUTH-010
    objective: >-
    Build capability-derived conformance, real-CLI contract testing,
    architecture fitness functions, E2E infrastructure, fault injection, and
    reusable multi-agent scenarios.
* id: WS-008
    name: claude_code_reference_adapter
    owner: AUTH-005
    objective: >-
    Implement Claude Code’s peer-compliant adapter, native lifecycle mapping,
    installer wiring, capabilities declaration, and reference certification.
* id: WS-009
    name: migration_shadow_and_cutover
    owner: AUTH-012
    objective: >-
    Capture legacy fixtures, run shadow equivalence, perform canary
    enforcement, rehearse rollback, cut over safely, and remove superseded
    Claude-specific memory components.
* id: WS-010
    name: peer_reuse_certification
    owner: AUTH-013
    objective: >-
    Select and integrate a second peer using unchanged foundational schemas
    and runtime, then prove reusable conformance and lifecycle portability.
* id: WS-011
    name: governance_documentation_and_CI
    owner: AUTH-002
    objective: >-
    Update registry, validators, architecture decisions, topology, setup,
    governance documentation, protected-root references, CI, and architecture
    fitness enforcement.
* id: WS-012
    name: remote_promotion_and_review
    owner: AUTH-011
    objective: >-
    Prepare evidence-backed commits and exact approval packets for push,
    pull-request creation, CI observation, review, merge, and any later release
    or deployment transition.
* id: WS-013
    name: closeout
    owner: AUTH-001
    objective: >-
    Reconcile final evidence, export the Controller handoff, record residual
    decisions and risks, and request the human terminal verdict.

dependency_edges:

* from: TASK-001
    to: TASK-002
* from: TASK-002
    to: TASK-003
* from: TASK-002
    to: TASK-004
* from: TASK-004
    to: TASK-005
* from: TASK-003
    to: TASK-006
* from: TASK-003
    to: TASK-007
* from: TASK-004
    to: TASK-008
* from: TASK-006
    to: TASK-008
* from: TASK-007
    to: TASK-008
* from: TASK-005
    to: TASK-009
* from: TASK-008
    to: TASK-009
* from: TASK-005
    to: TASK-010
* from: TASK-007
    to: TASK-010
* from: TASK-008
    to: TASK-010
* from: TASK-010
    to: TASK-011
* from: TASK-007
    to: TASK-012
* from: TASK-004
    to: TASK-013
* from: TASK-005
    to: TASK-013
* from: TASK-003
    to: TASK-014
* from: TASK-009
    to: TASK-014
* from: TASK-014
    to: TASK-015
* from: TASK-003
    to: TASK-016
* from: TASK-006
    to: TASK-016
* from: TASK-008
    to: TASK-016
* from: TASK-009
    to: TASK-017
* from: TASK-010
    to: TASK-017
* from: TASK-014
    to: TASK-017
* from: TASK-016
    to: TASK-017
* from: TASK-017
    to: TASK-018
* from: TASK-018
    to: TASK-019
* from: TASK-011
    to: TASK-019
* from: TASK-012
    to: TASK-019
* from: TASK-013
    to: TASK-019
* from: TASK-015
    to: TASK-020
* from: TASK-018
    to: TASK-020
* from: TASK-019
    to: TASK-020
* from: TASK-020
    to: TASK-021
* from: TASK-021
    to: TASK-022
* from: TASK-022
    to: TASK-023
* from: TASK-003
    to: TASK-024
* from: TASK-024
    to: TASK-025
* from: TASK-016
    to: TASK-025
* from: TASK-019
    to: TASK-025
* from: TASK-025
    to: TASK-026
* from: TASK-013
    to: TASK-027
* from: TASK-019
    to: TASK-027
* from: TASK-020
    to: TASK-027
* from: TASK-023
    to: TASK-028
* from: TASK-026
    to: TASK-028
* from: TASK-028
    to: TASK-029
* from: TASK-029
    to: TASK-030
* from: TASK-027
    to: TASK-031
* from: TASK-030
    to: TASK-031
* from: TASK-031
    to: TASK-032
* from: TASK-032
    to: TASK-033
* from: TASK-023
    to: TASK-034
* from: TASK-026
    to: TASK-034
* from: TASK-033
    to: TASK-034

waves:

* id: W0
    name: authority_and_current_state_lock
    task_ids:
    * TASK-001
    * TASK-002
        predecessor_wave_ids: []
        exit_gate_ids:
    * GATE-001
    * GATE-002
* id: W1
    name: canonical_contracts_and_external_interface_lock
    task_ids:
    * TASK-003
    * TASK-004
    * TASK-005
        predecessor_wave_ids:
    * W0
        exit_gate_ids:
    * GATE-003
    * GATE-004
* id: W2
    name: shared_runtime_and_policy_foundation
    task_ids:
    * TASK-006
    * TASK-007
    * TASK-008
    * TASK-009
        predecessor_wave_ids:
    * W1
        exit_gate_ids:
    * GATE-005
    * GATE-006
* id: W3
    name: identity_claims_enforcement_and_ingestion
    task_ids:
    * TASK-010
    * TASK-011
    * TASK-012
    * TASK-013
    * TASK-014
    * TASK-015
        predecessor_wave_ids:
    * W2
        exit_gate_ids:
    * GATE-007
    * GATE-008
    * GATE-009
* id: W4
    name: reference_adapter_materialization
    task_ids:
    * TASK-016
    * TASK-017
    * TASK-018
        predecessor_wave_ids:
    * W3
        exit_gate_ids:
    * GATE-010
    * GATE-011
* id: W5
    name: end_to_end_shadow_and_canary
    task_ids:
    * TASK-019
    * TASK-020
    * TASK-021
    * TASK-022
        predecessor_wave_ids:
    * W4
        exit_gate_ids:
    * GATE-012
    * GATE-013
    * GATE-014
    * GATE-015
* id: W6
    name: legacy_removal_and_reference_certification
    task_ids:
    * TASK-023
    * TASK-024
        predecessor_wave_ids:
    * W5
        exit_gate_ids:
    * GATE-016
    * GATE-017
* id: W7
    name: second_peer_reuse_certification
    task_ids:
    * TASK-025
    * TASK-026
        predecessor_wave_ids:
    * W6
        exit_gate_ids:
    * GATE-018
* id: W8
    name: governance_CI_and_documentation_convergence
    task_ids:
    * TASK-027
    * TASK-028
    * TASK-029
    * TASK-030
        predecessor_wave_ids:
    * W7
        exit_gate_ids:
    * GATE-019
    * GATE-020
    * GATE-021
* id: W9
    name: exact_remote_promotion
    task_ids:
    * TASK-031
    * TASK-032
    * TASK-033
        predecessor_wave_ids:
    * W8
        exit_gate_ids:
    * GATE-022
    * GATE-023
    * GATE-024
* id: W10
    name: evidence_backed_closeout
    task_ids:
    * TASK-034
        predecessor_wave_ids:
    * W9
        exit_gate_ids:
    * GATE-025

tasks:

* id: TASK-001
    title: Admit campaign and lock canonical authority
    definition_status: blocked
    workstream_id: WS-001
    wave_id: W0
    target_id: TARGET-002
    execution_kind: program_control
    objective: >-
    Preserve the immutable source, resolve the human program owner, verify the
    Program Execution v2 host, and establish the admission authority baseline.
    authority_basis_ids:
    * AUTH-001
    * AUTH-002
    * AUTH-003
        required_decision_ids: []
        blocking_unknown_ids:
    * UNK-001
    * UNK-003
        input_evidence_ids:
    * EVID-001
        actions:
    * preserve_campaign_source_byte_for_byte
    * compute_external_source_digest
    * resolve_program_owner
    * inspect_current_program_execution_interfaces
    * instantiate_draft_blueprint_and_controller
    * validate_template_mode_without_mutating_targets
        outputs:
    * id: OUT-001
        type: receipt
        location: controller/admission/source-integrity-receipt.json
        required: true
    * id: OUT-002
        type: evidence
        location: CURRENT_STATE_DELTA.yaml
        required: true
        acceptance:
    * id: AC-001
        statement: >-
        The immutable campaign source is preserved externally and bound to an
        independently computed SHA-256 receipt.
        required_evidence_types:
        * digest
        * inspection
    * id: AC-002
        statement: >-
        The human program owner and terminal-verdict authority are explicit.
        required_evidence_types:
        * authority_record
    * id: AC-003
        statement: >-
        Current Program Execution v2 interfaces are inspected and the draft
        Blueprint passes supported template-mode validation.
        required_evidence_types:
        * test_result
        * command_output
            validation:
    * id: VAL-001
        method: command
        command_or_inspection: >-
        Inspect current Program Execution v2 validator –help output and run
        the supported template-mode Blueprint validation command.
        environment: program_execution_control_plane
        expected_result: PASS
        negative_cases:
    * unresolved_program_owner
    * source_digest_mismatch
    * missing_required_host_surface
    * unsupported_validator_invocation
    * existing_runtime_identity_conflict
        rollback:
        strategy: discard_unaccepted_generated_runtime_and_preserve_immutable_source
        trigger: admission_or_template_validation_failure
        validation: No accepted Blueprint, Program Lock, or target repository mutation exists.
        risk:
        tier: T0
        reversibility: fully_reversible
        blast_radius: program_definition
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-001
* id: TASK-002
    title: Inventory current repository and legacy memory implementation
    definition_status: ready
    workstream_id: WS-001
    wave_id: W0
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Bind the exact Cursor-Governance baseline and produce a complete inventory
    of the current adapter architecture, Claude Code memory pipeline, CI,
    documentation, ADR, installer, and protected-root references.
    authority_basis_ids:
    * AUTH-002
    * AUTH-005
        required_decision_ids: []
        blocking_unknown_ids:
    * UNK-002
    * UNK-008
        input_evidence_ids:
    * EVID-002
    * EVID-003
    * EVID-004
    * EVID-005
        actions:
    * inspect_git_identity_branch_head_remotes_and_dirty_state
    * inspect_environment_agents_registry_contracts_and_peer_adapters
    * inventory_environment_claude_code_memory_hooks_clients_state_tests_and_schemas
    * search_Makefile_CI_rules_commands_docs_ADRs_and_root_files_for_legacy_references
    * classify_current_behavior_as_transport_domain_policy_lifecycle_or_delivery
        outputs:
    * id: OUT-003
        type: evidence
        location: blueprint/evidence/legacy-memory-pipeline-inventory.yaml
        required: true
    * id: OUT-004
        type: evidence
        location: blueprint/evidence/repository-baseline.yaml
        required: true
        acceptance:
    * id: AC-004
        statement: >-
        Repository identity, exact baseline revision, branch, remotes, and
        unexplained working-tree state are recorded.
        required_evidence_types:
        * inspection
        * revision
    * id: AC-005
        statement: >-
        Every direct and indirect dependency on the legacy Claude Code memory
        pipeline is mapped to a durable inventory record.
        required_evidence_types:
        * inspection
        * reference_map
            validation:
    * id: VAL-002
        method: inspection
        command_or_inspection: >-
        Compare repository-wide searches for legacy hook, client, state,
        schema, validator, and ADR identifiers against the generated inventory.
        environment: local
        expected_result: No unexplained reference remains.
        negative_cases:
    * unexplained_dirty_tree
    * missing_indirect_reference
    * current_behavior_inferred_without_inspection
    * repository_alias_mismatch
        rollback:
        strategy: remove_generated_inventory_only
        trigger: incomplete_or_inaccurate_inventory
        validation: Repository source files remain unchanged.
        risk:
        tier: T0
        reversibility: fully_reversible
        blast_radius: evidence_only
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-002
* id: TASK-003
    title: Define canonical adapter schemas and compatibility contracts
    definition_status: blocked
    workstream_id: WS-002
    wave_id: W1
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Materialize peer-neutral schemas for adapter identity, capabilities,
    lifecycle events, operation classification, receipts, episodes, journals,
    CLI envelopes, and version compatibility.
    authority_basis_ids:
    * AUTH-004
    * AUTH-008
        required_decision_ids:
    * DEC-006
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-003
    * EVID-010
        actions:
    * define_adapter_manifest_schema
    * define_adapter_capabilities_schema
    * define_lifecycle_event_and_result_schemas
    * define_operation_classification_schema
    * define_session_receipt_and_delivery_journal_schemas
    * define_memory_episode_and_CLI_response_envelope_schemas
    * define_contract_runtime_CLI_protocol_compatibility_fields
        outputs:
    * id: OUT-005
        type: artifact
        location: environment/agents/contracts/adapter-manifest.schema.json
        required: true
    * id: OUT-006
        type: artifact
        location: environment/agents/contracts/adapter-capabilities.schema.json
        required: true
    * id: OUT-007
        type: artifact
        location: environment/agents/contracts/memory-lifecycle.schema.json
        required: true
    * id: OUT-008
        type: artifact
        location: environment/agents/contracts/memory-episode.schema.json
        required: true
        acceptance:
    * id: AC-006
        statement: >-
        Canonical schemas contain no Claude-specific native event names or
        implementation assumptions.
        required_evidence_types:
        * schema_validation
        * architecture_review
    * id: AC-007
        statement: >-
        All declared adapter guarantees and compatibility constraints are
        machine-validated.
        required_evidence_types:
        * test_result
            validation:
    * id: VAL-003
        method: command
        command_or_inspection: >-
        Run repository-owned JSON Schema validation and negative fixtures for
        all new adapter contract schemas.
        environment: local
        expected_result: PASS
        negative_cases:
    * Claude_specific_field_in_shared_contract
    * missing_schema_version
    * unknown_capability_silently_accepted
    * incompatible_version_range_accepted
        rollback:
        strategy: revert_unaccepted_contract_files_and_generated_fixtures
        trigger: schema_review_or_validation_failure
        validation: Existing adapters remain valid under the prior accepted contract.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: adapter_contracts
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-003
* id: TASK-004
    title: Verify and codify the shared CLI automation contract
    definition_status: blocked
    workstream_id: WS-003
    wave_id: W1
    target_id: TARGET-006
    execution_kind: external_tool_validation
    objective: >-
    Determine the exact supported l9-memory-mcp command surface, machine
    output, exit codes, timeouts, protocol versions, and release provenance.
    authority_basis_ids:
    * AUTH-006
        required_decision_ids:
    * DEC-002
        blocking_unknown_ids:
    * UNK-004
    * UNK-005
        input_evidence_ids:
    * EVID-006
    * EVID-007
        actions:
    * inspect_version_capabilities_doctor_and_command_help
    * verify_hydrate_conflicts_claim_and_ingest_commands
    * record_supported_output_and_non_interactive_modes
    * record_exit_code_and_error_taxonomy
    * verify_distribution_provenance_and_version_policy
    * define_unsupported_capabilities_as_explicit_UNKNOWNs
        outputs:
    * id: OUT-009
        type: contract
        location: environment/agents/docs/CLI_CONTRACT.md
        required: true
    * id: OUT-010
        type: evidence
        location: blueprint/evidence/l9-memory-mcp-capability-probe.json
        required: true
        acceptance:
    * id: AC-008
        statement: >-
        Every CLI command and flag used by the campaign is supported by
        observed CLI evidence.
        required_evidence_types:
        * command_output
        * inspection
    * id: AC-009
        statement: >-
        The compatible CLI version range and failure taxonomy are explicit.
        required_evidence_types:
        * contract
            validation:
    * id: VAL-004
        method: command
        command_or_inspection: >-
        Execute non-mutating version, capability, doctor, and help probes using
        the installed or pinned CLI.
        environment: local_and_CI
        expected_result: Supported contract recorded without invented behavior.
        negative_cases:
    * unsupported_command_assumed
    * undocumented_flag_used
    * unverified_binary_provenance
    * human_text_parsing_required_for_automation
        rollback:
        strategy: remove_unaccepted_CLI_contract_and_probe_receipts
        trigger: unsupported_or_incompatible_CLI
        validation: No adapter runtime depends on the rejected contract.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: shared_CLI_contract
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-004
* id: TASK-005
    title: Verify memory service identity and protocol behavior
    definition_status: blocked
    workstream_id: WS-003
    wave_id: W1
    target_id: TARGET-007
    execution_kind: external_service_validation
    objective: >-
    Prove MCP protocol compatibility, authenticated principal binding,
    claim/conflict semantics, and ingestion behavior using controlled,
    non-production-safe probes.
    authority_basis_ids:
    * AUTH-007
    * AUTH-009
        required_decision_ids:
    * DEC-002
        blocking_unknown_ids:
    * UNK-006
    * UNK-007
    * UNK-017
    * UNK-018
        input_evidence_ids:
    * EVID-008
    * EVID-009
        actions:
    * resolve_approved_endpoint_and_identity_configuration
    * execute_authenticated_non_mutating_protocol_probe
    * verify_server_confirmed_principal
    * test_token_header_and_manifest_identity_mismatch_rejection
    * inspect_claim_conflict_and_ingestion_capabilities
    * record_service_failure_and_rate_limit_semantics
        outputs:
    * id: OUT-011
        type: evidence
        location: blueprint/evidence/memory-service-contract-probe.json
        required: true
    * id: OUT-012
        type: security_evidence
        location: blueprint/evidence/identity-binding-negative-tests.json
        required: true
        acceptance:
    * id: AC-010
        statement: >-
        The authenticated token principal, declared adapter identity, and
        server-confirmed identity must match.
        required_evidence_types:
        * security_test
    * id: AC-011
        statement: >-
        Protocol and service capabilities required by the adapter foundation
        are verified or explicitly blocked.
        required_evidence_types:
        * capability_probe
            validation:
    * id: VAL-005
        method: test
        command_or_inspection: >-
        Execute controlled valid-identity and forged-identity probes through
        l9-memory-mcp against the approved test or staging service.
        environment: controlled_test_service
        expected_result: Valid identity succeeds and every mismatch is rejected.
        negative_cases:
    * forged_header_accepted
    * token_identity_not_bound
    * unsupported_protocol_accepted
    * secret_value_logged
    * production_mutation_during_probe
        rollback:
        strategy: revoke_test_claims_and_remove_ephemeral_probe_data
        trigger: probe_failure_or_identity_security_failure
        validation: No durable production mutation or active test claim remains.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: external_service_test_scope
        authorization_ceiling:
        inspect: true
        local_write: false
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-004
* id: TASK-006
    title: Implement peer-neutral lifecycle model and shared runner
    definition_status: blocked
    workstream_id: WS-004
    wave_id: W2
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Implement the canonical lifecycle state machine and a reusable runner that
    accepts normalized events without embedding Claude Code assumptions.
    authority_basis_ids:
    * AUTH-004
        required_decision_ids:
    * DEC-001
    * DEC-006
    * DEC-007
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-010
    * EVID-017
        actions:
    * implement_normalized_lifecycle_events
    * implement_session_state_machine
    * implement_adapter_manifest_and_capabilities_loading
    * implement_schema_validated_event_dispatch
    * implement_explicit_failure_state_transitions
    * expose_thin_native_entrypoint_interface
        outputs:
    * id: OUT-013
        type: artifact
        location: environment/agents/runtime/lifecycle_runner.py
        required: true
    * id: OUT-014
        type: artifact
        location: environment/agents/runtime/state_machine.py
        required: true
        acceptance:
    * id: AC-012
        statement: >-
        Shared runtime transitions are deterministic, schema-valid, and
        independent of a specific native agent surface.
        required_evidence_types:
        * unit_test
        * state_transition_test
    * id: AC-013
        statement: Invalid lifecycle transitions fail without widening authority.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-006
        method: command
        command_or_inspection: >-
        Run lifecycle schema, state transition, and invalid-transition tests.
        environment: local
        expected_result: PASS
        negative_cases:
    * uninitialized_session_enters_claimed_state
    * expired_claim_allows_governed_boundary
    * native_event_name_leaks_into_shared_contract
    * unknown_state_defaults_to_active
        rollback:
        strategy: revert_shared_runtime_files_and_keep_existing_adapter_paths_active
        trigger: lifecycle_contract_or_test_failure
        validation: Existing adapters and legacy Claude pipeline remain operational.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: shared_adapter_runtime
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-005
* id: TASK-007
    title: Implement effect-based operation classification and policy profiles
    definition_status: blocked
    workstream_id: WS-004
    wave_id: W2
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Classify native actions by effect and bind shared role profiles to exact
    governance controls and failure behavior.
    authority_basis_ids:
    * AUTH-004
    * AUTH-008
        required_decision_ids:
    * DEC-001
    * DEC-006
    * DEC-007
        blocking_unknown_ids:
    * UNK-010
        input_evidence_ids:
    * EVID-001
    * EVID-005
    * EVID-012
        actions:
    * define_canonical_operation_categories
    * define_observer_reviewer_implementer_maintainer_orchestrator_and_administrator_profiles
    * classify_shell_native_tool_Git_and_GitHub_operations
    * classify_protected_path_mutations
    * define_unknown_potentially_mutating_policy
    * create_adversarial_command_corpus
        outputs:
    * id: OUT-015
        type: artifact
        location: environment/agents/runtime/operation_classifier.py
        required: true
    * id: OUT-016
        type: artifact
        location: environment/agents/policy/profiles.yaml
        required: true
    * id: OUT-017
        type: artifact
        location: environment/agents/policy/operations.yaml
        required: true
        acceptance:
    * id: AC-014
        statement: >-
        Equivalent mutating effects receive equivalent classifications across
        literal commands, wrappers, aliases, and native tools.
        required_evidence_types:
        * unit_test
        * property_test
    * id: AC-015
        statement: >-
        Unknown potentially mutating operations do not default to allow under
        strict profiles.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-007
        method: command
        command_or_inspection: >-
        Run operation-classification fixtures including nested shells,
        absolute binaries, Make targets, GitHub CLI, aliases, and direct tool
        events.
        environment: local
        expected_result: PASS
        negative_cases:
    * absolute_git_path_bypass
    * nested_shell_bypass
    * Make_target_bypass
    * GitHub_CLI_bypass
    * unknown_mutation_defaults_to_allow
        rollback:
        strategy: revert_classifier_and_profiles_without_changing_active_legacy_gate
        trigger: classification_gap_or_false_allow
        validation: Existing deterministic gate remains authoritative.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: mutation_policy
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-005
* id: TASK-008
    title: Implement shared CLI gateway and response validation
    definition_status: blocked
    workstream_id: WS-004
    wave_id: W2
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Provide one secure runtime gateway for invoking l9-memory-mcp with
    validated arguments, bounded execution, structured results, and no direct
    MCP or HTTP implementation.
    authority_basis_ids:
    * AUTH-004
    * AUTH-006
        required_decision_ids:
    * DEC-001
    * DEC-002
    * DEC-006
        blocking_unknown_ids:
    * UNK-005
        input_evidence_ids:
    * EVID-007
    * EVID-011
        actions:
    * implement_fixed_executable_resolution
    * implement_argument_array_invocation_without_shell_interpolation
    * implement_sanitized_environment_and_secret_safe_logging
    * implement_timeout_process_group_termination_and_bounded_output
    * validate_CLI_response_envelope_and_schema_version
    * map_verified_exit_codes_to_typed_runtime_failures
    * prohibit_direct_network_memory_transport_from_runtime
        outputs:
    * id: OUT-018
        type: artifact
        location: environment/agents/runtime/cli_gateway.py
        required: true
        acceptance:
    * id: AC-016
        statement: >-
        All shared runtime memory calls pass exclusively through
        l9-memory-mcp.
        required_evidence_types:
        * architecture_test
        * unit_test
    * id: AC-017
        statement: >-
        Invalid, malformed, oversized, or incompatible CLI responses are
        rejected before policy decisions.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-008
        method: command
        command_or_inspection: >-
        Run CLI gateway tests with successful, timed-out, malformed,
        truncated, oversized, unsupported-schema, and secret-bearing output.
        environment: local
        expected_result: PASS
        negative_cases:
    * shell_injection
    * token_in_process_arguments
    * zero_exit_with_invalid_JSON
    * unsupported_schema_version
    * direct_HTTP_dependency
        rollback:
        strategy: revert_CLI_gateway_and_retain_legacy_transport_as_authoritative
        trigger: gateway_security_or_contract_failure
        validation: No adapter has switched to the rejected gateway.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: shared_runtime_transport
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-006
* id: TASK-009
    title: Implement secure external session state storage
    definition_status: blocked
    workstream_id: WS-004
    wave_id: W2
    target_id: TARGET-012
    execution_kind: local_runtime
    objective: >-
    Store minimal session receipts and pending delivery state outside
    repositories using secure, atomic, cross-platform mechanics.
    authority_basis_ids:
    * AUTH-004
    * AUTH-009
        required_decision_ids:
    * DEC-004
    * DEC-005
        blocking_unknown_ids:
    * UNK-011
        input_evidence_ids:
    * EVID-014
        actions:
    * define_external_state_root_resolution
    * implement_atomic_session_receipt_writes
    * enforce_owner_permission_and_symlink_checks
    * exclude_tokens_hydrated_content_and_prompts
    * implement_bounded_retention_and_cleanup
    * validate_cross_platform_path_behavior
        outputs:
    * id: OUT-019
        type: artifact
        location: environment/agents/runtime/receipt_store.py
        required: true
    * id: OUT-020
        type: contract
        location: environment/agents/docs/STATE_STORAGE_CONTRACT.md
        required: true
        acceptance:
    * id: AC-018
        statement: >-
        Local state is external to source and worktrees, minimally scoped, and
        cannot independently authorize mutation.
        required_evidence_types:
        * security_test
        * inspection
    * id: AC-019
        statement: >-
        Permission, owner, symlink, partial-write, and corruption failures are
        detected and handled safely.
        required_evidence_types:
        * fault_injection
            validation:
    * id: VAL-009
        method: command
        command_or_inspection: >-
        Run state-store tests for permissions, ownership, symlinks, atomicity,
        corruption, path traversal, retention, and worktree exclusion.
        environment: local_and_CI
        expected_result: PASS
        negative_cases:
    * state_inside_repository
    * symlink_followed
    * world_readable_receipt
    * hydrated_content_persisted
    * corrupted_receipt_grants_authority
        rollback:
        strategy: remove_unaccepted_external_state_and_restore_prior_runtime_state_path
        trigger: storage_security_or_compatibility_failure
        validation: No pending ingest or active claim evidence is lost.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: local_adapter_state
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-006
* id: TASK-010
    title: Implement claim acquisition and governed-boundary verification
    definition_status: blocked
    workstream_id: WS-005
    wave_id: W3
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Enforce conflicts checks, claim acquisition, and fresh verification bound
    to identity, repository, branch, revision, scope, operation, and lease.
    authority_basis_ids:
    * AUTH-004
    * AUTH-007
    * AUTH-009
        required_decision_ids:
    * DEC-001
    * DEC-003
    * DEC-004
        blocking_unknown_ids:
    * UNK-005
    * UNK-007
    * UNK-010
    * UNK-018
        input_evidence_ids:
    * EVID-009
    * EVID-013
    * EVID-014
        actions:
    * implement_conflicts_check_flow
    * implement_claim_acquire_flow
    * bind_claim_request_to_exact_repository_context
    * implement_fresh_claim_verify_before_governed_boundaries
    * detect_branch_base_and_scope_drift
    * reject_identity_ownership_or_expiry_mismatch
    * implement_explicit_degraded_and_fail_closed_results
        outputs:
    * id: OUT-021
        type: artifact
        location: environment/agents/runtime/claim_controller.py
        required: true
        acceptance:
    * id: AC-020
        statement: >-
        No governed boundary is allowed without current server-verifiable
        authority covering the exact candidate state.
        required_evidence_types:
        * integration_test
        * negative_test
    * id: AC-021
        statement: >-
        Expired, revoked, wrong-principal, wrong-branch, stale-base, and
        scope-mismatched claims are rejected.
        required_evidence_types:
        * integration_test
            validation:
    * id: VAL-010
        method: command
        command_or_inspection: >-
        Run controlled claim acquire and verify tests for valid, expired,
        revoked, forged, stale, and expanded-scope candidates.
        environment: controlled_test_service
        expected_result: PASS
        negative_cases:
    * no_claim_allows_commit
    * expired_claim_allows_push
    * forged_principal_accepted
    * new_protected_path_not_in_claim
    * stale_base_revision_accepted
        rollback:
        strategy: disable_new_claim_controller_and_restore_legacy_gate_authority
        trigger: false_allow_or_identity_binding_failure
        validation: All governed operations remain fail-closed under the legacy path.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: governed_mutation_authority
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-007
* id: TASK-011
    title: Implement mutation-boundary policy enforcement
    definition_status: blocked
    workstream_id: WS-005
    wave_id: W3
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Evaluate normalized operation classifications and enforce profile-specific
    requirements at protected edits, commits, pushes, merges, pull requests,
    promotions, and destructive memory operations.
    authority_basis_ids:
    * AUTH-004
    * AUTH-007
        required_decision_ids:
    * DEC-001
    * DEC-003
    * DEC-004
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-012
    * EVID-013
    * EVID-019
        actions:
    * implement_policy_engine
    * map_operation_categories_to_required_controls
    * distinguish_read_only_local_mutation_and_irreversible_boundaries
    * enforce_profile_specific_failure_behavior
    * emit_structured_allow_deny_and_degraded_results
    * require_current_claim_verification_for_irreversible_actions
        outputs:
    * id: OUT-022
        type: artifact
        location: environment/agents/runtime/policy_engine.py
        required: true
        acceptance:
    * id: AC-022
        statement: >-
        Each governed operation has explicit required controls and failure
        behavior.
        required_evidence_types:
        * policy_test
    * id: AC-023
        statement: >-
        Memory or coordination failure does not silently grant mutation
        authority.
        required_evidence_types:
        * fault_injection
            validation:
    * id: VAL-011
        method: command
        command_or_inspection: >-
        Run policy matrix tests across all profiles, operation classes, claim
        states, service states, and break-glass states.
        environment: local
        expected_result: PASS
        negative_cases:
    * strict_profile_unknown_operation_allowed
    * service_outage_allows_push
    * observer_profile_mutates_protected_path
    * expired_claim_allows_merge
        rollback:
        strategy: disable_shared_policy_engine_and_retain_legacy_gate
        trigger: incorrect_allow_or_denial_matrix
        validation: Existing governed boundaries remain protected.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: policy_enforcement
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-007
* id: TASK-012
    title: Implement adversarial mutation-boundary bypass tests
    definition_status: blocked
    workstream_id: WS-005
    wave_id: W3
    target_id: TARGET-009
    execution_kind: test_harness
    objective: >-
    Prove that governed effects cannot bypass classification and enforcement
    through alternate command forms, wrappers, tools, or indirect execution.
    authority_basis_ids:
    * AUTH-010
        required_decision_ids: []
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-012
        actions:
    * test_absolute_binary_paths
    * test_nested_shells_aliases_and_environment_wrappers
    * test_Make_and_script_indirection
    * test_GitHub_CLI_and_native_repository_tools
    * test_direct_edit_and_write_tools
    * test_unknown_potentially_mutating_operations
        outputs:
    * id: OUT-023
        type: test_suite
        location: environment/agents/conformance/security/test_mutation_bypass.py
        required: true
        acceptance:
    * id: AC-024
        statement: >-
        Every tested governed effect is denied without required authority
        regardless of invocation form.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-012
        method: command
        command_or_inspection: >-
        Run the complete mutation-bypass corpus against the shared classifier
        and policy engine.
        environment: local_and_CI
        expected_result: PASS
        negative_cases:
    * absolute_git_bypass
    * bash_lc_bypass
    * Make_publish_bypass
    * gh_pr_merge_bypass
    * native_tool_mutation_bypass
        rollback:
        strategy: revert_test_only_changes
        trigger: invalid_or_non_portable_test_harness
        validation: Production runtime remains unchanged.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: test_harness
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-008
* id: TASK-013
    title: Build real-CLI contract test service and suite
    definition_status: blocked
    workstream_id: WS-007
    wave_id: W3
    target_id: TARGET-008
    execution_kind: test_harness
    objective: >-
    Execute the real l9-memory-mcp binary against a controlled MCP service and
    verify command contracts, failure taxonomy, compatibility, and secret
    safety.
    authority_basis_ids:
    * AUTH-006
    * AUTH-010
        required_decision_ids:
    * DEC-002
        blocking_unknown_ids:
    * UNK-004
    * UNK-005
        input_evidence_ids:
    * EVID-006
    * EVID-007
    * EVID-016
        actions:
    * implement_controlled_MCP_service
    * execute_real_CLI_hydrate_conflicts_claim_and_ingest_flows
    * inject_malformed_truncated_delayed_and_incompatible_responses
    * verify_exit_codes_and_error_envelopes
    * verify_token_and_secret_non_disclosure
    * test_minimum_and_current_supported_CLI_versions
        outputs:
    * id: OUT-024
        type: test_suite
        location: environment/agents/conformance/cli_contract
        required: true
    * id: OUT-025
        type: test_service
        location: environment/agents/conformance/fixtures/mcp_test_service
        required: true
        acceptance:
    * id: AC-025
        statement: >-
        The actual shared CLI satisfies the accepted automation contract in
        clean local and CI environments.
        required_evidence_types:
        * contract_test
    * id: AC-026
        statement: >-
        Malformed or incompatible service behavior produces deterministic,
        typed failures without secret leakage.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-013
        method: command
        command_or_inspection: >-
        Run the real-CLI contract suite against the controlled MCP test
        service for all supported version bounds.
        environment: local_and_CI
        expected_result: PASS
        negative_cases:
    * mock_only_validation
    * malformed_success_response_accepted
    * secret_in_subprocess_output
    * unsupported_CLI_major_version_accepted
        rollback:
        strategy: remove_unaccepted_test_service_and_contract_suite
        trigger: non_reproducible_or_unsafe_test_design
        validation: No external service or production configuration is modified.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: test_infrastructure
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-008
* id: TASK-014
    title: Implement durable idempotent session ingestion
    definition_status: blocked
    workstream_id: WS-006
    wave_id: W3
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Persist session episode envelopes before transmission, ingest through the
    shared CLI with idempotency, and retain unacknowledged work for replay.
    authority_basis_ids:
    * AUTH-004
    * AUTH-007
    * AUTH-009
        required_decision_ids:
    * DEC-004
    * DEC-005
        blocking_unknown_ids:
    * UNK-011
    * UNK-012
        input_evidence_ids:
    * EVID-015
        actions:
    * define_episode_envelope_and_idempotency_key
    * separate_harness_provenance_from_model_summary
    * implement_append_before_send_delivery_journal
    * implement_acknowledgement_tracking
    * implement_secret_redaction_and_payload_limits
    * implement_retry_and_dead_letter_handling
        outputs:
    * id: OUT-026
        type: artifact
        location: environment/agents/runtime/delivery_journal.py
        required: true
    * id: OUT-027
        type: artifact
        location: environment/agents/runtime/redaction.py
        required: true
        acceptance:
    * id: AC-027
        statement: >-
        Every ingest attempt is idempotent and either acknowledged or retained
        durably for retry.
        required_evidence_types:
        * integration_test
        * fault_injection
    * id: AC-028
        statement: >-
        Tokens, secrets, hydrated memory, and unsupported payload fields are
        absent from durable adapter state.
        required_evidence_types:
        * security_test
            validation:
    * id: VAL-014
        method: command
        command_or_inspection: >-
        Run ingest tests for duplicate delivery, timeout, accepted-but-
        unacknowledged response, malformed payload, redaction, size limit, and
        retry.
        environment: controlled_test_service
        expected_result: PASS
        negative_cases:
    * episode_lost_after_timeout
    * duplicate_episode_created
    * bearer_token_persisted
    * model_controls_provenance_fields
    * oversized_payload_accepted
        rollback:
        strategy: disable_new_journal_writer_and_preserve_all_pending_entries
        trigger: data_loss_duplicate_or_secret_leak
        validation: Pending entries remain recoverable and legacy writeback remains available.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: session_memory_delivery
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-009
* id: TASK-015
    title: Implement ingestion replay and crash recovery
    definition_status: blocked
    workstream_id: WS-006
    wave_id: W3
    target_id: TARGET-012
    execution_kind: local_runtime
    objective: >-
    Recover pending session episodes after process interruption and replay them
    safely before new hydration.
    authority_basis_ids:
    * AUTH-004
        required_decision_ids:
    * DEC-005
        blocking_unknown_ids:
    * UNK-011
    * UNK-012
        input_evidence_ids:
    * EVID-015
        actions:
    * scan_pending_journal_on_session_start
    * reconcile_acknowledgement_unknown_outcomes
    * replay_with_original_idempotency_key
    * preserve_failed_entries_with_reason
    * bound_retry_and_retention
    * verify_previous_episode_available_to_subsequent_hydration
        outputs:
    * id: OUT-028
        type: artifact
        location: environment/agents/runtime/recovery.py
        required: true
        acceptance:
    * id: AC-029
        statement: >-
        Process death after server acceptance but before local acknowledgement
        does not create duplicate episodes.
        required_evidence_types:
        * crash_recovery_test
    * id: AC-030
        statement: >-
        Pending prior-session evidence is reconciled before current-session
        hydration proceeds.
        required_evidence_types:
        * end_to_end_test
            validation:
    * id: VAL-015
        method: command
        command_or_inspection: >-
        Execute crash points before send, during send, after acceptance, and
        before local acknowledgement, then verify replay and hydration.
        environment: controlled_test_service
        expected_result: PASS
        negative_cases:
    * duplicate_after_ack_loss
    * pending_entry_deleted_without_ack
    * infinite_retry_loop
    * new_hydration_precedes_required_replay
        rollback:
        strategy: preserve_journal_and_revert_recovery_worker
        trigger: replay_duplication_or_loss
        validation: Every pending entry remains inspectable and recoverable.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: local_recovery
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-009
* id: TASK-016
    title: Materialize Claude Code adapter manifest and capabilities
    definition_status: blocked
    workstream_id: WS-008
    wave_id: W4
    target_id: TARGET-004
    execution_kind: repo_local
    objective: >-
    Create the canonical Claude Code adapter package with registry-consistent
    identity, capabilities, MCP configuration, environment contract, and setup
    documentation.
    authority_basis_ids:
    * AUTH-005
    * AUTH-008
        required_decision_ids:
    * DEC-006
        blocking_unknown_ids:
    * UNK-017
        input_evidence_ids:
    * EVID-003
    * EVID-010
        actions:
    * create_adapter_yaml
    * create_capabilities_yaml
    * create_mcp_template
    * create_environment_example
    * create_setup_and_reference_documentation
    * align_registry_identity_token_source_and_runtime_projection
        outputs:
    * id: OUT-029
        type: artifact
        location: environment/agents/adapters/claude-code/adapter.yaml
        required: true
    * id: OUT-030
        type: artifact
        location: environment/agents/adapters/claude-code/capabilities.yaml
        required: true
    * id: OUT-031
        type: artifact
        location: environment/agents/adapters/claude-code/mcp.template.json
        required: true
        acceptance:
    * id: AC-031
        statement: >-
        Registry, manifest, capabilities, environment, and MCP identity fields
        are consistent and schema-valid.
        required_evidence_types:
        * schema_validation
        * identity_validation
    * id: AC-032
        statement: >-
        Claude Code declares only capabilities proven or scheduled for
        conformance before activation.
        required_evidence_types:
        * capability_review
            validation:
    * id: VAL-016
        method: command
        command_or_inspection: >-
        Run adapter schema, identity consistency, secret scan, and manifest-
        capabilities cross-reference validation.
        environment: local
        expected_result: PASS
        negative_cases:
    * identity_mismatch
    * literal_secret_committed
    * unsupported_capability_declared
    * Claude_specific_memory_transport_configured
        rollback:
        strategy: remove_unaccepted_Claude_adapter_directory
        trigger: contract_or_identity_validation_failure
        validation: Existing Claude environment remains unchanged.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: adapter_definition
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-010
* id: TASK-017
    title: Implement Claude Code native lifecycle bridge
    definition_status: blocked
    workstream_id: WS-008
    wave_id: W4
    target_id: TARGET-004
    execution_kind: repo_local
    objective: >-
    Map Claude Code native lifecycle events into the shared runtime while
    keeping native entrypoints thin and memory-domain agnostic.
    authority_basis_ids:
    * AUTH-005
    * AUTH-004
        required_decision_ids:
    * DEC-007
        blocking_unknown_ids:
    * UNK-006
    * UNK-008
    * UNK-017
        input_evidence_ids:
    * EVID-004
    * EVID-017
        actions:
    * map_session_start_to_canonical_initialization
    * map_pre_tool_events_to_operation_proposal
    * map_stop_and_abort_to_finalization_or_recovery
    * invoke_shared_lifecycle_runner
    * inject_hydrated_context_without_persisting_contents
    * wire_settings_template_and_setup_idempotently
        outputs:
    * id: OUT-032
        type: artifact
        location: environment/agents/adapters/claude-code/hooks
        required: true
    * id: OUT-033
        type: artifact
        location: environment/agents/adapters/claude-code/mappings/lifecycle.yaml
        required: true
    * id: OUT-034
        type: artifact
        location: environment/agents/adapters/claude-code/mappings/operations.yaml
        required: true
        acceptance:
    * id: AC-033
        statement: >-
        Native Claude events are translated to canonical events without
        implementing memory transport or policy semantics in the hook.
        required_evidence_types:
        * integration_test
        * architecture_test
    * id: AC-034
        statement: Setup is idempotent and preserves unexplained user settings.
        required_evidence_types:
        * installation_test
            validation:
    * id: VAL-017
        method: command
        command_or_inspection: >-
        Run native event fixtures, settings merge tests, repeated installer
        tests, and shared-runtime invocation tests.
        environment: Claude_Code_test_environment
        expected_result: PASS
        negative_cases:
    * hook_calls_HTTP_directly
    * setup_overwrites_user_settings
    * duplicate_hook_registration
    * unsupported_event_silently_ignored
        rollback:
        strategy: restore_prior_settings_and_disable_new_native_bridge
        trigger: native_integration_or_installer_failure
        validation: Existing Claude Code session startup and legacy hooks remain intact.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: Claude_Code_surface
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-010
* id: TASK-018
    title: Capture legacy fixtures and enable MCP shadow mode
    definition_status: blocked
    workstream_id: WS-009
    wave_id: W4
    target_id: TARGET-005
    execution_kind: repo_local
    objective: >-
    Encode legacy externally meaningful behavior as regression fixtures and run
    the new shared-CLI path in non-authoritative comparison mode.
    authority_basis_ids:
    * AUTH-005
    * AUTH-012
    * AUTH-010
        required_decision_ids:
    * DEC-008
        blocking_unknown_ids:
    * UNK-008
    * UNK-009
        input_evidence_ids:
    * EVID-004
    * EVID-018
        actions:
    * create_legacy_behavioral_golden_fixtures
    * classify_differences_as_intended_compatible_breaking_or_unknown
    * implement_legacy_MCP_shadow_and_MCP_enforced_modes
    * preserve_one_authoritative_path_in_shadow_mode
    * prevent_duplicate_claims_and_ingestion
    * emit_structured_equivalence_metrics
        outputs:
    * id: OUT-035
        type: test_fixture
        location: environment/agents/conformance/legacy_fixtures
        required: true
    * id: OUT-036
        type: artifact
        location: environment/agents/runtime/migration_mode.py
        required: true
        acceptance:
    * id: AC-035
        statement: >-
        Every material legacy behavior has a fixture or an explicit,
        authority-approved replacement rationale.
        required_evidence_types:
        * regression_fixture
        * architecture_review
    * id: AC-036
        statement: Shadow mode creates no duplicate active authority or memory episode.
        required_evidence_types:
        * integration_test
            validation:
    * id: VAL-018
        method: command
        command_or_inspection: >-
        Run legacy and shared-CLI implementations against identical fixtures
        and verify zero unexplained unsafe divergence.
        environment: local_and_controlled_service
        expected_result: PASS
        negative_cases:
    * duplicate_claim_in_shadow
    * duplicate_ingest_in_shadow
    * unknown_difference_ignored
    * legacy_behavior_deleted_before_fixture
        rollback:
        strategy: set_pipeline_mode_to_legacy_and_preserve_shadow_evidence
        trigger: unsafe_or_unexplained_shadow_divergence
        validation: Legacy path remains authoritative and no duplicate state remains.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: migration_behavior
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-011
* id: TASK-019
    title: Execute governed-operation end-to-end certification
    definition_status: blocked
    workstream_id: WS-007
    wave_id: W5
    target_id: TARGET-009
    execution_kind: end_to_end_test
    objective: >-
    Prove hydration, conflict checks, claims, mutation gating, commit, push
    simulation, and final ingestion through real hooks, real CLI, and a
    controlled memory service.
    authority_basis_ids:
    * AUTH-010
    * AUTH-007
        required_decision_ids:
    * DEC-001
    * DEC-003
        blocking_unknown_ids:
    * UNK-007
    * UNK-010
    * UNK-017
        input_evidence_ids:
    * EVID-013
    * EVID-017
    * EVID-019
        actions:
    * create_temporary_repository_and_bare_remote
    * start_Claude_session_and_hydrate
    * acquire_claim_for_exact_scope
    * mutate_governed_path
    * verify_claim_before_commit_and_push_simulation
    * ingest_session_and_hydrate_next_session
    * verify_unauthorized_variants_are_denied
        outputs:
    * id: OUT-037
        type: test_suite
        location: environment/agents/conformance/e2e/test_reference_adapter.py
        required: true
        acceptance:
    * id: AC-037
        statement: >-
        The complete reference flow succeeds only with valid current authority
        and preserves memory continuity across sessions.
        required_evidence_types:
        * end_to_end_test
    * id: AC-038
        statement: >-
        Missing hydration, missing claim, expired claim, and scope mismatch
        each deny governed boundaries.
        required_evidence_types:
        * negative_test
            validation:
    * id: VAL-019
        method: command
        command_or_inspection: >-
        Execute the real reference-adapter E2E suite using temporary
        repositories, temporary remotes, real CLI, and controlled service.
        environment: isolated_local_and_CI
        expected_result: PASS
        negative_cases:
    * commit_without_claim
    * push_with_expired_claim
    * protected_path_added_after_claim
    * wrong_agent_claim
    * next_session_missing_prior_episode
        rollback:
        strategy: destroy_ephemeral_repositories_services_and_test_claims
        trigger: E2E_failure
        validation: No production repository, remote, or service state is modified.
        risk:
        tier: T2
        reversibility: fully_reversible
        blast_radius: isolated_test_environment
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: true
        push: true
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: true
        external_message: false
        completion_gate_ids:
    * GATE-012
* id: TASK-020
    title: Execute concurrency, idempotency, and crash-recovery E2E
    definition_status: blocked
    workstream_id: WS-007
    wave_id: W5
    target_id: TARGET-009
    execution_kind: end_to_end_test
    objective: >-
    Prove safe overlapping-claim rejection, non-overlapping concurrency,
    duplicate prevention, stale-lease rejection, and durable recovery.
    authority_basis_ids:
    * AUTH-010
    * AUTH-007
        required_decision_ids:
    * DEC-001
    * DEC-003
    * DEC-004
        blocking_unknown_ids:
    * UNK-009
    * UNK-012
        input_evidence_ids:
    * EVID-015
    * EVID-018
    * EVID-020
        actions:
    * run_two_identity_overlapping_claim_scenario
    * run_non_overlapping_scope_parallel_scenario
    * expire_and_revoke_claims_mid_session
    * inject_crashes_before_and_after_ingest_acceptance
    * replay_pending_journal_with_same_idempotency_key
    * verify_single_episode_and_correct_conflict_outcomes
        outputs:
    * id: OUT-038
        type: test_suite
        location: environment/agents/conformance/e2e/test_concurrency_and_recovery.py
        required: true
        acceptance:
    * id: AC-039
        statement: >-
        Overlapping governed scopes cannot be concurrently authorized to
        competing principals.
        required_evidence_types:
        * concurrency_test
    * id: AC-040
        statement: >-
        Crash and acknowledgement-loss recovery creates exactly one durable
        episode.
        required_evidence_types:
        * crash_recovery_test
            validation:
    * id: VAL-020
        method: command
        command_or_inspection: >-
        Run concurrent multi-agent, lease expiry, revocation, duplicate
        ingest, and acknowledgement-loss scenarios repeatedly.
        environment: isolated_local_and_CI
        expected_result: PASS
        negative_cases:
    * split_brain_overlapping_claim
    * stale_claim_mutation
    * duplicate_episode
    * lost_pending_journal
    * non_overlapping_work_unnecessarily_blocked
        rollback:
        strategy: remove_ephemeral_test_state_and_revoke_all_test_claims
        trigger: concurrency_or_recovery_failure
        validation: Test service contains no active claims or unreconciled episodes.
        risk:
        tier: T2
        reversibility: fully_reversible
        blast_radius: isolated_test_environment
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: true
        push: true
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: true
        external_message: false
        completion_gate_ids:
    * GATE-013
* id: TASK-021
    title: Execute outage, corruption, and security fault injection
    definition_status: blocked
    workstream_id: WS-007
    wave_id: W5
    target_id: TARGET-009
    execution_kind: fault_injection
    objective: >-
    Validate explicit degraded states, fail-closed governed boundaries,
    secret safety, state integrity, and operator-visible remediation under
    adverse conditions.
    authority_basis_ids:
    * AUTH-009
    * AUTH-010
        required_decision_ids:
    * DEC-004
    * DEC-008
        blocking_unknown_ids:
    * UNK-016
        input_evidence_ids:
    * EVID-021
    * EVID-022
        actions:
    * inject_network_timeout_reset_rate_limit_and_server_errors
    * inject_malformed_and_truncated_CLI_output
    * inject_corrupted_receipts_symlinks_permission_failures_and_disk_full
    * rotate_or_expire_tokens_mid_session
    * revoke_claim_between_check_and_boundary
    * verify_degraded_read_only_and_durable_queue_behavior
        outputs:
    * id: OUT-039
        type: test_suite
        location: environment/agents/conformance/fault_injection
        required: true
        acceptance:
    * id: AC-041
        statement: >-
        Harmless read-only work may continue only in declared degraded modes,
        while governed mutation remains denied.
        required_evidence_types:
        * fault_injection
    * id: AC-042
        statement: >-
        No injected failure leaks secrets, loses local work, or fabricates
        durable memory delivery.
        required_evidence_types:
        * security_test
        * resilience_test
            validation:
    * id: VAL-021
        method: command
        command_or_inspection: >-
        Run the complete network, process, identity, filesystem, protocol, and
        storage fault matrix.
        environment: isolated_local_and_CI
        expected_result: PASS
        negative_cases:
    * service_outage_allows_commit
    * corrupted_receipt_grants_authority
    * token_rotation_logs_secret
    * disk_full_discards_episode
    * malformed_output_treated_as_success
        rollback:
        strategy: restore_test_environment_and_preserve_failure_receipts
        trigger: fault_injection_harness_or_runtime_failure
        validation: No production state changed and every injected failure is traceable.
        risk:
        tier: T2
        reversibility: fully_reversible
        blast_radius: isolated_test_environment
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: true
        push: true
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: true
        external_message: false
        completion_gate_ids:
    * GATE-014
* id: TASK-022
    title: Execute Claude Code MCP-enforced canary and rollback rehearsal
    definition_status: blocked
    workstream_id: WS-009
    wave_id: W5
    target_id: TARGET-004
    execution_kind: controlled_canary
    objective: >-
    Run the reference adapter in MCP-enforced mode within a controlled Claude
    Code environment and prove immediate operational rollback.
    authority_basis_ids:
    * AUTH-012
    * AUTH-010
        required_decision_ids:
    * DEC-008
        blocking_unknown_ids:
    * UNK-016
        input_evidence_ids:
    * EVID-022
    * EVID-024
    * EVID-025
        actions:
    * enable_MCP_enforced_mode_in_controlled_environment
    * run_representative_hydration_claim_mutation_and_ingest_sessions
    * monitor_equivalence_latency_denials_and_pending_ingestion
    * revert_to_legacy_mode
    * replay_pending_journal_and_reconcile_claims
    * repeat_canary_after_successful_rollback
        outputs:
    * id: OUT-040
        type: receipt
        location: controller/evidence/claude-canary-receipt.json
        required: true
    * id: OUT-041
        type: receipt
        location: controller/evidence/rollback-rehearsal-receipt.json
        required: true
        acceptance:
    * id: AC-043
        statement: >-
        MCP-enforced canary completes with no unsafe divergence, lost
        ingestion, identity mismatch, or unauthorized allow.
        required_evidence_types:
        * canary_receipt
    * id: AC-044
        statement: >-
        Rollback restores operational safety and reconciles all pending state.
        required_evidence_types:
        * rollback_receipt
            validation:
    * id: VAL-022
        method: inspection
        command_or_inspection: >-
        Independently verify canary logs, claim state, journal state,
        ingestion acknowledgements, and post-rollback legacy operation.
        environment: controlled_Claude_Code_environment
        expected_result: PASS
        negative_cases:
    * unsafe_allow_during_canary
    * pending_episode_lost_on_rollback
    * active_claim_left_after_rollback
    * configuration_not_restored
        rollback:
        strategy: switch_to_legacy_mode_restore_prior_wiring_and_reconcile_pending_state
        trigger: any_canary_blocking_failure
        validation: Legacy pipeline is authoritative and all pending episodes are preserved.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: controlled_Claude_Code_environment
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: true
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-015
* id: TASK-023
    title: Remove superseded Claude Code memory implementation
    definition_status: blocked
    workstream_id: WS-009
    wave_id: W6
    target_id: TARGET-005
    execution_kind: repo_local
    objective: >-
    Delete Claude-specific memory transport, domain schemas, local authority,
    obsolete tests, and obsolete validators only after independently verified
    cutover readiness.
    authority_basis_ids:
    * AUTH-005
    * AUTH-012
        required_decision_ids:
    * DEC-008
        blocking_unknown_ids:
    * UNK-008
    * UNK-009
    * UNK-016
        input_evidence_ids:
    * EVID-018
    * EVID-024
    * EVID-025
        actions:
    * remove_legacy_memory_transport_and_client
    * remove_duplicate_memory_state_and_schemas
    * remove_obsolete_memory_hooks_and_validation_targets
    * remove_or_rewrite_obsolete_tests_after_assertion_parity
    * remove_dangling_installer_Makefile_and_CI_references
    * preserve_non_memory_Claude_governance_integrations
        outputs:
    * id: OUT-042
        type: repository_diff
        location: git_diff
        required: true
        acceptance:
    * id: AC-045
        statement: >-
        No Claude-specific memory transport, conflict semantics, local lock
        authority, or duplicate identity logic remains.
        required_evidence_types:
        * architecture_test
        * diff
    * id: AC-046
        statement: >-
        Every removed behavioral assertion has an equivalent shared-runtime or
        conformance test.
        required_evidence_types:
        * test_mapping
            validation:
    * id: VAL-023
        method: command
        command_or_inspection: >-
        Run forbidden-pattern, dependency, dangling-reference, regression,
        adapter, and full repository test suites.
        environment: local
        expected_result: PASS
        negative_cases:
    * direct_memory_client_remains
    * old_hook_reference_remains
    * removed_test_without_replacement
    * non_memory_Claude_governance_removed
        rollback:
        strategy: revert_legacy_deletion_commit_and_restore_legacy_mode
        trigger: regression_or_cutover_failure
        validation: Legacy pipeline files, wiring, tests, and pending state are restored.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: Claude_Code_memory_pipeline
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: true
        external_message: false
        completion_gate_ids:
    * GATE-016
* id: TASK-024
    title: Build reusable adapter generator and implementation guide
    definition_status: blocked
    workstream_id: WS-002
    wave_id: W6
    target_id: TARGET-003
    execution_kind: repo_local
    objective: >-
    Provide deterministic scaffolding, validation, and documentation for
    future peer adapters without copy-paste divergence.
    authority_basis_ids:
    * AUTH-004
    * AUTH-008
        required_decision_ids:
    * DEC-006
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-010
    * EVID-023
        actions:
    * implement_create_adapter_tool
    * generate_manifest_capabilities_MCP_environment_mapping_and_test_scaffolds
    * validate_generated_adapter_immediately
    * document_mandatory_optional_and_prohibited_patterns
    * document_capability_to_conformance_mapping
    * document_identity_failure_and_migration_semantics
        outputs:
    * id: OUT-043
        type: artifact
        location: environment/agents/tools/create_adapter.py
        required: true
    * id: OUT-044
        type: documentation
        location: environment/agents/docs/ADAPTER_IMPLEMENTATION_GUIDE.md
        required: true
        acceptance:
    * id: AC-047
        statement: >-
        A generated adapter is structurally and schema valid without copying
        another adapter.
        required_evidence_types:
        * generator_test
    * id: AC-048
        statement: >-
        The guide distinguishes required contracts, optional native strength,
        unsupported shortcuts, and certification requirements.
        required_evidence_types:
        * documentation_review
            validation:
    * id: VAL-024
        method: command
        command_or_inspection: >-
        Generate a temporary adapter, run all schema and structure validators,
        and verify deterministic repeated output.
        environment: local_and_CI
        expected_result: PASS
        negative_cases:
    * generated_adapter_contains_Claude_specific_fields
    * generated_secret_value
    * nondeterministic_scaffold
    * claimed_capability_without_test_stub
        rollback:
        strategy: remove_generator_and_generated_test_fixtures
        trigger: invalid_or_non_reusable_scaffolding
        validation: Existing adapter contracts remain unchanged.
        risk:
        tier: T1
        reversibility: fully_reversible
        blast_radius: adapter_scaffolding
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-017
* id: TASK-025
    title: Select and materialize second peer adapter
    definition_status: blocked
    workstream_id: WS-010
    wave_id: W7
    target_id: TARGET-011
    execution_kind: repo_local
    objective: >-
    Select one representative peer and integrate it using only canonical
    schemas, shared runtime, native mappings, and generated scaffolding.
    authority_basis_ids:
    * AUTH-013
    * AUTH-004
        required_decision_ids:
    * DEC-009
        blocking_unknown_ids:
    * UNK-014
        input_evidence_ids:
    * EVID-003
    * EVID-026
        actions:
    * assess_candidate_peer_surfaces
    * record_selected_peer_decision
    * generate_peer_adapter_scaffold
    * implement_native_lifecycle_and_operation_mappings
    * declare_only_supported_capabilities
    * prohibit_shared_runtime_or_foundational_schema_changes
        outputs:
    * id: OUT-045
        type: adapter
        location: environment/agents/adapters/selected-second-peer
        required: true
        acceptance:
    * id: AC-049
        statement: >-
        The second peer uses the canonical adapter package and shared runtime
        without foundational contract modification.
        required_evidence_types:
        * diff
        * schema_validation
    * id: AC-050
        statement: >-
        Native differences are isolated to adapter manifest, capabilities,
        mappings, and thin entrypoints.
        required_evidence_types:
        * architecture_review
            validation:
    * id: VAL-025
        method: command
        command_or_inspection: >-
        Run adapter schema, identity, mapping, and shared-core unchanged checks.
        environment: local
        expected_result: PASS
        negative_cases:
    * shared_runtime_forked_for_peer
    * foundational_schema_modified
    * unsupported_capability_declared
    * peer_adapter_is_static_copy_only
        rollback:
        strategy: remove_unaccepted_second_peer_adapter
        trigger: core_change_or_conformance_failure
        validation: Shared runtime and canonical schemas remain at pre-task revisions.
        risk:
        tier: T2
        reversibility: fully_reversible
        blast_radius: second_peer_adapter
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-018
* id: TASK-026
    title: Certify second peer through shared conformance and E2E
    definition_status: blocked
    workstream_id: WS-010
    wave_id: W7
    target_id: TARGET-009
    execution_kind: conformance_test
    objective: >-
    Prove capability-derived conformance and lifecycle portability for the
    selected second peer.
    authority_basis_ids:
    * AUTH-010
    * AUTH-013
        required_decision_ids:
    * DEC-009
        blocking_unknown_ids: []
        input_evidence_ids:
    * EVID-026
        actions:
    * derive_required_tests_from_declared_capabilities
    * run_manifest_identity_lifecycle_policy_and_CLI_contract_tests
    * run_supported_shared_E2E_scenarios
    * verify_shared_runtime_and_schema_diffs_are_empty
    * record_unsupported_native_capabilities_truthfully
        outputs:
    * id: OUT-046
        type: receipt
        location: controller/evidence/second-peer-conformance-receipt.json
        required: true
        acceptance:
    * id: AC-051
        statement: >-
        Every declared second-peer capability has passing conformance evidence.
        required_evidence_types:
        * conformance_test
    * id: AC-052
        statement: >-
        The second peer demonstrates actual runtime reuse without foundational
        changes.
        required_evidence_types:
        * exact_diff
        * end_to_end_test
            validation:
    * id: VAL-026
        method: command
        command_or_inspection: >-
        Run the capability-derived conformance suite and supported multi-agent
        E2E scenarios for the selected peer.
        environment: local_and_CI
        expected_result: PASS
        negative_cases:
    * capability_without_required_test
    * shared_runtime_modified
    * foundational_schema_modified
    * unsupported_feature_reported_as_supported
        rollback:
        strategy: remove_second_peer_certification_and_revert_unaccepted_adapter
        trigger: conformance_or_reuse_failure
        validation: Claude reference adapter and shared runtime remain unaffected.
        risk:
        tier: T2
        reversibility: fully_reversible
        blast_radius: peer_reuse_certification
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: true
        external_message: false
        completion_gate_ids:
    * GATE-018
* id: TASK-027
    title: Add architecture fitness functions and CI suites
    definition_status: blocked
    workstream_id: WS-011
    wave_id: W8
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Continuously prevent direct memory transport, duplicate semantics,
    capability drift, identity inconsistency, missing tests, and adapter
    bypasses.
    authority_basis_ids:
    * AUTH-002
    * AUTH-004
    * AUTH-010
        required_decision_ids: []
        blocking_unknown_ids:
    * UNK-013
        input_evidence_ids:
    * EVID-023
    * EVID-027
        actions:
    * add_adapter_schema_CI_job
    * add_real_CLI_contract_CI_job
    * add_memory_E2E_and_fault_injection_jobs
    * add_forbidden_transport_and_dependency_checks
    * add_capability_to_test_coverage_checks
    * add_documentation_and_dangling_reference_checks
    * add_minimum_and_current_CLI_version_matrix
        outputs:
    * id: OUT-047
        type: CI_configuration
        location: repository_CI_workflows
        required: true
    * id: OUT-048
        type: architecture_test
        location: environment/agents/conformance/architecture
        required: true
        acceptance:
    * id: AC-053
        statement: >-
        CI fails when an adapter reintroduces direct memory transport,
        duplicate domain semantics, invalid identity, or unproven capability.
        required_evidence_types:
        * CI_test
    * id: AC-054
        statement: >-
        All reference and second-peer conformance suites run at exact candidate
        revisions.
        required_evidence_types:
        * CI_configuration
            validation:
    * id: VAL-027
        method: command
        command_or_inspection: >-
        Run all repository-owned validation, architecture, contract, E2E, and
        fault-injection targets locally before remote execution.
        environment: local
        expected_result: PASS
        negative_cases:
    * direct_HTTP_client_not_detected
    * missing_capability_test_not_detected
    * dangling_legacy_reference_not_detected
    * mock_only_CLI_validation
        rollback:
        strategy: revert_new_CI_jobs_and_architecture_checks_as_one_unit
        trigger: nondeterministic_or_invalid_CI_behavior
        validation: Existing required CI remains intact.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: repository_CI
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-019
* id: TASK-028
    title: Update architecture decisions and memory topology
    definition_status: blocked
    workstream_id: WS-011
    wave_id: W8
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Record the accepted shared CLI architecture, preserved enforcement
    invariant, authority boundaries, migration evidence, and final topology.
    authority_basis_ids:
    * AUTH-004
    * AUTH-002
        required_decision_ids:
    * DEC-010
        blocking_unknown_ids:
    * UNK-008
        input_evidence_ids:
    * EVID-005
    * EVID-018
    * EVID-024
    * EVID-026
        actions:
    * author_new_architecture_decision
    * supersede_or_amend_ADR_0002_per_accepted_decision
    * document_shared_CLI_runtime_service_and_adapter_boundaries
    * document_migration_modes_and_deletion_gate
    * update_memory_topology_and_failure_semantics
    * add_forward_and_backward_ADR_links
        outputs:
    * id: OUT-049
        type: architecture_decision
        location: docs/decisions/ADR-shared-mcp-memory-adapter-foundation.md
        required: true
    * id: OUT-050
        type: documentation
        location: environment/agents/docs/MEMORY_TOPOLOGY.md
        required: true
        acceptance:
    * id: AC-055
        statement: >-
        The architecture decision preserves the evidence and enforcement
        invariant of ADR-0002 while replacing its implementation mechanism.
        required_evidence_types:
        * architecture_review
    * id: AC-056
        statement: >-
        Documentation distinguishes transport, runtime enforcement, memory
        truth, identity, coordination, and delivery ownership.
        required_evidence_types:
        * documentation_review
            validation:
    * id: VAL-028
        method: inspection
        command_or_inspection: >-
        Verify ADR links, topology consistency, terminology, accepted decision
        mapping, and absence of superseded architecture claims.
        environment: local
        expected_result: PASS
        negative_cases:
    * ADR_claims_model_only_enforcement
    * ADR_erases_prior_failure_evidence
    * topology_assigns_claim_truth_to_adapter
    * supersession_links_missing
        rollback:
        strategy: revert_unaccepted_ADR_and_topology_changes
        trigger: architecture_authority_or_consistency_failure
        validation: Prior ADR history remains intact.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: architecture_governance
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-020
* id: TASK-029
    title: Update protected-root governance references
    definition_status: blocked
    workstream_id: WS-011
    wave_id: W8
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Replace obsolete Claude-specific memory-gate language in protected root
    files without weakening canonical governance.
    authority_basis_ids:
    * AUTH-002
        required_decision_ids:
    * DEC-011
        blocking_unknown_ids:
    * UNK-010
    * UNK-015
        input_evidence_ids:
    * EVID-001
    * EVID-029
        actions:
    * inspect_current_root_append_only_and_deletion_controls
    * identify_exact_obsolete_gate_references
    * preserve_deterministic_enforcement_invariant
    * add_required_ALLOW_ROOT_DELETION_markers
    * obtain_required_CODEOWNERS_review_evidence
        outputs:
    * id: OUT-051
        type: repository_diff
        location: AGENTS.md_and_CANONICAL_LAW.md_if_required
        required: true
        acceptance:
    * id: AC-057
        statement: >-
        Protected-root text reflects the shared CLI architecture and retains
        deterministic enforcement requirements.
        required_evidence_types:
        * diff
        * governance_review
    * id: AC-058
        statement: >-
        Every non-additive root change has the exact required marker and review
        path.
        required_evidence_types:
        * marker_validation
        * review_evidence
            validation:
    * id: VAL-029
        method: command
        command_or_inspection: >-
        Run root append-only validation, marker checks, CODEOWNERS inspection,
        and semantic governance regression review.
        environment: local
        expected_result: PASS
        negative_cases:
    * missing_root_deletion_marker
    * deterministic_gate_invariant_removed
    * unauthorized_CANONICAL_LAW_change
    * stale_legacy_reference_retained
        rollback:
        strategy: restore_protected_root_files_to_exact_baseline
        trigger: marker_review_or_governance_failure
        validation: Root-file digests match the admission baseline.
        risk:
        tier: T3
        reversibility: reversible
        blast_radius: canonical_governance
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-020
* id: TASK-030
    title: Reconcile registry, validators, setup, docs, and legacy references
    definition_status: blocked
    workstream_id: WS-011
    wave_id: W8
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Complete repository-wide convergence so all active contracts, setup paths,
    validators, commands, and documentation point to the canonical foundation.
    authority_basis_ids:
    * AUTH-002
    * AUTH-004
    * AUTH-008
        required_decision_ids:
    * DEC-011
        blocking_unknown_ids:
    * UNK-015
        input_evidence_ids:
    * EVID-003
    * EVID-023
    * EVID-029
        actions:
    * remove_Claude_adapter_exemption
    * validate_adapter_yaml_and_capabilities_yaml
    * update_registry_adapter_path_and_secret_projection_docs
    * update_setup_Makefile_commands_rules_and_end_session_docs
    * remove_dangling_legacy_references
    * add_adapter_generator_and_reference_architecture_docs
        outputs:
    * id: OUT-052
        type: repository_diff
        location: environment_agents_and_related_repository_docs
        required: true
        acceptance:
    * id: AC-059
        statement: >-
        Claude Code satisfies the same canonical adapter contract as peers,
        with explicit native capability declarations.
        required_evidence_types:
        * adapter_validation
    * id: AC-060
        statement: >-
        Repository-wide searches find no unexplained obsolete pipeline
        reference or duplicate memory authority.
        required_evidence_types:
        * reference_scan
            validation:
    * id: VAL-030
        method: command
        command_or_inspection: >-
        Run adapter validators, documentation consistency checks, recursive
        legacy-reference scans, and full repository validation.
        environment: local
        expected_result: PASS
        negative_cases:
    * Claude_adapter_still_exempt
    * obsolete_setup_path
    * duplicate_token_configuration
    * dangling_Make_target
    * documentation_claims_retired_behavior
        rollback:
        strategy: revert_registry_validator_setup_and_documentation_changes
        trigger: cross_reference_or_validation_failure
        validation: Existing repository validation returns to baseline behavior.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: repository_integration
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-021
* id: TASK-031
    title: Create evidence-bound local commit stack
    definition_status: blocked
    workstream_id: WS-012
    wave_id: W9
    target_id: TARGET-001
    execution_kind: repo_local
    objective: >-
    Organize the implementation into independently reviewable commits, bind
    exact candidate revisions, and prepare an approval packet for remote push.
    authority_basis_ids:
    * AUTH-002
    * AUTH-011
        required_decision_ids:
    * DEC-012
        blocking_unknown_ids:
    * UNK-002
    * UNK-013
        input_evidence_ids:
    * EVID-027
    * EVID-029
        actions:
    * verify_clean_or_owned_worktree
    * rebase_or_refresh_only_with_exact_authority
    * create_logical_reversible_commit_stack
    * bind_validation_receipts_to_each_candidate_revision
    * prepare_exact_push_approval_packet
    * stop_before_remote_push
        outputs:
    * id: OUT-053
        type: git_commits
        location: local_branch
        required: true
    * id: OUT-054
        type: approval_packet
        location: controller/approvals/push-approval.yaml
        required: true
        acceptance:
    * id: AC-061
        statement: >-
        Local commits are logically partitioned, validation-bound, and contain
        no unexplained work.
        required_evidence_types:
        * commit_history
        * validation_receipt
    * id: AC-062
        statement: >-
        The push request identifies exact branch, candidate SHA, paths, risks,
        checks, and rollback.
        required_evidence_types:
        * approval_packet
            validation:
    * id: VAL-031
        method: command
        command_or_inspection: >-
        Run the complete local validation suite at the final candidate SHA and
        inspect commit contents against task boundaries.
        environment: local
        expected_result: PASS
        negative_cases:
    * unrelated_work_in_commit
    * validation_receipt_bound_to_wrong_SHA
    * protected_root_marker_missing
    * remote_push_without_exact_approval
        rollback:
        strategy: reset_local_campaign_branch_to_admission_baseline_after_preserving_diff
        trigger: commit_stack_or_validation_failure
        validation: No remote branch or pull request exists.
        risk:
        tier: T2
        reversibility: reversible
        blast_radius: local_git_history
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: true
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-022
* id: TASK-032
    title: Push approved branch and verify remote CI
    definition_status: blocked
    workstream_id: WS-012
    wave_id: W9
    target_id: TARGET-010
    execution_kind: remote_mutation
    objective: >-
    Push the exact approved candidate branch and independently observe required
    CI results without creating a pull request.
    authority_basis_ids:
    * AUTH-011
        required_decision_ids:
    * DEC-012
        blocking_unknown_ids:
    * UNK-013
        input_evidence_ids:
    * EVID-027
    * EVID-028
    * EVID-029
        actions:
    * validate_exact_push_approval
    * reverify_candidate_SHA_and_branch
    * push_exact_branch
    * observe_remote_branch_revision
    * observe_required_CI_checks
    * prepare_exact_pull_request_approval_packet
        outputs:
    * id: OUT-055
        type: remote_evidence
        location: controller/evidence/remote-branch-and-CI.json
        required: true
    * id: OUT-056
        type: approval_packet
        location: controller/approvals/pull-request-approval.yaml
        required: true
        acceptance:
    * id: AC-063
        statement: >-
        The observed remote branch points to the exact approved candidate SHA.
        required_evidence_types:
        * remote_observation
    * id: AC-064
        statement: >-
        All required CI checks pass or failures are recorded without
        misreporting success.
        required_evidence_types:
        * CI_result
            validation:
    * id: VAL-032
        method: inspection
        command_or_inspection: >-
        Independently inspect the remote branch, workflow runs, check suites,
        logs, and artifact identities.
        environment: GitHub
        expected_result: PASS
        negative_cases:
    * pushed_SHA_differs_from_approval
    * CI_failure_reported_as_pass
    * pull_request_created_without_approval
    * local_push_exit_used_as_remote_proof
        rollback:
        strategy: delete_unmerged_remote_branch_only_with_exact_approval_or_push_corrective_commit
        trigger: wrong_remote_candidate_or_blocking_CI_failure
        validation: Remote state and rollback action are independently observed.
        risk:
        tier: T3
        reversibility: reversible_before_merge
        blast_radius: remote_branch_and_CI
        authorization_ceiling:
        inspect: true
        local_write: false
        commit: false
        push: true
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-023
* id: TASK-033
    title: Create reviewed pull request and obtain exact merge decision
    definition_status: blocked
    workstream_id: WS-012
    wave_id: W9
    target_id: TARGET-010
    execution_kind: remote_mutation
    objective: >-
    Create the exact approved pull request, obtain required reviews and checks,
    and stop before merge unless separately authorized.
    authority_basis_ids:
    * AUTH-011
    * AUTH-002
        required_decision_ids:
    * DEC-012
        blocking_unknown_ids:
    * UNK-001
        input_evidence_ids:
    * EVID-028
    * EVID-029
        actions:
    * validate_exact_pull_request_approval
    * create_pull_request_for_exact_branch_and_base
    * attach_architecture_validation_and_rollback_evidence
    * obtain_required_CODEOWNERS_and_architecture_review
    * observe_final_required_checks
    * prepare_exact_merge_approval_packet
    * merge_only_when_exactly_authorized
        outputs:
    * id: OUT-057
        type: pull_request
        location: GitHub_pull_request
        required: true
    * id: OUT-058
        type: approval_packet
        location: controller/approvals/merge-approval.yaml
        required: true
        acceptance:
    * id: AC-065
        statement: >-
        The pull request contains the exact approved candidate and complete
        architecture, test, migration, and rollback evidence.
        required_evidence_types:
        * pull_request
        * review
    * id: AC-066
        statement: >-
        Merge occurs only under an exact current approval and produces an
        independently observed merge commit.
        required_evidence_types:
        * approval
        * remote_observation
            validation:
    * id: VAL-033
        method: inspection
        command_or_inspection: >-
        Inspect pull-request head and base SHAs, reviews, required checks,
        protected-root approvals, merge authority, and merge commit if
        authorized.
        environment: GitHub
        expected_result: PASS
        negative_cases:
    * PR_head_differs_from_approved_SHA
    * missing_CODEOWNERS_review
    * merge_without_exact_approval
    * merge_claim_without_observed_merge_commit
        rollback:
        strategy: close_unmerged_pull_request_or_prepare_forward_recovery_after_merge_with_exact_approval
        trigger: review_CI_or_authority_failure
        validation: Remote pull-request and merge state are independently observed.
        risk:
        tier: T3
        reversibility: reversible_before_merge_forward_recovery_after_merge
        blast_radius: canonical_repository_default_branch
        authorization_ceiling:
        inspect: true
        local_write: false
        commit: false
        push: false
        pull_request: true
        merge: true
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: false
        completion_gate_ids:
    * GATE-024
* id: TASK-034
    title: Export evidence-backed final handoff
    definition_status: blocked
    workstream_id: WS-013
    wave_id: W10
    target_id: TARGET-002
    execution_kind: program_control
    objective: >-
    Reconcile all campaign evidence, export the Controller handoff, and request
    the human program owner’s terminal verdict.
    authority_basis_ids:
    * AUTH-001
    * AUTH-010
        required_decision_ids: []
        blocking_unknown_ids:
    * UNK-001
        input_evidence_ids:
    * EVID-030
        actions:
    * reconcile_all_task_attempt_and_verification_receipts
    * reconcile_gate_evaluations
    * bind_final_repository_and_remote_revisions
    * record_accepted_decisions_remaining_unknowns_risks_and_waivers
    * record_rollback_state_and_pending_external_actions
    * export_controller_handoff_receipt
    * request_human_terminal_verdict
        outputs:
    * id: OUT-059
        type: receipt
        location: controller/handoff.json
        required: true
        acceptance:
    * id: AC-067
        statement: >-
        The handoff is schema-valid, revision-bound, evidence-complete, and
        distinguishes completed, failed, cancelled, and superseded work.
        required_evidence_types:
        * receipt
        * schema_validation
    * id: AC-068
        statement: >-
        The Controller recommends but does not declare the terminal verdict.
        required_evidence_types:
        * authority_review
            validation:
    * id: VAL-034
        method: inspection
        command_or_inspection: >-
        Validate the Controller Handoff Receipt against the canonical schema
        and independently reconcile all referenced evidence.
        environment: controller
        expected_result: PASS
        negative_cases:
    * controller_declares_terminal_verdict
    * missing_failed_task_or_attempt
    * unsupported_remote_event_claim
    * unresolved_risk_hidden
        rollback:
        strategy: regenerate_handoff_from_immutable_controller_ledger
        trigger: handoff_validation_or_reconciliation_failure
        validation: Prior evidence, receipts, and candidate revisions remain unchanged.
        risk:
        tier: T0
        reversibility: fully_reversible
        blast_radius: program_closeout
        authorization_ceiling:
        inspect: true
        local_write: true
        commit: false
        push: false
        pull_request: false
        merge: false
        publish_or_release: false
        deploy_or_migrate: false
        destructive_change: false
        external_message: true
        completion_gate_ids:
    * GATE-025

gates:

* id: GATE-001
    name: campaign_admission_and_program_owner_lock
    gate_type: entry
    blocking: true
    owner_authority_id: AUTH-001
    task_ids:
    * TASK-001
        required_evidence_ids:
    * EVID-001
        pass_criteria:
    * Immutable source is externally preserved and digest-bound.
    * Human program owner is explicit.
    * Program Execution v2 host and validator interfaces are verified.
    * Draft Blueprint passes template-mode validation.
        failure_effect: Block Blueprint acceptance, Controller bootstrap, and all mutation tasks.
* id: GATE-002
    name: repository_and_legacy_state_lock
    gate_type: entry
    blocking: true
    owner_authority_id: AUTH-002
    task_ids:
    * TASK-002
        required_evidence_ids:
    * EVID-002
    * EVID-003
    * EVID-004
    * EVID-005
        pass_criteria:
    * Exact repository identity, revision, branch, remotes, and dirty state are recorded.
    * Legacy memory pipeline inventory is complete.
    * Current adapter and ADR contracts are evidenced.
    * No unexplained work is absorbed or overwritten.
        failure_effect: Block implementation and migration planning for affected surfaces.
* id: GATE-003
    name: canonical_adapter_contracts_valid
    gate_type: architecture
    blocking: true
    owner_authority_id: AUTH-004
    task_ids:
    * TASK-003
        required_evidence_ids:
    * EVID-010
        pass_criteria:
    * All canonical schemas parse and validate.
    * Shared contracts contain no Claude-specific assumptions.
    * Compatibility and capability obligations are machine-checkable.
    * Independent schema verification passes.
        failure_effect: Block shared runtime and adapter implementation.
* id: GATE-004
    name: shared_CLI_and_memory_service_contract_locked
    gate_type: integration
    blocking: true
    owner_authority_id: AUTH-006
    task_ids:
    * TASK-004
    * TASK-005
        required_evidence_ids:
    * EVID-006
    * EVID-007
    * EVID-008
    * EVID-009
        pass_criteria:
    * Required CLI commands and automation behavior are verified.
    * Compatible CLI version and provenance are recorded.
    * Service protocol compatibility is proven.
    * Forged or inconsistent identity is rejected.
        failure_effect: Block runtime CLI integration and reference adapter activation.
* id: GATE-005
    name: lifecycle_policy_and_classification_foundation_valid
    gate_type: architecture
    blocking: true
    owner_authority_id: AUTH-004
    task_ids:
    * TASK-006
    * TASK-007
        required_evidence_ids:
    * EVID-010
    * EVID-012
    * EVID-017
        pass_criteria:
    * Lifecycle state transitions are deterministic and peer-neutral.
    * Operation classification covers all declared governed effects.
    * Unknown potentially mutating operations follow strict profile policy.
    * Independent unit and negative tests pass.
        failure_effect: Block enforcement, native adapter wiring, and E2E execution.
* id: GATE-006
    name: CLI_gateway_and_local_state_security_valid
    gate_type: security
    blocking: true
    owner_authority_id: AUTH-009
    task_ids:
    * TASK-008
    * TASK-009
        required_evidence_ids:
    * EVID-011
    * EVID-014
        pass_criteria:
    * Runtime uses only the shared CLI for memory transport.
    * CLI output is schema-validated before use.
    * Local state is external, atomic, minimally scoped, and non-authoritative.
    * Secret, symlink, permission, and corruption tests pass.
        failure_effect: Block identity, claim, ingestion, and adapter integration tasks.
* id: GATE-007
    name: identity_claim_and_mutation_enforcement_valid
    gate_type: security
    blocking: true
    owner_authority_id: AUTH-007
    task_ids:
    * TASK-010
    * TASK-011
        required_evidence_ids:
    * EVID-009
    * EVID-013
    * EVID-019
        pass_criteria:
    * Claims bind authenticated identity and exact repository context.
    * Governed boundaries require current verification.
    * Expired, revoked, forged, stale, and scope-mismatched claims are rejected.
    * Outage does not silently grant mutation authority.
        failure_effect: Block reference adapter activation and all cutover work.
* id: GATE-008
    name: bypass_and_real_CLI_contract_tests_pass
    gate_type: verification
    blocking: true
    owner_authority_id: AUTH-010
    task_ids:
    * TASK-012
    * TASK-013
        required_evidence_ids:
    * EVID-012
    * EVID-016
        pass_criteria:
    * All command and native-tool bypass cases are denied correctly.
    * The real CLI passes contract tests against the controlled service.
    * Version, schema, timeout, and malformed-response negatives pass.
    * Independent verification is bound to the exact candidate state.
        failure_effect: Block reference adapter E2E and CI promotion.
* id: GATE-009
    name: durable_ingestion_and_recovery_valid
    gate_type: resilience
    blocking: true
    owner_authority_id: AUTH-010
    task_ids:
    * TASK-014
    * TASK-015
        required_evidence_ids:
    * EVID-015
        pass_criteria:
    * Every ingest is acknowledged or retained durably.
    * Duplicate retries create one durable episode.
    * Crash and acknowledgement-loss recovery pass.
    * Secret redaction and payload limits pass.
        failure_effect: Block reference adapter activation and legacy writeback removal.
* id: GATE-010
    name: Claude_Code_reference_adapter_contract_valid
    gate_type: adapter_conformance
    blocking: true
    owner_authority_id: AUTH-005
    task_ids:
    * TASK-016
    * TASK-017
        required_evidence_ids:
    * EVID-010
    * EVID-017
        pass_criteria:
    * Adapter manifest and capabilities are schema-valid.
    * Identity matches the registry and authenticated service principal.
    * Native hooks contain only translation and shared-runtime invocation.
    * Installer is idempotent and preserves existing user work.
        failure_effect: Block shadow mode and Claude Code certification.
* id: GATE-011
    name: legacy_fixture_and_shadow_equivalence_valid
    gate_type: migration
    blocking: true
    owner_authority_id: AUTH-012
    task_ids:
    * TASK-018
        required_evidence_ids:
    * EVID-004
    * EVID-018
        pass_criteria:
    * Every material legacy behavior has a fixture or accepted replacement.
    * Shadow mode has one authoritative path.
    * No duplicate claims, episodes, or enforcement decisions occur.
    * No unexplained unsafe divergence remains.
        failure_effect: Block MCP-enforced E2E, canary, and legacy deletion.
* id: GATE-012
    name: reference_adapter_governed_E2E_pass
    gate_type: end_to_end
    blocking: true
    owner_authority_id: AUTH-010
    task_ids:
    * TASK-019
        required_evidence_ids:
    * EVID-019
        pass_criteria:
    * Hydrate, conflict check, claim, governed mutation, verification, and ingest succeed end to end.
    * Unauthorized variants are denied.
    * Next-session hydration observes prior-session ingestion.
    * Exact candidate revisions and test environments are recorded.
        failure_effect: Block canary and reference certification.
* id: GATE-013
    name: concurrency_and_recovery_E2E_pass
    gate_type: end_to_end
    blocking: true
    owner_authority_id: AUTH-010
    task_ids:
    * TASK-020
        required_evidence_ids:
    * EVID-015
    * EVID-020
        pass_criteria:
    * Overlapping competing claims are rejected.
    * Safe non-overlapping work is allowed.
    * Stale, expired, and revoked claims fail.
    * Crash recovery produces exactly one episode.
        failure_effect: Block canary and reference certification.
* id: GATE-014
    name: fault_injection_and_degraded_mode_pass
    gate_type: resilience
    blocking: true
    owner_authority_id: AUTH-009
    task_ids:
    * TASK-021
        required_evidence_ids:
    * EVID-021
    * EVID-022
        pass_criteria:
    * Network, service, protocol, filesystem, token, and state failures are handled explicitly.
    * Governed mutation fails closed.
    * Safe read-only degradation behaves as declared.
    * No secrets leak and no pending evidence is silently lost.
        failure_effect: Block canary and production-capable certification.
* id: GATE-015
    name: Claude_Code_canary_and_rollback_pass
    gate_type: cutover
    blocking: true
    owner_authority_id: AUTH-012
    task_ids:
    * TASK-022
        required_evidence_ids:
    * EVID-024
    * EVID-025
        pass_criteria:
    * MCP-enforced canary has zero unauthorized allows.
    * No ingestion is lost or duplicated.
    * Rollback restores legacy operational safety.
    * Pending claims and journals are reconciled.
        failure_effect: Block legacy pipeline deletion.
* id: GATE-016
    name: legacy_pipeline_removal_verified
    gate_type: completion
    blocking: true
    owner_authority_id: AUTH-012
    task_ids:
    * TASK-023
        required_evidence_ids:
    * EVID-018
    * EVID-024
    * EVID-025
        pass_criteria:
    * No Claude-specific memory transport or duplicate domain semantics remain.
    * No obsolete hook, installer, Makefile, CI, or test reference remains.
    * Replacement tests cover every removed behavioral assertion.
    * Full local validation passes at the exact candidate revision.
        failure_effect: Block reference certification and governance convergence.
* id: GATE-017
    name: reusable_adapter_scaffolding_valid
    gate_type: completion
    blocking: true
    owner_authority_id: AUTH-004
    task_ids:
    * TASK-024
        required_evidence_ids:
    * EVID-010
    * EVID-023
        pass_criteria:
    * Generator output is deterministic and schema-valid.
    * No Claude-specific assumption appears in generated shared artifacts.
    * Capability declarations generate required test obligations.
    * Implementation documentation passes review.
        failure_effect: Block second-peer reuse certification.
* id: GATE-018
    name: second_peer_reuse_certified
    gate_type: adapter_conformance
    blocking: true
    owner_authority_id: AUTH-013
    task_ids:
    * TASK-025
    * TASK-026
        required_evidence_ids:
    * EVID-026
        pass_criteria:
    * Selected peer uses canonical schemas and shared runtime.
    * No foundational schema or runtime modification is required.
    * Every declared capability passes conformance.
    * Supported common E2E scenarios pass.
        failure_effect: Platform may be accepted only as a Claude reference implementation, not a reusable peer foundation.
* id: GATE-019
    name: architecture_fitness_and_CI_valid
    gate_type: regression
    blocking: true
    owner_authority_id: AUTH-010
    task_ids:
    * TASK-027
        required_evidence_ids:
    * EVID-023
    * EVID-027
        pass_criteria:
    * Architecture fitness functions detect prohibited regressions.
    * Real-CLI, E2E, fault, schema, and adapter jobs are configured.
    * Local execution passes at the exact candidate revision.
    * CI configuration contains no secret or environment-specific assumption.
        failure_effect: Block local commit stack and remote promotion.
* id: GATE-020
    name: architecture_and_protected_governance_converged
    gate_type: governance
    blocking: true
    owner_authority_id: AUTH-002
    task_ids:
    * TASK-028
    * TASK-029
        required_evidence_ids:
    * EVID-005
    * EVID-029
        pass_criteria:
    * ADR disposition matches the accepted decision.
    * Root governance preserves deterministic enforcement invariants.
    * Required deletion markers and reviews are present.
    * Architecture documentation matches implementation and topology.
        failure_effect: Block repository integration and remote promotion.
* id: GATE-021
    name: repository_integration_and_reference_cleanup_valid
    gate_type: regression
    blocking: true
    owner_authority_id: AUTH-002
    task_ids:
    * TASK-030
        required_evidence_ids:
    * EVID-003
    * EVID-023
    * EVID-027
        pass_criteria:
    * Registry, validators, setup, docs, commands, and rules reference the canonical foundation.
    * Claude Code no longer relies on an adapter exemption.
    * No dangling legacy reference remains.
    * Full repository validation passes.
        failure_effect: Block local commit stack and remote promotion.
* id: GATE-022
    name: local_candidate_ready_for_push_approval
    gate_type: promotion
    blocking: true
    owner_authority_id: AUTH-011
    task_ids:
    * TASK-031
        required_evidence_ids:
    * EVID-027
    * EVID-029
        pass_criteria:
    * Local commit stack is reviewable and free of unrelated work.
    * All required local validation passes at the final candidate SHA.
    * Protected-root requirements are satisfied.
    * Exact push approval packet is complete.
        failure_effect: Block remote push.
* id: GATE-023
    name: remote_branch_and_CI_verified
    gate_type: remote_validation
    blocking: true
    owner_authority_id: AUTH-011
    task_ids:
    * TASK-032
        required_evidence_ids:
    * EVID-028
        pass_criteria:
    * Remote branch points to the exact approved SHA.
    * Required CI checks pass and are independently observed.
    * No pull request was created without exact approval.
    * Pull-request approval packet is complete.
        failure_effect: Block pull-request creation and merge preparation.
* id: GATE-024
    name: pull_request_review_and_merge_state_complete
    gate_type: remote_promotion
    blocking: true
    owner_authority_id: AUTH-011
    task_ids:
    * TASK-033
        required_evidence_ids:
    * EVID-028
    * EVID-029
        pass_criteria:
    * Pull request head and base match the approved candidate.
    * Required CI, CODEOWNERS, security, and architecture reviews are complete.
    * Merge occurs only when exactly authorized.
    * Merge commit or unmerged final state is independently observed.
        failure_effect: Block convergence closeout or record campaign as not converged.
* id: GATE-025
    name: controller_handoff_and_terminal_verdict_request_complete
    gate_type: convergence
    blocking: true
    owner_authority_id: AUTH-001
    task_ids:
    * TASK-034
        required_evidence_ids:
    * EVID-030
        pass_criteria:
    * Handoff receipt is schema-valid and evidence-complete.
    * Final revisions and remote events are independently supported.
    * Remaining decisions, Unknowns, risks, waivers, and rollback state are explicit.
    * Controller recommends but does not declare a terminal verdict.
        failure_effect: Terminal verdict remains INCONCLUSIVE.

scheduler:
objective_order:
- resolve_program_owner_and_admission_authority
- lock_repository_and_legacy_current_state
- lock_canonical_contracts_and_external_interfaces
- complete_shared_runtime_and_security_foundation
- prove_claim_enforcement_and_durable_ingestion
- certify_Claude_Code_reference_adapter
- complete_shadow_canary_and_rollback
- remove_legacy_pipeline_only_after_cutover_proof
- prove_second_peer_reuse
- converge_governance_CI_and_documentation
- prepare_exact_remote_approval_packets
- close_out_with_complete_evidence
one_writer_per_repository: true
non_mutating_cross_repository_tasks_allowed: true
mutating_cross_repository_tasks_forbidden: true
initial_max_workers: 1
maximum_workers_without_new_authorization: 2
concurrency_increase_requirements:
- isolated_workspaces
- non_overlapping_writable_scopes
- valid_claims
- current_leases
- passing_integration_boundary
- independent_verification_capacity
blocked_task_behavior: >-
Block only the affected task or dependency subgraph, continue unrelated
ready read-only or reversible work, and include the blocker in every
subsequent program digest.
repository_write_policy: >-
Only one active writer may mutate Quantum-L9/Cursor-Governance at a time.
Read-only evidence collection and isolated ephemeral tests may run in
parallel when they do not share mutable state.

retry_policy:
max_attempts: 2
retryable:
- worker_timeout
- worker_crash
- temporary_file_lock
- transient_test_infrastructure
- temporary_remote_observation_failure
- temporary_adapter_failure
- temporary_memory_projection_failure
- rate_limited_read_only_probe
- ephemeral_test_service_startup_failure
non_retryable:
- deterministic_test_failure
- architecture_invariant_violation
- scope_violation
- secret_access_attempt
- identity_mismatch
- stale_base_revision
- stale_or_revoked_claim
- unsupported_CLI_contract
- unsupported_protocol_version
- semantic_unknown
- approval_mismatch
- program_lock_failure
- forbidden_command
- protected_root_authority_failure
- unexplained_shadow_divergence
- unauthorized_remote_mutation
preserve_every_attempt: true
require_new_source_contract_when:
- base_revision_changes
- writable_scope_changes
- accepted_decision_changes
- validation_obligation_changes
- authorization_expiration_changes
- adapter_contract_version_changes
- CLI_compatibility_range_changes
- selected_second_peer_changes
- cutover_sequence_changes
unknown_external_side_effect_rule: >-
Never replay an external operation whose outcome is unknown unless an
idempotency key or independent reconciliation proves replay safety.

observability:
program_progress_fields:
- program
- current_wave
- current_task
- controller_status
- repository_revisions
- evidence_added
- commands_executed
- validation_result
- decisions_resolved
- unknowns_remaining
- risks_changed
- next_ready_task
- approval_required
- pipeline_mode
- adapter_id
- CLI_version
- protocol_version
- session_id
- request_id
- claim_id
- hydration_id
- candidate_revision
- scope_digest
- pending_ingest_count
- oldest_pending_ingest_age
- shadow_equivalence_status
- canary_status
- rollback_readiness
required_structured_events:
- memory_CLI_invocation
- memory_hydration_result
- memory_conflict_result
- memory_claim_acquire_result
- memory_claim_verify_result
- memory_claim_release_result
- governed_operation_decision
- identity_mismatch
- degraded_mode_transition
- ingest_queued
- ingest_acknowledged
- ingest_replayed
- shadow_comparison
- canary_transition
- rollback_transition
- break_glass_activation
required_metrics:
- memory_CLI_invocations_total
- memory_CLI_latency_seconds
- hydration_failures_total
- conflict_results_total
- claim_denials_total
- identity_mismatch_total
- governed_actions_denied_total
- break_glass_total
- ingest_queued_total
- ingest_retry_total
- ingest_oldest_pending_seconds
- schema_incompatibility_total
- shadow_equivalence_rate
- unauthorized_allow_total
evidence_policy:
append_only: true
bind_exact_revision: true
bind_collection_method: true
bind_environment: true
bind_producer_and_timestamp: true
distinguish_fact_intent_inference_recommendation_unknown: true
prohibit_secret_values: true
prohibit_hydrated_memory_content_in_operational_logs: true

cutover_and_rollback:
cutover_authority: exact_human_approval_required
preconditions:
- accepted_blueprint
- valid_program_lock
- exact_candidate_revision
- independent_verification
- all_predecessor_gates_pass
- current_rollback_proof
- zero_unauthorized_allows
- zero_unexplained_unsafe_shadow_divergence
- durable_ingestion_recovery_pass
- identity_spoofing_tests_pass
- reference_adapter_canary_pass
- rollback_rehearsal_pass
- second_peer_reuse_gate_pass_or_explicitly_recorded_non_convergence
migration_modes:
- legacy
- mcp_shadow
- mcp_enforced_canary
- mcp_enforced
cutover_sequence:
- preserve_legacy_authority
- enable_non_authoritative_MCP_shadow
- prove_fixture_and_runtime_equivalence
- enable_controlled_MCP_enforced_canary
- rehearse_operational_rollback
- obtain_exact_legacy_removal_approval
- remove_legacy_pipeline
- rerun_full_conformance_and_repository_validation
- activate_canonical_MCP_enforced_mode
rollback_rules:
- never_move_a_public_tag
- never_replace_an_existing_published_package_version
- preserve_failed_release_and_deployment_evidence
- use_new_version_when_corrective_source_changes_are_required
- use_forward_recovery_when_restore_would_discard_valid_transactions
- restore_operational_safety_not_only_source_files
- preserve_and_replay_pending_ingestion
- revoke_or_reconcile_incompatible_active_claims
- record_every_rollback_attempt_and_result
exact_campaign_rollbacks:
- >-
Before legacy deletion, switch pipeline mode to legacy, restore prior
settings and hook wiring, preserve all shadow and canary evidence, and
reconcile active claims and pending ingestion.
- >-
After legacy deletion but before merge, revert the deletion and cutover
commits, restore legacy files from Git, restore previous configuration, and
replay retained journal entries.
- >-
After merge, use a reviewed forward-recovery pull request or approved
revert commit; do not rewrite public history or silently discard valid
memory events.
- >-
For CLI incompatibility, pin the last verified compatible CLI release and
disable unsupported adapter capabilities until a new accepted contract is
available.
- >-
For identity-binding failure, disable governed mutation immediately,
revoke affected credentials and claims, preserve audit evidence, and
require security authority review before reactivation.
- >-
For second-peer certification failure, remove the unaccepted peer adapter
and retain Claude Code as the reference implementation without claiming
platform-wide convergence.

closeout:
required_handoff_content:
- campaign_source_digest
- blueprint_digest
- program_lock_digest
- governance_revision
- final_target_revisions
- final_shared_runtime_revision
- final_Claude_Code_adapter_revision
- selected_second_peer_and_conformance_state
- CLI_version_and_protocol_compatibility
- memory_service_identity_and_capability_evidence
- pull_requests_and_merge_commits
- tags_releases_publications_and_deployments
- workflow_runs_and_artifact_hashes
- task_attempt_and_verification_receipts
- completed_failed_cancelled_and_superseded_tasks
- gate_evaluations
- accepted_decisions
- remaining_unknowns_risks_and_waivers
- shadow_equivalence_results
- canary_results
- rollback_rehearsal_results
- pending_ingestion_state
- active_or_revoked_claim_state
- architecture_fitness_results
- protected_root_review_evidence
- rollback_state
- recommended_terminal_verdict
convergence_requirements:
- shared_CLI_is_the_only_adapter_memory_transport
- no_Claude_specific_memory_domain_implementation_remains
- deterministic_governed_boundary_enforcement_is_preserved
- identity_is_server_bound_and_registry_consistent
- durable_idempotent_ingestion_is_proven
- reference_adapter_conformance_passes
- second_peer_reuse_is_proven_without_foundational_changes
- architecture_fitness_functions_are_active
- all_remote_events_are_supported_by_observed_evidence
controller_may_declare_terminal_verdict: false
terminal_verdict_authority_id: AUTH-001