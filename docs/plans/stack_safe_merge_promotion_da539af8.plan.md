---
name: stack_safe_merge merge-commit promotions and long-lived head retention
overview: "Make ops/autonomy/stack_safe_merge.py choose merge_method=merge and keep the head branch whenever the PR head is a long-lived branch (default, protected, ruleset-guarded, or a long-lived name), failing safe when that cannot be determined, while leaving squash-for-unstacked-feature-leaf and merge-for-stack-parent behavior unchanged."
todos:
  - id: T1
    content: "Add long_lived_head(repo, head) probe: default branch, protected flag, deletion/non_fast_forward/update branch rules, long-lived names; L9_STACK_PROBE_FILE keys default_branch/protected/rules for offline tests; any REST failure returns long_lived with an unknown reason"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "select_merge_method: method merge when children or long-lived; record head_long_lived and keep_head_reason in the selection JSON"
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Deletion guard: merge_argv and _execute never delete a long-lived head on either transport regardless of --keep-branch; print the reason"
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "Regression tests: promotion head default/protected/ruleset/name selects merge and issues no delete; fail-safe on probe error; feature leaf still squash+delete; stack parent unchanged"
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "Update the l9-pr-remediation SKILL.md method comment to say long-lived heads (promotions) merge with a merge commit and are never deleted"
    status: pending
    phase: execute
    depends_on: [T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: stack_safe_merge merge-commit promotions and long-lived head retention

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention_dec5b97f.plan.md`
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
| plan_id | `plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| name | stack_safe_merge merge-commit promotions and long-lived head retention |
| overview | Make ops/autonomy/stack_safe_merge.py choose merge_method=merge and keep the head branch whenever the PR head is a long-lived branch (default, protected, ruleset-guarded, or a long-lived name), failing safe when that cannot be determined, while leaving squash-for-unstacked-feature-leaf and merge-for-stack-parent behavior unchanged. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-10T02:28:54+00:00 |
| updated_at | 2026-11-10T02:28:54+00:00 |
| depth | `standard` |
| estimate | 1 GMP |

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
| captured_at | `2026-11-10T02:28:54+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/home/user/wt/gov-ssm` |
| branch | `agent/claude-code/stack-safe-merge-promotion` |
| commit_sha | `f90e4e2e84254b2198efb4b42ca6cfd273dc48c5` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make ops/autonomy/stack_safe_merge.py choose merge_method=merge and keep the head branch whenever the PR head is a long-lived branch (default, protected, ruleset-guarded, or a long-lived name), failing safe when that cannot be determined, while leaving squash-for-unstacked-feature-leaf and merge-for-stack-parent behavior unchanged.

### Scope in

- ops/autonomy/stack_safe_merge.py long-lived head probe, method selection and deletion guard
- tests/ops/autonomy/test_stack_safe_merge.py regression tests for promotion and fail-safe cases
- skills/l9-pr-remediation/SKILL.md one-line method description

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | A Staging->Production promotion (head is the default or protected branch) selects method merge and the run issues no ref DELETE and no --delete-branch (V1) | `quality_gate` | V1: `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q` → all tests pass including the new promotion and fail-safe cases | `true` |
| SP-02 | An unstacked feature leaf with no long-lived signal still selects squash and still deletes its head (V1) | `quality_gate` | V1: `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q` → all tests pass including the new promotion and fail-safe cases | `true` |
| SP-03 | When the long-lived probe cannot be read the selection is merge with the head kept (V1) | `quality_gate` | V1: `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q` → all tests pass including the new promotion and fail-safe cases | `true` |
| SP-04 | The existing stack_safe_merge and merge_gate suites stay green (V2) | `quality_gate` | V2: `uv run pytest tests/ops/autonomy/test_merge_gate.py tests/ops/autonomy/test_merge_gate_rest_probe.py tests/ops/autonomy/test_merge_gate_rest_verb.py -q` → PASS unchanged | `true` |
| SP-05 | make precommit-repo passes on the changed files (V3) | `quality_gate` | V3: `make precommit-repo (.pre-commit-config.yaml)` → PASS on changed files (.pre-commit-config.yaml hooks) | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| source_ref | `plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind worktree /home/user/wt/gov-ssm on agent/claude-code/stack-safe-merge-promotion at origin/main f90e4e2` | clean worktree at base sha | `true` |
| P1 | pre-validation (status `passed`) | `read ops/autonomy/stack_safe_merge.py select_merge_method and _execute` | squash chosen solely from children; delete on by default | `true` |
| P2 | pre-validation (status `passed`) | `probe GitHub signals on cryptoxdog/IB-Odoo_19 Staging, Production, a feature branch and Quantum-L9/Cursor-Governance main and an agent branch` | long-lived branches report protected=true or deletion/non_fast_forward rules; feature branches report protected=false and no rules | `true` |
| P3 | pre-validation (status `passed`) | `name .pre-commit-config.yaml as the hook catalog for changed files` | catalog present | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/autonomy/stack_safe_merge.py`, `tests/ops/autonomy/test_stack_safe_merge.py`, `skills/l9-pr-remediation/SKILL.md`
- **write_deny:** `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q`, `make precommit-repo`, `uv run pytest tests/ops/autonomy/test_merge_gate.py tests/ops/autonomy/test_merge_gate_rest_probe.py tests/ops/autonomy/test_merge_gate_rest_verb.py -q`, `make precommit-repo (.pre-commit-config.yaml)`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | none |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- stack parent selects merge and keeps its branch
- unstacked feature leaf selects squash and deletes its head
- merge authorization and MERGE_PENDING semantics unchanged

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/stack_safe_merge.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/stack_safe_merge.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/autonomy/stack_safe_merge.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/ops/autonomy/test_stack_safe_merge.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-pr-remediation/SKILL.md` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `ops/autonomy` | `control_plane` | `stack parent selects merge and keeps its branch`, `unstacked feature leaf selects squash and deletes its head`, `merge authorization and MERGE_PENDING semantics unchanged` | `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile` |
| T2 | `ops/autonomy` | `control_plane` | `stack parent selects merge and keeps its branch`, `unstacked feature leaf selects squash and deletes its head`, `merge authorization and MERGE_PENDING semantics unchanged` | `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile` |
| T3 | `ops/autonomy` | `control_plane` | `stack parent selects merge and keeps its branch`, `unstacked feature leaf selects squash and deletes its head`, `merge authorization and MERGE_PENDING semantics unchanged` | `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile` |
| T4 | `tests/ops/autonomy` | `assurance` | `stack parent selects merge and keeps its branch`, `unstacked feature leaf selects squash and deletes its head`, `merge authorization and MERGE_PENDING semantics unchanged` | `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile` |
| T5 | `skills/l9-pr-remediation` | `docs` | `stack parent selects merge and keeps its branch`, `unstacked feature leaf selects squash and deletes its head`, `merge authorization and MERGE_PENDING semantics unchanged` | `ops/autonomy/merge_gate.py`, `CANONICAL_LAW.md`, `AGENTS.md`, `Makefile` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| source_execution_ref | `plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (--json on a probe-file promotion entry shows method merge and head_long_lived true) → stop and fix the probe before touching deletion; C2 fails (pytest tests/ops/autonomy/test_stack_safe_merge.py and test_merge_gate.py PASS) → block publication |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the single commit on main; the helper returns to children-only selection |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q`
- re-run `make precommit-repo`
- re-run `uv run pytest tests/ops/autonomy/test_merge_gate.py tests/ops/autonomy/test_merge_gate_rest_probe.py tests/ops/autonomy/test_merge_gate_rest_verb.py -q`
- re-run `make precommit-repo (.pre-commit-config.yaml)`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 5 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `high` — every merge executed by l9-pr-remediation across all repositories; a wrong method rewrites history shape and a wrong delete removes a long-lived branch |
| architectural_boundaries_crossed | none |
| external_systems_touched | `GitHub REST API (read-only probe)` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Add long_lived_head(repo, head) probe: default branch, protected flag, deletion/non_fast_forward/update branch rules, long-lived names; L9_STACK_PROBE_FILE keys default_branch/protected/rules for offline tests; any REST failure returns long_lived with an unknown reason | Cursor Build agent | `medium` | M | `[]` | `ops/autonomy/stack_safe_merge.py` |
| T2 | select_merge_method: method merge when children or long-lived; record head_long_lived and keep_head_reason in the selection JSON | Cursor Build agent | `medium` | S | `[T1]` | `ops/autonomy/stack_safe_merge.py` |
| T3 | Deletion guard: merge_argv and _execute never delete a long-lived head on either transport regardless of --keep-branch; print the reason | Cursor Build agent | `high` | S | `[T2]` | `ops/autonomy/stack_safe_merge.py` |
| T4 | Regression tests: promotion head default/protected/ruleset/name selects merge and issues no delete; fail-safe on probe error; feature leaf still squash+delete; stack parent unchanged | Cursor Build agent | `low` | M | `[T3]` | `tests/ops/autonomy/test_stack_safe_merge.py` |
| T5 | Update the l9-pr-remediation SKILL.md method comment to say long-lived heads (promotions) merge with a merge commit and are never deleted | Cursor Build agent | `low` | S | `[T3]` | `skills/l9-pr-remediation/SKILL.md` |

**Critical path:** T1 → T2 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | selection reports merge and keep-head for a long-lived head | deletion guard |
| M2 | regression and existing suites green | publication via make pr |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | --json on a probe-file promotion entry shows method merge and head_long_lived true | stop and fix the probe before touching deletion |
| C2 | M2 | pytest tests/ops/autonomy/test_stack_safe_merge.py and test_merge_gate.py PASS | block publication |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`, `T5`
- **Shared causes:** merge method and branch deletion inferred from stacked children only
- **Deletions / consolidations:** fold the children-only delete_branch=False special case into one keep-head decision

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | merge authority and publication law unchanged; only method selection and branch retention inside the helper |
| CANONICAL_LAW.md | `n_a` | — | no authority or gate semantics change |
| skills/l9-pr-remediation/SKILL.md | `update` | `T5` | — |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-03 | `quality_gate_evidence` | command | `uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q` | all tests pass including the new promotion and fail-safe cases | `not_run` |
| E-V2 | SP-04 | `quality_gate_evidence` | command | `uv run pytest tests/ops/autonomy/test_merge_gate.py tests/ops/autonomy/test_merge_gate_rest_probe.py tests/ops/autonomy/test_merge_gate_rest_verb.py -q` | PASS unchanged | `not_run` |
| E-V3 | SP-05 | `quality_gate_evidence` | command | `make precommit-repo (.pre-commit-config.yaml)` | PASS on changed files (.pre-commit-config.yaml hooks) | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Would an org ruleset that applies required_status_checks or workflows to every branch make every feature PR merge instead of squash?
- Could a feature branch named release/x or develop be squashed and deleted?
- Does the CLI fallback still pass --delete-branch for a long-lived head?
- Does an unreadable rules endpoint on a restricted gateway silently fall back to squash?

### Assumption failure conditions

- GitHub returns protected=false and no deletion/non_fast_forward/update rules for a branch the operator considers long-lived
- the session gateway refuses repos/{o}/{r}/rules/branches/{head} so every merge becomes a merge commit

### Blast radius notes

- every merge executed by l9-pr-remediation across all repositories; a wrong method rewrites history shape and a wrong delete removes a long-lived branch

### Rollback constraints

- revert the single commit on main; the helper returns to children-only selection

### Risks

| risk | mitigation |
|------|------------|
| an all-branches org ruleset marks every branch long-lived and stops squash | count only deletion, non_fast_forward and update rule types; required_status_checks and workflows are ignored |
| probe failures turn squash into merge on restricted surfaces | accepted: merge is ancestry-safe; the reason is printed in the selection JSON |

## Out of scope

- merge_gate.py authorization or stack-parent denial logic
- repository delete_branch_on_merge settings or GitHub rulesets
- pr_board.py and pr_fleet.py merge ordering
- CANONICAL_LAW.md and AGENTS.md
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
| source_ref | `plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `open_blocker` | stop_reason | plan validated structurally; implementation not yet run | planning convergence `partial` |

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
  plan_id: "plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1"
  name: "stack_safe_merge merge-commit promotions and long-lived head retention"
  overview: "Make ops/autonomy/stack_safe_merge.py choose merge_method=merge and keep the head branch whenever the PR head is a long-lived branch (default, protected, ruleset-guarded, or a long-lived name), failing safe when that cannot be determined, while leaving squash-for-unstacked-feature-leaf and merge-for-stack-parent behavior unchanged."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "f90e4e2e84254b2198efb4b42ca6cfd273dc48c5"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make ops/autonomy/stack_safe_merge.py choose merge_method=merge and keep the head branch whenever the PR head is a long-lived branch (default, protected, ruleset-guarded, or a long-lived name), failing safe when that cannot be determined, while leaving squash-for-unstacked-feature-leaf and merge-for-stack-parent behavior unchanged."
  success_properties:
    - id: "SP-01"
      property: "A Staging->Production promotion (head is the default or protected branch) selects method merge and the run issues no ref DELETE and no --delete-branch (V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "An unstacked feature leaf with no long-lived signal still selects squash and still deletes its head (V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-03"
      property: "When the long-lived probe cannot be read the selection is merge with the head kept (V1)"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-04"
      property: "The existing stack_safe_merge and merge_gate suites stay green (V2)"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-05"
      property: "make precommit-repo passes on the changed files (V3)"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/autonomy/stack_safe_merge.py", "tests/ops/autonomy/test_stack_safe_merge.py", "skills/l9-pr-remediation/SKILL.md"]
    write_deny: ["ops/autonomy/merge_gate.py", "CANONICAL_LAW.md", "AGENTS.md", "Makefile"]
  commands:
    allow: ["uv run pytest tests/ops/autonomy/test_stack_safe_merge.py -q", "make precommit-repo", "uv run pytest tests/ops/autonomy/test_merge_gate.py tests/ops/autonomy/test_merge_gate_rest_probe.py tests/ops/autonomy/test_merge_gate_rest_verb.py -q", "make precommit-repo (.pre-commit-config.yaml)"]
  network:
    mode: "none"
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
rollback_contract_ref: "rollback.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1"
dependency_topology_ref: "dag.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3"]
stress_and_disconfirm:
  disconfirming_cases: ["Would an org ruleset that applies required_status_checks or workflows to every branch make every feature PR merge instead of squash?", "Could a feature branch named release/x or develop be squashed and deleted?", "Does the CLI fallback still pass --delete-branch for a long-lived head?", "Does an unreadable rules endpoint on a restricted gateway silently fall back to squash?"]
  assumption_failure_conditions: ["GitHub returns protected=false and no deletion/non_fast_forward/update rules for a branch the operator considers long-lived", "the session gateway refuses repos/{o}/{r}/rules/branches/{head} so every merge becomes a merge commit"]
out_of_scope: ["merge_gate.py authorization or stack-parent denial logic", "repository delete_branch_on_merge settings or GitHub rulesets", "pr_board.py and pr_fleet.py merge ordering", "CANONICAL_LAW.md and AGENTS.md"]
convergence_contract_ref: "conv.plan.simple.stack_safe_merge_merge_commit_promotions_and_long_lived_head_retention.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Add long_lived_head(repo, head) probe: default branch, protected flag, deletion/non_fast_forward/update branch rules, long-lived names; L9_STACK_PROBE_FILE keys default_branch/protected/rules for offline tests; any REST failure returns long_lived with an unknown reason"
    status: "pending"
  - id: "T2"
    content: "select_merge_method: method merge when children or long-lived; record head_long_lived and keep_head_reason in the selection JSON"
    status: "pending"
  - id: "T3"
    content: "Deletion guard: merge_argv and _execute never delete a long-lived head on either transport regardless of --keep-branch; print the reason"
    status: "pending"
  - id: "T4"
    content: "Regression tests: promotion head default/protected/ruleset/name selects merge and issues no delete; fail-safe on probe error; feature leaf still squash+delete; stack parent unchanged"
    status: "pending"
  - id: "T5"
    content: "Update the l9-pr-remediation SKILL.md method comment to say long-lived heads (promotions) merge with a merge commit and are never deleted"
    status: "pending"
```
