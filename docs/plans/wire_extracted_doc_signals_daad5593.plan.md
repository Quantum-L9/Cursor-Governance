---
name: Wire every extracted signal in l9-update-agent-docs into a compiled document
overview: "Every fact l9-update-agent-docs extracts (source facts, interface summaries and signatures, imports, relationships, skill contract fields, manifest and tsconfig fields, surface-analyzer parses, evidence references, quality findings) reaches at least one compiled output (a README, AGENTS.md, CLAUDE.md, INVARIANTS.md, llm.txt, filetree.md, or the receipt), and a ratchet test fails when a new extr..."
todos:
  - id: T1
    content: "Add the signal ledger ratchet: test_signal_ledger.py enumerates dataclass fields of ModuleDoc, InterfaceDoc, SourceFact, DependencyDoc, ReadmeModel, the SkillContract slots, and surface-analyzer output keys, and asserts each is read by a consumer module (renderers, doc_root, doc_llm, receipt writer). Start with an explicit UNWIRED allowlist naming today's drops; each later wiring task deletes its entries; final state is an empty allowlist"
    status: completed
    phase: execute
    depends_on: []
  - id: T2
    content: "Compile README models once in repo_docs.audit_repository before root docs and llm.txt, and pass the compiled (model, rendered) outputs into compile_missing_root_docs and render_llm_txt"
    status: completed
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Feed JS/TS imports into classify_dependencies in both compile_readme_model branches; resolve local relative imports to the sibling module path so Internal names a real target"
    status: completed
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Capture the exported function parameter list in _extract_javascript and store it in InterfaceDoc.signature"
    status: completed
    phase: execute
    depends_on: [T1]
  - id: T5
    content: "Render SkillContract.version in the skill README header and render model.authority_links as links in the Authority section; carry version onto ReadmeModel"
    status: completed
    phase: execute
    depends_on: [T1]
  - id: T6
    content: "AGENTS.md compiles a Commands section from package.json scripts and pyproject project.scripts (reuse surface_analyzers/python_project.py parse) and a Module map from the compiled README models (path link plus compiled purpose); INVARIANTS.md lists workflow name and job ids from the workflow parse"
    status: completed
    phase: execute
    depends_on: [T2]
  - id: T7
    content: "llm.txt manifest gains one entry per compiled README (path, purpose, sha256, owner l9-update-agent-docs, authority_class projection) under the existing L9_DOC_MANIFEST schema; add the policy hook in doc-surface-policy.yaml"
    status: completed
    phase: execute
    depends_on: [T2]
  - id: T8
    content: "Receipt module_readme_quality entries carry each README's evidence references and every WARN finding (rule_id, message), not only counts"
    status: completed
    phase: execute
    depends_on: [T1]
  - id: T9
    content: "Targeted tests for T3-T8, empty the ledger allowlist, add the signal-utilization law to SKILL.md (every extracted field has a named consumer; ledger is the gate), bump version to 4.4.0, add self_test token"
    status: completed
    phase: execute
    depends_on: [T3, T4, T5, T6, T7, T8]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Wire every extracted signal in l9-update-agent-docs into a compiled document

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `wire-every-extracted-signal-in-l9-update-agent-docs-into-a-compiled-document_f06c1c24.plan.md`

## Objective (from PLAN_DOCUMENT)

Every fact l9-update-agent-docs extracts (source facts, interface summaries and signatures, imports, relationships, skill contract fields, manifest and tsconfig fields, surface-analyzer parses, evidence references, quality findings) reaches at least one compiled output (a README, AGENTS.md, CLAUDE.md, INVARIANTS.md, llm.txt, filetree.md, or the receipt), and a ratchet test fails when a new extracted field has no downstream consumer.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | skills/l9-update-agent-docs/tests/test_signal_ledger.py PASSes with an empty unwired allowlist: every field of ModuleDoc, InterfaceDoc, SourceFact, DependencyDoc, ReadmeModel, SkillContract, and every surface-analyzer output key is read by a renderer, root-doc compiler, llm.txt compiler, or receipt writer | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | A TypeScript module README renders a Dependencies section whose External list names its package imports (for example openai, zod) and whose Internal list names sibling modules, instead of only raw import strings | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | A TypeScript exported function renders its parameter list on the interface line, the same way a Python function already does | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | A skill README renders the SKILL.md metadata.version and links every model.authority_links entry | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | AGENTS.md compiled from a repository with package.json scripts lists those scripts as commands, and lists each compiled README path with its compiled purpose | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | INVARIANTS.md lists each workflow's name and job ids from the workflow parse, not only the file path | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-07 | llm.txt lists every compiled README with its path, purpose, and sha256 in the L9_DOC_MANIFEST block | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-08 | The receipt records, per README, the evidence references and every WARN quality finding | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-09 | repo_docs.py compiles README models once per run and hands the same models to doc_root.py and doc_llm.py | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-10 | .venv/bin/python -m pytest skills/l9-update-agent-docs/tests -q PASSes and .venv/bin/python skills/l9-update-agent-docs/scripts/self_test.py PASSes | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** skills/l9-update-agent-docs/scripts (readme_evidence.py, source_facts.py, readme_renderers.py, readme_model.py, generate_module_readmes.py, doc_root.py, doc_llm.py, repo_docs.py, surface_analyzers/workflow.py), skills/l9-update-agent-docs/references/doc-surface-policy.yaml (llm.txt surface entries for compiled READMEs), skills/l9-update-agent-docs/tests (new test_signal_ledger.py plus targeted assertions), skills/l9-update-agent-docs/SKILL.md (signal-utilization law, version 4.4.0)

**Out:**
- New extractor languages or a new parser dependency
- LLM-authored prose of any kind
- Running --full against /Users/macm2/LLM-Router-META-INJECTOR-TEST (user runs it)
- ADR reconciliation and the agent/cursor/adr-number-realign branch
- Overwriting an unowned AGENTS.md, CLAUDE.md, INVARIANTS.md, llm.txt, or filetree.md
- Copying Quantum-L9/.github content (cite-only stays)
- CLAUDE.md growing beyond a pointer (policy pointer_only; no registry dump)

## Critical path (seed)

T1 → T2 → T6 → T9

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Every repository that runs l9-update-agent-docs --full gets rewritten AGENTS.md (marker-owned only), INVARIANTS.md, llm.txt, and READMEs; a wrong wire propagates to all of them on the next run
- Rollback: Revert the branch commits on feat/l9-repo-docs-full; target repos regenerate from the previous compiler with the same --full command

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: plan validated; implementation waits for Build
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Wire every extracted signal in l9-update-agent-docs into a compiled document

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
