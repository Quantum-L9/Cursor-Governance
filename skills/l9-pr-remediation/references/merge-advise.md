<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: merge_advise
tags: [pr, merge, diagnose, git]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-07
/L9_META -->

# Merge advise (Diagnose exit)

**CRITICAL:** Adoption = merge via git. NEVER manually write PR files from a diff.

```text
MERGE THE PR = ADOPT THE FILES
Git handles file transfer. NEVER unpack / copy / rewrite files from `gh pr diff`.
```

Violation: Manual file write from PR diff = CRITICAL — revert and re-merge via git.

## When

Only after **Diagnose** presents a verdict and the user explicitly confirms merge.
**Converge never merges** (skill law 12).

## Preferred — GitHub merge

```bash
gh pr merge {number} --squash --delete-branch -b "{summary}"
```

## Local rebase merge (when GitHub merge blocked by infra)

```bash
git stash push -m "WIP before PR {number} merge"
git fetch origin {pr_branch}:pr-{number}-branch
git checkout pr-{number}-branch
git rebase origin/main
git checkout main
git merge pr-{number}-branch --no-edit -m "{commit_message}"
git push origin main
git branch -d pr-{number}-branch
git stash pop
```

PlasticOS: use `make push` instead of raw `git push` when that workflow applies.

## Forbidden

- `git apply` / hand-copy from `gh pr diff` to adopt the PR
- Force-push to main
- Merge without user confirm during Diagnose
