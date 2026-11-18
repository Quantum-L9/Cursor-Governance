---
name: Fix load query cluster
overview: Remove all 12 HIGH query-in-loop findings in plasticos_logistics/models/load.py.
  Each call does a fixed number of reads after its locks, not one read per record.
  Create and reconcile keep different candidate sets and different failure behavior.
  Child creates and the documents parent-link override use that same shape. Lane-history
  limits stay per load.
todos:
- id: batch-counts
  content: Replace the two per-load search_count calls with _read_group on self.ids,
    using the Odoo 19 tuple result
  status: completed
- id: batch-stale-rfq
  content: Search stale RFQs once inside _cancel_stale_freight_quote_requests; leave
    the per-load callers in place
  status: completed
- id: batch-ack-activity
  content: Look up today’s urgent acknowledgment activities once before the cron loop
  status: completed
- id: batch-parent-link
  content: Share sale-order locks and the two eligibility reads. Keep create and reconcile
    load sets and raise-versus-skip behavior apart. Batch protection for reconcile,
    unlink, and the parent guard, with documents overriding only the recordset method.
  status: completed
- id: batch-freight-commands
  content: Lock sorted loads, then one existence read and one create for RFQ, estimate,
    actual cost, and correction; keep per-lane history limits
  status: completed
- id: tests-version-baseline
  content: Extend freight and cardinality tests, bump logistics to 19.0.1.14.12 and
    documents to 19.0.2.1.13, and delete only fingerprints the rescan no longer emits
  status: completed
isProject: false
built: true
status: built
---

# Fix all 12 load.py query-in-loop findings

The scanner in [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py) flags an ORM `search`, `search_count`, or `create` whose call sits inside a `for` loop. It does not follow calls into other methods. A helper that still searches once per record would clear the finding and leave the query. That is the patch this plan does not use.

Last run (2026-11-04 17:02 EST) found 12 HIGH hits in [`plasticos_logistics/models/load.py`](plasticos_logistics/models/load.py). Two of those lines are the same statement, so they share one fingerprint. `plasticos.load` stays the owner. Nothing under `plasticos_logistics/business_rules/` changes. The two count fields stay unstored and gain no `@api.depends`.

`_lock_rows` locks `sale_order`, then `plasticos_transaction`, then `plasticos_load`, each in id order. Keep that order. Advisory locks are taken in load-id order. Validation errors are still raised in the incoming recordset order, before the first `create`, so a multi-record call does not change which load fails first.

## Counts, stale RFQs, and the acknowledgment cron

These four have no row lock in front of the query.

- [`_compute_freight_evidence_counts`](plasticos_logistics/models/load.py) lines 600–607 (`12a520cd78523550`, `670a7c33576ad45e`). Use `_read_group`, not deprecated `read_group`. Odoo 19 returns `(group_value, count)` tuples and implements `__count` as `COUNT(*)`. A many2one group is a recordset. An integer group is the integer. `load_id in self.ids` for quote requests. `source_model = plasticos.load` and `source_record_id in self.ids` for estimates (`source_record_id` is an Integer). Skip both calls when `self` is empty. A missing id counts as 0.
- [`_cancel_stale_freight_quote_requests`](plasticos_logistics/models/load.py) lines 1172–1178 (`3348fdeb82d3f957`). One search inside this method. Do not move the callers in `action_resolve_freight` and `_confirm_freight_rate`; each already holds that load’s lock and correlation id. Keep truthy-fingerprint behavior: `None` still cancels every active episode. One `_rfq_write` for the stale recordset, then one event per cancelled request with `load=request.load_id`. Unknown `reason` still raises `KeyError` before the search.
- [`_cron_check_dispatch_acknowledgments`](plasticos_logistics/models/load.py) lines 1487–1505 (`11554bc8c48159c0`). Keep the load search, its order, and `limit=100`. One `mail.activity` search for those ids, then skip ids already present. `activity_schedule` and `action_send_dispatch_direct` stay per load. No sudo.

