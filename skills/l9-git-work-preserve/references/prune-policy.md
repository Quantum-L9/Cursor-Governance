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

## `archive_ref`

A redundant branch is not a merged branch, and the difference decides what can
delete it. `prune_candidate` means zero commits ahead — `git branch -d` removes
it, because every commit is reachable from HEAD. `archive_ref` means the *work*
landed while the *commits* did not: reimplemented, squashed, or cherry-picked
onto a different parent. Its tip is not an ancestor, so **`git branch -d`
refuses it**, correctly.

Clearing one therefore needs `git branch -D`, which is force-delete, and that
requires everything `prune-execute` requires plus:

- receipt class `archive_ref` with a non-empty `redundancy_basis`
- `fetched: true` when the repo has a remote — redundancy judged against a stale
  baseline is not judged at all
- the tip SHA recorded, so `git branch <name> <sha>` restores it

Weigh the basis. `patch_id` is exact. `content_superset` is a heuristic that a
rename defeats, so it warrants a look at the receipt's paths before forcing.

## `/ff` boundary

`/ff` runs `git branch -d` only. Anything safe-delete refuses is reported in
`needs_human[]` with its tip SHA and the exact `-D` command — it is never forced
on the user's behalf, and `--prune-superseded` marks intent without performing
the delete. Git's own merged-into-HEAD check stays the last line of defence.

## Never auto

- Force-push, hard-reset, admin-merge
- Stash drop (see `stash-deep-analysis.md`)
- Deleting a worktree with unique dirty paths
