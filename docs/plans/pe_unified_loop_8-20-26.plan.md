---
name: PE unified-loop seam wiring: worker dispatch, receipt-to-distill signals, Graphiti evidence intake, autonomy projection (clean branch off main)
overview: "Close the Program Execution development loop end-to-end by wiring the four verified-but-unconnected seams on top of what already landed on Quantum-L9/Cursor-Governance main: (1) controller-side worker dispatch through the Peer Execution Core to thin providers (claude-code-direct / codex / cursor-background / ci) under EXECUTION_ROUTING_POLICY; (2) program receipts into the subagent-signal publi..."
todos:
  - id: todo-01
    content: "Baseline + clean branch: lock origin/main full SHA; create pe/unified-loop from it in a dedicated worktree (rule 46); record baseline receipt"
    status: pending
    phase: execute
    depends_on: []
  - id: todo-02
    content: "Re-land the 8 unmerged admission/gate fixes on the clean branch (re-cut from the clean 6c65557 content with explicit pathspecs; NOT from the contaminated branch tip; verify each against main before landing)"
    status: pending
    phase: execute
    depends_on: [todo-01]
  - id: todo-03
    content: "Dispatch seam: new pec/dispatch.py — at render-contract, resolve execution profile via identity_binding/peer_readiness, consult EXECUTION_ROUTING_POLICY + capability probes, invoke peer_execution.runner (subprocess thin providers: claude-code-direct, codex, cursor-background) with Worker Brief + context manifest; map CanonicalProviderResult into attempt-receipt pre-submission; worker_cannot_self_verify invariant preserved; fallback to manual worker brief when CAPABILITY_UNSUPPORTED"
    status: pending
    phase: execute
    depends_on: [todo-02]
  - id: todo-04
    content: "Signal seam: call outcome_publisher at record-attempt, verify, evaluate-gate, export-handoff — receipt_projection — distill_queue enqueue (dry-run observable); agent-scoped atomic facts only"
    status: pending
    phase: execute
    depends_on: [todo-03]
  - id: todo-05
    content: "Evidence intake: collect_evidence.py memory-lookup flag using integrations/graphiti/context_reader (read-only; fails closed offline; never writes memory from admission)"
    status: pending
    phase: execute
    depends_on: [todo-02]
  - id: todo-06
    content: "Autonomy projection: claim-time autonomy_action_id + campaign-packet skeleton emission via autonomy-control-plane contract_mapper (emission only — no autonomy-side mutation)"
    status: pending
    phase: execute
    depends_on: [todo-02]
  - id: todo-07
    content: "Routing + conformance: add codex preference row to EXECUTION_ROUTING_POLICY for tightly-scoped mechanical work; golden vectors: policy enforcement, no-match returns CAPABILITY_UNSUPPORTED, worker_cannot_self_verify; extend shared peer-execution lifecycle test with the dispatch path"
    status: pending
    phase: execute
    depends_on: [todo-03, todo-06]
  - id: todo-08
    content: "Converge: make sync-generated + template manifest regen; full suites (PE conformance, controller, autonomy, compile, campaign-schema); kernels; L4 authorize-release; open PR into main via the governance publish flow; remediate via l9-pr-remediation; merge per operator override (bottom-up); export handoff"
    status: pending
    phase: execute
    depends_on: [todo-04, todo-05, todo-07]
isProject: false
---

# PLAN: PE unified-loop seam wiring: worker dispatch, receipt-to-distill signals, Graphiti evidence intake, autonomy projection (clean branch off main)

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `pe-unified-loop-seam-wiring-worker-dispatch-receipt-to-distill-signals-graphiti-evidence-intake-autonomy-projection-clean-branch-off-main_3036b0a8.plan.md`

## Objective (from PLAN_DOCUMENT)

