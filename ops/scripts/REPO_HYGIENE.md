# Repo hygiene

`ops/scripts/repo_hygiene.py` deletes local git residue whose content already
landed, and reports — loudly — the residue whose content did not.

It exists because the residue is decidable. Whether a branch is spent, whether a
worktree still holds work, and whether there are untracked files are all
questions git can answer, so none of them should ever be asked of a human.

## Running it

```bash
python3 ops/scripts/repo_hygiene.py                      # report, changes nothing
python3 ops/scripts/repo_hygiene.py --apply              # perform the safe deletions
python3 ops/scripts/repo_hygiene.py --apply --json       # receipt for automation
python3 ops/scripts/repo_hygiene.py --assert-origin Quantum-L9/Cursor-Governance
```

It runs automatically at `sessionEnd` via
`ops/hooks/session_end_repo_hygiene.sh`, last in the chain so that
`governance-backup.sh` has already committed and pushed. Receipts land in
`<workspace>/.l9/hygiene/`; the log is `~/.cursor-governance/hygiene.log`.
Kill switch: `L9_REPO_HYGIENE=0`. Report-only: `L9_REPO_HYGIENE_MODE=--report`.

## Why deletion is safe here

Every delete is preceded by a ref under `refs/l9/preserved/`. Refs are not
subject to reflog expiry, so a tip stays reachable indefinitely:

```bash
git branch recovered refs/l9/preserved/branch/20260817T203000Z-feat-thing
git stash apply refs/l9/preserved/stash/20260817T203000Z-wip
```

That is what makes the automatic answer and the safe answer the same answer.

## How a branch is judged

Ancestry alone cannot decide this. A squash merge lands the content while
leaving the branch's commits unreachable from `main`, so `git branch --merged`
reports a fully-landed branch as unmerged. The deciding test is instead: do all
the paths this branch touched already match `origin/main`?

| status | meaning | action |
|---|---|---|
| `absorbed` | no unique commits, or every touched path matches main | delete |
| `merged` | same, corroborated by a MERGED pull request | delete |
| `open_pr` | pull request still open | keep |
| `unmerged_no_pr` | unique commits, never proposed | keep |
| `closed_unlanded` | PR closed, commits are **not** in main | keep + report |
| `reused_after_merge` | PR merged, but later commits on the same branch name are **not** in main | keep + report |
| `protected` | `main`, `master`, `campaign/*` | never touched |

The last two are the point of the tool as much as the deletion is. Both are
shapes where work quietly stops existing:

- `closed_unlanded` is a PR that was closed rather than merged while still
  holding commits — the state PR #200 ended in.
- `reused_after_merge` is a branch name reused after its PR merged. Judging it
  by PR state alone would delete the newer commits, because GitHub still
  reports the branch as merged.

Both are printed under `UNLANDED WORK` with a recovery SHA.

## What is never touched

- A worktree with anything in `git status --porcelain` — modified *or* untracked.
- Any untracked file, anywhere. They are listed in the report so the question
  "are there untracked files?" is always already answered, never deleted.
- A stash that has not first been written to a preserve ref. Stashes younger
  than `--stash-age-hours` (default 24) are reported and left alone, so an
  in-flight agent's stash is not yanked out from under it.
- `main`, `master`, and `campaign/*`.

## Ordering

Worktrees are removed before their branches, since a checked-out branch cannot
be deleted. A branch whose worktree is dirty is reported `blocked-by-worktree`
and kept — the dirty worktree wins.

## PR index paging

`pr_index` pages GitHub `/pulls` until a short page (100 per page). It does not
silently stop at 200. `--apply` fail-closes when `gh` cannot answer — open-PR
heads must be visible before anything is deleted. Report-only stays fail-soft
(ancestry only, with the error recorded).

OPEN beats MERGED for the same head so a reused branch with a live PR is kept
as `open_pr`.

## Leftovers this tool does not delete

SessionEnd never force-deletes dirty trees, open-PR heads, or `[gone]` locals
whose content is not yet proven spent. That close is
`skills/l9-git-work-preserve/scripts/prune_execute.py` (receipt +
`L9_GIT_PRUNE_AUTHORIZED`, preserve-ref, local only by default) after
`prune_open_pr_copies.py` unlinks untracked sha-matches of open-PR blobs.
See `skills/l9-git-work-preserve/references/prune-policy.md`.
