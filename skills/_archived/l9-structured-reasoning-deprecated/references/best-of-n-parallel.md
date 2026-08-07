<!-- L9_META
l9_schema: 1
origin: folded from governance-v2 dev-best-of-n-solving
tags: [best-of-n, parallel, worktrees, decision]
status: active
/L9_META -->

# Best-of-N Parallel Solving

When a problem has multiple viable strategies and "just try it" beats more analysis — complex refactors, tricky bugs, performance work, or pattern choices — solve N approaches in parallel and pick the winner.

## Workflow

1. **Define 2–3 distinct strategies** up front. Example (slow query): (A) composite index + rewrite, (B) materialized view, (C) application-level cache.
2. **Launch parallel runners** — one `Task` with `subagent_type: "best-of-n-runner"` per strategy, all in a single message so they run concurrently. Each runner gets its own git branch + worktree (fully isolated). Put clear success criteria in each prompt (e.g. "run the tests and report pass/fail", "measure query time"), plus the exact file paths and problem statement.
3. **Compare results** — which passes all tests? cleanest implementation? best performance? easiest to maintain?
4. **Merge the winner** — check out / cherry-pick the winning branch; clean up the other worktree branches.

## Notes
- Runners are isolated — they can't see each other's changes; branches are real and inspectable.
- Overkill for simple problems — use a single agent instead.
