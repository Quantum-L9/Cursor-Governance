---
name: Batch documents loop queries
overview: Batch the three live loop queries and the scale-ticket activity check the
  scanner cannot see. The previous built stamp is withdrawn. This workspace has
  not landed the change.
todos:
  - id: batch-sale-order
    content: Replace the per-document sale.order search in _get_related_transactions
      with one grouped search. Leave conflict routing in the existing loop.
    status: pending
  - id: extract-missing-doc-page
    content: Move the missing-docs loop into _apply_missing_doc_page, hoist the rule
      read, prefetch today's escalation activities once, inherit mail.activity.mixin
      on that same class, and keep the cron as the only caller inside the lock.
    status: pending
  - id: batch-scale-ticket
    content: Prefetch scale-ticket escalation activities once per aimed page and remove
      search_count from _record_scale_ticket_escalation without changing the flag write.
    status: pending
  - id: tests-baseline-version
    content: Import a TransactionCase that fails when the new paths are bypassed, bump
      plasticos_documents to 19.0.2.1.13, and delete the six baseline rows only after
      the scanner is clean.
    status: pending
isProject: false
---

# Batch the documents loop queries

Implementation has not landed. Inspected at `afb2f78a` on `feat/native-opportunity-matching`. [`plasticos_documents/__manifest__.py`](plasticos_documents/__manifest__.py) is still `19.0.2.1.12`. [`plasticos_documents/models/document.py`](plasticos_documents/models/document.py) line 511 still searches inside the record loop. [`plasticos_documents/models/transaction_docs.py`](plasticos_documents/models/transaction_docs.py) lines 155 and 188 still query inside `for tx`. `_apply_missing_doc_page` does not exist. A prior `built` stamp on this file is not evidence.

Do this work on a new branch from `Staging`. Do not commit it on `feat/native-opportunity-matching`.

The allowlist cluster of three per file is not three live defects per file. [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py) flags `search` and `search_count` only when the call's own function body contains the loop. It does not follow a call into another method.

Live, still inside a loop:

- [`plasticos_documents/models/transaction_docs.py`](plasticos_documents/models/transaction_docs.py) line 155, `plasticos.document.rule` `.search()` inside `for tx in transactions` in `cron_check_missing_docs`. Fingerprint `e35b8df6a7b1d579`.
- Same method, line 188, `mail.activity` `.search_count()` per escalated transaction. Fingerprint `37c6d7c3281a4d46`.
- [`plasticos_documents/models/document.py`](plasticos_documents/models/document.py) line 511, `plasticos.transaction` `.search()` per `sale.order` document inside `_get_related_transactions`. Fingerprint `c45c2c4ad7188980`.

Stale allowlist rows, still present in [`ci/baselines/extended_audit_baseline.json`](ci/baselines/extended_audit_baseline.json):

- `document.py` `7803590a5a8f5fa2` and `acaac85f56e67706`. Those searches are gone. Do not invent replacements.
- `transaction_docs.py` `ff6bb4221892a030`. The `.search_count()` now lives in `_record_scale_ticket_escalation` (line 325), which has no loop. `cron_check_scale_tickets` still calls it once per load (line 450). The scanner cannot see that. Fix the helper. A clean scanner does not prove that fix.

No new model, field, or scanner exception. `recordset.grouped()` exists on this Odoo 19 (`odoo/orm/models.py`). A field-name key is the field value. For `sale_order_id` that value is a `sale.order` recordset, empty when unset, not an integer.

## Repairs already required by the current source

