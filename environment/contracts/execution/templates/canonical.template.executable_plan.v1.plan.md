---
name: "<plan_title>"
overview: "<overview>"
todos:
  # Repeat this mapping once per DAG node. Roots use depends_on: [].
  - id: <todo_id>
    content: "<todo_content>"
    status: pending
    phase: <phase>
    depends_on: [<depends_on_todo_id>]
    side_effect_ref: <side_effect_id>
    evidence_property_refs: [<success_property_id>]
isProject: false
kernel_pass:
  bound_path: ""
  improve:
    kernel: kernels/Improve.md
    ran_at: ""
    body_sha256:
    deltas: []
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: ""
    body_sha256:
    deltas: []
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: ""
    body_sha256:
    deltas: []
---

# PLAN: <plan_title>

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every `<parameter>` is an instance slot. Backtick tokens are the closed vocabulary for that field. Replace each parameter before status becomes `executable`. Leave no sample instance in a delivered plan.
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `<snake_case_name>_<8hex>.plan.md` before execute.
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
  provider_ref: <provider_ref>
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease (`COMPATIBILITY.yaml` / autonomy-control-plane bridge). Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile
scripts from this template.

```bash
make -C "<governance_root>" campaign INTENT=<intent_ref>
```

`run_campaign.py` projects the plan into Blueprint artifacts under
`<program_runtime_root>`, admits the lock, executes every task, stacks
PRs, and closes into `<completed_campaign_root>`. Never mutate sealed
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

### Adapter routing (from `<routing_policy_ref>`)

| Work class | provider_ref |
|------------|----------------|
| interactive local repair | `<provider_ref>` |
| repository implementation | `<provider_ref>` |
| verification | `<provider_ref>` |
| remote PR/merge actions | `<provider_ref>` |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: <packet_id>
authority: <authority>
profile: <profile>
authority_profile: <authority_profile>
autonomous_merge: false
plan_ref: <plan_path>
plan_id: plan.<domain>.<slug>.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: <program_id>
  program_lock_digest: <program_lock_digest>
  blueprint_ref: <blueprint_ref>
  runtime_ref: <runtime_ref>
  provider_ref: <provider_ref>
  execution_profile_ref: <execution_profile_ref>
  autonomy_provider_id: <autonomy_provider_id>
declared_prs: [<pull_request>]
declared_branches: [<branch>]
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
created_by: "<created_by>"
```

### Phase-0 action table ↔ PE Task Cards

Derive one row per frontmatter todo and one optional `poll` row when a remote poll is in scope. Columns are the projection; values are parameters.

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| `<todo_id>` | `<pe_task_id>` | `<wave>` | `[<depends_on_todo_id>]` | `<mutation>` | `<lock_keys>` | `<isolation_key>` | `<autonomy_action_id>` | `<kind>` | `<provider_ref>` |
| `<poll_id>` | — | `<wave>` | `[<depends_on_todo_id>]` | `<mutation>` | `<lock_keys>` | `<isolation_key>` | `<autonomy_action_id>` | `poll` | `<provider_ref>` |

`kind` ∈ `work` | `poll`. Omit the poll row when no poll is in scope.

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A (ready `work` Tasks in one message) / B (`poll` + `run_in_background: true`) / C (join) / D (PICKUP). Autonomy must not bypass wave order or Program Lock drift checks (`program_lock_stale_or_invalid` → stop).

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint not accepted / Controller not bootstrapped; Program Lock drift; capability preflight blocked; DAG cyclic; envelope or Task Card ceiling incomplete; blocking unknowns remain; autonomy revoke / lease expired.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.<domain>.<slug>.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `<status>` — `draft` \| `preflight_blocked` \| `executable` \| `in_progress` \| `validation_failed` \| `converged` \| `superseded` |
| is_project | *(frontmatter `isProject`)* |
| owner | `<owner>` |
| created_at | `<created_at>` |
| updated_at | `<updated_at>` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `<planning_ssot>` |
| plan_class | `<plan_class>` — `bounded_execution_contract` \| `migration_plan` \| `retirement_plan` \| `remediation_plan` \| `deployment_plan` \| `refactor_plan` \| `integration_plan` \| `recovery_plan` \| `custom` |
| redesign_allowed | `<redesign_allowed>` |
| follow_on_schema_evolution_separate | `<follow_on_schema_evolution_separate>` |
| framing_notes | Execute via @environment/program-execution + subordinate @autonomy; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `<captured_at>` |
| repository | `<repository>` |
| workspace | `<workspace>` |
| ssot_clone | `<ssot_clone>` |
| branch | `<branch>` |
| commit_sha | `<commit_sha>` — full 40-char SHA (PLAN-SCHEMA-001) |
| dirty | `<dirty>` — `true` \| `false` |
| artifact_hashes | `<artifact_hashes>` |
| allowed_local_dirt | `<allowed_local_dirt>` |
| overlap_policy | `<overlap_policy>` — `stop_if_dirty_overlaps_may_modify` \| `require_clean_tree` \| `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

