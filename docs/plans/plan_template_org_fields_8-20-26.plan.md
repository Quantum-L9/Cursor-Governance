---
name: Plan template organization fields
overview: "Project first-order leverage, seams, and files into Cursor plan frontmatter so the store can be scored without a second schema. Edit the git SSOT template, then sync _TEMPLATE. Do not fork the mirror."
leverage_class: contract
leverage:
  ranked_todo_ids: [todo-02-template-frontmatter, todo-03-schema-optional, todo-04-renderer, todo-01-baseline-preflight, todo-05-skill-align, todo-06-sync-mirror, todo-07-prove]
  shared_causes: [organization fields exist only in PLAN_DOCUMENT JSON]
  deletions_or_consolidations: [no second score schema; no concern folders]
seams_affected: [l9-plan, plan_store, cursor_frontmatter]
files_impacted:
  - environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md
  - environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md.meta.md
  - docs/plans/_TEMPLATE.plan.md
  - skills/l9-plan/scripts/render_plan_pe_autonomy.py
  - skills/l9-plan/schemas/plan-document.schema.json
  - skills/l9-plan/SKILL.md
  - skills/l9-plan/references/plan-workflow-pe-autonomy.md
  - skills/l9-plan/references/first-order-leverage.md
  - commands/l9-plan.md
todos:
  - id: todo-01-baseline-preflight
    content: "PE W0: re-verify HEAD + _TEMPLATE is a sync mirror of the git SSOT"
    status: pending
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: todo-02-template-frontmatter
    content: "Add leverage_class, leverage, seams_affected, files_impacted to canonical template frontmatter + Metadata"
    status: pending
    phase: execute
    depends_on: [todo-01-baseline-preflight]
    side_effect_ref: SE-todo-02
    evidence_property_refs: [SP-02]
  - id: todo-03-schema-optional
    content: "Optional PLAN_DOCUMENT fields: leverage.class, seams_affected, files_impacted (do not add to required[])"
    status: pending
    phase: execute
    depends_on: [todo-02-template-frontmatter]
    evidence_property_refs: [SP-02]
  - id: todo-04-renderer
    content: "Renderer emits the new frontmatter from PLAN_DOCUMENT"
    status: pending
    phase: execute
    depends_on: [todo-03-schema-optional]
    evidence_property_refs: [SP-02]
  - id: todo-05-skill-align
    content: "Align SKILL.md, plan-workflow, first-order-leverage.md, commands/l9-plan.md (date filename + new fields)"
    status: pending
    phase: execute
    depends_on: [todo-02-template-frontmatter]
    evidence_property_refs: [SP-02]
  - id: todo-06-sync-mirror
    content: "sync_cursor_plan_template.py writes _TEMPLATE.plan.md from SSOT"
    status: pending
    phase: execute
    depends_on: [todo-02-template-frontmatter]
    evidence_property_refs: [SP-02]
  - id: todo-07-prove
    content: "Fixtures PASS, self_test PASS, sync --check 0, make pr-check PASS"
    status: pending
    phase: validate
    depends_on: [todo-03-schema-optional, todo-04-renderer, todo-05-skill-align, todo-06-sync-mirror]
    evidence_property_refs: [SP-01, SP-03]
isProject: false
kernel_pass:
  bound_path: plan_template_org_fields_8-20-26.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T17:20:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Stamp kernel_pass so the next editor is not the first to fail G_PLAN_KERNEL_PASS"
      - "Keep this plan's existing todos and body; do not reopen landed work from this stamp"
      - "Do not mix #374 end-of-file-fixer exclude into this corpus pass"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-29T17:20:30Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Align with issue #377 and the #376 G_PRECOMMIT_CONFIG plus kernel_pass precedent"
      - "Leave docs/plans/_TEMPLATE.plan.md exempt via PLAN_SKIP_PREFIXES"
      - "Do not edit .pre-commit-config.yaml in this cluster"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T17:21:00Z
    body_sha256: "3ef7c791c97fc8c49408138e2f0cc3c57988b2fb0ce11fb82006b16cb49bdd05"
    deltas:
      - "G_PLAN_ETC and G_PLAN_EITHER_OR stay clean after this stamp"
      - "Canonical body_sha256 is the post-stamp file hash with sha fields zeroed"
      - "Do not mark status executable while the checker still fails"
