---
name: Repair the remaining OdooLS diagnostics
overview: Clear the 4 errors, 14 warnings, and 4 information notes from the 2026-11-06
  make odools-diagnostics run. Each repair stays in the module that owns the symbol.
  plasticos_logistics does not gain a dependency on plasticos_documents, and plasticos_material_profile
  does not gain a dependency on plasticos_order_lines. Branch from Staging at 09c65ed5.
  Publication is make pr into Staging.
todos:
- id: T1
  content: In action_approve_lot, rename the _() placeholder source to lot_source
    so it no longer binds the positional-only source parameter of get_text_alias.
    Leave the mint(source=...) call unchanged. Bump plasticos_crm_bridge once.
  status: completed
- id: T2
  content: Move test_accepted_document_protects_the_parent_and_blocks_unlink into
    a new plasticos_documents test. documents already depends on logistics, so logistics
    must not depend on documents. Recreate the sale order, transaction, and load with
    the public models and keep the accepted-association and unlink assertions. Bump
    plasticos_logistics and plasticos_documents once each.
  status: completed
- id: T3
  content: Add sale_crm next to sale_management in plasticos_transaction depends so
    sale.order.opportunity_id is a real field. Keep the missing-field guard. sale_crm
    depends only on sale and crm, and plasticos_crm_bridge already depends on transaction,
    so this does not cycle. One transaction version bump covers T3, T4, and T6.
  status: completed
- id: T4
  content: Add mail.activity.mixin to plasticos.transaction _inherit. mail is already
    a dependency. activity_schedule is called today and is defined on that mixin,
    not on mail.thread. Do not add a second mail depends line.
  status: completed
- id: T5
  content: Replace the material_description attribute read in action_create_purchase_order
    with a hook that returns display_name. Override that hook in a new plasticos_order_lines
    inherit of plasticos.material.profile and read material_description there, where
    purchase.order.line defines it. Do not add plasticos_order_lines to material_profile
    depends. Bump both modules once.
  status: completed
- id: T6
  content: Hoist _Report out of _silent in native_document_import.py, and hoist the
    three Adapter classes at test_orchestrator_upsert.py lines 606, 744, and 1757
    to module level without closing over the test method. Bump plasticos_crm_sync
    once. The transaction bump is the one shared with T3.
  status: completed
- id: T7
  content: Pin MarkupSafe==2.1.5 in requirements-dev.txt, the same pin Odoo 19 uses
    for Python 3.12, and install it into .venv. Leave plasticos_crm_bridge/models/web_lead.py
    unchanged when the rescan no longer reports markupsafe.Markup.
  status: completed
- id: T8
  content: Inside the existing try, import GateAuthorizationError and GateClientError
    from constellation_node_sdk.gate.errors and GateClient from constellation_node_sdk.gate.client.
    If the rescan still reports OLS02001, replace that static import with importlib.import_module
    and bind the three names from the loaded module. Keep the except path and the
    optional-SDK behavior. Bump plasticos_gate once for T8 and T9.
  status: completed
- id: T9
  content: After the existing sys.path insert, load scripts.evidence_odoo_mapping_consumer
    with importlib and bind the eight re-exported names from that module. Do not move
    the policy module into the addon. The phantom-enum split stays.
  status: completed
- id: T10
  content: Keep the test_enable guard and bind TransactionCase once, so OdooLS no
    longer sees two definitions of the base class. Do not import odoo.tests.common
    when test mode is off. Bump plasticos_base once. If the rescan still reports OLS01003,
    stop and do not add a diagnostic filter.
  status: completed