## Parent linking

[`_reconcile_unlinked_for_transactions`](plasticos_logistics/models/load.py) lines 467 and 470 share fingerprint `8e1992604279258f` because the statement is identical. [`_link_unique_sale_order_transaction`](plasticos_logistics/models/load.py) is the create-time twin. They share the sale-order and transaction locks. They do not share a candidate-load set, a second load search, or a failure mode.

- Create's candidate loads are `self` with no parent. After the transaction re-read it invalidates that recordset. It does not search for other unlinked loads.
- Reconcile's candidate loads are one search: unlinked loads on sale orders whose re-read still shows exactly one eligible transaction, and that transaction is one of the arguments. Any other eligible count skips that sale order. Lock those loads, invalidate them, and run that same unlinked search once more.
- More than one eligible transaction raises on create and skips on reconcile.
- A failed identity, company, or milestone check raises on create through `_require_parent_identity` and `_require_join_milestone`. Reconcile uses `_parent_identity_error` and `_join_milestone_error` and leaves that load unlinked. The skip happens before `write`.
- Assignment stays a `write` of `transaction_id`, grouped by target transaction, so `_guard_transaction_parent` and `_touch_membership_epoch` still run.

Shared sequence, two eligibility searches per call:

1. Lock the sale orders.
2. Search eligible transactions for all of those sale orders.
3. Lock those transactions and search eligibility again.
4. Take the candidate loads from the rule above and lock them.
5. Decide protection once for that candidate recordset, then write the links that pass.

`_eligible_transactions(sale_order)` is not used on these two paths.

`_parent_link_is_protected` is called from reconcile, `unlink`, and `_guard_transaction_parent`. The guard only needs it for loads that already have a parent. [`plasticos_documents/models/load_docs_bridge.py`](plasticos_documents/models/load_docs_bridge.py) overrides the boolean method and adds its own per-id search for an accepted `plasticos.document`. Calling that boolean inside a `for` puts the per-load query back.

- Add `_protected_parent_loads(self)`. Logistics uses in-memory state, provenance, and RFQ rows, plus one `plasticos.dispatch` search when that model is installed.
- Documents overrides only that recordset method: one accepted-document search on `self.ids`, union `super`. Remove the boolean override so it cannot shadow the base method.
- The base boolean method is `self in self._protected_parent_loads()` and is only for a one-record caller such as `action_correct_draft_parent`.
- Reconcile, `unlink`, and `_guard_transaction_parent` call `_protected_parent_loads` once on their candidate recordset, then test membership in the loop.

Bump [`plasticos_documents/__manifest__.py`](plasticos_documents/__manifest__.py) from `19.0.2.1.12` to `19.0.2.1.13` in the same change. Upgrade both modules. Documents already depends on logistics.

## Freight commands

Six findings: RFQ search and create (`6010dcff30531442`, `7e2913d5b6d13f2f`), estimate existence search (`8a3be482baa91c4c`), actual-cost calibration and estimate searches (`7a63f7ea80657cb0`, `e0c5d3363ea22c4a`), and correction prior search (`1f83723fc564052c`).

Each command keeps its current raises, its per-load `new_correlation_id()`, and its advisory lock. Locks run in id order after the checks that already happen before the lock today. The existence read is one search after those locks. One `create(vals_list)` inserts the rows that are still missing.

`action_request_freight_estimate` also calls `recent_executed_lane_evidence` and `recent_comparable_executed_evidence`. Each load keeps its own limit of 20. Do not fold those into one global search. They are not among the 12 findings, and one combined search would change which rows the limit keeps.

The latest calibration row for a load is the first row for that `load_id` after `order by observed_at desc, id desc`.

`create_freight_evidence` stays the authority check. Teach it to take the pairs for one command, check every load, set each row’s company, and call `sudo().create` once. A single-row caller uses that same path with one pair. The sudo reason stays the read-only evidence ACL. Chatter `message_post` stays per load.

