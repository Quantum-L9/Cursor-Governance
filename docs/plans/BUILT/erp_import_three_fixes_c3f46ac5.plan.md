---
name: Fix ERP XMLID, quantity, and vendor-credit defects
overview: Make legacyXerpXoutinvX123 eligible for explicit automatic posting while
  a real archived ERP invoice stays unposted. Realize a zero-weight nonzero amount
  as amount divided by price only after the operator approves that rule, and quarantine
  a purchase-total payable that cannot be represented. Link a vendor credit only when
  ReverseBatchNo identifies exactly one original payable and the link does ...
todos:
- id: T1
  content: Drop the three =like name clauses from account.move._historical_source_ids.
    Keep module plasticos_transaction, model account.move, res_id in the recordset,
    and startswith on legacy_erp_outinv_, legacy_erp_ininv_, and legacy_erp_ledger_.
    Make plasticos.transaction._historical_erp_moves return that same set. Do not
    add a compliance post. Add the ORM cases for the three prefixes, legacyXerpXoutinvX123
    posted by _auto_post_pending_invoices, a real prefix left draft, explicit action_post
    refusal, wrong module and model, and a mixed operational and historical set.
  status: completed
- id: T2
  content: After U1 is approved, add one pure commercial quantity function in native_orders.py.
    Nonzero weight stays on SWeight and PWeight, including short tons. Zero weight,
    nonzero amount, and nonzero price becomes positive quantity abs(amount/price)
    and signed unit price amount/quantity. Vendor-bill material lines keep absolute
    quantity and price because the credit is in_refund. A missing price is an anomaly
    with the detail id and the parsed amount, not quantity 1. Before _move, a purchase-total
    payable with any unpriceable line, or with no representable line, creates no bill
    and records one quarantine. The unmatched-payable lump and freight quantity 1
    stay unchanged.
  status: cancelled
- id: T3
  content: Do not project ReverseBatchNo and do not write reversed_entry_id until
    U2 is resolved. account.move.write already refuses that field once the historical
    XMLID exists, and _move writes the XMLID at create. A later credit.write is not
    safe. When U2 names a proved batch reference and a create-time or separately reviewed
    server-side mechanism, accept one original only when the payable id is distinct,
    the original is an in_invoice, the vendor matches, and the reversed batch has
    exactly one payable. Report every other case. Leave both documents unposted drafts.
    A rerun does not rewrite an existing move.
  status: cancelled
isProject: false
built: true
status: built
---

# PLAN: Fix ERP XMLID, quantity, and vendor-credit defects

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `fix_erp_xmlid_quantity_and_vendor_credit_defects_9e29886d.plan.md`
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
| plan_id | `plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| name | Fix ERP XMLID, quantity, and vendor-credit defects |
| overview | Make legacyXerpXoutinvX123 eligible for explicit automatic posting while a real archived ERP invoice stays unposted. Realize a zero-weight nonzero amount as amount divided by price only after the operator approves that rule, and quarantine a purchase-total payable that cannot be represented. Link a vendor credit only when ReverseBatchNo identifies exactly one original payable and the link does not violate the archive write guard. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1, U2; blocking unknowns: U1, U2 |
| is_project | `false` |
| owner | operator |
| created_at | 2026-11-08T21:16:12+00:00 |
| updated_at | 2026-11-08T21:16:12+00:00 |
| depth | `deep` |
| estimate | T1 is one small implementation. T2 and T3 stay blocked. |

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
| captured_at | `2026-11-08T21:16:12+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `Staging` |
| commit_sha | `1b1b35bb2f5ed734e580d3474f516ba6fa8c107f` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make legacyXerpXoutinvX123 eligible for explicit automatic posting while a real archived ERP invoice stays unposted. Realize a zero-weight nonzero amount as amount divided by price only after the operator approves that rule, and quarantine a purchase-total payable that cannot be represented. Link a vendor credit only when ReverseBatchNo identifies exactly one original payable and the link does not violate the archive write guard.

### Scope in