- id: T11
  content: Re-run make odools-diagnostics. The pass condition is that none of the
    22 current rows remain. Do not treat a new unrelated row as one of these 22.
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Repair the remaining OdooLS diagnostics

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `repair_the_remaining_odools_diagnostics_6acfdbf3.plan.md`
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
| plan_id | `plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| name | Repair the remaining OdooLS diagnostics |
| overview | Clear the 4 errors, 14 warnings, and 4 information notes from the 2026-11-06 make odools-diagnostics run. Each repair stays in the module that owns the symbol. plasticos_logistics does not gain a dependency on plasticos_documents, and plasticos_material_profile does not gain a dependency on plasticos_order_lines. Branch from Staging at 09c65ed5. Publication is make pr into Staging. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1, U2 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-06T15:42:31+00:00 |
| updated_at | 2026-11-06T15:42:31+00:00 |
| depth | `standard` |
| estimate | one implementation pass across nine modules and one dev pin |

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
| captured_at | `2026-11-06T15:42:31+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `Staging` |
| commit_sha | `09c65ed5b389e1d688643a534a28d2e47432ec8b` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Clear the 4 errors, 14 warnings, and 4 information notes from the 2026-11-06 make odools-diagnostics run. Each repair stays in the module that owns the symbol. plasticos_logistics does not gain a dependency on plasticos_documents, and plasticos_material_profile does not gain a dependency on plasticos_order_lines. Branch from Staging at 09c65ed5. Publication is make pr into Staging.

### Scope in

