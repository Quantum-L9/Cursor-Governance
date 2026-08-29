---
name: PR-train pack overlap
overview: "Fix pr-train so a colocated conflict component stays one stacked car, remainder ships unique blobs including filenames main already touched, empty extracts skip instead of aborting the train, and the diagnose SHA list cap rises from 50 to 100. Land on feat/pr-train-pack-overlap from merged #370 (main @ d6b30cdc)."
todos:
  - id: T0
    content: "Emit this PLAN_DOCUMENT JSON and Cursor Build .plan.md under docs/plans/; validate with validate_plan_document.py. Branch feat/pr-train-pack-overlap from d6b30cdc."
    status: pending
    phase: execute
    depends_on: []
  - id: T1
    content: "filter_slices_against_tip: one tip-conflict or unknown in a colocated non-remainder group skips the whole ordered group to remainder. Do not publish a clean subset. Keep parent-inherit only inside a fully clean group. Disjoint fully-clean groups stay separate cars."
    status: pending
    phase: execute
    depends_on: [T0]
  - id: T2
    content: "remainder_paths_for_commit: keep paths whose blob at sha differs from tip (or tip lacks the path). Drop identical blobs only. Do not use tip_changed_paths fork-diff. Leave collect_remainder_slice last-writer and extract_remainder checkout mechanics."
    status: pending
    phase: execute
    depends_on: [T0]
  - id: T3
    content: "Raise ExtractEmpty from empty cherry-pick skip-all and empty remainder. extract_node catches it: current_slice+1, clear extract_worktree. route_after_extract goes to stack_base when worktree empty. Cherry-pick conflict still fail-closes."
    status: pending
    phase: execute
    depends_on: [T1, T2]
  - id: T4
    content: "RECEIPT_SHA_LIST_CAP=100 on cherry_novel_commits, cherry_dup_commits, commit_subjects in diagnose_ref_value.py. Comment 59371162 display bound vs pr-train incomplete-receipt halt. Keep test_incomplete_novelty_receipt_halts."
    status: pending
    phase: execute
    depends_on: [T0]
  - id: T5
    content: "Update commands/pr-train.md OPEN_TRAIN: colocated slice is all-or-nothing; remainder is unique blobs vs tip including overlap; last writer wins. Do not restore unique_tip."
    status: pending
    phase: execute
    depends_on: [T1, T2]
  - id: T6
    content: "Rewrite remainder tests (overlap unique bytes kept; identical blob dropped). Add all-or-nothing group test and ExtractEmpty skip/route tests. Keep two-group clean-stays and H4 extract_remainder mechanics. pytest then make precommit-repo. Scoped commit. No make pr."
    status: pending
    phase: execute
    depends_on: [T1, T2, T3, T4, T5]
isProject: false
kind: simple
execute_via: cursor-build
kernel_pass:
  bound_path: pr_train_pack_overlap_37baa1e0.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T04:40:00Z
    body_sha256: "a8d70ced9e712eedfcdf9c990f3d812ee786795b78aa666a660fdba01506c68d"
    deltas:
      - "All-or-nothing colocated filter is first-order leverage: do not publish a clean subset of a conflict component"
      - "Remainder keep predicate is unique blobs vs tip, not filenames main touched since the fork"
      - "ExtractEmpty skips an empty car so remainder appended last still runs"
      - "Diagnose SHA list cap 50 to 100; incomplete-receipt halt stays"
      - "Land from merged #370 tip d6b30cdc; do not mix leftover haul"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T04:41:00Z
    body_sha256: "a8d70ced9e712eedfcdf9c990f3d812ee786795b78aa666a660fdba01506c68d"
    deltas:
      - "pytest tests/workflows/test_pr_train_dag.py 48 passed including tombstone last-writer delete"
      - "Deleted donor paths still listed so collect_remainder_slice can pop"
      - "Cherry-pick conflict still fail-closes; extract_remainder checkout mechanics unchanged"
      - "Foreign dirty on this checkout is write_deny; no make pr from this Build"
---

# PLAN: PR-train pack overlap

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Work in the current checkout. Do not run `make campaign`.
> **Suggested filename:** `pr-train-pack-overlap_e5334bb7.plan.md`

## Objective (from PLAN_DOCUMENT)

