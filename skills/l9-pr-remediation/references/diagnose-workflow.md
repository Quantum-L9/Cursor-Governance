<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: diagnose_workflow
tags: [pr, diagnose, review, blockers, readiness]
owner: igor_beylin
status: active
version: 1.5.0
updated: 2026-09-05
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
2. **Digest first (mandatory).** Read `skills/l9-pr-digest/SKILL.md`. Bind exact base/head and run:

```bash
python3 skills/l9-pr-digest/scripts/pr_digest.py \
  --repo {owner}/{repo} --pr-number {n} --workspace "$PWD" \
  --output .l9/pr/pr-digest-result.json
python3 skills/l9-pr-digest/scripts/require_digest.py \
  --path .l9/pr/pr-digest-result.json --mode diagnose
```

Do **not** pass `--quiet` on a manual `/pr` or Diagnose invoke. Show the `[digest]` stream and interactive unpack in chat, then continue. `--quiet` is for poll-worker / automation only.

If the head moved, discard the stale file and re-run. A valid non-READY decision still continues. An unbound or missing digest is STOP / `Unknown` for that PR. Carry `decision`, `expansion_items`, and `remediation_packet` into the verdict below. Do not re-invent intent, expansion, or CI the digest already bound.
3. **Discovery (mandatory reviews)**

```bash
gh pr view {number} --json title,author,files,additions,deletions,baseRefName,headRefName,mergeable,reviewDecision,statusCheckRollup
gh pr diff {number} --stat
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | {path, line, body, author: .user.login}'
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '.[] | {state, body, author: .user.login}'
gh pr checks {number}
```

GATE: review comments fetched before any verdict. Attribute `github-code-quality[bot]` and Copilot as [code-review agents](code-review-agents.md) and list every unanswered member comment under Review Comments / Merge Blockers.

4. **Optional policy** — if present, load `config/policies/pr_merge_policy.yaml`, `config/policies/protected_files.yaml`, `.github/pr_review_config.yaml` for size/protected notes. Skip with `Unknown` when absent.
5. **Optional angles** — when user asks for focused review, load [review-angles.md](review-angles.md).
6. **Synthesize blockers** — from unresolved reviews (humans + all bots + code-review agents), failing checks + failed-job logs, protected files, merge conflicts, and the digest decision. Also list file-overlap across other open PRs (advisory). For Converge, after `RUN_CONTRACT`, ingest only the PR about to be edited, and only when `require_digest.py --mode converge` is PASS.
7. **Present inline** — format below. Load `l9-ynp` for yes/no/proceed when useful. Diagnose YNP must not emit `gh pr merge`.
8. **Stop.** Diagnose never merges. If the user wants merge, tell them to invoke `/l9-pr-remediation` (Converge). Load [merge-advise.md](merge-advise.md) only as advise.

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

### Digest
- **Decision:** {READY_FOR_REMEDIATION | READY_WITH_NON_BLOCKING_NOTES | NARROW_BEFORE_REMEDIATION | ARCHITECTURE_REPAIR_BEFORE_REMEDIATION | CI_OR_EXECUTION_FAILURE | INTENT_UNKNOWN_REVIEW_REQUIRED | BLOCKED | UNKNOWN}
- **Base/Head bound:** {base_sha} / {head_sha}
- **Expansion / narrowing:** {summary or none}

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
| Skip digest when PR number is known | HIGH — block verdict |
| Hide digest stream behind JSON on a manual Diagnose | HIGH — stream findings |
| Skip review comments | HIGH — block verdict |
| Commit/push/merge during Diagnose | CRITICAL |
| Emit `gh pr merge` from Diagnose YNP | CRITICAL |
| Alignment/gap/deep-eval theater | HIGH — do not emit |
| Manual file write from PR diff | CRITICAL — see merge-advise.md |
