---
name: Screen views
overview: "Add one installable module, plasticos_screen_views, that turns on the Odoo view engines already in this checkout. Contacts gain a map pinned on the contact itself and a hierarchy of companies and their contacts. Web Leads open on the list, and gain calendar on submitted_at, pivot and graph on decision, state, source, and weight, the engine's own map through partner_id, and activities. The activ..."
todos:
  - id: T1
    content: "Create plasticos_screen_views with manifest 19.0.1.0.0, auto_install, and depends contacts, mail, web_hierarchy, web_map, plasticos_web_leads. Wire models and both view files. Add no security file and no new model name."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Add the contact map with res_partner id and the contact hierarchy with child_field child_ids and a hierarchy-box card showing the name. Extend contacts.action_contacts view_mode to list,kanban,form,activity,map,hierarchy and pin the two new views with ir.actions.act_window.view. Leave the existing list sequence 0 binding in place."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Set the web lead action to open on list, including mobile_view_mode list. Add a calendar on submitted_at, a pivot and a bar graph grouped by decision, state, and lead_source_id with estimated_lbs_per_load as the measure. Add map and activity to view_mode with no extra arch. Keep search_default_hot."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Inherit plasticos.web.lead together with mail.activity.mixin. Override write so a vals dict whose keys are only mixin fields reaches the base write on an intake-created lead. Any other key still goes through the existing guard."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T5
    content: "Add a post_install TransactionCase that reads the two actions' view modes and view arches, schedules an activity on an intake-created lead, and asserts a company_name write on that lead still raises."
    status: pending
    phase: execute
    depends_on: [T2, T3, T4]
  - id: T6
    content: "Name plasticos_screen_views in an additive AGENTS.md correction. Do not rewrite the protected project-structure block."
    status: pending
    phase: execute
    depends_on: [T1]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Screen views

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `screen_views_2793f4e1.plan.md`
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
| plan_id | `plan.simple.screen_views.v1` |
| name | Screen views |
| overview | Add one installable module, plasticos_screen_views, that turns on the Odoo view engines already in this checkout. Contacts gain a map pinned on the contact itself and a hierarchy of companies and their contacts. Web Leads open on the list, and gain calendar on submitted_at, pivot and graph on decision, state, source, and weight, the engine's own map through partner_id, and activities. The activity mixin lives in the new module. A follow-up can be scheduled after intake creation, and every other field on an intake-created lead stays blocked. CRM leads are left on the views CRM Enterprise already adds. Grid, Gantt, Cohort, and Hierarchy stay off Web Leads. Studio is not used. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-10T16:58:24+00:00 |
| updated_at | 2026-11-10T16:58:24+00:00 |
| depth | `standard` |
| estimate | M |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-10T16:58:24+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `feat/web-lead-date-photos` |
| commit_sha | `95ea2a42223d055b19081b01ff731daccdf59320` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Add one installable module, plasticos_screen_views, that turns on the Odoo view engines already in this checkout. Contacts gain a map pinned on the contact itself and a hierarchy of companies and their contacts. Web Leads open on the list, and gain calendar on submitted_at, pivot and graph on decision, state, source, and weight, the engine's own map through partner_id, and activities. The activity mixin lives in the new module. A follow-up can be scheduled after intake creation, and every other field on an intake-created lead stays blocked. CRM leads are left on the views CRM Enterprise already adds. Grid, Gantt, Cohort, and Hierarchy stay off Web Leads. Studio is not used.

### Scope in

