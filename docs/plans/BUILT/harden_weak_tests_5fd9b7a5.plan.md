---
name: Harden weak tests
overview: Each flagged test must fail if the production function is a no-op or writes
  the wrong thing. Cron names come from ir.cron XML. Helpers, seed rewrites, global
  counts, and writes the search limit cannot reach do not count.
todos:
- id: pure-asserts
  content: Positive validator tests must fail if the function returns its input or
    returns None without enforcing a rule
  status: completed
- id: cron-binding
  content: One Odoo-free registry, bidirectionally locked to cron XML code fields;
    drop methods no cron calls
  status: completed
- id: cron-effects
  content: Delete the swallow helpers. One in-domain and one out-of-domain assert
    per live cron, or fail closed when the batch cannot reach the row
  status: completed
- id: prove-scanner
  content: These two cron files and the four pure files show zero assertion-free tests;
    pytest runs the pure lock
  status: completed
isProject: false
built: true
status: built
---

# Harden the 27 tests to the live contract

Architecture is settled. Test-contract repair only: no new model, no cron rewrite, no scanner change, no `plasticos_base` edit, no addon test loader, no module version bump.

A test is aligned only when a no-op implementation fails it. Asserting a fixture key that was true before the call does not count. [`ci/weak_test_fixer.py`](ci/weak_test_fixer.py) only sees the test function. [`tests/test_weak_test_authority.py`](tests/test_weak_test_authority.py) rejects helper calls. Do not rename `_run_twice` or `_run_cron_safely`. Delete them. They turn exceptions into skip or a string and hide the traceback.

## Validators CI already runs

`validate_supply_payload` and `validate_buyer_demand_payload` return `None` and do not change the payload. Asserting [`SUPPLY_REQUIRED`](scripts/opportunity_protocol.py) on the input is true even if the function body is `return`. In [`tests/test_opportunity_protocol_split.py`](tests/test_opportunity_protocol_split.py) and in [`tests/test_semantic_gate_payloads.py`](tests/test_semantic_gate_payloads.py) `test_example_fixtures_still_valid`, the same test function must do both: the example call returns `None`, and a copy that breaks one rule that function enforces raises `OpportunityProtocolError` (supply: set `quantity.target` below `quantity.minimum`; demand: set `need_window.start_at` after `need_window.end_at`). Leave the existing negative tests in place.

[`tests/test_projection_outcome_schemas.py`](tests/test_projection_outcome_schemas.py) asserts the normalized dict, and asserts the function did not return the input unchanged:

- canonical result has `entity_ref == "plasticos.material.specification:9"`, `entity_type == "material_specification"`, `revision == 3`, `tombstone is False`, and has no `properties` or `contract_version`
- sync upsert result has `records[0].operation == "upsert"`, `entity_ref == "res.partner:102"`, `revision == 8`, and has no `contract_version`
- tombstone result has `records[0].operation == "tombstone"` and `revision == 9`
- outcome result has `outcomes[0].outcome_type == "accepted"`, `idempotency_key == "match-501-accepted-20260802"`, `match_result_ref == "plasticos.match.result:501"`, and has no `contract_version`

[`tests/test_gate_sdk_invocation.py`](tests/test_gate_sdk_invocation.py) `test_sdk_validates_the_adapter_packet_as_gate_bound` calls `validate_outbound_gate_packet` on the packet `_send` returned and asserts that same object's `address.destination_node == "gate"`. Do not copy `reply_to` from the sibling test.

## One cron binding

Put the registry in a module that does not import Odoo, so pytest can import it. Both cron files import that module. The pure lock test parses `model.<method>()` out of each listed cron XML `code` field. For each registry row, the XML id suffix after `model_` must equal `model.replace(".", "_")`, and the code method must equal the registry method. A call in either cron file to a method that is not in the registry fails the lock. The lock does not have to name every cron in the repo.

Drop a row when no cron `code` field calls it. A search of tracked cron XML found no `cron_run_enrichment`, `action_cron_enrich_pending`, or `action_cron_inference_only`. `plasticos_enrichment` is editor-ignored, so implementation reads that module's XML on disk. If those methods are still absent, delete the enrichment cases. Do not invent a cron and do not touch `pipeline_v2.py`.