- plasticos.transaction._historical_erp_moves and account.move._historical_source_ids
- worksheet sale, purchase, customer-invoice, and vendor-bill quantity for zero weight
- PayablesBatch.ReverseBatchNo only after restored SQL and a guard-safe link are proved

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves legacyXerpXoutinvX123 is not historical and _auto_post_pending_invoices posts that draft, while legacy_erp_outinv_ stays draft and action_post raises the archived-invoice error. | `quality_gate` | V1: `Odoo TransactionCase plasticos_documents/tests/test_account_move_transaction_link.py` → legacyXerpXoutinvX123 posts from _auto_post_pending_invoices; legacy_erp_outinv_ stays draft and action_post raises the archived-invoice error | `true` |
| SP-02 | V2 proves a representable zero-weight line is on the customer invoice at the source total and an unpriceable purchase-total payable is quarantined with its amount rather than saved as a partial bill. | `quality_gate` | V2: `python -m pytest tests/test_erp_native_orders.py and the worksheet import ORM tests` → representable unit-priced totals match the source amount and every unpriceable purchase-total payable is quarantined | `true` |
| SP-03 | V3 proves a vendor credit receives reversed_entry_id only for one source-proven original payable, and an ordinary write of that field on a marked historical move still fails. | `quality_gate` | V3: `worksheet import ORM reversal tests plus an ordinary historical write` → one proved original is linked at create and a marked historical write of reversed_entry_id still raises | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| source_ref | `plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind IB-Odoo_19; MEMORY_PREFETCH namespace ib-odoo-19 snapshot d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f` | prefetch HIT and conflicts 0 | `true` |
| P1 | pre-validation (status `passed`) | `confirm _historical_erp_moves uses =like without startswith and _historical_source_ids filters startswith after =like` | both methods read in plasticos_transaction | `true` |
| P2 | pre-validation (status `passed`) | `confirm _customer_invoice continues when weight is 0 and account.move.write protects reversed_entry_id` | both sites read | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_transaction/models/transaction.py`, `plasticos_transaction/models/account_move_inherit.py`, `plasticos_transaction/models/native_document_import.py`, `plasticos_transaction/__manifest__.py`, `plasticos_transaction/tests/test_erp_worksheet_import.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_partner_import/erp/mapping_status.py`, `plasticos_partner_import/erp_extracted_data/25_payablesbatch.sql`, `plasticos_partner_import/__manifest__.py`, `plasticos_documents/tests/test_account_move_transaction_link.py`, `tests/test_erp_native_orders.py`, `tests/test_erp_source_layer.py`, `tests/test_erp_mapping_status.py`
- **write_deny:** `tests/production-rehearsal`, `plasticos_security_base`, `.github/workflows`, `Makefile`, `pipeline_v2.py`, `plasticos_partner_import/erp/source_index.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `Odoo TransactionCase plasticos_documents/tests/test_account_move_transaction_link.py`, `python -m pytest tests/test_erp_native_orders.py and the worksheet import ORM tests`, `worksheet import ORM reversal tests plus an ordinary historical write`, `.pre-commit-config.yaml`
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

