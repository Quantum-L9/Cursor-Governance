---
name: Scratch hold never-lose
overview: Sacred WIP stays unparkable; shell-gate /tmp parking; .l9/scratch-hold for non-WIP only; make pr restore-all start/end. Execute via PE + max @autonomy under Program lease.
todos:
  - id: todo-01-baseline-preflight
    content: "PE W0: lock immutable baseline (full SHA) + capability probes; confirm sacred WIP policy still live; Program Lock bind; stop_and_replan on drift"
    status: completed
  - id: todo-02-mutate-hold-and-gates
    content: "PE claim→render→worker + @autonomy: scratch_hold.py, .l9/scratch-hold gitignore, classify/WARN filters, worktree shell denials, run_pr_gate+open_pr restore wiring, sessionStart restore"
    status: completed
  - id: todo-03-prove
    content: "PE verify: unit/integration evidence (WIP park rejected, /tmp deny, make pr-check restore roundtrip, dirty WIP present); make pr-check PASS"
    status: completed
  - id: todo-04-converge
    content: PE handoff + @autonomy join/PR-poll; L4 authorize-release → push/PR → l9-pr-remediation; merge per L4 plan-Build stack after green+mergeable
    status: completed
isProject: false
---

# PLAN: Scratch hold never-lose

> **Template conformance:** Body follows [`.cursor/plans/_TEMPLATE.plan.md`](.cursor/plans/_TEMPLATE.plan.md) (local mirror of [`canonical.template.executable_plan.v1.plan.md`](environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md)). Prior draft was design-only; this revision is the PE-executable contract.
> **Schema:** `canonical.schema.plan_document.v1` — status below; promote to `executable` only when law holds.
> **Execute:** **[@environment/program-execution](environment/program-execution/)** + **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Profile: **`program_deploy_max_autonomy`** (max within ceiling; `autonomous_merge: false`). Do **not** free-form mutate from this markdown alone.
> **Rename to:** `scratch_hold_never_lose_<8hex>.plan.md` before execute.
> **Upstream:** [`wip_sacred_tracked_unscanned`](/Users/ib-mac/.cursor/plans/wip_sacred_tracked_unscanned_9d3e1592.plan.md) **done/committed** — do NOT ignore `WIP/**`; WIP unparkable.

## Execute via @environment/program-execution + autonomy (required)

**Authority order (fail-closed — `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md
        │ project
        ▼
@environment/program-execution   HOW (Blueprint → Program Lock → Controller)
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  profile: program_deploy_max_autonomy  (max within ceiling; owns_program_state: false)
        │
        ▼
PE adapter: cursor-foreground (mutate) + cursor-background (PR poll)
```

### Pipeline steps

1. Attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md).
2. Project plan → Blueprint under `$HOME/.l9/programs/pes-scratch-hold-never-lose/` (never mutate sealed `core/` templates).
3. `pec.py bootstrap` → `reconcile` → `status` → `next`.
4. Admit Source Contract ⊂ Task Card ceiling → `claim` → `prepare` → `render-contract`.
5. Map Program tasks → autonomy campaign via `integrations/autonomy-control-plane/` (`autonomy_action_id` per card).
6. Orchestrate Protocols A–D under `@autonomy` with **`program_deploy_max_autonomy`** packet (below). Spawn ready `work` Tasks; PR `poll` with `run_in_background=true`; main continues.
7. L4: local commits until `l4_local.py authorize-release` → push/PR → `l9-pr-remediation` Converge. Build / PE+`/autonomy` launch = merge authorization for this stack after green+mergeable (bottom-up). Packet keeps `autonomous_merge: false` (COMPATIBILITY).
8. `record-attempt` → `verify` → `export-handoff`.

### Campaign authorization packet (fill digests at execute)

```yaml
packet_id: autonomy-scratch-hold-never-lose
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: program_deploy_max_autonomy
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: .cursor/plans/scratch_hold_never-lose_5f0886ad.plan.md
plan_id: plan.ops.scratch_hold_never_lose.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-scratch-hold-never-lose
  program_lock_digest: <sha256 at Lock>
  adapter_id: cursor-foreground
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [feat/scratch-hold-never-lose]
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
  - ignore_WIP_tree
  - park_WIP_to_tmp_or_hold_vault
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|--------------------|------|--------------|
| todo-01-baseline-preflight | TASK-001 | W0 | [] | false | pes.w0.task001 | work | cursor-foreground |
| todo-02-mutate-hold-and-gates | TASK-002 | W1 | [todo-01-baseline-preflight] | true | pes.w1.task002 | work | cursor-foreground |
| todo-03-prove | TASK-003 | W1 | [todo-02-mutate-hold-and-gates] | false | pes.w1.task003 | work | cursor-foreground |
| todo-04-converge | TASK-004 | W2 | [todo-03-prove] | true | pes.w2.task004 | work | github-* + poll |
| poll-pr-N | — | W2 | [todo-04-converge] | true | pes.w2.poll.prN | poll | cursor-background |

**Stop when:** status ≠ `executable`; Program Lock drift; capability preflight blocked; envelope incomplete; sacred WIP policy regresses.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.ops.scratch_hold_never_lose.v1` |
| schema_version | `1.0.0` |
| status | `draft` (→ `executable` after baseline+envelope+DAG filled at Build) |
| is_project | `false` |
| owner | governance-control-plane |
| created_at | `2026-08-12` |
| updated_at | `2026-08-12` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | WIP sacred policy + this plan |
| plan_class | `bounded_execution_contract` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via PE + max @autonomy; no redesign |

## Immutable baseline

