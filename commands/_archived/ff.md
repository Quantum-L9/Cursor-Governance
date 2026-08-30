---
name: ff
version: "1.7.0"
description: "In-place catch-up: this Cursor-Governance clone + SSOT in parallel; corpus keep-list like .venv; --clone / --ssot for one target"
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
  stay (machine-local keep-list; same as sessionStart swap)
- **Corpus keep-list** — worktree bytes survive catch-up (never reset to
  `HEAD`, never clobbered by `checkout -f origin/main -- .`):
  - `TODO.md` (agent task queue — not code)
  - `WIP/**` (except `WIP/Legal Defense/` and credential-shaped globs)
  - `docs/plans/**`
  - `environment/program-execution/campaigns/**`
  SSOT: `ops/scripts/lib/ssot_machine_local_keep.sh` → `ssot_is_ff_corpus_keep`
- unique untracked files stay in the tree
- unique local commits are parked on `l9/ff-preserve-<stamp>`
- other dirty tracked paths are classified, copied to
  `$HOME/.cursor/l9-ff-hold/`, and parked at
  `refs/l9/preserved/ff-dirty/<stamp>` so `reset --keep` can proceed
- untracked paths that `origin/main` now tracks move to that hold (not `/tmp`)

It does **not** call `governance_sync.sh` (that script stashes untracked).

Rule: [`rules/55-ff-only-ssot-sync.mdc`](../rules/55-ff-only-ssot-sync.mdc).
Skill: [`skills/l9-repo-sync/SKILL.md`](../skills/l9-repo-sync/SKILL.md).

## Clean-repo law (corpus)

Corpus is not code. Modified corpus bytes belong on GitHub — committed and
pushed via the shelf loop — not in a agent stash, not left to rot in
`refs/l9/preserved/ff-dirty/*` without a PR.

| Corpus path | During `/ff` | After `/ff` |
|---|---|---|
| `TODO.md` | **Protected** (corpus keep-list) | If still dirty vs `origin/main`, shelf + commit + `PR_STACK=auto PR_REMEDIATE=0 make pr` |
| `WIP/`, `docs/plans/`, `environment/program-execution/campaigns/` (untracked) | Copied to shelf worktree | Same shelf loop |
| Same trees (dirty **tracked**) | **Protected** in worktree through catch-up | Shelf loop must include those paths in the pathspec commit |

**MUST NOT** use `git stash push` / `git stash save` to “save” corpus for `/ff`.
That hides bytes off-branch and has caused data loss (e.g. `wip-todo-unrelated`).
Use the shelf loop or a scoped commit on the current branch before catch-up.

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

2. **Shelf corpus** — untracked **and** dirty tracked paths under the
   keep-list trees plus `TODO.md` when they still differ from what is already
   on an open `feat/ff-shelf-*` PR or `origin/main`. Skip gitignored secret
   globs, `WIP/Legal Defense/`, credential filenames, and paths an open shelf
   PR already carries at the same sha256. Cut a sibling worktree from the new
   `origin/main` tip (`feat/ff-shelf-<stamp>`), **copy those files into it** —
   untracked bytes do not exist in a fresh checkout. **Before commit and before
   precommit**, apply `kernels/Improve.md`, then `kernels/Recursive
   Alignment.md`, then `kernels/Validate & Repair.md` (write `kernel_pass` on
   shelved `*.plan.md`). Then pathspec-add **only** those files, scoped commit,
   run `l4_local.py begin` then `authorize-release` in that worktree
   (**not** `record-kernels` — corpus kernels are not an L4 phase). Then
   **finish the shelf loop** unless `FF_SHELF_PUBLISH=0`:
   `PR_STACK=auto PR_REMEDIATE=0 make pr` in the shelf worktree and display
   the opened **PR URL**. If the shelf list was empty after dedupe, skip publish.
   Opt-out: `FF_SHELF_PUBLISH=0` shelves and commits only (no `make pr`).
   Do **not** put `make pr` inside `ff.sh`. Do not scoop other untracked paths.
   Do not delete the copies in the named clone.

   Record which clones `ff.sh` synced into `FF_TARGETS` (same resolution as the
   table above) before post-shelf — do not assume `$(pwd)`.
3. **Post-shelf close** — on every clone `/ff` actually synced (not
   `$(pwd)` when that is a consumer repo, and not only one clone when bare
   `/ff` paired two):

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
- `git stash -u` / `git stash push` on corpus paths / `git reset --hard` /
  deleting files to unblock catch-up
- Agent `git switch` / `checkout` / `pull` / `clone`. Inner `ff.sh` `git switch`
  **to `main` after parking** is the exception. Resetting a feature branch
  onto `origin/main` stays forbidden.
- Stopping to name `ssot` vs `workspace`
- Sequential second `ff.sh` after this clone already finished (the script pairs)

`make ff` is this command (same wrapper). `make ff-clone` / `make ff-ssot`
are `--clone` / `--ssot`. `make sync` remains `governance_sync.sh` and is
**not** `/ff`.