- The missing-docs cron loads at most 300 active transactions, oldest `create_date` first. A new row is not in that page on a populated fixture. Test `_apply_missing_doc_page` with an explicit recordset. Prove the cron calls it with a separate patch.
- `_count_business_days` is a `@staticmethod`. Patch the model class with a callable `(start_date, end_date)`, not `self`.
- `get_missing_documents` is `plasticos.compliance.service.get_missing_documents(self, res_model, res_id, purpose=None)` in [`plasticos_documents/models/compliance_service.py`](plasticos_documents/models/compliance_service.py). `_compute_missing_doc_flags` calls that. Patch that method. A patch on the transaction does not run.
- `_compute_missing_doc_flags` keeps a code only when it is also in an active supplier, carrier, or buyer matrix tag set. A patch that returns an arbitrary code leaves `has_missing` false and never reaches the activity branch.
- The scale-ticket cron wraps a short page back to cursor 0. Aim the cursor at `min(new load ids) - 1` and clear `plasticos_documents.scale_ticket_retry_ids` before each run. Older delivered loads then stay outside the page.
- Seed rule `rule_scale_ticket_carrier` escalates after 7 business days from pickup ([`plasticos_documents/data/scale_ticket_rule.xml`](plasticos_documents/data/scale_ticket_rule.xml)). The 30-day `dispatched_at` in [`plasticos_documents/tests/test_scale_ticket_cardinality.py`](plasticos_documents/tests/test_scale_ticket_cardinality.py) meets that. Do not invent a higher threshold.
- `plasticos.transaction` has `unique(name)`. Every transaction in the new test gets its own name. The default `"New"` collides.
- A sale order is left unconfirmed. `action_confirm` creates another transaction.
- Two transactions may share one `sale_order_id`. [`plasticos_documents/tests/test_pr322_findings.py`](plasticos_documents/tests/test_pr322_findings.py) already does that. Do not `skipTest` if that create fails.
- A load on that shared order is not legal when both transactions have a supplier and a buyer. [`plasticos_logistics/models/load.py`](plasticos_logistics/models/load.py) `_link_unique_sale_order_transaction` raises `ValidationError` and rolls the create back. The two-transaction order gets no load. The conflict load is created only on the single-transaction order, so its parent is that one transaction.
- There is no savepoint in `cron_check_missing_docs`. The savepoint is only in `cron_check_scale_tickets`, inside `for load in loads`.
- `plasticos.document` create requires `name`, `res_model`, `res_id`, `tag_id`, and `attachment_id`.
- The missing-docs domain compares `date_deadline` to `date.today()` (line 134). `activity_schedule` with no deadline stores `fields.Date.context_today`. This change keeps `date.today()`. It does not switch clocks. If those two dates differ in the fixture, stop and report that. Do not drop the date filter to make the second call pass.

## `document.py` — one sale-order search

Keep `_association_conflict_reason`, `_route_association_conflict`, the direct `transaction_id` and `plasticos.transaction` collection, the load `browse().exists()` path, and the `load_id.transaction_id` path inside the existing loop. Keep the final `browse(list(tx_ids))` when `tx_ids` is non-empty, and the empty `tx_model` return when it is empty. [`plasticos_claims/tests/test_constraints_onchanges.py`](plasticos_claims/tests/test_constraints_onchanges.py) asserts the conflict record's result is falsy.

If any record has `res_model == "sale.order"`, search once before that loop:

```python
tx_model.search([("sale_order_id", "in", sale_order_ids)])
```

`sale_order_id` is an identity field, so this domain is a proven bound. Skip the search when that id set is empty. Include every such `res_id`, including `0` and rows that later `continue` because of a conflict. Group with `grouped("sale_order_id")`. Convert each key with `order.id` (`False` when the order is empty) before lookup. Do not look up an integer against the recordset key. A missing key, including `res_id == 0`, adds no transaction. In the `sale.order` branch, add a transaction id only when that group has length 1.

## `transaction_docs.py` — missing-docs page

`PlasticosTransactionDocs` keeps `_name` unset and changes `_inherit` from the string `"plasticos.transaction"` to `["plasticos.transaction", "mail.activity.mixin"]`. `activity_schedule` lives on that mixin ([`odoo/addons/mail/models/mail_activity_mixin.py`](odoo/addons/mail/models/mail_activity_mixin.py)). `plasticos.transaction` inherits only `mail.thread`, and `plasticos.load` already has the mixin. The missing-docs cron and [`plasticos_transaction/models/transaction.py`](plasticos_transaction/models/transaction.py) `_escalate_supplier_confirmation` already call `activity_schedule`. Without the mixin the new proof raises `AttributeError`. Do not add a chatter widget or a view. The mixin fields in this Odoo 19 are computed or a One2many, so this adds no table column and no `migrations/` script. `mail` is already in the documents manifest. Do not also edit `plasticos_transaction` to add the same mixin.

`cron_check_missing_docs` keeps the advisory lock, the `search(..., limit=300)`, and the `finally` unlock. Inside the `try`, after that search, it calls `_apply_missing_doc_page(transactions)` and does not keep a `for tx` loop or either of the two queries.

`_apply_missing_doc_page` returns immediately on an empty recordset and does not search. Otherwise, before its loop:

- Search `plasticos.document.rule` once for `res_model = plasticos.transaction` and `active = True`, ordered `id ASC`. Compute `overdue_threshold` and `escalation_threshold` once. Defaults stay 2 and 5. Keep the `hasattr` checks and the falsy-zero skip. Do not add `limit`. The result is the full active set, because `min()` must see every truthy threshold. A limit of 1 would change the status. A MODERATE unbounded-search note on this one search is accepted. It is not a HIGH finding and it is not a new baseline row.
- Search `mail.activity` once for `res_model = plasticos.transaction`, `res_id in` the page, `date_deadline =` the same `date.today()` the cron already uses, and `summary in` the exact `ESCALATION: Missing documents on {tx.name}` strings. Remember `(res_id, summary)` pairs. `res_id in` the page ids is the bound.

