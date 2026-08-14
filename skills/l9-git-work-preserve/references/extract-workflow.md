# Extract workflow

Local-only mutation. Never deletes the source ref.

1. Require a diagnosis receipt with unique commits or paths.
2. Create `git worktree add -b <new-branch> <path> <start-point>` (prefer dedicated worktree).
3. Cherry-pick or path-limited commits onto the new branch.
4. Record extract receipt: source tip SHA, new branch, worktree path, file list.
5. Leave source ref intact for human follow-up.

Forbidden: reset/checkout on a dirty shared primary clone to perform extract.