Replace the stale names. Do not keep both the old name and the live name:

- claims → `plasticos.claim._cron_check_sla` ([`plasticos_claims/data/claim_cron.xml`](plasticos_claims/data/claim_cron.xml))
- logistics escalation → `plasticos.load._cron_escalation_check` ([`plasticos_logistics/data/cron.xml`](plasticos_logistics/data/cron.xml))
- monthly audit → `plasticos.audit.cron.run_monthly_audit` ([`plasticos_transaction/data/audit_cron.xml`](plasticos_transaction/data/audit_cron.xml))
- scale tickets → `plasticos.transaction.cron_check_scale_tickets` ([`plasticos_documents/data/scale_ticket_rule.xml`](plasticos_documents/data/scale_ticket_rule.xml))
- missing docs → `plasticos.transaction.cron_check_missing_docs` ([`plasticos_documents/data/cron_missing_docs.xml`](plasticos_documents/data/cron_missing_docs.xml))
- contract renewal → `res.partner.cron_contract_renewal_alert` ([`plasticos_automation/data/contract_renewal_cron.xml`](plasticos_automation/data/contract_renewal_cron.xml))
- sale approval → `sale.order.cron_flag_sale_approvals` ([`plasticos_automation/data/sale_approval_cron.xml`](plasticos_automation/data/sale_approval_cron.xml))
- stock reorder → `product.product.cron_stock_reorder_alert` ([`plasticos_automation/data/stock_alert_cron.xml`](plasticos_automation/data/stock_alert_cron.xml))

These already match: `plasticos.midnight.recompute._cron_midnight_recompute`, `plasticos.intake.cron_batch_normalize`, `res.partner.cron_geo_backfill`, `plasticos.offer.cron_expire_offers`, `account.move.cron_invoice_reminder`, `plasticos.load.cron_load_sla_check`.

One pair of tests per live method, not the old 13 plus 7 names. Claims, audit, geo, and missing docs are each one method. An old test name is removed or given an in-body assert. `skipTest` for a missing model or method is removed. An exception fails with its traceback.

These Odoo files stay unloaded: [`tests/conftest.py`](tests/conftest.py) ignores them without Odoo, and no addon imports them. Do not add a loader. [`tests/integration/test_offer_state_machine.py`](tests/integration/test_offer_state_machine.py) `TestOfferCronExpiry` already expires one offer and may keep its `skipTest`; this change does not edit it. The flagged offer tests still need their own asserts.

## What a cron assert may say

Create only records this test owns. Never `search().write()` seed rows. The current `test_expire_offers_empty_db` write of `valid_until` on every draft offer is that bug. Delete it.

Do not assert a table-wide count. Other rows already exist. Assert the fields on the records this test created.

`pg_try_advisory_lock` is session-scoped. The cron releases it in `finally` on the success path. Do not mock the lock. If the write did not happen, the test fails. `return` of `None` is not success: the lock-held path also returns `None`.

Several crons `search(..., limit=200|300|500)`. A new row is inside that batch only when it sorts first. Set the field in the `order` so this row is first (`valid_until`, `invoice_date_due`, `contract_end_date`, `opened_at`, `entered_state_at`). `create_date` and `id ASC` cannot be aimed that way through a normal `create`. Sale approval and stock reorder order by `id ASC`. If `search_count(domain) >= limit` before the call, fail with that count. Do not skip, and do not assert a write the batch cannot reach.

Copy the `create` dict from an existing test of that model when one exists. The offer dict is `intake_id`, `supplier_id`, `buyer_id`, `valid_until`, `state` in `TestOfferCronExpiry`. Do not invent a second offer stack.

Per method:

- Offer expire. Copy that create dict. One `sent` or `draft` offer with `valid_until` yesterday becomes `expired` after the call and stays `expired` after the second call. A second offer with `valid_until` tomorrow stays `draft`. `invalidate_recordset()` before each state read.
- Sale approval. One draft whose `amount_total` is over `sale_approval_threshold` and whose `requires_approval` is False gets `requires_approval` True and one `approval_flag` log on that `res_id`. The second call adds no second log. A draft at or under the threshold stays `requires_approval` False. If the over-threshold domain is already at 500, fail closed.
- Invoice reminder. One posted unpaid `out_invoice` with `invoice_date_due` before today minus `invoice_overdue_days` gets `last_reminder_date` today and one `invoice_reminder` log. The second call adds no log. An invoice due in the future gets no log.
- Contract renewal. One partner with `contract_end_date` inside `contract_alert_days_before` gets one `contract_alert` log. The second call the same day adds no log. A partner with `contract_end_date` False gets no log.
- Stock reorder. One `consu` product with `qty_available` below `min_stock_threshold` gets one `stock_alert` log. The second call the same day adds no log. A product at or above the threshold gets no log. If the `type in (product, consu)` domain is already at 500, fail closed.
- Claim SLA. One `pending` claim whose `opened_at + sla_hours` is in the past is escalated by the first call. The second call does not add a second mail activity with summary `Open Claim Reminder: {name}` and `date_deadline` today. A `resolved` claim stays `resolved`.
- Intake batch. The domain is `normalized` False and `match_status` `pending`, ordered by `create_date`. An intake this test creates that is already `normalized` True stays `normalized` True with the same `match_status` across two calls. That out-of-domain assert does not depend on the batch limit. The in-domain error transition (`match_status` `error`, `normalized` stays False, second call leaves `normalization_errors` unchanged) is required only when this row can be first. If `create_date` cannot be set and the pending count is already at `batch_limit`, fail closed. Do not claim the error transition happened.
- Load SLA. States in `_SLA_HOURS` are `awaiting_ready`, `ready_confirmed`, `rate_confirmed`, `scheduled`, `dispatched`. One load in one of those states with `entered_state_at` older than that state's hour limit gets `sla_breached` True. The second call does not create a second log for the same `escalation_level`. A load in a state outside that map stays `sla_breached` False.
- Missing docs. Domain is `state == active`. A transaction this test creates with any other `state` keeps `missing_doc_status` across two calls.
- Scale tickets. Domain is `state in (delivered, closed, invoiced)` and `load_id` set. A transaction outside that state, or with no `load_id`, keeps `scale_ticket_escalated` False across two calls.
- Geo backfill. Domain needs `partner_latitude` in `(0.0, False)` and a street or city. A partner with no street and no city keeps `partner_latitude` across two calls. Do not create an addressed partner. That path calls Nominatim.
- Midnight recompute. `_recompute_document_expiry` and `_recompute_claim_time_fields` on the base model are empty. Two calls leave a document and a claim this test created unchanged. Do not assert expiry.
- Logistics escalation. `_cron_escalation_check` only calls `check_escalations`. A load this test creates keeps its `state` across two calls. Do not assert an escalation the test did not set up.
- Monthly audit. `run_monthly_audit` only logs. A closed transaction this test creates keeps `state` and `gross_margin` across two calls. Do not assert a mail or a write.

## Out of scope

- [`ci/weak_test_fixer.py`](ci/weak_test_fixer.py) and the extended-audit baseline.
- The separate helper warning in `test_suite_structure.py`.
- Production cron bodies, manifests, ACL, and `pipeline_v2.py`.
- Editing `TestOfferCronExpiry`.
- An addon import that would put these files on `--test-enable`.

## Proof

- `python3 ci/weak_test_fixer.py` reports zero assertion-free tests in the two cron files and the four validator/SDK files. Old names are either gone or no longer flagged.
- `python3 -m pytest` on those four modules, the cron-XML lock, and `tests/test_weak_test_authority.py`.
- `ruff check` and `ruff format` on the edited test files.
- Do not claim a Docker cron run. The behavioral files are still not on the addon roster. The XML lock is what CI runs. The field asserts are the contract those files enforce when Odoo loads them.

## Build evidence (auto)

- detected_at: `2026-10-29T01:39:42Z`
- conversation_id: `07d954b9-d92d-4df5-a528-abd67ec58f69`
- generation_id: `5960d927-6315-4c84-afc0-2db1b4f81102`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/07d954b9-d92d-4df5-a528-abd67ec58f69/07d954b9-d92d-4df5-a528-abd67ec58f69.jsonl`
- todos at build time:
- `pure-asserts`: completed
- `cron-binding`: completed
- `cron-effects`: completed
- `prove-scanner`: completed
