# LANE-C — Native dashboard spike + Logistics command center

## MANIFEST
- Campaign: `ib-odoo-dashboard-command-centers` v1.0.0 — definition in Quantum-L9/Cursor-Governance, execution in `cryptoxdog/IB-Odoo_19` off `Staging` @ `c422140`.
- Tasks (order): TASK-001 → TASK-032.
- Writable paths: `docs/reports/gmp-reports/ib-odoo-dashboard-command-centers-TASK-001-native-dashboard-spike.md`, `plasticos_logistics/models/load_dashboard.py`, `plasticos_logistics/views/load_dashboard_views.xml`, `plasticos_logistics/tests/test_load_dashboard*.py`, `plasticos_logistics/tests/__init__.py`, `plasticos_logistics/__manifest__.py`. Everything else is read-only.
- Repositories: attach `cryptoxdog/IB-Odoo_19` with push (add_repo), clone, register_repo_root. Read-only: `Quantum-L9/L9-Ops-MCP` (kernels), `Quantum-L9/Cursor-Governance` (campaign definition; your session source).
- Role: coding agent in the CTO pool (launch system prompt governs reporting, publishing and PR ownership).

## OBJECTIVE
1. TASK-001 (UNK-001): read the installed `spreadsheet_dashboard` and `spreadsheet_edition` source (Enterprise mirror per `docker-compose.yml` / `make runtime-bootstrap`; `plasticos_odoo_standard_apps/__manifest__.py:24`). Determine the exact data shape to ship a `spreadsheet.dashboard` (spreadsheet JSON file field, dashboard group, `group_ids`) from a custom module, and whether `-u` upgrades it reproducibly. Write the spike report with verdict SUPPORTED / NOT_SUPPORTED, the source file:line evidence, the record shape, and any native gap that would need Owl. Commit the report only — no product code. Publish it as its own PR into Staging (CTO reads it to close GATE-002).
2. TASK-032: upgrade `plasticos.load.dashboard` (`load_dashboard.py:17-239`, views `load_dashboard_views.xml`) into the Logistics command center: today's pickups and deliveries, late loads, SLA breached, exceptions, missing BOL, pending scheduling, carrier issues — each a DEC-007 drill to `plasticos.load`; add kanban, pivot and graph views reusing the existing filters (`filter_sla_breached`, `filter_missing_bol`). Keep the existing buttons (`action_view_load/transaction/documents/carrier`). Add the module's first dashboard tests.

## NON-GOALS
- No change to the global company rule or the rep/logistics/ops-manager dashboard rules in `plasticos_security_base` (they already exist).
- No Linda, freight or escalation-engine logic changes.
- No spreadsheet dashboard for Logistics unless the spike says SUPPORTED and the CTO assigns it.
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
- AC-001: spike report with verdict, source lines and record shape; no product code in that PR.
- AC-032: each logistics counter equals `search_count` of its drill domain on `plasticos.load`; company isolation and the sales-rep own rule hold on the dashboard (two-company + two-rep fixtures).
- PRs into Staging green via `make pr`; CTO-STATUS: ready-to-merge per PR.

## ACTIVATION
Launch via `cto_mode.py launch-spec --cto-session <CTO session> --lane-repo cryptoxdog/IB-Odoo_19 --model <model> --tag lane:lane-c --tag campaign:ib-odoo-dashboard-command-centers`; pass `create_session` fields unchanged; this file's body is the task prompt. Start condition: see `CAMPAIGN_EXECUTION_BINDING.yaml` lanes[].
