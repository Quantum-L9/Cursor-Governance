# Harvest workflow (cross-worktree dirt)

Repeatable extract of **misplaced dirty and untracked work** across sibling
worktrees of the same repo. Complements `extract` (one diagnosed ref) and
`make clean` (this workspace only). Complements `ops/scripts/repo_hygiene.py`
(sessionEnd prune of *landed* residue — never harvests).

Default is **report-only**. Mutation is a later extract onto a fresh
`origin/main` worktree. Source worktrees stay intact.

Incident 2026-08-21: leftover `/ff`, protected-root PR template, and WIP sat
in stale worktrees 74 commits behind `origin/main`. Applying those dirty diffs
wholesale would have reverted later `main` wording. Harvest classifies first,
then ports unique paths onto current tip.

## When to run

User asks to harvest leftover / lingering / misplaced dirty or untracked work
across worktrees, including WIP, into a PR. Also when `audit` shows many dirty
worktrees and the next action is “roll unique value into one branch.”

## Classify before copy

```bash
python3 scripts/harvest_worktree_dirt.py \
  --repo "$(pwd)" \
  --baseline origin/main \
  --include-wip \
  --json
```

`--extra-root` may be repeated. Defaults (when they exist):
`$HOME/.l9/gov-worktrees`, `$HOME/.l9/program-worktrees`,
`$HOME/Cursor-Governance-worktrees`. Same-remote only unless
`--allow-other-remotes`.

| Class | Meaning | Harvest? |
|---|---|---|
| `skip_noise` | `.venv`, `node_modules`, `__pycache__`, `.l9` | No |
| `wiring_noise` | Mass `.claude/skills/l9-*` copies, `.claude/rules` overlay | No |
| `already_on_baseline` | Path exists at `--baseline` | No |
| `already_in_open_pr` | Same path on an open PR (optional `gh` pass) | No — leave to that PR |
| `refuse_foreign_shared` | Dirty primary `main` checkout (rule 49) | No scoop |
| `unique_wip` | Under `WIP/` and not on baseline | Yes (default `--include-wip`) |
| `unique_plans` | Untracked `docs/plans/` not on baseline | Yes |
| `unique_product` | Other unique dirty / untracked | Yes, one theme per PR |

A worktree **behind** baseline with dirty tracked files is
`stale_apply_risk`. Do not `git apply` that worktree’s full diff onto current
`main`. Port named unique files, or re-diff each path against current
baseline.

## Execute (local only)

1. Diagnosis receipt from the classifier (unique paths + classes).
2. Fresh worktree from fetched `origin/main` via
   `ops/scripts/agent_worktree_start.sh`. Do not mutate the dirty shared clone.
3. Copy or patch **only** `unique_*` pathspecs. Keep WIP in-repo; never route
   `WIP/` through `/tmp` (sacred-WIP isolation).
4. `additive_only` root files: append only. A rewrite needs
   `ALLOW-ROOT-DELETION: <path> — <reason>` in the commit message.
5. Do not replay stale `AGENTS.md` / `CLAUDE.md` / law hunks that delete later
   `main` wording.
6. Regenerate derived artifacts with
   `ops/scripts/sync_generated_artifacts.py --force` — do not copy stale
   `RULES-MANIFEST.*` / skill-registry JSON from a behind worktree.
7. Stage **explicit pathspecs**. Never `git add -A` / `git add .`.
8. Leave every source worktree and ref intact.

## Publish

Same publish path as any other extract: L4 kernels → `authorize-release` →
`make precommit-repo` → `PR_REMEDIATE=0 make pr`.

`PR_OVERLAP=block` is the default. Drop paths already on an open PR, or wait.
Do not set `PR_OVERLAP=ignore` without an explicit user override. Do not stack
this harvest onto an unrelated open PR just to clear the gate.

## After publish: shipped copies, then prune-execute

Once the unique paths are on an **open** PR, leftover worktrees still hold
untracked copies of those blobs. Those copies are not unique value:

```bash
python3 scripts/prune_open_pr_copies.py --repo "$(pwd)" --json
python3 scripts/prune_open_pr_copies.py --repo "$(pwd)" --apply
```

Then, only with diagnosis receipts + `L9_GIT_PRUNE_AUTHORIZED`, delete leftover
refs/worktrees (preserve-ref first):

```bash
python3 scripts/prune_execute.py --repo "$(pwd)" --receipt <diagnose.json> --json
L9_GIT_PRUNE_AUTHORIZED="<reason>" python3 scripts/prune_execute.py \
  --repo "$(pwd)" --receipt <diagnose.json> --apply
```

Do not treat `repo_hygiene.py --apply` as this close: hygiene only removes
spent+clean residue at sessionEnd.

## Forbidden

- Scoop the dirty shared primary clone
- Copy WIP through public temp
- Apply a stale worktree’s dirty tree as the source of truth
- Mix unrelated `unique_product` themes into one PR
- Delete the source worktree after harvest
- Treat `repo_hygiene.py --apply` as harvest (that tool only deletes landed residue)
