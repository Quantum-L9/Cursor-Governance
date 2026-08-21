---
name: Autonomy first-class
status: superseded
built: true
overview: "Elevate the autonomy family to a registered first-class subordinate primitive (MANIFEST + law + fail-closed validators) without promoting WIP Phase-0 PE rail or overturning Program Execution ownership."
todos:
  - id: built-marker
    content: Marked built after execution; session-start audit should skip
    status: cancelled
  - id: todo-01-baseline-preflight
    content: "PE W0: lock immutable baseline (full SHA) + capability probes; Program Lock bind; stop_and_replan on drift"
    status: completed
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: todo-02-mutate
    content: "PE claim→render→worker under Program lease + @autonomy packet: contracts home, law/discovery, validator, protected_paths"
    status: cancelled
    phase: execute
    depends_on: [todo-01-baseline-preflight]
    side_effect_ref: SE-todo-02
    evidence_property_refs: [SP-02]
  - id: todo-03-prove
    content: "PE verify: autonomy-contracts-validate + autonomy-validate + program-execution-conformance + make pr-check"
    status: cancelled
    phase: validate
    depends_on: [todo-02-mutate]
    evidence_property_refs: [SP-01, SP-02, SP-03]
  - id: todo-04-converge
    content: "PE handoff + max @autonomy join/PR-poll; L4 authorize-release → make pr → remediate → merge per plan-Build stack"
    status: cancelled
    phase: converge
    depends_on: [todo-03-prove]
    evidence_property_refs: [SP-03]
isProject: false
---
# PLAN: Autonomy first-class

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: `executable`)
> **Execute:** through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease.
> **Rename:** `autonomy_first_class_2796c877.plan.md` (this file).
> **Law:** baseline locked; envelope respected; PE Controller authoritative; autonomy `owns_program_state: false`.

## Execute via @environment/program-execution + autonomy (required)

```text
this .plan.md
        │ project
        ▼
@environment/program-execution
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act? — owns_program_state: false
        │
        ▼
PE adapter (cursor-foreground)
```

### Campaign authorization packet

```yaml
packet_id: autonomy-2026-08-12-1
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: .cursor/plans/autonomy_first_class_2796c877.plan.md
plan_id: plan.governance.autonomy_first_class.v1
program_execution:
  root: environment/program-execution
  program_id: pes-autonomy-first-class
  adapter_id: cursor-foreground
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [feat/autonomy-first-class]
allowed_inside_packet:
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch
  - inspect_ci_and_comments
forbidden_inside_packet:
  - widen_blueprint_or_task_card_ceiling
  - mutate_without_program_lease
  - outlive_program_lease
  - merge_outside_l4_plan_build_stack
  - force_push
  - admin_merge
  - expand_scope
  - commit_secrets
  - weaken_tests_for_green
created_by: "/autonomy+program-execution"
```

