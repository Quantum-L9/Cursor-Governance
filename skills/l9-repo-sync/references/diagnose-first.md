<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, diagnose]
status: active
version: 1.2.0
updated: 2026-08-22
/L9_META -->

# Diagnose first

On **this** clone (`pwd` / `CURSOR_GOVERNANCE_DIR`), record:

1. `git rev-parse --git-common-dir` (identity — must be unchanged after ff)
2. current branch
3. `git status --porcelain` (dirty vs clean)
4. `git worktree list`
5. whether **this branch** can ff onto `origin/<branch>`:
   `git rev-list --count HEAD..origin/<branch>` (ahead/behind only).
   Do not change branches.

Optional inventory (do not copy the script):

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  skills/l9-git-work-preserve/scripts/inventory_git_work.py \
  --repo "<absolute-named-clone>" --json
```

Use the worktree `.venv` if the SSOT interpreter is missing.

Dirty, unique commits, and untracked are **not** a stop. `/ff` parks them
(preserve branch, dirty ref, hold directory) then uses `git reset --keep`.
That primitive keeps unique untracked and `.venv`. It does **not** delete
files to unblock catch-up.

If the clone is not on `main`, that is **not** a stop. `ff.sh` parks dirt
then `git switch`es to `main`; the feature branch ref stays. Do not reset a
feature branch onto `origin/main`. Extra worktrees use
`worktree_add_wired.sh` only when the user asked for a new tree.
