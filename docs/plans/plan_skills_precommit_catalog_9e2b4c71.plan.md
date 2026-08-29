---
name: Plan skills keep only the precommit catalog
overview: "Strip commit and push ceremony from /l9-plan and /l9-plan-simple. Planning teachers and the shared validator bind quality to .pre-commit-config.yaml as the hook catalog only. Do not mutate the catalog. Do not rewrite Makefile public ceremony or PE packet commit/push allowances."
todos:
  - id: retarget-gate
    content: "Rename G_PR_CHECK to G_PRECOMMIT_CONFIG. code_in_scope final_validation must name .pre-commit-config.yaml and must not require make pr-check or make pr. Update gates, router, fixtures."
    status: pending
    phase: execute
    depends_on: []
  - id: strip-teachers
    content: "Remove named commit/push/pr/pr-check gates from both plan SKILL.md files, both workflows, legacy workflow, and commands/l9-plan.md. Bind .pre-commit-config.yaml. Keep PE and Cursor Build execute headings."
    status: pending
    phase: execute
    depends_on: [retarget-gate]
  - id: renderer-template
    content: "Renderer SP proof and canonical template SP-03 / EV-SP-03 examples name .pre-commit-config.yaml. Leave allowed_inside_packet commit and push lines untouched."
    status: pending
    phase: execute
    depends_on: [retarget-gate]
  - id: reentry-scan
    content: "Extend test_ceremony_ownership.py to scan the four plan teacher files for unnegated make pr-check, isolated make pr, OPEN_PR=0, git commit, git push."
    status: pending
    phase: execute
    depends_on: [strip-teachers, renderer-template]
  - id: prove
    content: "Pack self_test PASS; ceremony ownership PASS; git diff -- .pre-commit-config.yaml empty. Pathspecs only."
    status: pending
    phase: validate
    depends_on: [reentry-scan]
isProject: false
kind: pe
execute_via: pe-campaign
kernel_pass:
  bound_path: plan_skills_precommit_catalog_9e2b4c71.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T00:45:00Z
    body_sha256: "b729bab339118564eb40eca2a2cdc7a420a61314f65cb628ca70602d07088e55"
    deltas:
      - "Locked quality bind to .pre-commit-config.yaml; G_PRECOMMIT_CONFIG replaces G_PR_CHECK"
      - "Four plan teachers lose named commit/push/pr gates; PE packet commit/push stays execute-only"
      - "Catalog file and Makefile graph are write_deny"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T00:45:30Z
    body_sha256: "b729bab339118564eb40eca2a2cdc7a420a61314f65cb628ca70602d07088e55"
    deltas:
      - "Companion PLAN_DOCUMENT JSON already PASSes validate_plan_document.py under the current G_PR_CHECK"
      - "Stacked on feat/pr-check-folded; not a KERNEL pack new-branch from origin/main"
      - "Foreign dirty .claude/settings.json and fold_pr-check plan stay write_deny"
---

# PLAN: Plan skills keep only the precommit catalog

**kind:** `pe` · **execute_via:** `pe-campaign` · **skill:** `l9-plan`
**plan_id:** `plan.governance.plan-skills-precommit-catalog.v1` · **schema_version:** `1.0.0` · **status:** `executable`

Machine SSOT: [`docs/plans/plan_skills_precommit_catalog_9e2b4c71.plan.json`](plan_skills_precommit_catalog_9e2b4c71.plan.json) (`validate_plan_document.py` PASS).

> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** then subordinate **[@autonomy](commands/autonomy.md)** under a Program lease. Do not free-form mutate from this markdown alone.

## Metadata