`<mission>`

### Success properties

One row per property. `evidence_type` ∈ `filesystem` | `runtime_behavior` | `structural` | `quality_gate` | `repository_state` | `network_observation` | `proof_receipt` | `human_confirmation`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| `<success_property_id>` | `<property>` | `<evidence_type>` | `<proof>` | `<blocking>` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `<capability_preflight_ref>`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.<plan_id>` |
| source_ref | `<plan_id>` |
| phase_id | `preflight` |
| blocking | `<blocking>` |
| immutable_baseline_ref | `<immutable_baseline_ref>` |
| baseline_verified | `<baseline_verified>` |
| drift_detected | `<drift_detected>` |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| `<probe_id>` | `<capability>` | `<command_or_action>` | `<pass_criteria>` | `<blocking>` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `<write_allow>`
- **write_deny:** `<write_deny>`
- **delete_allow:** `<delete_allow>`

### Commands

- **allow:** `<commands_allow>`
- **deny:** `<commands_deny>`

### Network

| Field | Value |
|-------|-------|
| mode | `<network_mode>` — `none` \| `read_only` \| `named_services_only` \| `existing_tunnel_only` \| `bounded_external_write` |
| allowed_services | `<allowed_services>` |

### Secrets

| Field | Value |
|-------|-------|
| access | `<secrets_access>` — `none` \| `read_only_named` \| `runtime_injected_only` |
| redaction_required | `<redaction_required>` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per `<todo_id>`.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| `<todo_id>` | `<side_effects>` | `<idempotency>` | `<retry>` | `<compensation>` | `<irreversible>` |

`side_effects` ∈ `none` | `filesystem_read` | `filesystem_mutation` | `destructive_filesystem_mutation` | `network_read` | `network_write` | `database_read` | `database_write` | `external_state_mutation` | `human_approval`

`idempotency` ∈ `safe_to_repeat` | `safe_with_dedupe` | `unsafe_blind_repeat` | `non_idempotent`

`retry` ∈ `none` | `manual_only` | `retry_once` | `bounded_retry`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| `<todo_id>` | `<bounded_context>` | `<layer>` | `<owning_contract>` | `<prohibited>` |

`layer` ∈ `control_plane` | `data_plane` | `chassis` | `ops` | `runtime` | `policy` | `assurance` | `memory` | `graph` | `docs` | `external_system`

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.<plan_id>` |
| source_execution_ref | `<plan_id>` |
| supported | `<rollback_supported>` — `true` \| `false` |
| automatic_allowed | `false` |
| approval_required | `<approval_required>` |
| trigger_conditions | `<trigger_conditions>` |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `<code_rollback_mode>` | `git_restore_scoped_paths` \| `revert_commit` \| `none` |
| data | `<data_rollback_mode>` | `none` \| `restore_snapshot` \| `compensating_transaction` \| `manual_recovery` |
| external_state | `<external_state_rollback_mode>` | `none` \| `corrective_append_only_record` \| `manual_recovery` |
| local_state | `<local_state_rollback_mode>` | `none` \| `git_restore_scoped_paths` \| `manual_recovery` |

### Irreversible operations

- `<irreversible_operation>` (PLAN-SCHEMA-010)

### Rollback verification

- `<rollback_verification>`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `<complexity>` — `low` \| `medium` \| `high` \| `critical` |
| uncertainty | `<uncertainty>` — `low` \| `medium` \| `high` \| `critical` |
| blast_radius | `<blast_radius>` — `low` \| `medium` \| `high` \| `critical` |
| architectural_boundaries_crossed | `<architectural_boundaries_crossed>` |
| external_systems_touched | `<external_systems_touched>` |
| migration_required | `<migration_required>` |
| unknown_dependency_count | `<unknown_dependency_count>` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | `<inventory_receipt_path>` |
| categories | `<inventory_category>` — `delete` \| `migrate_then_delete` \| `keep` \| `replace` \| `skip` |
| checksum_required | `<checksum_required>` |
| destructive_gate_required_for | `<destructive_gate_required_for>` |

