---
name: Fail-closed l9-plan-simple pipeline
overview: "Make /l9-plan-simple fail closed so an invocation runs l9-global-architect and emits a plan whose required sections validate with no unknown or unbound markers. GAR run gar-fail-closed-20261105 is STANDALONE (orchestration authority was not transferred). Realization mode is MUTATION by OBJECTIVE_DERIVATION RM-001. Validation is required by VD-001. Delivery is PERSISTED_REPOSITORY by DL-003. Dep..."
todos:
  - id: T1
    content: "Add write_plan_run.py that hashes GAR load_order and stores the bound intervention evidence. Standalone GAR persistence stays optional."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Require owner, estimate, execution_envelope, complexity, and the layer field on every task in the plan schema. Renderer exits non-zero on unknown or unbound markers unless --allow-draft is set."
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Bind the section receipt to the GAR run file hash and fail when the markdown contains unknown or unbound markers."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Add run_plan_pipeline.py as the only writer: prefetch receipt, GAR run file, validator, renderer with required --execute-via and --workspace, then receipt generate and validate."
    status: pending
    phase: execute
    depends_on: [T1, T2, T3]
  - id: T5
    content: "Add admit_plan.py, call it from plan_kernel_gate handle_post_tool_use, append a changed-file hook to .pre-commit-config.yaml, and probe whether the host plan-tool payload is visible."
    status: pending
    phase: execute
    depends_on: [T3, T4]
  - id: T6
    content: "Remove the hand-copy sentence. Point SKILL.md, plan-workflow-simple.md, and commands/l9-plan-build.md at run_plan_pipeline.py."
    status: pending
    phase: execute
    depends_on: [T4]
  - id: T7
    content: "Lock V1 through V6, including a title-and-paragraph fixture that admit_plan.py rejects, and update the renderer marker test to require --allow-draft."
    status: pending
    phase: execute
    depends_on: [T4, T5, T6]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Fail-closed l9-plan-simple pipeline

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `fail_closed_l9_plan_simple_pipeline_3c712fa8.plan.md`
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
| plan_id | `plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| name | Fail-closed l9-plan-simple pipeline |
| overview | Make /l9-plan-simple fail closed so an invocation runs l9-global-architect and emits a plan whose required sections validate with no unknown or unbound markers. GAR run gar-fail-closed-20261105 is STANDALONE (orchestration authority was not transferred). Realization mode is MUTATION by OBJECTIVE_DERIVATION RM-001. Validation is required by VD-001. Delivery is PERSISTED_REPOSITORY by DL-003. Depth profile is DEEP because the blast radius crosses the skill, the plan schema, and the hook plane. First-Order intervention, bound before architecture: one pipeline is the only admissible writer of a simple plan. Governing cause is verified from the two host plan cards and from the scripts: the host accepts a plan with no architect proof, and validate_plan_document.py plus render_plan_pe_autonomy.py treat a half-filled plan as success. Kill-pattern hypothesis KP-001 is confirmed: CreatePlan and the renderer are two writers of the same artifact with no consistency protocol. Selected architecture stays inside that intervention: run_plan_pipeline.py sequences the existing validator and renderer, a GAR run file is mandatory for this skill only, and admit_plan.py rejects any other simple plan. Standalone GAR persistence stays optional for other callers. The L9 architecture profile applies as a constraint on this governance skill and does not activate L9_INTEGRATED. Evaluator result for the host plan-tool payload is UNKNOWN (U2). |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U2 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T16:07:19+00:00 |
| updated_at | 2026-11-05T16:07:19+00:00 |
| depth | `deep` |
| estimate | 1 PR |

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
| captured_at | `2026-11-05T16:07:19+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| branch | `main` |
| commit_sha | `ae8e17c403bb1231aeb9f69816a3c1598488632a` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make /l9-plan-simple fail closed so an invocation runs l9-global-architect and emits a plan whose required sections validate with no unknown or unbound markers. GAR run gar-fail-closed-20261105 is STANDALONE (orchestration authority was not transferred). Realization mode is MUTATION by OBJECTIVE_DERIVATION RM-001. Validation is required by VD-001. Delivery is PERSISTED_REPOSITORY by DL-003. Depth profile is DEEP because the blast radius crosses the skill, the plan schema, and the hook plane. First-Order intervention, bound before architecture: one pipeline is the only admissible writer of a simple plan. Governing cause is verified from the two host plan cards and from the scripts: the host accepts a plan with no architect proof, and validate_plan_document.py plus render_plan_pe_autonomy.py treat a half-filled plan as success. Kill-pattern hypothesis KP-001 is confirmed: CreatePlan and the renderer are two writers of the same artifact with no consistency protocol. Selected architecture stays inside that intervention: run_plan_pipeline.py sequences the existing validator and renderer, a GAR run file is mandatory for this skill only, and admit_plan.py rejects any other simple plan. Standalone GAR persistence stays optional for other callers. The L9 architecture profile applies as a constraint on this governance skill and does not activate L9_INTEGRATED. Evaluator result for the host plan-tool payload is UNKNOWN (U2).

