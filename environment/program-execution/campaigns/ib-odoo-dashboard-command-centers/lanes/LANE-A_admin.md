# LANE-A — Admin correctness + Admin command center

## MANIFEST
- Campaign: `ib-odoo-dashboard-command-centers` v1.0.0 — definition in Quantum-L9/Cursor-Governance, execution in `cryptoxdog/IB-Odoo_19` off `Staging` @ `c422140`.
- Tasks (order): TASK-010 → TASK-011 → TASK-013 → TASK-031; TASK-012 after TASK-013 once DEC-002 is decided (CTO sends CTO ANSWER).
- Writable paths: `plasticos_admin_dashboard/**` only. Everything else is read-only.
- Repositories: attach `cryptoxdog/IB-Odoo_19` with push (add_repo), clone, register_repo_root. Read-only: `Quantum-L9/L9-Ops-MCP` (kernels), `Quantum-L9/Cursor-Governance` (campaign definition; your session source).
- Role: coding agent in the CTO pool (launch system prompt governs reporting, publishing and PR ownership).

## OBJECTIVE
Make every Admin dashboard number correct and every Admin KPI open exactly the records it counts.
1. TASK-010 (F-001, F-007, N-002): rebuild the eight urgency drills (`admin_dashboard.py:521-629`) under DEC-007. Retarget each drill to its source model (`plasticos.transaction`, `plasticos.offer`, `plasticos.web.lead`, `plasticos.intake`) with the same predicate its KPI SQL counts (e.g. negative margin → the transaction margin predicate used at :283-313; missing docs → `compliance_status`; stalled follow-up → `supplier_confirmation_followup_count` / `is_supplier_confirmed`; commission unlocked → `commission_locked`). Fix `action_open_sales_dashboard`'s undefined `search_default_filter_open`. Bind the menu (`views:318-323`) to `action_open_admin_dashboard` (server action) so it opens the stored singleton.
2. TASK-011 (F-002): rewrite the rep-performance view (`:695-783`) — one CTE per measure, each pre-aggregated per (user, period) before the join; `deals_open = COUNT(DISTINCT ot.id)`; exclude `legacy_erp_history` (DEC-009); label open pipeline as a snapshot.
3. TASK-013 (F-006, DEC-008): add `company_id` to `plasticos.admin.kpi`, one record per company via `_get_or_create`, scope every KPI query to `env.companies` through `sale_order_id.company_id` (loads: `plasticos_load.company_id`; invoices: `account_move.company_id`). MINOR bump + repeatable migration. The record rule waits for DEC-005(c): write the CTO-QUESTION, do not add it.
4. TASK-012 (N-001, blocked on DEC-002): replace `write_date` in every closed-deal period predicate (`:296,325-336,736-744`) with the decided business date.
5. TASK-031 (F-005): every KPI in sections B, C, E, F becomes a drill button; unavailable ≠ 0. If the TASK-001 spike report says SUPPORTED, ship the Admin analytic board as `spreadsheet.dashboard` module data with the record shape that report specifies; if NOT_SUPPORTED, stop at native views.

## NON-GOALS
- No new Admin KPIs beyond those in the views today (scope is correctness + drillability).
- No change to the 15-minute cron (`data/cron_refresh_dashboard.xml`) cadence.
- No Owl unless the TASK-001 report names a gap and the CTO assigns it.
- No Gate / CEG / EIE / Neo4j / TransportPacket surface is touched by this lane; if a change would reach one, CTO-QUESTION.

## ASSETS USED
- Campaign definition (Quantum-L9/Cursor-Governance): `environment/program-execution/campaigns/ib-odoo-dashboard-command-centers/CAMPAIGN_SOURCE.yaml` (decisions DEC-001..009, tasks, gates), `CURRENT_STATE.yaml` (re-verified findings at Staging c422140), `ACCEPTANCE.md`.
- Coding kernel: `Quantum-L9/L9-Ops-MCP` `docs/kernels/R5/l9_coding_kernel.v1.md` (hard bans: no print, no eval/exec, CI-enforced) and `docs/kernels/R5/l9_build_kernel.v1.md` (no stubs or pass-only functions; no `status: pass`-only reports).
- Governance coding kernel: `skills/l9-coding-agent/kernels/CODING_KERNEL.yaml` (smallest complete root-cause repair) — bound through /coding-agent mode, never invoked as a skill.
- Target repo law (cryptoxdog/IB-Odoo_19): `AGENTS.md` (Git Workflow :236-242, Ask First :543-547, Never list :549-566), `CLAUDE.md`, `INVARIANTS.md` (POS-INV-05 company isolation, POS-INV-19 repeatable migrations), `skills/plasticos-odoo-version-bump/SKILL.md`.
- Odoo 19 docs: Context7 `/websites/odoo/19.0` (verify any ORM/view/action API before use; record the query in the PR).

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
- Truth contract: report NOT RUN where a check did not run; never present a static read as runtime proof.

## DONE-CRITERIA
- AC-010: per urgency KPI, a `TransactionCase` builds fixtures and asserts `search_count(drill domain) == KPI value`; every drill domain validates on its `res_model`; the menu opens the stored record.
- AC-011: fixture of 2 closed (10k, 20k), 3 open (5k each), 2 intakes × 2 offers yields revenue_closed 30k, pipeline 15k, deals_open 3; `test_rep_performance_view.py` still passes.
- AC-013: two companies' data never mix in either company's KPI record.
- AC-012: a closed deal edited today stays in its original period (after DEC-002).
- AC-031: no actionable KPI is a plain field; each has a parity test; unavailable renders distinct from 0.
- One PR per task (stacked within the lane), each green through `make pr`; then CTO-STATUS: ready-to-merge per PR.

## ACTIVATION
Launch via `cto_mode.py launch-spec --cto-session <CTO session> --lane-repo cryptoxdog/IB-Odoo_19 --model <model> --tag lane:lane-a --tag campaign:ib-odoo-dashboard-command-centers`; pass `create_session` fields unchanged; this file's body is the task prompt. Start condition: see `CAMPAIGN_EXECUTION_BINDING.yaml` lanes[].