## Gated write pipeline *(optional — irreversible or external writes)*

- **gates (ordered):** `<write_gates>`
- **dedupe_before_non_idempotent_write:** `<dedupe_before_non_idempotent_write>`
- **bounded_write_count:** `<bounded_write_count>`
- **receipt_required:** `<receipt_required>`

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| `<regeneration_id>` | `<regeneration_source>` | `<required_change>` | `<regeneration_validation>` |

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
| `<todo_id>` | `<owner>` | `<layer>` | `[<depends_on_todo_id>]` | `<outputs>` |

**Critical path:** `<critical_path>`

**Forbidden edges:** `<forbidden_edges>`

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| `<evidence_id>` | `<success_property_id>` | `<evidence_kind>` | `<method>` | `<command>` | `<expected_positive>` | `<evidence_status>` |

`evidence_kind` ∈ `repository_state_evidence` | `property_evidence` | `structural_evidence` | `runtime_behavior_evidence` | `quality_gate_evidence`

`evidence_status` ∈ `not_run` | `passed` | `failed`

## Stress and disconfirm

### Disconfirming cases

- `<disconfirming_case>`

### Assumption failure conditions

- `<assumption_failure>` (PLAN-SCHEMA-013)

### Blast radius notes

- `<blast_radius_note>`

### Rollback constraints

- `<rollback_constraint>`

## Out of scope

- `<out_of_scope_item>`
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `<separate_plan_required>` |

| priority | change | why |
|----------|--------|-----|
| `<priority>` | `<follow_on_change>` | `<follow_on_why>` |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.<plan_id>` |
| source_ref | `<plan_id>` |
| current_state | `<current_state>` — `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `<implementation_ready>` |

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

- **required_evidence_refs:** `<required_evidence_refs>`
- **observed_evidence_refs:** `<observed_evidence_refs>`
- **missing_evidence:** `<missing_evidence>`

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `<blocker_kind>` | `<blocker_id>` | `<blocker_note>` | `<blocker_resolution>` |

`blocker_kind` ∈ `open_blocker` | `unknown`

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `<next_convergence_gate>` |
| minimum_safe_next_action | When law holds and status=`executable`, attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); project→Lock→claim→render→autonomy lanes — do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| broader_work_requires_separate_contract | `<broader_work_requires_separate_contract>` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.<domain>.<slug>.v1
  name: <plan_title>
  overview: <overview>
  status: <status>
  is_project: false
  created_at: <created_at>
architect_framing:
  planning_ssot: <planning_ssot>
  plan_class: <plan_class>
  redesign_allowed: <redesign_allowed>
  follow_on_schema_evolution_separate: <follow_on_schema_evolution_separate>
immutable_baseline:
  repository: <repository>
  commit_sha: <commit_sha>
  dirty: <dirty>
  artifact_hashes: {}
  overlap_policy: <overlap_policy>
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: <mission>
  success_properties:
    - id: <success_property_id>
      property: <property>
      evidence_type: <evidence_type>
      proof: <proof>
      blocking: <blocking>
capability_preflight_ref: <capability_preflight_ref>
execution_envelope:
  filesystem:
    write_allow: [<write_allow>]
    write_deny: [<write_deny>]
  commands:
    allow: [<commands_allow>]
    deny: [<commands_deny>]
  network:
    mode: <network_mode>
  secrets:
    access: <secrets_access>
    redaction_required: <redaction_required>
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: <rollback_contract_ref>
complexity_and_uncertainty:
  complexity: <complexity>
  uncertainty: <uncertainty>
  blast_radius: <blast_radius>
  architectural_boundaries_crossed: <architectural_boundaries_crossed>
  external_systems_touched: <external_systems_touched>
  migration_required: <migration_required>
  unknown_dependency_count: <unknown_dependency_count>
dependency_topology_ref: <dependency_topology_ref>
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: <convergence_contract_ref>
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  controller: environment/program-execution/core/program-execution-controller-template
  blueprint: environment/program-execution/core/program-execution-blueprint-template
  autonomy_provider: <autonomy_provider_id>
  autonomy_integration: environment/program-execution/integrations/autonomy-control-plane
  adapter_default: <provider_ref>
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
  - id: <todo_id>
    content: <todo_content>
    status: pending
```
