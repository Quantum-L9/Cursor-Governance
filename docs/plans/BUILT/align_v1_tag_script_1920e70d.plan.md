---
name: Align v1 tag script
overview: "Residual work only. PR #11 and published @v1/@v1.0.0 tags already exist. Align Quantum-L9/.github ops/tag-v1.sh EXPECTED_SHA to live tip 978cf94, fix the obsolete main==EXPECTED_SHA guard, re-run verify, footnote AGENTS.md §6. Skip retagging and all PR #11 rebuilds."
todos:
  - id: residual-confirm-tip
    content: "Record evidence that published @v1/@v1.0.0 → 978cf94 is intentional (PR #44 + docs/v1-compatibility.md); no retag"
    status: completed
  - id: residual-align-sha
    content: In Quantum-L9/.github ops/tag-v1.sh set EXPECTED_SHA to 978cf948133fa4d9cd6b78ecbb383295869cb70f; rewrite provenance; replace origin/main==EXPECTED_SHA with tag-consistency + no-retag guards
    status: completed
  - id: residual-verify
    content: Run ops/verify-v1-anchor.sh after EXPECTED_SHA change; require PASS on workflow_call kernels at 978cf94
    status: completed
  - id: residual-agents
    content: Footnote l9-ci-core AGENTS.md §6 Legacy @v1 with live tip SHA 978cf94 and one-line provenance
    status: completed
  - id: residual-pr
    content: Open PR on Quantum-L9/.github for script align only; human merges; do not run tag creation/push
    status: completed
isProject: false
---

# Align v1 tag script to published tip (residual)

## Objective

Make `Quantum-L9/.github` `ops/tag-v1.sh` match the already-published `@v1` / `@v1.0.0` tip — without recreating tags or redoing [PR #11](https://github.com/Quantum-L9/.github/pull/11).

## Decisions (locked)

- **Published tip is authoritative:** `978cf948133fa4d9cd6b78ecbb383295869cb70f` (PR #44 v1-compat kernels).
- **Align** `EXPECTED_SHA` to that tip (not document-only drift).
- **Include** [`AGENTS.md`](AGENTS.md) §6 footnote in `l9-ci-core`.
- **Skip** PR #11 deliverables and any create/force-push tag step.

## Already done (do not rebuild)

- PR #11 merged: bad `2b330a5` → `2a3270be5`, plus `ops/verify-v1-anchor.sh`.
- Tags exist: `v1.0.0` and `v1` peel to `978cf94…`.
- Intentional tip: PR #44 + [`docs/v1-compatibility.md`](docs/v1-compatibility.md) tag policy; `978cf94` is an ancestor of current `main`; kernel `uses:` at that tip are 40-char SHA pins.

## Residual defect

`ops/tag-v1.sh` still pins `EXPECTED_SHA=2a3270be5…` (not an ancestor of `978cf94`) and asserts `origin/main == EXPECTED_SHA`, which cannot succeed for a historical freeze and leaves a dangerous create/force-push path if someone “fixes” main temporarily.

`verify-v1-anchor.sh` needs no behavior change — it parses `EXPECTED_SHA` from `tag-v1.sh`.

## Scope

**In:** confirm tip intentional (evidence in PR body); edit `.github` `ops/tag-v1.sh`; run verify PASS; footnote `AGENTS.md` §6; open new `.github` PR.

**Out:** rebuild PR #11; create/move/delete tags; PyPI; kernel body edits; advancing moving `v1` to newer main.

## Implementation

### 1. Confirm tip (no tag mutation)

PR body cites: peeled tags → `978cf94`; PR #44 purpose; `docs/v1-compatibility.md`; SHA-pin spot-check at tip.

### 2. Align `ops/tag-v1.sh` (`Quantum-L9/.github`)

- Set `EXPECTED_SHA="978cf948133fa4d9cd6b78ecbb383295869cb70f"`.
- Rewrite Anchor comment: published `@v1.0.0` tip (PR #44); supersedes `2a3270be5…`.
- Replace `fetch origin/main` + equality assert with:
  - Fetch/ensure `EXPECTED_SHA` reachable.
  - If `v1.0.0` / `v1` exist and peel to `EXPECTED_SHA` → print match, **exit 0, no push**.
  - If tags exist at a different SHA → fail closed (never force-update `v1.0.0`).
  - Keep verify-first prerequisite; do not require `main == EXPECTED_SHA`.

### 3. Re-run verify

```bash
ops/verify-v1-anchor.sh   # expect PASS at 978cf94
```

Do not run tag create/push.

### 4. `AGENTS.md` §6 footnote (`l9-ci-core`)

One short note: live tip `978cf94…` (PR #44); pointer to `docs/v1-compatibility.md`; tag scripts live in `Quantum-L9/.github` `ops/`.

### 5. PRs

- New PR on `Quantum-L9/.github` for script align only.
- `AGENTS.md` change in this repo (separate PR/commit as needed).
- Human merges; **do not cut or push tags**.

## Success criteria

1. `EXPECTED_SHA` == `978cf948133fa4d9cd6b78ecbb383295869cb70f`
2. `verify-v1-anchor.sh` exits 0
3. No `origin/main == EXPECTED_SHA` guard
4. Matching existing tags → idempotent exit 0; mismatched tags → non-zero, no retag
5. `AGENTS.md` §6 names the live tip
6. No new tags created during execution

## Stress / rollback

- Retag risk mitigated by idempotent match + fail-closed mismatch + execution skip of push.
- Rollback = revert the `.github` / `AGENTS.md` PRs; tags untouched.