- plasticos_crm_bridge/models/crm_lead.py placeholder rename
- Move test_accepted_document_protects_the_parent_and_blocks_unlink from plasticos_logistics into plasticos_documents
- plasticos_transaction depends on sale_crm and plasticos.transaction inherits mail.activity.mixin
- material_description read moves to a plasticos_order_lines override
- Hoist the four nested classes in native_document_import.py and test_orchestrator_upsert.py
- Pin MarkupSafe==2.1.5 in requirements-dev.txt and install it into .venv
- Retarget the optional constellation_node_sdk and scripts.evidence_odoo_mapping_consumer imports so OdooLS no longer resolves them statically
- Single TransactionCase binding in plasticos_base/test_common.py
- One manifest version bump per edited plasticos module

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: a fresh make odools-diagnostics run no longer reports the 22 rows in .l9/odools/diagnostics.jsonl (4 OLS errors, 14 warnings, 4 information notes). | `quality_gate` | V1: `make odools-diagnostics` → none of the 22 rows in the planning .l9/odools/diagnostics.jsonl remain | `true` |
| SP-02 | V2: ruff check and ruff format --check pass on every Python file this plan edits. | `quality_gate` | V2: `.venv/bin/ruff check . && .venv/bin/ruff format --check .` → no ruff findings on the edited Python | `true` |
| SP-03 | V3: scripts/check_module_wiring.py and ci/check_circular_deps.py pass after the sale_crm depends line and the test move. | `quality_gate` | V3: `python3 scripts/check_module_wiring.py && python3 ci/check_circular_deps.py` → wiring and circular-deps both pass | `true` |
| SP-04 | V4: .pre-commit-config.yaml commit-stage hooks pass on the change set. | `quality_gate` | V4: `.pre-commit-config.yaml` → commit-stage hooks pass | `true` |
| SP-05 | V5: make test-module proves the re-homed document association test and the transaction opportunity search still pass on the admitted Docker fixture. | `quality_gate` | V5: `make test-module m=plasticos_documents` → the re-homed association test passes on the admitted fixture; then make test-module m=plasticos_transaction for the opportunity search | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.repair_the_remaining_odools_diagnostics.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| source_ref | `plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --porcelain` | Staging at 09c65ed5; only untracked docs/campaigns/11-03-26/odoo test failures/ | `true` |
| P1 | pre-validation (status `passed`) | `make odools-diagnostics` | 22 rows written to .l9/odools/diagnostics.jsonl: 4 errors, 14 warnings, 4 information notes | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence partial --json` | depth standard and omit_gates empty | `true` |
| P3 | pre-validation (status `passed`) | `gh pr list --base Staging --state open` | no open pull request; branch the repair from Staging | `true` |
| P4 | pre-validation (status `passed`) | `name .pre-commit-config.yaml as the hook catalog for this workspace` | catalog present; hooks run at commit, not during planning | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_crm_bridge/models/crm_lead.py`, `plasticos_crm_bridge/__manifest__.py`, `plasticos_logistics/tests/test_load_cardinality.py`, `plasticos_logistics/__manifest__.py`, `plasticos_documents/tests/`, `plasticos_documents/__manifest__.py`, `plasticos_transaction/models/sale_inherit.py`, `plasticos_transaction/models/transaction.py`, `plasticos_transaction/models/native_document_import.py`, `plasticos_transaction/__manifest__.py`, `plasticos_material_profile/models/material_profile.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_order_lines/models/`, `plasticos_order_lines/__manifest__.py`, `plasticos_gate/services/gate_client.py`, `plasticos_gate/services/evidence_mapping.py`, `plasticos_gate/__manifest__.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py`, `plasticos_crm_sync/__manifest__.py`, `plasticos_base/test_common.py`, `plasticos_base/__manifest__.py`, `requirements-dev.txt`
- **write_deny:** `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `make odools-diagnostics`, `.venv/bin/ruff check . && .venv/bin/ruff format --check .`, `python3 scripts/check_module_wiring.py && python3 ci/check_circular_deps.py`, `.pre-commit-config.yaml`, `make test-module m=plasticos_documents`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `pypi.org` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- Layer order: a lower module does not depend on a higher one
- plasticos_documents keeps its dependency on plasticos_logistics
- Gate SDK import stays optional and fail-closed
- Evidence mapping policy stays in scripts/ for the phantom-enum split
- odoo.tests is not imported when test mode is off
- One 19.0.X.Y.Z bump per edited module, then make update only for those modules
- Publication is make pr into Staging from a branch off Staging
- Untracked rehearsal screenshots stay untracked

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_bridge/models/crm_lead.py plasticos_crm_bridge/__manifest__.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_logistics/tests/test_load_cardinality.py plasticos_logistics/__manifest__.py plasticos_documents/tests/test_load_document_association.py plasticos_documents/tests/__init__.py plasticos_documents/__manifest__.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/__manifest__.py plasticos_transaction/models/sale_inherit.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/models/transaction.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_profile.py plasticos_material_profile/__manifest__.py plasticos_order_lines/models/material_profile.py plasticos_order_lines/models/__init__.py plasticos_order_lines/__manifest__.py` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/models/native_document_import.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_crm_sync/__manifest__.py` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- requirements-dev.txt` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_gate/services/gate_client.py plasticos_gate/__manifest__.py` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_gate/services/evidence_mapping.py` | `false` |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_base/test_common.py plasticos_base/__manifest__.py` | `false` |
| T11 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .l9/odools/diagnostics.jsonl` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `plasticos_crm_bridge` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T2 | `repository root` | `assurance` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T3 | `plasticos_transaction` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T4 | `plasticos_transaction/models` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T5 | `repository root` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T6 | `repository root` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T7 | `repository root` | `ops` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T8 | `plasticos_gate` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T9 | `plasticos_gate/services` | `runtime` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T10 | `plasticos_base` | `assurance` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |
| T11 | `.l9/odools` | `assurance` | `Layer order: a lower module does not depend on a higher one`, `plasticos_documents keeps its dependency on plasticos_logistics`, `Gate SDK import stays optional and fail-closed`, `Evidence mapping policy stays in scripts/ for the phantom-enum split`, `odoo.tests is not imported when test mode is off`, `One 19.0.X.Y.Z bump per edited module, then make update only for those modules`, `Publication is make pr into Staging from a branch off Staging`, `Untracked rehearsal screenshots stay untracked` | `plasticos_web_leads/`, `plasticos_logistics/__manifest__.py depends`, `plasticos_material_profile/__manifest__.py depends`, `docs/campaigns/11-03-26/odoo test failures/`, `odools.toml diagnostic_filters`, `pipeline_v2.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.repair_the_remaining_odools_diagnostics.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| source_execution_ref | `plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (check_circular_deps.py and check_module_wiring.py pass, and neither forbidden depends line exists) → revert the depends edit and keep the symbol in the owning module; C2 fails (ruff check and ruff format --check pass, and each edited module manifest version was bumped once) → do not start the rescan or the publication; C3 fails (make odools-diagnostics prints none of the 22 rows recorded in the planning diagnostics.jsonl) → stop on the remaining row; do not hide it with a diagnostic filter |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the branch before upgrade. After upgrade, removing mail.activity.mixin leaves its columns in place; do not drop them. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `make odools-diagnostics`
- re-run `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- re-run `python3 scripts/check_module_wiring.py && python3 ci/check_circular_deps.py`
- re-run `.pre-commit-config.yaml`
- re-run `make test-module m=plasticos_documents`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 11 todo(s) |
| uncertainty | `medium` — 2 unknown(s), 0 blocking |
| blast_radius | `medium` — Module upgrades for plasticos_transaction, plasticos_gate, plasticos_crm_bridge, plasticos_material_profile, plasticos_order_lines, plasticos_logistics, plasticos_documents, plasticos_crm_sync, and plasticos_base. A wrong test_common import fails Odoo.sh startup. sale_crm will install with transaction on the next upgrade. |
| architectural_boundaries_crossed | `document association test moves from plasticos_logistics to plasticos_documents`, `purchase line description read moves from plasticos_material_profile to plasticos_order_lines`, `plasticos_transaction declares sale_crm` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `2` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.repair_the_remaining_odools_diagnostics.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | In action_approve_lot, rename the _() placeholder source to lot_source so it no longer binds the positional-only source parameter of get_text_alias. Leave the mint(source=...) call unchanged. Bump plasticos_crm_bridge once. | Cursor Build agent | `low` | S | `[]` | `plasticos_crm_bridge/models/crm_lead.py`, `plasticos_crm_bridge/__manifest__.py` |
| T2 | Move test_accepted_document_protects_the_parent_and_blocks_unlink into a new plasticos_documents test. documents already depends on logistics, so logistics must not depend on documents. Recreate the sale order, transaction, and load with the public models and keep the accepted-association and unlink assertions. Bump plasticos_logistics and plasticos_documents once each. | Cursor Build agent | `medium` | M | `[]` | `plasticos_logistics/tests/test_load_cardinality.py`, `plasticos_logistics/__manifest__.py`, `plasticos_documents/tests/test_load_document_association.py`, `plasticos_documents/tests/__init__.py`, `plasticos_documents/__manifest__.py` |
| T3 | Add sale_crm next to sale_management in plasticos_transaction depends so sale.order.opportunity_id is a real field. Keep the missing-field guard. sale_crm depends only on sale and crm, and plasticos_crm_bridge already depends on transaction, so this does not cycle. One transaction version bump covers T3, T4, and T6. | Cursor Build agent | `medium` | S | `[]` | `plasticos_transaction/__manifest__.py`, `plasticos_transaction/models/sale_inherit.py` |
| T4 | Add mail.activity.mixin to plasticos.transaction _inherit. mail is already a dependency. activity_schedule is called today and is defined on that mixin, not on mail.thread. Do not add a second mail depends line. | Cursor Build agent | `medium` | S | `[]` | `plasticos_transaction/models/transaction.py` |
| T5 | Replace the material_description attribute read in action_create_purchase_order with a hook that returns display_name. Override that hook in a new plasticos_order_lines inherit of plasticos.material.profile and read material_description there, where purchase.order.line defines it. Do not add plasticos_order_lines to material_profile depends. Bump both modules once. | Cursor Build agent | `medium` | M | `[]` | `plasticos_material_profile/models/material_profile.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_order_lines/models/material_profile.py`, `plasticos_order_lines/models/__init__.py`, `plasticos_order_lines/__manifest__.py` |
| T6 | Hoist _Report out of _silent in native_document_import.py, and hoist the three Adapter classes at test_orchestrator_upsert.py lines 606, 744, and 1757 to module level without closing over the test method. Bump plasticos_crm_sync once. The transaction bump is the one shared with T3. | Cursor Build agent | `low` | S | `[]` | `plasticos_transaction/models/native_document_import.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py`, `plasticos_crm_sync/__manifest__.py` |
| T7 | Pin MarkupSafe==2.1.5 in requirements-dev.txt, the same pin Odoo 19 uses for Python 3.12, and install it into .venv. Leave plasticos_crm_bridge/models/web_lead.py unchanged when the rescan no longer reports markupsafe.Markup. | Cursor Build agent | `low` | S | `[]` | `requirements-dev.txt` |
| T8 | Inside the existing try, import GateAuthorizationError and GateClientError from constellation_node_sdk.gate.errors and GateClient from constellation_node_sdk.gate.client. If the rescan still reports OLS02001, replace that static import with importlib.import_module and bind the three names from the loaded module. Keep the except path and the optional-SDK behavior. Bump plasticos_gate once for T8 and T9. | Cursor Build agent | `medium` | S | `[]` | `plasticos_gate/services/gate_client.py`, `plasticos_gate/__manifest__.py` |
| T9 | After the existing sys.path insert, load scripts.evidence_odoo_mapping_consumer with importlib and bind the eight re-exported names from that module. Do not move the policy module into the addon. The phantom-enum split stays. | Cursor Build agent | `medium` | S | `[]` | `plasticos_gate/services/evidence_mapping.py` |
| T10 | Keep the test_enable guard and bind TransactionCase once, so OdooLS no longer sees two definitions of the base class. Do not import odoo.tests.common when test mode is off. Bump plasticos_base once. If the rescan still reports OLS01003, stop and do not add a diagnostic filter. | Cursor Build agent | `medium` | S | `[]` | `plasticos_base/test_common.py`, `plasticos_base/__manifest__.py` |
| T11 | Re-run make odools-diagnostics. The pass condition is that none of the 22 current rows remain. Do not treat a new unrelated row as one of these 22. | Cursor Build agent | `low` | S | `[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]` | `.l9/odools/diagnostics.jsonl` |

**Critical path:** T2 → T5 → T3 → T4 → T1 → T8 → T9 → T7 → T10 → T6 → T11

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The two illegal dependency repairs are in the owning modules | the remaining symbol repairs cannot reintroduce a cycle or a layer inversion |
| M2 | Every other current diagnostic has its declared repair | the acceptance rescan |
| M3 | The 22 current OdooLS rows are gone | scoped commit and make pr into Staging |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | check_circular_deps.py and check_module_wiring.py pass, and neither forbidden depends line exists | revert the depends edit and keep the symbol in the owning module |
| C2 | M2 | ruff check and ruff format --check pass, and each edited module manifest version was bumped once | do not start the rescan or the publication |
| C3 | M3 | make odools-diagnostics prints none of the 22 rows recorded in the planning diagnostics.jsonl | stop on the remaining row; do not hide it with a diagnostic filter |

### Leverage

- **Ranked todos:** `T2`, `T5`, `T3`, `T4`, `T1`, `T8`, `T9`, `T7`, `T10`, `T6`, `T11`
- **Shared causes:** symbol referenced outside the module that owns it; optional import written as a static from-import; class nested inside a function
- **Deletions / consolidations:** delete the document-association test from plasticos_logistics instead of adding a circular depends; one version bump per module, not one bump per todo

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | No command, module count, or CI contract changes |
| INVARIANTS.md | `n_a` | — | No invariant is added or relaxed |
| CLAUDE.md | `n_a` | — | Root instructions stay append-only and this repair does not change them |
| requirements-dev.txt | `update` | `T7` | — |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `make odools-diagnostics` | none of the 22 rows in the planning .l9/odools/diagnostics.jsonl remain | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` | no ruff findings on the edited Python | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `python3 scripts/check_module_wiring.py && python3 ci/check_circular_deps.py` | wiring and circular-deps both pass | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | commit-stage hooks pass | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `make test-module m=plasticos_documents` | the re-homed association test passes on the admitted fixture; then make test-module m=plasticos_transaction for the opportunity search | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does sale_crm on plasticos_transaction cycle through plasticos_crm_bridge, which already depends on transaction?
- Does moving the document test drop the unlink assertion or leave logistics calling plasticos.document?
- Does importlib hide a Gate SDK name the runtime import currently binds?
- Does mail.activity.mixin add stored activity columns the transaction model does not already need for activity_schedule?
- Does the TransactionCase edit import odoo.tests.common during a normal registry load?

