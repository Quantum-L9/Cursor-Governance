# LANE-C — Dashboard authoring proof + Logistics Live Control Tower + Linda authority

## MANIFEST
- Campaign: `ib-odoo-dashboard-command-centers` v1.2.0 — definition in Quantum-L9/Cursor-Governance, execution in `cryptoxdog/IB-Odoo_19` off `Staging` @ `c422140`.
- Tasks (order): TASK-001 → TASK-032 (starts once LANE-D's TASK-060 is merged into Staging) → TASK-061 (starts once DEC-011 is decided; CTO sends CTO ANSWER).
- Writable paths: `docs/reports/gmp-reports/ib-odoo-dashboard-command-centers-TASK-001-*`, `plasticos_logistics/models/load_dashboard.py`, `plasticos_logistics/models/linda_approval.py`, `plasticos_logistics/views/load_dashboard_views.xml`, `plasticos_logistics/views/linda_approval_views.xml`, `plasticos_logistics/data/**` (activity types / dashboard data only), `plasticos_logistics/tests/test_load_dashboard*.py`, `plasticos_logistics/tests/test_s11_linda_approval.py`, `plasticos_logistics/tests/__init__.py`, `plasticos_logistics/__manifest__.py`. Everything else is read-only.
- Repositories: attach `cryptoxdog/IB-Odoo_19` with push (add_repo), clone, register_repo_root. Read-only: `Quantum-L9/L9-Ops-MCP` (kernels), `Quantum-L9/Cursor-Governance` (campaign definition; your session source).
- Role: coding agent in the CTO pool (launch system prompt governs reporting, publishing and PR ownership).

## OBJECTIVE
1. TASK-001 (UNK-001): prove the DEC-001 authoring path. On the runtime fixture (`make runtime-bootstrap`, Enterprise editor), author one dashboard: one Odoo pivot on `plasticos.load` with a domain, one global date filter with `fieldMatching`, one chart with a `chartOdooMenusReferences` entry. Export the JSON; ship it on a throwaway branch as a `spreadsheet.dashboard` record in the official shape (`spreadsheet_binary_data` type=base64 file=…, `main_data_model_ids`, `dashboard_group_id`, `group_ids` = Logistics, `company_ids`, `sequence`, `is_published`); install, `-u` twice, diff the stored JSON, click-test drill-down. Write the report (verdict, evidence, exact XML, any native gap that would need the Owl review surface). Publish the report only.
2. TASK-032 Logistics Live Control Tower: upgrade `plasticos.load.dashboard` (`load_dashboard.py:17-239`) and its views. Default searches Today, Next 48 Hours, Needs Attention. Pickup/delivery timeline beside: Linda held commands (`plasticos.linda.approval` pending), missing shipping documents and Logistics-routed exception activities (DEC-012 types from TASK-060), unconfirmed carriers, loads blocked from release (`load.py` release-hold guards). Every count is a DEC-007 drill. A Linda case form shows the original reply, conflicting fact, affected load, proposed command and next action, resolvable in place for whichever role `linda_approval` authorizes at that time. Kanban with progressbar, pivot, graph, searchpanel; keep existing buttons and filters (`filter_sla_breached`, `filter_missing_bol`). Emphasis on exceptions that threaten the next shipment. Add the module's first dashboard tests.
3. TASK-061 (DEC-011): replace the single `MANAGER_GROUP` check in `_require_approver` (`linda_approval.py:50,374-378`) with a server-side authority table keyed on (`command`, `edge_case`) granting `plasticos_security_base.group_logistics_ops` only the classes DEC-011 decides; Operations Manager keeps all; Linda stays refused. On `hold_for_approval` (`:198`) schedule one idempotent activity for the class's owning role. Do not touch replay (`_execute` :441-457), the stale-conflict check, `FOR UPDATE` locking, the pending unique index, refusal records or the kill switch.

## NON-GOALS
- No change to the global company rule or the rep/logistics/ops dashboard rules in `plasticos_security_base`, and no group membership change (DEC-011 changes code authority, not groups).
- No Linda send/chase logic, freight or escalation-engine changes; Linda stays the sole logistics-document chase sender.
- No pricing, credit or accounting actions on any Logistics surface.

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
- AC-001: authoring-path report with verdict, source lines, exact XML and reproducibility diff; no product code in that PR.
- AC-032 / A09 / A13: each Control Tower count equals `search_count` of its drill domain; BOL and scale-ticket exceptions appear with one-click navigation to the exact load and original; company isolation and the sales-rep own rule hold (two-company + two-rep fixtures).
- AC-061 / A17 / A18: per (command, edge_case) class the authorized role succeeds through the unchanged replay path; every other role, Linda and a plain Logistics user get `AccessError`; a pending approval has exactly one open activity for its owning role; re-holding does not duplicate it.
- Each task its own PR into Staging, green via `make pr`; CTO-STATUS: ready-to-merge per PR.

## ACTIVATION
Launch via `cto_mode.py launch-spec --cto-session <CTO session> --lane-repo cryptoxdog/IB-Odoo_19 --model <model> --tag lane:lane-c --tag campaign:ib-odoo-dashboard-command-centers`; pass `create_session` fields unchanged; this file's body is the task prompt. Start condition: see `CAMPAIGN_EXECUTION_BINDING.yaml` lanes[].
