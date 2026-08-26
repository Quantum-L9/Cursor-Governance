---
name: l9-repo-sync
description: "Catch a named clone to origin/main in place. Parks unique work; keeps .venv. Use when /ff or make ff. Do not use for activate_fresh or feature-branch reset."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, git, sync, fast-forward, ssot, cursor-governance]
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-08-22
---

# Repo Sync (in-place fast-forward)

## Purpose

Catch a **named** Cursor-Governance clone up to `origin/main` **in place**.
`.venv`, env.local keep-list files (`.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json`), and unique untracked files
stay. Unique local commits and every dirty tracked path are parked first.
Nothing unique is deleted.
Slash entry: [`/ff`](../../commands/ff.md). Rule:
[`rules/55-ff-only-ssot-sync.mdc`](../../rules/55-ff-only-ssot-sync.mdc).

**Incident 2026-08-21:** `governance_activate_fresh.sh` shallow-clone + atomic
swap replaced `$HOME/.cursor-governance` and dropped `.venv`. Never treat
that script as sync.

**Incident 2026-08-22:** leftover dirty tracked files plus unrelated history
(`HEAD...origin/main` has no merge-base) made `reset --keep` abort
(`Entry not uptodate`). `/ff` now parks **all** dirty tracked paths before
catch-up — not only triple-dot colliding ones.

## Core Contract

| Mode | Mutates? | Action |
|---|---|---|
| diagnose | No | Name the clone. Inventory. Can this branch ff? |
| sync (`/ff`) | Yes — catch-up | Run [references/execute.md](references/execute.md) via `scripts/ff.sh` |
| refuse | No | Clone is not on `main`, or park/hold failed |

No new pull script. The only mutate path is `scripts/ff.sh` (`reset --keep`
after preserve refs). It does **not** call `governance_sync.sh` (that script
stashes untracked). `GOVERNANCE_SYNC_PUSH=0`. `GOVERNANCE_SYNC_HARD_RESET=0`.

## Authority Order

1. User-named target clone (`ssot` vs `workspace`).
2. This skill + rule `55-ff-only-ssot-sync`.
3. `l9-git-work-preserve` when a parked ref needs later extract.

## Compact Workflow

1. **Name** — print [references/clone-map.md](references/clone-map.md). If the
   user said “this repo” and both gitdirs exist, **stop until they name one**.
2. **Diagnose** — [references/diagnose-first.md](references/diagnose-first.md).
3. **Refuse** — [references/forbidden.md](references/forbidden.md) if the ask
   needs switch, clone, swap, or push.
4. **Execute** — [references/execute.md](references/execute.md) via
   `scripts/ff.sh`. Dirt and unique commits are **not** a stop.
5. **Verify** — same `gitdir`, same branch, `.venv` and env.local keep-list
   still present at the same paths, no new `~/.cursor-governance.bak.*`
   from this run.

## Failure Handling

`reset --keep` abort → stop. Work is still in the tree. Unique commits are
on `l9/ff-preserve-*`. Dirty bytes are on `refs/l9/preserved/ff-dirty/*`
and `$HOME/.cursor/l9-ff-hold/`. Do not run `activate_fresh`. Re-run `/ff`
after reading the FAIL line.

## Forbidden

See [references/forbidden.md](references/forbidden.md). Never
`git switch` / `git checkout` / `git pull` / `git clone` / `git stash -u` /
`git reset --hard` as a sync. Catch-up is `git reset --keep` inside `ff.sh`.
Never delete unique files to “unblock” `/ff`.

## Validation

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  skills/l9-repo-sync/scripts/validate_pack_structure.py
```
