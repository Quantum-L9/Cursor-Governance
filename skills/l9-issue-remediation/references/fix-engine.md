<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: fix_engine
tags: [issues, fix, verify, commit]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Fix Engine

Concurrent safe codebase fixes for one sticky cluster → local verify → one commit.

## Lesson Recall (before inventing a fix)

Before proposing a new patch, search the governance learning corpus for a matching known pattern:

```bash
rg -i "<error class or key phrase>" \
  "$HOME/.cursor-governance/learning/failures/repeated-mistakes.md" \
  "$HOME/.cursor-governance/learning/patterns/quick-fixes.md"
```

- If a match is found, apply that template (smallest diff that implements it).
- If no match, proceed with the smallest original fix.
- Do **not** auto-apply unmatched regex patches.
- Do **not** write `memory_log.json` or `session_status.md` (retired; Graphiti is session SSOT).

## Steps

1. Clone or open the **owning repo** worktree (never invent paths).
2. **Lesson recall** — run the search above; apply a matching template only when the current failure matches.
3. Implement the smallest change that removes the root cause.
4. Prefer shared contracts/tests that would fail if the audited bug returned.
5. Run every locally reproducible required gate for that repo (lint/type/test).
6. On fail: fix and re-run all (≤5 iterations). If a fix breaks a gate, revert that
   fix and defer with reason.
7. One conventional commit + push with trailer:

```text
Issue-Remediation-Cycle: {owner}/{repo}#{issue}/cycle-{N}
```

8. If a PR is needed or already open →
   [handoff-to-pr-remediation.md](handoff-to-pr-remediation.md).

## Forbidden

- Gate weakening, blanket suppressions, skipped tests
- Editing `.github/workflows/**` or branch protection
- Force-push / history rewrite
- Merging PRs from this skill
- Secret values in commits or issue comments
