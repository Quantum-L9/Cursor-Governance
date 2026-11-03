---
name: PR test remediation
overview: 'Close every failure from the combined fixture run, then leave #345 through
  #349 CLEAN against Staging with green CI. Ordered merge of #346, #347, #348, and
  #349 passes the Enterprise fixture with zero failures.'
todos:
- id: linda-role
  content: 'On #346, switch the Linda SO issuance user to group_logistics. The class
    is covered by the one fixture run, not a per-commit test.'
  status: completed
- id: acl-rows
  content: 'On #347, move transaction-line and claim blanket ACL rows to base.group_system;
    bump transaction to 19.0.2.3.46 and claims to 19.0.1.1.5'
  status: completed
- id: doc-projection
  content: 'On #347, privilege all six missing-doc flag writes and bump plasticos_documents
    to 19.0.2.1.10'
  status: completed
- id: stale-tests
  content: 'On #347, fix load_ids, the compliance-audit cron contract, and the web-lead
    review_status assertion'
  status: completed
- id: rebase-348-349
  content: 'Rebase #348 at transaction 19.0.2.3.47 keeping both behaviors and group_system
    ACL; rebase #349 to partner_import 19.0.2.10.33'
  status: completed
- id: retest
  content: Ordered merge on a throwaway worktree, then make test-odoo on the pinned
    fixture clone; drop the clone
  status: completed
- id: publish-ci
  content: One commit and one push per open PR. No full pytest and no install-smoke
    on those commits or pushes. GitHub CI is the per-PR verdict.
  status: completed
isProject: false
built: true
status: built
---

# Remediate every open pull request

Architecture is settled. No new model, group, or module. Linda is `plasticos_security_base.group_logistics`. Sale confirmation in [plasticos_transaction/models/sale_inherit.py](plasticos_transaction/models/sale_inherit.py) stays an unprivileged `transactions.create`.

Source run: throwaway `integration/prs-346-349` at `3f7e0fb6` on fixture `odoo_test_tpl_ee_c9e8a81f52f23680`. Scoped roster: 3 failed, 31 errors, 853 tests. Full roster: 4 failed, 31 errors, 1117 tests. The extra failure is the web-lead assertion; the 31 errors are the same set. SQL noise in `/tmp/int_full.log` (duplicate keys, lock timeout, serialization, a missing rollback relation) did not fail a test. `TestWebLeadConfigPrivilege.test_internal_user_is_denied_before_any_provider_call` logs an expected `openai_api_key` AccessError and passed. Leave both alone.

## Finding ledger

Each row below was an ERROR or FAIL on that run. One code change covers each group.

- **ERROR** `TestLindaSoIssuance.test_so_only_live_issue_reaches_sink_once`. `sale_inherit.py` line 42 creates `plasticos.transaction` as uid 101, `sales_team.group_sale_salesman`. After #347 that group cannot create a transaction. Fix on #346: the user is `plasticos_security_base.group_logistics`. No `sudo()` on the create.
- **ERROR** 28 document tests, one stack. `action_associate` → `_trigger_transaction_recompute` → `_compute_missing_doc_flags` assigns `tx.missing_supplier_docs` ([transaction_docs.py](plasticos_documents/models/transaction_docs.py) line 94) as the document user, and `transaction.write` denies it. Classes: `TestHistoricalAutopostGuard` (6), `TestExactAssociation` (2), `TestExpiryFinalGate` (5), `TestNativeVerificationOnEnterpriseFixture` (1), `TestPr322Findings` (8), `TestVerificationWriter` (6). Fix on #347: privilege every flag assignment in that method, including the three early-return writes at lines 68–70 and `missing_carrier_docs` / `missing_buyer_docs` at lines 95–96. #348 owns the historical tests and does not edit this file. After the fix, `TestVerificationWriter.test_base_internal_user_cannot_verify` must still reach its real assertion that a base user cannot verify.
- **ERROR** `TestCronInDomain.test_compliance_audit_clears_verified_on_expired_document`. Create writes `verified`, and [document.py](plasticos_documents/models/document.py) `_refuse_direct_decision_write` raises. The cron only logs; it does not clear `verified`. Fix the test to that contract.
- **ERROR** `TestCronInDomain.test_scale_tickets_leave_unloaded_transaction`. Line 327 reads `transaction.load_id`. The field on Staging is `load_ids`. Assert `load_ids` is empty.
- **FAIL** `TestTransactionACL.test_base_user_cannot_write_tx_line`. `access_transaction_line_all` is still full CRUD for `base.group_user`. Move that row to `base.group_system`. Keep `access_transaction_line_user` read-only.
- **FAIL** `TestClaimACL.test_claim_user_cannot_unlink` and `test_no_group_cannot_read`. `access_claim_all` is full CRUD for `base.group_user`, and ACL rows are OR-ed. Move that row to `base.group_system`. Claims-user stays create, write, read, no unlink.
- **FAIL** `TestWebLeadOpportunity.test_hot_admission_creates_one_new_opportunity_without_partner`. [web_lead.py](plasticos_web_leads/models/web_lead.py) sets `clarification_required` when the economic assessment is not assessed. The test expects `pending`. Change the assertion. Do not edit `web_lead.py`.

