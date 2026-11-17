---
name: "Audit findings: repair scanners and clear the 48 HIGH N+1 findings"
overview: "extended_audit_report.json (48 HIGH N_PLUS_ONE_QUERY) is live on origin/Staging, baselined but unreviewed. odoo_audit_report.json (3 HIGH INVALID_DEPENDS, one finding repeated) is a scanner defect. Build on a clean worktree off origin/Staging: fix the Odoo scanner, triage all 48 rows with evidence, fix scanner false positives, fix real per-record queries, prune baselines to exactly what remains, publish with make pr (full smoke)."
todos:
  - id: T0
    content: "Create clean worktree + branch from origin/Staging; prove zero dirt and 0/0 divergence"
    status: pending
    phase: setup
    depends_on: []
  - id: T1
    content: "Delete both gitignored reports (worktree and main clone); regenerate via run_baseline_gate.sh; confirm 48 HIGH + 3 HIGH snapshot matches this plan"
    status: pending
    phase: triage
    depends_on: [T0]
  - id: T2
    content: "Fix odoo_audit.py INVALID_DEPENDS (AST class index, dedupe per model/method/base_field); tests first; remove baseline entry 8bf7ef9ea67765ca"
    status: pending
    phase: scanner
    depends_on: [T1]
  - id: T3
    content: "Triage the 48 N_PLUS_ONE rows: REAL / SCANNER_FP / REAL_ACCEPT with file:line evidence (kept for the PR body)"
    status: pending
    phase: triage
    depends_on: [T1]
  - id: T4
    content: "Fix performance_audit.py for each SCANNER_FP class (candidate: document_sync.py:201); red/green fixtures; true per-record searches still flagged"
    status: pending
    phase: scanner
    depends_on: [T3]
  - id: T5
    content: "Group A (22 rows, 11 files): per-record code-uniqueness searches -> one batched query"
    status: pending
    phase: code
    depends_on: [T3]
  - id: T6
    content: "Group B (8 rows): per-record count computes -> batched read"
    status: pending
    phase: code
    depends_on: [T3]
  - id: T7
    content: "Group C (17 rows): create/search inside loops -> create(list) / hoisted search"
    status: pending
    phase: code
    depends_on: [T3]
  - id: T8
    content: "Bump __manifest__.py version of every module touched in T5-T7; ruff format manifests"
    status: pending
    phase: code
    depends_on: [T5, T6, T7]
  - id: T9
    content: "Rewrite extended baseline to exactly the surviving HIGH set (each with review:); prove new 0 AND stale 0 for both baselines"
    status: pending
    phase: verify
    depends_on: [T2, T4, T8]
  - id: T10
    content: "Local gates: ruff, pre-commit, wiring, scoped pytest, make test-module per touched module, make update m=<module> per bumped module"
    status: pending
    phase: verify
    depends_on: [T9]
  - id: T11
    content: "make commit; git status clean; remote-feedback gate clear; PR_STACK=auto PR_REMEDIATE=0 make pr (attached, full smoke); show PR URL"
    status: pending
    phase: publish
    depends_on: [T10]
isProject: false
---

# PLAN: Audit findings: repair scanners and clear the 48 HIGH N+1 findings

> Mode: `cursor-build` · kind: simple · status: current · Handoff: user presses **Build**; publish is `PR_STACK=auto PR_REMEDIATE=0 make pr`; the PR URL is shown at the end.
> Validation status: **not machine-validated.** `run_plan_pipeline.py`, `write_plan_run.py` and `ops/hooks/plan_memory_prefetch.py` do not exist in the installed governance checkout, so no architect run file, prefetch receipt or section receipt exists. GAR is waived: architecture is settled (existing scanners plus the per-finding baseline). Reported, not silently worked around.

## 1. Verified ground truth

Re-verified against a `git archive origin/Staging` snapshot (not the working branch), 2026-11-05:

| Fact | Evidence |
|---|---|
| Staging produces the same findings as the clone I first scanned | `run_baseline_gate.sh` on the snapshot: Extended 48 HIGH, Known 48, New 0; Comprehensive 3 HIGH, Known 3, New 0. The same 48 `(file, line)` pairs. The current branch's baseline files differ from Staging, so T1 still re-derives everything inside the new worktree. |
| Both reports are untracked and gitignored | `.gitignore:53-54`. Deleting or regenerating them cannot dirty a tree. |
| Extended report is 113 findings | 48 HIGH `N_PLUS_ONE_QUERY`, 31 MODERATE `UNBOUNDED_SEARCH`, 34 MODERATE `UNJUSTIFIED_SUDO`. Only HIGH is gated. |
| The 48 are baselined, not stale | live fingerprints = baseline fingerprints = 48. The scanner exit 1 is by design; the baseline diff is the verdict. |
| None of the 48 baseline entries has a `review:` reason | bulk-accepted debt (2026-10-10) |
| Odoo report: 3 identical rows | `plasticos_documents/models/transaction_docs.py:62`, `document_ids`. Baseline entry `8bf7ef9ea67765ca` already calls it a false positive. |
| Root cause | `scan_model_fields` (`odoo_audit.py` ~L170-185) files every field of a no-`_name` file under the first `_inherit` regex hit, here `account.move`. `check_compute_depends` (~L593-620) is regex-based and emits one row per dotted path. The AST `model_classes` index (~L255-300) is already correct and should be the source of truth. |
| Fingerprints ignore line numbers but include the flagged source line | `baseline_utils.py` L32-35. Rewriting a flagged line **changes its fingerprint**: the old baseline entry becomes stale and any residual finding looks new. Every code fix therefore needs the baseline pruned in the same change. The gate checks only "new"; stale entries are not detected by it, so T9 adds an explicit stale check. |
| Dirt in the main clone | untracked `docs/campaigns/11-03-26/odoo test failures/`; branch `fix/crm-material-call-note-filter` carries open PR #383. Do not build there. |
| Parallel unmerged branches own overlapping files | `fix/material-profile-count-batch` (`plasticos_material_profile/models/material_profile.py`), `fix/transaction-uniqueness-prefetch` (`plasticos_transaction/models/transaction.py`). Do not edit either file. |

Corrected row map (22 + 8 + 17 + 1 = 48):

| Group | Rows | Files |
|---|---|---|
| A code-uniqueness | 22 | `facility_profile`: `partner_type`, `equipment_type`. `material_profile`: `filler_type`, `process_type`, `source_type`, `material_attribute`, `packaging_type`, `material_form`, `polymer`, `material_color`. `claims`: `claim.py` 236/245. Each file has a `create` row and a `write` row. |
| B counts | 8 | `offer.py:195`, `crm_lead.py:128`, `material_profile/res_partner.py:51`, `intake/res_partner_intake.py:27`, `intake/material_profile_intake.py:27`, `claims/claim.py:425`, `crm_bridge/material_profile.py:91`, `offer/offer_price_bridge.py:27` |
| C create/search in loop | 17 | `plasticos_automation` (one module, 7 files, 8 rows: `sale_approval`, `stock_picking_automation`, `purchase_order_automation`, `stock_reorder_alert` x2, `load_automation`, `contract_renewal` x2). `enrichment_run.py` x3. `sale_inherit.py` x2. `transaction_import_service.py:185`. `freight_quote.py:636`. `rate_memory.py:75`. `facility_profile/res_partner.py:371` |
| Likely FP | 1 | `document_sync.py:201` (id-keyset pagination, one search per 200 documents) |

Modules touched by code: `plasticos_facility_profile`, `plasticos_material_profile`, `plasticos_claims`, `plasticos_offer`, `plasticos_crm_bridge`, `plasticos_intake`, `plasticos_automation`, `plasticos_enrichment`, `plasticos_transaction`, `plasticos_logistics` (10, subject to T3). `plasticos_documents_native` changes only if T3 contradicts the FP call.

Out of scope: the 65 MODERATE findings, `pipeline_v2.py`, any new field/model/cron/ACL row, any `res.partner` schema change, `plasticos_base`, `.cursor-commands`, `AGENTS.md` edits (append-only; add a dated correction only if gated counts in its tables change).

## 2. Worktree (T0) — fail-closed

```bash
cd "/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19"
git fetch origin Staging
git rev-list --left-right --count Staging...origin/Staging      # must print "0 0"; otherwise STOP
git worktree add "../IB-Odoo_19-audit-repair" -b fix/audit-scanner-n1-repair origin/Staging
cd "../IB-Odoo_19-audit-repair"
test -z "$(git status --porcelain)" && git rev-parse --abbrev-ref HEAD   # must be fix/audit-scanner-n1-repair
git rev-parse HEAD origin/Staging                                         # identical SHAs
```