### Assumption failure conditions

- plasticos_documents can be added to plasticos_logistics depends
- plasticos_order_lines can be added to plasticos_material_profile depends
- installing MarkupSafe into .venv changes the Odoo.sh runtime image

### Blast radius notes

- Module upgrades for plasticos_transaction, plasticos_gate, plasticos_crm_bridge, plasticos_material_profile, plasticos_order_lines, plasticos_logistics, plasticos_documents, plasticos_crm_sync, and plasticos_base. A wrong test_common import fails Odoo.sh startup. sale_crm will install with transaction on the next upgrade.

### Rollback constraints

- Revert the branch before upgrade. After upgrade, removing mail.activity.mixin leaves its columns in place; do not drop them.

### Risks

| risk | mitigation |
|------|------------|
| sale_crm pulls crm into every transaction install | The domain already refuses to run without opportunity_id. sale_crm is the community module that defines that field, and it does not depend on any plasticos module. |
| mail.activity.mixin adds stored fields on plasticos.transaction | The model already calls activity_schedule. The mixin is the declaration of that call. Do not write a column drop. |
| The re-homed documents test cannot build a load without the logistics fixtures | documents depends on logistics and transaction, so the test creates the records through the public models and asserts the same association and unlink results. |
| A test_common import regression marks Odoo.sh failed at startup | The test_enable guard stays. odoo.tests.common is imported only when that guard is true. |

