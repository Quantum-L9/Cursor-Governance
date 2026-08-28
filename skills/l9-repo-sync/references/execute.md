<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, execute, fast-forward]
status: active
version: 1.2.0
updated: 2026-08-22
/L9_META -->

# Execute (only this)

`/ff` catches a **named** clone up to `origin/main` **in place** while keeping
`.venv`, env.local keep-list files, and every unique untracked path. Unique
work is parked first. Nothing unique is deleted. Keep-list:
`.env.local`, `env.local`, `.env.*.local`, `.claude/settings.local.json`
(same lib as `governance_activate_fresh.sh` swap carry).

The only mutate path is the wrapper:

```bash
CURSOR_GOVERNANCE_DIR="<absolute-named-clone>" \
  bash skills/l9-repo-sync/scripts/ff.sh
```

`ff.sh` does **not** call `governance_sync.sh`. That script’s dirty path is
`stash -u` → ff → pop, which can drop or conflict-mark untracked work.
`GOVERNANCE_SYNC_PUSH=0` and `GOVERNANCE_SYNC_HARD_RESET=0` stay set so no
caller can turn push or hard-reset back on.

## Catch-up primitive

On branch `main` only, after fetch:

1. If `ahead > 0`, create the preserve branch/ref (do not drop unique commits).
2. If the clone is **behind or ahead** and has dirty **tracked** paths, park
   **all** of them (not only paths that differ on `origin/main`, and not
   `HEAD...origin/main` — that fails when there is no merge-base):
   - `git stash create` (no `-u`) at `refs/l9/preserved/ff-dirty/<stamp>`
   - copy each path to `$HOME/.cursor/l9-ff-hold/<clone-key>/<stamp>/tracked/`
   - classify `already_at_origin` vs `unique`
   - restore only those tracked paths from `HEAD` so `reset --keep` can run
   Untracked and `.venv` stay in the tree.
3. If already at the tip, leave unique dirty tracked in the worktree.
4. If an untracked path is now tracked on `origin/main`, move the local copy
   to `$HOME/.cursor/l9-ff-hold/<clone-key>/<stamp>/untracked/` (never delete).
5. `git reset --keep origin/main` — moves `main` to the tip, **aborts** if a
   remaining dirty tracked file would be lost, does **not** delete untracked
   or `.venv`.

If `reset --keep` aborts, work is still in the tree. Re-run `/ff` after
reading the FAIL line. Do not delete files to unblock.

## After success

Same gitdir, same branch, `.venv` still at `<clone>/.venv` when it existed
before, env.local keep-list still present, unique untracked still present
or held, no new `~/.cursor-governance.bak.*`.

## After success — shelf WIP and plans

`ff.sh` is finished. The slash/`make ff` caller then shelves leftover
**untracked** `WIP/` and `docs/plans/` so the named clone is not a dump:

1. List untracked under `WIP/` and `docs/plans/` (respect `.gitignore`).
2. Skip `WIP/Legal Defense/`, `WIP/*oauth*.json`, `WIP/*credentials*.json`,
   `WIP/*client_secret*.json`, and any file that looks like a live secret.
3. If the list is empty, stop. If not, add a sibling worktree from the new
   `origin/main` tip: `feat/ff-shelf-<stamp>`.
4. Pathspec-add **only** those files. Scoped commit. `PR_REMEDIATE=0 make pr`.
5. Leave the copies in the named clone. Do not `git stash -u`. Do not run
   `make pr` from inside `ff.sh`.

`refs/l9/preserved/ff-dirty/<stamp>` stays until `l9-git-work-preserve` triage
plus `prune-policy` say otherwise. `/ff` never deletes it.
