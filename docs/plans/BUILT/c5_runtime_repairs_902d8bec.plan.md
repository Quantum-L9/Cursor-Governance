---
name: C5 runtime repairs
overview: Repair the runtime failures at the one place each contract is decided, on
  the open pull request that already owns that file. The booking-source check is doing
  its job and stays. Nothing is merged.
todos:
- id: schedule-lane
  content: 'Add the schedule lane to the Linda sweep cursor on #536, and stop queuing
    a Linda mail with no address.'
  status: completed
- id: facility-defaults
  content: 'Assert the dock-rule default through default_get, and keep the baler selection
    key hrb, on #537.'
  status: completed
- id: enrichment-inject
  content: 'Record an already-filled converge field as skipped_immutable, and skip
    cursor rollback under the test cursor, on #535.'
  status: completed
- id: crm-contracts
  content: Keep Buyer/Supplier off partner categories, place the address-matched material,
    format phones canonically, and point the sale order at the facility.
  status: completed
- id: gate-reach
  content: Make the Linda gate-reach scan follow the receiver class instead of every
    same-named function, without an allowlist.
  status: completed
- id: reprove
  content: Publish the owning tips with make pr-nosmoke, then rerun install-smoke
    and runtime-test on a new disposable worktree.
  status: completed
isProject: false
built: true
status: built
---

# Repair the C5 runtime failures

Install-smoke on combined `6a506de9` already passed. Runtime on `odoo_test_w5b47f5f252` was 20 failed and 13 errors of 1449. Pure Python on the touched modules passed (812). Lane R stays stopped. No merge.

The booking insert in `test_typed_rows_obey_the_branch_check` is the negative check: it expects the database to reject a `booking_issue` row with no `source_revision_key`. Leave [`plasticos_logistics/models/linda_request.py`](plasticos_logistics/models/linda_request.py) `_check_exactly_one_source_order` as it is.

Each repair is committed on the open tip that already contains that file, then published with `make pr-nosmoke` and the existing stacked `base=`. Module versions that exist only on these branches stay put. A fresh disposable worktree then reruns install-smoke and the same runtime list. Do not reuse `2140-c5-open-prs`.

## One cause, one place

