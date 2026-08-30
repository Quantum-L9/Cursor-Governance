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
`governance-backup.sh` has already committed and pushed. Dirt-close
(`session_end_dirt_close.py --apply`) runs **before** this tool's
`--apply` so landed copies in the **session workspace** are gone and
novel unique bytes sit on `l9/dirt-shelf`. Receipts land in
`<workspace>/.l9/hygiene/`; the log is `~/.cursor-governance/hygiene.log`.
Kill switch: `L9_REPO_HYGIENE=0`. Dirt-close kill switch:
`L9_HYGIENE_DIRT_CLOSE=0`. Report-only: `L9_REPO_HYGIENE_MODE=--report`.

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

- **Sibling** worktrees with anything in `git status --porcelain` — modified
  *or* untracked. `repo_hygiene.py` still will not remove those trees.
- A stash that has not first been written to a preserve ref. Stashes younger
  than `--stash-age-hours` (default 24) are reported and left alone, so an
  in-flight agent's stash is not yanked out from under it.
- `main`, `master`, `campaign/*`, and a novel `l9/dirt-shelf` tip.

SessionEnd dirt-close **does** change porcelain in the **session workspace
only** (the payload `$WS`): landed copies (`origin/main` or an open-PR blob
at the same path) and generated deltas are restored or removed and are
**not** parked. Novel unique bytes are parked on one rolling
`refs/heads/l9/dirt-shelf`, then restored/removed only after `git cat-file`
proves the path on that tip. Secrets / `WIP/Legal Defense/` stay on disk.
Absorbed dirt-shelf (and leftover `refs/l9/preserved/worktree-dirt/*`) tips
are deleted **after** the tip SHA is written to the dirt-close receipt.
Sibling dirty worktrees stay untouched. Do not call `/ff` or
`prune_execute.py` for this close.

The honest answer to "what dirty files are there" is
`session_end_dirt_close.py --status` (`dirty_files` / `dirty_unique`), not
raw `git status --porcelain`.

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

`repo_hygiene.py` never force-deletes sibling dirty trees, open-PR heads, or
`[gone]` locals whose content is not yet proven spent. Branch/worktree prune
beyond absorbed locals is still
`skills/l9-git-work-preserve/scripts/prune_execute.py` (receipt +
`L9_GIT_PRUNE_AUTHORIZED`, preserve-ref, local only by default). Session
workspace porcelain is closed by `session_end_dirt_close.py`, which reuses
`prune_open_pr_copies.py` blob identity and does **not** invoke
`prune_execute.py`. See `skills/l9-git-work-preserve/references/prune-policy.md`.
