# LANE-D — Operations Manager command center (starts only after DEC-004 and DEC-005)

## MANIFEST
- Campaign: `ib-odoo-dashboard-command-centers` v1.0.0 — definition in Quantum-L9/Cursor-Governance, execution in `cryptoxdog/IB-Odoo_19` off `Staging` @ `c422140`.
- Tasks (order): TASK-040.
- Writable paths: the DEC-004 host module (recommended new `plasticos_ops_dashboard/**`) plus exactly the security records DEC-005 approves. Everything else is read-only.
- Repositories: attach `cryptoxdog/IB-Odoo_19` with push (add_repo), clone, register_repo_root. Read-only: `Quantum-L9/L9-Ops-MCP` (kernels), `Quantum-L9/Cursor-Governance` (campaign definition; your session source).
- Role: coding agent in the CTO pool (launch system prompt governs reporting, publishing and PR ownership).

## OBJECTIVE
Build a cross-department execution queue for `plasticos_security_base.group_operations_manager` (`security_groups.xml:112-117`), company-scoped per DEC-008, every item drilling to its source record (DEC-007):
- Linda approvals pending decision — `plasticos.linda.approval` `state='pending'` (`linda_approval.py:259-309`; approve/reject already require this group, :377-426).
- Claims escalated or overdue — `plasticos.claim` `state='escalated'` or `is_overdue` (`claim.py:14`, cron `_cron_check_sla` :404). Company derives via `transaction_id`/`load_id` (claim has no company_id).
- Load exceptions / SLA breaches / missing BOL — `plasticos.load` (`state='exception'`, `sla_breached`, `bol_*_attached`).
- Document gaps overdue or escalated — `plasticos.transaction.missing_doc_status in ('overdue','escalated')` (`transaction_docs.py:18`).
- Documents awaiting review — `plasticos.document.association_review_required` and native `documents.document.verification_review_required`.
- Delivered-uninvoiced handoffs — the predicate `admin_dashboard.py:283-313` already counts (reuse the DEC-007 declaration LANE-A creates; coordinate via CTO-QUESTION if not merged yet).
Menus restricted to the Operations Manager group (DEC-005b); claims access per DEC-005a.

## NON-GOALS
- Not an executive financial report (that is Admin).
- No approval workflow changes — the queue links to existing approve/reject actions.
- No `company_id` added to claim/transaction/offer/intake.
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
- AC-040: an Operations Manager sees each queue with counts equal to its drills; a sales rep cannot open the menu; a second company's items never appear; claims queue present only if DEC-005a approved.
- New module (if DEC-004 OPT-A) has its own ACL, literal `_name`, `ondelete=` on every Many2one, manifest wiring checked by `scripts/check_module_wiring.py`.
- PR into Staging green via `make pr`; CTO-STATUS: ready-to-merge.

## ACTIVATION
Launch via `cto_mode.py launch-spec --cto-session <CTO session> --lane-repo cryptoxdog/IB-Odoo_19 --model <model> --tag lane:lane-d --tag campaign:ib-odoo-dashboard-command-centers`; pass `create_session` fields unchanged; this file's body is the task prompt. Start condition: see `CAMPAIGN_EXECUTION_BINDING.yaml` lanes[].