The loop tests membership instead of `search_count`. Status is still written before the activity check. An existing today's activity still `continue`s, which skips the log line and does not schedule. Do not add to the pair set after `activity_schedule`. Each transaction is visited once. A same-day activity with a different summary still does not count. The overdue branch still posts the reminder, still `continue`s, and does not schedule this activity.

## `transaction_docs.py` — scale-ticket escalation

The only caller of `_record_scale_ticket_escalation` is line 450. The load page is already deduped by id. After the early returns (no loads, missing SCALE tag), and before `for load in loads`, search `mail.activity` once for `res_model = plasticos.load`, `res_id in` the deduped page, and `summary in` the exact `ESCALATION: Missing scale ticket on {load.name}` strings. That search is outside every `savepoint()`. Pass that snapshot as a new last argument, a `set` of `(res_id, summary)` pairs. Update the only call in the same edit. The helper does not search.

The helper schedules only when `(load.id, summary)` is absent. It still calls `_write_scale_ticket_status({"scale_ticket_escalated": True})` when the activity is already there, which is what line 340 does today. Do not add a `date_deadline` filter. Do not update the snapshot after scheduling. A savepoint rollback of one load does not change another load's key. The next cron run searches again.

Leave `_load_has_current_scale_ticket` alone. Leave the per-transaction `get_missing_documents` call inside `_compute_missing_doc_flags` alone. Neither is one of these six rows.

## Allowlist and version

Bump [`plasticos_documents/__manifest__.py`](plasticos_documents/__manifest__.py) from `19.0.2.1.12` to `19.0.2.1.13`. No `migrations/` directory: the mixin adds no stored column. Run `ruff format` on the manifest.

After the scanner reports zero hits in both files, delete all six entries for these two files. The fingerprints are `7803590a5a8f5fa2`, `acaac85f56e67706`, `c45c2c4ad7188980`, `e35b8df6a7b1d579`, `37c6d7c3281a4d46`, and `ff6bb4221892a030`. Deleting a live fingerprint before the scanner is clean fails the HIGH gate. Do not edit [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py).

## Proof

Add [`plasticos_documents/tests/test_document_query_batch.py`](plasticos_documents/tests/test_document_query_batch.py) and import it from [`plasticos_documents/tests/__init__.py`](plasticos_documents/tests/__init__.py). Odoo loads only modules imported there. Use `TransactionCase`, tagged `post_install` and `-at_install`, matching [`plasticos_documents/tests/test_scale_ticket_cardinality.py`](plasticos_documents/tests/test_scale_ticket_cardinality.py).

Runtime, and able to fail if the new path is bypassed:

- `_get_related_transactions` on one mixed recordset. Create a buyer (`customer_rank` > 0) and a supplier (`is_company`, `supplier_rank` > 0). Each sale order is `sale.order` create with that buyer as `partner_id`, and it is not confirmed. Each transaction sets `supplier_id`, `buyer_id`, `sale_order_id`, and a distinct `name`. One unconfirmed order has one transaction. Another has two. Do not create a load on the order that has two. The conflict load is `plasticos.load` create with only the single-transaction order's `sale_order_id`, so `_link_unique_sale_order_transaction` sets its parent to that transaction. Each document has `name`, `tag_id`, `attachment_id`, `res_model`, and `res_id`. The attachment is an `ir.attachment` with `name`, `datas`, `res_model = plasticos.document`, and `res_id = 0`, the same shape as the claims test. The two `sale.order` documents have empty `transaction_id` and empty `load_id`, and `res_id` is that order's id. One order has one transaction and that transaction is included. One order has two transactions and neither is included. The third document uses the claims conflict shape: `res_model = plasticos.load`, `res_id` and `load_id` are the single-order load, and `transaction_id` is a transaction from the other order. Create already calls `_get_related_transactions`, so the conflict marker may already be on the document before the explicit call. The explicit call still returns no transaction for that document, and its messages contain `Conflicting association withheld from evidence.`
- `_apply_missing_doc_page` on two transactions the test creates, with distinct names, supplier, and buyer. They do not need `state = active`, because this call does not go through the cron search. Create a new `plasticos.document.tag` with `name` and a unique `code`, and an active `plasticos.document.validation.matrix` row with `name`, `doc_category = supplier`, and that tag. Patch `plasticos.compliance.service.get_missing_documents` with a callable `(self, res_model, res_id, purpose=None)` that returns `[tag.code]`. Patch `_count_business_days` on the transaction model class with `(start_date, end_date)` returning `2`. Create one `plasticos.document.rule` with `name`, that new `tag_id`, `res_model = plasticos.transaction`, `client_id` empty, and both day fields set to `1`, so `unique(tag_id, res_model, client_id)` does not collide with a seed rule and `min()` of the escalation field cannot stay above 1. Before the call, `activity_schedule("mail.mail_activity_data_todo", date_deadline=date.today(), ...)` on one transaction with the exact summary `ESCALATION: Missing documents on {tx.name}`. After the call that transaction has one such activity and the sibling has one. A second call stays at one each.
- Wiring: patch `_apply_missing_doc_page` to record its calls, call `cron_check_missing_docs`, and assert it was called once. This does not prove page membership. It proves the cron no longer owns the loop.
- `cron_check_scale_tickets` on two loads built in this test, not by calling the cardinality test's method. Repeat its sequence: unconfirmed sale order, one transaction with supplier, buyer, `sale_order_id`, and a distinct name, then a draft load with that `sale_order_id`. Set the transaction to `delivered` with `bypass_state_guard=True`. Then write the load with `state = delivered`, `delivered_at`, and `dispatched_at` 30 days ago, using `_FREIGHT_INTERNAL_WRITE` and `_FREIGHT_INTERNAL_WRITE_TOKEN` imported from `odoo.addons.plasticos_logistics.models.load`. The 30-day delivery also sends the reminder. That reminder is not the assertion. Ensure the SCALE tag exists the same way the cardinality test does: search `code = SCALE`, and create `name` and `code` only when that search is empty. Clear the retry parameter and set the scan cursor to the first new load id minus 1 before each run. Set `scale_ticket_batch_size` to the number of loads this test creates. Resolve `plasticos_security_base.group_logistics` and fail if that xmlid is missing. If no active user has that group, `self.env.user.write({"group_ids": [fields.Command.link(group.id)]})`. On one load, schedule the exact summary `ESCALATION: Missing scale ticket on {load.name}` and leave `scale_ticket_escalated` false, so `due_escalation` still enters the helper. Neither load has a current scale ticket. After the first run that load still has one activity and `scale_ticket_escalated` is true; the other load has one activity and the flag is true. Reset the cursor and the retry parameter, run again, and both activity counts stay at one.

