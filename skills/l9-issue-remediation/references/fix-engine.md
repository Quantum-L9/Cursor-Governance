<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: fix_engine
tags: [issues, fix, verify, commit]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Fix Engine

Concurrent safe codebase fixes for one sticky cluster → local verify → one commit.

## Steps

1. Clone or open the **owning repo** worktree (never invent paths).
2. Implement the smallest change that removes the root cause.
3. Prefer shared contracts/tests that would fail if the audited bug returned.
4. Run every locally reproducible required gate for that repo (lint/type/test).
5. On fail: fix and re-run all (≤5 iterations). If a fix breaks a gate, revert that
   fix and defer with reason.
6. One conventional commit + push with trailer:

```text
Issue-Remediation-Cycle: {owner}/{repo}#{issue}/cycle-{N}
```

7. If a PR is needed or already open →
   [handoff-to-pr-remediation.md](handoff-to-pr-remediation.md).

## Forbidden

- Gate weakening, blanket suppressions, skipped tests
- Editing `.github/workflows/**` or branch protection
- Force-push / history rewrite
- Merging PRs from this skill
- Secret values in commits or issue comments