---

# PLAN: Plan template organization fields

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` + `skills/l9-plan/schemas/plan-document.schema.json`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` under a Program lease. `/l9-plan` does not mutate.
> **Rename to:** `plan_template_org_fields_8-20-26.plan.md`
> **Companion:** `docs/plans/plan_template_org_fields_8-20-26.plan.json` (`validate_plan_document.py` PASS)

## Execute via @environment/program-execution + autonomy (required)

```text
this .plan.md
        │
        ▼
@environment/program-execution   Blueprint → Program Lock → Controller
        │ lease
        ▼
@autonomy (/autonomy → l9-bounded-autonomy)
        │
        ▼
cursor-foreground
```

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

Or explicit execute of this plan on a **new branch from `origin/main`** (KERNEL/pack landing default). Do not mix the dirty primary WIP.

`autonomous_merge: false`. Packet: `authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE` · `profile: pr-convergence` · `plan_ref: docs/plans/plan_template_org_fields_8-20-26.plan.md`

### Phase-0 ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | kind |
|----|------------|------|------------|----------|------|
| todo-01-baseline-preflight | TASK-001 | W0 | [] | false | work |
| todo-02-template-frontmatter | TASK-002 | W1 | [todo-01] | true | work |
| todo-03-schema-optional | TASK-003 | W1 | [todo-02] | true | work |
| todo-04-renderer | TASK-004 | W1 | [todo-03] | true | work |
| todo-05-skill-align | TASK-005 | W1 | [todo-02] | true | work |
| todo-06-sync-mirror | TASK-006 | W1 | [todo-02] | true | work |
| todo-07-prove | TASK-007 | W2 | [todo-03..06] | false | work |

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.l9-plan.template-org-fields.v1` |
| schema_version | `1.0.0` |
| status | `draft` |
| owner | Igor Beylin |
| created_at | `2026-08-20` |
| leverage_class | `contract` |
| seams_affected | `l9-plan`, `plan_store`, `cursor_frontmatter` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `skills/l9-plan/references/first-order-leverage.md` + `docs/plans/README.md` score law |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Project existing JSON leverage into Cursor frontmatter. Do not invent a second score. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-20T21:24:00Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `main` (dirty; execute on new branch from `origin/main`) |
| commit_sha | `b406feeb4734f7029c36d718a68b004cacd6a68a` |
| dirty | `true` |
| overlap_policy | `explicitly_allow_listed_paths` |
| allowed_local_dirt | `docs/plans/**` store hygiene already in flight |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

`/l9-plan` already has a `leverage` object and per-task `files`. Those fields never reach Cursor frontmatter, so the plans store cannot scan them. Add three fill-in frontmatter keys — `leverage_class`, `seams_affected`, `files_impacted` — plus the existing `leverage` lists — to the **git SSOT** template, then sync `_TEMPLATE.plan.md`. Align skill/command/renderer. Optional schema keys only.

`leverage_class` ∈ `shared_root_cause` | `contract` | `validation` | `local_symptom` (first-order-leverage.md). `seams_affected` is a token list for collision/census, **not** a folder taxonomy. `files_impacted` is the plan-level union of task files.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline SHA still matches at execute start | `repository_state` | `git rev-parse HEAD` == `b406feeb4734f7029c36d718a68b004cacd6a68a` or stop_and_replan | true |
| SP-02 | SSOT frontmatter + renderer emit the four keys; skill/command name them; `_TEMPLATE` matches SSOT | `structural` | grep keys in SSOT + rendered sample; `sync --check` exit 0 | true |
| SP-03 | Existing fixtures still PASS; changed-files gate PASS | `quality_gate` | `validate_plan_document.py fixtures/plan_pass.json`; `self_test.py`; `make pr-check` | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.l9-plan.template-org-fields.v1` |
| blocking | `true` |

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | equals locked SHA or replan | true |
| CP-02 | `command_available` | `python3 skills/l9-plan/scripts/sync_cursor_plan_template.py --help` | exit 0 | true |
| CP-03 | `filesystem_write` | SSOT + skill paths writable | paths exist | true |

## Execution envelope

### Filesystem

- **write_allow:** paths in `gmp_handoff.may_modify`
- **write_deny:** `AGENTS.md`, `CANONICAL_LAW.md`, `Makefile`, `docs/plans/built/`, `docs/plans/backlog/`, `docs/plans/archive/`, secrets

### Commands

- **allow:** `python3 skills/l9-plan/scripts/*`, `make pr-check`
- **deny:** force-push, hard-reset, `make pr` from plan mode

### Network

| Field | Value |
|-------|-------|
| mode | `none` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| todo-01-baseline-preflight | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| todo-02-template-frontmatter | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore` SSOT | false |
| todo-03-schema-optional | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore` schema | false |
| todo-04-renderer | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore` renderer | false |
| todo-05-skill-align | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore` skill/command | false |
| todo-06-sync-mirror | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | re-run sync | false |
| todo-07-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| todo-02-template-frontmatter | l9-plan | `control_plane` | first-order-leverage.md + executable-plan SSOT | second score schema; concern folders; required[] expansion |
| todo-03-schema-optional | l9-plan | `control_plane` | plan-document.schema.json | breaking required fields |
| todo-06-sync-mirror | plan_store | `docs` | sync_cursor_plan_template.py | hand-edit _TEMPLATE as SSOT |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.l9-plan.template-org-fields.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | may_modify only |
| data | `none` | |
| external_state | `none` | |
| local_state | `git_restore_scoped_paths` | re-sync mirror |

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` |
| uncertainty | `low` |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `0` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Execution DAG

**Critical path:** todo-01 → todo-02 → todo-03 → todo-04 → todo-05 → todo-06 → todo-07

todo-05 and todo-06 may run after todo-02 in parallel with todo-03/04.

**Forbidden edges:** required[] expansion; editing `_TEMPLATE` before SSOT.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | command | expected_positive | status |
|-------------|---------------|---------------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | `git rev-parse HEAD` | locked SHA | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | grep + `sync --check` | keys present; exit 0 | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | `validate_plan_document.py` + `self_test.py` + `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

- If new schema fields are **required**, every existing fixture and campaign JSON fails → keep optional.
- If `_TEMPLATE` is edited as SSOT, next `sync --check` fails or overwrites → edit canonical only.
- If `seams_affected` is used as a folder name, we recreate concern shelves → README + skill forbid that.

Blast radius: new `/l9-plan` projections and the template mirror. Parked plans unchanged.

Rollback: scoped `git restore` of may_modify; re-run sync.

## Out of scope

- Mass-rename of `built/` / `backlog/` / `archive/`
- New `pe/` / `ci/` / date folders
- Second scoring system
- Auto-Build of the live queue
- AGENTS.md / CANONICAL_LAW.md

## Convergence

| Field | Value |
|-------|-------|
| status | `partial` |
| remaining_unknown_ids | `[]` |
| next_skill | `l9-ynp` |
| execute_via | `@environment/program-execution` → `@autonomy` |
| stop_reason | `/l9-plan` is planning-only; JSON PASSed; implementation not run |

## Frontmatter contract to add (execute)

```yaml
leverage_class: shared_root_cause | contract | validation | local_symptom
leverage:
  ranked_todo_ids: []
  shared_causes: []
  deletions_or_consolidations: []
seams_affected: []   # tokens for census/collision; not folders
files_impacted: []   # plan-level union of task files
```
