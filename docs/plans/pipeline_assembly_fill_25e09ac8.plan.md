---
name: Fill every PE pipeline-assembly gap from brief to COMPLETED
overview: "Close GAP-001..032 so make campaign is one autonomous line: brief → write compiled output → pec verify/complete → stacked task PRs never on main → pec plus host close → campaigns/COMPLETED. Factory is Cursor-Governance feat/pipeline-assembly-fill from 8c2932d. Do not touch l9-ci-core or the dirty primary."
todos:
  - id: T00
    content: "PE W0: cut feat/pipeline-assembly-fill from 8c2932d; commit audit only on that branch; lock UNK defaults"
    status: pending
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: T01
    content: "GAP-002: later tasks definition_status ready; wave/deps remain the serial lock"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-02]
  - id: T02
    content: "GAP-009 GAP-029: evaluate-gate on completion and W0 exit before complete and W1 claim"
    status: pending
    phase: execute
    depends_on: [T01]
    evidence_property_refs: [SP-02]
  - id: T25
    content: "GAP-032: pec verify PASS for inspection-only tasks when output files exist and validation_commands is empty"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-02, SP-09]
  - id: T03
    content: "GAP-003: claim/prepare base_sha from STACK.json predecessor tip; refuse origin/main"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-04]
  - id: T04
    content: "GAP-004: stack_pr.py and make pr read STACK.json; main fallback is a hard fail"
    status: pending
    phase: execute
    depends_on: [T03]
    evidence_property_refs: [SP-04]
  - id: T05
    content: "GAP-001 GAP-028: until=execute pec loop prepare→complete→claim next; no idle after arm"
    status: pending
    phase: execute
    depends_on: [T01, T02, T03, T25]
    evidence_property_refs: [SP-02, SP-03]
  - id: T06
    content: "GAP-025: pec next/status emit current leased task; empty ready is not idle"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-03]
  - id: T07
    content: "GAP-007 GAP-018 GAP-026: until=merge means execute-then-close; refuse host-only merge; commit emit after execute starts"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-05]
  - id: T08
    content: "GAP-016: one merge law; runner merges only PRs it opened; policy matches"
    status: pending
    phase: execute
    depends_on: [T07]
    evidence_property_refs: [SP-05]
  - id: T09
    content: "GAP-006 GAP-005 GAP-024: pec close + close_campaign.py + move to campaigns/COMPLETED; export-handoff evidence only"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-02]
  - id: T10
    content: "GAP-010: relaunch reuses in_progress id after quarantine; -v2 only if complete/cancelled"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-06]
  - id: T11
    content: "GAP-011: isolate_worktree reuse only if clean at expected branch"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-06]
  - id: T12
    content: "GAP-012 GAP-027: donor origin must match repository_id; fetch stack history; no main-only stump"
    status: pending
    phase: execute
    depends_on: [T03]
    evidence_property_refs: [SP-04]
  - id: T13
    content: "GAP-013: EVID-001 revision is reconciled target HEAD 40-char SHA"
    status: pending
    phase: execute
    depends_on: [T12]
    evidence_property_refs: [SP-06]
  - id: T14
    content: "GAP-022: quarantine blueprint + pec workspace together before compile"
    status: pending
    phase: execute
    depends_on: [T10]
    evidence_property_refs: [SP-06]
  - id: T15
    content: "GAP-015: claim TTL matches TASK_BUDGET_MINUTES (1h ceiling)"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-03]
  - id: T16
    content: "GAP-017: push campaign/<id> before PR_BASE=origin/campaign/<id>"
    status: pending
    phase: execute
    depends_on: [T07]
    evidence_property_refs: [SP-05]
  - id: T17
    content: "GAP-008: register pec abort-execution or delete the call; one executor"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-07]
  - id: T18
    content: "GAP-014 GAP-030: clear program_blockers after arm; LAUNCH.json is live SSOT"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-03]
  - id: T19
    content: "GAP-019 GAP-031: ack stays null; operator_ack_required false for T0; document admission law"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-08]
  - id: T20
    content: "GAP-020: pec bootstrap refuses pe-[0-9a-f]{8,} ids"
    status: pending
    phase: execute
    depends_on: [T00]
    evidence_property_refs: [SP-08]
  - id: T21
    content: "GAP-021: pec start refuses operator memo path as working context"
    status: pending
    phase: execute
    depends_on: [T05]
    evidence_property_refs: [SP-03]
  - id: T22
    content: "GAP-023: pipeline.md matches three trees; pec prepare worktree is the write tree"
    status: pending
    phase: execute
    depends_on: [T03, T05]
    evidence_property_refs: [SP-07]
  - id: T23
    content: "Unmocked two-task brief→COMPLETED fixture; regen MANIFEST; mark GAPs Resolved only after acceptance_test"
    status: pending
    phase: validate
    depends_on: [T01, T02, T03, T04, T05, T06, T07, T08, T09, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T25]
    evidence_property_refs: [SP-02, SP-07]
  - id: T24
    content: "make pr-check PASS; remediate without weakening scanners; stack PR on feat/campaign-tunnel"
    status: pending
    phase: converge
    depends_on: [T23]
    evidence_property_refs: [SP-07]
isProject: false
---

# PLAN: Fill every PE pipeline-assembly gap from brief to COMPLETED

> **Machine SSOT:** `/Users/macm2/.cursor/plans/pipeline_assembly_fill.plan.json` (`validate_plan_document.py` **PASS**)
> **Audit SSOT:** `$HOME/.l9/gov-worktrees/make-campaign/environment/program-execution/audits/pipeline-assembly-audit.v1.yaml` (32 findings; GAP-032 added this Improve pass)
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Schema:** `canonical.schema.plan_document.v1` + `l9-plan` `plan-document.schema.json`
> **Status:** `draft` (planning complete, implementation not started). Promote to `executable` only after T00 baseline reverify.
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Rename lock:** `pipeline_assembly_fill_25e09ac8.plan.md`

