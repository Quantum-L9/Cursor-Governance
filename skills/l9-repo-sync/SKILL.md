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
  version: 1.7.0
  updated: 2026-09-14
---

# Repo Sync (in-place fast-forward)

## Purpose

Catch **this** Cursor-Governance clone **and** `$HOME/.cursor-governance`
up to `origin/main` **in place**, in parallel, when they are different
gitdirs.
`.venv`, env.local keep-list files (`.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json`), **corpus keep-list files**
(`TODO.md`, `WIP/`, `docs/plans/`, `environment/program-execution/campaigns/`
— `ssot_is_ff_corpus_keep`), and unique untracked files
stay. Unique local commits and other dirty tracked paths are parked first.
Nothing unique is deleted.

`/ff` ends when `ff.sh` prints `OK:` and parked files are back at their
original paths. Unique WIP/plans stay in the tree. Hold copies stay as
backup. Do not run `ff_shelf.py`, `run_ff_post_shelf.sh`, or
`verify_worktree_clean.py`. No commit. No push. No PR.

**Corpus clean-repo law:** never `git stash push` corpus (incident:
`wip-todo-unrelated` clobbered `TODO.md`). Leave it in the tree.

Slash entry: skill `l9-repo-sync` (legacy slash file:
[`commands/ff.md`](../../commands/ff.md)). Rule:
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
   Step 0 inside the script switches to `main` without moving the feature
   ref, then switches back and restores parked files.
4. **Done** when the script prints `OK:` for each clone and parked files
   are back at their original paths. Do not add a second census or pytest.
   Do not run `ff_shelf.py`, `run_ff_post_shelf.sh`, or
   `verify_worktree_clean.py`. The dirty-preserve ref is **not** deleted
   here — see Handoff.

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
