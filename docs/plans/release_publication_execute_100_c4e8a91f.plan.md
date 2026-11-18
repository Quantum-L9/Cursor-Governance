---
name: Make release publication executable
overview: "Raise skill/l9-release-publication from the scored 50 percent gaps to 100 percent on lifecycle, async wait, error handling, observability, configuration, and tests by replacing prose steps 3-10 with one fail-closed runner. GAR architecture is settled: extend the existing skill, do not create a second agent. MEMORY_PREFETCH namespace=l9-graphiti-memory snapshot_digest=2a8b4264368940756e2c334e350..."
todos:
  - id: T1
    content: "Add run_release_publication.py. Default mode only observes. It checks the existing tag verifier, reads the admission receipt from --admission-receipt, selects one workflow run, stops with APPROVAL_REQUIRED while a run is waiting, allows one WORKFLOW_DISPATCH recommendation only after an admission stop, compares digests, and checks Release assets from repeated --release-asset flags. Every step prints one JSON object and the command writes one receipt file. --execute is required before any push, dispatch, or Release create."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Test the runner with a fake gh and a temp git repo. Cover admission mismatch, approval wait, a second dispatch refusal, a missing Release, digest mismatch, and the receipt file. Assert observe mode never invokes push or release create."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Point SKILL.md steps 3-10 at the runner and its flags. Keep the fail-closed rules: no approval on the operator's behalf, no deploy, no retag, and the 2.6.0 sdist mismatch stays a stop until a matching run exists."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Run the skill pack validators and the skill pytest suite from the release worktree. Do not claim 100 percent unless those commands pass."
    status: pending
    phase: execute
    depends_on: [T2, T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Make release publication executable

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `make-release-publication-executable_0bb5301f.plan.md`

## Objective (from PLAN_DOCUMENT)

Raise skill/l9-release-publication from the scored 50 percent gaps to 100 percent on lifecycle, async wait, error handling, observability, configuration, and tests by replacing prose steps 3-10 with one fail-closed runner. GAR architecture is settled: extend the existing skill, do not create a second agent. MEMORY_PREFETCH namespace=l9-graphiti-memory snapshot_digest=2a8b4264368940756e2c334e35063945d7fa90d8dbae8b069867ae78f2e79e07 conflicts=0. route_plan depth=deep omit_gates=[].

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | scripts/run_release_publication.py returns structured JSON for tag identity, admission match, approval wait, dispatch-once, digest match, and GitHub Release presence | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | The runner writes one publication receipt and performs no push, dispatch, or Release create unless --execute is set | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | With --execute it still refuses environment approval, deploy, tag recreate, and force-push | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | SKILL.md steps 3-10 invoke that runner instead of leaving those steps as prose | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | pytest for the runner and verify_release_tag.py passes, and validate_skill_pack.py plus validate_exemplary_skill.py pass | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | A re-score of the six gap dimensions is 100 percent because each now has an executable check, a structured error, a receipt field, a flag, and a test | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** /Users/ib-mac/tmp/l9-memory-release-skill-20261027/skill/l9-release-publication/scripts/run_release_publication.py, /Users/ib-mac/tmp/l9-memory-release-skill-20261027/skill/l9-release-publication/tests/test_run_release_publication.py, /Users/ib-mac/tmp/l9-memory-release-skill-20261027/skill/l9-release-publication/SKILL.md, /Users/ib-mac/tmp/l9-memory-release-skill-20261027/skill/l9-release-publication/references/admission-receipt.md, /Users/ib-mac/tmp/l9-memory-release-skill-20261027/skill/l9-release-publication/references/github-release.md

**Out:**
- Pull requests 101, 102, and 103
- Tag recreate, force-push, environment approval, and deployment
- PyPI upload from the laptop
- Cursor-Governance rebind
- The dirty or unrelated checkout at /Users/ib-mac/l9-graphiti-memory-1

## Critical path (seed)

T1 → T2 → T3 → T4

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: A runner bug can push a tag, dispatch publish.yml, or open a GitHub Release for Quantum-L9/l9-graphiti-memory. It must not approve an environment or deploy.
- Rollback: Delete scripts/run_release_publication.py and its test, and restore SKILL.md to call only verify_release_tag.py. No tag or workflow is rolled back because observe mode publishes nothing.

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: Plan is ready to Build. U1 stays bounded: do not stack this skill onto PRs 101, 102, or 103.
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Make release publication executable

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