- New module plasticos_screen_views version 19.0.1.0.0, auto_install when its dependencies are present
- Contacts map arch with res_partner id, and hierarchy arch with child_field child_ids and a hierarchy-box card
- Web lead action view_mode list,kanban,form,calendar,pivot,graph,map,activity and mobile_view_mode list
- Web lead calendar, pivot, and graph arches. Map and activity use the engine default and get no second arch
- mail.activity.mixin on plasticos.web.lead, with a write passthrough limited to the mixin's own fields
- One Odoo test module and an additive AGENTS.md correction naming the new addon

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves contacts.action_contacts offers map and hierarchy, the map uses res_partner id, and the hierarchy uses child_ids. | `quality_gate` | V1: `plasticos_screen_views/tests/test_screen_views.py` → The contacts action offers map and hierarchy, the map arch sets res_partner to id, and the hierarchy arch sets child_field to child_ids. | `true` |
| SP-02 | V2 proves plasticos_web_leads.action_web_lead opens on list and also offers calendar, pivot, graph, map, and activity, with calendar on submitted_at and pivot and graph on decision, state, lead source, and weight. | `quality_gate` | V2: `plasticos_screen_views/tests/test_screen_views.py` → The web lead action view_mode starts with list and includes calendar, pivot, graph, map, and activity. The calendar date is submitted_at. The pivot and graph name decision, state, lead_source_id, and estimated_lbs_per_load. | `true` |
| SP-03 | V3 proves an intake-created web lead accepts an activity and still rejects a write of company_name. | `quality_gate` | V3: `plasticos_screen_views/tests/test_screen_views.py` → Scheduling an activity on an intake-created lead succeeds, and writing company_name on that lead raises. | `true` |
| SP-04 | V4 proves .pre-commit-config.yaml is the hook catalog for the new module's Python and XML. | `quality_gate` | V4: `.pre-commit-config.yaml` → The new module's Python and XML pass the catalogued hooks, including module wiring and the Odoo 19 XML checks. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.screen_views.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.screen_views.v1` |
| source_ref | `plan.simple.screen_views.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.screen_views.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git status and git rev-parse on the workspace; gh pr view 446` | Clean tree on feat/web-lead-date-photos at 95ea2a42. PR 446 is merged into Staging. Open PRs 442 and 445 are unrelated sibling chains. | `true` |
| P1 | pre-validation (status `passed`) | `Read plasticos_web_leads.action_web_lead, contacts.action_contacts, and the web lead write guard` | Web leads are kanban,list,form with no act_window.view rows, so view_mode order is the open order. Contacts already bind list at sequence 0 and name activity in view_mode. intake_created rejects every field outside the allowlist. | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence sufficient --json` | depth standard and omit_gates empty | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_screen_views/`, `AGENTS.md`
- **write_deny:** `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 scripts/check_module_wiring.py`, `python3 ci/check_odoo19_xml.py`, `.venv/bin/ruff check plasticos_screen_views`, `plasticos_screen_views/tests/test_screen_views.py`, `.pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `github` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- intake_created still rejects writes other than the activity mixin fields
- Web leads do not gain Grid, Gantt, Cohort, or Hierarchy
- search_default_hot stays on the web lead action
- No automatic partner is created

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_screen_views/__manifest__.py plasticos_screen_views/__init__.py plasticos_screen_views/models/__init__.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_screen_views/views/contact_views.xml` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_screen_views/views/web_lead_views.xml` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_screen_views/models/web_lead.py plasticos_screen_views/models/__init__.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_screen_views/tests/__init__.py plasticos_screen_views/tests/test_screen_views.py` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- AGENTS.md` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `plasticos_screen_views` | `runtime` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |
| T2 | `plasticos_screen_views/views` | `runtime` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |
| T3 | `plasticos_screen_views/views` | `runtime` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |
| T4 | `plasticos_screen_views/models` | `runtime` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |
| T5 | `plasticos_screen_views/tests` | `assurance` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |
| T6 | `repository root` | `docs` | `intake_created still rejects writes other than the activity mixin fields`, `Web leads do not gain Grid, Gantt, Cohort, or Hierarchy`, `search_default_hot stays on the web lead action`, `No automatic partner is created` | `plasticos_web_leads/`, `plasticos_crm_bridge/`, `odoo-enterprise/`, `pipeline_v2.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.screen_views.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.screen_views.v1` |
| source_execution_ref | `plan.simple.screen_views.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (python3 scripts/check_module_wiring.py exits 0 and the manifest version is 19.0.1.0.0.) → Stop. Do not add views to plasticos_web_leads or contacts to compensate.; C2 fails (ci/check_odoo19_xml.py accepts both view files. Web lead view_mode starts with list and contains no space and no duplicate mode.) → Stop. Do not invent a Grid, Gantt, Cohort, or Hierarchy arch for web leads.; C3 fails (The new TransactionCase covers the activity passthrough and the rejected company_name write.) → Stop. Do not widen the intake_created allowlist inside plasticos_web_leads. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Uninstall plasticos_screen_views. The action view modes and the new arches leave with it. The mixin columns are dropped with the uninstall. No data migration is rewritten. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 scripts/check_module_wiring.py`
- re-run `python3 ci/check_odoo19_xml.py`
- re-run `.venv/bin/ruff check plasticos_screen_views`
- re-run `plasticos_screen_views/tests/test_screen_views.py`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 6 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — One new addon. Contacts and Web Leads gain view icons. plasticos_web_leads Python and XML stay untouched. An install adds the standard activity columns onto plasticos_web_lead through the mixin. |
| architectural_boundaries_crossed | `plasticos_screen_views depends on enterprise web_map and community web_hierarchy`, `mail.activity.mixin is added to plasticos.web.lead from the new module` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.screen_views.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.screen_views.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Create plasticos_screen_views with manifest 19.0.1.0.0, auto_install, and depends contacts, mail, web_hierarchy, web_map, plasticos_web_leads. Wire models and both view files. Add no security file and no new model name. | Cursor Build agent | `medium` | S | `[]` | `plasticos_screen_views/__manifest__.py`, `plasticos_screen_views/__init__.py`, `plasticos_screen_views/models/__init__.py` |
| T2 | Add the contact map with res_partner id and the contact hierarchy with child_field child_ids and a hierarchy-box card showing the name. Extend contacts.action_contacts view_mode to list,kanban,form,activity,map,hierarchy and pin the two new views with ir.actions.act_window.view. Leave the existing list sequence 0 binding in place. | Cursor Build agent | `low` | S | `[T1]` | `plasticos_screen_views/views/contact_views.xml` |
| T3 | Set the web lead action to open on list, including mobile_view_mode list. Add a calendar on submitted_at, a pivot and a bar graph grouped by decision, state, and lead_source_id with estimated_lbs_per_load as the measure. Add map and activity to view_mode with no extra arch. Keep search_default_hot. | Cursor Build agent | `low` | S | `[T1]` | `plasticos_screen_views/views/web_lead_views.xml` |
| T4 | Inherit plasticos.web.lead together with mail.activity.mixin. Override write so a vals dict whose keys are only mixin fields reaches the base write on an intake-created lead. Any other key still goes through the existing guard. | Cursor Build agent | `medium` | S | `[T1]` | `plasticos_screen_views/models/web_lead.py`, `plasticos_screen_views/models/__init__.py` |
| T5 | Add a post_install TransactionCase that reads the two actions' view modes and view arches, schedules an activity on an intake-created lead, and asserts a company_name write on that lead still raises. | Cursor Build agent | `low` | S | `[T2, T3, T4]` | `plasticos_screen_views/tests/__init__.py`, `plasticos_screen_views/tests/test_screen_views.py` |
| T6 | Name plasticos_screen_views in an additive AGENTS.md correction. Do not rewrite the protected project-structure block. | Cursor Build agent | `low` | S | `[T1]` | `AGENTS.md` |

