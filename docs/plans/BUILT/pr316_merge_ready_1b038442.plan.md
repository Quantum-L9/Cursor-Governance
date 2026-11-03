---
name: Make PR 316 merge-ready on PostgreSQL 15
overview: Publish local commit 1b038442 on existing pull request 316 after make test-odoo
  exits 0 on the accepted PostgreSQL 15 fixture. Do not open a new pull request. Do
  not merge.
todos:
- id: rebind-head
  content: Confirm wt-linda-native-dispatch is clean at 1b0384423390118702b0a8e5a22bbd90586bf098
    on fix/linda-no-reservation-dispatch and that origin/fix/linda-no-reservation-dispatch
    is still 53b18fd90046696e946a0d8e1e60e88595a5e143. Stop when either SHA differs.
  status: completed
- id: roster-proof
  content: In the Linda worktree run make test-odoo against template odoo_test_tpl_ee_c9e8a81f52f23680.
    Leave TEST_ENV_ALLOW_NEW_TEMPLATE unset. Leave TEST_ENV_PARITY unset. Record the
    receipt path.
  status: completed
- id: repair-roster
  content: When make test-odoo exits 0, change no file and keep the receipt. When
    it fails inside plasticos_logistics, repair that failure, bump the module version,
    and rerun make test-odoo. When it fails outside plasticos_logistics, stop and
    report the log path.
  status: completed
- id: publish-316
  content: After the roster receipt is green, run l4_local.py authorize-release in
    the Linda worktree, then PR_STACK=auto PR_REMEDIATE=0 make pr so existing pull
    request 316 updates. The finish reply contains the pull request URL. Do not merge.
  status: cancelled
isProject: false
built: true
status: built
---

# PLAN: Make PR 316 merge-ready on PostgreSQL 15

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `make-pr-316-merge-ready-on-postgresql-15_9ac81046.plan.md`

## Objective (from PLAN_DOCUMENT)

Publish local commit 1b038442 on existing pull request 316 after make test-odoo exits 0 on the accepted PostgreSQL 15 fixture. Do not open a new pull request. Do not merge.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | make test-odoo in /Users/ib-mac/IB-Odoo_19 (LOCAL)/wt-linda-native-dispatch exits 0 on template odoo_test_tpl_ee_c9e8a81f52f23680 with image postgres:15 | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | origin/fix/linda-no-reservation-dispatch contains 1b0384423390118702b0a8e5a22bbd90586bf098 and matches the GitHub head of pull request 316 | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | The finish reply contains the URL of pull request 316 | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** worktree /Users/ib-mac/IB-Odoo_19 (LOCAL)/wt-linda-native-dispatch, branch fix/linda-no-reservation-dispatch at 1b0384423390118702b0a8e5a22bbd90586bf098, plasticos_logistics Linda cancellation and issuance tests, publication of existing pull request 316 into Staging

**Out:**
- merging pull request 316
- Contract 02 and pull request 318
- pull request 314
- rebuilding odoo_test_tpl_ee_c9e8a81f52f23680
- switching the compose image to postgres:16
- a new pull request or a base of origin/main
- the dirty checkout feat/crm-lead-material-identity
- stash@{0} on the Linda worktree

## Critical path (seed)

rebind-head → roster-proof → repair-roster → publish-316

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: One module on one open pull request, plus a full-roster test clone of the existing PostgreSQL 15 template.
- Rollback: Do not push. Leave origin/fix/linda-no-reservation-dispatch at 53b18fd90046696e946a0d8e1e60e88595a5e143. Local commits stay in the worktree.

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: Module proof, pr-check, and install-smoke already passed. Full roster proof and publication are still open. PostgreSQL 15 is accepted.
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Make PR 316 merge-ready on PostgreSQL 15

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every `<parameter>` is an instance slot. Backtick tokens are the closed vocabulary for that field. Replace each parameter before status becomes `executable`. Leave no sample instance in a delivered plan.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **Rename to:** `<snake_case_name>_<8hex>.plan.md` before execute.
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
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

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
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
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
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: <todo_id>
    content: <todo_content>
    status: pending
```

## Build evidence (auto)

- detected_at: `2026-10-27T22:58:45Z`
- conversation_id: `bc1d64a5-f2e7-4350-83b8-4142197daf6f`
- generation_id: `b5dd5941-25f2-4347-b496-380ecd1376d5`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/bc1d64a5-f2e7-4350-83b8-4142197daf6f/bc1d64a5-f2e7-4350-83b8-4142197daf6f.jsonl`
- todos at build time:
- `rebind-head`: completed
- `roster-proof`: completed
- `repair-roster`: completed
- `publish-316`: cancelled