Fix pr-train so a colocated conflict component stays one stacked car, remainder ships unique blobs including filenames main already touched, empty extracts skip instead of aborting the train, and the diagnose SHA list cap rises from 50 to 100. Land on feat/pr-train-pack-overlap from merged #370 (main @ d6b30cdc).

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | filter_slices_against_tip: one tip-conflict or unknown probe in a colocated group skips the whole group to remainder; pytest proves no clean-subset keep | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | remainder_paths_for_commit keeps sha blob != tip blob (overlap included) and drops identical blobs only; collect_remainder_slice / extract_remainder checkout mechanics unchanged | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | ExtractEmpty skips the car (current_slice + 1, empty extract_worktree) and route_after_extract goes to stack_base; cherry-pick conflict still blocks | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | diagnose_ref_value.py RECEIPT_SHA_LIST_CAP=100 on cherry_novel_commits, cherry_dup_commits, commit_subjects; incomplete-receipt halt still fires when count > listed | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | pytest tests/workflows/test_pr_train_dag.py PASS then make precommit-repo PASS on authored pathspecs; Cursor stop (do not make pr unless the human typed it) | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** workflows/dags/pr_train_dag.py filter_slices_against_tip remainder_paths_for_commit ExtractEmpty extract_node route_after_extract, skills/l9-git-work-preserve/scripts/diagnose_ref_value.py RECEIPT_SHA_LIST_CAP, tests/workflows/test_pr_train_dag.py remainder all-or-nothing empty-skip, commands/pr-train.md OPEN_TRAIN remainder sentence

