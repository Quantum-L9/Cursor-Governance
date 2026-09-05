<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, execute, fast-forward]
status: active
version: 1.4.0
updated: 2026-08-29
/L9_META -->

# Execute (only this)

`/ff` (no flags) from a Cursor-Governance checkout catches **this tree and**
`$HOME/.cursor-governance` up to `origin/main` **in parallel**. `/ff --clone`
and `/ff --ssot` are one target each (other repos). Unique work is parked
first. Nothing unique is deleted. Keep-list: `.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json`. **Corpus keep-list** (worktree
bytes survive catch-up): `TODO.md`, `WIP/`, `docs/plans/`,
`environment/program-execution/campaigns/` (`ssot_is_ff_corpus_keep`).
Never `git stash push` corpus — shelf + commit + `make pr`.

The only mutate path is the wrapper:

```bash
bash skills/l9-repo-sync/scripts/ff.sh
CURSOR_GOVERNANCE_DIR="$(pwd)" bash skills/l9-repo-sync/scripts/ff.sh --clone
bash skills/l9-repo-sync/scripts/ff.sh --ssot
```

`ff.sh` does **not** call `governance_sync.sh`. That script’s dirty path is
`stash -u` → ff → pop, which can drop or conflict-mark untracked work.
`GOVERNANCE_SYNC_PUSH=0` and `GOVERNANCE_SYNC_HARD_RESET=0` stay set so no
caller can turn push or hard-reset back on.

## Catch-up primitive

Inside `scripts/ff.sh`, after fetch:

0. If HEAD is not `main`, park dirty tracked and untracked paths that
   `origin/main` already tracks, then `git switch` to `main` (or create it
   tracking `origin/main`). The feature branch ref stays. Do **not** count
   feature commits as `ahead` / `l9/ff-preserve-*`.
1. If `ahead > 0` **on main**, create the preserve branch/ref (do not drop
   unique commits on `main`).
2. If the clone is **behind or ahead** and has dirty **tracked** paths, park
   **all** **non-corpus** paths (corpus keep-list bytes stay in the worktree — see
   `ssot_is_ff_corpus_keep`):
   - `git stash create` (no `-u`) at `refs/l9/preserved/ff-dirty/<stamp>`
   - copy each path to `$HOME/.cursor/l9-ff-hold/<clone-key>/<stamp>/tracked/`
   - classify `already_at_origin` vs `unique`
   - restore non-corpus tracked paths from `HEAD` so `reset --keep` can run
   - copy corpus keep-list paths to hold; **do not** restore from `HEAD`;
     restore from hold after `checkout -f origin/main -- .`
   Untracked, `.venv`, and corpus keep-list dirty tracked stay in the tree.
3. If already at the tip **on main**, leave unique dirty tracked in the worktree.
   Feature-branch dirt parked in step 0 is not restored onto `main`.
4. If an untracked path is now tracked on `origin/main`, move the local copy
   to `$HOME/.cursor/l9-ff-hold/<clone-key>/<stamp>/untracked/` (never delete).
5. `git reset --keep origin/main` — moves `main` to the tip, **aborts** if a
   remaining dirty tracked file would be lost, does **not** delete untracked
   or `.venv`.

If `reset --keep` aborts, work is still in the tree. Re-run `/ff` after
reading the FAIL line. Do not delete files to unblock.

## After success

Same gitdir, HEAD on `main`, `.venv` still at `<clone>/.venv` when it existed
before, env.local keep-list still present, unique untracked still present
or held, no new `~/.cursor-governance.bak.*`.

## After success — shelf leftover untracked corpus

`ff.sh` is finished and stays **push-off**. The slash/`make ff` caller then
runs **one** script for leftover **untracked** `WIP/`, `docs/plans/`, and
`environment/program-execution/campaigns/` (not the root task-queue file, not
dirty-tracked corpus):

```bash
GOV_PY="${GOV_PY:-$HOME/.cursor-governance/.venv/bin/python}"
"$GOV_PY" skills/l9-repo-sync/scripts/ff_shelf.py --clone "$CLONE"
```

`ff_shelf.py` owns the mutate path:

1. Writes `$CLONE/.l9/ff-shelf-untracked.txt` (respect `.gitignore`).
2. Skips `WIP/Legal Defense/`, `WIP/*oauth*.json`, `WIP/*credentials*.json`,
   `WIP/*client_secret*.json`, and any file that looks like a live secret.
3. Drops paths an open same-author `feat/ff-shelf-*` PR already carries at the
   same sha256. Appends that worktree; does not cut a second stamp. If none is
   open, cuts one `feat/ff-shelf-<stamp>`.
4. `rsync -R --files-from=$CLONE/.l9/ff-shelf-untracked.txt` — no process
   substitution, no `/tmp` files-from. Untracked bytes are not in a fresh
   checkout.
5. Applies corpus kernels (Improve, then Recursive Alignment, then Validate &
   Repair) on leftover files. Writes `kernel_pass` YAML only on `*.plan.md`.
6. `git add --pathspec-from-file` on that list, then a **separate** commit.
   Then `l4_local.py begin` + `authorize-release` in the shelf worktree (not
   `record-kernels`).
7. Shelf publish (default ON): `PR_STACK=auto PR_REMEDIATE=0 make pr` in the
   shelf worktree. Opt-out: `FF_SHELF_PUBLISH=0`. Display the opened **PR URL**.
   Do not put `make pr` inside `ff.sh`.
8. Post-shelf close in the named clone (also invoked by the script):

   ```bash
   bash ops/scripts/run_ff_post_shelf.sh "$CLONE"
   "$GOV_PY" ops/scripts/verify_worktree_clean.py --workspace "$CLONE"
   ```

   Always `GOV_PY verify_worktree_clean.py` (locked interpreter; the verify
   script is not executable). Leave shelf copies in the named clone until
   verify passes. Do not `git stash -u`.

`refs/l9/preserved/ff-dirty/<stamp>` stays until `l9-git-work-preserve` triage
plus `prune-policy` say otherwise. `/ff` never deletes it.
