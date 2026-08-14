---
name: git-work-preserve
version: "1.0.0"
description: "Diagnose-first audit/extract/prune-propose for local git work — never lose unique commits"
auto_chain: ynp
---

# /git-work-preserve — Preserve Git Work

## WHAT IT DOES

Delegates to skill **`l9-git-work-preserve`**:

| Mode | When |
|------|------|
| `audit` (default) | Inventory unpushed / dirty / worktrees / orphans / stashes |
| `diagnose-value` | Prove unique value of a ref vs `origin/main` |
| `extract` | Move unique work to a new branch/worktree (keeps source) |
| `prune-propose` | Report-only delete candidates + receipts |
| `prune-execute` | Only with user auth + `L9_GIT_PRUNE_AUTHORIZED` |

Stash drop requires deep analysis + `L9_GIT_STASH_DROP_AUTHORIZED`.

## EXECUTION

1. Load skill `l9-git-work-preserve`.
2. Default to `audit` unless the user names another mode.
3. Run `python3 skills/l9-git-work-preserve/scripts/inventory_git_work.py --repo "$(pwd)" --json`.
4. For candidates, run `diagnose_ref_value.py` before any mutation.
5. Obey Diagnose-First + rule `88-shared-worktree-isolation` (use a worktree; do not thrash a shared dirty clone).
6. Auto-chain `/ynp`.

## FORBIDDEN

- Broad `git add -A` / scooping foreign dirty paths
- Stash drop / branch delete without auth env + receipt
- Claiming a branch is worthless from age alone
