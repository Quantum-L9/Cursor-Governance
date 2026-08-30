---
description: Sync or fast-forward a Cursor-Governance clone only via /ff and l9-repo-sync (in-place ff). Corpus keep-list like .venv. Never governance_activate_fresh swap. Never delete unique work.
---

# Fast-forward only (no SSOT clobber)

SessionStart does **not** auto-update or auto-sync the SSOT. Inbound tip
activation (`governance_activate_fresh.sh`) is skipped unless
`L9_GOVERNANCE_AUTO_UPDATE=1` (breakglass). Catch up only via **`/ff`**.

When the user asks to sync, fast-forward, or “update the SSOT / this
governance clone,” use **`/ff`** — nothing else.

| Link | Role |
|---|---|
| [`commands/ff.md`](../commands/ff.md) | Slash protocol `/ff` (thin caller) |
| [`skills/l9-repo-sync/SKILL.md`](../skills/l9-repo-sync/SKILL.md) | Skill contract |
| [`skills/l9-repo-sync/scripts/ff.sh`](../skills/l9-repo-sync/scripts/ff.sh) | Park unique work, then `reset --keep` |

An in-place catch-up leaves `.venv`, **env.local keep-list files**, **corpus
keep-list files** (`TODO.md`, `WIP/`, `docs/plans/`,
`environment/program-execution/campaigns/` — see
`ssot_is_ff_corpus_keep` in `ops/scripts/lib/ssot_machine_local_keep.sh`), and
unique untracked files. Unique commits and other dirty tracked bytes are parked
(preserve branch, dirty ref, `$HOME/.cursor/l9-ff-hold/`). That is the
success test. Do not call `governance_sync.sh` (it stashes untracked). Do
not delete files to unblock. Do not `git stash push` corpus — shelf + commit +
`make pr` instead. Machine-local keep-list: `.env.local`, `env.local`,
`.env.*.local`, `.claude/settings.local.json` (same as sessionStart swap).

## MUST

- Bare `/ff` in this repo: run `skills/l9-repo-sync/scripts/ff.sh` **once**
  (pairs this checkout + `$HOME/.cursor-governance` in parallel)
- `/ff --clone` / `/ff --ssot`: pass that flag through; one target
- Set `GOVERNANCE_SYNC_PUSH=0` and `GOVERNANCE_SYNC_HARD_RESET=0`
- Do not `git switch` yourself (the script switches to `main` after parking)
- After catch-up, shelf leftover untracked **and dirty tracked** corpus under
  `TODO.md`, `WIP/`, `docs/plans/`, and
  `environment/program-execution/campaigns/` onto a sibling branch — copy the
  bytes in, apply Improve then Recursive Alignment then Validate & Repair
  before precommit, then `l4_local.py begin` + `authorize-release` (not
  `record-kernels`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` in the shelf
  worktree unless `FF_SHELF_PUBLISH=0`, then `run_ff_post_shelf.sh` +
  `verify_worktree_clean.py` on the named clone. `ff.sh` stays push-off.
- Never `git stash push` corpus paths to “prepare” for `/ff`

## MUST NOT

- Run `ops/scripts/governance_activate_fresh.sh` as a sync (shallow clone +
  atomic swap **replaces** the live directory and drops `.venv`)
- Use `make start` / sessionStart activate as a stand-in for `/ff`
- Treat `make sync` as `/ff` (`make sync` is still `governance_sync.sh`)
- `git stash -u` / `git stash push` on corpus / `git reset --hard` / `git pull` / agent `git switch` /
  `git checkout` / `git clone` to “catch up” (inner `ff.sh` `git switch` to
  `main` after park is the exception)
- Reset a feature branch onto `origin/main`
- Delete dirty or untracked files so `reset --keep` can proceed
- Stop to name `ssot` vs `workspace`
- Sequential second `ff.sh` after this clone (the script pairs)

If `reset --keep` aborts, unique bytes are still in the tree or on a
preserve/hold ref. Re-run `/ff`. Do not swap. Do not delete.

<!-- generated-from: rules/55-ff-only-ssot-sync.mdc; do-not-edit -->
