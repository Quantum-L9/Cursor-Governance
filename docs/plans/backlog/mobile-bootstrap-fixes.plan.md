---
name: Claude Code Mobile bootstrap readiness remediation
overview: "NOT LANDED. Shelf=backlog (not current). Repo-side Claude Web/Mobile adapter contract is already COMPLETE in docs/CLAUDE_SURFACE_PARITY.md; these 12 todos are still pending and must be revalidated against origin/main before Build. Intent: make the Claude Code cloud/mobile adapter self-healing and truthful — wrong-workspace wiring, false READY, MCP drift, command parity; isolate the capability-broker gap."
todos:
  - id: T1
    content: "Add a cloud-only installer-drift self-heal to SessionStart: when the receipt names a different workspace or an older governance revision than live, re-run install.sh bounded and fail-open, then re-read the receipt"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Replace the SSOT SKILL.md file count with a loadable-skill probe over the real discovery paths and report both numbers"
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Mark receipt-derived statuses STALE in the SessionStart projection when receipt.workspace differs from the session project dir, instead of printing READY verbatim"
    status: pending
    phase: execute
    depends_on: []
  - id: T4
    content: "Detect and remove a pre-commit-generated .git/hooks/pre-commit during cloud SessionStart, matching the prohibition the helper already documents"
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "Make .mcp.json a managed artifact: reconcile it from mcp.template.json when it carries the L9 managed marker, and update the committed workspace .mcp.json to the 6-server broker template"
    status: pending
    phase: execute
    depends_on: []
  - id: T6
    content: "Allow gate_shape and note on the precondition definition in the memory-enforcement schema so the contract the doctrine requires validates"
    status: pending
    phase: execute
    depends_on: []
  - id: T7
    content: "Invoke validate_claude_env.py from install.sh and downgrade a receipt status on non-zero, so adapter self-validation failures surface instead of sitting unread"
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T8
    content: "Extend the MCP inventory scan set to the Claude Code surface (.mcp.json in workspace and $HOME/.claude.json) so it stops reporting an empty server list"
    status: pending
    phase: execute
    depends_on: []
  - id: T9
    content: "Add a slash-command reconciler that mirrors commands/ into <workspace>/.claude/commands, and call it from install.sh beside the skill reconciler"
    status: pending
    phase: execute
    depends_on: []
  - id: T10
    content: "Add regression tests: drift self-heal fires only on mismatch, loadable-skill probe counts load paths, STALE projection on workspace mismatch, stale git hook removed, .mcp.json reconcile is idempotent"
    status: pending
    phase: execute
    depends_on: [T1, T2, T3, T4, T5]
  - id: T11
    content: "Deploy the capability broker and run sessions in the self-hosted ccpool_ environment it is built for, then set L9_CAPABILITY_BROKER_URL"
    status: pending
    phase: execute
    depends_on: []
  - id: T12
    content: "Add api.context7.io to the environment's Custom allowed-domains list; the same edit forces a setup-script cache rebuild, which is what lands the T1 installer fix"
    status: pending
    phase: execute
    depends_on: []
isProject: false
---

# PLAN: Claude Code Mobile bootstrap readiness remediation

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `claude-code-mobile-bootstrap-readiness-remediation_c549432e.plan.md`

## Objective (from PLAN_DOCUMENT)

Make the Claude Code cloud/mobile adapter self-healing and truthful: eliminate the wrong-workspace wiring class, stop READY being reported for artifacts that never load, reconcile the drifted MCP surface, and isolate the capability-broker gap as the one remaining infrastructure blocker.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | A session whose bootstrap receipt names a workspace other than CLAUDE_PROJECT_DIR re-runs install.sh and ends with receipt.workspace == CLAUDE_PROJECT_DIR | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | SessionStart reports a loadable-skill count read from the actual load paths, and that count is 51 in this workspace | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | When receipt.workspace != CLAUDE_PROJECT_DIR, SessionStart prints settings/skills/rules as STALE(<value>) instead of the bare value | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | validate_claude_env.py exits 0 and is invoked by install.sh | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | Workspace .mcp.json declares the same server set as mcp.template.json (6 servers) | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | No .git/hooks/pre-commit generated by pre-commit survives a cloud SessionStart | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | inventory_mcp_servers.py lists the workspace .mcp.json servers instead of reporting none | quality_gate | observe during PE verify / make pr-check | true |
| SP-08 | pytest tests/ops/scripts and environment/agents/adapters/claude-code/tests PASS | quality_gate | observe during PE verify / make pr-check | true |
| SP-09 | make pr-check PASS | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh, environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh, environment/agents/adapters/claude-code/install.sh, environment/agents/adapters/claude-code/memory/memory-enforcement.schema.json, ops/scripts/inventory_mcp_servers.py, ops/scripts/reconcile_claude_commands.py (new), workspace .mcp.json, tests for the above, ops/secrets/k8s/broker-deployment.yaml + deploy/broker-kubernetes.yaml