**Critical path:** T1 → T3 → T4 → T5

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The module manifest names the engines and the two apps and wires its Python and XML. | view records and the activity inherit |
| M2 | Both window actions expose the new view types and the arches name the agreed fields. | the runtime assertions |
| M3 | Activity scheduling works after intake creation and the rest of the write guard still holds. | publication |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | python3 scripts/check_module_wiring.py exits 0 and the manifest version is 19.0.1.0.0. | Stop. Do not add views to plasticos_web_leads or contacts to compensate. |
| C2 | M2 | ci/check_odoo19_xml.py accepts both view files. Web lead view_mode starts with list and contains no space and no duplicate mode. | Stop. Do not invent a Grid, Gantt, Cohort, or Hierarchy arch for web leads. |
| C3 | M3 | The new TransactionCase covers the activity passthrough and the rejected company_name write. | Stop. Do not widen the intake_created allowlist inside plasticos_web_leads. |

### Leverage

- **Ranked todos:** `T1`, `T3`, `T2`, `T4`, `T5`, `T6`
- **Shared causes:** The view engines are installed and the two actions never name them. One module that only points actions at existing engines covers both screens.
- **Deletions / consolidations:** Do not copy map, calendar, pivot, or graph XML into plasticos_web_leads and a contacts module. Both actions are extended from plasticos_screen_views.; Do not add a CRM view file. Those icons already exist.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `update` | `T6` | The addon set gains plasticos_screen_views. The correction is additive. |
| INVARIANTS.md | `n_a` | — | No invariant changes. The intake write guard remains the authority for non-activity fields. |
| CLAUDE.md | `n_a` | — | CLAUDE.md points at AGENTS.md for the addon snapshot. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `plasticos_screen_views/tests/test_screen_views.py` | The contacts action offers map and hierarchy, the map arch sets res_partner to id, and the hierarchy arch sets child_field to child_ids. | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `plasticos_screen_views/tests/test_screen_views.py` | The web lead action view_mode starts with list and includes calendar, pivot, graph, map, and activity. The calendar date is submitted_at. The pivot and graph name decision, state, lead_source_id, and estimated_lbs_per_load. | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `plasticos_screen_views/tests/test_screen_views.py` | Scheduling an activity on an intake-created lead succeeds, and writing company_name on that lead raises. | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | The new module's Python and XML pass the catalogued hooks, including module wiring and the Odoo 19 XML checks. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does contacts.action_contacts ignore a view_mode edit because its existing act_window.view rows already occupy list, kanban, and form? Missing modes are appended only when the view_mode string names them and an ir.ui.view of that type exists.
- Does the web lead map generator fail because the model has no partner_id? It has partner_id, so the default map is legal, and a lead with an empty partner draws no pin.
- Does scheduling an activity on an intake-created lead still hit the guard if the passthrough misses a mixin field the compute writes back?
- Does auto_install pull the module onto a community database that has no web_map? The enterprise test fixture and Odoo.sh both have the enterprise addons path. A community database without web_map cannot install this module, and that is the intended boundary.

