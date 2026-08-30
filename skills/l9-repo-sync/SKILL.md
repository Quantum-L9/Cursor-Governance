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
  version: 1.4.0
  updated: 2026-08-29
---

# Repo Sync (in-place fast-forward)

## Purpose

Catch **this** Cursor-Governance clone **and** `$HOME/.cursor-governance`
up to `origin/main` **in place**, in parallel, when they are different
gitdirs.
`.venv`, env.local keep-list files (`.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json`), and unique untracked files
stay. Unique local commits and every dirty tracked path are parked first.
Nothing unique is deleted.

**Shelf publish loop (2026-08-29):** when `/ff` shelves WIP/plans/campaigns, the
caller finishes with `PR_STACK=auto PR_REMEDIATE=0 make pr` in the shelf
worktree unless `FF_SHELF_PUBLISH=0`, then runs
`ops/scripts/run_ff_post_shelf.sh` and `verify_worktree_clean.py` on the named
clone. See `commands/ff.md` step 2–3 and `AGENTS.md` `FF_CLOSE_PUBLISH_LOOP_V1`.
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
| diagnose | No | Skip. Not a stop. |
| sync (`/ff`) | Yes | `ff.sh` (pairs SSOT). `/ff --clone` / `/ff --ssot` = one target. |
| refuse | No | Park/hold/switch failed. Do not reset a feature branch onto main. |

No new pull script. The only mutate path is `scripts/ff.sh` (`reset --keep`
after preserve refs). It does **not** call `governance_sync.sh` (that script
stashes untracked). `GOVERNANCE_SYNC_PUSH=0`. `GOVERNANCE_SYNC_HARD_RESET=0`.

## Authority Order

1. `/ff` / `make ff` from this checkout — script pairs SSOT. No naming.
2. This skill + rule `55-ff-only-ssot-sync`.
3. `l9-git-work-preserve` when a parked ref needs later triage or extract.

## Handoff — what becomes of what `/ff` parked

`/ff` parks and never deletes, which is correct and also means the preserve refs
accumulate: nothing in this skill reads them again. Sorting them is
`l9-git-work-preserve`'s job, and it decides by evidence rather than by age:

```bash
python3 skills/l9-git-work-preserve/scripts/triage_preserved_refs.py \
  --repo "$(pwd)" --fetch
```

It classifies `refs/l9/preserved/ff/*`, `refs/l9/preserved/ff-dirty/*`, and
`l9/ff-preserve-*` into `novel` / `superseded` / `review` / `merged` /
`unproven`, and deletes nothing. Contract:
`skills/l9-git-work-preserve/references/triage-handoff.md`. Removing a ref stays
`prune-policy.md`'s call — never `/ff`'s, and never triage's.

## Compact Workflow

1. **Run once** — [references/clone-map.md](references/clone-map.md).
   `bash skills/l9-repo-sync/scripts/ff.sh` or `make ff`. The script pairs
   this checkout + SSOT in parallel. Do not diagnose both. Do not wait, then
   ff SSOT. Do not stop to name clones.
2. **Refuse** — [references/forbidden.md](references/forbidden.md) if the ask
   needs clone, swap, push, or an **agent** `git switch`. Inner `ff.sh` may
   `git switch` to `main` after parking.
3. **Execute** — [references/execute.md](references/execute.md) via
   `scripts/ff.sh`. Dirt, unique commits, and not-on-main are **not** a stop.
   Step 0 inside the script switches to `main` without moving the feature ref.
4. **Done** when the script prints `OK:` for each clone. Do not add a second
   census or pytest to `/ff`.
5. **Shelf** — leftover untracked `WIP/`, `docs/plans/`, and
   `environment/program-execution/campaigns/` become a sibling branch
   (`feat/ff-shelf-<stamp>`). Copy the bytes into the new worktree
   (untracked files are not in a fresh checkout). Apply Improve, then
   Recursive Alignment, then Validate & Repair **before** commit/precommit.
   Then `l4_local.py begin` + `authorize-release` (not `record-kernels`).
   **Finish the shelf publish loop** unless `FF_SHELF_PUBLISH=0`:
   `PR_STACK=auto PR_REMEDIATE=0 make pr` in the shelf worktree and display
   the opened **PR URL** (see Shelf publish loop above / `FF_CLOSE_PUBLISH_LOOP_V1`).
   Opt-out: `FF_SHELF_PUBLISH=0` shelves and commits only. Skip paths an open
   shelf PR already carries. `ff.sh` stays push-off. Secret globs stay out.
   The dirty-preserve ref is **not** deleted here — see Handoff.

## Failure Handling

`reset --keep` abort → stop. Work is still in the tree. Unique commits are
on `l9/ff-preserve-*`. Dirty bytes are on `refs/l9/preserved/ff-dirty/*`
and `$HOME/.cursor/l9-ff-hold/`. Do not run `activate_fresh`. Re-run `/ff`
after reading the FAIL line.

## Forbidden

See [references/forbidden.md](references/forbidden.md). Never
`git switch` / `git checkout` / `git pull` / `git clone` / `git stash -u` /
`git reset --hard` as an **agent** sync. Catch-up is `git switch` to `main`
(after park) then `git reset --keep` **inside** `ff.sh`. Never reset a
feature branch onto `origin/main`. Never delete unique files to “unblock” `/ff`.

## Validation

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  skills/l9-repo-sync/scripts/validate_pack_structure.py
```
