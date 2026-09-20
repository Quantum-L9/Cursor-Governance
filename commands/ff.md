---
name: ff
version: "1.7.0"
description: "In-place catch-up: this Cursor-Governance clone + SSOT in parallel; --clone / --ssot for one target"
auto_chain: ynp
aliases:
  - /repo-sync
  - /fast-forward
---

# /ff — In-place catch-up (keep work)

## WHAT IT DOES

Thin caller for skill **`l9-repo-sync`**. Run `skills/l9-repo-sync/scripts/ff.sh`.
`make ff` is the same wrapper (pairs when this checkout is not the live SSOT).

| Typed | What runs |
|---|---|
| `/ff` | **Both**: this Cursor-Governance checkout **and** `$HOME/.cursor-governance`, **in parallel**. This is the default in this repo. |
| `/ff --clone` | The Cursor-Governance **working copy** only (not SSOT). Use from other repos. |
| `/ff --ssot` | `$HOME/.cursor-governance` only. Use from other repos. |

Unique work is **parked, never deleted**:

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

Do **not** name clones. Do **not** diagnose. Do **not** wait for one clone
then start the other. Do **not** run pytest as part of `/ff`.

0. **`ff.sh` parks, switches to `main`, catch-up, then switches back
   and restores parked files to their original paths.** Do not
   `git switch` yourself.
1. Pass through the user's flags. Bare `/ff` has no flags.

```bash
# /ff          → both, parallel
bash skills/l9-repo-sync/scripts/ff.sh
# /ff --clone  → working copy only
bash skills/l9-repo-sync/scripts/ff.sh --clone
# /ff --ssot   → $HOME/.cursor-governance only
bash skills/l9-repo-sync/scripts/ff.sh --ssot
```

`--clone` from another repo: this checkout if it is a governance identity
tree, else `$HOME/Cursor-Governance`, else `CURSOR_GOVERNANCE_CLONE`.

2. **Stop when `ff.sh` prints `OK:` and files are back at their original
   paths.** Unique `TODO.md` / `WIP/` / `docs/plans/` / PE campaigns stay
   in the tree. Hold copies stay as backup. No commit. No push. No PR.
   Do not run `ff_shelf.py`, `run_ff_post_shelf.sh`, or
   `verify_worktree_clean.py`. Do not invent a “shelf but no PR” mode.
3. Auto-chain `/ynp`.

## FORBIDDEN

- `governance_activate_fresh.sh` / `make start` as “sync”
- `GOVERNANCE_SYNC_PUSH=1` or `GOVERNANCE_SYNC_HARD_RESET=1`
- `git stash -u` / `git reset --hard` / deleting files to unblock catch-up
- Agent `git switch` / `checkout` / `pull` / `clone`. Inner `ff.sh` `git switch`
  **to `main` after parking** is the exception. Resetting a feature branch
  onto `origin/main` stays forbidden.
- Stopping to name `ssot` vs `workspace`
- Sequential second `ff.sh` after this clone already finished (the script pairs)

`make ff` is this command (same wrapper). `make ff-clone` / `make ff-ssot`
are `--clone` / `--ssot`. `make sync` remains `governance_sync.sh` and is
**not** `/ff`.
