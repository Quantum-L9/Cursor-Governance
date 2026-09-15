<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, execute, fast-forward]
status: active
version: 1.7.0
updated: 2026-09-14
/L9_META -->

# Execute (only this)

`/ff` (no flags) from a Cursor-Governance checkout catches **this tree and**
`$HOME/.cursor-governance` up to `origin/main` **in parallel**. `/ff --clone`
and `/ff --ssot` are one target each (other repos). Unique work is parked
first. Nothing unique is deleted. Keep-list: `.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json`. **Corpus keep-list** (worktree
bytes survive catch-up): `TODO.md`, `WIP/`, `docs/plans/`,
`environment/program-execution/campaigns/` (`ssot_is_ff_corpus_keep`).
Never `git stash push` corpus. Leave unique WIP/plans in the tree.
Do not run `ff_shelf.py`. Do not run `run_ff_post_shelf.sh`.

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
   Feature-branch dirt parked in step 0 is restored to the pre-/ff branch
   after catch-up, not left only in hold.
4. If an untracked path is now tracked on `origin/main`, move the local copy
   to `$HOME/.cursor/l9-ff-hold/<clone-key>/<stamp>/untracked/` (never delete).
5. `git reset --keep origin/main` — moves `main` to the tip, **aborts** if a
   remaining dirty tracked file would be lost, does **not** delete untracked
   or `.venv`.
6. Switch back to the pre-/ff branch. Copy parked tracked hold files to the
   same relative paths. Copy parked untracked only when HEAD does not now
   track that path. Write `.l9/ff-restore-receipt.json`.

If `reset --keep` aborts, work is still in the tree. Re-run `/ff` after
reading the FAIL line. Do not delete files to unblock.

## After success

Same gitdir, `refs/heads/main` at `origin/main`, HEAD back on the pre-/ff
branch, parked files back at their original paths, `.venv` still at
`<clone>/.venv` when it existed before, env.local keep-list still present,
unique untracked still present or held, no new `~/.cursor-governance.bak.*`.

`/ff` is finished. Unique WIP/plans stay in the tree. Hold copies stay as
backup. Do not run `ff_shelf.py`. Do not run `run_ff_post_shelf.sh`.
Do not run `verify_worktree_clean.py`. No commit. No push. No PR.

`refs/l9/preserved/ff-dirty/<stamp>` stays until `l9-git-work-preserve` triage
plus `prune-policy` say otherwise. `/ff` never deletes it.
