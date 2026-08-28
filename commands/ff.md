---
name: ff
version: "1.3.0"
description: "In-place catch-up of a named Cursor-Governance clone — parks unique work, keeps .venv; never activate_fresh"
auto_chain: ynp
aliases:
  - /repo-sync
  - /fast-forward
---

# /ff — In-place catch-up (keep work)

## WHAT IT DOES

Thin caller for skill **`l9-repo-sync`**. Run `skills/l9-repo-sync/scripts/ff.sh`.
`make ff` is the same wrapper.

Catch the named clone up to `origin/main` **in place**. Unique work is
**parked, never deleted**:

- `.venv` stays at the same path
- `.env.local`, `env.local`, `.env.*.local`, and `.claude/settings.local.json`
  stay (same keep-list as sessionStart swap)
- unique untracked files stay in the tree
- unique local commits are parked on `l9/ff-preserve-<stamp>`
- every dirty tracked path is classified, copied to
  `$HOME/.cursor/l9-ff-hold/`, and parked at
  `refs/l9/preserved/ff-dirty/<stamp>` so `reset --keep` can proceed
- untracked paths that `origin/main` now tracks move to that hold (not `/tmp`)

It does **not** call `governance_sync.sh` (that script stashes untracked).

Rule: [`rules/55-ff-only-ssot-sync.mdc`](../rules/55-ff-only-ssot-sync.mdc).
Skill: [`skills/l9-repo-sync/SKILL.md`](../skills/l9-repo-sync/SKILL.md).

## EXECUTION

1. Read and follow skill `l9-repo-sync`.
2. Name the clone (`ssot` = `$HOME/.cursor-governance`, or `workspace`).
   “This workspace” / untracked-in-this-folder → `workspace`.
3. Diagnose (branch, porcelain, ahead/behind, `.venv` present).
4. Run **only**:

```bash
CURSOR_GOVERNANCE_DIR="<absolute-named-clone>" \
  bash skills/l9-repo-sync/scripts/ff.sh
```

5. Verify same gitdir, same branch, `.venv` and env.local keep-list still
   present, unique untracked still present or held, no new
   `~/.cursor-governance.bak.*`.
6. **Shelf leftover `WIP/` and `docs/plans/`** — if any untracked files remain
   under those trees (skip gitignored secret globs, `WIP/Legal Defense/`,
   credential filenames, and anything an open `feat/ff-shelf-*` PR already
   carries), cut a sibling worktree from the new `origin/main` tip
   (`feat/ff-shelf-<stamp>`), **copy those files into it** — untracked bytes
   do not exist in a fresh checkout — pathspec-add **only** those files,
   scoped commit, run `l4_local.py begin / record-kernels / authorize-release`
   in that worktree, then **ask the user** before `PR_REMEDIATE=0 make pr`.
   Catching a clone up is not authorization to publish. Do **not** put
   `make pr` inside `ff.sh`. Do not scoop other untracked paths. Do not delete
   the copies in the named clone.
7. Auto-chain `/ynp`.

## FORBIDDEN

- `governance_activate_fresh.sh` / `make start` as “sync”
- `GOVERNANCE_SYNC_PUSH=1` or `GOVERNANCE_SYNC_HARD_RESET=1`
- `git stash -u` / `git reset --hard` / deleting files to unblock catch-up
- `git switch` / `checkout` / `pull` / `clone`

`make ff` is this command (same wrapper). `make sync` remains
`governance_sync.sh` and is **not** `/ff`.
