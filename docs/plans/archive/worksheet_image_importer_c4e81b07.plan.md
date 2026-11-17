---
name: Worksheet image importer
overview: "Partition the eligible worksheet images against Production transaction names, install the already-shipped plasticos_documents_native bridge on the running Production database, and add an idempotent writer that attaches one decoded file to the one matching transaction. Publication is make pr into Staging. This pass does not upload the 97346 files."
todos:
  - id: T1
    content: "Partition the private journal before any writer exists. Read /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv, /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv, and the Drive folder /Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded. Keep ImportScope eligible only. Match RefID to name with Python string equality, preserving suffixes and hyphens. A unique match requires one name and a decoded file. ImageID 633316 is the known not_gzip integrity failure and has no file. Zero names is missing. Two or more names is ambiguous. Write the four counts and the exception rows to /Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json. Leave journal.csv and the decoded folder unchanged. Stop T2, T3, and T4 when eligible does not equal unique plus missing plus ambiguous plus integrity failure."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "On the running Production database, read ir.module.module state for documents, documents_account, plasticos_documents, plasticos_logistics, plasticos_transaction, plasticos_intake, plasticos_material_profile, and plasticos_security_base. When any state is not installed, stop and name that module. When all eight are installed, install plasticos_documents_native on cryptoxdog-ib-odoo-19-production-29882273 using the code already at eff41988 and confirm documents.document has a field named transaction_id. Upload no images."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Cut the branch from origin/Staging. Do not use feat/web-lead-location and do not stack onto the open campaign docs branch. Add plasticos_documents_native/erp_worksheet_match.py with no Odoo import. It accepts journal rows, transaction names, and a decoded directory, returns the four partitions, and refuses an eligible ImportScope whose RefType is outside W and #. tests/test_erp_worksheet_image_match.py loads that file with importlib from its path and covers a suffixed hit, a bare-number miss, a duplicate name, a missing name, and ImageID 633316 with no file."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Add documents.document.erp_source_key, a stored indexed Char, with models.Constraint UniqueConstraint so an empty key stays NULL and repeats are rejected. Add AbstractModel plasticos.erp.worksheet.image.importer in models/erp_worksheet_image.py and import it from models/__init__.py. Its run method calls the pure matcher. For each unique match it creates one ir.attachment from decoded bytes and one documents.document in folder xmlid plasticos_documents_native.folder_plasticos_inbox, sets transaction_id, sets erp_source_key to erp_SM plus the ImageID, and sets company_id from the transaction sale order. It omits verified, verified_by, verified_at, override, override_reason, owner_id, doc_type, partner_id, and load_id. It does not call sync_native_to_legacy or action_associate_exact. It searches the key first so a second run creates zero documents and zero attachments. commit_every defaults to 0 so Odoo tests stay inside one cursor. The later Production runner passes 200. Missing, ambiguous, and missing-file rows are returned and not written. The method writes no transaction, order, invoice, stock move, or mail.mail. Tracking on the new document may add a mail.message on that document only. Bump plasticos_documents_native from 19.0.1.2.13 to 19.0.1.2.14. Add plasticos_documents_native/tests/test_erp_worksheet_image.py for one create and one replay, and assert mail.mail count and the transaction write count stay unchanged."
    status: pending
    phase: execute
    depends_on: [T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Worksheet image importer

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `worksheet_image_importer_fcbdbacf.plan.md`
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
| plan_id | `plan.simple.worksheet_image_importer.v1` |
| name | Worksheet image importer |
| overview | Partition the eligible worksheet images against Production transaction names, install the already-shipped plasticos_documents_native bridge on the running Production database, and add an idempotent writer that attaches one decoded file to the one matching transaction. Publication is make pr into Staging. This pass does not upload the 97346 files. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-10T18:14:42+00:00 |
| updated_at | 2026-11-10T18:14:42+00:00 |
| depth | `deep` |
| estimate | one private count, one Production module install, and one Staging writer |

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
| captured_at | `2026-11-10T18:14:42+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `feat/web-lead-location` |
| commit_sha | `e08b6581a8713d217998556917b677a16fa6fb86` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Partition the eligible worksheet images against Production transaction names, install the already-shipped plasticos_documents_native bridge on the running Production database, and add an idempotent writer that attaches one decoded file to the one matching transaction. Publication is make pr into Staging. This pass does not upload the 97346 files.

### Scope in

- Read-only partition of journal.import-scope.csv against production-transactions.csv and the Drive decoded folder
- Install of the already-shipped plasticos_documents_native module on the Production database after its eight dependencies are confirmed installed
- Stored erp_source_key on documents.document and one AbstractModel importer in plasticos_documents_native
- Pytest of the pure matcher and one Odoo test of create-once replay
- Patch version bump of plasticos_documents_native and publication to Staging from a branch cut off origin/Staging

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves eligible rows equal unique match plus missing transaction plus ambiguous transaction plus integrity failure, and RefID 51687-JCH does not match a transaction named 51687. | `quality_gate` | V1: `python3 -m pytest tests/test_erp_worksheet_image_match.py -q` → Eligible count equals unique plus missing plus ambiguous plus integrity failure, and a suffixed RefID does not match the bare worksheet number. | `true` |
| SP-02 | V2 proves one ImageID creates one documents.document with transaction_id set and erp_source_key erp_SM:<ImageID>, and a second run creates zero documents and zero attachments. | `quality_gate` | V2: `odoo test plasticos_documents_native.tests.test_erp_worksheet_image` → The first call creates one document bound to the transaction. The second call creates zero documents and zero attachments. mail.mail and the transaction write count stay unchanged.; V3: `odoo-bin shell read of ir.module.module and documents.document._fields on the Production database` → plasticos_documents_native state is installed and transaction_id is a field. | `true` |
| SP-03 | V3 proves plasticos_documents_native is installed on cryptoxdog-ib-odoo-19-production-29882273 and documents.document has transaction_id. | `quality_gate` | V3: `odoo-bin shell read of ir.module.module and documents.document._fields on the Production database` → plasticos_documents_native state is installed and transaction_id is a field. | `true` |
| SP-04 | V4 proves the changed Python passes the hook catalog in .pre-commit-config.yaml. | `quality_gate` | V4: `.pre-commit-config.yaml` → The changed Python passes the catalogued hooks. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.worksheet_image_importer.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.worksheet_image_importer.v1` |
| source_ref | `plan.simple.worksheet_image_importer.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.worksheet_image_importer.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `Read Production ir.module.module for documents, documents_account, and plasticos_documents_native` | documents and documents_account are installed. plasticos_documents_native is uninstalled. Host ampp304, database cryptoxdog-ib-odoo-19-production-29882273, checkout eff41988 dated 2026-11-10T02:13:53+00:00. 7727 transactions, 7727 unique names, company Scrap Management Inc. | `true` |
| P1 | pre-validation (status `passed`) | `Read document_native.create and document_sync.batch_sync_unlinked` | create calls _refuse_direct_decision_write and raises AccessError when verified is in vals. batch_sync_unlinked requires doc_type. _schedule_review_once returns when owner_id is empty. Setting transaction_id alone does not call sync. | `true` |
| P2 | pre-validation (status `passed`) | `Bind the workspace and cite MEMORY_PREFETCH` | HEAD is feat/web-lead-location at e08b6581. MEMORY_PREFETCH namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f conflicts 0. Hook catalog is .pre-commit-config.yaml. The writer branch is cut from origin/Staging. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_documents_native/erp_worksheet_match.py`, `plasticos_documents_native/models/document_native.py`, `plasticos_documents_native/models/erp_worksheet_image.py`, `plasticos_documents_native/models/__init__.py`, `plasticos_documents_native/__manifest__.py`, `plasticos_documents_native/tests/test_erp_worksheet_image.py`, `tests/test_erp_worksheet_image_match.py`, `/Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json`
- **write_deny:** `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded`, `plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/test_erp_worksheet_image_match.py -q`, `odoo test plasticos_documents_native.tests.test_erp_worksheet_image`, `.pre-commit-config.yaml`, `odoo-bin shell read of ir.module.module and documents.document._fields on the Production database`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `odoo.sh production ssh` |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- RefID equals plasticos.transaction.name with suffixes preserved.
- verified is not written.
- erp_source_key erp_SM:<ImageID> is unique and a replay creates nothing.
- The Production image upload waits until this writer is on that build.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- /Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_documents_native/__manifest__.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_documents_native/erp_worksheet_match.py tests/test_erp_worksheet_image_match.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_documents_native/models/document_native.py plasticos_documents_native/models/erp_worksheet_image.py plasticos_documents_native/models/__init__.py plasticos_documents_native/__manifest__.py plasticos_documents_native/tests/test_erp_worksheet_image.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `//Users/ib-mac/Odoo-ERP-Files/private` | `data_plane` | `RefID equals plasticos.transaction.name with suffixes preserved.`, `verified is not written.`, `erp_source_key erp_SM:<ImageID> is unique and a replay creates nothing.`, `The Production image upload waits until this writer is on that build.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded`, `plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail` |
| T2 | `plasticos_documents_native` | `external_system` | `RefID equals plasticos.transaction.name with suffixes preserved.`, `verified is not written.`, `erp_source_key erp_SM:<ImageID> is unique and a replay creates nothing.`, `The Production image upload waits until this writer is on that build.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded`, `plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail` |
| T3 | `repository root` | `data_plane` | `RefID equals plasticos.transaction.name with suffixes preserved.`, `verified is not written.`, `erp_source_key erp_SM:<ImageID> is unique and a replay creates nothing.`, `The Production image upload waits until this writer is on that build.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded`, `plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail` |
| T4 | `plasticos_documents_native` | `runtime` | `RefID equals plasticos.transaction.name with suffixes preserved.`, `verified is not written.`, `erp_source_key erp_SM:<ImageID> is unique and a replay creates nothing.`, `The Production image upload waits until this writer is on that build.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded`, `plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.worksheet_image_importer.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.worksheet_image_importer.v1` |
| source_execution_ref | `plan.simple.worksheet_image_importer.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 passes and the private receipt stores the four counts.) → Do not start the writer and do not install the bridge when the eligible identity does not close.; C2 fails (V2, V3, and V4 pass.) → Do not call the importer against the Drive folder on Production. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | This pass uploads no files, so there is no file rollback. Revert the module bump to remove the writer from Staging. The Production bridge install is limited to the module already present in checkout eff41988. The Drive extract remains the source copy the operator can restore from. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/test_erp_worksheet_image_match.py -q`
- re-run `odoo test plasticos_documents_native.tests.test_erp_worksheet_image`
- re-run `.pre-commit-config.yaml`
- re-run `odoo-bin shell read of ir.module.module and documents.document._fields on the Production database`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 4 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `high` — A wrong match attaches an image to the wrong worksheet. A missing idempotency key duplicates originals on retry. Installing the bridge on Production changes that database module set and does not upload files. A later upload is a separate pass and is outside this plan. |
| architectural_boundaries_crossed | `documents.document transaction link`, `hosted Production module install` |
| external_systems_touched | `Odoo.sh Production` |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.worksheet_image_importer.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.worksheet_image_importer.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Partition the private journal before any writer exists. Read /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv, /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv, and the Drive folder /Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded. Keep ImportScope eligible only. Match RefID to name with Python string equality, preserving suffixes and hyphens. A unique match requires one name and a decoded file. ImageID 633316 is the known not_gzip integrity failure and has no file. Zero names is missing. Two or more names is ambiguous. Write the four counts and the exception rows to /Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json. Leave journal.csv and the decoded folder unchanged. Stop T2, T3, and T4 when eligible does not equal unique plus missing plus ambiguous plus integrity failure. | Cursor Build agent | `low` | S | `[]` | `/Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json` |
| T2 | On the running Production database, read ir.module.module state for documents, documents_account, plasticos_documents, plasticos_logistics, plasticos_transaction, plasticos_intake, plasticos_material_profile, and plasticos_security_base. When any state is not installed, stop and name that module. When all eight are installed, install plasticos_documents_native on cryptoxdog-ib-odoo-19-production-29882273 using the code already at eff41988 and confirm documents.document has a field named transaction_id. Upload no images. | Cursor Build agent | `medium` | S | `[T1]` | `plasticos_documents_native/__manifest__.py` |
| T3 | Cut the branch from origin/Staging. Do not use feat/web-lead-location and do not stack onto the open campaign docs branch. Add plasticos_documents_native/erp_worksheet_match.py with no Odoo import. It accepts journal rows, transaction names, and a decoded directory, returns the four partitions, and refuses an eligible ImportScope whose RefType is outside W and #. tests/test_erp_worksheet_image_match.py loads that file with importlib from its path and covers a suffixed hit, a bare-number miss, a duplicate name, a missing name, and ImageID 633316 with no file. | Cursor Build agent | `medium` | M | `[T1]` | `plasticos_documents_native/erp_worksheet_match.py`, `tests/test_erp_worksheet_image_match.py` |
| T4 | Add documents.document.erp_source_key, a stored indexed Char, with models.Constraint UniqueConstraint so an empty key stays NULL and repeats are rejected. Add AbstractModel plasticos.erp.worksheet.image.importer in models/erp_worksheet_image.py and import it from models/__init__.py. Its run method calls the pure matcher. For each unique match it creates one ir.attachment from decoded bytes and one documents.document in folder xmlid plasticos_documents_native.folder_plasticos_inbox, sets transaction_id, sets erp_source_key to erp_SM plus the ImageID, and sets company_id from the transaction sale order. It omits verified, verified_by, verified_at, override, override_reason, owner_id, doc_type, partner_id, and load_id. It does not call sync_native_to_legacy or action_associate_exact. It searches the key first so a second run creates zero documents and zero attachments. commit_every defaults to 0 so Odoo tests stay inside one cursor. The later Production runner passes 200. Missing, ambiguous, and missing-file rows are returned and not written. The method writes no transaction, order, invoice, stock move, or mail.mail. Tracking on the new document may add a mail.message on that document only. Bump plasticos_documents_native from 19.0.1.2.13 to 19.0.1.2.14. Add plasticos_documents_native/tests/test_erp_worksheet_image.py for one create and one replay, and assert mail.mail count and the transaction write count stay unchanged. | Cursor Build agent | `high` | L | `[T3]` | `plasticos_documents_native/models/document_native.py`, `plasticos_documents_native/models/erp_worksheet_image.py`, `plasticos_documents_native/models/__init__.py`, `plasticos_documents_native/__manifest__.py`, `plasticos_documents_native/tests/test_erp_worksheet_image.py` |

**Critical path:** T1 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The private crosswalk receipt closes the eligible identity and records how many Production worksheet names match. | The writer stays limited to the unique-match set, and the Production bridge install proceeds only after that close. |
| M2 | Production has transaction_id, and Staging has an idempotent importer that has not been pointed at the 97346 files. | A later Production load can run only after this commit is the running build and the receipt still matches. |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 passes and the private receipt stores the four counts. | Do not start the writer and do not install the bridge when the eligible identity does not close. |
| C2 | M2 | V2, V3, and V4 pass. | Do not call the importer against the Drive folder on Production. |

### Leverage

- **Ranked todos:** `T3`, `T4`, `T1`, `T2`
- **Shared causes:** the eligible image set has not been partitioned against Production names; no writer is keyed by erp_SM and ImageID
- **Deletions / consolidations:** Do not add a new document model.; Do not call the legacy sync or the verification writer.; Do not upload the decoded corpus in this pass.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The bridge and the exact worksheet-name rule already exist. This plan adds a writer and does not change a root contract. |
| INVARIANTS.md | `n_a` | — | No invariant id changes. Verified stays unread and unwritten. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_erp_worksheet_image_match.py -q` | Eligible count equals unique plus missing plus ambiguous plus integrity failure, and a suffixed RefID does not match the bare worksheet number. | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `odoo test plasticos_documents_native.tests.test_erp_worksheet_image` | The first call creates one document bound to the transaction. The second call creates zero documents and zero attachments. mail.mail and the transaction write count stay unchanged. | `not_run` |
| E-V3 | SP-02, SP-03 | `quality_gate_evidence` | command | `odoo-bin shell read of ir.module.module and documents.document._fields on the Production database` | plasticos_documents_native state is installed and transaction_id is a field. | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | The changed Python passes the catalogued hooks. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can RefID 51687-JCH attach to a transaction named 51687?
- Can a second run of the same ImageID create a second documents.document?
- Can setting transaction_id with an empty doc_type and an empty owner_id call sync_native_to_legacy or create a mail.mail row?
- Can the importer on the Staging pull request run against Production before that commit is the running build?

### Assumption failure conditions

- Git auto_install has already installed plasticos_documents_native on the running database.
- A sale order number is an acceptable substitute for plasticos.transaction.name.
- The current branch feat/web-lead-location is a safe base for this writer.
- A database backup is required before this pass.

### Blast radius notes

- A wrong match attaches an image to the wrong worksheet. A missing idempotency key duplicates originals on retry. Installing the bridge on Production changes that database module set and does not upload files. A later upload is a separate pass and is outside this plan.

### Rollback constraints

- This pass uploads no files, so there is no file rollback. Revert the module bump to remove the writer from Staging. The Production bridge install is limited to the module already present in checkout eff41988. The Drive extract remains the source copy the operator can restore from.

### Risks

| risk | mitigation |
|------|------------|
| create vals include verified and _refuse_direct_decision_write raises AccessError. | The writer never puts verified, verified_by, verified_at, override, or override_reason in create or write vals. The Odoo test asserts the computed verified value stays false. |
| doc_type or owner_id lets batch_sync_unlinked create a pending plasticos.document and an activity. | Leave doc_type, owner_id, partner_id, and load_id empty. The batch domain requires doc_type. _schedule_review_once returns when owner_id is empty. The Odoo test asserts mail.mail is unchanged. |
| A dependency of plasticos_documents_native is not installed, so the Production install fails halfway. | Read all eight dependency states first and stop with the missing module name before the install command. |
| The unique constraint rejects a legitimate second worksheet image because the key omitted ImageID, or it rejects ordinary documents because the empty value was stored as an empty string. | The key is erp_SM plus the ImageID, not the worksheet number. Many images may share one transaction_id. Leave the field False so Postgres stores NULL, which a unique constraint allows to repeat. |
| commit_every inside an Odoo test ends the test cursor and hides a failed assertion. | commit_every defaults to 0. Only the later Production runner passes 200. |

## Out of scope

- Uploading the 97346 decoded files to Production in this pass
- A second document store or a change to plasticos.document verification
- Rewriting journal.csv, the Drive decoded folder, or the server extract
- A backup, a restore, or a second Postgres
- Writes to plasticos.transaction, sale.order, purchase.order, account.move, stock, or mail.mail
- Implementation on feat/web-lead-location or on docs/campaigns-11-09-26
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.worksheet_image_importer.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.worksheet_image_importer.v1` |
| source_ref | `plan.simple.worksheet_image_importer.v1` |
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
| `open_blocker` | stop_reason | The partition, the bridge install, and the writer are specified. V1 through V4 run when those todos are built. The decoded upload stays outside this pass. | planning convergence `partial` |

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
  plan_id: "plan.simple.worksheet_image_importer.v1"
  name: "Worksheet image importer"
  overview: "Partition the eligible worksheet images against Production transaction names, install the already-shipped plasticos_documents_native bridge on the running Production database, and add an idempotent writer that attaches one decoded file to the one matching transaction. Publication is make pr into Staging. This pass does not upload the 97346 files."
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
  commit_sha: "e08b6581a8713d217998556917b677a16fa6fb86"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Partition the eligible worksheet images against Production transaction names, install the already-shipped plasticos_documents_native bridge on the running Production database, and add an idempotent writer that attaches one decoded file to the one matching transaction. Publication is make pr into Staging. This pass does not upload the 97346 files."
  success_properties:
    - id: "SP-01"
      property: "V1 proves eligible rows equal unique match plus missing transaction plus ambiguous transaction plus integrity failure, and RefID 51687-JCH does not match a transaction named 51687."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves one ImageID creates one documents.document with transaction_id set and erp_source_key erp_SM:<ImageID>, and a second run creates zero documents and zero attachments."
      evidence_type: "quality_gate"
      proof: ["V2", "V3"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves plasticos_documents_native is installed on cryptoxdog-ib-odoo-19-production-29882273 and documents.document has transaction_id."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves the changed Python passes the hook catalog in .pre-commit-config.yaml."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.worksheet_image_importer.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_documents_native/erp_worksheet_match.py", "plasticos_documents_native/models/document_native.py", "plasticos_documents_native/models/erp_worksheet_image.py", "plasticos_documents_native/models/__init__.py", "plasticos_documents_native/__manifest__.py", "plasticos_documents_native/tests/test_erp_worksheet_image.py", "tests/test_erp_worksheet_image_match.py", "/Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json"]
    write_deny: ["/Users/ib-mac/Odoo-ERP-Files/journal.csv", "/Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded", "plasticos.transaction, sale.order, purchase.order, account.move, stock, and mail.mail"]
  commands:
    allow: ["python3 -m pytest tests/test_erp_worksheet_image_match.py -q", "odoo test plasticos_documents_native.tests.test_erp_worksheet_image", ".pre-commit-config.yaml", "odoo-bin shell read of ir.module.module and documents.document._fields on the Production database"]
  network:
    mode: "bounded_external_write"
  secrets:
    access: "read_only_named"
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
rollback_contract_ref: "rollback.plan.simple.worksheet_image_importer.v1"
dependency_topology_ref: "dag.plan.simple.worksheet_image_importer.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Can RefID 51687-JCH attach to a transaction named 51687?", "Can a second run of the same ImageID create a second documents.document?", "Can setting transaction_id with an empty doc_type and an empty owner_id call sync_native_to_legacy or create a mail.mail row?", "Can the importer on the Staging pull request run against Production before that commit is the running build?"]
  assumption_failure_conditions: ["Git auto_install has already installed plasticos_documents_native on the running database.", "A sale order number is an acceptable substitute for plasticos.transaction.name.", "The current branch feat/web-lead-location is a safe base for this writer.", "A database backup is required before this pass."]
out_of_scope: ["Uploading the 97346 decoded files to Production in this pass", "A second document store or a change to plasticos.document verification", "Rewriting journal.csv, the Drive decoded folder, or the server extract", "A backup, a restore, or a second Postgres", "Writes to plasticos.transaction, sale.order, purchase.order, account.move, stock, or mail.mail", "Implementation on feat/web-lead-location or on docs/campaigns-11-09-26"]
convergence_contract_ref: "conv.plan.simple.worksheet_image_importer.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Partition the private journal before any writer exists. Read /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv, /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv, and the Drive folder /Users/ib-mac/Library/CloudStorage/GoogleDrive-ib@scrapmanagement.com/My Drive/ERP Blobs Restored/decoded. Keep ImportScope eligible only. Match RefID to name with Python string equality, preserving suffixes and hyphens. A unique match requires one name and a decoded file. ImageID 633316 is the known not_gzip integrity failure and has no file. Zero names is missing. Two or more names is ambiguous. Write the four counts and the exception rows to /Users/ib-mac/Odoo-ERP-Files/private/crosswalk-receipt.json. Leave journal.csv and the decoded folder unchanged. Stop T2, T3, and T4 when eligible does not equal unique plus missing plus ambiguous plus integrity failure."
    status: "pending"
  - id: "T2"
    content: "On the running Production database, read ir.module.module state for documents, documents_account, plasticos_documents, plasticos_logistics, plasticos_transaction, plasticos_intake, plasticos_material_profile, and plasticos_security_base. When any state is not installed, stop and name that module. When all eight are installed, install plasticos_documents_native on cryptoxdog-ib-odoo-19-production-29882273 using the code already at eff41988 and confirm documents.document has a field named transaction_id. Upload no images."
    status: "pending"
  - id: "T3"
    content: "Cut the branch from origin/Staging. Do not use feat/web-lead-location and do not stack onto the open campaign docs branch. Add plasticos_documents_native/erp_worksheet_match.py with no Odoo import. It accepts journal rows, transaction names, and a decoded directory, returns the four partitions, and refuses an eligible ImportScope whose RefType is outside W and #. tests/test_erp_worksheet_image_match.py loads that file with importlib from its path and covers a suffixed hit, a bare-number miss, a duplicate name, a missing name, and ImageID 633316 with no file."
    status: "pending"
  - id: "T4"
    content: "Add documents.document.erp_source_key, a stored indexed Char, with models.Constraint UniqueConstraint so an empty key stays NULL and repeats are rejected. Add AbstractModel plasticos.erp.worksheet.image.importer in models/erp_worksheet_image.py and import it from models/__init__.py. Its run method calls the pure matcher. For each unique match it creates one ir.attachment from decoded bytes and one documents.document in folder xmlid plasticos_documents_native.folder_plasticos_inbox, sets transaction_id, sets erp_source_key to erp_SM plus the ImageID, and sets company_id from the transaction sale order. It omits verified, verified_by, verified_at, override, override_reason, owner_id, doc_type, partner_id, and load_id. It does not call sync_native_to_legacy or action_associate_exact. It searches the key first so a second run creates zero documents and zero attachments. commit_every defaults to 0 so Odoo tests stay inside one cursor. The later Production runner passes 200. Missing, ambiguous, and missing-file rows are returned and not written. The method writes no transaction, order, invoice, stock move, or mail.mail. Tracking on the new document may add a mail.message on that document only. Bump plasticos_documents_native from 19.0.1.2.13 to 19.0.1.2.14. Add plasticos_documents_native/tests/test_erp_worksheet_image.py for one create and one replay, and assert mail.mail count and the transaction write count stay unchanged."
    status: "pending"
```