Structural, not runtime:

- The performance scanner reports zero `N_PLUS_ONE_QUERY` hits in these two files.
- An AST walk of `_record_scale_ticket_escalation` finds no `search` or `search_count` call. A substring check is not the proof.
- `scripts/audit/check_baseline.py` against the extended baseline, severities HIGH, reports no new HIGH finding for these files.
- `ruff check` and `ruff format` on the edited Python, including [`plasticos_documents/__manifest__.py`](plasticos_documents/__manifest__.py).

Regression nets, because the load and conflict paths stay in the loop and `make test-module` accepts one module: `make test-module m=plasticos_documents`, then `m=plasticos_documents_native`, then `m=plasticos_claims`. Those commands clone only the database named in [`config/test_env_fixture.conf`](config/test_env_fixture.conf). The native parent-load test and the claims conflict assertion are the callers. They do not prove the sale-order batch.

Upgrade only this module with `make update m=plasticos_documents`.

## Left out on purpose

`_load_has_current_scale_ticket` still searches documents once per load, and `_compute_missing_doc_flags` still calls `get_missing_documents` once per transaction. Those reads stay. This change does not claim to remove them.

## Alignment record

The previous frontmatter said every todo was completed. The source above contradicts that, so those statuses are pending again. Corrections applied to this contract:

- Branch boundary is `Staging`, not the current feature branch.
- `grouped("sale_order_id")` keys are recordsets. Lookup uses `order.id`.
- The rule search stays unlimited because `min()` reads the whole active set. MODERATE is not a HIGH baseline row.
- The activity prefetch uses the cron's `date.today()`. The deadline clock is not changed.
- The scale-ticket prefetch is outside the per-load savepoint. The helper gains the snapshot argument at its only caller.
- The missing-docs test patches `plasticos.compliance.service.get_missing_documents` with the real signature, and the business-day patch is a two-argument staticmethod.
- Documents in the new test include the required `attachment_id`. The conflict document uses `res_model = plasticos.load`, the same reason the claims test already asserts.
- The six baseline rows are deleted only after both files are clear of scanner hits.

## Gaps filled

Checked against the current source. These were holes in the contract, not new behavior:

- `activity_schedule` is not on `plasticos.transaction`. The documents class this plan already edits inherits `mail.activity.mixin`. No second module and no stored column.
- A second transaction on one sale order is legal. A load on that order is refused when both transactions have a supplier and a buyer. The conflict load uses the single-transaction order only.
- Sale orders stay unconfirmed. Transaction names are unique. Matrix rows need `name`. Tags need `name` and `code`. Group membership uses `fields.Command.link`.
- The scale-ticket loads are created in this test with the freight-write token. They do not call another test class.
- Create already recomputes related transactions, so the conflict assertion is the return value and the marker, not a second post.