### Scope in

- skills/l9-global-architect/scripts/write_plan_run.py
- skills/l9-plan/schemas/plan-document.schema.json
- skills/l9-plan/scripts/render_plan_pe_autonomy.py
- skills/l9-plan/fixtures/plan_pass.json
- skills/l9-plan-simple/scripts/run_plan_pipeline.py
- skills/l9-plan-simple/scripts/admit_plan.py
- skills/l9-plan-simple/scripts/generate_plan_section_receipt.py
- skills/l9-plan-simple/scripts/validate_plan_section_receipt.py
- skills/l9-plan-simple/scripts/plan_sections.py
- skills/l9-plan-simple/SKILL.md
- skills/l9-plan-simple/references/plan-workflow-simple.md
- commands/l9-plan-build.md
- ops/hooks/plan_kernel_gate.py
- .pre-commit-config.yaml

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves run_plan_pipeline.py exits non-zero when the GAR run file is absent | `quality_gate` | V1: `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py on a fixture with no GAR run file` → exit non-zero; V3: `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .` → section receipt PASS and the markdown has no unknown or unbound marker | `true` |
| SP-02 | V2 proves validate_plan_document.py rejects a document that omits owner, execution_envelope, complexity, or todo layer | `quality_gate` | V2: `python3 skills/l9-plan/scripts/validate_plan_document.py on a document missing owner, execution_envelope, complexity, or layer` → exit non-zero | `true` |
| SP-03 | V3 proves the render_plan_pe_autonomy.py projection has a passing section receipt and contains no unknown or unbound marker | `quality_gate` | V3: `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .` → section receipt PASS and the markdown has no unknown or unbound marker; V6: `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json` → exit 0 and the Program Execution heading is present | `true` |
| SP-04 | V4 proves admit_plan.py exits non-zero on a title-and-paragraph plan | `quality_gate` | V4: `python3 skills/l9-plan-simple/scripts/admit_plan.py on a title-and-paragraph fixture` → exit non-zero; V7: `python3 -m pytest tests/skills/l9_plan_simple -q && python3 skills/l9-plan-simple/scripts/self_test.py && .pre-commit-config.yaml` → pytest and self_test exit 0; the changed-file hook listed in .pre-commit-config.yaml runs admit_plan.py | `true` |
| SP-05 | V5 proves validate_plan_section_receipt.py exits non-zero when gar_upstream.invoked is true and the GAR run file is absent | `quality_gate` | V5: `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py on a receipt whose gar run file is absent` → exit non-zero and the error names the missing run file | `true` |
| SP-06 | V6 proves render_plan_pe_autonomy.py without --execute-via still emits the Program Execution heading for a complete document | `quality_gate` | V6: `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json` → exit 0 and the Program Execution heading is present | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.fail_closed_l9_plan_simple_pipeline.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| source_ref | `plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P1 | pre-validation (status `passed`) | `python3 ops/hooks/plan_memory_prefetch.py --workspace . --task fail-closed l9-plan-simple pipeline` | MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=d61f55afac338e26f63d0e606eda537b24b8c292d0158da42c420c8c7dc406fc checked_record_count=349 conflicts=0 policy_version=memory-phase-lock/v2 | `true` |
| P2 | pre-validation (status `passed`) | `Read skills/l9-global-architect/SKILL.md and runtime/MANIFEST.yaml load_order: catalogs/REASON_CODES.yaml, runtime/EVALUATOR_REGISTRY.yaml, contracts/EPISTEMIC_DISCIPLINE.yaml, contracts/L9_ARCHITECTURE_PROFILE.yaml, integrations/REASONING_FOURSOME_BINDING.yaml, contracts/ARCHITECTURAL_INTEGRITY.yaml, contracts/OBJECTIVE_DERIVATION.yaml, contracts/OUTCOME_OWNERSHIP.yaml, contracts/CONVERGENCE.yaml, kernels/ARCHITECT_KERNEL.yaml, catalogs/KILL_PATTERNS.yaml, runtime/RUN_STATE.yaml, integrations/L9_RUNTIME_BINDING.yaml, runtime/STATE_MACHINE.yaml; reasoning foursome 01 through 04` | GAR run gar-fail-closed-20261105 reached PLAN with intervention bound and integration_mode STANDALONE | `true` |
| P3 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk high --evidence partial --json` | depth=deep and omit_gates=[] | `true` |
| P4 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD` | branch main at 7da1b739baa535bd9842b5147de9abc8ac4421f6; hook catalog is .pre-commit-config.yaml | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `skills/l9-global-architect/scripts/write_plan_run.py`, `skills/l9-plan/schemas/plan-document.schema.json`, `skills/l9-plan/scripts/render_plan_pe_autonomy.py`, `skills/l9-plan/fixtures/plan_pass.json`, `tests/skills/l9_plan_simple/test_renderer_fill.py`, `skills/l9-plan-simple/scripts/plan_sections.py`, `skills/l9-plan-simple/scripts/generate_plan_section_receipt.py`, `skills/l9-plan-simple/scripts/validate_plan_section_receipt.py`, `skills/l9-plan-simple/schemas/plan-section-receipt.schema.json`, `skills/l9-plan-simple/scripts/run_plan_pipeline.py`, `skills/l9-plan-simple/scripts/admit_plan.py`, `ops/hooks/plan_kernel_gate.py`, `.pre-commit-config.yaml`, `skills/l9-plan-simple/SKILL.md`, `skills/l9-plan-simple/references/plan-workflow-simple.md`, `commands/l9-plan-build.md`, `skills/l9-plan-simple/scripts/self_test.py`, `tests/skills/l9_plan_simple/`
- **write_deny:** `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 skills/l9-plan/scripts/validate_plan_document.py`, `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py`, `python3 skills/l9-plan-simple/scripts/self_test.py`, `python3 -m pytest tests/skills/l9_plan_simple -q`, `.pre-commit-config.yaml`, `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py on a fixture with no GAR run file`, `python3 skills/l9-plan/scripts/validate_plan_document.py on a document missing owner, execution_envelope, complexity, or layer`, `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .`, `python3 skills/l9-plan-simple/scripts/admit_plan.py on a title-and-paragraph fixture`, `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py on a receipt whose gar run file is absent`, `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json`, `python3 -m pytest tests/skills/l9_plan_simple -q && python3 skills/l9-plan-simple/scripts/self_test.py && .pre-commit-config.yaml`
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

- renderer --execute-via default stays Program Execution
- beforeSubmitPrompt stays fail-open
- kernel-pass stays a separate latch
- standalone GAR persistence stays optional

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-global-architect/scripts/write_plan_run.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan/schemas/plan-document.schema.json skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json tests/skills/l9_plan_simple/test_renderer_fill.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan-simple/scripts/plan_sections.py skills/l9-plan-simple/scripts/generate_plan_section_receipt.py skills/l9-plan-simple/scripts/validate_plan_section_receipt.py skills/l9-plan-simple/schemas/plan-section-receipt.schema.json` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan-simple/scripts/run_plan_pipeline.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan-simple/scripts/admit_plan.py ops/hooks/plan_kernel_gate.py .pre-commit-config.yaml` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan-simple/SKILL.md skills/l9-plan-simple/references/plan-workflow-simple.md commands/l9-plan-build.md` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- skills/l9-plan-simple/scripts/self_test.py tests/skills/l9_plan_simple/` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `skills/l9-global-architect/scripts` | `control_plane` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T2 | `repository root` | `policy` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T3 | `skills/l9-plan-simple` | `assurance` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T4 | `skills/l9-plan-simple/scripts` | `control_plane` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T5 | `repository root` | `runtime` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T6 | `repository root` | `docs` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |
| T7 | `repository root` | `assurance` | `renderer --execute-via default stays Program Execution`, `beforeSubmitPrompt stays fail-open`, `kernel-pass stays a separate latch`, `standalone GAR persistence stays optional` | `AGENTS.md`, `CANONICAL_LAW.md`, `skills/l9-pr-integration-testing/references/adapters.md` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.fail_closed_l9_plan_simple_pipeline.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| source_execution_ref | `plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (validate_plan_document.py fails a fixture missing owner) → stop and fix the schema before writing the pipeline; C2 fails (admit_plan.py rejects a title-and-paragraph fixture) → stop and fix admission before retargeting the skill text; C3 fails (self_test.py and pytest tests/skills/l9_plan_simple exit 0) → block publication |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the pull request. No data migration and no deployed service. Restoring the previous scripts restores the previous exit codes. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 skills/l9-plan/scripts/validate_plan_document.py`
- re-run `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py`
- re-run `python3 skills/l9-plan-simple/scripts/self_test.py`
- re-run `python3 -m pytest tests/skills/l9_plan_simple -q`
- re-run `.pre-commit-config.yaml`
- re-run `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py on a fixture with no GAR run file`
- re-run `python3 skills/l9-plan/scripts/validate_plan_document.py on a document missing owner, execution_envelope, complexity, or layer`
- re-run `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .`
- re-run `python3 skills/l9-plan-simple/scripts/admit_plan.py on a title-and-paragraph fixture`
- re-run `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py on a receipt whose gar run file is absent`
- re-run `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json`
- re-run `python3 -m pytest tests/skills/l9_plan_simple -q && python3 skills/l9-plan-simple/scripts/self_test.py && .pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 7 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `high` — Every new simple plan, the plan-pass fixture, renderer tests, and any changed kind:simple plan in a pull request. Historical plans outside the diff stay as they are. A wrong admit rule blocks publication of a legitimate plan edit until the receipt is regenerated. |
| architectural_boundaries_crossed | `skill prompt plane`, `PLAN_DOCUMENT schema`, `Cursor post-tool hook`, `pre-commit publication gate` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.fail_closed_l9_plan_simple_pipeline.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Add write_plan_run.py that hashes GAR load_order and stores the bound intervention evidence. Standalone GAR persistence stays optional. | Cursor Build agent | `medium` | S | `[]` | `skills/l9-global-architect/scripts/write_plan_run.py` |
| T2 | Require owner, estimate, execution_envelope, complexity, and the layer field on every task in the plan schema. Renderer exits non-zero on unknown or unbound markers unless --allow-draft is set. | Cursor Build agent | `high` | M | `[]` | `skills/l9-plan/schemas/plan-document.schema.json`, `skills/l9-plan/scripts/render_plan_pe_autonomy.py`, `skills/l9-plan/fixtures/plan_pass.json`, `tests/skills/l9_plan_simple/test_renderer_fill.py` |
| T3 | Bind the section receipt to the GAR run file hash and fail when the markdown contains unknown or unbound markers. | Cursor Build agent | `medium` | M | `[T1]` | `skills/l9-plan-simple/scripts/plan_sections.py`, `skills/l9-plan-simple/scripts/generate_plan_section_receipt.py`, `skills/l9-plan-simple/scripts/validate_plan_section_receipt.py`, `skills/l9-plan-simple/schemas/plan-section-receipt.schema.json` |
| T4 | Add run_plan_pipeline.py as the only writer: prefetch receipt, GAR run file, validator, renderer with required --execute-via and --workspace, then receipt generate and validate. | Cursor Build agent | `medium` | M | `[T1, T2, T3]` | `skills/l9-plan-simple/scripts/run_plan_pipeline.py` |
| T5 | Add admit_plan.py, call it from plan_kernel_gate handle_post_tool_use, append a changed-file hook to .pre-commit-config.yaml, and probe whether the host plan-tool payload is visible. | Cursor Build agent | `high` | M | `[T3, T4]` | `skills/l9-plan-simple/scripts/admit_plan.py`, `ops/hooks/plan_kernel_gate.py`, `.pre-commit-config.yaml` |
| T6 | Remove the hand-copy sentence. Point SKILL.md, plan-workflow-simple.md, and commands/l9-plan-build.md at run_plan_pipeline.py. | Cursor Build agent | `low` | S | `[T4]` | `skills/l9-plan-simple/SKILL.md`, `skills/l9-plan-simple/references/plan-workflow-simple.md`, `commands/l9-plan-build.md` |
| T7 | Lock V1 through V6, including a title-and-paragraph fixture that admit_plan.py rejects, and update the renderer marker test to require --allow-draft. | Cursor Build agent | `medium` | M | `[T4, T5, T6]` | `skills/l9-plan-simple/scripts/self_test.py`, `tests/skills/l9_plan_simple/` |