| Field | Value |
|-------|-------|
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| branch | `feat/scratch-hold-never-lose` (create at execute) |
| commit_sha | **lock full SHA at W0** |
| dirty | capture at W0 |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| allowed_local_dirt | `WIP/**` (sacred edits OK; do not park), `.l9/scratch-hold/**` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Stop agents from parking sacred `WIP/` (or other work) under `/tmp` for `make pr` without restore. Keep sacred WIP tracked/unparkable; add non-WIP hold vault + shell denials; **wire `make pr` restore-all at start/end** (product gap).

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline SHA matches at start | repository_state | `git rev-parse HEAD` | true |
| SP-02 | WIP cannot be parked to /tmp or scratch-hold; make pr restores holds | structural + filesystem | unit tests + park reject + restore roundtrip | true |
| SP-03 | `make pr-check` PASS on changed files | quality_gate | `make pr-check` → PASS | true |

## Capability preflight

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | branch_and_HEAD_resolution | `git rev-parse HEAD` | equals locked SHA | true |
| CP-02 | sacred_wip_policy_live | `rg -n 'intentionally tracked' .gitignore WIP/README.md` | both hit; no blanket `WIP/` ignore | true |
| CP-03 | filesystem_write | write probe under `ops/` `ops/autonomy/` `.gitignore` | writable | true |

## Execution envelope

### Filesystem

- **write_allow:** `ops/scripts/scratch_hold.py`, `ops/scripts/run_pr_gate.sh`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/classify_generated_dirtiness.sh`, `ops/autonomy/worktree_isolation_gate.py`, `ops/autonomy/local_execution_gate.py`, `ops/autonomy/surface_profile.yaml`, `ops/hooks/session_start_bootstrap.sh` (or restore delegate), `.gitignore` (append `.l9/scratch-hold/` only), `learning/failures/repeated-mistakes.md`, `rules/92-learned-lessons.mdc`, `WIP/README.md` (optional one Agent-rules line only), `tests/**` for hold/gate, `Makefile` (scratch-hold targets if needed)
- **write_deny:** blanket `WIP/` ignore; delete/move of `WIP/**` content; `environment/program-execution/core/**`; secrets; unrelated trees

### Commands

- **allow:** pytest/ruff scoped; `make pr-check`; `python3 ops/scripts/scratch_hold.py …`; git add pathspecs in envelope
- **deny:** force-push; hard-reset; `git clean -fdx`; park WIP to `/tmp`; ignore entire WIP/

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` (push/PR only after L4 release) |

### Autonomous merge

`autonomous_merge: false` — merge only via L4 plan/PE Build stack after green+mergeable.

## Design summary (binding intent)

1. **No WIP gitignore** — sacred policy stands.
2. **Shell deny** WIP→`/tmp`, `rm -rf WIP`, hold-dir creation under `/tmp/cg-*-hold*`.
3. **`scratch_hold.py`** — park rejects `WIP/**`; vault `.l9/scratch-hold/` gitignored.
4. **`make pr` restore gap** — restore-all at start/end of `run_pr_gate.sh` + `open_pr_after_gate.sh`; status fail-closed.
5. **sessionStart** restore + legacy `/tmp` import.
6. Soften dirty WARN / classify for WIP + reports + scratch-hold.

## Rollback

| Field | Value |
|-------|-------|
| supported | `true` |
| automatic_allowed | `false` |
| strategies | `git_restore_scoped_paths` / `revert_commit` on write_allow |
| irreversible | none if WIP never deleted |

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry |
|---------|--------------|-------------|-------|
| todo-01-baseline-preflight | filesystem_read | safe_to_repeat | none |
| todo-02-mutate-hold-and-gates | filesystem_mutation | safe_with_dedupe | retry_once |
| todo-03-prove | filesystem_read | safe_to_repeat | retry_once |
| todo-04-converge | network_write | safe_with_dedupe | manual_only |

## Execution DAG

**Critical path:** todo-01 → todo-02 → todo-03 → todo-04 (+ poll)

| id | depends_on | outputs |
|----|------------|---------|
| todo-01-baseline-preflight | [] | baseline_receipt, preflight_receipt |
| todo-02-mutate-hold-and-gates | [todo-01] | scratch_hold.py, gate/hook wiring, doctrine |
| todo-03-prove | [todo-02] | test evidence, pr-check PASS |
| todo-04-converge | [todo-03] | PR + handoff |

## Property evidence matrix

| evidence_id | SP | method | expected | status |
|-------------|----|--------|----------|--------|
| EV-SP-01 | SP-01 | `git rev-parse HEAD` | locked SHA | not_run |
| EV-SP-02 | SP-02 | park WIP rejected; /tmp deny; restore roundtrip | pass | not_run |
| EV-SP-03 | SP-03 | `make pr-check` | PASS | not_run |

## Out of scope

- Re-ignoring `WIP/` or undoing sacred WIP commit
- Deleting WIP corpus
- Free-form mutate without PE lease / @autonomy packet
- Force-push, admin-merge, secret exfil
- Weakening scanners for green

## Convergence

| Field | Value |
|-------|-------|
| current_state | `draft` |
| implementation_ready | `false` until W0 baseline+preflight+envelope complete |
| execute_via | `@environment/program-execution` → Program Lock → `@autonomy` (`program_deploy_max_autonomy`) → adapters |
| minimum_safe_next_action | Fill W0 SHA; status→`executable`; Build / `/autonomy`+PE — do not free-form implement |

### Confirmation (2026-08-12)

| Question | Answer |
|----------|--------|
| Was `_TEMPLATE.plan.md` used originally? | **No** — first drafts were CreatePlan design memos |
| Is this file template-conformant now? | **Yes** — rewritten onto template + PE execute section |
| Flows through PE + max @autonomy? | **Yes when status=`executable` and Build/`/autonomy` launched** — profile `program_deploy_max_autonomy`, `autonomous_merge: false`, L4 plan-Build merge after green |
