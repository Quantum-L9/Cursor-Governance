<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: diagnose_workflow
tags: [pr, diagnose, review, blockers, readiness]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-16
/L9_META -->

# Diagnose Workflow (read-only)

Read-only PR readiness. **Never** commit, push, or edit the worktree for fixes.
**Forbidden:** alignment %, gap matrix, deep-eval scores, repo-index theater, babysit loops.

When Converge loads this file it is the **per-PR ingest** half of [remediation-plan.md](remediation-plan.md) after [run-contract.md](run-contract.md). Diagnose-only still presents the slim verdict below, plus an overlap advisory across open PRs, and stops. Never merge.

## Usage

```text
/pr #45
# or: review PR readiness / merge blockers
```

## Steps

1. **Identify PR** — number/URL from user or list open PRs. STOP if missing.
2. **Discovery (mandatory reviews)**

```bash
gh pr view {number} --json title,author,files,additions,deletions,baseRefName,headRefName,mergeable,reviewDecision,statusCheckRollup
gh pr diff {number} --stat
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | {path, line, body, author: .user.login}'
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '.[] | {state, body, author: .user.login}'
gh pr checks {number}
```

GATE: review comments fetched before any verdict. Attribute `github-code-quality[bot]` and Copilot as [code-review agents](code-review-agents.md) and list every unanswered member comment under Review Comments / Merge Blockers.

3. **Optional policy** — if present, load `config/policies/pr_merge_policy.yaml`, `config/policies/protected_files.yaml`, `.github/pr_review_config.yaml` for size/protected notes. Skip with `Unknown` when absent.
4. **Optional angles** — when user asks for focused review, load [review-angles.md](review-angles.md).
5. **Synthesize blockers** — from unresolved reviews (humans + all bots + code-review agents), failing checks + failed-job logs, protected files, merge conflicts. For Converge, this list is the census that the remediation plan must cover 1:1.
6. **Present inline** — format below. Load `l9-ynp` for yes/no/proceed when useful.
7. **Merge** — only after explicit user confirm; load [merge-advise.md](merge-advise.md). Diagnose itself does not merge.

## Inline output

```markdown
## PR #{number} Diagnose: {title}

**Author:** @{author} | **Files:** {count} | **+/-:** {additions}/{deletions}
**Base/Head:** {base} ← {head} | **Mergeable:** {mergeable} | **Review:** {reviewDecision}

### Review Comments
- **Reviews:** {review_count}
- **Unresolved / key concerns:** {bullets}
- **Code-review agents:** {github-code-quality / Copilot comment count, unanswered count}

### CI / Checks
- {pass/fail/pending summary}

### Protected Surface (if policy present)
- `{path}` — {note}

### Merge Blockers ({count})
| # | Blocker | Source | Severity | Resolution |

### Merge Warnings ({count})
| # | Warning | Source | Notes |

**Merge Verdict:** MERGE | MERGE WITH CONDITIONS | BLOCKED

### YNP
**YES:** Merge PR (after confirm)
**NO:** Block — list resolutions
**PROCEED:** `gh pr merge {number} --squash --delete-branch`
```

## Enforcement

| Rule | Severity |
|------|----------|
| Skip review comments | HIGH — block verdict |
| Commit/push during Diagnose | CRITICAL |
| Alignment/gap/deep-eval theater | HIGH — do not emit |
| Manual file write from PR diff | CRITICAL — see merge-advise.md |
