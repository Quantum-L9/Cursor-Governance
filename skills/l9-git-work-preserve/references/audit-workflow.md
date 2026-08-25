# Audit workflow

Default mode. Read-only.

## Steps

1. Resolve `--repo` (default cwd) and confirm it is a git work tree.
2. Run `scripts/inventory_git_work.py --repo <path> --json`.
3. Summarize for the human: unpushed tips, dirty paths, worktrees, orphans (`gone` upstream), ahead/behind vs `origin/main`, stash list (metadata only).
4. Do **not** mutate. Offer next mode: `diagnose-value` for candidates,
   `harvest` for leftover worktree dirt/WIP, or `extract` / `prune-propose`.

## Commands (deterministic)

```bash
python3 scripts/inventory_git_work.py --repo "$(pwd)" --json
```