**Out:**
- Changing the broker's identity model — it is complete as designed for a ccpool_ self-hosted pool
- Introducing any second authentication path beside the existing ccr session assertion
- Editing mcp.template.json's Authorization header, which is the existing design's contract
- Pasting any Infisical, Sonar, Semgrep or Graphiti credential onto this surface
- Memory readiness, memory hydration and memory MCP behaviour
- Re-pasting the account Setup script as the remediation mechanism
- Installing the uploaded l9-plan v2.0.0 over SSOT v4.0.0
- Any git push, PR open or merge from plan mode

## Critical path (seed)

T1 → T2 → T3 → T5 → T7 → T10

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: session_start_claude_governance.sh and session_deps_cloud.sh run on every cloud session across every consumer repository that commits the adapter, so a defect here degrades or blocks session startup fleet-wide rather than in one repo. install.sh additionally runs on CLI and Desktop. .mcp.json reconciliation touches the MCP surface every session start. The fail-open contract on both hooks is the containment boundary and must be preserved.
- Rollback: Every change is confined to four adapter files plus two ops scripts and a new reconciler; git revert of the feature branch restores d424f588-equivalent behaviour. The self-heal is gated on CLAUDE_CODE_REMOTE=true and on an explicit drift comparison, so setting L9_CLAUDE_SELFHEAL=0 disables it without a code change. .mcp.json changes are recoverable from mcp.template.json. No infrastructure, credential or remote state is mutated, so there is nothing to roll back outside the repository.

## Convergence (seed)

- status: partial
- next_skill: l9-ynp
- stop_reason: U2 is resolved by the platform contract: the environment cache rebuilds on a setup-script or allowed-hosts change and at ~7 days, so T12 and the T1 rollout are one lever and B-01 self-heals passively within a week. U3 is no longer 'is there an issuer' but 'when do sessions run in the ccpool_ pool the broker already targets' — an operator scheduling question. T11 stays infrastructure-blocked with a precise cause. T1-T10 and T12 are unblocked and require no architectural change.
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: Claude Code Mobile bootstrap readiness remediation

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
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

Live execution is one command. Do not hand-run pec, L4, or inner compile
scripts from this template.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
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
| captured_at | 2026-08-20 (session) |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/home/user/Cursor-Governance` |
| ssot_clone | `/root/.cursor-governance` @ `b406feeb4734f7029c36d718a68b004cacd6a68a` (branch `main`) |
| branch | `claude/mobile-bootstrap-readiness-audit-aoi0mn` |
| commit_sha | `941ab775c3e6d2a4d8b0425b10e9cb32b9a8e403` |
| dirty | `false` |
| plan_document | `docs/plans/claude-code/mobile-bootstrap-fixes.plan.json` |
| artifact_hashes | `{ "docs/plans/claude-code/mobile-bootstrap-fixes.plan.json": "sha256:faa52899491e81bdbcd4d23f71cf08eb2bef711f4c30e651384ce7a6c10054c7" }` |
| allowed_local_dirt | `.cursor/plans/**`, `reports/**` (gitignored working copies) |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

**Environment fact pinned into this baseline.** `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`, while the capability broker targets a self-hosted `ccpool_` pool (`broker-deployment.yaml:65`; `broker_identity.py:143`). That mismatch is the whole of T11 and is not a code defect.

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