- compliance does not post
- replay of an existing account.move does not write it
- archive guard still refuses reversed_entry_id
- freight quantity 1 and the unmatched payable lump stay

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/models/account_move_inherit.py plasticos_transaction/models/transaction.py plasticos_documents/tests/test_account_move_transaction_link.py plasticos_transaction/__manifest__.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_partner_import/erp/native_orders.py plasticos_transaction/models/native_document_import.py tests/test_erp_native_orders.py plasticos_transaction/tests/test_erp_worksheet_import.py plasticos_partner_import/__manifest__.py plasticos_transaction/__manifest__.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_partner_import/erp_extracted_data/25_payablesbatch.sql plasticos_partner_import/erp/mapping_status.py plasticos_partner_import/erp/native_orders.py plasticos_transaction/models/native_document_import.py tests/test_erp_source_layer.py tests/test_erp_mapping_status.py tests/test_erp_native_orders.py plasticos_transaction/tests/test_erp_worksheet_import.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `repository root` | `runtime` | `compliance does not post`, `replay of an existing account.move does not write it`, `archive guard still refuses reversed_entry_id`, `freight quantity 1 and the unmatched payable lump stay` | `tests/production-rehearsal`, `plasticos_security_base`, `.github/workflows`, `Makefile`, `pipeline_v2.py`, `plasticos_partner_import/erp/source_index.py` |
| T2 | `repository root` | `data_plane` | `compliance does not post`, `replay of an existing account.move does not write it`, `archive guard still refuses reversed_entry_id`, `freight quantity 1 and the unmatched payable lump stay` | `tests/production-rehearsal`, `plasticos_security_base`, `.github/workflows`, `Makefile`, `pipeline_v2.py`, `plasticos_partner_import/erp/source_index.py` |
| T3 | `repository root` | `data_plane` | `compliance does not post`, `replay of an existing account.move does not write it`, `archive guard still refuses reversed_entry_id`, `freight quantity 1 and the unmatched payable lump stay` | `tests/production-rehearsal`, `plasticos_security_base`, `.github/workflows`, `Makefile`, `pipeline_v2.py`, `plasticos_partner_import/erp/source_index.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| source_execution_ref | `plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (ORM receipt for the lookalike and the real prefix) → do not publish T1; C2 fails (operator rule, SQL census, and invoice and bill totals) → leave T2 unstarted; C3 fails (SQL census, approved pairing, and an ORM proof that an ordinary historical write still fails) → leave T3 unstarted |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | revert the implementation commit; historical drafts stay unposted and no column is dropped |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `Odoo TransactionCase plasticos_documents/tests/test_account_move_transaction_link.py`
- re-run `python -m pytest tests/test_erp_native_orders.py and the worksheet import ORM tests`
- re-run `worksheet import ORM reversal tests plus an ordinary historical write`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 3 todo(s) |
| uncertainty | `high` — 2 unknown(s), 2 blocking |
| blast_radius | `high` — customer invoices, vendor bills, and archived ERP drafts on the import path |
| architectural_boundaries_crossed | `plasticos_transaction historical classifier`, `plasticos_partner_import worksheet quantity` |
| external_systems_touched | `restored SQL Server is read-only evidence for U1 and U2 and is not a code dependency` |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Drop the three =like name clauses from account.move._historical_source_ids. Keep module plasticos_transaction, model account.move, res_id in the recordset, and startswith on legacy_erp_outinv_, legacy_erp_ininv_, and legacy_erp_ledger_. Make plasticos.transaction._historical_erp_moves return that same set. Do not add a compliance post. Add the ORM cases for the three prefixes, legacyXerpXoutinvX123 posted by _auto_post_pending_invoices, a real prefix left draft, explicit action_post refusal, wrong module and model, and a mixed operational and historical set. | Cursor Build agent | `medium` | S | `[]` | `plasticos_transaction/models/account_move_inherit.py`, `plasticos_transaction/models/transaction.py`, `plasticos_documents/tests/test_account_move_transaction_link.py`, `plasticos_transaction/__manifest__.py` |
| T2 | After U1 is approved, add one pure commercial quantity function in native_orders.py. Nonzero weight stays on SWeight and PWeight, including short tons. Zero weight, nonzero amount, and nonzero price becomes positive quantity abs(amount/price) and signed unit price amount/quantity. Vendor-bill material lines keep absolute quantity and price because the credit is in_refund. A missing price is an anomaly with the detail id and the parsed amount, not quantity 1. Before _move, a purchase-total payable with any unpriceable line, or with no representable line, creates no bill and records one quarantine. The unmatched-payable lump and freight quantity 1 stay unchanged. | Cursor Build agent | `high` | M | `[]` | `plasticos_partner_import/erp/native_orders.py`, `plasticos_transaction/models/native_document_import.py`, `tests/test_erp_native_orders.py`, `plasticos_transaction/tests/test_erp_worksheet_import.py`, `plasticos_partner_import/__manifest__.py`, `plasticos_transaction/__manifest__.py` |
| T3 | Do not project ReverseBatchNo and do not write reversed_entry_id until U2 is resolved. account.move.write already refuses that field once the historical XMLID exists, and _move writes the XMLID at create. A later credit.write is not safe. When U2 names a proved batch reference and a create-time or separately reviewed server-side mechanism, accept one original only when the payable id is distinct, the original is an in_invoice, the vendor matches, and the reversed batch has exactly one payable. Report every other case. Leave both documents unposted drafts. A rerun does not rewrite an existing move. | Cursor Build agent | `high` | M | `[]` | `plasticos_partner_import/erp_extracted_data/25_payablesbatch.sql`, `plasticos_partner_import/erp/mapping_status.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_transaction/models/native_document_import.py`, `tests/test_erp_source_layer.py`, `tests/test_erp_mapping_status.py`, `tests/test_erp_native_orders.py`, `plasticos_transaction/tests/test_erp_worksheet_import.py` |

