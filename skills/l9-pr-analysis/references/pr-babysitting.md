<!-- L9_META
l9_schema: 1
origin: folded from governance-v2 dev-babysitting-pr
tags: [pr, ci, merge-ready, loop]
status: active
/L9_META -->

# PR Babysitting (keep a PR merge-ready)

Monitor an open PR and keep it merge-ready: fix CI failures, address clear review comments, resolve conflicts, repeat.

## Loop

1. **Status** — `gh pr view --json number,title,state,mergeable,reviewDecision,statusCheckRollup,comments,reviews` and `gh pr view --json mergeStateStatus`.
2. **CI** — `gh pr checks` for pass/fail/pending per check.
3. **Fix failures** — `gh run view <run-id> --log-failed`, then by type: lint (`--fix`, then manual), type errors (read + fix types), test failures (run suite locally, fix code or intended expectations), build (read output, fix imports/deps). Commit after each.
4. **Review comments** — `gh api repos/{owner}/{repo}/pulls/{pr}/comments`. Apply clear fixes (typo, naming, null check, style). Skip anything needing a design decision and report it.
5. **Conflicts** — `git fetch origin <base> && git merge origin/<base>`, resolve by reading both sides; ask the user on ambiguous ones.
6. **Re-check** — `gh pr checks --watch`; new failures → back to step 3.

## Stop conditions
- All checks green, no unresolved comments, no conflicts → merge-ready (`gh pr ready`).
- **3** fix-push-check cycles attempted without full resolution → report what's still blocking.
- A fix needs a design decision → ask the user.

## Guardrails
Never force-push a shared PR branch. Don't change test assertions to force a pass unless the behavior change was intentional. Don't resolve review comments you're unsure about. Wait for queued/pending CI before analyzing.

> In PlasticOS repos, CI fixes/pushes must follow `make push` / `make pr-check` (see `70-github-push-workflow`), not raw `git push`.