**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | GAR run file and schema both refuse an incomplete plan | pipeline writer |
| M2 | run_plan_pipeline.py is the only writer and admit_plan.py rejects other simple plans | publication hook and skill text |
| M3 | V1 through V6 pass | ready to publish |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | validate_plan_document.py fails a fixture missing owner | stop and fix the schema before writing the pipeline |
| C2 | M2 | admit_plan.py rejects a title-and-paragraph fixture | stop and fix admission before retargeting the skill text |
| C3 | M3 | self_test.py and pytest tests/skills/l9_plan_simple exit 0 | block publication |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`
- **Shared causes:** GAR invocation is a self-attested boolean; validator PASS still renders unknown markers and exits 0; two writers and no consistency protocol
- **Deletions / consolidations:** Remove the hand-copy path in plan-workflow-simple.md; Remove the self-attested --gar-invoked success path

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| skills/l9-plan-simple/SKILL.md | `update` | `T6` | — |
| skills/l9-plan-simple/references/plan-workflow-simple.md | `update` | `T6` | — |
| commands/l9-plan-build.md | `update` | `T6` | — |
| .pre-commit-config.yaml | `update` | `T5` | — |
| AGENTS.md | `n_a` | — | Additive operating instructions already name l9-plan-simple. The behavior change lives in the skill, the schema, and the hooks. |
| CANONICAL_LAW.md | `n_a` | — | Symlink law and publication law are unchanged. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py on a fixture with no GAR run file` | exit non-zero | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `python3 skills/l9-plan/scripts/validate_plan_document.py on a document missing owner, execution_envelope, complexity, or layer` | exit non-zero | `not_run` |
| E-V3 | SP-01, SP-03 | `quality_gate_evidence` | command | `python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .` | section receipt PASS and the markdown has no unknown or unbound marker | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `python3 skills/l9-plan-simple/scripts/admit_plan.py on a title-and-paragraph fixture` | exit non-zero | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py on a receipt whose gar run file is absent` | exit non-zero and the error names the missing run file | `not_run` |
| E-V6 | SP-03, SP-06 | `quality_gate_evidence` | command | `python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json` | exit 0 and the Program Execution heading is present | `not_run` |
| E-V7 | SP-04 | `quality_gate_evidence` | command | `python3 -m pytest tests/skills/l9_plan_simple -q && python3 skills/l9-plan-simple/scripts/self_test.py && .pre-commit-config.yaml` | pytest and self_test exit 0; the changed-file hook listed in .pre-commit-config.yaml runs admit_plan.py | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- If the only new check is skill prose, can the next session still emit a title-and-paragraph host plan card?
- If the schema change is not paired with a renderer failure, can a valid JSON document still render unknown markers and exit 0?
- If admission runs on _TEMPLATE.plan.md and on /ff corpus edits, do unrelated plan files fail publication?
- If handle_post_tool_use starts enforcing kernel-pass again, do store plans gain a second ceremony this plan does not authorize?

### Assumption failure conditions

- validate_plan_document.py remains the schema owner and the renderer remains the only projection
- Cursor postToolUse still receives file-write paths ending in .plan.md
- beforeSubmitPrompt stays fail-open and is not the gate
- .pre-commit-config.yaml runs on changed files inside make pr

### Blast radius notes

- Every new simple plan, the plan-pass fixture, renderer tests, and any changed kind:simple plan in a pull request. Historical plans outside the diff stay as they are. A wrong admit rule blocks publication of a legitimate plan edit until the receipt is regenerated.

### Rollback constraints

- Revert the pull request. No data migration and no deployed service. Restoring the previous scripts restores the previous exit codes.

### Risks

| risk | mitigation |
|------|------------|
| Schema tightening breaks plan_pass.json and renderer tests that expect unknown markers and exit 0 | Update the fixture in the same change and require --allow-draft for the marker test |
| Admission on every plan file blocks /ff corpus edits and the template plan | Exempt _TEMPLATE.plan.md and apply the gate to kind simple status current plans in the changed-file set |
| .pre-commit-config.yaml is a protected root file | Append one hook entry and use the protected-root stamp on the pull request |

## Out of scope

- Rewriting the BRS drift plan or the integration-PR plan from the screenshots
- Program Execution campaign publication and Program Lock
- Requiring a disk run file for every standalone GAR invoke
- Cancelling the host plan-card UI
- Migrating historical docs/plans JSON
- Editing AGENTS.md or CANONICAL_LAW.md
- The unrelated dirty file skills/l9-pr-integration-testing/references/adapters.md
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.fail_closed_l9_plan_simple_pipeline.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
| source_ref | `plan.simple.fail_closed_l9_plan_simple_pipeline.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6, E-V7

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U2 | Does postToolUse receive the host plan-tool payload, or only file writes? — The file gate and the pre-commit hook land either way. A payload that includes the plan body also fails the latch when required headings are absent. | `probe` |
| `open_blocker` | stop_reason | PLAN_DOCUMENT is the planning deliverable. Implementation proofs V1-V7 are pending. U2 stays a probe and blocks converged. | planning convergence `partial` |

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
  plan_id: "plan.simple.fail_closed_l9_plan_simple_pipeline.v1"
  name: "Fail-closed l9-plan-simple pipeline"
  overview: "Make /l9-plan-simple fail closed so an invocation runs l9-global-architect and emits a plan whose required sections validate with no unknown or unbound markers. GAR run gar-fail-closed-20261105 is STANDALONE (orchestration authority was not transferred). Realization mode is MUTATION by OBJECTIVE_DERIVATION RM-001. Validation is required by VD-001. Delivery is PERSISTED_REPOSITORY by DL-003. Depth profile is DEEP because the blast radius crosses the skill, the plan schema, and the hook plane. First-Order intervention, bound before architecture: one pipeline is the only admissible writer of a simple plan. Governing cause is verified from the two host plan cards and from the scripts: the host accepts a plan with no architect proof, and validate_plan_document.py plus render_plan_pe_autonomy.py treat a half-filled plan as success. Kill-pattern hypothesis KP-001 is confirmed: CreatePlan and the renderer are two writers of the same artifact with no consistency protocol. Selected architecture stays inside that intervention: run_plan_pipeline.py sequences the existing validator and renderer, a GAR run file is mandatory for this skill only, and admit_plan.py rejects any other simple plan. Standalone GAR persistence stays optional for other callers. The L9 architecture profile applies as a constraint on this governance skill and does not activate L9_INTEGRATED. Evaluator result for the host plan-tool payload is UNKNOWN (U2)."
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
  commit_sha: "ae8e17c403bb1231aeb9f69816a3c1598488632a"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make /l9-plan-simple fail closed so an invocation runs l9-global-architect and emits a plan whose required sections validate with no unknown or unbound markers. GAR run gar-fail-closed-20261105 is STANDALONE (orchestration authority was not transferred). Realization mode is MUTATION by OBJECTIVE_DERIVATION RM-001. Validation is required by VD-001. Delivery is PERSISTED_REPOSITORY by DL-003. Depth profile is DEEP because the blast radius crosses the skill, the plan schema, and the hook plane. First-Order intervention, bound before architecture: one pipeline is the only admissible writer of a simple plan. Governing cause is verified from the two host plan cards and from the scripts: the host accepts a plan with no architect proof, and validate_plan_document.py plus render_plan_pe_autonomy.py treat a half-filled plan as success. Kill-pattern hypothesis KP-001 is confirmed: CreatePlan and the renderer are two writers of the same artifact with no consistency protocol. Selected architecture stays inside that intervention: run_plan_pipeline.py sequences the existing validator and renderer, a GAR run file is mandatory for this skill only, and admit_plan.py rejects any other simple plan. Standalone GAR persistence stays optional for other callers. The L9 architecture profile applies as a constraint on this governance skill and does not activate L9_INTEGRATED. Evaluator result for the host plan-tool payload is UNKNOWN (U2)."
  success_properties:
    - id: "SP-01"
      property: "V1 proves run_plan_pipeline.py exits non-zero when the GAR run file is absent"
      evidence_type: "quality_gate"
      proof: ["V1", "V3"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves validate_plan_document.py rejects a document that omits owner, execution_envelope, complexity, or todo layer"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves the render_plan_pe_autonomy.py projection has a passing section receipt and contains no unknown or unbound marker"
      evidence_type: "quality_gate"
      proof: ["V3", "V6"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves admit_plan.py exits non-zero on a title-and-paragraph plan"
      evidence_type: "quality_gate"
      proof: ["V4", "V7"]
      blocking: true
    - id: "SP-05"
      property: "V5 proves validate_plan_section_receipt.py exits non-zero when gar_upstream.invoked is true and the GAR run file is absent"
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
    - id: "SP-06"
      property: "V6 proves render_plan_pe_autonomy.py without --execute-via still emits the Program Execution heading for a complete document"
      evidence_type: "quality_gate"
      proof: ["V6"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.fail_closed_l9_plan_simple_pipeline.v1"
execution_envelope:
  filesystem:
    write_allow: ["skills/l9-global-architect/scripts/write_plan_run.py", "skills/l9-plan/schemas/plan-document.schema.json", "skills/l9-plan/scripts/render_plan_pe_autonomy.py", "skills/l9-plan/fixtures/plan_pass.json", "tests/skills/l9_plan_simple/test_renderer_fill.py", "skills/l9-plan-simple/scripts/plan_sections.py", "skills/l9-plan-simple/scripts/generate_plan_section_receipt.py", "skills/l9-plan-simple/scripts/validate_plan_section_receipt.py", "skills/l9-plan-simple/schemas/plan-section-receipt.schema.json", "skills/l9-plan-simple/scripts/run_plan_pipeline.py", "skills/l9-plan-simple/scripts/admit_plan.py", "ops/hooks/plan_kernel_gate.py", ".pre-commit-config.yaml", "skills/l9-plan-simple/SKILL.md", "skills/l9-plan-simple/references/plan-workflow-simple.md", "commands/l9-plan-build.md", "skills/l9-plan-simple/scripts/self_test.py", "tests/skills/l9_plan_simple/"]
    write_deny: ["AGENTS.md", "CANONICAL_LAW.md", "skills/l9-pr-integration-testing/references/adapters.md"]
  commands:
    allow: ["python3 skills/l9-plan/scripts/validate_plan_document.py", "python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py", "python3 skills/l9-plan-simple/scripts/self_test.py", "python3 -m pytest tests/skills/l9_plan_simple -q", ".pre-commit-config.yaml", "python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py on a fixture with no GAR run file", "python3 skills/l9-plan/scripts/validate_plan_document.py on a document missing owner, execution_envelope, complexity, or layer", "python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py --execute-via=cursor-build --workspace .", "python3 skills/l9-plan-simple/scripts/admit_plan.py on a title-and-paragraph fixture", "python3 skills/l9-plan-simple/scripts/validate_plan_section_receipt.py on a receipt whose gar run file is absent", "python3 skills/l9-plan/scripts/render_plan_pe_autonomy.py skills/l9-plan/fixtures/plan_pass.json", "python3 -m pytest tests/skills/l9_plan_simple -q && python3 skills/l9-plan-simple/scripts/self_test.py && .pre-commit-config.yaml"]
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
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.fail_closed_l9_plan_simple_pipeline.v1"
dependency_topology_ref: "dag.plan.simple.fail_closed_l9_plan_simple_pipeline.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6", "E-V7"]
stress_and_disconfirm:
  disconfirming_cases: ["If the only new check is skill prose, can the next session still emit a title-and-paragraph host plan card?", "If the schema change is not paired with a renderer failure, can a valid JSON document still render unknown markers and exit 0?", "If admission runs on _TEMPLATE.plan.md and on /ff corpus edits, do unrelated plan files fail publication?", "If handle_post_tool_use starts enforcing kernel-pass again, do store plans gain a second ceremony this plan does not authorize?"]
  assumption_failure_conditions: ["validate_plan_document.py remains the schema owner and the renderer remains the only projection", "Cursor postToolUse still receives file-write paths ending in .plan.md", "beforeSubmitPrompt stays fail-open and is not the gate", ".pre-commit-config.yaml runs on changed files inside make pr"]
out_of_scope: ["Rewriting the BRS drift plan or the integration-PR plan from the screenshots", "Program Execution campaign publication and Program Lock", "Requiring a disk run file for every standalone GAR invoke", "Cancelling the host plan-card UI", "Migrating historical docs/plans JSON", "Editing AGENTS.md or CANONICAL_LAW.md", "The unrelated dirty file skills/l9-pr-integration-testing/references/adapters.md"]
convergence_contract_ref: "conv.plan.simple.fail_closed_l9_plan_simple_pipeline.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Add write_plan_run.py that hashes GAR load_order and stores the bound intervention evidence. Standalone GAR persistence stays optional."
    status: "pending"
  - id: "T2"
    content: "Require owner, estimate, execution_envelope, complexity, and the layer field on every task in the plan schema. Renderer exits non-zero on unknown or unbound markers unless --allow-draft is set."
    status: "pending"
  - id: "T3"
    content: "Bind the section receipt to the GAR run file hash and fail when the markdown contains unknown or unbound markers."
    status: "pending"
  - id: "T4"
    content: "Add run_plan_pipeline.py as the only writer: prefetch receipt, GAR run file, validator, renderer with required --execute-via and --workspace, then receipt generate and validate."
    status: "pending"
  - id: "T5"
    content: "Add admit_plan.py, call it from plan_kernel_gate handle_post_tool_use, append a changed-file hook to .pre-commit-config.yaml, and probe whether the host plan-tool payload is visible."
    status: "pending"
  - id: "T6"
    content: "Remove the hand-copy sentence. Point SKILL.md, plan-workflow-simple.md, and commands/l9-plan-build.md at run_plan_pipeline.py."
    status: "pending"
  - id: "T7"
    content: "Lock V1 through V6, including a title-and-paragraph fixture that admit_plan.py rejects, and update the renderer marker test to require --allow-draft."
    status: "pending"
```
