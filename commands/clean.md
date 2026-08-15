---
name: clean
version: "1.0.0"
description: "Ship leftover git work to scoped PRs in the owning repo, prune merged locals, prime main"
auto_chain: ynp
---

# /clean — Workspace ship + reset

Delegates to `make clean` / `ops/scripts/workspace_clean.py`.

## WHAT IT DOES

1. Inventory dirty, untracked, and unpushed work in `WS`.
2. Route each path with `ops/config/workspace-clean-routing.yaml` (fail-closed).
3. Extract unique work into a dedicated worktree per destination repo.
4. Push a scoped feature branch and open a PR (never `main`).
5. Prune local branches that are already ancestors of `origin/main` and not checked out elsewhere.
6. Prime `$HOME/.l9/primed/<dest>` at `origin/main` for the next task.

## EXECUTION

```bash
# preview
CLEAN_MODE=plan make -C "$HOME/.cursor-governance" clean WS="$(pwd)"

# ship
make -C "$HOME/.cursor-governance" clean WS="$(pwd)"
```

Uses skill `l9-git-work-preserve` inventory rules: no `git add -A`, no force-push, no checkout on a dirty shared clone, no delete of unique work.

## FORBIDDEN

- Committing `.env.local` / secrets / `.cursor-commands` / IDE residue
- Pushing to `main` / `master`
- Touching a branch checked out in another agent's worktree
- Guessing a destination when a path matches zero or many repos
