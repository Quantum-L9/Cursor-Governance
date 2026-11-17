---
name: Claims query batching
overview: Remove the three HIGH N+1 findings in plasticos_claims/models/claim.py by replacing per-record searches with one query each, then publish that change from a new branch off Staging.
todos:
  - id: branch
    content: New branch from Staging; leave the current feature-branch dirty files untouched
    status: pending
  - id: batch-queries
    content: Move the three claim.py searches out of their loops and keep the duplicate-name ValidationError
    status: pending
  - id: manifest-baseline-test
    content: Bump plasticos_claims to 19.0.1.1.6, prune the three baseline rows, add the duplicate-name test
    status: pending
  - id: prove-and-pr
    content: Ruff, audit-baseline, make test-module m=plasticos_claims, then make pr into Staging
    status: pending
isProject: false
---

# Batch the three claim.py queries

The extended audit (`extended_audit_report.json`, gitignored) flags three HIGH `N_PLUS_ONE_QUERY` hits in [`plasticos_claims/models/claim.py`](plasticos_claims/models/claim.py). The scanner in [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py) flags any `search` / `search_count` call whose AST node sits inside a `for` loop. Moving each query out of the loop clears the finding. Do not special-case the scanner.

Current checkout is `fix/material-form-grade-normalizer` with unrelated dirty files (`plasticos_documents`, `plasticos_logistics`, untracked campaign docs). Leave those untouched. Local `Staging` matches `origin/Staging`.

## The three findings

1. **create** (line 236) — `self.search([("name", "=", name)], limit=1)` inside `for vals in vals_list`.
2. **write** (line 245) — the same name lookup inside `for record in self`.
3. **SLA cron** (line 425) — `mail.activity.search_count(...)` inside `for claim in open_claims`.

`_unique_name = models.Constraint("unique(name)", ...)` already exists (line 218). The Python checks only exist to raise `ValidationError: Claim reference '{name}' already exists.` before the database error. Keep that message.

## Code change

**create** — assign sequences in the existing loop (that call is not flagged). Then, outside any loop:

- Detect a repeated name inside `vals_list` in memory.
- One `self.search([("name", "in", claimed)], limit=max(len(claimed), 1))` for names already stored. `max(..., 1)` is a proven positive limit, so this does not add a gated unbounded-search finding. Skip the search when `claimed` is empty.
- Raise the same `ValidationError` on the first collision.

**write** — one search before the archived-state loop:

```python
duplicate = self.search([("name", "=", name), ("id", "not in", self.ids)], limit=1)
```

Raise when `duplicate` is set, or when `len(self) > 1` (one name written onto several claims cannot satisfy `unique(name)`). A single-record rename keeps today's behavior: another claim with that name is rejected; rewriting a claim's own name is allowed.

**`_cron_check_sla`** — before the reminder loop, one search:

```python
("res_model", "=", "plasticos.claim"),
("res_id", "in", open_claims.ids),
("date_deadline", "=", fields.Date.today()),
```

`res_id in <ids>` is an identity bound, so the search stays outside the HIGH unbounded-search gate. Build a `(res_id, summary)` set and skip claims already reminded today. Leave `action_escalate()` and `_create_reminder_activity()` as they are; they are not the flagged calls. Reminder idempotency in [`plasticos_claims/tests/test_cron_idempotency.py`](plasticos_claims/tests/test_cron_idempotency.py) (`test_claim_sla_in_domain`) must still see exactly one activity after two cron runs.

## Manifest, baseline, tests

- Bump [`plasticos_claims/__manifest__.py`](plasticos_claims/__manifest__.py) `19.0.1.1.5` → `19.0.1.1.6` (runtime Python change; do not ask). No migration: no schema change.
- Prune the three `plasticos_claims/models/claim.py` rows from [`ci/baselines/extended_audit_baseline.json`](ci/baselines/extended_audit_baseline.json) (`d813c0ae011298e3`, `04f80cbf17344749`, `0530bdec0d6c3289`). Stale rows do not fail CI; removing them keeps the allowlist honest. Add one sentence to `_root_cause`. Do not edit `performance_audit.py`.
- Add one constraint test on `TestClaimConstraintsConsolidated` in [`plasticos_claims/tests/test_constraints_onchanges.py`](plasticos_claims/tests/test_constraints_onchanges.py): a second claim created with an explicit duplicate `name` raises `ValidationError`.

## Proof and publication

Work on a new branch from `Staging` (for example `fix/claims-query-batching`). Do not stack on the current feature branch.

- `ruff check` and `ruff format` on the touched Python files.
- Re-run the extended audit and `scripts/audit/check_baseline.py` against `ci/baselines/extended_audit_baseline.json` (`--severities HIGH`). The three claim lines must be gone, and the diff must show no new HIGH finding.
- `make test-module m=plasticos_claims` on the pinned Docker fixture (`config/test_env_fixture.conf`).
- Commit, then `make pr` so the pull request targets `Staging`. Return the PR URL. Do not `git push` and do not `make update-all`.