### Phase-0 action table

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| todo-01-baseline-preflight | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.task001` | `work` | `cursor-foreground` |
| todo-02-mutate | TASK-002 | W1 | [todo-01-baseline-preflight] | true | `path:environment/contracts/**` | `mutate` | `pes.w1.task002` | `work` | `cursor-foreground` |
| todo-03-prove | TASK-003 | W1 | [todo-02-mutate] | false | `evidence:plan.governance.autonomy_first_class.v1` | `validate` | `pes.w1.task003` | `work` | `cursor-foreground` |
| todo-04-converge | TASK-004 | W2 | [todo-03-prove] | true | `branch:feat/autonomy-first-class` | `converge` | `pes.w2.task004` | `work` | `github-remote-actions` |
| poll-pr-N | — | W2 | [todo-04-converge] | true | `pr:<n>` | `pr:<n>` | `pes.w2.poll.pr<n>` | `poll` | background |

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.governance.autonomy_first_class.v1` |
| name | Autonomy first-class |
| overview | Elevate autonomy family to first-class subordinate primitive |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` |
| owner | platform |
| created_at | `2026-08-12` |
| updated_at | `2026-08-12` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | environment/contracts/execution/MANIFEST.yaml + PEER_EXECUTION.md |
| plan_class | `integration_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via PE + subordinate @autonomy; register family without relocating runtimes |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-12T16:47:10Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `~/.cursor-governance` |
| branch | `feat/autonomy-first-class` |
| commit_sha | `e2b39654fb5b7480a653ad7bc1b4c90fb8d280bf` |
| dirty | `false` |
| overlap_policy | `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make the autonomy family (root control plane, ops L4/surface gates, Claude scheduler) officially elevated as a registered first-class subordinate primitive—discoverable via contracts MANIFEST, cited in CANONICAL_LAW, and fail-closed via validators—without overturning PE ownership of program state.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline branch is feat/autonomy-first-class stacked work | `repository_state` | `git branch --show-current` | true |
| SP-02 | Autonomy contracts MANIFEST registers four SSOTs; validator PASS; owns_program_state false | `structural` | `make autonomy-contracts-validate` → PASS | true |
| SP-03 | Changed-files quality gate PASS | `quality_gate` | `make pr-check` → PASS | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.governance.autonomy_first_class.v1` |
| blocking | `true` |
| baseline_verified | `true` |
| drift_detected | `false` |

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | on feat/autonomy-first-class | true |
| CP-02 | `command_available` | `python3` | present | true |
| CP-03 | `filesystem_write` | envelope paths writable | write succeed | true |

## Execution envelope

### Filesystem

- **write_allow:** `environment/contracts/autonomy/**`, `environment/contracts/execution/README.md`, `CANONICAL_LAW.md`, `README.md`, `ORG_INVARIANTS.yaml`, `Makefile`, `ops/scripts/validate_autonomy_contracts.py`, `tests/ops/autonomy/test_autonomy_contracts_validate.py`, `commands/autonomy.md`, `skills/l9-bounded-autonomy/SKILL.md`, `environment/agents/PEER_EXECUTION.md`, `docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md`, `.cursor/plans/autonomy_first_class_2796c877.plan.md`
- **write_deny:** `autonomy/**` (runtime relocate), `environment/agents/adapters/claude-code/autonomy/**` (rewrite scheduler), `WIP/**`, secrets, unrelated trees
- **delete_allow:** none required

### Commands

- **allow:** `python3 ops/scripts/validate_autonomy_contracts.py`, `make autonomy-contracts-validate`, `make autonomy-validate`, `make program-execution-conformance`, `make pr-check`, `make pr`, `git commit`, `ops/autonomy/l4_local.py *`
- **deny:** force-push, hard-reset, secret exfil, Phase-0 WIP promotion

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | GitHub via `gh` after L4 release_authorized |

### Autonomous merge

`autonomous_merge:` `false` in packet. Merge for this plan only after green+mergeable on L4 plan-Build stack.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| todo-01-baseline-preflight | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| todo-02-mutate | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | git restore scoped paths | false |
| todo-03-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |
| todo-04-converge | `network_write` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| todo-02-mutate | autonomy family registry | `control_plane` | PEER_EXECUTION + surface_profile | relocating runtimes; PE owns_program_state flip; Phase-0 WIP promote |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.governance.autonomy_first_class.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | validator FAIL; envelope breach; PE authority regression |

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | scoped to write_allow |
| data | `none` | |
| external_state | `manual_recovery` | close PR if opened |
| local_state | `git_restore_scoped_paths` | |

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `low` |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `1` |
| external_systems_touched | `1` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Execution DAG

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| todo-01-baseline-preflight | agent | assurance | [] | baseline_receipt |
| todo-02-mutate | agent | control_plane | [todo-01-baseline-preflight] | contracts + law + validator |
| todo-03-prove | agent | assurance | [todo-02-mutate] | validation_evidence |
| todo-04-converge | agent | control_plane | [todo-03-prove] | PR + merge |

**Critical path:** `todo-01` → `todo-02` → `todo-03` → `todo-04`

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | branch check | `git branch --show-current` | `feat/autonomy-first-class` | `pass` |
| EV-SP-02 | SP-02 | `structural_evidence` | contracts validate | `make autonomy-contracts-validate` | PASS | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

- Disconfirm: agents treat first-class as peer-to-PE → mitigate with `owns_program_state: false` in MANIFEST purpose + PEER_EXECUTION cite.
- Blast: law + Makefile + ORG_INVARIANTS; runtime code paths unchanged.

## Convergence

| Field | Value |
|-------|-------|
| status | `in_progress` |
| handoff | L4 release → make pr → l9-pr-remediation → merge |

## Scope

### In

- `environment/contracts/autonomy/` family registry
- Law/discovery pointers
- Fail-closed validator + Makefile wiring
- `environment/contracts/**` protected_paths

### Out

- WIP Phase-0 autonomy rail promotion
- Relocating/rewriting root `autonomy/` or Claude scheduler Python
- Cursor ask-free A4 velocity change
- Overturning PE lease authority