### Assumption failure conditions

- The HOT filter is removed. It stays, so a database whose leads are all cold still opens an empty list until that data is reclassified.
- CRM needs a new map or cohort. crm_enterprise already attaches both to the pipeline.
- Column width, last view, and last filter are part of this module. They are not Enterprise view engines and they are out of scope.

### Blast radius notes

- One new addon. Contacts and Web Leads gain view icons. plasticos_web_leads Python and XML stay untouched. An install adds the standard activity columns onto plasticos_web_lead through the mixin.

### Rollback constraints

- Uninstall plasticos_screen_views. The action view modes and the new arches leave with it. The mixin columns are dropped with the uninstall. No data migration is rewritten.

### Risks

| risk | mitigation |
|------|------------|
| The web lead menu still applies search_default_hot, so the new list opens empty while every stored lead is cold. | Leave the filter. The merged classifier in PR 446 fills the list after that module is upgraded. This plan does not reclassify leads. |
| A prefix match on activity would let a later field sneak past the intake guard. | The passthrough compares against the exact field names declared on mail.activity.mixin. |
| Open PRs 442 and 445 are unrelated. Stacking this work onto either one mixes docs or tooling with the view module. | Branch from origin/Staging. Do not stack on 442 or 445. PR 446 is already merged. |

## Out of scope

- CRM lead, pipeline, and opportunity views. crm_enterprise already supplies activity, calendar, pivot, graph, map, and cohort
- Grid, Gantt, Cohort, and Hierarchy on plasticos.web.lead
- Gantt or Grid on res.partner
- Removing search_default_hot from the web lead action
- Editing plasticos_web_leads classifier, photos, submitted_at, or its view XML
- Studio customizations, a dashboard action, and remembering the last view, filter, or column width
- A new partner, a second photo model, and any change to the intake write allowlist beyond the activity fields
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.screen_views.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.screen_views.v1` |
| source_ref | `plan.simple.screen_views.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Should publication stack onto an open pull request? — 442 and 445 do not contain this work and are not a single chain. | `accept_bounded` |
| `open_blocker` | stop_reason | The view binding is specified. V1 through V4 run when the module is built, so this plan is not converged. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.screen_views.v1"
  name: "Screen views"
  overview: "Add one installable module, plasticos_screen_views, that turns on the Odoo view engines already in this checkout. Contacts gain a map pinned on the contact itself and a hierarchy of companies and their contacts. Web Leads open on the list, and gain calendar on submitted_at, pivot and graph on decision, state, source, and weight, the engine's own map through partner_id, and activities. The activity mixin lives in the new module. A follow-up can be scheduled after intake creation, and every other field on an intake-created lead stays blocked. CRM leads are left on the views CRM Enterprise already adds. Grid, Gantt, Cohort, and Hierarchy stay off Web Leads. Studio is not used."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "95ea2a42223d055b19081b01ff731daccdf59320"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Add one installable module, plasticos_screen_views, that turns on the Odoo view engines already in this checkout. Contacts gain a map pinned on the contact itself and a hierarchy of companies and their contacts. Web Leads open on the list, and gain calendar on submitted_at, pivot and graph on decision, state, source, and weight, the engine's own map through partner_id, and activities. The activity mixin lives in the new module. A follow-up can be scheduled after intake creation, and every other field on an intake-created lead stays blocked. CRM leads are left on the views CRM Enterprise already adds. Grid, Gantt, Cohort, and Hierarchy stay off Web Leads. Studio is not used."
  success_properties:
    - id: "SP-01"
      property: "V1 proves contacts.action_contacts offers map and hierarchy, the map uses res_partner id, and the hierarchy uses child_ids."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves plasticos_web_leads.action_web_lead opens on list and also offers calendar, pivot, graph, map, and activity, with calendar on submitted_at and pivot and graph on decision, state, lead source, and weight."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves an intake-created web lead accepts an activity and still rejects a write of company_name."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves .pre-commit-config.yaml is the hook catalog for the new module's Python and XML."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.screen_views.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_screen_views/", "AGENTS.md"]
    write_deny: ["plasticos_web_leads/", "plasticos_crm_bridge/", "odoo-enterprise/", "pipeline_v2.py"]
  commands:
    allow: ["python3 scripts/check_module_wiring.py", "python3 ci/check_odoo19_xml.py", ".venv/bin/ruff check plasticos_screen_views", "plasticos_screen_views/tests/test_screen_views.py", ".pre-commit-config.yaml"]
  network:
    mode: "named_services_only"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T5"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.screen_views.v1"