## Out of scope

- Adding plasticos_documents to plasticos_logistics depends
- Adding plasticos_order_lines to plasticos_material_profile depends
- Editing plasticos_web_leads write or unlink guards or _find_or_create_partner
- Changing the web_lead Markup import if the venv pin clears OLS02001
- Committing docs/campaigns/11-03-26/odoo test failures/
- New models, new features, column drops, or a migrations folder
- Branching from origin/main
- Diagnostic filters that hide these OLS codes
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.repair_the_remaining_odools_diagnostics.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.repair_the_remaining_odools_diagnostics.v1` |
| source_ref | `plan.simple.repair_the_remaining_odools_diagnostics.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Does OdooLS resolve GateAuthorizationError from constellation_node_sdk.gate.errors, or only after the static import is removed? — T8 tries the defining module first and falls back to importlib only if the rescan still reports OLS02001. | `probe` |
| `unknown` | U2 | Does a single TransactionCase assignment clear OLS01003 while the test_enable guard remains? — T10 stops if the rescan still reports OLS01003. No diagnostic filter is added. | `probe` |
| `open_blocker` | stop_reason | Architecture is settled and the plan is ready for Build. U1 and U2 are probes inside T8 and T10, not blockers to starting. | planning convergence `partial` |

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
  plan_id: "plan.simple.repair_the_remaining_odools_diagnostics.v1"
  name: "Repair the remaining OdooLS diagnostics"
  overview: "Clear the 4 errors, 14 warnings, and 4 information notes from the 2026-11-06 make odools-diagnostics run. Each repair stays in the module that owns the symbol. plasticos_logistics does not gain a dependency on plasticos_documents, and plasticos_material_profile does not gain a dependency on plasticos_order_lines. Branch from Staging at 09c65ed5. Publication is make pr into Staging."
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
  commit_sha: "09c65ed5b389e1d688643a534a28d2e47432ec8b"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Clear the 4 errors, 14 warnings, and 4 information notes from the 2026-11-06 make odools-diagnostics run. Each repair stays in the module that owns the symbol. plasticos_logistics does not gain a dependency on plasticos_documents, and plasticos_material_profile does not gain a dependency on plasticos_order_lines. Branch from Staging at 09c65ed5. Publication is make pr into Staging."
  success_properties:
    - id: "SP-01"
      property: "V1: a fresh make odools-diagnostics run no longer reports the 22 rows in .l9/odools/diagnostics.jsonl (4 OLS errors, 14 warnings, 4 information notes)."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: ruff check and ruff format --check pass on every Python file this plan edits."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3: scripts/check_module_wiring.py and ci/check_circular_deps.py pass after the sale_crm depends line and the test move."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4: .pre-commit-config.yaml commit-stage hooks pass on the change set."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-05"
      property: "V5: make test-module proves the re-homed document association test and the transaction opportunity search still pass on the admitted Docker fixture."
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.repair_the_remaining_odools_diagnostics.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_crm_bridge/models/crm_lead.py", "plasticos_crm_bridge/__manifest__.py", "plasticos_logistics/tests/test_load_cardinality.py", "plasticos_logistics/__manifest__.py", "plasticos_documents/tests/", "plasticos_documents/__manifest__.py", "plasticos_transaction/models/sale_inherit.py", "plasticos_transaction/models/transaction.py", "plasticos_transaction/models/native_document_import.py", "plasticos_transaction/__manifest__.py", "plasticos_material_profile/models/material_profile.py", "plasticos_material_profile/__manifest__.py", "plasticos_order_lines/models/", "plasticos_order_lines/__manifest__.py", "plasticos_gate/services/gate_client.py", "plasticos_gate/services/evidence_mapping.py", "plasticos_gate/__manifest__.py", "plasticos_crm_sync/tests/test_orchestrator_upsert.py", "plasticos_crm_sync/__manifest__.py", "plasticos_base/test_common.py", "plasticos_base/__manifest__.py", "requirements-dev.txt"]
    write_deny: ["plasticos_web_leads/", "plasticos_logistics/__manifest__.py depends", "plasticos_material_profile/__manifest__.py depends", "docs/campaigns/11-03-26/odoo test failures/", "odools.toml diagnostic_filters", "pipeline_v2.py"]
  commands:
    allow: ["make odools-diagnostics", ".venv/bin/ruff check . && .venv/bin/ruff format --check .", "python3 scripts/check_module_wiring.py && python3 ci/check_circular_deps.py", ".pre-commit-config.yaml", "make test-module m=plasticos_documents"]
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
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T8"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T9"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T10"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T11"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.repair_the_remaining_odools_diagnostics.v1"
dependency_topology_ref: "dag.plan.simple.repair_the_remaining_odools_diagnostics.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5"]
stress_and_disconfirm:
  disconfirming_cases: ["Does sale_crm on plasticos_transaction cycle through plasticos_crm_bridge, which already depends on transaction?", "Does moving the document test drop the unlink assertion or leave logistics calling plasticos.document?", "Does importlib hide a Gate SDK name the runtime import currently binds?", "Does mail.activity.mixin add stored activity columns the transaction model does not already need for activity_schedule?", "Does the TransactionCase edit import odoo.tests.common during a normal registry load?"]
  assumption_failure_conditions: ["plasticos_documents can be added to plasticos_logistics depends", "plasticos_order_lines can be added to plasticos_material_profile depends", "installing MarkupSafe into .venv changes the Odoo.sh runtime image"]