**Out:**
- Re-running /pr-train --execute / leftover haul
- Restoring unique_tip_node (never in #370)
- Makefile / pyproject.toml / dag-authoring / audit-component from #370
- MERGE_TRAIN, force-push, --all-refs
- Uncapping novel lists entirely
- make campaign / Program Lock / AGENTS.md rewrite

## Critical path (seed)

T0 → T1 → T2 → T3 → T4 → T5 → T6

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Wrong all-or-nothing can merge unrelated clean work into remainder; wrong blob remainder can clobber tip files with older donor blobs; empty-skip must not swallow cherry-pick conflicts
- Rollback: Revert feat/pr-train-pack-overlap; main @ d6b30cdc (#370) stays

## Convergence (seed)

- status: partial
- next_skill: Build (current checkout)
- stop_reason: Plan validated structurally; implementation is this Build
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: PR-train pack overlap

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, press **Build** and work in the **current checkout**. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.<domain>.<slug>.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `draft` \| `preflight_blocked` \| `executable` \| `in_progress` \| `validation_failed` \| `converged` \| `superseded` |
| is_project | `false` *(frontmatter `isProject`)* |
| owner | |
| created_at | `YYYY-MM-DD` |
| updated_at | |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | path or ADR that owns architecture for this change |
| plan_class | `bounded_execution_contract` \| `migration_plan` \| `retirement_plan` \| `remediation_plan` \| `deployment_plan` \| `refactor_plan` \| `integration_plan` \| `recovery_plan` \| `custom` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build on the current checkout; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | ISO datetime |
| repository | `org/repo` |
| workspace | absolute or `$(pwd)` convention |
| ssot_clone | if applicable |
| branch | feature branch name |
| commit_sha | **full 40-char SHA** (PLAN-SCHEMA-001) |
| dirty | `true` \| `false` |
| artifact_hashes | `{ "path": "sha256:…" }` |
| allowed_local_dirt | optional path list |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` \| `require_clean_tree` \| `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

One paragraph: residual defect or feature; system bound; non-negotiable preserved contracts.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline still matches locked SHA at start | `repository_state` | `git rev-parse HEAD` == locked SHA | true |
| SP-02 | Declared behavior/structure holds after mutation | `runtime_behavior` \| `structural` \| `filesystem` | exact command + expected marker (not exit-0 alone) | true |
| SP-03 | Quality gate / PR gate PASS on changed files | `quality_gate` | e.g. bind `.pre-commit-config.yaml` catalog | true |

`evidence_type` ∈ `filesystem` \| `runtime_behavior` \| `structural` \| `quality_gate` \| `repository_state` \| `network_observation` \| `proof_receipt` \| `human_confirmation`

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → fill path or inline id below.

| Field | Value |
|-------|-------|
| preflight_id | `preflight.<plan_id>` |
| source_ref | this plan_id |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | baseline section / receipt path |
| baseline_verified | |
| drift_detected | |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | equals locked commit_sha | true |
| CP-02 | `command_available` | tool X present | version / path | true |
| CP-03 | `filesystem_write` | may_modify paths writable | write probe or ACL | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `path/or/glob/...`
- **write_deny:** `protected/...`, secrets, unrelated trees
- **delete_allow:** *(optional)*

### Commands

- **allow:** listed validation / mutate commands
- **deny:** force-push, hard-reset, secret exfil, out-of-scope installs

### Network

| Field | Value |
|-------|-------|
| mode | `none` \| `read_only` \| `named_services_only` \| `existing_tunnel_only` \| `bounded_external_write` |
| allowed_services | *(if named_services_only / bounded)* |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` \| `read_only_named` \| `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005).

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| todo-01-baseline-preflight | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| todo-02-mutate | `filesystem_mutation` | `safe_with_dedupe` \| `unsafe_blind_repeat` \| `non_idempotent` | `manual_only` \| `retry_once` \| `bounded_retry` | restore scoped paths / revert | false |
| todo-03-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |
| todo-04-converge | `network_write` \| `none` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

`side_effects` ∈ `none` \| `filesystem_read` \| `filesystem_mutation` \| `destructive_filesystem_mutation` \| `network_read` \| `network_write` \| `database_read` \| `database_write` \| `external_state_mutation` \| `human_approval`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| todo-02-mutate | e.g. memory / ops / adapters | `control_plane` \| `data_plane` \| `chassis` \| `ops` \| `runtime` \| `policy` \| `assurance` \| `memory` \| `graph` \| `docs` \| `external_system` | ADR / schema / skill that owns it | redesign X; touch Y; invent Z |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.<plan_id>` |
| source_execution_ref | this plan_id |
| supported | `true` \| `false` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` \| `revert_commit` \| `none` | scoped to write_allow |
| data | `none` \| `restore_snapshot` \| `compensating_transaction` \| `manual_recovery` | |
| external_state | `none` \| `corrective_append_only_record` \| `manual_recovery` | never claim false reversibility |
| local_state | `none` \| `git_restore_scoped_paths` \| `manual_recovery` | |

### Irreversible operations

- *(enumerate; PLAN-SCHEMA-010)* none | …

### Rollback verification

- command / proof that rollback restored invariants

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` \| `medium` \| `high` \| `critical` |
| uncertainty | `low` \| `medium` \| `high` \| `critical` |
| blast_radius | `low` \| `medium` \| `high` \| `critical` |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `0` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | |
| categories | `delete` \| `migrate_then_delete` \| `keep` \| `replace` \| `skip` |
| checksum_required | `true` |
| destructive_gate_required_for | `migrate_then_delete` |

## Gated write pipeline *(optional — irreversible or external writes)*

- **gates (ordered):** …
- **dedupe_before_non_idempotent_write:** `true`
- **bounded_write_count:**
- **receipt_required:** `true`

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| RG-01 | regenerator path / script | disable or retarget | prove artifact not recreated |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.<plan_id>` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| todo-01-baseline-preflight | agent | assurance | [] | baseline_receipt, preflight_receipt |
| todo-02-mutate | agent | *(layer)* | [todo-01-baseline-preflight] | mutated paths |
| todo-03-prove | agent | assurance | [todo-02-mutate] | validation_evidence refs |
| todo-04-converge | agent | control_plane | [todo-03-prove] | convergence receipt / PR |

**Critical path:** `todo-01-baseline-preflight` → `todo-02-mutate` → `todo-03-prove` → `todo-04-converge`

**Forbidden edges:** *(none, or list cycles / illegal orderings)*

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | locked SHA | `not_run` |
| EV-SP-02 | SP-02 | `property_evidence` \| `structural_evidence` \| `runtime_behavior_evidence` | … | … | marker / structure | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | catalog | `.pre-commit-config.yaml` | catalog named | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Assumption A false → …
- Probe/environment differs from baseline capture → …

### Assumption failure conditions

- Dirty tree overlaps `write_allow` under `stop_if_dirty_overlaps_may_modify`
- Blocking success property fails after mutation
- Unknown dependency discovered mid-flight (PLAN-SCHEMA-013)

### Blast radius notes

- …

### Rollback constraints

- No force-push / history rewrite
- External append-only systems → compensating record only

## Out of scope

- Adjacent features / refactors not listed in envelope
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | … | … |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.<plan_id>` |
| source_ref | this plan_id |
| current_state | `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `false` until preflight + DAG + envelope filled |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking SP-* evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** `EV-SP-01`, `EV-SP-02`, `EV-SP-03`
- **observed_evidence_refs:** *(fill during execution)*
- **missing_evidence:** *(fill)*

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | | | |
| unknown | U1 | | ask / measure / lock — do not infer away |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build** and work in the current checkout — do not free-form execute |
| execute_via | Cursor Build on the current checkout |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.domain.slug.v1
  name: Short plan title
  overview: "…"
  status: draft
  is_project: false
  created_at: YYYY-MM-DD
architect_framing:
  planning_ssot: …
  plan_class: bounded_execution_contract
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: org/repo
  commit_sha: REPLACE_WITH_FULL_SHA
  dirty: false
  artifact_hashes: {}
  overlap_policy: stop_if_dirty_overlaps_may_modify
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: …
  success_properties:
    - id: SP-01
      property: …
      evidence_type: repository_state
      proof: …
      blocking: true
capability_preflight_ref: preflight.plan.domain.slug.v1
execution_envelope:
  filesystem:
    write_allow: []
    write_deny: []
  commands:
    allow: []
    deny: []
  network:
    mode: none
  secrets:
    access: none
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: rollback.plan.domain.slug.v1
complexity_and_uncertainty:
  complexity: low
  uncertainty: low
  blast_radius: low
  architectural_boundaries_crossed: 0
  external_systems_touched: 0
  migration_required: false
  unknown_dependency_count: 0
dependency_topology_ref: dag.plan.domain.slug.v1
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: conv.plan.domain.slug.v1
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: current checkout
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: todo-01-baseline-preflight
    content: …
    status: pending
```
