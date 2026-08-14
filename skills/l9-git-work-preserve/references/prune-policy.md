# Prune policy

## Default: report-only (`prune-propose`)

Emit candidates with:

- diagnosis receipt hash
- tip SHA (for reflog recovery)
- exact commands for human review
- whether remote delete is requested (default **no**)

## `prune-execute`

Requires **all** of:

1. Explicit user authorization in this turn
2. Env `L9_GIT_PRUNE_AUTHORIZED=<non-empty reason>`
3. Diagnosis receipt with class `prune_candidate` and confidence `high`
4. Tip SHA recorded in receipt before delete

Local branch delete only by default. Remote `git push --delete` requires the reason to include `remote_delete=1` and a second explicit user confirmation.

## Never auto

- Force-push, hard-reset, admin-merge
- Stash drop (see `stash-deep-analysis.md`)
- Deleting a worktree with unique dirty paths
