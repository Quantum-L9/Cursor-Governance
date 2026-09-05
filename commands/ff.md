---
name: ff
version: "1.6.0"
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

0. **`ff.sh` switches to `main`.** Do not `git switch` yourself.
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

2. **Shelf leftover untracked and dirty-tracked `TODO.md`, `WIP/`,
   `docs/plans/`, and `environment/program-execution/campaigns/`** with
   one script (skip gitignored secret globs, `WIP/Legal Defense/`,
   credential filenames).
   Do **not** invent an rsync/`git add` recipe. `ff.sh` stays push-off.

   ```bash
   GOV_PY="${GOV_PY:-$HOME/.cursor-governance/.venv/bin/python}"
   for _ff_ws in "${FF_TARGETS[@]}"; do
     "$GOV_PY" "$_ff_ws/skills/l9-repo-sync/scripts/ff_shelf.py" --clone "$_ff_ws"
   done
   ```

   The script writes `$CLONE/.l9/ff-shelf-untracked.txt`, appends an existing
   same-author `feat/ff-shelf-*` PR (or cuts one stamp), applies corpus kernels
   (`kernel_pass` on `*.plan.md` only), pathspec-from-file then a separate
   commit, `l4_local.py begin` + `authorize-release`, then
   `PR_STACK=auto PR_REMEDIATE=0 make pr` unless `FF_SHELF_PUBLISH=0`.
   Display the opened **PR URL**. If the leftover list is empty, the script
   exits 0 without a stamp. Do not scoop other untracked paths. Do not delete
   the copies in the named clone.

   Record which clones `ff.sh` synced into `FF_TARGETS` (same resolution as the
   table above) before post-shelf — do not assume `$(pwd)`.
3. **Post-shelf close** — on every clone `/ff` actually synced (not
   `$(pwd)` when that is a consumer repo, and not only one clone when bare
   `/ff` paired two). `ff_shelf.py` already runs post-shelf; re-verify through
   the locked interpreter:

   ```bash
   # Resolve the same target set ff.sh used:
   #   bare /ff     → this Cursor-Governance checkout + $HOME/.cursor-governance
   #   /ff --clone  → working-copy only
   #   /ff --ssot   → $HOME/.cursor-governance only
   GOV_PY="${GOV_PY:-$HOME/.cursor-governance/.venv/bin/python}"
   for _ff_ws in "${FF_TARGETS[@]}"; do
     bash "$_ff_ws/ops/scripts/run_ff_post_shelf.sh" "$_ff_ws"
     "$GOV_PY" "$_ff_ws/ops/scripts/verify_worktree_clean.py" --workspace "$_ff_ws"
   done
   ```

   `verify_worktree_clean.py` is not executable (`100644`); always invoke it
   through the locked interpreter. For plan execution on a clean baseline
   after verify passes, prefer `agent_worktree_start.sh` off the open-PR tip
   or `origin/main`.
4. Auto-chain `/ynp`.

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
