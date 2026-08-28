---
name: Compile harvestable plan components into GMP Compiled plans
overview: "Replace the binary plan-shelf verdict with a per-component classifier so a stale or superseded mission can still donate live invariants. Harvest those invariants without implementation, consolidate them by concern, and emit compiled plans that execute via /gmp. Do not use Program Execution to fix Program Execution."
todos:
  - id: todo-01-baseline-preflight
    content: "Cut a wired worktree from fetched origin/main, lock that full SHA, copy this plan onto the branch, and re-run CP-01..CP-04. Stop and replan on SHA drift. Do not execute on the dirty primary checkout."
    status: cancelled
    phase: execute
    depends_on: []
  - id: todo-02-component-verdict-law
    content: "Write the component-verdict contract: live_invariant, stale_wiring, superseded_mission, spent. A mixed plan stays harvestable. compiled: true is a live PE tag, not a built skip. Donors use status: superseded plus compiled_into after harvest."
    status: completed
    phase: execute
    depends_on: [todo-01-baseline-preflight]
  - id: todo-03-classifier-emit
    content: "Extend audit_plans.py to emit per-component verdicts and a harvestable count without moving files. SessionStart stays display-only and fail-open. Keep the PyYAML fallback and Do **not** run make-campaign prohibition. Add mixed-verdict fixtures to self_test.py."
    status: completed
    phase: execute
    depends_on: [todo-02-component-verdict-law]
  - id: todo-04-audit-plans-harvest-step
    content: "Add a harvest-candidate report to /l9-audit-plans after the live-queue scan. It lists harvestable components by concern. It must not auto-Build, auto-compile, or auto-shelf a mixed plan as superseded."
    status: completed
    phase: execute
    depends_on: [todo-03-classifier-emit]
  - id: todo-05-harvest-invariants
    content: "Add harvest_plan_invariants.py that reads Gold Nugget Extractor by path and writes invariants-only receipts grouped by concern. No implementation code. No l9-harvest-pipeline. No new l9-intelligence-harvest skill. Fail closed if a receipt contains code fences destined for deploy."
    status: completed
    phase: execute
    depends_on: [todo-03-classifier-emit]
  - id: todo-06-gar-compile-by-concern
    content: "Explicitly boot l9-global-architect in STANDALONE mode, load runtime/MANIFEST.yaml in load_order, and compile harvest receipts into one concern map. Repository presence must not flip GAR into PE-integrated mode. Output is a concern bundle, not product code."
    status: cancelled
    phase: execute
    depends_on: [todo-05-harvest-invariants]
  - id: todo-07-emit-compiled-pe-plans
    content: "For each concern bundle, run l9-plan (not l9-plan-simple): validate_plan_document.py PASS, render_plan_pe_autonomy.py --execute-via pe-campaign, kernel receipt PASS. Frontmatter compiled: true, kind: pe. Stamp donor compiled_into. Land compiled plans at docs/plans root."
    status: completed
    phase: execute
    depends_on: [todo-06-gar-compile-by-concern]
  - id: todo-08-rewire-stale-pe
    content: "On each compiled plan, replace stale PE wires: restore a live Execute via @environment/program-execution heading, bind Program Lock and Controller lease, and remove leftover Cursor-Build-only execute paths. Keep Do not run make campaign only as a prohibition on simple leftovers, not as the execute path."
    status: cancelled
    phase: execute
    depends_on: [todo-07-emit-compiled-pe-plans]
  - id: todo-09-e2e-conformance
    content: "Prove each compiled concern on the execute worktree: make program-execution-conformance, then the campaign probe named by that plan. Fail closed on empty commands or inspection-only compiled tasks."
    status: cancelled
    phase: execute
    depends_on: [todo-08-rewire-stale-pe]
  - id: todo-10-converge
    content: "Run l9-plan-audit self_test and harvest extractor tests, make pr-check on the changed set, then PR_REMEDIATE=0 make pr. Do not merge. Write Graphiti PICKUP for the compiled cohort."
    status: cancelled
    phase: execute
    depends_on: [todo-04-audit-plans-harvest-step, todo-09-e2e-conformance]
isProject: false
kind: simple
execute_via: gmp
kernel_pass:
  bound_path: plan_component_compile_8-28-26.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-28T19:20:00Z
    body_sha256: "dbb999587b86756efb9e7714709428b59aebd43d2b89687406f4708612f4573e"
    deltas:
      - "User override: execute this compile via /gmp, not Program Execution"
      - "Neutralized the live make campaign command and PE execute heading"
      - "Cancelled PE worktree, GAR-integrated boot, PE rewire, and campaign-conformance todos"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-28T19:21:00Z
    body_sha256: "dbb999587b86756efb9e7714709428b59aebd43d2b89687406f4708612f4573e"
    deltas:
      - "compiled packets are kind:simple / execute_via:gmp; donors carry compiled_into only"
      - "Harvest CLI refuses implementation fences; first pe-loop packet emitted"
      - "Stamped kernel_pass after Improve then Validate and Repair"
