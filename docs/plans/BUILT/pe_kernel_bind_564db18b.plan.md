---
name: Bind AI control-plane kernels onto PE campaign transitions
overview: Bind the AI coding control-plane kernels, Gold Nugget Extractor, Diagnose First, Preflight 2, and harvested wiring taxonomy onto existing make-campaign transitions so the runner refuses stub seeds, verifies with honest PASS/FAIL/INCOMPLETE including wiring, repairs on the same task, and completes only on Definition of Done — without a second front door, new runner stage, or kernel YAML dumps.
todos:
  - id: T00
    content: Create a new Cursor-Governance branch from origin/main in a gov-worktree isolate. Bind the full SHA. If default_context7_stack is absent on that tip, rebase onto feat/pe-context7-stack so stack-proof is present. Do not write the dirty primary. Do not write l9-ci-core.
    status: completed
  - id: T01
    content: Create the PE projection adapter. Encode authority_order, task ceiling CommitReady, dropped modes deploy/publish/Greenfield/Release-depth, output projection onto CAMPAIGN_SOURCE fields, and the wiring taxonomy harvested from Validate & Repair. Do not load Validate & Repair as a kernel. Do not rewrite the seven doctrine files.
    status: completed
  - id: T02
    content: Add named campaign-source properties and refuse stub compile. Map plan_status Ready or ConditionallyReady to program.definition_status ready. Do not invent actions when the seed is empty.
    status: completed
  - id: T03
    content: Insert the PLAN window inside activate after stack-proof and before compile_activation. Emit nuggets.json. Refuse seal unless plan_status is Ready or ConditionallyReady. No new UNTIL_STAGE.
    status: completed
  - id: T04
    content: verify_attempt writes kernel_verdict PASS|FAIL|INCOMPLETE. Missing command is INCOMPLETE. Inspection file presence is not runtime PASS. Preflight 2 when validation[] has commands. Wiring inventory gate.
    status: completed
  - id: T05
    content: Require the seven PE-mandatory DoD gates before evaluate-gate PASS and before complete_task. PASSED_LOCAL is not Done. Task ceiling stays CommitReady.
    status: completed
  - id: T06
    content: Carry kernel_profile on the Rendered Contract. CHANGE only on kernel_verdict FAIL with Diagnose First. INCOMPLETE does not enter CHANGE.
    status: completed
  - id: T07
    content: Regression tests, activate docs, PE MANIFEST sync, make pr-check on the factory branch.
    status: completed
isProject: false
---

# PLAN: Bind AI control-plane kernels onto PE campaign transitions

> **Projected from** validated PLAN_DOCUMENT `~/.cursor/plans/pe_kernel_bind.plan.json` (validator PASS).
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Schema:** `canonical.schema.plan_document.v1` · status `draft` (not `executable` until T00 re-probes UNK-001/UNK-002)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.

