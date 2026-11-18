---
name: Opportunity close
overview: "Supersede opportunity_pipeline_34b692e6.plan.md. Do not build that plan: it reads the live material profile, drafts a purchase order at offer acceptance, and compiles the transaction by confirming the sale order. The native crm.lead form stays. At creation the opportunity copies the supplier material, notes, and pictures and never writes them back. The broker records the supplier price and read..."
todos:
  - id: T1
    content: "On first link of material_profile_id, copy the profile's polymer, form, color, source, material type, packaging, filler, scalar specs, freeform notes, and attribute ids onto stored crm.lead fields, and copy its pictures onto the lead. The form shows that copy, the supplier price, and the ready date at the top, and opens the lead's pictures. Hide New Quotation. Never call the profile write, action_attach_images, or image propagation toward the profile. Later profile edits do not refresh the copy. Bump plasticos_crm_bridge from 19.0.3.4.24 to 19.0.3.4.25."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Deactivate the six PlasticOS stages and clear is_won on Active Supplier. Post-migrate 19.0.3.4.25 maps the extra New to crm.stage_lead1, HOT, WARM, Resistant, and Active Supplier to native Qualified, and Dead Lead to native Lost. New opportunities and HOT web leads start on crm.stage_lead1. VanillaSoft New maps to native New; HOT, WARM, and Resistant map to native Qualified. Nothing in that map sets Won. Update the tests that still assert the old stage xmlids."
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Offer acceptance still enforces one winner, then marks that opportunity won on crm.stage_lead4 and pending for admin. Remove the call that drafts the sale order. The admin dashboard gains one urgency button, hidden at zero, that opens the pending opportunities. Add plasticos_crm_bridge to the dashboard depends and bump plasticos_admin_dashboard from 19.0.1.1.2 to 19.0.1.1.3. Do not add a KPI section."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Add sale.order._plasticos_release_deal. It requires the buyer company, buyer facility, and buyer price. It creates one draft purchase order to the supplier company at the opportunity supplier price, with the ready date as the line planned date, and one draft sale order to the buyer facility at the admin buyer price. Both lines store the opportunity's material copy. It creates one draft plasticos.transaction linked to both and sets the sale order's transaction_id. A second submit returns those records. Do not confirm, activate, or call Linda. In action_confirm, an order that already has a transaction is not compiled again; if that transaction is still draft, activate it. Leave import_mode compilation unchanged. Bump plasticos_transaction from 19.0.2.3.61 to 19.0.2.3.62."
    status: pending
    phase: execute
    depends_on: [T1, T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Opportunity close

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `opportunity_close_88485964.plan.md`
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
| plan_id | `plan.simple.opportunity_close.v1` |
| name | Opportunity close |
| overview | Supersede opportunity_pipeline_34b692e6.plan.md. Do not build that plan: it reads the live material profile, drafts a purchase order at offer acceptance, and compiles the transaction by confirming the sale order. The native crm.lead form stays. At creation the opportunity copies the supplier material, notes, and pictures and never writes them back. The broker records the supplier price and ready date on that copy. Accepting the offer marks the opportunity won and pending. It creates no order. The admin dashboard shows those pending opportunities and nothing else new. Arthur selects the buyer company, buyer facility, and buyer price, and may edit only the opportunity copy. Submit creates one unconfirmed purchase order to the supplier at the broker's supplier price, one unconfirmed sale order to the buyer facility at Arthur's price, and one draft transaction because both orders then exist. Confirming that sale order later activates the existing transaction and does not create a second one. Logistics keeps its existing send, which runs only after a native confirm, and its existing ready check. No new mail cron is added. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-09T21:06:54+00:00 |
| updated_at | 2026-11-09T21:06:54+00:00 |
| depth | `deep` |
| estimate | one implementation pass on the open feature branch |

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
| captured_at | `2026-11-09T21:06:54+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `feat/erp-company-role-tags` |
| commit_sha | `d5856d868538e59b83e8dad2bfdb9c1a6170ed51` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Supersede opportunity_pipeline_34b692e6.plan.md. Do not build that plan: it reads the live material profile, drafts a purchase order at offer acceptance, and compiles the transaction by confirming the sale order. The native crm.lead form stays. At creation the opportunity copies the supplier material, notes, and pictures and never writes them back. The broker records the supplier price and ready date on that copy. Accepting the offer marks the opportunity won and pending. It creates no order. The admin dashboard shows those pending opportunities and nothing else new. Arthur selects the buyer company, buyer facility, and buyer price, and may edit only the opportunity copy. Submit creates one unconfirmed purchase order to the supplier at the broker's supplier price, one unconfirmed sale order to the buyer facility at Arthur's price, and one draft transaction because both orders then exist. Confirming that sale order later activates the existing transaction and does not create a second one. Logistics keeps its existing send, which runs only after a native confirm, and its existing ready check. No new mail cron is added.

### Scope in

- Native crm.lead opportunity form: opportunity-owned material copy, pictures, supplier price, ready date, and hidden New Quotation
- Native stage bar only, with a post-migrate off the VanillaSoft stages
- Offer acceptance queues the won opportunity for admin and does not draft orders
- One pending-deals control on the existing admin dashboard
- Submit releases one draft purchase order, one draft sale order, and one draft transaction

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves an edit of the opportunity's polymer, notes, attributes, or pictures leaves the linked material profile unchanged. | `quality_gate` | V1: `pytest plasticos_crm_bridge/tests/test_opportunity_material_copy.py` → The linked material profile is unchanged after the opportunity copy is edited. | `true` |
| SP-02 | V2 proves offer acceptance marks the opportunity won and pending and creates neither a purchase order nor a sale order. | `quality_gate` | V2: `pytest plasticos_crm_bridge/tests/test_opportunity_approval.py` → Acceptance creates no purchase order and no sale order and leaves the opportunity pending. | `true` |
| SP-03 | V3 proves submit creates one draft purchase order at the broker supplier price, one draft sale order at the admin buyer price, and exactly one transaction, and a later confirmation does not create a second transaction. | `quality_gate` | V3: `pytest plasticos_crm_bridge/tests/test_opportunity_release.py` → Submit creates one draft purchase order, one draft sale order, and one transaction. Confirmation does not create a second transaction. | `true` |
| SP-04 | V4 proves .pre-commit-config.yaml is the hook catalog for the changed Python and XML. | `quality_gate` | V4: `.pre-commit-config.yaml` → The changed Python and XML pass the catalogued hooks. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.opportunity_close.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.opportunity_close.v1` |
| source_ref | `plan.simple.opportunity_close.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.opportunity_close.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `Read plasticos_crm_bridge/models/match_lineage.py action_accept and plasticos_transaction/models/sale_inherit.py action_confirm` | Acceptance drafts a buyer sale order and does not mark the opportunity won. Confirmation compiles a transaction only when transaction_id is empty. Linda issues only a confirmed purchase or sale order. | `true` |
| P1 | pre-validation (status `passed`) | `Read plasticos_crm_bridge/models/opportunity_approval.py and plasticos_order_lines/models/purchase_order_line.py` | The approved lot is immutable. Purchase-line material fields are stored copies, not related writes into the profile. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_crm_bridge/`, `plasticos_admin_dashboard/`, `plasticos_transaction/models/sale_inherit.py`, `plasticos_transaction/__manifest__.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py`
- **write_deny:** `plasticos_material_profile/views/partner_material_ux.xml`, `plasticos_crm_bridge/models/opportunity_approval.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_transaction/models/sale_inherit.py import_mode compilation`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `pytest plasticos_crm_bridge/tests/test_opportunity_material_copy.py`, `pytest plasticos_crm_bridge/tests/test_opportunity_approval.py`, `pytest plasticos_crm_bridge/tests/test_opportunity_release.py`, `.pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | none |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- The native crm.lead form remains the opportunity.
- The approved lot stays immutable and is not the editable copy.
- Linda sends only after a native confirm of an existing purchase or sale order.
- Historical worksheet import still compiles through import_mode.
- opportunity_pipeline_34b692e6.plan.md is superseded and must not be executed.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_bridge/models/crm_lead.py plasticos_crm_bridge/views/crm_lead_views.xml plasticos_crm_bridge/__manifest__.py plasticos_crm_bridge/tests/test_opportunity_material_copy.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_bridge/data/crm_stage_data.xml plasticos_crm_bridge/models/crm_mapping.py plasticos_crm_bridge/models/web_lead.py plasticos_crm_bridge/migrations/19.0.3.4.25/post-migrate.py plasticos_crm_bridge/tests/test_web_lead_opportunity.py plasticos_crm_sync/tests/test_orchestrator_upsert.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_bridge/models/match_lineage.py plasticos_crm_bridge/tests/test_opportunity_approval.py plasticos_admin_dashboard/models/admin_dashboard.py plasticos_admin_dashboard/views/admin_dashboard_views.xml plasticos_admin_dashboard/__manifest__.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/models/sale_inherit.py plasticos_transaction/__manifest__.py plasticos_crm_bridge/models/crm_lead.py plasticos_crm_bridge/views/crm_lead_views.xml plasticos_crm_bridge/tests/test_opportunity_release.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `plasticos_crm_bridge` | `data_plane` | `The native crm.lead form remains the opportunity.`, `The approved lot stays immutable and is not the editable copy.`, `Linda sends only after a native confirm of an existing purchase or sale order.`, `Historical worksheet import still compiles through import_mode.`, `opportunity_pipeline_34b692e6.plan.md is superseded and must not be executed.` | `plasticos_material_profile/views/partner_material_ux.xml`, `plasticos_crm_bridge/models/opportunity_approval.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_transaction/models/sale_inherit.py import_mode compilation` |
| T2 | `repository root` | `data_plane` | `The native crm.lead form remains the opportunity.`, `The approved lot stays immutable and is not the editable copy.`, `Linda sends only after a native confirm of an existing purchase or sale order.`, `Historical worksheet import still compiles through import_mode.`, `opportunity_pipeline_34b692e6.plan.md is superseded and must not be executed.` | `plasticos_material_profile/views/partner_material_ux.xml`, `plasticos_crm_bridge/models/opportunity_approval.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_transaction/models/sale_inherit.py import_mode compilation` |
| T3 | `repository root` | `runtime` | `The native crm.lead form remains the opportunity.`, `The approved lot stays immutable and is not the editable copy.`, `Linda sends only after a native confirm of an existing purchase or sale order.`, `Historical worksheet import still compiles through import_mode.`, `opportunity_pipeline_34b692e6.plan.md is superseded and must not be executed.` | `plasticos_material_profile/views/partner_material_ux.xml`, `plasticos_crm_bridge/models/opportunity_approval.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_transaction/models/sale_inherit.py import_mode compilation` |
| T4 | `repository root` | `runtime` | `The native crm.lead form remains the opportunity.`, `The approved lot stays immutable and is not the editable copy.`, `Linda sends only after a native confirm of an existing purchase or sale order.`, `Historical worksheet import still compiles through import_mode.`, `opportunity_pipeline_34b692e6.plan.md is superseded and must not be executed.` | `plasticos_material_profile/views/partner_material_ux.xml`, `plasticos_crm_bridge/models/opportunity_approval.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_transaction/models/sale_inherit.py import_mode compilation` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.opportunity_close.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.opportunity_close.v1` |
| source_execution_ref | `plan.simple.opportunity_close.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 passes: a profile write count stays zero after an opportunity material edit.) → Stop before acceptance or release changes.; C2 fails (V2 and V3 pass: no order at acceptance, one transaction at submit, no second transaction at confirm.) → Do not publish. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the three module bumps and their migrations. Deactivate no stage that the post-migrate already cleared without restoring the previous stage xmlids in the same revert. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `pytest plasticos_crm_bridge/tests/test_opportunity_material_copy.py`
- re-run `pytest plasticos_crm_bridge/tests/test_opportunity_approval.py`
- re-run `pytest plasticos_crm_bridge/tests/test_opportunity_release.py`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 4 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `high` — Acceptance, sale confirmation, and the admin dashboard change for every opportunity that uses the Gate offer winner. Historical worksheet import is outside that path. |
| architectural_boundaries_crossed | `crm.lead commercial copy`, `sale.order confirmation`, `admin dashboard` |
| external_systems_touched | none |
| migration_required | `true` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.opportunity_close.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.opportunity_close.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | On first link of material_profile_id, copy the profile's polymer, form, color, source, material type, packaging, filler, scalar specs, freeform notes, and attribute ids onto stored crm.lead fields, and copy its pictures onto the lead. The form shows that copy, the supplier price, and the ready date at the top, and opens the lead's pictures. Hide New Quotation. Never call the profile write, action_attach_images, or image propagation toward the profile. Later profile edits do not refresh the copy. Bump plasticos_crm_bridge from 19.0.3.4.24 to 19.0.3.4.25. | Cursor Build agent | `high` | M | `[]` | `plasticos_crm_bridge/models/crm_lead.py`, `plasticos_crm_bridge/views/crm_lead_views.xml`, `plasticos_crm_bridge/__manifest__.py`, `plasticos_crm_bridge/tests/test_opportunity_material_copy.py` |
| T2 | Deactivate the six PlasticOS stages and clear is_won on Active Supplier. Post-migrate 19.0.3.4.25 maps the extra New to crm.stage_lead1, HOT, WARM, Resistant, and Active Supplier to native Qualified, and Dead Lead to native Lost. New opportunities and HOT web leads start on crm.stage_lead1. VanillaSoft New maps to native New; HOT, WARM, and Resistant map to native Qualified. Nothing in that map sets Won. Update the tests that still assert the old stage xmlids. | Cursor Build agent | `medium` | M | `[]` | `plasticos_crm_bridge/data/crm_stage_data.xml`, `plasticos_crm_bridge/models/crm_mapping.py`, `plasticos_crm_bridge/models/web_lead.py`, `plasticos_crm_bridge/migrations/19.0.3.4.25/post-migrate.py`, `plasticos_crm_bridge/tests/test_web_lead_opportunity.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py` |
| T3 | Offer acceptance still enforces one winner, then marks that opportunity won on crm.stage_lead4 and pending for admin. Remove the call that drafts the sale order. The admin dashboard gains one urgency button, hidden at zero, that opens the pending opportunities. Add plasticos_crm_bridge to the dashboard depends and bump plasticos_admin_dashboard from 19.0.1.1.2 to 19.0.1.1.3. Do not add a KPI section. | Cursor Build agent | `high` | M | `[T1]` | `plasticos_crm_bridge/models/match_lineage.py`, `plasticos_crm_bridge/tests/test_opportunity_approval.py`, `plasticos_admin_dashboard/models/admin_dashboard.py`, `plasticos_admin_dashboard/views/admin_dashboard_views.xml`, `plasticos_admin_dashboard/__manifest__.py` |
| T4 | Add sale.order._plasticos_release_deal. It requires the buyer company, buyer facility, and buyer price. It creates one draft purchase order to the supplier company at the opportunity supplier price, with the ready date as the line planned date, and one draft sale order to the buyer facility at the admin buyer price. Both lines store the opportunity's material copy. It creates one draft plasticos.transaction linked to both and sets the sale order's transaction_id. A second submit returns those records. Do not confirm, activate, or call Linda. In action_confirm, an order that already has a transaction is not compiled again; if that transaction is still draft, activate it. Leave import_mode compilation unchanged. Bump plasticos_transaction from 19.0.2.3.61 to 19.0.2.3.62. | Cursor Build agent | `high` | L | `[T1, T3]` | `plasticos_transaction/models/sale_inherit.py`, `plasticos_transaction/__manifest__.py`, `plasticos_crm_bridge/models/crm_lead.py`, `plasticos_crm_bridge/views/crm_lead_views.xml`, `plasticos_crm_bridge/tests/test_opportunity_release.py` |

**Critical path:** T1 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The opportunity owns an editable material copy and the native stage bar is the only bar. | Admin can open a won opportunity without touching the supplier profile. |
| M2 | Acceptance only queues the opportunity, and submit creates both drafts and one transaction. | Logistics uses the purchase and sale orders it already knows how to send after confirm. |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 passes: a profile write count stays zero after an opportunity material edit. | Stop before acceptance or release changes. |
| C2 | M2 | V2 and V3 pass: no order at acceptance, one transaction at submit, no second transaction at confirm. | Do not publish. |

### Leverage

- **Ranked todos:** `T1`, `T4`, `T3`, `T2`
- **Shared causes:** the opportunity has no commercial copy of its own; acceptance currently drafts the buyer sale order
- **Deletions / consolidations:** Do not draft a purchase order at offer acceptance.; Do not add a buyer-purchase-order follow-up cron.; Do not add a second opportunity model or a second stage widget.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The 2026-11-05 correction already names the opportunity, the optional facility, and the draft sale order. This plan changes that hand-off and does not edit the append-only root file. |
| INVARIANTS.md | `n_a` | — | No invariant id changes. The approved lot stays immutable and is not the editable copy. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `pytest plasticos_crm_bridge/tests/test_opportunity_material_copy.py` | The linked material profile is unchanged after the opportunity copy is edited. | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `pytest plasticos_crm_bridge/tests/test_opportunity_approval.py` | Acceptance creates no purchase order and no sale order and leaves the opportunity pending. | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `pytest plasticos_crm_bridge/tests/test_opportunity_release.py` | Submit creates one draft purchase order, one draft sale order, and one transaction. Confirmation does not create a second transaction. | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | The changed Python and XML pass the catalogued hooks. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can an admin edit of attributes or pictures write the live material profile?
- Can offer acceptance still draft a sale order or a purchase order?
- Can confirming the released sale order create a second transaction?
- Does submit confirm an order or queue a Linda send?

### Assumption failure conditions

- The opportunity form uses related fields that write through to the material profile.
- The frozen approval lot is reused as the admin's editable copy.
- A missing buyer purchase order needs a new follow-up cron in this change.

### Blast radius notes

- Acceptance, sale confirmation, and the admin dashboard change for every opportunity that uses the Gate offer winner. Historical worksheet import is outside that path.

### Rollback constraints

- Revert the three module bumps and their migrations. Deactivate no stage that the post-migrate already cleared without restoring the previous stage xmlids in the same revert.

### Risks

| risk | mitigation |
|------|------------|
| A related field or image helper writes the opportunity edit back onto the material profile. | Store the copy on crm.lead and assert the profile write count stays zero. |
| Changing action_confirm compiles or drops transactions for sales that are not this release. | Create the transaction only in _plasticos_release_deal. Confirmation activates an existing draft and otherwise keeps today's compile, including import_mode. |
| The dashboard depend on plasticos_crm_bridge forms a cycle. | crm_bridge does not depend on plasticos_admin_dashboard. Stop if a wiring check reports a cycle. |

## Out of scope

- opportunity_pipeline_34b692e6.plan.md and its close
- Writing any opportunity edit back to plasticos.material.profile
- A new opportunity model, a second stage bar, or a rebuilt partner or notes block
- Calling Linda or confirming either order inside submit
- A buyer-purchase-order follow-up cron
- Rewriting historical import compilation
- plasticos_material_profile/views/partner_material_ux.xml
- pipeline_v2.py
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.opportunity_close.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.opportunity_close.v1` |
| source_ref | `plan.simple.opportunity_close.v1` |
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
| `open_blocker` | stop_reason | The close is specified. V1 through V4 run when the todos are built, so this plan is not converged. | planning convergence `partial` |

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
  plan_id: "plan.simple.opportunity_close.v1"
  name: "Opportunity close"
  overview: "Supersede opportunity_pipeline_34b692e6.plan.md. Do not build that plan: it reads the live material profile, drafts a purchase order at offer acceptance, and compiles the transaction by confirming the sale order. The native crm.lead form stays. At creation the opportunity copies the supplier material, notes, and pictures and never writes them back. The broker records the supplier price and ready date on that copy. Accepting the offer marks the opportunity won and pending. It creates no order. The admin dashboard shows those pending opportunities and nothing else new. Arthur selects the buyer company, buyer facility, and buyer price, and may edit only the opportunity copy. Submit creates one unconfirmed purchase order to the supplier at the broker's supplier price, one unconfirmed sale order to the buyer facility at Arthur's price, and one draft transaction because both orders then exist. Confirming that sale order later activates the existing transaction and does not create a second one. Logistics keeps its existing send, which runs only after a native confirm, and its existing ready check. No new mail cron is added."
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
  commit_sha: "d5856d868538e59b83e8dad2bfdb9c1a6170ed51"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Supersede opportunity_pipeline_34b692e6.plan.md. Do not build that plan: it reads the live material profile, drafts a purchase order at offer acceptance, and compiles the transaction by confirming the sale order. The native crm.lead form stays. At creation the opportunity copies the supplier material, notes, and pictures and never writes them back. The broker records the supplier price and ready date on that copy. Accepting the offer marks the opportunity won and pending. It creates no order. The admin dashboard shows those pending opportunities and nothing else new. Arthur selects the buyer company, buyer facility, and buyer price, and may edit only the opportunity copy. Submit creates one unconfirmed purchase order to the supplier at the broker's supplier price, one unconfirmed sale order to the buyer facility at Arthur's price, and one draft transaction because both orders then exist. Confirming that sale order later activates the existing transaction and does not create a second one. Logistics keeps its existing send, which runs only after a native confirm, and its existing ready check. No new mail cron is added."
  success_properties:
    - id: "SP-01"
      property: "V1 proves an edit of the opportunity's polymer, notes, attributes, or pictures leaves the linked material profile unchanged."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves offer acceptance marks the opportunity won and pending and creates neither a purchase order nor a sale order."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves submit creates one draft purchase order at the broker supplier price, one draft sale order at the admin buyer price, and exactly one transaction, and a later confirmation does not create a second transaction."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves .pre-commit-config.yaml is the hook catalog for the changed Python and XML."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.opportunity_close.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_crm_bridge/", "plasticos_admin_dashboard/", "plasticos_transaction/models/sale_inherit.py", "plasticos_transaction/__manifest__.py", "plasticos_crm_sync/tests/test_orchestrator_upsert.py"]
    write_deny: ["plasticos_material_profile/views/partner_material_ux.xml", "plasticos_crm_bridge/models/opportunity_approval.py", "plasticos_logistics/models/linda_request.py", "plasticos_transaction/models/sale_inherit.py import_mode compilation"]
  commands:
    allow: ["pytest plasticos_crm_bridge/tests/test_opportunity_material_copy.py", "pytest plasticos_crm_bridge/tests/test_opportunity_approval.py", "pytest plasticos_crm_bridge/tests/test_opportunity_release.py", ".pre-commit-config.yaml"]
  network:
    mode: "none"
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
rollback_contract_ref: "rollback.plan.simple.opportunity_close.v1"
dependency_topology_ref: "dag.plan.simple.opportunity_close.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Can an admin edit of attributes or pictures write the live material profile?", "Can offer acceptance still draft a sale order or a purchase order?", "Can confirming the released sale order create a second transaction?", "Does submit confirm an order or queue a Linda send?"]
  assumption_failure_conditions: ["The opportunity form uses related fields that write through to the material profile.", "The frozen approval lot is reused as the admin's editable copy.", "A missing buyer purchase order needs a new follow-up cron in this change."]