---

# PLAN: Compile harvestable plan components into GMP Compiled plans

> **GMP override 2026-08-28:** execute this compile via `/gmp`. Do **not** run `make campaign`. Do not admit a Program Lock. Compiled packets are `kind: simple` / `execute_via: gmp`.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Suggested filename:** `plan_component_compile_8-28-26.plan.md`

## Objective (from PLAN_DOCUMENT)

Replace the binary plan-shelf verdict with a per-component classifier so a stale or superseded mission can still donate live invariants. Harvest those invariants without implementation, have Global Architect consolidate them by concern, and emit new PE-wired plans tagged compiled that rewire stale Program Execution wires and prove them with conformance plus e2e.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Classifier output names each scanned component as live_invariant, stale_wiring, superseded_mission, or spent, and a plan with mixed verdicts is not forced into a single built or superseded shelf. | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | Harvest writes an invariants-only receipt: no implementation files, no sed/cp deploy through l9-harvest-pipeline, and every invariant cites a source plan path plus a concern id. | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | A compiled plan is a new artifact with compiled: true, kind: simple, execute_via: gmp, and is not marked status: superseded. | quality_gate | observe during /gmp validate | true |
| SP-04 | Donor plans that were harvested gain compiled_into pointing at the compiled plan; they are not whole-file superseded. SessionStart still lists mixed donors as unbuilt until spent. | quality_gate | observe during /gmp validate | true |
| SP-05 | Compiled plans execute via /gmp. They must not carry a live Execute via @environment/program-execution heading or an unnegated make campaign as the execute path. | quality_gate | observe during /gmp validate | true |
| SP-06 | make program-execution-conformance and the campaign probe targeted by the compiled plan PASS on the execute worktree. | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | make pr-check PASS on the changed-file set; PR_REMEDIATE=0 make pr opens or updates one PR; no merge. | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** skills/l9-plan-audit/scripts/audit_plans.py — component verdicts plus harvestable report, skills/l9-plan-audit/scripts/self_test.py — mixed-verdict and compiled-tag fixtures, skills/l9-plan-audit/references/staleness-rules.md — component law, skills/l9-plan-audit/scripts/harvest_plan_invariants.py — new invariants-only extractor citing kernels/Gold Nugget Extractor by path, commands/l9-audit-plans.md — harvest-candidate step; still no auto-Build and no auto-compile, docs/plans/README.md — compiled tag, donor compiled_into, no new pe/ci/date folder, Explicit l9-global-architect invocation to consolidate harvest receipts by concern, l9-plan PE projection of each compiled plan (not l9-plan-simple), PE rewire of stale wires on those compiled plans, then program-execution-conformance plus campaign probe, First compile cohort: current root PE-kind plans flagged kernel_unfired or missing_execute_section, plus parked donors that still hold invariants

**Out:**
- Creating or compiling skills/l9-intelligence-harvest — compiler qualification BLOCKED; source kernel lacks activation surface
- Using skills/l9-harvest-pipeline sed/cp deploy on plan markdown
- Do not run make campaign from sessionStart Plan audit, and do not auto-Build
- Treating compiled: true as a built skip the way built/superseded/cancelled are skipped
- A compiled/ folder or pe/ci/date shelves
- Rewriting kernels/Gold Nugget Extractor or kernels/Improve.md / Validate & Repair.md
- Consumer repo product code, l9-ci-core tag cuts, Quantum-L9/.github seeder work
- Merging the resulting PR
- Mass-executing every backlog plan in one campaign

## Critical path (seed)

todo-01-baseline-preflight → todo-02-component-verdict-law → todo-03-classifier-emit → todo-05-harvest-invariants → todo-06-gar-compile-by-concern → todo-07-emit-compiled-pe-plans → todo-08-rewire-stale-pe → todo-09-e2e-conformance → todo-10-converge

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Wrong skip rules hide the live queue. Wrong harvest owner deploys plan prose as code. Wrong GAR mode widens execution authority. Stale PE wires in compiled plans recreate the kernel_unfired and missing_execute_section noise this campaign exists to retire.
- Rollback: Revert the classifier and command edits; leave donor plans where they were; delete compiled plans that have no PE conformance PASS; do not delete harvest receipts already cited by a compiled_into pointer until the donor restore is committed.

## Convergence (seed)

- status: partial
- next_skill: l9-pe-campaign-activate
- stop_reason: PLAN_DOCUMENT is the compile contract. Execution starts on a new origin/main worktree via Program Execution, not on this dirty main checkout. U2 is a probe inside todo-01.
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: Compile harvestable plan components into PE Compiled plans

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via GMP (required)