## Execute via @environment/program-execution + autonomy (required)

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

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease. Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile scripts from this plan.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` projects the plan into Blueprint artifacts under `$HOME/.l9/programs/<id>/`, admits the lock, executes every task, stacks PRs, and closes into `campaigns/COMPLETED/<id>/`. Never mutate sealed `environment/program-execution/core/` templates in place on a live program.

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

If the runner exits nonzero, stop and report. Do not continue with `pec.py bootstrap`, `claim`, `record-attempt`, or a second scheduler.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-github-actions` / `ci-generic-shell` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-2026-08-16-pe-kernel-bind
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: /Users/macm2/.cursor/plans/pe_kernel_bind_564db18b.plan.md
plan_id: plan.pe.kernel-bind.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-pe-kernel-bind
  provider_ref: cursor-foreground
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [feat/pe-kernel-bind]
allowed_inside_packet:
  - execute_rendered_contract_only
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
  - direct_graphiti_task_claim
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| T00 | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.task001` | `work` | `cursor-foreground` |
| T01 | TASK-002 | W1 | [T00] | true | `path:environment/program-execution/adapters/` | `mutate` | `pes.w1.task002` | `work` | routed |
| T02 | TASK-003 | W1 | [T01] | true | `path:campaign-source.schema.json` `path:compile_activation_files.py` | `mutate` | `pes.w1.task003` | `work` | routed |
| T03 | TASK-004 | W1 | [T02] | true | `path:run_campaign.py` `path:extract_nuggets.py` | `mutate` | `pes.w1.task004` | `work` | routed |
| T04 | TASK-005 | W1 | [T02] | true | `path:controller.py` `path:verification-receipt.schema.json` | `mutate` | `pes.w1.task005` | `work` | routed |
| T05 | TASK-006 | W1 | [T04] | true | `path:controller.py` | `mutate` | `pes.w1.task006` | `work` | routed |
| T06 | TASK-007 | W1 | [T04, T05] | true | `path:contracts.py` `path:run_campaign.py` | `mutate` | `pes.w1.task007` | `work` | routed |
| T07 | TASK-008 | W2 | [T03, T06] | true | `path:SKILL.md` `path:MANIFEST.json` | `validate` | `pes.w2.task008` | `work` | `ci-*` / foreground |

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint not accepted / Controller not bootstrapped; Program Lock drift; capability preflight blocked; DAG cyclic; envelope or Task Card ceiling incomplete; blocking unknowns remain; autonomy revoke / lease expired.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.pe.kernel-bind.v1` |
| name | Bind AI control-plane kernels onto PE campaign transitions |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | Igor Beylin |
| created_at | `2026-08-16` |
| updated_at | `2026-08-16` |
| depth | `deep` |
| machine_artifact | `~/.cursor/plans/pe_kernel_bind.plan.json` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | Cursor-Governance PE + l9-ci-core kernel doctrine (read-only) |
| plan_class | `integration_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Kernels **project** onto PE objects. PE **refuses stubs**. No new runner stage. No standalone kernel YAML dumps. No eighth Core workflow. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-16T18:08:00-04:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `$HOME/.l9/gov-worktrees/<new-isolate>` at execute |
| ssot_clone | do not write `~/.cursor-governance` (dirty primary @ `389b030`) |
| branch | `feat/pe-kernel-bind` (new from `origin/main`; rebase onto `feat/pe-context7-stack` if stack-proof is absent) |
| commit_sha | `389b03009b33f614d0b346c8f878d842cbbdc89f` (`origin/main`) |
| context7_tip | `feat/pe-context7-stack` @ `1960722` (ahead 2; consume, do not rebuild) |
| factory_fill_tip | `feat/pipeline-assembly-fill` @ `24ee3ab` (separate PR; do not merge into this plan) |
| l9_ci_core_tip | `373bb6d26084e67ef76aaab95021364182a34ee7` on `main` (read-only; dirty `AGENTS.md` local) |
| dirty | primary `true`; this plan writes only a new isolate |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

`make campaign` today compiles hollow tasks (`implement_task_00n`, title-plus-locally-verified acceptance, empty `validation_commands`) and pec verify treats missing commands as file-exists PASS (`PASSED_LOCAL`). Kernels exist as doctrine and are not consumed. Bind PLAN, VALIDATION, CHANGE, DoD, and RELEASE onto the existing transitions so a campaign cannot seal a stub, cannot pass a missing command, cannot CHANGE an INCOMPLETE task, and cannot complete without DoD.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Stub seed refused before integrity receipt | `runtime_behavior` | compile exits nonzero; no `source-integrity-receipt.json` | true |
| SP-02 | `plan_status` not in `{Ready, ConditionallyReady}` leaves source unsealed | `runtime_behavior` | compile_activation nonzero; no seal | true |
| SP-03 | `kernel_verdict` is `PASS\|FAIL\|INCOMPLETE`; missing command is INCOMPLETE; inspection ≠ runtime PASS | `structural` | verification receipt field + unit test | true |
| SP-04 | CHANGE only on `kernel_verdict==FAIL`; Diagnose First enforced | `runtime_behavior` | INCOMPLETE skip test; FAIL re-verify test | true |
| SP-05 | DoD seven gates required for evaluate-gate PASS and complete | `runtime_behavior` | `PASSED_LOCAL` alone does not complete | true |
| SP-06 | Rendered Contract carries `kernel_profile`; merge/deploy stay false | `structural` | contracts.py field set + ceiling | true |
| SP-07 | `nuggets.json` primed-only; every ready task has `nugget_id`; stack nuggets cite `stack-proof.json` | `filesystem` | primed path exists; campaign dir still two git files | true |
| SP-08 | No new UNTIL_STAGE; no eighth Core workflow; `make pr-check` PASS | `quality_gate` | `make pr-check` PASS | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.pe.kernel-bind.v1` |
| blocking | `true` |
| baseline_verified | re-probe at T00 |
| drift_detected | |

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` in isolate | new branch from `389b030` or rebased context7 tip | true |
| CP-02 | `stack_proof_hook` | `default_context7_stack` present in `run_campaign.py` | function exists; no live skip env | true |
| CP-03 | `write_root` | isolate ≠ `~/.cursor-governance` | `refuse_write_to_dirty_primary` still holds | true |
| CP-04 | `sibling_plans` | inventory GAP vs kernel bind | this PR does not close GAP-001..032 | true |

## Execution envelope

### Filesystem

- **write_allow:** `environment/program-execution/adapters/**`, `environment/program-execution/core/shared/schemas/campaign-source.schema.json`, `environment/program-execution/core/program-execution-controller-template/schemas/verification-receipt.schema.json`, `environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py`, `environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py`, `environment/program-execution/core/program-execution-controller-template/scripts/tests/**`, `environment/program-execution/scripts/run_campaign.py`, `environment/program-execution/scripts/tests/test_run_campaign.py`, `environment/program-execution/MANIFEST.json`, `skills/l9-pe-campaign-activate/scripts/**`, `skills/l9-pe-campaign-activate/SKILL.md`, `skills/l9-pe-campaign-activate/references/pipeline.md`, `skills/l9-pe-campaign-activate/references/file-set.md`, `Makefile` (append-only)
- **write_deny:** `~/.cursor-governance` primary, `l9-ci-core` product/workflows/`MANIFEST.sha256`, seven kernel doctrine files, live `campaigns/<id>/`, `PHASE0_USER_CONFIG.yaml` ack, `ops/scripts/stack_pr.py` main fallback, pipeline-assembly-fill GAP audit closes

### Commands

- **allow:** `python3 -m unittest discover …`, `make pr-check`, `sync_generated_artifacts --force`, scoped git commit on `feat/pe-kernel-bind`
- **deny:** force-push, hard-reset, admin-merge, `PR_BASE=main`, forge Phase 0 ack, live skip env for Context7

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | GitHub for the factory PR after L4 release_authorized |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`. Merge only after PE verify/handoff + `@autonomy` join on this L4 plan/PE stack, green+mergeable.

## Locked bind (do not re-open)

```text
brief → seed → Context7 stack-proof → nuggets → PLAN Ready|ConditionallyReady → compile+receipt
                activate (no new stage)
```

| Kernel | PE insert | Law |
|--------|-----------|-----|
| PLAN | `activate → blueprint` before integrity receipt | `plan_status ∈ {Ready, ConditionallyReady}` or no seal. PLAN output **is** `CAMPAIGN_SOURCE.yaml`. |
| Gold Nugget Extractor | inside PLAN, beside Context7 | `$HOME/.l9/primed/<id>/nuggets.json`. Every ready task has `nugget_id`. Tool/stack nuggets cite `stack-proof.json`. No 16-section essay. |
| VALIDATION + Preflight 2 | `pec verify_attempt` | Receipt `kernel_verdict ∈ {PASS, FAIL, INCOMPLETE}`. Missing command = INCOMPLETE. Inspection ≠ runtime. Preflight 2 when `validation[]` has commands. Wiring inventory gate. |
| CHANGE + Diagnose First | `kernel_verdict==FAIL` on the **same** task | INCOMPLETE does not enter CHANGE. Refuse mutate-before-diagnosis. Revalidate before next execute. One polish pass. |
| DoD | `evaluate-gate` then `pec complete` | Seven gates. `PASSED_LOCAL` ≠ Done. Ceiling `CommitReady`. |
| RELEASE | existing `pr / merge / close` | No deploy. Pre-flight PR-order/freshness only. |
| AUDIT | existing admit `EVID-001` | Recursive Alignment folded into adapter; not a new profile. |
| BUILD | worker **mode** via `kernel_profile` | Not a runner stage. |
| WIRING | PLAN fields + verify inventory | Harvest taxonomy from Validate & Repair. Do not load that file as a kernel. |
| Validate & Repair / Recursive Leverage | **out** | Do not load as profiles. |

### Enum map

| Kernel | PE object |
|--------|-----------|
| PLAN Ready / ConditionallyReady | `program.definition_status: ready` |
| VALIDATION PASS | `kernel_verdict=PASS` → pec `PASSED_LOCAL` |
| VALIDATION FAIL | `kernel_verdict=FAIL` → pec `FAILED` → CHANGE |
| VALIDATION INCOMPLETE | `kernel_verdict=INCOMPLETE` → pec `FAILED` + CHANGE skip |
| CHANGE Succeeded | re-verify |
| DoD Done | evaluate-gate PASS + complete |
| RELEASE MergeReady | authorize + merge (not this task ceiling) |

### Schema fields (named; schema const stays `l9.program-execution.campaign-source.v2`)

`plan_status`, `consumers[]`, `entrypoints[]`, `validation[]`, `kernel_profile` (`BUILD\|CHANGE\|AUDIT`), `nugget_id`

`campaign-source.schema.json` already has `additionalProperties: true` on tasks. Named properties plus compile refuse are the enforcement. `verification-receipt.schema.json` is closed (`additionalProperties: false`) — T04 adds `kernel_verdict` and `INCOMPLETE` on gates. `contracts.py` rejects unknown source-contract fields — T06 adds `kernel_profile` to the allowed set.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T00 | `filesystem_read` | `safe_to_repeat` | `none` | abandon isolate | false |
| T01 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | delete adapter file | false |
| T02 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert compile/schema | false |
| T03 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert run_campaign insert | false |
| T04 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert verify + receipt schema | false |
| T05 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert complete/DoD | false |
| T06 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | revert CHANGE dispatcher | false |
| T07 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert docs/MANIFEST | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T01–T07 | program-execution | `control_plane` | PE campaign-source v2 + pec verification-receipt v2 | new UNTIL_STAGE; second executor; kernel doctrine rewrite; eighth Core workflow; deploy |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.pe.kernel-bind.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; INCOMPLETE treated as CHANGE; stub compile still seals; envelope breach |

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | drop the factory isolate branch; do not revert `origin/main`, `feat/pe-context7-stack`, or `feat/pipeline-assembly-fill` |
| data | `none` | |
| external_state | `none` | no live campaign launch |
| local_state | `manual_recovery` | primed `nuggets.json` is runtime-only and dies with the campaign id |

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `1` (kernel doctrine → PE consume) |
| external_systems_touched | `0` (GitHub only at PR) |
| migration_required | `false` |
| unknown_dependency_count | `2` |

## Execution DAG

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.pe.kernel-bind.v1` |
| graph_type | `directed_acyclic_graph` |

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T00 | agent | assurance | [] | isolate SHA, stack-proof present |
| T01 | agent | policy | [T00] | `ai-control-plane.project-policy.yaml` |
| T02 | agent | control_plane | [T01] | named schema fields; refuse-stub compile |
| T03 | agent | control_plane | [T02] | PLAN window; `nuggets.json` |
| T04 | agent | assurance | [T02] | `kernel_verdict` on receipt |
| T05 | agent | assurance | [T04] | DoD on evaluate-gate/complete |
| T06 | agent | control_plane | [T04, T05] | `kernel_profile` on contract; Diagnose First |
| T07 | agent | docs | [T03, T06] | tests, docs, MANIFEST, `make pr-check` |

**Critical path:** T00 → T01 → T02 → T03 → T04 → T05 → T06 → T07

**Leverage order:** T02 → T01 → T04 → T05 → T03 → T06 → T07 → T00

**Forbidden edges:** PLAN window before refuse-stub; CHANGE before `kernel_verdict`; complete before DoD; new UNTIL_STAGE.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `runtime_behavior_evidence` | stub seed compile | unittest compile_activation | nonzero; no receipt | `not_run` |
| EV-SP-02 | SP-02 | `runtime_behavior_evidence` | plan_status refuse | unittest compile_activation | unsealed | `not_run` |
| EV-SP-03 | SP-03 | `structural_evidence` | verify_attempt | unittest pec | `kernel_verdict=INCOMPLETE` | `not_run` |
| EV-SP-04 | SP-04 | `runtime_behavior_evidence` | CHANGE dispatcher | unittest run_campaign | INCOMPLETE skip | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | complete_task | unittest pec | DoD required | `not_run` |
| EV-SP-06 | SP-06 | `structural_evidence` | contracts.py | unittest pec | `kernel_profile` allowed | `not_run` |
| EV-SP-07 | SP-07 | `filesystem` | primed nuggets | unittest extract_nuggets | path + citation | `not_run` |
| EV-SP-08 | SP-08 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Factory-fill GAP-032 already treats empty `validation_commands` plus a present output file as `PASSED_LOCAL` → this bind must keep INCOMPLETE and win on rebase.
- `feat/pe-context7-stack` not merged → T00 rebases onto that tip; do not rebuild stack-proof.
- `kernel_verdict` stored only in `last_error` → future execute loop treats pec FAILED as CHANGE. Receipt field is mandatory.
- PLAN fills actions from the brief title alone → hollow prose replaces `implement_task_*`. Refuse that class too.
- `additionalProperties: true` plus forgotten compile checks → hand-edited source skips `nugget_id` and still seals. Compile refuse is the gate.

### Assumption failure conditions

- Dirty primary overlaps `write_allow`
- Sibling factory-fill PR lands overlapping compile/verify edits
- `default_context7_stack` missing on the execute tip

### Blast radius notes

Cursor-Governance PE compile, pec verify/complete, and `run_campaign` activate/execute. A wrong INCOMPLETE→CHANGE map mutates incomplete work. A wrong refuse-stub map blocks every live campaign. Kernel doctrine in l9-ci-core is out of blast if the adapter stays PE-owned.

### Rollback constraints

- No force-push / history rewrite
- Drop the isolate branch only
- Primed `nuggets.json` is not a git file

## Out of scope

- l9-ci-core product, workflows, `MANIFEST.sha256`
- Rewriting the seven kernel doctrine files
- Loading Validate & Repair or Recursive Leverage as profiles
- Dirty `~/.cursor-governance` primary
- pipeline-assembly-fill GAP-001..032
- Rebuilding Context7 stack-proof
- PE- Memory.md / document-class live launch
- New `UNTIL_STAGE` or second executor
- Third campaign git file; `VALIDATION_EVIDENCE.md` in campaign dir
- Ceremonial pass counts / seven-pass Improve
- Deploy / publish / Greenfield / Release-depth
- `PR_BASE=main`; Phase 0 ack forge; eighth Core workflow

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | pipeline-assembly-fill GAP-001..032 | repairs the tunnel (stack, execute loop, close). This plan repairs work **inside** the tunnel. Sequential PRs. |
| P2 | Optional KERNEL-pack copy of the adapter next to doctrine in l9-ci-core | PE-owned adapter is sufficient for consume. |

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.pe.kernel-bind.v1` |
| current_state | `partial` |
| implementation_ready | `false` until T00 re-probes UNK-001/UNK-002 and status is `executable` |
| remaining_unknown_ids | `UNK-001`, `UNK-002` |
| next_skill | `l9-ynp` |
| stop_reason | PLAN_DOCUMENT validates. Pre/final validation pending until execute. Do not implement from this markdown alone. |

### Unknowns (accept_bounded)

| id | question | execute rule |
|----|----------|--------------|
| UNK-001 | Are `feat/pe-context7-stack` commits on `origin/main`? | If absent, rebase the new branch onto that tip. Do not rebuild stack-proof. |
| UNK-002 | Has factory-fill already changed stub fill or empty-command PASS? | Keep refuse-stub and INCOMPLETE. Rebase. Do not merge the two plans into one PR. |

## GMP / PE handoff

**may_modify:** PE adapter, campaign-source schema, verification-receipt schema, `controller.py`, `contracts.py`, pec tests, `run_campaign.py`, activate compile/nugget scripts and tests, activate SKILL.md / pipeline.md / file-set.md, PE `MANIFEST.json`, Makefile append-only.

**must_not_modify:** l9-ci-core product/workflows, seven kernel doctrine files, dirty primary, pipeline-assembly-fill GAP audit closes, live campaigns, Phase 0 ack, `stack_pr.py` main fallback.

**preserved_contracts:** one front door; frozen UNTIL_STAGES; two-file campaign allowlist; Core→SDK one-way; seven workflows; stack-proof before emit; merge/deploy false on cards; `autonomous_merge: false`.

## Handoff

1. Next skill: **l9-ynp** (highest-leverage next action).
2. Execute path: `@environment/program-execution` → Program Lock/Controller → `/autonomy` under Program lease.
3. Do not start implementation from this markdown.
4. Optional GMP Phase 0 only if the operator chains `l9-gmp-protocol`.