out_of_scope: ["Adding plasticos_documents to plasticos_logistics depends", "Adding plasticos_order_lines to plasticos_material_profile depends", "Editing plasticos_web_leads write or unlink guards or _find_or_create_partner", "Changing the web_lead Markup import if the venv pin clears OLS02001", "Committing docs/campaigns/11-03-26/odoo test failures/", "New models, new features, column drops, or a migrations folder", "Branching from origin/main", "Diagnostic filters that hide these OLS codes"]
convergence_contract_ref: "conv.plan.simple.repair_the_remaining_odools_diagnostics.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "In action_approve_lot, rename the _() placeholder source to lot_source so it no longer binds the positional-only source parameter of get_text_alias. Leave the mint(source=...) call unchanged. Bump plasticos_crm_bridge once."
    status: "pending"
  - id: "T2"
    content: "Move test_accepted_document_protects_the_parent_and_blocks_unlink into a new plasticos_documents test. documents already depends on logistics, so logistics must not depend on documents. Recreate the sale order, transaction, and load with the public models and keep the accepted-association and unlink assertions. Bump plasticos_logistics and plasticos_documents once each."
    status: "pending"
  - id: "T3"
    content: "Add sale_crm next to sale_management in plasticos_transaction depends so sale.order.opportunity_id is a real field. Keep the missing-field guard. sale_crm depends only on sale and crm, and plasticos_crm_bridge already depends on transaction, so this does not cycle. One transaction version bump covers T3, T4, and T6."
    status: "pending"
  - id: "T4"
    content: "Add mail.activity.mixin to plasticos.transaction _inherit. mail is already a dependency. activity_schedule is called today and is defined on that mixin, not on mail.thread. Do not add a second mail depends line."
    status: "pending"
  - id: "T5"
    content: "Replace the material_description attribute read in action_create_purchase_order with a hook that returns display_name. Override that hook in a new plasticos_order_lines inherit of plasticos.material.profile and read material_description there, where purchase.order.line defines it. Do not add plasticos_order_lines to material_profile depends. Bump both modules once."
    status: "pending"
  - id: "T6"
    content: "Hoist _Report out of _silent in native_document_import.py, and hoist the three Adapter classes at test_orchestrator_upsert.py lines 606, 744, and 1757 to module level without closing over the test method. Bump plasticos_crm_sync once. The transaction bump is the one shared with T3."
    status: "pending"
  - id: "T7"
    content: "Pin MarkupSafe==2.1.5 in requirements-dev.txt, the same pin Odoo 19 uses for Python 3.12, and install it into .venv. Leave plasticos_crm_bridge/models/web_lead.py unchanged when the rescan no longer reports markupsafe.Markup."
    status: "pending"
  - id: "T8"
    content: "Inside the existing try, import GateAuthorizationError and GateClientError from constellation_node_sdk.gate.errors and GateClient from constellation_node_sdk.gate.client. If the rescan still reports OLS02001, replace that static import with importlib.import_module and bind the three names from the loaded module. Keep the except path and the optional-SDK behavior. Bump plasticos_gate once for T8 and T9."
    status: "pending"
  - id: "T9"
    content: "After the existing sys.path insert, load scripts.evidence_odoo_mapping_consumer with importlib and bind the eight re-exported names from that module. Do not move the policy module into the addon. The phantom-enum split stays."
    status: "pending"
  - id: "T10"
    content: "Keep the test_enable guard and bind TransactionCase once, so OdooLS no longer sees two definitions of the base class. Do not import odoo.tests.common when test mode is off. Bump plasticos_base once. If the rescan still reports OLS01003, stop and do not add a diagnostic filter."
    status: "pending"
  - id: "T11"
    content: "Re-run make odools-diagnostics. The pass condition is that none of the 22 current rows remain. Do not treat a new unrelated row as one of these 22."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-06T15:57:37Z`
- conversation_id: `9a697480-779d-432e-900a-6e4cbd10bf03`
- generation_id: `50e636f6-d4a3-406c-bcff-428f8ea1c840`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/9a697480-779d-432e-900a-6e4cbd10bf03/9a697480-779d-432e-900a-6e4cbd10bf03.jsonl`
- todos at build time:
- `T1`: completed
- `T2`: completed
- `T3`: completed
- `T4`: completed
- `T5`: completed
- `T6`: completed
- `T7`: completed
- `T8`: completed
- `T9`: completed
- `T10`: completed
- `T11`: completed
