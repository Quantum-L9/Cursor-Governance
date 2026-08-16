<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: merge_advise
tags: [pr, merge, diagnose, git]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-16
/L9_META -->

# Merge (Diagnose advise vs Converge action)

**CRITICAL:** Adoption = merge via git. NEVER manually write PR files from a diff.

```text
MERGE THE PR = ADOPT THE FILES
Git handles file transfer. NEVER unpack / copy / rewrite files from `gh pr diff`.
```

Violation: Manual file write from PR diff = CRITICAL — revert and re-merge via git.

## When

- **Diagnose (`/pr`):** advise only. Merge after the user explicitly confirms.
- **Converge (`/l9-pr-remediation`):** merge is authorized. After each PR is
  green + mergeable, with no unanswered codebase or code-review agent threads
  (`github-code-quality[bot]`, Copilot), merge it. Do all open PRs in the
  target repo, oldest first.

Write the receipt before the first `gh pr merge`:

```bash
python3 ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
```

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
- `--admin` / bypass rules
- Merge without user confirm during Diagnose
- Merge a red or conflicted PR
