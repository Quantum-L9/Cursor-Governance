<!-- L9_META
layer: reference
role: pr_lifecycle
tags: [git, github, pr, remediation]
status: active
-->
# Pull Request Lifecycle

## Before staging

- Confirm exact base/head repositories and branches.
- Inspect staged and unstaged diffs.
- Run PR-pack validation.
- Stage only approved paths with explicit path arguments. Never use `git add .`, `git add -A`, or `git add --all`.

## Commits

Use dependency-ordered, independently green commits. A useful default:

1. `chore(contract): align declarations and lock state`
2. `feat(governance): establish canonical repository control plane`
3. `test(governance): enforce drift and negative cases`
4. `ci(governance): consume canonical entrypoints`

Adapt scopes to the repository. Do not create empty ceremony commits.

## PR creation

Reuse an existing matching PR. Otherwise create one draft PR with exact base/head, a generated body, validation evidence, risks, rollback, and remaining debt. Create at most one PR.

## Check remediation

Classify every failure:

- caused by renovation and in scope: fix, validate, commit, push when authorized;
- pre-existing: prove against the pinned baseline and report;
- external or unavailable: report exact provider/check and preserve local evidence;
- scope-changing: halt and revise the contract before editing.

Before each remediation push, rerun the smallest failing test plus the full contract gate required for that checkpoint.

## Handoff

Stop when required checks are green and in-scope review threads are resolved. Report PR, commits, changed files, validation, risks, rollback, and any external debt. Never merge without separate authorization.