**Critical path:** T1 → T2 → T3

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | one literal XMLID classifier | V1 |
| M2 | representable lines or an honest quarantine | V2 |
| M3 | source-proved vendor credit link that respects the archive guard | V3 |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | ORM receipt for the lookalike and the real prefix | do not publish T1 |
| C2 | M2 | operator rule, SQL census, and invoice and bill totals | leave T2 unstarted |
| C3 | M3 | SQL census, approved pairing, and an ORM proof that an ordinary historical write still fails | leave T3 unstarted |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`
- **Shared causes:** LIKE underscore wildcard; zero weight drops a commercial amount; historical move refuses reversed_entry_id
- **Deletions / consolidations:** one classifier instead of a second =like search; one commercial quantity function instead of a second import path

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | no agent command or module inventory change |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `Odoo TransactionCase plasticos_documents/tests/test_account_move_transaction_link.py` | legacyXerpXoutinvX123 posts from _auto_post_pending_invoices; legacy_erp_outinv_ stays draft and action_post raises the archived-invoice error | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `python -m pytest tests/test_erp_native_orders.py and the worksheet import ORM tests` | representable unit-priced totals match the source amount and every unpriceable purchase-total payable is quarantined | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `worksheet import ORM reversal tests plus an ordinary historical write` | one proved original is linked at create and a marked historical write of reversed_entry_id still raises | `not_run` |
| E-V4 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | hook catalog for the implementation commit; not run by this plan | `not_run` (not_applicable) |

## Stress and disconfirm

### Disconfirming cases

- Does compliance start posting because the classifier changed?
- Does a mixed priced and unpriced purchase-total payable still become a partial bill?
- Does a credit created in this run accept a later reversed_entry_id write?

### Assumption failure conditions

- the frozen 2026-08-07 extract is treated as the live ReverseBatchNo census
- WKSDetail.Units is treated as the quantity

### Blast radius notes

- customer invoices, vendor bills, and archived ERP drafts on the import path

### Rollback constraints

- revert the implementation commit; historical drafts stay unposted and no column is dropped

### Risks

| risk | mitigation |
|------|------------|
| delegating _historical_erp_moves uses the existing sudo search on ir.model.data | keep the existing sudo comment and add no second sudo |
| a partial vendor bill hides a missing amount | quarantine the whole purchase-total payable when any line is unpriceable |
| a deferred reversal link rewrites an archived move | do not implement T3 until a create-time or reviewed mechanism is proved in Odoo 19 |

## Out of scope

- issues 182, 183, 217, and 299
- compliance-triggered auto-post
- WKSDetail.Units reinterpreted as packages or a new Each unit
- amount-opposite pairing and a post-marker write of reversed_entry_id
- production rehearsal kit, security ACLs, workflows, and pipeline_v2.py
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
| source_ref | `plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1` |
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
| `unknown` | U1 | Which zero-weight Amount/Price cases and source units does the operator approve, and what does the live restored SQL census count? — T2 cannot choose a quantity or a unit until this is answered | `block` |
| `unknown` | U2 | What does PayablesBatch.ReverseBatchNo mean on the restored server, and which mechanism can set the link without weakening account.move.write? — T3 cannot project the column or write reversed_entry_id until this is answered | `block` |
| `open_blocker` | stop_reason | T1 is ready. T2 waits on U1. T3 waits on U2. This plan does not implement them. | planning convergence `partial` |

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
  plan_id: "plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1"
  name: "Fix ERP XMLID, quantity, and vendor-credit defects"
  overview: "Make legacyXerpXoutinvX123 eligible for explicit automatic posting while a real archived ERP invoice stays unposted. Realize a zero-weight nonzero amount as amount divided by price only after the operator approves that rule, and quarantine a purchase-total payable that cannot be represented. Link a vendor credit only when ReverseBatchNo identifies exactly one original payable and the link does not violate the archive write guard."
  status: "draft"
  is_project: false
  owner: "operator"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "1b1b35bb2f5ed734e580d3474f516ba6fa8c107f"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make legacyXerpXoutinvX123 eligible for explicit automatic posting while a real archived ERP invoice stays unposted. Realize a zero-weight nonzero amount as amount divided by price only after the operator approves that rule, and quarantine a purchase-total payable that cannot be represented. Link a vendor credit only when ReverseBatchNo identifies exactly one original payable and the link does not violate the archive write guard."
  success_properties:
    - id: "SP-01"
      property: "V1 proves legacyXerpXoutinvX123 is not historical and _auto_post_pending_invoices posts that draft, while legacy_erp_outinv_ stays draft and action_post raises the archived-invoice error."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves a representable zero-weight line is on the customer invoice at the source total and an unpriceable purchase-total payable is quarantined with its amount rather than saved as a partial bill."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves a vendor credit receives reversed_entry_id only for one source-proven original payable, and an ordinary write of that field on a marked historical move still fails."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_transaction/models/transaction.py", "plasticos_transaction/models/account_move_inherit.py", "plasticos_transaction/models/native_document_import.py", "plasticos_transaction/__manifest__.py", "plasticos_transaction/tests/test_erp_worksheet_import.py", "plasticos_partner_import/erp/native_orders.py", "plasticos_partner_import/erp/mapping_status.py", "plasticos_partner_import/erp_extracted_data/25_payablesbatch.sql", "plasticos_partner_import/__manifest__.py", "plasticos_documents/tests/test_account_move_transaction_link.py", "tests/test_erp_native_orders.py", "tests/test_erp_source_layer.py", "tests/test_erp_mapping_status.py"]
    write_deny: ["tests/production-rehearsal", "plasticos_security_base", ".github/workflows", "Makefile", "pipeline_v2.py", "plasticos_partner_import/erp/source_index.py"]
  commands:
    allow: ["Odoo TransactionCase plasticos_documents/tests/test_account_move_transaction_link.py", "python -m pytest tests/test_erp_native_orders.py and the worksheet import ORM tests", "worksheet import ORM reversal tests plus an ordinary historical write", ".pre-commit-config.yaml"]
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
rollback_contract_ref: "rollback.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1"
dependency_topology_ref: "dag.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Does compliance start posting because the classifier changed?", "Does a mixed priced and unpriced purchase-total payable still become a partial bill?", "Does a credit created in this run accept a later reversed_entry_id write?"]
  assumption_failure_conditions: ["the frozen 2026-08-07 extract is treated as the live ReverseBatchNo census", "WKSDetail.Units is treated as the quantity"]
out_of_scope: ["issues 182, 183, 217, and 299", "compliance-triggered auto-post", "WKSDetail.Units reinterpreted as packages or a new Each unit", "amount-opposite pairing and a post-marker write of reversed_entry_id", "production rehearsal kit, security ACLs, workflows, and pipeline_v2.py"]
convergence_contract_ref: "conv.plan.simple.fix_erp_xmlid_quantity_and_vendor_credit_defects.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Drop the three =like name clauses from account.move._historical_source_ids. Keep module plasticos_transaction, model account.move, res_id in the recordset, and startswith on legacy_erp_outinv_, legacy_erp_ininv_, and legacy_erp_ledger_. Make plasticos.transaction._historical_erp_moves return that same set. Do not add a compliance post. Add the ORM cases for the three prefixes, legacyXerpXoutinvX123 posted by _auto_post_pending_invoices, a real prefix left draft, explicit action_post refusal, wrong module and model, and a mixed operational and historical set."
    status: "pending"
  - id: "T2"
    content: "After U1 is approved, add one pure commercial quantity function in native_orders.py. Nonzero weight stays on SWeight and PWeight, including short tons. Zero weight, nonzero amount, and nonzero price becomes positive quantity abs(amount/price) and signed unit price amount/quantity. Vendor-bill material lines keep absolute quantity and price because the credit is in_refund. A missing price is an anomaly with the detail id and the parsed amount, not quantity 1. Before _move, a purchase-total payable with any unpriceable line, or with no representable line, creates no bill and records one quarantine. The unmatched-payable lump and freight quantity 1 stay unchanged."
    status: "pending"
  - id: "T3"
    content: "Do not project ReverseBatchNo and do not write reversed_entry_id until U2 is resolved. account.move.write already refuses that field once the historical XMLID exists, and _move writes the XMLID at create. A later credit.write is not safe. When U2 names a proved batch reference and a create-time or separately reviewed server-side mechanism, accept one original only when the payable id is distinct, the original is an in_invoice, the vendor matches, and the reversed batch has exactly one payable. Report every other case. Leave both documents unposted drafts. A rerun does not rewrite an existing move."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-08T21:27:16Z`
- conversation_id: `6f8996c4-dd59-4da7-b50c-e443b3c7718e`
- generation_id: `ed95a8b0-ceae-4a47-9d30-fba42df9514a`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/6f8996c4-dd59-4da7-b50c-e443b3c7718e/6f8996c4-dd59-4da7-b50c-e443b3c7718e.jsonl`
- todos at build time:
- `T1`: completed
- `T2`: cancelled
- `T3`: cancelled
