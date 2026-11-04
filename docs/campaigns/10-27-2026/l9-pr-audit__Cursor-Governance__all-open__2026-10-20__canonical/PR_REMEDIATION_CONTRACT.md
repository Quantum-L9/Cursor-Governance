# PR Remediation Contract

```yaml
role:
  identity: "Claude Code Fable remediation executor"

run_control:
  autoremediate: 0
  default: 0
  law: >
    autoremediate=0 means audit generation stops after producing and validating
    this bundle. No remediation executor is launched automatically. A value of 1
    is valid only when the latest explicit user instruction enabled it for this run.

objective: >
  Apply the remediation defined by the provided audit pack to the affected open
  pull requests in https://github.com/Quantum-L9/Cursor-Governance.

  Fix the validated findings in-place on their existing PR branches.

  Do not expand scope, create new architecture, introduce parallel systems,
  duplicate existing responsibility, or turn bounded fixes into redesign work.

target:
  repository:
    url: "https://github.com/Quantum-L9/Cursor-Governance"
    owner: "Quantum-L9"
    name: "Cursor-Governance"

  PR_scope: "The PRs and work units defined by audit audit.quantum-l9.cursor-governance.open-prs.2026-10-20 for #737, #738, #739, #740, #741, #744, #745, #746, #747, #748, #749, #750, #751, #752, #755 that are still open and whose current source heads satisfy the pack freshness requirements."

audit_pack:
  source: PROVIDED_TO_AGENT
  authority: PRIMARY_REMEDIATION_SPECIFICATION
  audit_id: "audit.quantum-l9.cursor-governance.open-prs.2026-10-20"

  read_order:
    - "00_READ_FIRST.md"
    - "remediation-handoff.json"
    - "PR_REMEDIATION_CONTRACT.md"
    - "audit.json only for evidence IDs required by an active work unit"
    - "change-ledger.json only when deterministic census provenance must be verified"
    - "audit.md only when additional context is required"
    - "MANIFEST.json for bundle integrity when applicable"

  rules:
    - >
      Reference and execute the pack. Do not duplicate its findings, work units,
      evidence, write surfaces, preservation obligations, or closure conditions
      into a new remediation plan.
    - >
      Treat remediation-handoff.json as the machine-readable work-unit authority.
    - >
      Treat PR_REMEDIATION_CONTRACT.md as the execution contract.
    - >
      Use audit.json only for cited proof required to execute or validate a work
      unit.
    - >
      Do not re-audit the repository from scratch unless a specific unresolved
      condition requires bounded read-only inspection.

authority_order:
  - latest_explicit_user_instruction
  - provided_audit_and_remediation_pack
  - repository_local_governance_and_scoped_instructions
  - authoritative_repository_invariants_contracts_and_owners
  - current_repository_state
  - executable_validation_evidence
  - UNKNOWN

scope:
  authorized:
    - fix_pack_defined_mutation_eligible_findings
    - modify_existing_open_PR_branches_covered_by_the_pack
    - use_pack_defined_write_surfaces
    - perform_pack_required_validation
    - make_required_commits_to_the_existing_PR_branches
    - publish_validated_fixes_to_the_existing_PR_branches_through_SSOT_make_pr

  prohibited:
    - unrelated_refactors
    - speculative_cleanup
    - architecture_expansion
    - new_architecture
    - parallel_systems
    - duplicate_control_planes
    - duplicate_sources_of_truth
    - replacement_subsystems_when_the_existing_owner_can_be_fixed
    - unrelated_feature_work
    - unrelated_dependency_changes
    - changes_outside_pack_authorized_write_surfaces_without_explicit_new_authority

scope_law: >
  Every source mutation must be justified by a mutation-eligible work unit in
  the supplied pack and must remain inside that work unit's authorized write
  surfaces.

  If a correct fix appears to require an unlisted path, do not silently widen
  scope. Classify the work unit as SCOPE_EXTENSION_REQUIRED and preserve the
  evidence.

freshness_gate:
  before_mutation:
    MUST:
      - independently_resolve_each_pack_target_PR_current_source_head
      - verify_the_PR_is_still_open
      - compare_current_source_head_to_the_pack_audited_source_head

  outcomes:
    exact_match_and_open: CONTINUE

    head_changed:
      status: STALE_AUDIT
      action: >
        Do not mutate that PR from stale evidence.

    PR_not_open:
      status: OUT_OF_CURRENT_SCOPE
      action: >
        Do not mutate that PR unless the pack or a stronger current instruction
        explicitly authorizes work on its current state.

    source_head_unprovable:
      status: FRESHNESS_UNPROVEN
      action: >
        Do not mutate that PR.

  identity_rule: >
    Preserve the distinction between PR source-head identity and any
    tested_revision_sha recorded by the pack.

    Never relabel historical validation as having run on a newer revision.

execution:
  work_unit_source: "remediation-handoff.json"

  selection:
    execute_only_when:
      mutation_eligible: true
      freshness_gate: CONTINUE

    non_mutating_classes: >
      Preserve pack classifications such as validation-only, CI-owned,
      environment-owned, external-owned, human-owned, or UNKNOWN unless the pack
      explicitly grants code mutation authority.

  order:
    rule: >
      Follow the pack's dependency and remediation order.

      Resolve root causes before dependent symptoms.

  for_each_work_unit:
    MUST:
      - bind_to_the_exact_current_PR_head
      - read_the_work_unit_and_only_its_needed_evidence
      - inspect_authoritative_and_coupled_surfaces_named_by_the_pack
      - understand_the_behavioral_closure_condition_before_editing
      - modify_only_authorized_write_surfaces
      - preserve_all_pack_defined_preservation_obligations
      - repair_the_root_cause
      - keep_the_existing_architectural_owner
      - avoid_new_abstractions_unless_the_existing_repository_already_requires_them
      - run_the_pack_defined_closing_validation
      - verify_the_behavioral_closure_condition
      - reread_the_final_changed_surface
      - keep_the_fix_minimal_and_complete

implementation_constraints:
  MUST:
    - reuse_existing_repository_architecture
    - reuse_existing_owners
    - reuse_existing_control_planes
    - reuse_existing_contracts
    - reuse_existing_validation_paths
    - preserve_existing_public_behavior_except_where_the_finding_requires_change
    - preserve_fail_closed_or_fail_open_semantics_defined_by_repository_authority
    - preserve_generators_and_sources_of_truth
    - preserve_pack_defined_invariants

  MUST_NOT:
    - create_a_new_framework_to_fix_a_local_defect
    - introduce_a_second_path_beside_the_existing_path
    - introduce_a_second_owner_for_the_same_responsibility
    - add_compatibility_layers_without_pack_or_repository_authority
    - move_responsibility_between_layers_without_requirement
    - redesign_neighboring_components
    - generalize_beyond_the_current_finding
    - replace_a_simple_fix_with_a_new_subsystem
    - weaken_tests_or_gates_to_make_validation_green
    - add_skips_ignores_or_suppressions_to_hide_the_defect
    - bypass_authoritative_generators
    - edit_generated_artifacts_as_competing_authority

minimal_change_rule: >
  Choose the smallest implementation that completely satisfies the pack's
  behavioral closure condition while preserving the existing architecture.

  Minimal does not mean partial.

  Do not leave the root cause reachable through another path merely to reduce
  the diff.

convergence_addenda:
  primary_objective: RESOLVE_AUDIT_FINDINGS

  ci_failures:
    required: true
    rule: >
      In addition to the audit work units, inspect current CI for every affected
      PR after each publication. Diagnose and repair every codebase-owned CI
      failure that is reachable within authorized scope. Do not weaken gates,
      skip tests, suppress scanners, or edit CI-owned infrastructure merely to
      obtain green. Re-run or poll required checks on the repaired head. A
      truly external CI_PIPELINE, ENVIRONMENT, or HUMAN blocker must be
      preserved explicitly in the final result rather than silently ignored.

  code_review_threads:
    required: true
    rule: >
      In addition to the audit work units, inspect every unresolved current code
      review thread on each affected PR regardless of author. Validate each
      comment against current code. Fix validated code findings, reply with the
      disposition for every thread, resolve the thread when appropriate, and
      re-query after every publication because new threads may appear on new
      lines. Completion requires zero unresolved review threads unless a
      specific external blocker is reported.

  merge:
    authorized: false
    rule: >
      Converge the affected PRs to audit-closed, CI-resolved, review-resolved,
      merge-ready state, then stop. Do not merge.

validation:
  authority:
    - pack_defined_closing_validation
    - pack_defined_preservation_validation
    - repository_native_validation_required_for_changed_surfaces

  execution:
    MUST:
      - execute_entries_marked_COMMAND_as_commands
      - observe_entries_marked_CHECK_through_the_named_check_surface
      - treat_entries_marked_MANUAL_as_non_shell_verification
      - rerun_required_validation_after_mutation
      - preserve_exact_command_results_and_exit_codes
      - verify_preservation_obligations_after_the_fix
      - verify_required_CI_on_the_repaired_PR_head_when_available

  result_values:
    - PASS
    - FAIL
    - BLOCKED
    - NOT_EXECUTED
    - UNKNOWN

  hard_rules:
    - "NOT_EXECUTED is not PASS."
    - "A changed file is not proof of closure."
    - "A green unrelated check is not proof of closure."
    - "Historical validation is not validation of the repaired head."
    - "Do not weaken the discriminator that originally exposed the defect."

failure_handling:
  validation_failure:
    action: >
      Diagnose within the current authorized work-unit scope, correct the
      root cause if still within that scope, and rerun the discriminating
      validation.

  scope_extension_required:
    action: >
      Stop only the affected work unit, preserve completed independent work,
      and report the exact additional path and direct-coupling evidence.

  stale_audit:
    action: >
      Do not mutate the affected PR.

  unrelated_pre_existing_failure:
    action: >
      If it is a current CI failure on an affected PR, triage it under the CI
      convergence addendum: repair codebase-owned root causes within authorized
      scope or report the exact external owner/blocker. For unrelated non-CI
      defects outside the audit objective, preserve evidence and do not absorb
      them into remediation.

publication:
  objective: >
    Land completed validated fixes onto the existing affected PR branches so the
    open PRs contain the repaired implementation while preserving PR identity.

  command: "make pr"
  makefile_authority: SSOT_MAKEFILE
  target_repository_makefile_authorized: false

  resolution_rule: >
    Resolve the canonical SSOT Makefile publication surface and its existing
    make pr invocation contract from current operator, session, or governance
    authority. Do not infer publication authority from the target repository.

  MUST:
    - invoke_make_pr_from_the_canonical_SSOT_Makefile_surface
    - keep_changes_on_the_existing_affected_PR_branches
    - preserve_PR_identity
    - publish_only_after_required_local_validation_for_the_work_unit
    - pass_target_repository_and_branch_context_only_through_the_existing_SSOT_interface
    - verify_the_remote_PR_head_after_publication
    - observe_required_checks_on_the_published_repaired_head

  MUST_NOT:
    - invoke_make_pr_from_the_target_repository_Makefile
    - substitute_raw_gh_pr_for_the_SSOT_publication_surface
    - create_parallel_replacement_PRs_for_the_same_pack_work
    - create_parallel_feature_branches_as_a_substitute_for_updating_the_existing_PR
    - force_push_unless_repository_governance_explicitly_requires_and_authorizes_it
    - broaden_the_PR_objective

  unresolved_SSOT_path:
    status: PUBLICATION_BLOCKED
    action: >
      Do not substitute another publication path. Preserve the validated work and
      report the missing SSOT Makefile location or invocation contract required
      to run make pr.

  merge: false
  merge_authority: FORBIDDEN_BY_THIS_CONTRACT

convergence:
  required: true

  sequence:
    - READ_PACK_ENTRYPOINT
    - VERIFY_PACK_INTEGRITY_WHEN_REQUIRED
    - BIND_TARGET_REPOSITORY
    - LOAD_REMEDIATION_HANDOFF
    - RESOLVE_PACK_TARGET_PRS
    - VERIFY_OPEN_STATE_AND_SOURCE_HEAD_FRESHNESS
    - SELECT_MUTATION_ELIGIBLE_WORK_UNITS
    - RESOLVE_DEPENDENCY_ORDER
    - EXECUTE_ROOT_CAUSE_FIXES
    - RUN_WORK_UNIT_CLOSING_VALIDATION
    - VERIFY_PRESERVATION_OBLIGATIONS
    - RUN_REQUIRED_REPOSITORY_NATIVE_VALIDATION
    - VERIFY_NO_SCOPE_EXPANSION
    - VERIFY_NO_NEW_OR_PARALLEL_ARCHITECTURE
    - COMMIT_VALIDATED_FIXES_TO_EXISTING_PR_BRANCHES
    - RESOLVE_SSOT_MAKEFILE_PUBLICATION_SURFACE
    - PUBLISH_WITH_SSOT_MAKE_PR
    - VERIFY_REMOTE_PR_HEADS
    - OBSERVE_REQUIRED_POST_PUBLICATION_CHECKS
    - RESOLVE_CURRENT_CODEBASE_OWNED_CI_FAILURES
    - REQUERY_AND_RESOLVE_ALL_CURRENT_CODE_REVIEW_THREADS
    - REPUBLISH_IF_REQUIRED_WITH_SSOT_MAKE_PR
    - VERIFY_REQUIRED_CHECKS_ON_FINAL_HEAD
    - VERIFY_ZERO_UNRESOLVED_REVIEW_THREADS_OR_EXPLICIT_EXTERNAL_BLOCKER
    - RECHECK_ALL_MUTATION_ELIGIBLE_FINDINGS
    - STOP_BEFORE_MERGE
    - EMIT_FINAL_REMEDIATION_RESULT

  terminal_rule: >
    Complete only when every freshness-valid, mutation-eligible finding in the
    supplied pack has been repaired at its root cause, all pack-defined closure
    and preservation conditions have been satisfied, required validation has
    been executed against the repaired state, the fixes have been published to
    the existing affected open PR branches through the canonical SSOT Makefile
    make pr path, and no scope expansion, new architecture, parallel system,
    duplicate authority, or unrelated change has been introduced; every
    codebase-owned CI failure on the affected PRs has been resolved, all current
    code review threads have been dispositioned and resolved unless an explicit
    external blocker remains, and the executor stops before merge (MERGE=False).

deliverables:
  MUST_include:
    - target_repository
    - affected_PRs
    - initial_source_head_per_PR
    - final_source_head_per_PR
    - work_units_closed
    - work_units_blocked
    - files_changed_per_work_unit
    - commits_created
    - publication_result_per_PR
    - behavioral_closure_result_per_work_unit
    - preservation_obligation_results
    - validation_results
    - post_publication_check_results
    - final_CI_failure_disposition_per_PR
    - final_unresolved_review_thread_count_per_PR
    - merge_attempted_false
    - scope_extension_required_items
    - stale_audit_items
    - residual_UNKNOWNs
    - final_remediation_status

final_remediation_status_values:
  - COMPLETE
  - COMPLETE_WITH_EXTERNAL_BLOCKERS
  - PARTIALLY_REMEDIATED
  - STALE_AUDIT
  - BLOCKED
  - UNKNOWN

stop_conditions:
  - stop_if_the_pack_cannot_be_read
  - stop_affected_PR_if_its_current_source_head_does_not_match_the_audited_binding
  - stop_affected_PR_if_its_source_head_cannot_be_proven
  - do_not_mutate_a_PR_that_is_no_longer_open_without_stronger_authority
  - do_not_mutate_work_units_without_mutation_eligible_true
  - do_not_edit_outside_pack_authorized_write_surfaces
  - do_not_expand_scope
  - do_not_create_new_architecture
  - do_not_create_parallel_systems
  - do_not_create_duplicate_authority
  - do_not_reaudit_the_entire_repository_without_specific_need
  - do_not_weaken_tests_or_gates
  - do_not_fabricate_validation_or_closure
  - do_not_claim_historical_validation_ran_on_the_repaired_head
  - do_not_publish_without_resolving_the_canonical_SSOT_Makefile_make_pr_surface
  - do_not_merge
```
