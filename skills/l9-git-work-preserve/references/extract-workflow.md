# Extract workflow

Local-only mutation. Never deletes the source ref.

1. Require a diagnosis receipt with unique commits or paths.
2. Create `git worktree add -b <new-branch> <path> <start-point>` (prefer dedicated worktree).
3. Cherry-pick or path-limited commits onto the new branch.
4. Record extract receipt: source tip SHA, new branch, worktree path, file list.
5. Leave source ref intact for human follow-up.

Dirty/untracked leftover across **sibling worktrees** (including `WIP/`): use
[harvest-workflow.md](harvest-workflow.md) first. That classifier is the
repeatable harvest component. This file stays the one-ref cherry-pick path.

Forbidden: reset/checkout on a dirty shared primary clone to perform extract.