## Version ladder

Odoo skips a module whose version did not increase. #346 and #347 both currently set `plasticos_transaction` to `19.0.2.3.45`. Merging #346 first would make #347's ACL a no-op. Staging is `19.0.2.3.44`.

- #346 `plasticos_transaction` stays `19.0.2.3.45`. `plasticos_logistics` stays `19.0.1.14.10`. The Linda edit is test-only.
- #347 `plasticos_transaction` becomes `19.0.2.3.46` so the ACL CSV upgrades after #346. `plasticos_claims` becomes `19.0.1.1.5`. `plasticos_documents` becomes `19.0.2.1.10`.
- #348 `plasticos_transaction` becomes `19.0.2.3.47` (its current `.46` now belongs to #347). `plasticos_partner_import` stays `19.0.2.10.32`.
- #349 `plasticos_partner_import` becomes `19.0.2.10.33`.

`ruff format` every touched manifest.

## #346

In [plasticos_logistics/tests/test_linda_so_issuance.py](plasticos_logistics/tests/test_linda_so_issuance.py), replace `linda_so_sales` / `sales_team.group_sale_salesman` with `plasticos_security_base.group_logistics`, the group `linda.logistics.only` already uses. Rename the fixture off `salesperson` and update confirm, cancel, notice write, and the forged create.

`access_transaction_logistics` is create, write, read. `access_sale_order_logistics` is read and write, so confirmation stays a write; the order is created as superuser. Do not add `group_logistics` to `plasticos.logistics.request`. `_issue_orders` already records evidence under `sudo()`. The forge test must still raise `AccessError`. The whole `TestLindaSoIssuance` class is part of the one fixture run. Do not run that class, `make test-module`, or `make test` before the #346 push.

If confirm itself demands a salesman group, stop. Do not put `group_sale_salesman` back and do not `sudo()` the transaction create.

## #347

Read each ACL CSV before editing. Keep its id format. Do not add a row that a stronger row already covers.

- [plasticos_transaction/security/ir.model.access.csv](plasticos_transaction/security/ir.model.access.csv): `access_transaction_line_all` group becomes `base.group_system`. `access_transaction_all` stays `base.group_system`.
- [plasticos_claims/security/ir.model.access.csv](plasticos_claims/security/ir.model.access.csv): `access_claim_all` group becomes `base.group_system`.
- [plasticos_documents/models/transaction_docs.py](plasticos_documents/models/transaction_docs.py): all six flag assignments in `_compute_missing_doc_flags` are privileged writes. Same-line `sudo()` justification: compliance flags are a system effect of document association, not a documents-manager edit of the transaction. The write still enters `transaction.write`, so #346's load guard and #348's reopen still run for any vals they care about. These vals are only the three `missing_*_docs` flags.
- [plasticos_claims/tests/test_cron_idempotency.py](plasticos_claims/tests/test_cron_idempotency.py): `load_ids` assertion. Compliance test creates without `verified`, binds a real subject other than `res.partner`, verifies through `action_verify` while current, then sets `expiry_date` in the past, runs the cron twice, and asserts `verified` stays true.
- [plasticos_crm_bridge/tests/test_web_lead_opportunity.py](plasticos_crm_bridge/tests/test_web_lead_opportunity.py): expect `clarification_required`. Keep the one-opportunity and no-partner assertions.

## #348 rebase

Rebase onto #346 and #347. Keep both sides of the trial resolution:

- [plasticos_transaction/models/transaction.py](plasticos_transaction/models/transaction.py) `write`: #346's sale-order guard while loads are linked, then #348's `reopened` filter, `super().write`, and `_post_historical_reopen`.
- ACL: `access_transaction_all` and `access_transaction_line_all` stay on `base.group_system`, plus #348's reopen-wizard row. Do not put either `_all` row back on `base.group_user`.
- Version `19.0.2.3.47`.
- [sale_inherit.py](plasticos_transaction/models/sale_inherit.py): #348's historical worksheet values only. The conflict hunks sit above `transactions.create`. That create stays unprivileged.

## #349 rebase

Rebase onto #348. The only overlap is [plasticos_partner_import/__manifest__.py](plasticos_partner_import/__manifest__.py). Set `19.0.2.10.33`.

## Proof

One fixture run, after the four code branches are committed, not once per commit. Throwaway worktree off `origin/Staging`. Merge #346, #347, #348, #349 in that order. A conflict is a failed run: fix the later branch and merge again. Do not leave the resolution only in the worktree.

Clone only `odoo_test_tpl_ee_c9e8a81f52f23680`. `make test-odoo fresh=0` on that clone. Pass is failed = 0, errors = 0, tests > 0, dirty = false. That roster includes `TestLindaSoIssuance`, the document classes in the ledger, and `plasticos_crm_bridge` / `plasticos_web_leads`. Drop the clone and the worktree. Do not create a template and do not set `TEST_ENV_ALLOW_NEW_TEMPLATE` or `TEST_ENV_PARITY`.

This run is not `make test`, not `pytest tests/`, and not `make install-smoke`.

## Commit and push

Open pull requests are #345, #346, #347, #348, and #349. All stay targeted at Staging. No sixth pull request.

Each branch gets one `make commit` and one push to its existing remote branch. That updates the open pull request.

Do not run these on any of those commits or pushes:

- `make test` or `pytest tests/` (full pure-python suite)
- `make install-smoke`
- `make pr` or `make pr-nosmoke`

`make pr` runs `make test` and can run install-smoke. `make pr-nosmoke` skips install-smoke and still runs `make test`. Neither is the push for this work. Pre-commit on `make commit` stays. GitHub CI on the updated pull request is the pure-python verdict. Do not wait on a local full pytest or a local smoke before the push.

#345 (`chore/repo-index`) is regenerated from the green combined tip and pushed last. It does not share files with the other four. Same rule: no full pytest and no install-smoke on that commit or push.

## Done bar

Do not merge any pull request.

- Each of #345–#349 is `mergeable=MERGEABLE` and `mergeStateStatus=CLEAN` against Staging.
- Ordered merge of #346, #347, #348, #349 onto `origin/Staging` has zero conflicts.
- `gh pr checks` for all five shows every required check success. That is GitHub CI after the push. Pending or failed is still open work. A local full pytest or a local install-smoke is not required to call a push done.
- The fixture run is green, including every test named in the ledger.
- Module versions on the combined tip are transaction `19.0.2.3.47`, claims `19.0.1.1.5`, documents `19.0.2.1.10`, logistics `19.0.1.14.10`, partner import `19.0.2.10.33`.

## Execute via Cursor Build

Build commits each existing branch, pushes it without full pytest and without install-smoke, and prints each URL when GitHub CI is green:

- https://github.com/cryptoxdog/IB-Odoo_19/pull/345
- https://github.com/cryptoxdog/IB-Odoo_19/pull/346
- https://github.com/cryptoxdog/IB-Odoo_19/pull/347
- https://github.com/cryptoxdog/IB-Odoo_19/pull/348
- https://github.com/cryptoxdog/IB-Odoo_19/pull/349

`PR_STACK` does not apply. These are parallel branches into Staging, not one chain tip.

## Build evidence (auto)

- detected_at: `2026-10-30T16:46:15Z`
- conversation_id: `4c1cd8c5-9021-4cd7-8cf7-3ede63f0102f`
- generation_id: `cce832d4-5e76-4596-90af-b5a7451d5eea`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/4c1cd8c5-9021-4cd7-8cf7-3ede63f0102f/4c1cd8c5-9021-4cd7-8cf7-3ede63f0102f.jsonl`
- todos at build time:
- `linda-role`: completed
- `acl-rows`: completed
- `doc-projection`: completed
- `stale-tests`: completed
- `rebase-348-349`: completed
- `retest`: completed
- `publish-ci`: completed