| Field | Value |
|---|---|
| plan_id | `plan.governance.plan-skills-precommit-catalog.v1` |
| name | Plan skills keep only the precommit catalog |
| overview | Strip commit/push ceremony from the two plan skills; bind `.pre-commit-config.yaml` |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` |
| owner | cursor-governance |
| created_at | `2026-08-28` |
| updated_at | `2026-08-28` |

## Architect framing

| Field | Value |
|---|---|
| planning_ssot | `skills/l9-plan/SKILL.md` + `skills/l9-plan/scripts/validate_plan_document.py` |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Fold-pr-check already made `make pr` the public ceremony and `.pre-commit-config.yaml` the catalog. The two plan skills still teach a second ceremony (`make pr-check` / `OPEN_PR=0 make pr` / no-commit-no-push). Remove that teaching. Do not fold Make. |

## Immutable baseline

| Field | Value |
|---|---|
| captured_at | 2026-08-29T00:40:00Z |
| repository | Quantum-L9/Cursor-Governance |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `feat/pr-check-folded` |
| commit_sha | `ee4c40d954cdb480260d5a3fc2b6a588559d4f49` |
| dirty | `true` |
| artifact_hashes | `{ "skills/l9-plan/scripts/validate_plan_document.py": "on-disk", ".pre-commit-config.yaml": "must-remain-unchanged" }` |
| allowed_local_dirt | none of this change set |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

Write_deny (foreign): `.claude/settings.json`, `docs/plans/fold_pr-check_81560ec1.plan.md`.

Do not write `Lock: origin/main = <sha>`. At execute start, branch `feat/plan-skills-precommit-catalog` from this HEAD (same worktree is allowed; do not restack onto `origin/main` or the fold commits drop).

## Objective

### Mission

`/l9-plan` and `/l9-plan-simple` are planning teachers. They currently name a publish/diagnose ceremony as the governed-workspace quality gate. The residual catalog SSOT is already [`.pre-commit-config.yaml`](.pre-commit-config.yaml). Strip every named `git commit`, `git push`, `make pr`, `make pr-check`, and `OPEN_PR=0 make pr` gate from those two skills, their slash files, the shared validator, and the renderer/template examples. Keep the catalog. Do not edit the catalog.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Fixture with `.pre-commit-config.yaml` in `final_validation` PASSes | `quality_gate` | `python3 skills/l9-plan/scripts/validate_plan_document.py fixtures/plan_pass.json` PASS | true |
| SP-02 | Fixture omitting the catalog path FAILs `G_PRECOMMIT_CONFIG` | `quality_gate` | fail fixture stderr contains `G_PRECOMMIT_CONFIG` | true |
| SP-03 | Four live plan teachers name no commit/push/pr gate | `structural` | `test_ceremony_ownership.py` PASS on those paths | true |
| SP-04 | Renderer and template examples name the catalog | `structural` | `rg 'make pr-check' skills/l9-plan/scripts/render_plan_pe_autonomy.py` empty in `_success_table`; template SP-03/EV-SP-03 cite `.pre-commit-config.yaml` | true |
| SP-05 | Catalog bytes unchanged | `filesystem` | `git diff -- .pre-commit-config.yaml` empty | true |
| SP-06 | Pack self_test PASS | `quality_gate` | `python3 skills/l9-plan/scripts/self_test.py` PASS | true |

## Capability preflight

| Field | Value |
|---|---|
| preflight_id | `preflight.plan.governance.plan-skills-precommit-catalog.v1` |
| source_ref | this plan_id |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | Immutable baseline |
| baseline_verified | passed at plan emit |
| drift_detected | false |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | still `ee4c40d954cdb480260d5a3fc2b6a588559d4f49` or a child of it that only adds this plan | true |
| CP-02 | `command_available` | `python3 skills/l9-plan/scripts/validate_plan_document.py` | exits 0 on this JSON | true |
| CP-03 | `filesystem_write` | may_modify paths writable | skill/command/template/test paths exist and are not write_deny | true |

## Execution envelope

### Filesystem

- **write_allow:** `skills/l9-plan/**`, `skills/l9-plan-simple/**`, `commands/l9-plan.md`, `commands/l9-plan-simple.md`, `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`, `tests/ops/scripts/test_ceremony_ownership.py`, `docs/plans/plan_skills_precommit_catalog_9e2b4c71.plan.md`, `docs/plans/plan_skills_precommit_catalog_9e2b4c71.plan.json`
- **write_deny:** `.pre-commit-config.yaml`, `Makefile`, `AGENTS.md`, `CANONICAL_LAW.md`, `.claude/settings.json`, `docs/plans/fold_pr-check_81560ec1.plan.md`, `skills/l9-pr-remediation/**`

### Commands

- **allow:** pack `self_test.py`, `validate_plan_document.py`, `pytest tests/ops/scripts/test_ceremony_ownership.py`, scoped `git add` pathspecs, `git diff -- .pre-commit-config.yaml`
- **deny:** `make pr`, `make pr-check` as a plan-teacher string, `OPEN_PR=0 make pr` from plan mode, `pre-commit install`, `git add -A`

### Network / secrets

- none required

### Campaign packet stub

```yaml
authority_profile: program_controller_bound
autonomous_merge: false
declared_branches: [feat/plan-skills-precommit-catalog]
allowed_inside_packet:
  - execute_plan_todos_inside_envelope
forbidden_inside_packet:
  - force_push
  - admin_merge
  - commit_secrets
  - weaken_tests_for_green
  - mutate_.pre-commit-config.yaml
```

## Side effects + idempotency

| todo | mutation | idempotent | side effect |
|---|---|---|---|
| retarget-gate | yes | yes | fixtures that still say only `make pr-check` FAIL until updated in the same todo |
| strip-teachers | yes | yes | slash `/l9-plan` Gate commands block disappears |
| renderer-template | yes | yes | new rendered plans cite the catalog |
| reentry-scan | yes | yes | CI fails if a teacher re-adds a ceremony verb |
| prove | no | yes | evidence only |

## Architecture impact

Shared validator is the leverage point. Teachers and the template example follow it. Makefile public ceremony and remediator verify stay where fold-pr-check put them. Claude `.claude/skills/` copies are projections — do not hand-edit; they refresh on projection.

## Rollback

Revert the pathspec commits on `feat/plan-skills-precommit-catalog`. Catalog file is never edited, so hook ids cannot be corrupted. Restore `G_PR_CHECK` from git if the gate rename must be undone.

## Complexity and uncertainty

Standard depth. Evidence is in-tree (validator `_check_code_scope`, both SKILL.md Pre-Validate lines, `commands/l9-plan.md` Gate commands). No material Unknown. Projection lag of `.claude/skills/` is accepted and bounded (source is `skills/`).

## Execution DAG / Phase-0 ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | kind |
|----|------------|------|------------|----------|-----------|---------------|------|
| retarget-gate | TASK-001 | W1 | [] | true | `path:skills/l9-plan/scripts/validate_plan_document.py` | mutate-gate | work |
| strip-teachers | TASK-002 | W1 | [retarget-gate] | true | `path:skills/l9-plan/SKILL.md` | mutate-teachers | work |
| renderer-template | TASK-003 | W1 | [retarget-gate] | true | `path:skills/l9-plan/scripts/render_plan_pe_autonomy.py` | mutate-render | work |
| reentry-scan | TASK-004 | W2 | [strip-teachers, renderer-template] | true | `path:tests/ops/scripts/test_ceremony_ownership.py` | mutate-scan | work |
| prove | TASK-005 | W2 | [reentry-scan] | false | `evidence:plan.governance.plan-skills-precommit-catalog.v1` | validate | work |

`strip-teachers` and `renderer-template` may run in the same wave after `retarget-gate` (C1). Do not start `reentry-scan` until both are on disk.

## Property evidence matrix

| EV | SP | kind | command | expect | now |
|---|---|---|---|---|---|
| EV-SP-01 | SP-01 | quality_gate | `validate_plan_document.py fixtures/plan_pass.json` | PASS | not_run |
| EV-SP-02 | SP-02 | quality_gate | fail fixture | `G_PRECOMMIT_CONFIG` | not_run |
| EV-SP-03 | SP-03 | structural | `test_ceremony_ownership.py` | PASS | not_run |
| EV-SP-04 | SP-04 | structural | rg renderer + template | catalog named | not_run |
| EV-SP-05 | SP-05 | filesystem | `git diff -- .pre-commit-config.yaml` | empty | not_run |
| EV-SP-06 | SP-06 | quality_gate | pack `self_test.py` | PASS | not_run |

## Stress and disconfirm

- If agents still run `OPEN_PR=0 make pr` after the Gate commands block is gone, a generated `.claude/skills` copy or skill-registry blurb kept teaching it — thicken the `skills/` source, then let projection refresh. Do not hand-edit `.claude/skills`.
- If `G_PRECOMMIT_CONFIG` only searches `final_validation.command`, authors can hide `make pr-check` in `success_criteria`. Accept that: the teacher scan covers live skills/commands; do not corpus-scan `docs/plans/`.
- If template SP-03 stays `make pr-check`, every new PE plan re-teaches the gate. `renderer-template` is on the critical path for that reason.

## Out of scope

- Mutating `.pre-commit-config.yaml`
- Makefile `pr: pr-preflight pr-check` graph
- AGENTS.md append-only rewrite
- PE packet `commit_scoped_on_declared_branch` / `push_non_force_declared_branch`
- Remediator `make precommit-repo` / `git push`
- `pre-commit install`
- fold-pr-check leftover prove todo
- Foreign dirty listed above

## Convergence

| Field | Value |
|---|---|
| status | partial |
| remaining_unknown_ids | [] |
| next_skill | `/autonomy` + `@environment/program-execution` |
| stop_reason | Planning complete; implementation not started from plan mode |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| autonomous_merge | false |

## Execute via @environment/program-execution + autonomy

```text
.plan.md
  → @environment/program-execution  (Blueprint → Program Lock → Controller)
  → root autonomy/ + @autonomy (/autonomy → l9-bounded-autonomy)  [subordinate lease]
  → PE adapter (default Cursor: cursor-foreground)
```

1. Bind this checkout. Do not restack onto `origin/main`.
2. Open `feat/plan-skills-precommit-catalog` from `ee4c40d954cdb480260d5a3fc2b6a588559d4f49` (or this HEAD if it is still that SHA plus only this plan).
3. Controller `claim` / `render` TASK-001 then TASK-002/003, then TASK-004/005.
4. Autonomy must not widen write_allow onto `.pre-commit-config.yaml` or `Makefile`.
5. Do not merge. Do not run `make campaign` from this chat as a substitute for the Controller.

```yaml
execute_via:
  pipeline: pe-campaign
  mention_program: "@environment/program-execution"
  command_ref: Program Lock then Controller claim/render
  authority_order:
    - plan_document
    - program_execution
    - autonomy_subordinate
```