The child `create` methods that would otherwise repeat the existence search:

- [`plasticos_logistics/models/freight_quote.py`](plasticos_logistics/models/freight_quote.py) line 135 (`7d0c8ee14ccd9631`). One search of the idempotency keys in `vals_list`.
- [`plasticos_logistics/models/freight_estimate.py`](plasticos_logistics/models/freight_estimate.py) line 83 (`c425b97d30baa725`). One search, then a set of `(source_model, source_record_id, context_fingerprint, request_fingerprint)`. That is the same identity as the unique constraint.
- [`plasticos_logistics/models/freight_governance.py`](plasticos_logistics/models/freight_governance.py) line 121 (`afd796ea4ef03bdb`). One search of the load ids whose rows have no `supersedes_observation_id`. A correction that names a prior observation skips that check, as it does today.

[`freight_quote.py`](plasticos_logistics/models/freight_quote.py) line 629 (`9a67c59761b586aa`) stays out of this change.

## Tests, version, baseline

Bump logistics from `19.0.1.14.11` to `19.0.1.14.12` and documents from `19.0.2.1.12` to `19.0.2.1.13`. No migration. Run `ruff format` on both manifests.

- Counts, cancel, cron, and command tests go in [`plasticos_logistics/tests/test_linda_freight_models.py`](plasticos_logistics/tests/test_linda_freight_models.py), using `_new_load` and `_new_request`. Request counts are 1 and 0, because a second request for the same load and fingerprint is refused. Two estimates with different `request_fingerprint` values and `status="insufficient_evidence"` count as 2. An estimate with another `source_model` counts as 0. Cancel on two loads keeps today’s fingerprint and `exclude_request_ids` rules, and a request outside `self` stays draft. The cron reaches `dispatched` through `_confirm_freight_rate`, `action_schedule`, and `action_dispatch`. Assert only the two test loads. Do not assert a global activity count or a successful resend. Two new loads create two command rows and keep two correlation ids. A repeated key creates nothing. A second initial actual-cost call still raises. A correction with `supersedes_observation_id` is not rejected by the initial-row check. The existing single-load cancel tests stay.
- Parent linking keeps the outcomes in [`plasticos_logistics/tests/test_load_cardinality.py`](plasticos_logistics/tests/test_load_cardinality.py), including the concurrent cases. Add one reconcile of two sale orders under the one-eligible-transaction rule, and one create of a load that does not link some other unlinked load on a different sale order. A create with two eligible transactions still raises. A reconcile whose identity or milestone check fails still leaves that load unlinked. An accepted document still protects the parent when `plasticos_documents` is installed, and unlink of that load still raises.

After the rescan, delete a baseline entry only when its fingerprint is absent. The cleared set is the fingerprints named above. Do not delete `9a67c59761b586aa`. A new HIGH row is fixed in code. It is not added to the baseline.

## Proof

`make audit-baseline` prints `New: 0`. The fresh report has no HIGH `N_PLUS_ONE_QUERY` row for `plasticos_logistics/models/load.py`. `make test-module m=plasticos_logistics,plasticos_documents` runs on the fixture in [`config/test_env_fixture.conf`](config/test_env_fixture.conf).

Out of scope: the other modules in the 74, the quote-supersede search, lane-history limit changes, and any freight decision or send behavior.

## Build evidence (auto)

- detected_at: `2026-11-04T22:32:33Z`
- conversation_id: `3af0959d-6684-4755-823d-5f85acbd0c39`
- generation_id: `e1655f07-d3bb-49ce-8928-7dabc2ab34f2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/3af0959d-6684-4755-823d-5f85acbd0c39/3af0959d-6684-4755-823d-5f85acbd0c39.jsonl`
- todos at build time:
- `batch-counts`: completed
- `batch-stale-rfq`: completed
- `batch-ack-activity`: completed
- `batch-parent-link`: completed
- `batch-freight-commands`: completed
- `tests-version-baseline`: completed
