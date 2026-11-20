---
name: Fix pr-check gate errors
overview: 'Fix the three issues blocking the `fix/crm-material-call-note-filter` branch:
  prune 7 stale audit baseline entries (housekeeping) and resolve the open Codex PR
  review thread that is the actual gate blocker. The XML module-ref issue shown in
  screenshots is already fixed by recent commits.'
todos:
- id: prune-odoo-audit-baseline
  content: Remove fingerprint 9276c6434ccf90a0 from ci/baselines/odoo_audit_baseline.json
    (1 stale INVALID_CONSTRAINT_FIELD entry for commission_override_pct)
  status: completed
- id: prune-extended-audit-baseline
  content: Remove 6 stale N_PLUS_ONE_QUERY fingerprints from ci/baselines/extended_audit_baseline.json
    (39bbc2ad, 4a48e73c, f0103ed5, ade38a01, ad74fae1, 8115fd09)
  status: completed
- id: commit-baseline-pruning
  content: 'git add + git commit: ''chore(ci): prune 7 stale baseline entries (commission_override_pct
    fixed; 6 N+1 refactored)'''
  status: completed
- id: resolve-codex-thread
  content: 'Resolve the open Codex inline review thread at vanillasoft_material_mapping.csv:214
    on PR #383 via GitHub UI (''Resolve conversation'') or by posting ''@codex review''
    comment to trigger a re-review'
  status: completed
- id: verify-and-push
  content: Run make pr-check to confirm all gates pass (no REAL_BUG, stale entries
    gone), then make pr to push
  status: completed
isProject: false
built: true
status: built
---

# Fix pr-check Gate Errors

## Diagnosis

Five screenshots show three distinct issues from `make pr-check` on branch `fix/crm-material-call-note-filter` (PR #383):

### Issue 1 — XML module-ref vs depends (HIGH: 1) [Screenshots 3.15.22, 3.16.57]
- **Status: ALREADY FIXED** by commits 337d334a / e245d6c0 / 2e738061
- `python3 ci/check_xml_module_ref_deps.py` now returns `✅ XML module refs match declared depends`
- No code change needed

### Issue 2 — Stale baseline entries [Screenshots 3.15.13, 3.15.54]
- **Non-blocking** (CI passes, gate is green), but should be pruned as housekeeping
- `ci/baselines/odoo_audit_baseline.json`: **1 stale entry** — fingerprint `9276c6434ccf90a0`
  - `INVALID_CONSTRAINT_FIELD` for `commission_override_pct` in `plasticos_transaction/models/transaction.py:497`
  - Previously a known false positive; scanner no longer flags it
- `ci/baselines/extended_audit_baseline.json`: **6 stale entries** — all `N_PLUS_ONE_QUERY` for code that was refactored
  - `39bbc2ad6a8906c4` — `plasticos_buyer_match_engine/models/intake_extension.py:70`
  - `4a48e73c9623fd94` — `plasticos_crm_bridge/models/crm_lead.py:198`
  - `f0103ed5d8f56685` — `plasticos_logistics/models/load.py:1224`
  - `ade38a010fa17022` — `plasticos_material_profile/models/material_profile.py:344`
  - `ad74fae19f6f9ddc` — `plasticos_material_profile/models/material_profile.py:455`
  - `8115fd099193e5b4` — `plasticos_material_profile/models/material_profile.py:467`

### Issue 3 — Codex REAL_BUG (BLOCKER) [pr-check remote gate]
- `scripts/pr_autopilot.py` reads the open Codex inline review comment at `vanillasoft_material_mapping.csv:214`
- Comment says "Synchronize the note filter with the mapping" — **the fix is already in commit 2e738061** ("sync `_CRM_CALL_NOTE_PHRASES` with all 175 `note_not_material` rows")
- The Codex review thread is still OPEN on GitHub (not resolved), so pr-autopilot classifies it as REAL_BUG
- Gate fails: `❌ Remote PR gate FAILED: 1 REAL_BUG signal(s)`

## Files to Change

- [`ci/baselines/odoo_audit_baseline.json`](ci/baselines/odoo_audit_baseline.json) — remove 1 stale entry
- [`ci/baselines/extended_audit_baseline.json`](ci/baselines/extended_audit_baseline.json) — remove 6 stale entries

## Execution Steps

### Step 1 — Prune stale entries from `odoo_audit_baseline.json`
Remove the entry with fingerprint `9276c6434ccf90a0` from the `entries` array in [`ci/baselines/odoo_audit_baseline.json`](ci/baselines/odoo_audit_baseline.json). Keep the `8bf7ef9ea67765ca` entry (still active).

### Step 2 — Prune 6 stale entries from `extended_audit_baseline.json`
Remove the 6 entries with fingerprints `39bbc2ad6a8906c4`, `4a48e73c9623fd94`, `f0103ed5d8f56685`, `ade38a010fa17022`, `ad74fae19f6f9ddc`, `8115fd099193e5b4` from [`ci/baselines/extended_audit_baseline.json`](ci/baselines/extended_audit_baseline.json). No version bump — these are CI infrastructure files, not Odoo addon files.

### Step 3 — Commit the baseline pruning
```bash
git add ci/baselines/odoo_audit_baseline.json ci/baselines/extended_audit_baseline.json
git commit -m "chore(ci): prune 7 stale baseline entries (commission_override_pct fixed; 6 N+1 refactored)"
```

### Step 4 — Resolve the Codex PR review thread on GitHub
The Codex inline comment at CSV:214 on PR #383 must be marked resolved. Two equivalent options:
- **Option A (GitHub UI):** Open the PR, navigate to the Files Changed tab, find the Codex comment at `vanillasoft_material_mapping.csv:214`, click "Resolve conversation"
- **Option B (gh CLI/API):** Use GitHub GraphQL `resolveReviewThread` mutation with the thread node ID, OR post `@codex review` as a PR comment to trigger a re-review (Codex will see commit 2e738061 and may auto-resolve)

### Step 5 — Verify and push
```bash
make pr-check   # all gates must pass (no REAL_BUG, no stale noise)
make pr         # push branch + verify PR #383
```

## Key Constraints
- No version bump needed — `ci/baselines/` are not Odoo addon files
- No `make update` needed
- The XML module-ref issue shown in screenshots is already fixed — do not re-open
- Run `ruff format` after edits if any Python files touched (none planned here)
- Only remove fingerprints from baseline arrays; do not restructure the JSON schema

## Build evidence (auto)

- detected_at: `2026-11-05T20:41:32Z`
- conversation_id: `7d8f055b-b069-449c-8185-d1e9a7f8788a`
- generation_id: `4699b827-dcff-4844-ae4c-cecef66047eb`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/7d8f055b-b069-449c-8185-d1e9a7f8788a/7d8f055b-b069-449c-8185-d1e9a7f8788a.jsonl`
- todos at build time:
- `prune-odoo-audit-baseline`: completed
- `prune-extended-audit-baseline`: completed
- `commit-baseline-pruning`: completed
- `resolve-codex-thread`: completed
- `verify-and-push`: completed
