# LANE-B — Sales correctness + Sales command center

## MANIFEST
- Campaign: `ib-odoo-dashboard-command-centers` v1.2.0 — definition in Quantum-L9/Cursor-Governance, execution in `cryptoxdog/IB-Odoo_19` off `Staging` @ `c422140`.
- Tasks (order): TASK-020 → TASK-021 → TASK-033.
- Writable paths: `plasticos_commission/models/sales_dashboard.py`, `plasticos_commission/views/sales_dashboard_views.xml`, `plasticos_commission/tests/**`, `plasticos_commission/__manifest__.py`. Everything else is read-only.
- Repositories: attach `cryptoxdog/IB-Odoo_19` with push (add_repo), clone, register_repo_root. Read-only: `Quantum-L9/L9-Ops-MCP` (kernels), `Quantum-L9/Cursor-Governance` (campaign definition; your session source).
- Role: coding agent in the CTO pool (launch system prompt governs reporting, publishing and PR ownership).

## OBJECTIVE
Make the Sales dashboard show real commission state and let a rep reach every underlying record.
1. TASK-020 (F-003, DEC-006): replace the constants at `sales_dashboard.py:181-183`. `commission_locked_amount` ← `plasticos_transaction.commission_locked_amount`; `commission_payout_state` ← state of the newest non-cancelled `plasticos.commission.payout` linked via `commission_payout_tx_rel` (`commission_payout.py:73-83`), else `unpaid`. Un-hide the payout button when a payout exists.
2. TASK-021 (F-004, F-010, DEC-003): `action_view_load` with `load_count > 1` returns an `ir.actions.act_window` on `plasticos.load` with `domain [('transaction_id','=',…)]` (list, form). Add `action_view_transaction` opening the owning `plasticos.transaction`, visible only when the user can read it (check with `check_access`/record rules, never `sudo`). Update the docstring at `:17-18` to state DEC-003.
3. TASK-033: rep command center over the corrected projection — open opportunities, outstanding offers, active deals, pending confirmations, margin, commission, missing customer documents — each a DEC-007 drill; pivot and graph views.

## NON-GOALS
- Do not write `plasticos.transaction.commission_payout_state` (RISK-003; DNB-004).
- No changes to commission rules, payout generation or `commission_service.py`.
- No security group / record rule edits.
- No Gate / CEG / EIE / Neo4j / TransportPacket surface is touched by this lane; if a change would reach one, CTO-QUESTION.

## ASSETS USED
- Campaign definition (Quantum-L9/Cursor-Governance): `environment/program-execution/campaigns/ib-odoo-dashboard-command-centers/CAMPAIGN_SOURCE.yaml` (decisions DEC-001..009, tasks, gates), `CURRENT_STATE.yaml` (re-verified findings at Staging c422140), `ACCEPTANCE.md`.
- Coding kernel: `Quantum-L9/L9-Ops-MCP` `docs/kernels/R5/l9_coding_kernel.v1.md` (hard bans: no print, no eval/exec, CI-enforced) and `docs/kernels/R5/l9_build_kernel.v1.md` (no stubs or pass-only functions; no `status: pass`-only reports).
- Governance coding kernel: `skills/l9-coding-agent/kernels/CODING_KERNEL.yaml` (smallest complete root-cause repair) — bound through /coding-agent mode, never invoked as a skill.
- Target repo law (cryptoxdog/IB-Odoo_19): `AGENTS.md` (Git Workflow :236-242, Ask First :543-547, Never list :549-566), `CLAUDE.md`, `INVARIANTS.md` (POS-INV-05 company isolation, POS-INV-19 repeatable migrations), `skills/plasticos-odoo-version-bump/SKILL.md`.
- Odoo 19 docs: Context7 `/websites/odoo/19.0` first; where it lacks developer detail, the official sources below.
- Official Odoo 19.0 build sources (EVID-007): dashboard record shape `odoo/odoo` 19.0 `addons/spreadsheet_dashboard_account/data/dashboards.xml` L4-13 and `addons/spreadsheet_dashboard/models/spreadsheet_dashboard.py`; dashboard JSON keys (`pivots`, `lists`, `globalFilters` with `fieldMatching`, `chartOdooMenusReferences`) in `addons/spreadsheet_dashboard_sale/data/files/sales_dashboard.json`; access `addons/spreadsheet_dashboard/security/security.xml`; `mail.activity` `activity_search`/`activity_schedule`/`activity_feedback` in `addons/mail/models/mail_activity_mixin.py` L340-503; view reference https://www.odoo.com/documentation/19.0/developer/reference/user_interface/view_architectures.html (kanban progressbar, searchpanel, graph, pivot); client actions https://www.odoo.com/documentation/19.0/developer/howtos/javascript_client_action.html; Documents AI and digitization limits https://www.odoo.com/documentation/19.0/applications/productivity/ai/document_sort.html and .../finance/accounting/vendor_bills/invoice_digitization.html.