Close the Program Execution development loop end-to-end by wiring the four verified-but-unconnected seams on top of what already landed on Quantum-L9/Cursor-Governance main: (1) controller-side worker dispatch through the Peer Execution Core to thin providers (claude-code-direct / codex / cursor-background / ci) under EXECUTION_ROUTING_POLICY; (2) program receipts into the subagent-signal publisher and Graphiti distill queue; (3) admission evidence intake from Graphiti via context_reader; (4) claim-time autonomy projection via the merged autonomy-control-plane mappers. ALL WORK LANDS ON A NEW CLEAN BRANCH CREATED FROM origin/main (Quantum-L9/Cursor-Governance) — never on main directly, never on the contaminated pe/pipeline-fixes branch, never in any other repo.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | SC-01: baseline locked: origin/main full SHA recorded at execution start; new branch pe/unified-loop created from that SHA with a clean tree (no foreign files). | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | SC-02: re-land of the 8 unmerged admission/gate fixes (blueprint_ops, accept/collect tools, union-diff verify, L4 named-roots, heredoc-safe matching, memory session-id flags) verified present on the branch with the golden admission loop test passing (main was verified NOT to contain them). | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | SC-03: dispatch integration test passes: render-contract resolves an execution profile and probes a provider and invokes it; the provider result maps to an attempt-receipt pre-submission; worker_cannot_self_verify invariant holds. | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | SC-04: record-attempt/verify/evaluate-gate/export-handoff call outcome_publisher and enqueue distill jobs (observable via dry-run queue listing). | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | SC-05: collect_evidence memory-lookup flag returns Graphiti context read-only and fails closed when Graphiti is unreachable (no memory mutation from admission). | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | SC-06: claim emits per-task autonomy_action_id plus packet skeleton via contract_mapper; unit test asserts the mapping without any autonomy-side mutation. | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | SC-07: EXECUTION_ROUTING_POLICY extended with codex for tightly-scoped mechanical work; no-match routing returns CAPABILITY_UNSUPPORTED; routing golden vectors pass. | quality_gate | observe during PE verify / make pr-check | true |
| SP-08 | SC-08: all existing suites stay green: PE conformance (142+), controller (25+), autonomy (56+), compile (5+), campaign-schema (2), plus the shared peer-execution lifecycle test. | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** environment/program-execution/core/program-execution-controller-template/scripts/pec/ (dispatch.py new; contracts.py + controller.py call sites; tests/), environment/program-execution/integrations/worker-dispatch/ (new thin module if controller-internal placement proves insufficient), environment/program-execution/registry/EXECUTION_ROUTING_POLICY.yaml (additive preference row for codex), environment/program-execution/scripts/collect_evidence.py (optional Graphiti intake flag), environment/program-execution/scripts/tests/ + core controller-template scripts/tests/ (new tests), re-landed admission/gate fixes: environment/program-execution/scripts/{blueprint_ops,accept_blueprint,collect_evidence,compile_campaign_source}.py + tests, core template RUNBOOK + MANIFEST regenerations, ops/autonomy/{command_parse,local_execution_gate,worktree_isolation_gate}.py, environment/agents/adapters/claude-code/hooks/memory_*.py, tests/ops/autonomy/*, regenerated manifests via make sync-generated + template write_manifest (canonical generators only)

**Out:**
- Schema changes to Program Lock / Blueprint v2 required fields (no relaxation, no new required fields)
- Model-level inference routing (ADR-0020 defers provider-neutral model routing — out of scope)
- Autonomy-side mutation (this plan only PROJECTS to autonomy; packets/lanes are emitted, not executed here)
- The contaminated origin/pe/pipeline-fixes branch (abandoned; re-cut from clean commit content)
- Any repo other than Quantum-L9/Cursor-Governance
- Direct commits to main

## Critical path (seed)

todo-01 → todo-02 → todo-03 → todo-04 → todo-07 → todo-08

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Controller call sites (contracts/controller.py) are the execution heart of every future program; mitigations: additive call sites, manual-worker fallback preserved, full controller suite before PR.
- Rollback: git restore scoped paths on the pe/unified-loop branch; dispatch + signal call sites are additive — removal restores prior behavior; PR closable; no schema changes.

## Convergence (seed)

- status: partial
- next_skill: l9-ynp
- stop_reason: U1 (codex capability receipt) resolves at preflight PV-05; plan is execution-ready on the verified seam evidence
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: PE unified-loop seam wiring: worker dispatch, receipt-to-distill signals, Graphiti evidence intake, autonomy projection (clean branch off main)

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_YYYY-MM-DD.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

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

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease (`COMPATIBILITY.yaml` / autonomy-control-plane bridge). Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

1. **Attach** [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md).
2. **Project this plan → Blueprint artifacts** (instantiate under `$HOME/.l9/programs/<program_id>/` — never mutate sealed `environment/program-execution/core/` templates in place):

   | Plan section | PE Blueprint / Controller artifact |
   |--------------|-------------------------------------|
   | metadata / objective | `PROGRAM.yaml` / program identity |
   | immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA |
   | execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
   | execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
   | capability_preflight | Controller reconcile + gate probes before claim |
   | property_evidence_matrix | Task Card `validation` / evidence catalog refs |
   | rollback | Task Card `rollback` + recovery receipts |
   | convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

3. **Validate + bootstrap Controller** (from controller template RUNBOOK):

```bash
# from instantiated controller workspace (paths illustrative)
python scripts/pec.py bootstrap --workspace "$HOME/.l9/programs/<program_id>/runtime" \
  --blueprint "$HOME/.l9/programs/<program_id>/blueprint"
python scripts/pec.py reconcile --workspace … --repository <repository_id>=$(pwd)
python scripts/pec.py status --workspace …
python scripts/pec.py next --workspace …
```

4. **Admit exact task scope** — draft/register Source Contract ⊂ Task Card ceiling; then `claim` → `prepare` → `render-contract`. Worker receives **only** Rendered Contract + Worker Brief + worktree.
5. **Map Program task → autonomy campaign** via `environment/program-execution/integrations/autonomy-control-plane/` (`map_program_contract` / bridge). Set each mutating Task Card `autonomy_action_id` (e.g. `pes.<wave>.<task>`).
6. **Orchestrate under [@autonomy](commands/autonomy.md)** — load `l9-bounded-autonomy` Protocols A–D; campaign authorization **packet** aligned to Program Lock digest + declared branches/PRs (see AUTONOMY_BRIDGE vocabulary). Spawn ready `work` Tasks / background `poll` Tasks; main continues (no `AwaitShell` on poll).
7. **L4 local autonomy** inside the Program lease: local commits only until `ops/autonomy/l4_local.py authorize-release` → scoped push/PR → `l9-pr-remediation` Converge. Launching this plan through PE+`/autonomy` **or** clicking Build **is** merge authorization for this stack after green+mergeable (bottom-up older PRs first).
8. **Record + verify + handoff** — `pec.py record-attempt` → `verify` → `export-handoff`. Controller recommends; program owner accepts terminal verdict. Graphiti PICKUP on close (Protocol D) — observability only, never competing task claim.

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