## Execute via @environment/program-execution + autonomy (required)

**Authority order (fail-closed — see Cursor-Governance `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md + pipeline_assembly_fill.plan.json
        │ project
        ▼
@environment/program-execution   HOW work executes
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act?  owns_program_state: false
        │
        ▼
Peer Execution Core -> cursor-foreground (this factory repair)
```

This plan **repairs the factory**. Do not launch a live operator campaign (`PE- Memory.md`, `l9-ci-core-org-runtime-v1`, `pe-8c9f6de43b25`) as the vehicle. Fixture campaigns in `$L9_ROOT` / `--l9-root` temp dirs only.

### Pipeline steps

1. Attach `@environment/program-execution` + `@autonomy` on **Cursor-Governance**, not l9-ci-core.
2. Project todos T00–T25 → Task Cards / waves in an instantiated program under `$HOME/.l9/programs/pipeline-assembly-fill/` (never mutate sealed blueprint templates in place; pec **controller** source is in scope because it is the bug).
3. Bootstrap Controller **without** `--admission-draft`. Reconcile the factory worktree.
4. Claim one mutation unit at a time inside the envelope. Worker receives Rendered Contract + this plan's per-todo contract below.
5. Map mutating cards to autonomy actions `pes.w0.t00` … `pes.w2.t24`.
6. L4 local commits on `feat/pipeline-assembly-fill` only. Push after `ops/autonomy/l4_local.py authorize-release`. Merge only after green+mergeable, stacked on `feat/campaign-tunnel` while PR 189 is open. `autonomous_merge: false`.
7. `record-attempt` → `verify` → export handoff. Graphiti PICKUP on close is observability only.

### Adapter routing

| Work class | Prefer |
|------------|--------|
| this factory repair | `cursor-foreground` |
| pec/unittest proof | `ci-generic-shell` / local unittest |
| remote PR | `github-remote-actions` after L4 release |

### Campaign authorization packet (fill at execute)

```yaml
packet_id: autonomy-2026-08-16-pipeline-assembly-fill
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: /Users/macm2/.cursor/plans/pipeline_assembly_fill_25e09ac8.plan.md
plan_id: plan.pe.pipeline-assembly-fill.v1
program_execution:
  root: environment/program-execution
  program_id: pipeline-assembly-fill
  provider_ref: cursor-foreground
declared_prs: []
declared_branches: [feat/pipeline-assembly-fill]
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
  - write_dirty_primary
  - edit_l9_ci_core
  - forge_phase0_ack
  - pr_base_main
  - force_push
  - launch_pe_memory
  - resume_stopped_live_campaigns
  - merge_outside_l4_plan_build_stack
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|--------------------|------|--------------|
| T00 | TASK-001 | W0 | [] | true | pes.w0.t00 | work | cursor-foreground |
| T01 | TASK-002 | W1 | [T00] | true | pes.w1.t01 | work | cursor-foreground |
| T02 | TASK-003 | W1 | [T01] | true | pes.w1.t02 | work | cursor-foreground |
| T03 | TASK-004 | W1 | [T00] | true | pes.w1.t03 | work | cursor-foreground |
| T04 | TASK-005 | W1 | [T03] | true | pes.w1.t04 | work | cursor-foreground |
| T25 | TASK-006 | W1 | [T00] | true | pes.w1.t25 | work | cursor-foreground |
| T05 | TASK-007 | W1 | [T01,T02,T03,T25] | true | pes.w1.t05 | work | cursor-foreground |
| T06 | TASK-008 | W1 | [T05] | true | pes.w1.t06 | work | cursor-foreground |
| T07 | TASK-009 | W1 | [T05] | true | pes.w1.t07 | work | cursor-foreground |
| T08 | TASK-010 | W1 | [T07] | true | pes.w1.t08 | work | cursor-foreground |
| T09 | TASK-011 | W1 | [T05] | true | pes.w1.t09 | work | cursor-foreground |
| T10 | TASK-012 | W1 | [T00] | true | pes.w1.t10 | work | cursor-foreground |
| T11 | TASK-013 | W1 | [T00] | true | pes.w1.t11 | work | cursor-foreground |
| T12 | TASK-014 | W1 | [T03] | true | pes.w1.t12 | work | cursor-foreground |
| T13 | TASK-015 | W1 | [T12] | true | pes.w1.t13 | work | cursor-foreground |
| T14 | TASK-016 | W1 | [T10] | true | pes.w1.t14 | work | cursor-foreground |
| T15 | TASK-017 | W1 | [T05] | true | pes.w1.t15 | work | cursor-foreground |
| T16 | TASK-018 | W1 | [T07] | true | pes.w1.t16 | work | cursor-foreground |
| T17 | TASK-019 | W1 | [T05] | true | pes.w1.t17 | work | cursor-foreground |
| T18 | TASK-020 | W1 | [T05] | true | pes.w1.t18 | work | cursor-foreground |
| T19 | TASK-021 | W1 | [T00] | true | pes.w1.t19 | work | cursor-foreground |
| T20 | TASK-022 | W1 | [T00] | true | pes.w1.t20 | work | cursor-foreground |
| T21 | TASK-023 | W1 | [T05] | true | pes.w1.t21 | work | cursor-foreground |
| T22 | TASK-024 | W1 | [T03,T05] | true | pes.w1.t22 | work | cursor-foreground |
| T23 | TASK-025 | W2 | all mutate | true | pes.w2.t23 | work | ci-generic-shell |
| T24 | TASK-026 | W2 | [T23] | true | pes.w2.t24 | work | github-remote-actions |

**Stop / do not execute when:** status ≠ `executable`; Program Lock drift; envelope breach; attempt to write `~/.cursor-governance` or `/Users/macm2/l9-ci-core`; `PR_BASE` contains `main`; Phase 0 `acknowledged_at` would be written.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.pe.pipeline-assembly-fill.v1` |
| name | Fill every PE pipeline-assembly gap from brief to COMPLETED |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | Igor Beylin |
| created_at | `2026-08-16` |
| depth | `deep` (route_plan `--risk high --evidence sufficient`) |
| validator | `PASS` `pipeline_assembly_fill.plan.json` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `environment/program-execution/audits/pipeline-assembly-audit.v1.yaml` |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Repair the existing `make campaign` tunnel. Do not add an eighth workflow, a second front door, or an analysis kernel. Branch from `feat/campaign-tunnel` @ `8c2932d310a988e0ad5431c185d524146acbc459`, not from `origin/main` @ `93fbd924` (host-activate stub only). |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-16T19:32:00Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/macm2/.l9/gov-worktrees/make-campaign` |
| ssot_clone | dirty primary `~/.cursor-governance` is **not** writable |
| branch | `feat/campaign-tunnel` → cut `feat/pipeline-assembly-fill` |
| commit_sha | `8c2932d310a988e0ad5431c185d524146acbc459` |
| dirty | `true` (uncommitted audit yaml + MANIFEST.json) |
| allowed_local_dirt | `environment/program-execution/audits/pipeline-assembly-audit.v1.yaml`, `environment/program-execution/MANIFEST.json` |
| overlap_policy | `explicitly_allow_listed_paths` then `require_clean_tree` after T00 |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

`make campaign INTENT=<brief>` is the only operator front door. Today it reaches TASK-001 **LEASED** (S08) and then either idles or fakes a finish by merging a host PR with no task work. Successors stay `definition_status: blocked`. `STACK.json` is unread. `pec prepare` forks from reconcile HEAD. `stack_pr.py` falls back to `main`. Close is three unlinked commands. `COMPLETED/` does not exist. This plan fills every GAP-001..GAP-031 so the line is brief → execute → stacked PRs → pec+host close → `campaigns/COMPLETED/<id>/`.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline is 8c2932d plus audit commit on feat/pipeline-assembly-fill | `repository_state` | `git rev-parse HEAD` ancestry contains `8c2932d310a988e0ad5431c185d524146acbc459`; branch ≠ origin/main | true |
| SP-02 | Two-task fixture reaches both COMPLETED, pec closed, host ledger complete, `campaigns/COMPLETED/<id>/` present, live `campaigns/<id>/` absent | `runtime_behavior` | unmocked unittest in `test_run_campaign.py` | true |
| SP-03 | After arm, status/next names TASK-001 current; ready=[] is not idle | `runtime_behavior` | pec status JSON `current.task_id=TASK-001` | true |
| SP-04 | TASK-002 prepare parent SHA equals TASK-001 branch HEAD; no PR_BASE main | `structural` | git rev-parse + stack_pr.py test | true |
| SP-05 | until=merge before all tasks COMPLETED refuses host-only merge | `runtime_behavior` | CampaignError in unittest | true |
| SP-06 | Hygiene: same-id relaunch, clean isolate, matching donor, EVID-001 SHA, dual quarantine | `runtime_behavior` | existing + new run_campaign tests | true |
| SP-07 | make pr-check PASS; PE MANIFEST honest; all 31 GAP ids Resolved | `quality_gate` | `make pr-check`; audit file | true |
| SP-08 | No forged Phase 0 ack; no pe-hash bootstrap; no intent.v1 live path | `structural` | tests on annotate_phase0, pec bootstrap, compiler cli | true |
| SP-09 | Inspection-only compiled task reaches PASSED_LOCAL when output file exists | `runtime_behavior` | pec verify test: empty validation_commands + `docs/program-execution/TASK-001.md` present | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.pe.pipeline-assembly-fill.v1` |
| source_ref | `plan.pe.pipeline-assembly-fill.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| baseline_verified | T00 must re-run |
| drift_detected | dirty audit files expected until T00 commits them |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | branch_and_HEAD_resolution | `git -C $HOME/.l9/gov-worktrees/make-campaign rev-parse HEAD` | ancestry includes `8c2932d310a988e0ad5431c185d524146acbc459` | true |
| CP-02 | command_available | `python3`, `git`, `gh` | each on PATH | true |
| CP-03 | filesystem_write | factory worktree writable; `~/.cursor-governance` **not** used as write root | write probe on worktree only | true |
| CP-04 | audit_parse | yaml.safe_load audit | 31 unique GAP ids | true |
| CP-05 | refuse_wrong_repo | cwd is not `/Users/macm2/l9-ci-core` for mutations | factory worktree only | true |

## Execution envelope

### Filesystem

- **write_allow:** `environment/program-execution/scripts/**`, `environment/program-execution/scripts/tests/**`, `environment/program-execution/core/program-execution-controller-template/scripts/pec/**`, `environment/program-execution/core/program-execution-controller-template/scripts/tests/**`, `environment/program-execution/campaigns/scripts/**`, `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`, `environment/program-execution/campaigns/COMPLETED/**`, `environment/program-execution/audits/**`, `environment/program-execution/MANIFEST.json`, `environment/program-execution/compiler/cli.py`, `environment/program-execution/compiler/tests/**`, `skills/l9-pe-campaign-activate/**`, `ops/scripts/stack_pr.py`, `Makefile` (append-only)
- **write_deny:** `/Users/macm2/l9-ci-core/**`, `/Users/macm2/.cursor-governance/**`, `environment/program-execution/core/program-execution-blueprint-template/**`, `docs/templates/**`, `.cursor/plans/campaign_brief_ir_ebea99a7.plan.md`, live `$HOME/.l9/programs/l9-ci-core-org-runtime-v1/**`, `$HOME/.l9/programs/pe-8c9f6de43b25/**`
- **delete_allow:** only fixture `$L9_ROOT` temp trees created by tests

### Commands

- **allow:** `python3 -m unittest …`, `python3 environment/program-execution/scripts/generate_manifest.py`, `python3 environment/program-execution/scripts/validate_manifest.py`, `python3 ops/scripts/sync_generated_artifacts.py --force`, `make pr-check`, `git add/commit/push -u` on declared branch, `gh pr create` after L4
- **deny:** `git push --force`, `git reset --hard`, `gh pr merge` of unrelated PRs, `make campaign INTENT=` of PE- Memory.md, pec `--admission-draft`, `L9_ALLOW_INTENT_COMPILER=1` as a live path

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `github.com` (push/PR/checks on Cursor-Governance only) |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only` (existing `gh` auth) |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`. Merge this fill PR only after PE verify + green+mergeable, stacked on `feat/campaign-tunnel` while 189 is open.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T00 | `filesystem_mutation` + `repository_state` | `safe_with_dedupe` | `manual_only` | delete fill branch | false |
| T01–T22 | `filesystem_mutation` | `safe_with_dedupe` | `bounded_retry` | git restore scoped paths | false |
| T09 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | move COMPLETED/<id> back to campaigns/<id> | false |
| T23 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | delete fixture $L9_ROOT | false |
| T24 | `network_write` | `safe_with_dedupe` | `manual_only` | close/abandon fill PR | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T01 T02 | pec task unlock | `control_plane` | pec program-lock + blueprint task cards | do not invent a second readiness model |
| T03 T04 T12 | git stack | `control_plane` | STACK.json + pec lease.base_sha | do not rebase; do not PR_BASE=main |
| T05 T06 T15 T21 T25 | execute loop | `runtime` | run_campaign + pec CLI allowlist | do not implement analysis; do not spawn a second scheduler |
| T07 T08 T16 | publish | `ops` | CAMPAIGN_EXECUTION_POLICY + make pr | do not merge all open PRs |
| T09 | closeout | `ops` | pec close + close_campaign.py | do not leave a third close path live |
| T19 T20 | admission | `policy` | Phase 0 + refuse-hash | do not forge ack; do not restore intent.v1 |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.pe.pipeline-assembly-fill.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking SP fail; envelope breach; write to denied paths |

### Strategies

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | revert fill commits on feat/pipeline-assembly-fill; do not revert 8c2932d factory |
| data | `manual_recovery` | move COMPLETED/<id> back if mover ran on a real campaign |
| external_state | `corrective_append_only_record` | close/abandon fill PR; do not force-push |
| local_state | `git_restore_scoped_paths` | quarantine fixture `$L9_ROOT` |

### Irreversible operations

- none if no force-push and no real-campaign COMPLETED move

### Rollback verification

- `git merge-base --is-ancestor 8c2932d310a988e0ad5431c185d524146acbc459 HEAD` still true on feat/campaign-tunnel
- no `campaigns/COMPLETED/` entries except fixtures
- pec tests on `main`/8c2932d still collect if fill branch deleted

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `critical` |
| uncertainty | `medium` |
| blast_radius | `critical` |
| architectural_boundaries_crossed | `3` (pec controller, campaign runner, host policy) |
| external_systems_touched | `1` (GitHub Cursor-Governance) |
| migration_required | `false` |
| unknown_dependency_count | `3` (accept_bounded) |

## Execution DAG

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.pe.pipeline-assembly-fill.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

**Critical path:** `T00 → T01 → T25 → T02 → T03 → T05 → T06 → T07 → T09 → T23 → T24`

**Parallel after T00:** T01, T03, T10, T11, T19, T20, T25  
**Parallel after T05:** T06, T07, T09, T15, T17, T18, T21  
**T23 waits for every mutate todo.**

**Forbidden edges:** T05 before T01 (execute without unlock); T09 before T05 (close without execute); T24 before T23; T07 host PR before T05; any todo writing l9-ci-core.

## GAP coverage (no skip)

| GAP | todo | mechanism (do this, not a paraphrase) |
|-----|------|----------------------------------------|
| GAP-001 | T05 | Add `execute` to `UNTIL_STAGES`. After arm, call pec `prepare` → `render-contract` → `start` → `record-attempt` → `verify` → `evaluate-gate` → `complete` → `claim` next. Timeouts already in `run_cmd`. |
| GAP-002 | T01 | In `compile_activation_files.py` `build_source`, set every task `definition_status: ready`. Keep `wave_id` W0/W1 and `dependency_edges`. Do **not** rely on `complete_task` to flip status (it does not). |
| GAP-003 | T03 | `claim_task`: if `runtime/STACK.json` has a predecessor branch, `base_sha = rev-parse <pred>`. `prepare_worktree` already uses `lease.base_sha`. Refuse pred missing when task index > 1. |
| GAP-004 | T04 | `stack_pr.py cmd_base`: if `STACK.json` or `CAMPAIGN_ID`+`$L9_ROOT` exists, print that base; else exit 2. Never print `default_branch`. Append Makefile helper; do not edit `PR_BASE ?= origin/main`. |
| GAP-005 | T09 | After both closes, `shutil.move(campaigns/<id>, campaigns/COMPLETED/<id>)`. `next_campaign` skips `COMPLETED/` and `lifecycle in {complete,cancelled}`. |
| GAP-006 | T09 | New runner stage `close`: `pec close` then `close_campaign.py close --id --verdict --evidence`. Only when all required tasks `COMPLETED`. |
| GAP-007 | T07 | If `until=merge` and any required task not COMPLETED: raise `CampaignError`. Do not call `default_make_pr` / `default_authorize_and_merge` as a fake finish. Makefile may still pass `--until merge`. |
| GAP-008 | T17 | Prefer: delete `abort-execution` call and stop wiring `run_peer_task_pipeline` from `make campaign`. If the pipeline is kept, add `pec abort-execution` in `cli.py` that maps to an existing halt/cancel. One executor: `run_campaign` execute loop. |
| GAP-009 | T02 | After `verify` PASS, `evaluate-gate <completion_gate_id>` with attempt evidence so `gate.result == PASS` before `complete_task`. |
| GAP-010 | T10 | `assign_campaign_id`: if `base` exists and ledger lifecycle is `in_progress` or missing close, reuse `base` and quarantine. `-v2` only when prior is `complete` or `cancelled`. |
| GAP-011 | T11 | `isolate_worktree`: if exists, require `status --porcelain` empty and branch == expected; else move to `*.stale-<utc>` and recreate. |
| GAP-012 | T12 | Compare `git -C donor remote get-url origin` to `repository_id`. Mismatch → clone `https://github.com/<repository_id>.git` to `program-worktrees/<id>`. |
| GAP-013 | T13 | After reconcile, `revision = git rev-parse HEAD` (40 hex). Pass that to `collect_evidence`. Test catalog value. |
| GAP-014 | T18 | `default_program_blockers` after arm returns `[]` or only real blockers. Remove `target work not started`. |
| GAP-015 | T15 | `pec claim … --ttl-hours 1` (or minutes if added). Card `max_task_minutes` must match. Expired lease cannot stay `EXECUTING`. |
| GAP-016 | T08 | Set `publish.merge: true` only for PRs listed in STACK.json opened by this run, **or** keep `merge: false` and stop the runner from merging. `remediations.scope: stacked_prs_opened_by_this_run`. Add a test that policy.merge == runner.merge_behavior. |
| GAP-017 | T16 | `git push -u origin campaign/<id>` (no force) before `PR_BASE=origin/campaign/<id>`. Missing remote → `CampaignError`. |
| GAP-018 | T07 | `until=bootstrap` in Python includes arm (STAGE_INDEX bootstrap >= arm) **or** exits 2 saying arm is required. Do not rewrite Makefile comment. |
| GAP-019 | T19 | Keep `annotate_phase0_without_forging_ack`. Document in pipeline.md: make campaign is admission; GATE-000 stays draft while `program_deploying` is false. |
| GAP-020 | T20 | In `pec bootstrap`, if `program.id` matches `^pe-[0-9a-f]{8,}$` raise. Keep compiler refuse-by-default. |
| GAP-021 | T21 | `start_task` reads LAUNCH.json; if `load_operator_brief` is false and CWD/context is the primed brief path, raise. |
| GAP-022 | T14 | `quarantine_occupied` also moves `$L9/blueprints/<id>` to `blueprints/stale/<id>-<utc>`. |
| GAP-023 | T22 | Rewrite pipeline.md isolate: host `feat/<id>`, target `program-worktrees/<id>`, writes in `$L9/programs/<id>/worktrees/TASK-00N`. LAUNCH.json already has both paths; add `write_tree`. |
| GAP-024 | T09 | `export_handoff` must not set host ledger complete. Test: export-handoff alone → `CAMPAIGN_STATUS` lifecycle ≠ complete. |
| GAP-025 | T06 | `status`/`next` add `current: {task_id, runtime_state}`. `write_launch_pointer` sets `pec_ready_empty_is_expected: true` after claim. |
| GAP-026 | T07 | If a host PR is opened, `git add` only `ALLOWED_CAMPAIGN_FILES` and commit on `feat/<id>` after execute has started. `make pr` then has commits ahead of `campaign/<id>`. |
| GAP-027 | T12 | After clone, `git fetch origin campaign/<id> pec/w0/task-001 …` (or deepen). `--single-branch main` alone is illegal once STACK.json exists. |
| GAP-028 | T05 | Same as GAP-001: the runner **is** the executor. Do not wait for a human to read LAUNCH.json. |
| GAP-029 | T02 | W0 `exit_gate_ids=[GATE-001]`. After TASK-001 verify, evaluate GATE-001. W1 claim test asserts no `predecessor_wave_exit_gate_not_satisfied`. |
| GAP-030 | T18 | Do not teach agents to read dirty-primary `CAMPAIGN_STATUS.yaml`. LAUNCH.json `host_lifecycle=in_progress` after arm. Origin ledger changes only via host PR commit (T07). |
| GAP-031 | T19 | `operator_ack_required: false` for T0 make campaign. Keep `forge_operator_ack: false`. |
| GAP-032 | T25 | In `verify` / `_run_validation` path: if `contract.validation_commands` is empty and every Task Card validation method is `inspection`, set `gates["validation"]` PASS only when every compiled `outputs[].location` exists in the pec worktree. Do not treat acceptance prose as a shell command. Do not change compile remap-to-inspection. |

## Per-todo implementation contract

### Locked decisions (Improve pass — no OR left)

| id | was ambiguous | locked value |
|----|---------------|--------------|
| LD-00 | commit audit on campaign-tunnel vs fill | Commit only on `feat/pipeline-assembly-fill`. Do not commit onto `feat/campaign-tunnel` unless the operator names that branch. |
| LD-08 | policy.merge true vs false | Runner squash-merges only PR numbers it recorded on STACK.json after green+mergeable. `remediations.scope: stacked_prs_opened_by_this_run`. Never `all_open_prs_in_target_repo`. |
| LD-15 | 15 minutes vs 8 hours vs 1 hour | Add `pec claim --ttl-minutes`. Runner passes `15`. Card Budget is 15 minutes. |
| LD-17 | register abort-execution vs delete | Delete the call. Do not add a pec subcommand. |
| LD-32 | invent shell from prose vs pec inspect | pec verify PASS when `validation_commands==[]` and every compiled output file exists. Keep compile remap-to-inspection. |
| LD-exec | who writes the task body | Runner writes only the compiled `outputs[].location` (`docs/program-execution/TASK-00N.md`) in the pec prepare worktree. That is the factory attempt. Live richer edits stay inside those writable_paths. No analysis engine. |
| LD-gh | fixture vs live GitHub | Unmocked fixture never calls `gh`. Live `until` that includes `pr` opens stacked task PRs after COMPLETED. |

### T00 — bind
1. `git switch -c feat/pipeline-assembly-fill` from `8c2932d310a988e0ad5431c185d524146acbc459` plus the already-written audit/MANIFEST dirt.
2. Commit those two files on the fill branch when execution is authorized.
3. Write UNK defaults into the audit: UNK-001 admission=make campaign; UNK-002 `environment/program-execution/campaigns/COMPLETED/<id>/`; UNK-003 host PR only after emit commit and never before first task execute.

### T01 — unlock definition
Replace `"ready" if index == 1 else "blocked"` with `"ready"`. Add activation test: later tasks `definition_status == ready`. Add pec test using compiled source: after TASK-001 COMPLETED + GATE-001 PASS, `claim TASK-002` has no `definition_not_ready`.

### T02 — evaluate gates
Add `default_evaluate_completion_gates(workspace, task_id)` used by the execute loop. Do not auto-PASS without attempt evidence. Test `_gate_satisfied` false before evaluate, true after.

### T03 — stack at git
`build_pr_stack` already encodes bases. Thread STACK.json into `claim_task` (new optional `--base-ref` or read file). `prepare_worktree` stays SHA-based. Test: commit on TASK-001 branch; claim TASK-002; `lease.base_sha == task001_head`.

### T04 — helpers
`stack_pr.py`: resolve `L9_ROOT` + `CAMPAIGN_ID` or `--stack`. Append to Makefile:

```
campaign-stack-base:
	python3 ops/scripts/stack_pr.py base --stack "$$L9_ROOT/programs/$$CAMPAIGN_ID/runtime/STACK.json"
```

Do not change `PR_BASE ?= origin/main`.

### T25 — inspection verify (GAP-032)
In `controller.py` verify, today `gates["validation"]` is FAIL when `validations` is empty. Campaign compile emits `method: inspection` so `required_validation_commands` is `[]` and `draft_source_contract` copies that empty list. Without this fix, T05 can never reach PASSED_LOCAL.

Change: if `contract.get("validation_commands")` is empty, set `gates["validation"]` to PASS only when every Task Card `outputs[].location` exists as a file under the pec worktree. Keep `worker_validation_claim` as `[] == []`. Do not run acceptance prose through `bash -lc`.

Test: fixture task with inspection-only validation, write `docs/program-execution/TASK-001.md`, record-attempt, verify verdict `PASSED_LOCAL`. Negative: missing file → FAIL.

### T05 — execute loop algorithm
`UNTIL_STAGES` becomes `("activate", "blueprint", "admit", "bootstrap", "arm", "execute", "pr", "close")`. Python default `until` is `close`. Makefile may still pass `merge`; treat unknown/`merge` as `close` and refuse host-only merge (T07).

`default_execute(workspace, campaign_id)` for each incomplete required task in lock order:

1. `pec prepare <id>` — worktree `$L9/programs/<id>/worktrees/<TASK>`.
2. `pec render-contract <id>`.
3. `pec start <id> --actor make-campaign`.
4. Read rendered contract `writable_paths` (drafted from `outputs[].location`, normally `docs/program-execution/TASK-00N.md`).
5. Write that relative path in the pec worktree with body `TASK-00N complete: <title>\n`. Create parents. Do not write outside writable_paths.
6. `git -C <pec-worktree> add` those paths and `commit -m "pec: <TASK> output"` so `candidate_sha` moves. `GIT_TERMINAL_PROMPT=0`. Timeout `GIT_TIMEOUT_S`.
7. Build `attempt-receipt.v2` JSON:
   - `schema`: `program-execution-controller.attempt-receipt.v2`
   - `task_id`, `contract_digest` from rendered, `program_digest` from program-lock, `base_sha` from lease, `candidate_sha` from `rev-parse HEAD`
   - `changed_files`: exact list from `_changed_paths` / `git diff --name-only base..HEAD` plus porcelain (must match verify)
   - `validation_results`: `[]` when inspection-only
   - `produced_evidence`: `[]`
   - `residual_unknowns`: `[]`
   - `claimed_status`: `completed`
8. `pec record-attempt <id> --receipt <path>`.
9. `pec verify <id>` — requires T25.
10. `pec evaluate-gate <completion_gate> --result PASS --evidence EVID-RUNTIME-… --actor make-campaign` (T02).
11. `pec complete <id> --actor make-campaign --evidence EVID-RUNTIME-…`.
12. If more tasks: `pec claim <next> --holder make-campaign --ttl-minutes 15` using STACK.json predecessor tip (T03, T15).
13. Live only (`until` includes `pr` and `hooks.make_pr` is not a no-op): push task branch, `gh pr create --base <STACK pr_base>`. Fixture tests set `hooks.make_pr` to a recorder.

Stop and raise `CampaignError` on any pec non-zero. Do not sit. Do not open the operator memo. Do not implement Semgrep or SDK analysis.

### T06 — current work
Extend `status()` payload. Update LAUNCH.json writer.

### T07 — honest until
`STAGE_INDEX`: if requested `merge` and tasks remain, behave as `execute` then refuse merge. `until=bootstrap` maps to `arm`. Host commit helper `commit_allowed_campaign_files` after execute starts.

### T08 — merge law
Set `remediations.scope: stacked_prs_opened_by_this_run`. Runner `default_authorize_and_merge(host_repo, numbers: list[int])` refuses any number not in STACK.json `prs` recorded by this run. After `gh pr checks` green and mergeable, `gh pr merge --squash` those numbers bottom-up. Test: policy.scope != `all_open_prs_in_target_repo`.

### T09 — close + COMPLETED
`default_close`: `pec close --workspace … --actor make-campaign --verdict CONVERGED --evidence tasks=all_completed` then `close_campaign.py close --id … --verdict CONVERGED --evidence …` then `archive_completed` moves `campaigns/<id>/` to `campaigns/COMPLETED/<id>/` (including `handoff/CLOSEOUT.yaml`). Ledger `campaigns/CAMPAIGN_STATUS.yaml` stays in place with `lifecycle: complete`. `next_campaign` skips `COMPLETED/` and complete/cancelled. Update `COMPILE_ALLOWLIST.yaml` if it enumerates live campaign dirs. `export_handoff` must not set host ledger complete. Test: export-handoff alone leaves lifecycle ≠ complete; close fixture leaves no live `campaigns/<id>/`.

### T10 — same-id relaunch
In `assign_campaign_id`, if `base` exists on the host ledger and lifecycle is `in_progress` or absent, return `base` and let `quarantine_occupied` run. Assign `base-v2` only when prior lifecycle is `complete` or `cancelled`. Test: second `make campaign` on the same memo keeps `campaign_id`.

### T11 — clean isolate
`isolate_worktree`: if `write_root` exists, run `git status --porcelain` and `git rev-parse --abbrev-ref HEAD`. Reuse only when porcelain is empty and branch is `feat/<id>` or the expected isolate branch. Else `rename` to `<name>.stale-<utc>` and `worktree add` fresh from `origin/main`. Test: dirty leftover is not written.

### T12 — donor and history
`default_ensure_target_checkout`: parse `git -C donor remote get-url origin`; allow donor only when it ends with `repository_id` or `repository_id.git`. Else `git clone` that repo (depth may start at 1) then `git fetch origin campaign/<id> 'pec/*'` and deepen as needed. After STACK.json exists, refuse leaving the checkout as `--single-branch main` only. Test: seed target `Quantum-L9/l9-ci-core` has that origin.

### T13 — EVID-001 SHA
After `default_ensure_target_checkout` / reconcile, `revision = git rev-parse HEAD` (40 hex). Pass to `collect_evidence`. Test: catalog `EVID-001.revision` matches `^[0-9a-f]{40}$`.

### T14 — dual quarantine
`quarantine_occupied` moves both `$L9/programs/<id>` and `$L9/blueprints/<id>` to `…/stale/<id>-<utc>`. Test: second launch after a lock exists still admits.

### T15 — 15-minute lease
Add `claim_task(..., ttl_minutes: int | None = None)`. CLI `--ttl-minutes` (default 60 for back-compat). Runner passes `--ttl-minutes 15`. Card line `Budget: 15 minutes`. Test: `expires_at` is ≤ 16 minutes from `issued_at`. Expired lease: `start` / execute raises; state is not EXECUTING.

### T16 — push campaign branch
After `ensure_integration_branch`, `git push -u origin campaign/<id>` with `GIT_TERMINAL_PROMPT=0`, no force. If `origin/campaign/<id>` is missing after push, `CampaignError`. Call this before any `PR_BASE=origin/campaign/<id>`.

### T17 — one executor
Delete the `abort-execution` argv from `run_peer_task_pipeline.py`. Do not add `pec abort-execution`. Leave the file unwired from `make campaign`. If a test expects that subcommand, change the test to expect the deletion.

### T18 — live SSOT
`default_program_blockers` after arm returns `[]` (or only real pec blockers). Remove `target work not started` and `do not close … after host-only merge` once execute/close exist. `write_launch_pointer` remains the agent SSOT. `mark_host_campaign_active` stays on the isolated host worktree only.

### T19 — Phase 0 law
Keep `annotate_phase0_without_forging_ack`. Set `operator_ack_required: false` in LAUNCH.json for T0. pipeline.md: make campaign is the admission act; GATE-000 stays draft while `program_deploying` is false. Test: make campaign does not write a non-null `acknowledged_at`.

### T20 — refuse pe-hash
In `pec bootstrap` / `ensure` admission, if `program.id` matches `^pe-[0-9a-f]{8,}$` raise `ControllerError`. Keep compiler refuse-by-default. Test: bootstrap of `pe-deadbeef` fails even with `L9_ALLOW_INTENT_COMPILER=1`.

### T21 — refuse operator memo
`start_task` loads `runtime/LAUNCH.json`. If `load_operator_brief` is false and `Path.cwd()` or a provided context path equals the primed `*.activate.yaml` `brief` / intent path, raise. Test: start fails when CWD is the brief path.

### T22 — three trees
pipeline.md isolate section must list: host `feat/<id>`, target `$L9/program-worktrees/<id>`, write `$L9/programs/<id>/worktrees/TASK-00N`. LAUNCH.json adds `write_tree`. Test: after prepare, mutation path is the pec worktree, not the host isolate.

### T23 — proof
Unmocked loop: leftover pec quarantined → admit → bootstrap → all contracts → TASK-001 execute to COMPLETED → GATE-001 PASS → TASK-002 claim + prepare parent is predecessor → close → `COMPLETED/<id>` exists. Update SKILL.md steps 1–5 to match. Regen MANIFEST. Set audit `overall_autonomy_percent: 100` only after this test passes.

### T24 — gate
`make pr-check` in the factory worktree. Remediate. Stack PR onto `feat/campaign-tunnel` (or `origin/main` only after 189 merges). Do not merge from l9-ci-core.

## Property evidence matrix

| evidence_id | claim_id | evidence_kind | command | expected_positive | status |
|-------------|----------|---------------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | `git rev-parse HEAD` / merge-base | ancestor 8c2932d | `not_run` |
| EV-SP-02 | SP-02 | `runtime_behavior_evidence` | unmocked test_run_campaign close fixture | COMPLETED dir + both tasks COMPLETED | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | pec status after arm | current.task_id=TASK-001 | `not_run` |
| EV-SP-04 | SP-04 | `structural_evidence` | prepare + stack_pr tests | parent SHA; no main | `not_run` |
| EV-SP-05 | SP-05 | `runtime_behavior_evidence` | until=merge early | CampaignError | `not_run` |
| EV-SP-06 | SP-06 | `runtime_behavior_evidence` | hygiene tests | listed markers | `not_run` |
| EV-SP-07 | SP-07 | `quality_gate_evidence` | `make pr-check` | PASS | `not_run` |
| EV-SP-08 | SP-08 | `structural_evidence` | phase0/hash/compiler tests | refuse forge / pe-hash / intent | `not_run` |
| EV-SP-09 | SP-09 | `runtime_behavior_evidence` | pec verify inspection-only fixture | PASSED_LOCAL | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Later tasks stay `blocked` → execute loop “succeeds” after TASK-001 and closeout archives an unfinished program. **Guard:** T23 asserts TASK-002 COMPLETED.
- STACK.json written, prepare still uses reconcile HEAD → conflicts return. **Guard:** T03 parent-SHA test.
- Makefile `--until merge` bypasses Python default. **Guard:** T07 interprets merge as execute-then-close and refuses host-only merge.
- pec next ready=[] after claim → agents sit. **Guard:** T06 `current`.
- COMPLETED under `$HOME/.l9` → `next_campaign` reselects the id. **Guard:** UNK-002 locked to in-repo `campaigns/COMPLETED/`.
- donor=host for l9-ci-core target → wrong repo. **Guard:** T12 origin match.
- export-handoff used as close → no COMPLETED move. **Guard:** T09 + GAP-024 test.
- pec verify requires a nonempty validation command list → every compiled campaign task dies at SUBMITTED. **Guard:** T25 / SP-09.

### Assumption failure conditions

- Dirty tree overlaps write_allow beyond allowed_local_dirt after T00
- HEAD loses 8c2932d ancestry
- Attempt to write denied paths
- Unknown fourth close path appears

### Blast radius notes

Every future `make campaign` and every pec workspace using this controller template. Wrong merge scope can merge unrelated GitHub PRs.

### Rollback constraints

No force-push. No history rewrite. No dirty-primary writes.

## Out of scope

- l9-ci-core product, workflows, MANIFEST.sha256
- Dirty `~/.cursor-governance` primary
- Live campaigns `l9-ci-core-org-runtime-v1`, `pe-8c9f6de43b25`
- Launching `PE- Memory.md`
- Forging Phase 0 ack
- Rewriting CAMPAIGN_SOURCE.yaml after receipt bind
- Restoring intent.v1 / `--admission-draft`
- PR_BASE=main
- Force-push / admin-merge / scanner weakening
- Rewriting existing Makefile lines
- Eighth Core reusable workflow
- Editing `campaign_brief_ir_ebea99a7.plan.md`
- Full-throttle `program_deploying=true` without a real Igor ack
- Merging PR 189 from the l9-ci-core workspace
- Implementing Semgrep/SDK analysis inside the runner

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | Wire dormant SDK CLI (`gate evaluate`, `providers detect`) after v2.0.0 | AGENTS.md §7; expanding invoke-sdk mid-fill churns the candidate SHA |
| P2 | Makefile rewrite of CAMPAIGN_UNTIL comment / PR_BASE default | root-file append-only; needs an authorized root-file change |
| P3 | Human Phase 0 timestamp for deploy campaigns | UNK-001 deploy path; not T0 make campaign |

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.pe.pipeline-assembly-fill.v1` |
| current_state | `partial` |
| implementation_ready | `false` until T00 reverify + status `executable` |

### Gates

- **executable_when:** baseline locked; CP-01..CP-05 pass; DAG acyclic (true); envelope complete (true); UNKs accept_bounded (true)
- **complete_when:** EV-SP-01..09 `passed`; audit GAP-001..032 Resolved; `make pr-check` PASS
- **blocking_conditions:** preflight_blocked; envelope breach; baseline drift; write to l9-ci-core or dirty primary

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | UNK-001 | Phase 0 ack vs make campaign admission | accept_bounded: make campaign is admission; ack stays null; operator_ack_required false for T0 |
| unknown | UNK-002 | COMPLETED path | accept_bounded: `environment/program-execution/campaigns/COMPLETED/<id>/` |
| unknown | UNK-003 | host PR existence | accept_bounded: host PR only after emit commit; never before first task execute |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | `l9-ynp` then attach `@environment/program-execution` + `/autonomy` on Cursor-Governance `feat/pipeline-assembly-fill` |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → `cursor-foreground` |
| broader_work_requires_separate_contract | `true` |

---

## Plan audit (Improve kernel v3 — this revision)

Verified defects in the prior plan (now closed in these artifacts):

| id | severity | defect | remediation |
|----|----------|--------|-------------|
| PA-01 | critical | Execute loop never specified a receipt or worktree write; pec verify requires changed files + validation | T05 algorithm + T25 |
| PA-02 | critical | Compiled tasks are inspection-only; verify FAIL on empty commands | GAP-032 / T25 / SP-09 |
| PA-03 | high | T10–T22 said "Follow GAP table" | Per-todo contracts above |
| PA-04 | high | T08 / T17 / T00 / T15 were OR-decisions | Locked decisions table |
| PA-05 | medium | Phase-0 table lumped T06–T22 | Full 26-row table |
| PA-06 | medium | Architecture impact cited nonexistent T28 | Replaced with T25 |
| PA-07 | medium | 15-minute card vs 8-hour lease vs 1-hour ceiling | `--ttl-minutes 15` |
| PA-08 | low | T00 commit target contradicted itself | Fill branch only |

## Machine stub

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.pe.pipeline-assembly-fill.v1
  status: draft
  json_ssot: /Users/macm2/.cursor/plans/pipeline_assembly_fill.plan.json
  validator: PASS
immutable_baseline:
  repository: Quantum-L9/Cursor-Governance
  commit_sha: 8c2932d310a988e0ad5431c185d524146acbc459
  branch: feat/pipeline-assembly-fill
execute_via:
  pipeline: environment/program-execution
  autonomy: l9-bounded-autonomy
  adapter_default: cursor-foreground
  autonomous_merge: false
```
