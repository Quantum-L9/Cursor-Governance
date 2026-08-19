<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: diagnose_workflow
tags: [pr, diagnose, review, blockers, readiness]
owner: igor_beylin
status: active
version: 1.4.0
updated: 2026-08-18
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
5. **Synthesize blockers** — from unresolved reviews (humans + all bots + code-review agents), failing checks + failed-job logs, protected files, merge conflicts. Also list file-overlap across other open PRs (advisory). For Converge, after `RUN_CONTRACT`, ingest only the PR about to be edited.
6. **Present inline** — format below. Load `l9-ynp` for yes/no/proceed when useful. Diagnose YNP must not emit `gh pr merge`.
7. **Stop.** Diagnose never merges. If the user wants merge, tell them to invoke `/l9-pr-remediation` (Converge). Load [merge-advise.md](merge-advise.md) only as advise.

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
- {pass/fail/pending summary — only from `gh pr checks` / run logs this run}

### State (Diagnose First)
- **Observed:** {head SHA, mergeable, failing checks, unresolved thread count}
- **Expected:** {required checks success, zero unresolved threads, stack-safe}
- **Root cause:** {verified cause or Unknown}
- **Unknowns:** {list or none}
- **Evidence:** {commands actually run}

### Protected Surface (if policy present)
- `{path}` — {note}

### Overlap (advisory)
- {shared files / generated outputs with other open PRs, or none}

### Merge Blockers ({count})
| # | Blocker | Source | Severity | Resolution |

### Merge Warnings ({count})
| # | Warning | Source | Notes |

**Merge Verdict:** READY | READY WITH CONDITIONS | BLOCKED
(Diagnose verdict is advisory. It is not merge authority.)

### YNP
**YES:** Ready for Converge (`/l9-pr-remediation`) — do not merge from Diagnose
**NO:** Block — list resolutions
**PROCEED:** stay in Diagnose; if merge is wanted, invoke `/l9-pr-remediation`
```

## Enforcement

| Rule | Severity |
|------|----------|
| Skip review comments | HIGH — block verdict |
| Commit/push/merge during Diagnose | CRITICAL |
| Emit `gh pr merge` from Diagnose YNP | CRITICAL |
| Alignment/gap/deep-eval theater | HIGH — do not emit |
| Manual file write from PR diff | CRITICAL — see merge-advise.md |