Historical PE projection below is not the live execute path. Do **not** run `make campaign`.

**Authority order (fail-closed — see `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md  (intent / envelope / DAG / success properties)
        │ project
        ▼
@environment/program-execution   HOW work executes (authoritative)
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act?  (packet, lanes, PR poll) — owns_program_state: false
        │
        ▼
Peer Execution Core -> thin provider
  (Cursor: cursor-foreground | cursor-background;
   Claude: claude-code-direct)
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease (`COMPATIBILITY.yaml` / autonomy-control-plane bridge). Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile
scripts from this template.

```bash
# Do not run `make campaign`. This compile executed via /gmp.
```

`run_campaign.py` projects the plan into Blueprint artifacts under
`$HOME/.l9/programs/<id>/`, admits the lock, executes every task, stacks
PRs, and closes into `campaigns/COMPLETED/<id>/`. Never mutate sealed
`environment/program-execution/core/` templates in place.

| Plan section | Runner-owned Blueprint / Controller artifact |
|--------------|-------------------------------------|
| metadata / objective | `PROGRAM.yaml` / program identity |
| immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA |
| execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
| execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
| capability_preflight | Controller reconcile + gate probes before claim |
| property_evidence_matrix | Task Card `validation` / evidence catalog refs |
| rollback | Task Card `rollback` + recovery receipts |
| convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

If the runner exits nonzero, stop and report. Do not continue with
`pec.py bootstrap`, `claim`, `record-attempt`, or a second scheduler.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-github-actions` / `ci-generic-shell` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-<YYYY-MM-DD>-<n>
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence            # or program_deploy_max_autonomy when PES Phase-0 selects it
authority_profile: program_controller_bound
autonomous_merge: false            # COMPATIBILITY forbidden; L4 plan/PE stack merge after green+mergeable
plan_ref: <this .plan.md path>
plan_id: plan.<domain>.<slug>.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-<slug>
  program_lock_digest: <sha256 from Controller>
  blueprint_ref: $HOME/.l9/programs/<program_id>/blueprint
  runtime_ref: $HOME/.l9/programs/<program_id>/runtime
  provider_ref: cursor-foreground  # or routed thin provider
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [<feature-branch>]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch   # only after L4 release_authorized
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
  - direct_graphiti_task_claim
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

Derive from frontmatter todos + `execution_DAG`. Each row is both an autonomy action and a PE Task Card projection.

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| todo-01-baseline-preflight | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.task001` | `work` | `cursor-foreground` |
| todo-02-mutate | TASK-002 | W1 | [todo-01-baseline-preflight] | true | `path:<write_allow…>` | `mutate` | `pes.w1.task002` | `work` | routed |
| todo-03-prove | TASK-003 | W1 | [todo-02-mutate] | false | `evidence:<plan_id>` | `validate` | `pes.w1.task003` | `work` | `ci-*` / foreground |
| todo-04-converge | TASK-004 | W2 | [todo-03-prove] | true | `pr:<n>` / `branch:<name>` | `converge` | `pes.w2.task004` | `work` | `github-*` + poll |
| poll-pr-N | — | W2 | [todo-04-converge] | true | `pr:<n>` | `pr:<n>` | `pes.w2.poll.pr<n>` | `poll` | background |

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A (ready `work` Tasks in one message) / B (`poll` + `run_in_background: true`) / C (join) / D (PICKUP). Autonomy must not bypass wave order or Program Lock drift checks (`program_lock_stale_or_invalid` → stop).

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint not accepted / Controller not bootstrapped; Program Lock drift; capability preflight blocked; DAG cyclic; envelope or Task Card ceiling incomplete; blocking unknowns remain; autonomy revoke / lease expired.

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
| framing_notes | Execute via @environment/program-execution + subordinate @autonomy; no redesign unless plan_class requires it |

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
| SP-03 | Quality gate / PR gate PASS on changed files | `quality_gate` | e.g. `make pr-check` → PASS | true |

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
| EV-SP-03 | SP-03 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

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
| minimum_safe_next_action | When law holds and status=`executable`, attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); project→Lock→claim→render→autonomy lanes — do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
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
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  controller: environment/program-execution/core/program-execution-controller-template
  blueprint: environment/program-execution/core/program-execution-blueprint-template
  autonomy_provider: root-autonomy-control-plane
  autonomy_integration: environment/program-execution/integrations/autonomy-control-plane
  adapter_default: cursor-foreground
  command_ref: commands/autonomy.md
  slash: /autonomy
  skill: l9-bounded-autonomy
  mention_autonomy: "@autonomy"
  authority_order:
    - plan_document
    - program_lock_and_controller
    - autonomy_packet_subordinate
    - pe_adapter_worker
todos:
  - id: todo-01-baseline-preflight
    content: …
    status: pending
```
