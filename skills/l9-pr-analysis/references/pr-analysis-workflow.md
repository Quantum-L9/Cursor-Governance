<!-- L9_META
l9_schema: 1
parent: l9-pr-analysis
origin: migrated-from pr command v12.0.0
tags: [pr, analysis, merge, blockers, gh]
status: active
/L9_META -->

# PR Analysis Workflow — Intelligence Mode

## Usage

```text
/pr #45
/pr #45,#46
```

## Adoption = merge (not manual write)

```text
MERGE THE PR = ADOPT THE FILES
Git handles file transfer. NEVER manually write PR files from diff.
```

Policy when present: `config/policies/pr_merge_policy.yaml`

## Execution model

```text
ANALYSIS (Phases 0–6) → present INLINE → YNP → ADOPTION (git merge) after user confirm
```

## Inline output format

```markdown
## PR #{number} Analysis: {title}

**Author:** @{author} | **Files:** {count} | **Tier:** {tier}
**Size:** {LOC_total} lines ({status_size}) | **Protected:** {count_protected} files touched

### Review Comments Summary
- **Reviews:** {review_count}
- **Unresolved threads:** {unresolved_count}
- **Key concerns:** {bullets}

### File Status & Delta
| File | Status | LOC (Repo/PR) | Delta | Alignment | Notes |

### Protected Surface Check
- `file.py` — LCTO Approval Required

### Alignment & Suggested Fixes
- **Alignment Score:** {avg}%
- **Misalignment:** {example}
- **Suggested Fix:** {action}

### Gap Analysis (vs target)
| Dimension | Coverage % | Gap % |

### Deep Evaluation
| Metric | Score |
| Structure | N% |
| Quality | N% |
| Compliance | N% |
| Tech Debt | N% |

**Auto-Fix Candidates:** AUTO / SEMI / MANUAL lists

### Impact & Regression
- **Impact:** {downstream count}
- **Regression Check:** {test_status}

### Merge Blockers ({count})
| # | Blocker | Source | Severity | Resolution |

### Merge Warnings ({count})
| # | Warning | Source | Notes |

**Merge Verdict:** MERGE | MERGE WITH CONDITIONS | BLOCKED

### YNP
**YES:** Merge PR
**NO:** Block — list resolutions
**PROCEED:** `gh pr merge {number} --squash --delete-branch`
```

## Gated flow

```text
rules → MEMORY → CONFIG → DISCOVERY + REVIEWS → INDEX → INTELLIGENCE → GAP+EVAL → BLOCKERS → INLINE → USER CONFIRM → EXECUTE
```

## Phase 0 — Memory injection

```bash
python3 agents/cursor/cursor_memory_client.py search "PR merge lessons errors"
python3 agents/cursor/cursor_memory_client.py search "{pr_component} patterns"
```

Skip when memory client absent; note `Unknown`.

## Phase 1 — Config load

```bash
cat config/policies/pr_merge_policy.yaml
cat .github/pr_review_config.yaml
cat config/policies/protected_files.yaml
```

Adapt paths to repo when files differ. GATE: policies loaded before analysis.

## Phase 2 — Discovery + review comments

```bash
gh pr view {number} --json title,author,files,additions,deletions,baseRefName,headRefName
gh pr diff {number} --stat
gh pr diff {number}
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | {path, line, body, author: .user.login}'
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '.[] | {state, body, author: .user.login}'
```

Extract requested changes, unresolved threads, approval conditions, flagged risks. GATE: review comments before eval.

## Phase 3 — Index scan

When `reports/repo-index/` exists:

```bash
grep -i "{ClassName}" reports/repo-index/class_definitions.txt
grep -i "{function}" reports/repo-index/function_signatures.txt
grep "{path}" reports/repo-index/imports.txt
grep "{path}" reports/repo-index/test_catalog.txt
```

## Phase 4 — Intelligence analysis

1. Size check vs `size_limits`
2. Protected file cross-reference
3. Per-file LOC delta
4. Alignment score (logging, async, error handling vs repo)
5. Suggested fixes (ADR violations)
6. Impact via imports
7. Regression via test catalog
8. Elevate reviewer concerns that match findings

## Phase 5 — Gap + deep evaluation

Gap dimensions per touched file: Structure, Lifecycle, Async, Error handling, Observability, Configuration, Security, Tests.

Deep eval metrics: Structure, Quality, Compliance, Tech Debt.

Auto-fix: AUTO (<1min) | SEMI (1–5min) | MANUAL (>5min).

## Phase 6 — Merge blockers

Aggregate from: review comments, protected files, alignment, gap analysis, deep eval, CI code failures.

Verdict: MERGE | MERGE WITH CONDITIONS | BLOCKED.

## Phase 7–8 — Present + user confirm

Inline only. Wait for yes/proceed/no.

## Phase 9 — Execution (after confirm)

### Method 1 — GitHub merge (preferred)

```bash
gh pr merge {number} --squash --delete-branch -b "{summary}"
```

### Method 2 — Local rebase merge

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

PlasticOS: use `make push` instead of raw `git push`.

### Method 3 — Cherry-pick (partial)

```bash
gh pr diff {number} > /tmp/pr_{number}.diff
git apply --include='{path/to/wanted/*}' /tmp/pr_{number}.diff
```

## Enforcement

| Rule | Severity |
|------|----------|
| Skip config load | HIGH |
| Skip protected check | HIGH |
| Skip review comments | HIGH |
| No gap analysis | MEDIUM |
| No merge blocker assessment | HIGH |
| Manual file write from PR diff | CRITICAL |

Violation: revert manual changes; re-merge via git; write lesson to memory when client available.

## CI failure handling

- **Infrastructure** (steps: 0, runner timeout) → Method 2 may apply.
- **Code failures** (tests, lint, ADR in PR) → fix first, then merge.