dependency_topology_ref: "dag.plan.simple.screen_views.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Does contacts.action_contacts ignore a view_mode edit because its existing act_window.view rows already occupy list, kanban, and form? Missing modes are appended only when the view_mode string names them and an ir.ui.view of that type exists.", "Does the web lead map generator fail because the model has no partner_id? It has partner_id, so the default map is legal, and a lead with an empty partner draws no pin.", "Does scheduling an activity on an intake-created lead still hit the guard if the passthrough misses a mixin field the compute writes back?", "Does auto_install pull the module onto a community database that has no web_map? The enterprise test fixture and Odoo.sh both have the enterprise addons path. A community database without web_map cannot install this module, and that is the intended boundary."]
  assumption_failure_conditions: ["The HOT filter is removed. It stays, so a database whose leads are all cold still opens an empty list until that data is reclassified.", "CRM needs a new map or cohort. crm_enterprise already attaches both to the pipeline.", "Column width, last view, and last filter are part of this module. They are not Enterprise view engines and they are out of scope."]
out_of_scope: ["CRM lead, pipeline, and opportunity views. crm_enterprise already supplies activity, calendar, pivot, graph, map, and cohort", "Grid, Gantt, Cohort, and Hierarchy on plasticos.web.lead", "Gantt or Grid on res.partner", "Removing search_default_hot from the web lead action", "Editing plasticos_web_leads classifier, photos, submitted_at, or its view XML", "Studio customizations, a dashboard action, and remembering the last view, filter, or column width", "A new partner, a second photo model, and any change to the intake write allowlist beyond the activity fields"]
convergence_contract_ref: "conv.plan.simple.screen_views.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Create plasticos_screen_views with manifest 19.0.1.0.0, auto_install, and depends contacts, mail, web_hierarchy, web_map, plasticos_web_leads. Wire models and both view files. Add no security file and no new model name."
    status: "pending"
  - id: "T2"
    content: "Add the contact map with res_partner id and the contact hierarchy with child_field child_ids and a hierarchy-box card showing the name. Extend contacts.action_contacts view_mode to list,kanban,form,activity,map,hierarchy and pin the two new views with ir.actions.act_window.view. Leave the existing list sequence 0 binding in place."
    status: "pending"
  - id: "T3"
    content: "Set the web lead action to open on list, including mobile_view_mode list. Add a calendar on submitted_at, a pivot and a bar graph grouped by decision, state, and lead_source_id with estimated_lbs_per_load as the measure. Add map and activity to view_mode with no extra arch. Keep search_default_hot."
    status: "pending"
  - id: "T4"
    content: "Inherit plasticos.web.lead together with mail.activity.mixin. Override write so a vals dict whose keys are only mixin fields reaches the base write on an intake-created lead. Any other key still goes through the existing guard."
    status: "pending"
  - id: "T5"
    content: "Add a post_install TransactionCase that reads the two actions' view modes and view arches, schedules an activity on an intake-created lead, and asserts a company_name write on that lead still raises."
    status: "pending"
  - id: "T6"
    content: "Name plasticos_screen_views in an additive AGENTS.md correction. Do not rewrite the protected project-structure block."
    status: "pending"
```
