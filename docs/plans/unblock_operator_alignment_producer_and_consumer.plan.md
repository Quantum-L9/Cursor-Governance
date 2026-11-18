---
name: "Unblock operator alignment producer and consumer"
overview: "Clear the producer-dependent campaign blockers with a successor operator-scoped source contract, a compiler adapter, and a fail-closed consumer binding. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 checked_record_count=366 conflicts=0 policy_version=memory-phase-lock/v2. Route depth is deep and omit_gates is empty."
todos:
  - id: T1
    content: "Add a successor compiler-contract artifact that names an operator-scoped source class distinct from the global canonical registry. Do not change the admitted l9.compiler/generic@1 inputs."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Implement only the compiler adapter the successor contract names, with a negative test that strategy YAML is not a canonical source."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Extend the existing fail-closed consumer in place. Record the producer receipt bytes only after T2 emits them. Keep the receipt set empty until those exact bytes exist."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "Allow an opt-in operator view to be cited by CTO, Architect, and Planner after the consumer verifies the receipt. Do not set activation.default to true and do not edit mode contracts or child prompts."
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "Add tests that keep Coding Agent confidentiality and Meta Planner as explicit blocked results. Do not add a mode and do not hide strategy/ from the authority checkout."
    status: pending
    phase: execute
    depends_on: [T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Unblock operator alignment producer and consumer

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `unblock_operator_alignment_producer_and_consumer_285c01a4.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| name | Unblock operator alignment producer and consumer |
| overview | Clear the producer-dependent campaign blockers with a successor operator-scoped source contract, a compiler adapter, and a fail-closed consumer binding. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 checked_record_count=366 conflicts=0 policy_version=memory-phase-lock/v2. Route depth is deep and omit_gates is empty. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1, U2 |
| is_project | `false` |
| owner | repository owner |
| created_at | 2026-11-18T01:12:21+00:00 |
| updated_at | 2026-11-18T01:12:21+00:00 |
| depth | `deep` |
| estimate | two implementation sessions after Build |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-18T01:12:21+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| branch | `feat/pr-review-permission` |
| commit_sha | `d23fd61708c197cbddd09f37870751a99dd53d17` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Clear the producer-dependent campaign blockers with a successor operator-scoped source contract, a compiler adapter, and a fail-closed consumer binding. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 checked_record_count=366 conflicts=0 policy_version=memory-phase-lock/v2. Route depth is deep and omit_gates is empty.

### Scope in

- Successor operator-scoped compiler contract in Quantum-L9/.github
- Smallest compiler adapter and tests in l9-semantic-compiler-engine
- Fail-closed consumer extension in Cursor-Governance ops/autonomy/operator_alignment.py and its tests
- Opt-in load of one verified operator view without changing activation defaults

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: the compiler emits an operator-scoped receipt for strategy YAML and rejects that YAML as a global canonical source | `quality_gate` | V1: `python3 -m pytest tests/test_operator_source_projection.py` → operator-scoped receipt is emitted and the same YAML is rejected as a global canonical source | `true` |
| SP-02 | V2: the Cursor consumer accepts only that frozen receipt and still rejects a missing, forged, or mismatched view | `quality_gate` | V2: `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py` → missing, forged, and mismatched views are rejected and the frozen receipt is accepted | `true` |
| SP-03 | V3: the five sealed YAML digests stay equal to the approved subject manifest | `quality_gate` | V3: `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py` → five sealed YAML digests equal the approved subject manifest | `true` |
| SP-04 | V4: Planner and CTO activation defaults stay false while a verified view can be loaded on opt-in | `quality_gate` | V4: `python3 -m pytest tests/ops/autonomy/test_operator_view_opt_in.py` → activation defaults stay false and an opt-in verified view loads | `true` |
| SP-05 | V5: Coding Agent privacy stays BLOCKED_PRIVACY and Meta Planner stays BLOCKED_NO_CONSUMER | `quality_gate` | V5: `python3 -m pytest tests/ops/autonomy/test_alignment_role_blocks.py` → results are BLOCKED_PRIVACY and BLOCKED_NO_CONSUMER | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.unblock_operator_alignment_producer_and_consumer.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| source_ref | `plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git status on /Users/ib-mac/Cursor-Governance` | branch feat/pr-review-permission at d23fd617 is the planning workspace and is not the execution branch | `true` |
| P1 | pre-validation (status `passed`) | `route_plan.py --risk high --evidence partial` | depth deep and omit_gates empty | `true` |
| P2 | pre-validation (status `passed`) | `plan_memory_prefetch.py` | HIT conflicts=0 snapshot_digest 165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 | `true` |
| P3 | pre-validation (status `passed`) | `name .pre-commit-config.yaml as the hook catalog for Cursor-Governance edits` | catalog present in this checkout | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `Quantum-L9/.github successor compiler contract`, `l9-semantic-compiler-engine registry adapter and tests/test_operator_source_projection.py`, `ops/autonomy/operator_alignment.py`, `ops/autonomy/projection_mode.py`, `tests/ops/autonomy/test_operator_alignment.py`, `tests/ops/autonomy/test_operator_view_opt_in.py`, `tests/ops/autonomy/test_alignment_role_blocks.py`, `governance/operator-alignment/STATUS.yaml`
- **write_deny:** `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/test_operator_source_projection.py`, `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py`, `python3 -m pytest tests/ops/autonomy/test_operator_view_opt_in.py`, `python3 -m pytest tests/ops/autonomy/test_alignment_role_blocks.py`, `pre-commit run --config .pre-commit-config.yaml --files ops/autonomy/operator_alignment.py ops/autonomy/projection_mode.py`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `github.com` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- l9.compiler/generic@1 stays admitted and unchanged
- L9-REVISION-001 successor rather than rewrite
- L9-GLOBALIZATION-001 no global law from this plan
- activation.default remains false

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- semantics/compiler_contract successor in the Quantum-L9/.github authority checkout` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- src/l9_semantic_compiler/engine/registry.py tests/test_operator_source_projection.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/operator_alignment.py tests/ops/autonomy/test_operator_alignment.py governance/operator-alignment/STATUS.yaml` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/projection_mode.py tests/ops/autonomy/test_operator_view_opt_in.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/ops/autonomy/test_alignment_role_blocks.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `semantics/compiler_contract successor in the Quantum-L9` | `policy` | `l9.compiler/generic@1 stays admitted and unchanged`, `L9-REVISION-001 successor rather than rewrite`, `L9-GLOBALIZATION-001 no global law from this plan`, `activation.default remains false` | `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts` |
| T2 | `repository root` | `runtime` | `l9.compiler/generic@1 stays admitted and unchanged`, `L9-REVISION-001 successor rather than rewrite`, `L9-GLOBALIZATION-001 no global law from this plan`, `activation.default remains false` | `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts` |
| T3 | `repository root` | `control_plane` | `l9.compiler/generic@1 stays admitted and unchanged`, `L9-REVISION-001 successor rather than rewrite`, `L9-GLOBALIZATION-001 no global law from this plan`, `activation.default remains false` | `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts` |
| T4 | `repository root` | `control_plane` | `l9.compiler/generic@1 stays admitted and unchanged`, `L9-REVISION-001 successor rather than rewrite`, `L9-GLOBALIZATION-001 no global law from this plan`, `activation.default remains false` | `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts` |
| T5 | `tests/ops/autonomy` | `assurance` | `l9.compiler/generic@1 stays admitted and unchanged`, `L9-REVISION-001 successor rather than rewrite`, `L9-GLOBALIZATION-001 no global law from this plan`, `activation.default remains false` | `semantics/canonical_sources.yaml`, `the five sealed strategy YAML files`, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`, `governance/cto-mode/MODE.yaml`, `governance/planner-mode/MODE.yaml`, `commands/lcto.md`, `commands/planner.md`, `child system prompts` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.unblock_operator_alignment_producer_and_consumer.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| source_execution_ref | `plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (The successor artifact is a new id and strategy/ is absent from the global canonical registry) → Stop before any compiler edit; C2 fails (Receipt bytes and a negative canonical-source result) → Leave ADMITTED_PRODUCER_RECEIPTS empty; C3 fails (V1 through V5 pending commands have been run and the five YAML digests still match) → Do not publish and do not claim the five roles active |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the successor artifact, the compiler adapter, and the consumer receipt insertion. The admitted generic contract, the five YAML files, and the #256 admission text stay untouched, so rollback does not restore them. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/test_operator_source_projection.py`
- re-run `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py`
- re-run `python3 -m pytest tests/ops/autonomy/test_operator_view_opt_in.py`
- re-run `python3 -m pytest tests/ops/autonomy/test_alignment_role_blocks.py`
- re-run `pre-commit run --config .pre-commit-config.yaml --files ops/autonomy/operator_alignment.py ops/autonomy/projection_mode.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 5 todo(s) |
| uncertainty | `medium` — 2 unknown(s), 0 blocking |
| blast_radius | `high` — A wrong contract would make operator doctrine look like global semantic law, or a consumer would present an unverified view as admitted. |
| architectural_boundaries_crossed | `Quantum-L9/.github semantic contract`, `l9-semantic-compiler-engine producer`, `Cursor-Governance consumer` |
| external_systems_touched | `GitHub` |
| migration_required | `false` |
| unknown_dependency_count | `2` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.unblock_operator_alignment_producer_and_consumer.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Add a successor compiler-contract artifact that names an operator-scoped source class distinct from the global canonical registry. Do not change the admitted l9.compiler/generic@1 inputs. | Cursor Build agent | `high` | M | `[]` | `semantics/compiler_contract successor in the Quantum-L9/.github authority checkout` |
| T2 | Implement only the compiler adapter the successor contract names, with a negative test that strategy YAML is not a canonical source. | Cursor Build agent | `high` | M | `[T1]` | `src/l9_semantic_compiler/engine/registry.py`, `tests/test_operator_source_projection.py` |
| T3 | Extend the existing fail-closed consumer in place. Record the producer receipt bytes only after T2 emits them. Keep the receipt set empty until those exact bytes exist. | Cursor Build agent | `medium` | M | `[T2]` | `ops/autonomy/operator_alignment.py`, `tests/ops/autonomy/test_operator_alignment.py`, `governance/operator-alignment/STATUS.yaml` |
| T4 | Allow an opt-in operator view to be cited by CTO, Architect, and Planner after the consumer verifies the receipt. Do not set activation.default to true and do not edit mode contracts or child prompts. | Cursor Build agent | `medium` | S | `[T3]` | `ops/autonomy/projection_mode.py`, `tests/ops/autonomy/test_operator_view_opt_in.py` |
| T5 | Add tests that keep Coding Agent confidentiality and Meta Planner as explicit blocked results. Do not add a mode and do not hide strategy/ from the authority checkout. | Cursor Build agent | `low` | S | `[T3]` | `tests/ops/autonomy/test_alignment_role_blocks.py` |

**Critical path:** T1 → T2 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | Successor contract exists and does not globalize strategy/ | compiler adapter |
| M2 | Producer receipt bytes exist | consumer binding and opt-in view |
| M3 | Consumer and opt-in view are verified, with privacy and Meta Planner still blocked | Build publish on a branch from origin/main |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T1 | The successor artifact is a new id and strategy/ is absent from the global canonical registry | Stop before any compiler edit |
| C2 | T2 | Receipt bytes and a negative canonical-source result | Leave ADMITTED_PRODUCER_RECEIPTS empty |
| C3 | T4 | V1 through V5 pending commands have been run and the five YAML digests still match | Do not publish and do not claim the five roles active |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`, `T5`
- **Shared causes:** One missing operator-scoped source class blocks the producer, the consumer, and opt-in Architect, Planner, and CTO alignment views
- **Deletions / consolidations:** Do not add a second consumer module or a second planner; Do not open a companion-rewrite pull request inside this plan

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | No operating-instruction change. Activation defaults stay false. |
| CANONICAL_LAW.md | `n_a` | — | This plan does not amend law. The successor contract is a .github semantic artifact. |
| docs/campaigns/11-17-26/L9_Operator_Alignment_CTO_Campaign_v1.1.0/EVIDENCE_COLLECTION.md | `update` | `T3`, `T5` | Record the receipt coordinates and the two roles that remain blocked after Build. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V0 | regression gate (no SP) | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files ops/autonomy/operator_alignment.py ops/autonomy/projection_mode.py` | .pre-commit-config.yaml hook catalog passes on the consumer files | `not_run` |
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_operator_source_projection.py` | operator-scoped receipt is emitted and the same YAML is rejected as a global canonical source | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py` | missing, forged, and mismatched views are rejected and the frozen receipt is accepted | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/autonomy/test_operator_alignment.py` | five sealed YAML digests equal the approved subject manifest | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/autonomy/test_operator_view_opt_in.py` | activation defaults stay false and an opt-in verified view loads | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `python3 -m pytest tests/ops/autonomy/test_alignment_role_blocks.py` | results are BLOCKED_PRIVACY and BLOCKED_NO_CONSUMER | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does the successor still classify strategy YAML as canonical because the registry is the only input the compiler accepts?
- Does opt-in view loading turn Planner or CTO on without an explicit mode request?
- Does a consumer test pass by parsing a hand-written JSON preview instead of producer receipt bytes?
- Would replacing the #256 admission text be required for V1 through V5? If yes, the plan has widened past its scope.

### Assumption failure conditions

- The five sealed YAML bytes remain the approved manifest bytes
- Quantum-L9/.github remains the owner of the successor contract
- No existing Meta Planner consumer is discovered during T5
- The authority checkout can still open strategy/

### Blast radius notes

- A wrong contract would make operator doctrine look like global semantic law, or a consumer would present an unverified view as admitted.

### Rollback constraints

- Revert the successor artifact, the compiler adapter, and the consumer receipt insertion. The admitted generic contract, the five YAML files, and the #256 admission text stay untouched, so rollback does not restore them.

### Risks

| risk | mitigation |
|------|------------|
| The successor contract is guessed instead of being the owner's artifact | C1 stops the compiler work if the artifact is missing or if it registers strategy/ as canonical |
| Build starts on the dirty feat/pr-review-permission checkout and mixes the Context7 gate registration with this work | T3 and T4 require a branch cut from Cursor-Governance origin/main |
| Privacy or Meta Planner is marked active to make the closeout look finished | V5 passes only when both remain blocked |

## Out of scope

- Registering strategy/ in semantics/canonical_sources.yaml
- Rewriting l9.compiler/generic@1 in place or editing the five sealed YAML files
- Replacing strategy/ADMISSION.md or reordering the #256 release manifest
- Inventing a Meta Planner mode or setting Planner activation.default to true
- Claiming Coding Agent confidentiality while the authority checkout can read strategy/
- Landing this work on feat/pr-review-permission
- Program Execution campaign invocation, Program Lock, or a new global domain
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.unblock_operator_alignment_producer_and_consumer.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| source_ref | `plan.simple.unblock_operator_alignment_producer_and_consumer.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V0, E-V1, E-V2, E-V3, E-V4, E-V5
- **observed_evidence_refs:** none
- **missing_evidence:** E-V0, E-V1, E-V2, E-V3, E-V4, E-V5

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Which GitHub identity can be denied read of Quantum-L9/.github strategy/ so Coding Agent confidentiality can become true? — Privacy stays BLOCKED_PRIVACY in this plan. A later access-control change is a different plan. | `accept_bounded` |
| `unknown` | U2 | Is there an existing Meta Planner consumer to bind, or only an absent mode? — T5 records BLOCKED_NO_CONSUMER and does not create a mode. Discovery of a real consumer stops T5 and requires a new plan. | `probe` |
| `open_blocker` | stop_reason | Producer, consumer, and opt-in view are plannable. Privacy and Meta Planner stay blocked on purpose. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.unblock_operator_alignment_producer_and_consumer.v1"
  name: "Unblock operator alignment producer and consumer"
  overview: "Clear the producer-dependent campaign blockers with a successor operator-scoped source contract, a compiler adapter, and a fail-closed consumer binding. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 checked_record_count=366 conflicts=0 policy_version=memory-phase-lock/v2. Route depth is deep and omit_gates is empty."
  status: "draft"
  is_project: false
  owner: "repository owner"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "d23fd61708c197cbddd09f37870751a99dd53d17"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Clear the producer-dependent campaign blockers with a successor operator-scoped source contract, a compiler adapter, and a fail-closed consumer binding. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=165b1c81c2544136df8f02a8ec78e4c784b836946ebce25cec7af680790ea6c0 checked_record_count=366 conflicts=0 policy_version=memory-phase-lock/v2. Route depth is deep and omit_gates is empty."
  success_properties:
    - id: "SP-01"
      property: "V1: the compiler emits an operator-scoped receipt for strategy YAML and rejects that YAML as a global canonical source"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: the Cursor consumer accepts only that frozen receipt and still rejects a missing, forged, or mismatched view"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3: the five sealed YAML digests stay equal to the approved subject manifest"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4: Planner and CTO activation defaults stay false while a verified view can be loaded on opt-in"
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-05"
      property: "V5: Coding Agent privacy stays BLOCKED_PRIVACY and Meta Planner stays BLOCKED_NO_CONSUMER"
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.unblock_operator_alignment_producer_and_consumer.v1"
execution_envelope:
  filesystem:
    write_allow: ["Quantum-L9/.github successor compiler contract", "l9-semantic-compiler-engine registry adapter and tests/test_operator_source_projection.py", "ops/autonomy/operator_alignment.py", "ops/autonomy/projection_mode.py", "tests/ops/autonomy/test_operator_alignment.py", "tests/ops/autonomy/test_operator_view_opt_in.py", "tests/ops/autonomy/test_alignment_role_blocks.py", "governance/operator-alignment/STATUS.yaml"]
    write_deny: ["semantics/canonical_sources.yaml", "the five sealed strategy YAML files", "strategy/ADMISSION.md", "strategy/OPERATOR_RELEASE_MANIFEST.json", "governance/cto-mode/MODE.yaml", "governance/planner-mode/MODE.yaml", "commands/lcto.md", "commands/planner.md", "child system prompts"]
  commands:
    allow: ["python3 -m pytest tests/test_operator_source_projection.py", "python3 -m pytest tests/ops/autonomy/test_operator_alignment.py", "python3 -m pytest tests/ops/autonomy/test_operator_view_opt_in.py", "python3 -m pytest tests/ops/autonomy/test_alignment_role_blocks.py", "pre-commit run --config .pre-commit-config.yaml --files ops/autonomy/operator_alignment.py ops/autonomy/projection_mode.py"]
  network:
    mode: "named_services_only"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T5"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.unblock_operator_alignment_producer_and_consumer.v1"
dependency_topology_ref: "dag.plan.simple.unblock_operator_alignment_producer_and_consumer.v1"
validation_evidence_refs: ["E-V0", "E-V1", "E-V2", "E-V3", "E-V4", "E-V5"]
stress_and_disconfirm:
  disconfirming_cases: ["Does the successor still classify strategy YAML as canonical because the registry is the only input the compiler accepts?", "Does opt-in view loading turn Planner or CTO on without an explicit mode request?", "Does a consumer test pass by parsing a hand-written JSON preview instead of producer receipt bytes?", "Would replacing the #256 admission text be required for V1 through V5? If yes, the plan has widened past its scope."]
  assumption_failure_conditions: ["The five sealed YAML bytes remain the approved manifest bytes", "Quantum-L9/.github remains the owner of the successor contract", "No existing Meta Planner consumer is discovered during T5", "The authority checkout can still open strategy/"]
out_of_scope: ["Registering strategy/ in semantics/canonical_sources.yaml", "Rewriting l9.compiler/generic@1 in place or editing the five sealed YAML files", "Replacing strategy/ADMISSION.md or reordering the #256 release manifest", "Inventing a Meta Planner mode or setting Planner activation.default to true", "Claiming Coding Agent confidentiality while the authority checkout can read strategy/", "Landing this work on feat/pr-review-permission", "Program Execution campaign invocation, Program Lock, or a new global domain"]
convergence_contract_ref: "conv.plan.simple.unblock_operator_alignment_producer_and_consumer.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Add a successor compiler-contract artifact that names an operator-scoped source class distinct from the global canonical registry. Do not change the admitted l9.compiler/generic@1 inputs."
    status: "pending"
  - id: "T2"
    content: "Implement only the compiler adapter the successor contract names, with a negative test that strategy YAML is not a canonical source."
    status: "pending"
  - id: "T3"
    content: "Extend the existing fail-closed consumer in place. Record the producer receipt bytes only after T2 emits them. Keep the receipt set empty until those exact bytes exist."
    status: "pending"
  - id: "T4"
    content: "Allow an opt-in operator view to be cited by CTO, Architect, and Planner after the consumer verifies the receipt. Do not set activation.default to true and do not edit mode contracts or child prompts."
    status: "pending"
  - id: "T5"
    content: "Add tests that keep Coding Agent confidentiality and Meta Planner as explicit blocked results. Do not add a mode and do not hide strategy/ from the authority checkout."
    status: "pending"
```