Branch from `origin/Staging`, never local `Staging` or #383's branch. PR base is `Staging`; not stacked. Re-run `test -z "$(git status --porcelain)"` before every commit and immediately before `make pr`. Any output, including a stray untracked file, is a STOP: remove it or commit it deliberately. Do not remove the worktree until the PR is merged.

## 3. Reports (T1)

1. `rm -f odoo_audit_report.json extended_audit_report.json` in the new worktree, and in the main clone (disposable, gitignored).
2. Regenerate only via `bash scripts/audit/run_baseline_gate.sh`, the script `make audit-baseline` and `ci.yml` both call. Do not run scanners with ad-hoc flags: `run_all_audits.py --help` treats `--help` as a path and writes a report.
3. Assert the snapshot: Extended 48 HIGH / Comprehensive 3 HIGH. If it differs, STOP and re-plan; the row map above is then wrong.

## 4. Scanner repair (T2, T4) — fix the scanner, not the baseline

**T2 `scripts/audit/odoo_audit.py`**
- Write the failing tests first in `tests/test_odoo_audit_field_attribution.py`: (a) bridge file whose first class inherits `account.move` and second extends `plasticos.transaction` with `document_ids` gives no finding; (b) a depends path naming a genuinely absent field still gives exactly one HIGH; (c) three dotted paths on one base field give one row; (d) a field defined in another module's `_inherit` that is in the depends closure resolves.
- `check_compute_depends`: resolve valid fields from `model_classes` (same model after `_inherit` resolution, restricted to the module's depends closure via `_depends_closure`). Stop using the first-`_inherit` regex attribution for this check.
- Emit one finding per `(model, compute_method, base_field)`.
- Same change: delete baseline entry `8bf7ef9ea67765ca`. Do not widen any ignore list or add a special case.
- Acceptance: fresh `odoo_audit_report.json` has 0 `INVALID_DEPENDS`; no new CRITICAL/HIGH of any type appears (the scanner change must not expose previously hidden real findings; if it does, each is triaged, not baselined by default).

**T4 `scripts/audit/performance_audit.py`** — only for rows T3 labels SCANNER_FP
- Candidate `document_sync.py:201`: recognise a loop whose own cursor (last id of the previous page) advances the search domain and whose search is `limit=`-bounded.
- Fixtures in `tests/test_audit_n_plus_one.py`: the pagination shape is not flagged; a per-record `search` inside `for rec in self` with a `limit` is still flagged; a loop where the cursor is not derived from the previous iteration is still flagged.
- If T3 finds no FP, T4 is recorded as a no-op in the PR body. Never edit scanners to silence a real finding.

## 5. Triage (T3) — one evidence-backed verdict per row

Read each function. Verdicts:
- `REAL`: query or create runs once per record in a recordset that can have many records.
- `SCANNER_FP`: bounded loop, pagination, or already set-based.
- `REAL_ACCEPT`: real, but the call path is single-record in practice (for example a `create` of one vals dict). Requires a one-line reason, which becomes the baseline `review:` text. At most these may stay baselined.

Hints already found (confirm, do not assume):
- `partner_type.py` `create` loops over `vals_list` (per vals, not per record); `write` loops `for record in self` with one fixed `code`: if `len(self) > 1` that write is always a duplicate, so one query plus a length check is sufficient. A DB-level unique constraint already exists on these models, so the Python check exists for the friendly message; keep the message byte-identical.
- `intake_count` (`res_partner_intake.py`) is a non-stored compute with `@api.depends()` and an OR domain on `partner_id`/`facility_id`: one `_read_group` cannot express the OR per record, so use two grouped reads (or one `search` over the union and a Python tally) and sum.

## 6. Code fixes (T5-T7) — smallest verified change per module

- A: one batched read per `create`/`write` call over the code set, compare in Python, preserve error text and which record raises first.
- B: grouped read over the whole recordset, assign every record (default 0 for absent keys, also for `NewId`/unsaved records, as in the sibling branch's tests). `@api.depends` unchanged.
- C: collect vals and `create(list)` once; hoist existence/count searches before the loop as one `in` search; preserve log order, sequence assignment, sudo and its inline justification, and per-record exception behaviour (a failure must not newly roll back unrelated records unless the old code already did).
- No new fields, models, crons, ACL rows, or `res.partner` schema change. `res_partner.py` edits are query-only.
- Imports remain lazy where cross-addon. Every `fields.Many2one` untouched. Logging stays lazy `%s`.
- Tests per changed module (`TransactionCase`, `setUpClass` fixtures, `type='consu'`): behaviour unchanged, and a query-count assertion proving it does not grow with record count (`assertQueryCount` or a counted-patch of the flagged ORM method; avoid brittle absolute totals). A fix with no test is not done.
- Version bump rule: bump `__manifest__.py` `19.0.X.Y.Z` of each changed module (no migrations folder; there is no data or schema change). Tests-only changes get no bump. `ruff format` each manifest. Upgrade only bumped modules: `make update m=<module>` (never `update-all`).

## 7. Baseline (T9) — exact, not additive

- Rewrite `ci/baselines/extended_audit_baseline.json` so entries equal the surviving HIGH fingerprints exactly; each carries `review:`. Update its `_verified` date and `_root_cause`.
- Stale check (the gate does not do it): compare baseline fingerprints with fresh-report fingerprints for both baselines; require `baseline - live = {}` and `live - baseline = {}`.
- `bash scripts/audit/run_baseline_gate.sh` must end "No audit baseline regression"; `tests/test_audit_baseline_gate.py`, `test_audit_n_plus_one.py`, `test_odoo_audit_field_attribution.py` pass.

## 8. Verification (T10) — success properties and proofs

| Id | Property | Proof |
|---|---|---|
| P1 | Worktree clean at start, every commit, and publish | `git status --porcelain` empty each time |
| P2 | Odoo audit: no `document_ids` false positive, no duplicate rows, no new hidden findings | fresh report; regression tests |
| P3 | Extended audit: new 0, stale 0; every remaining HIGH has `review:` | gate + stale check |
| P4 | Behaviour preserved in each touched module | `make test-module m=<module>`, attached, 600000 ms, one at a time, fixture `odoo_test_tpl_ee_c9e8a81f52f23680` only |
| P5 | Modules upgrade | `make update m=<module>` per bumped module; install-smoke inside `make pr` |
| P6 | Lint/CI contract | `ruff check --fix . && ruff format .`, `pre-commit run --all-files`, `python3 scripts/check_module_wiring.py` |
| P7 | No forbidden surface touched | `git diff --name-only origin/Staging` contains none of: `pipeline_v2.py`, `plasticos_base/`, `material_profile.py`, `transaction.py` (parallel-branch owners), `.cursor-commands`, `AGENTS.md` |

## 9. Risks and stop conditions

- Breadth: about 10 modules. If T3 yields more than 8 modules of REAL fixes or more than about 600 changed lines, split into stacked PRs: root PR = T2, T4 and the baseline prune; then A, B, C via `make pr base=<parent branch>`; merge each parent into Staging first.
- `create(list)` side-effect order (sequences, mail tracking, logs): covered by P4 tests; if a fix changes observable order, mark `REAL_ACCEPT` instead.
- T2 may expose real findings the old regex hid: triage them; do not baseline reflexively.
- Fixture refusal (image, Postgres, roster, Enterprise drift): the only recovery is `make test-env-rebuild`. Do not set `TEST_ENV_ALLOW_NEW_TEMPLATE`, use another database, or `make pr-nosmoke`.
- Shell handoff kill (`Terminated: 15`): rerun that exact command once, still attached, 600000 ms wait.
- A failing remote-feedback gate must be resolved before `make pr`.
- Any P-check failing: fix at the cause, never loosen a scanner or baseline to pass.

## 10. Rollback

Source, test and baseline edits only: no data migration, no schema change, no column/table drops. Revert the PR (or the affected stacked PR); scanners and baselines revert with it.

## 11. Execute via Cursor Build

1. Press **Build**. Run T0; STOP unless clean and `0 0`.
2. T1 to T10 in dependency order, tests before fixes (T2, T4 red first). Commit with `make commit` (conventional messages: `fix(audit): ...`, `fix(<module>): batch ...`); re-verify P1 after each commit.
3. Publish, attached with a 600000 ms wait, nothing else running: `PR_STACK=auto PR_REMEDIATE=0 make pr` (full gate and smoke; `scripts/pr_check_scope.py` selects audit, audit-baseline and install-smoke because addon load inputs changed). Never raw `git push`, `make push`, or the API.
4. Display the opened PR URL. Merge into Staging is a human decision.