- **Schedule cursor lane.** Twelve logistics errors are `ValueError: Wrong value for plasticos.linda.sweep.cursor.lane: 'schedule'`. [`schedule_obligations.py`](plasticos_logistics/models/schedule_obligations.py) pages with lane `"schedule"`, and [`linda_sweep_cursor.py`](plasticos_logistics/models/linda_sweep_cursor.py) only allows `ack` and `chase`. Add `schedule` to that selection. This lands on #536.
- **Dock-rule default.** The created company is already `"appointment"`. Odoo 19 stores a Selection default as a callable, so [`test_capabilities.py`](plasticos_facility_profile/tests/test_capabilities.py) must read it through `default_get`, not `Field.default`. The field in [`res_partner_delivery_term.py`](plasticos_facility_profile/models/res_partner_delivery_term.py) stays `default="appointment"`. Lands on #537.
- **Baler detail key.** The seed selection is `['hrb', 'HRB']` and the migration writes the key `hrb`. A create of `{"baler": "hrb"}` is read back as `HRB`. Keep the key as the stored value on [`plasticos.capability`](plasticos_facility_profile/models/capability.py), so the migration identity and [`test_facility_form_edits.py`](plasticos_facility_profile/tests/test_facility_form_edits.py) see `hrb`. Lands on #537.
- **Enrichment inject and its test cursor.** [`enrichment_run.py`](plasticos_enrichment/models/enrichment_run.py) `action_inject` raises when `contamination_tolerance_pct` is already filled. The test's contract is a `skipped_immutable` provenance row and the value `1.5` left in place. Record that skip and continue. `_rollback_then_persist_operator_state` calls `cr.rollback()`, which the Odoo test cursor forbids. Under a test cursor, write the operator state on the current cursor and do not roll the test transaction back. A real request keeps rollback, then the owned cursor. Lands on #535.
- **Role categories.** [`test_crm45_classification.py`](plasticos_crm_sync/tests/test_crm45_classification.py) states the contract: Buyer and Supplier raise ranks and CRM tags, and they do not attach `categ_buyer` or `categ_supplier`. Company-type categories such as Manufacturer still attach. Stop the role-to-category write in [`orchestrator.py`](plasticos_crm_sync/services/orchestrator.py). A blocked role (`End User` / Broker) must also leave `lead.tag_ids` empty. Lands on #535.
- **Phone spelling.** The contact formatter's canonical NANP form is the stored value, for example `(215) 555-0101`. Update the five assertions that still expect the source spelling: three in [`test_orchestrator_upsert.py`](plasticos_crm_sync/tests/test_orchestrator_upsert.py) and two in [`test_opportunity_reach_contact.py`](plasticos_crm_bridge/tests/test_opportunity_reach_contact.py). Do not turn the formatter off.
- **Sale customer.** `test_manual_offer_reaches_one_winner_and_release` and `test_submit_creates_one_draft_pair_and_confirm_does_not_compile_another` get a different `sale.order.partner_id` than the facility the test names. Set the draft sale order's customer to that facility in the CRM-bridge release path. Lands on the tip that currently contains that release method.
- **Material on the matching site.** `test_person_material_lands_on_the_linked_site_matching_the_address` finds no HDPE profile on the south site. ADR-132 is the contract: the address-matching site gets the profile. Fix the writer used by that classification path. Lands on #535.
- **Missing-role report.** [`test_validation_query_scope.py`](plasticos_partner_import/tests/test_validation_query_scope.py) requires `audit_import_integrity()["facilities_missing_role"]` to equal `_original_missing_role`. The report currently adds `NC-D Location Pending`. Make the report use that same predicate.
- **Historical SO notice.** `test_notice_goes_only_to_the_historical_address` receives an extra `"Linda" <@False>` plus the buyer. Do not queue a message whose address does not normalize. The buyer notice stays. Lands on #536 with the cursor fix.
- **Gate-reach false path.** [`linda_gate_reach.py`](plasticos_logistics/tests/linda_gate_reach.py) follows every function of the same name, so `cron_enrichment_sweep_send` appears to reach `action_record_actual_event` through `run` and `action_confirm`. Follow a `self` call only to that class, and follow a bare name only when one definition exists. Do not add an allowlist. The planted-path tests in [`test_s11_linda_approval.py`](plasticos_logistics/tests/test_s11_linda_approval.py) must stay green. Lands on #536.
- **Two more reds in the same run.** `test_approved_aliases_create_one_facility_and_replay` finds material attributes on LDPE where it expects none, and the phrase `1 & 2 pet & hdpe co-mingled bottles` stays unresolved. Fix both in the VanillaSoft material writer and map on #535, or this runtime stays red.

## Proof

After the four tips publish, merge #535, #536, #537, and #531 onto current Staging in a new worktree. Pass is install-smoke exit 0 and a runtime receipt with failed 0 and errors 0. The pure-Python modules the diff touches run with the primary `.venv`. Write the T-C5 counts beside the lane brief; do not overwrite [`docs/campaigns/11-17-26/c5-campaign/CURSOR_C5_INTEGRATION.md`](docs/campaigns/11-17-26/c5-campaign/CURSOR_C5_INTEGRATION.md).

## Build evidence (auto)

- detected_at: `2026-11-17T23:29:58Z`
- conversation_id: `7613a2d3-bf24-42d2-945b-ba89004c9fd1`
- generation_id: `04ee7574-f0c4-4a32-a223-54c94b2eef04`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/7613a2d3-bf24-42d2-945b-ba89004c9fd1/7613a2d3-bf24-42d2-945b-ba89004c9fd1.jsonl`
- todos at build time:
- `schedule-lane`: completed
- `facility-defaults`: completed
- `enrichment-inject`: completed
- `crm-contracts`: completed
- `gate-reach`: completed
- `reprove`: completed