out_of_scope: ["opportunity_pipeline_34b692e6.plan.md and its close", "Writing any opportunity edit back to plasticos.material.profile", "A new opportunity model, a second stage bar, or a rebuilt partner or notes block", "Calling Linda or confirming either order inside submit", "A buyer-purchase-order follow-up cron", "Rewriting historical import compilation", "plasticos_material_profile/views/partner_material_ux.xml", "pipeline_v2.py"]
convergence_contract_ref: "conv.plan.simple.opportunity_close.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "On first link of material_profile_id, copy the profile's polymer, form, color, source, material type, packaging, filler, scalar specs, freeform notes, and attribute ids onto stored crm.lead fields, and copy its pictures onto the lead. The form shows that copy, the supplier price, and the ready date at the top, and opens the lead's pictures. Hide New Quotation. Never call the profile write, action_attach_images, or image propagation toward the profile. Later profile edits do not refresh the copy. Bump plasticos_crm_bridge from 19.0.3.4.24 to 19.0.3.4.25."
    status: "pending"
  - id: "T2"
    content: "Deactivate the six PlasticOS stages and clear is_won on Active Supplier. Post-migrate 19.0.3.4.25 maps the extra New to crm.stage_lead1, HOT, WARM, Resistant, and Active Supplier to native Qualified, and Dead Lead to native Lost. New opportunities and HOT web leads start on crm.stage_lead1. VanillaSoft New maps to native New; HOT, WARM, and Resistant map to native Qualified. Nothing in that map sets Won. Update the tests that still assert the old stage xmlids."
    status: "pending"
  - id: "T3"
    content: "Offer acceptance still enforces one winner, then marks that opportunity won on crm.stage_lead4 and pending for admin. Remove the call that drafts the sale order. The admin dashboard gains one urgency button, hidden at zero, that opens the pending opportunities. Add plasticos_crm_bridge to the dashboard depends and bump plasticos_admin_dashboard from 19.0.1.1.2 to 19.0.1.1.3. Do not add a KPI section."
    status: "pending"
  - id: "T4"
    content: "Add sale.order._plasticos_release_deal. It requires the buyer company, buyer facility, and buyer price. It creates one draft purchase order to the supplier company at the opportunity supplier price, with the ready date as the line planned date, and one draft sale order to the buyer facility at the admin buyer price. Both lines store the opportunity's material copy. It creates one draft plasticos.transaction linked to both and sets the sale order's transaction_id. A second submit returns those records. Do not confirm, activate, or call Linda. In action_confirm, an order that already has a transaction is not compiled again; if that transaction is still draft, activate it. Leave import_mode compilation unchanged. Bump plasticos_transaction from 19.0.2.3.61 to 19.0.2.3.62."
    status: "pending"
```
