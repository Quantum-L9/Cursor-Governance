<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, forbidden]
status: active
version: 1.2.0
updated: 2026-08-22
/L9_META -->

# Forbidden (incident / refuse)

These are **not** `/ff`. Name them so agents can refuse. Do not run them.

## Incident shapes

- Agent `git switch` / `git checkout` onto `main` on a dirty shared clone
- `git merge` / `git pull` / `git clone` as a “sync”
- `git reset --hard` (discards dirty tracked; not the catch-up primitive)
- `git stash` / `stash -u` / stash-pop as preserve (2026-08-21: this is why
  `/ff` used to refuse dirty trees — `governance_sync.sh` stashes untracked)
- Deleting dirty or untracked files to “unblock” `/ff`
- `governance_activate_fresh.sh` — ff-or-**swap**; swap `mv`s the live SSOT
  and drops `.venv` (2026-08-21)
- `make start` — sessionStart path; may call `activate_fresh` if breakglass is on
- `GOVERNANCE_SYNC_HARD_RESET=1`
- `GOVERNANCE_SYNC_PUSH=1` for “fast forward”
- `worktree prune` as cleanup
- Resetting a **feature** branch onto `origin/main`
- Stopping to name `ssot` vs `workspace`
- Sequential `ff.sh` on SSOT after this clone already finished (bare `/ff`
  pairs inside the script; from other repos use `--clone` or `--ssot`)

## Allowed catch-up (only inside `scripts/ff.sh`)

- `git fetch origin main`
- `git switch` **to `main`** after parking dirt (feature ref stays)
- `git update-ref` / `git branch` for `l9/ff-preserve-*` and `ff-dirty`
- `git stash create` (no `-u`) to park dirty tracked, then restore those paths
- copy/move unique bytes to `$HOME/.cursor/l9-ff-hold/`
- `git reset --keep origin/main` on branch `main` only

`make ff` is `/ff` (same `scripts/ff.sh`). `make sync` is still
`governance_sync.sh` and is **not** `/ff`. Do not treat `make backup` as sync.
