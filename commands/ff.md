---
name: ff
version: "1.2.0"
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

5. Verify same gitdir, same branch, `.venv` still present, unique untracked
   still present or held, no new `~/.cursor-governance.bak.*`.
6. Auto-chain `/ynp`.

## FORBIDDEN

- `governance_activate_fresh.sh` / `make start` as “sync”
- `GOVERNANCE_SYNC_PUSH=1` or `GOVERNANCE_SYNC_HARD_RESET=1`
- `git stash -u` / `git reset --hard` / deleting files to unblock catch-up
- `git switch` / `checkout` / `pull` / `clone`

`make ff` is this command (same wrapper). `make sync` remains
`governance_sync.sh` and is **not** `/ff`.
