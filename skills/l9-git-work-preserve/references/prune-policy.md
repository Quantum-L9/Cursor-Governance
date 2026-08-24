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

- receipt class `archive_ref` with **`redundancy_basis: patch_id`**
- `fetched: true` when the repo has a remote — redundancy judged against a stale
  baseline is not judged at all
- the tip SHA recorded, so `git branch <name> <sha>` restores it

**`content_superset` never authorises a delete.** Absorption fires while
`git cherry` still reports the commits novel — that disagreement is why it is
consulted — so a single added line that happens to exist somewhere upstream
classifies the ref `archive_ref` while its commit is genuinely unlanded. That is
a claim worth reporting and not a claim worth deleting on. Such refs are for
human review; if you conclude the work really did land, re-diagnose after the
fact or delete deliberately, but not on this evidence alone.

## `/ff` boundary

`/ff` runs `git branch -d` only. Anything safe-delete refuses is reported in
`needs_human[]` with its tip SHA and the exact `-D` command — it is never forced
on the user's behalf, and `--prune-superseded` marks intent without performing
the delete. Git's own merged-into-HEAD check stays the last line of defence.

## Never auto

- Force-push, hard-reset, admin-merge
- Stash drop (see `stash-deep-analysis.md`)
- Deleting a worktree with unique dirty paths