## WORKFLOW
1. Bootstrap per the launch system prompt; /coding-agent mode ACTIVE before any edit; first CTO-STATUS carries the mode JSON.
2. Re-verify each finding you fix at the current `origin/Staging` head (file:line) before editing; if it moved or was fixed, CTO-STATUS with the evidence and skip only that item.
3. Per task: GMP Phase 0 plan in your transcript (files, actions, tests) → write the failing parity/reconciliation test first → implement the smallest complete repair → version bump → `make check`, `make test`, `python3 scripts/check_module_wiring.py` → scoped commit (explicit pathspecs).
4. Publish each task as its own PR into `Staging` with `make pr` (stack later tasks on your open lane PR with `make pr base=<branch>`). PR body: finding ids closed, decision ids applied, old vs new metric definition (RISK-001), Context7 queries used.
5. Own each PR to ready-to-merge; then the next task.

## CONSTRAINTS
- Base branch `Staging`; PR into `Staging` through the repo's own `make pr` (follow-on tasks in this lane stack with `make pr base=<your open lane branch>`). Never touch `Production`. Never merge.
- Odoo 19 rules: `models.Constraint` not `_sql_constraints`; no `@api.depends("id")`; no `category_id` on `res.groups`; external IDs, never DB ids; no `sudo()` without a written justification in code.
- Bump the module version on every Python/XML/security/migration change (PATCH for views/ACL/logic, MINOR for a new field/model, with `migrations/<new_version>/` when schema changes). Never ask whether to bump.
- DEC-007 KPI-drill parity: each actionable KPI is declared once (model, domain, aggregate); the value and the drill come from that declaration; a test asserts `search_count(drill_domain) == displayed value` on fixtures.
- A true zero must render distinctly from unavailable/stale; never default an error to 0.
- Do not change security groups, record rules, crons or `plasticos_base` unless the campaign decision for it is accepted (DEC-005). Prohibited paths: `plasticos_base/**`, `plasticos_gate/**`, `.github/workflows/**`, `plasticos_transaction/models/**`, Docker/compose/.env files.
- Runtime tests: rely on the `make pr` pre-push gate (pr-check incl. install-smoke) — do not run `make test-module` / `make test-odoo` ad hoc. Locally run `make check` and `make test`; run `python3 scripts/check_module_wiring.py` before each commit.
- Exceptions are `mail.activity` records only (DEC-012): module-owned activity type per exception class, assignee via `plasticos_base` `_plasticos_escalation_manager_in_group`, `activity_search` before any create (Odoo never deduplicates), `activity_feedback` to close. No new queue table, scheduler or verification writer.
- Native AI Auto-Sort (DEC-013 OPT-C) may only move documents between the existing Plasticos folders and add existing tags; no bill/invoice creation, activity or code tool; it never verifies evidence; no bill auto-post; no new external sender — Linda stays the sole logistics-document chase sender. An unsure or failed AI run leaves Needs Review for Operations; UNKNOWN stays UNKNOWN.
- Authority is enforced server-side; a hidden or shown button is never the control.
- Truth contract: report NOT RUN where a check did not run; never present a static read as runtime proof.

## DONE-CRITERIA
- AC-020: transaction in a paid payout shows `paid` and its locked amount; a cancelled payout falls back to the prior state or `unpaid`; tests cover unpaid/confirmed/paid/cancelled.
- AC-021: a three-load deal's Track Load returns an act_window whose domain yields exactly those three loads (extend `test_sales_dashboard_load_cardinality.py`); Open Deal works for the owning rep and is absent for a non-owner.
- AC-033: every counter reconciles with its drill for the logged-in rep and excludes other reps' records.
- Stacked PRs into Staging, each green via `make pr`; CTO-STATUS: ready-to-merge per PR.

## ACTIVATION
Launch via `cto_mode.py launch-spec --cto-session <CTO session> --lane-repo cryptoxdog/IB-Odoo_19 --model <model> --tag lane:lane-b --tag campaign:ib-odoo-dashboard-command-centers`; pass `create_session` fields unchanged; this file's body is the task prompt. Start condition: see `CAMPAIGN_EXECUTION_BINDING.yaml` lanes[].
