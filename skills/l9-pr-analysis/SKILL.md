---
name: l9-pr-analysis
description: Analyze pull requests, review comments, merge blockers, gap status, and adoption strategy. Use when the user asks about a PR, merge decision, review findings, or PR readiness.
---

---
name: pr
version: "12.0.0"
description: "PR analysis with code review comments, gap analysis, deep evaluation, merge blockers, and git-native adoption"
before_chain: rules
auto_chain: ynp
strict_mode: true
workflow_injection: true
policy_file: "config/policies/pr_merge_policy.yaml"
---

# /pr — PR Analysis & Gap Assessment (INTELLIGENCE MODE)

## USAGE

```
/pr #45              # Analyze specific PR with full intelligence
/pr #45,#46          # Batch analyze (sequential)
```

## 🚨 CRITICAL: ADOPTION = MERGE (NOT MANUAL WRITE)

**Policy:** `config/policies/pr_merge_policy.yaml`

```
┌──────────────────────────────────────────────────────────────────────┐
│  MERGE THE PR = ADOPT THE FILES                                      │
│  Git handles file transfer. NEVER manually write PR files.             │
│                                                                      │
│  ❌ WRONG: Read diff → Write each file manually                      │
│  ✅ RIGHT: Analyze → Approve → Merge PR → Git brings in files        │
│                                                                      │
│  VIOLATION: Manual file write from PR diff = CRITICAL governance     │
│             violation. Revert and re-merge via git.                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 EXECUTION MODEL (ADR-0059 + ADR-0060)

```
ANALYSIS (Intelligence)               ADOPTION (Git-Native)
┌─────────────────────────┐           ┌─────────────────────────┐
│ Phases 0-6: Analysis    │           │ MERGE: gh pr merge      │
│ Present findings INLINE │  ──YNP──► │ CHERRY: /harvest + git  │
│ Recommend action        │           │ Git does file transfer  │
└─────────────────────────┘           └─────────────────────────┘
```

---

## 📋 INLINE OUTPUT FORMAT (v10.0.0)

Present analysis directly in chat using this structure:

```markdown
## PR #{number} Analysis: {title}

**Author:** @{author} | **Files:** {count} | **Tier:** {tier}
**📏 Size:** {LOC_total} lines ({status_size}) | **🔒 Protected:** {count_protected} files touched

### 🗨️ Review Comments Summary
- **Reviews:** {review_count} ({approved}/{changes_requested}/{commented})
- **Unresolved threads:** {unresolved_count}
- **Key reviewer concerns:** {bullet_list_of_concerns}

### 📊 File Status & Delta

| File | Status | LOC (Repo/PR) | Delta | Alignment | Notes |
|------|--------|---------------|-------|-----------|-------|
| `path/file.py` | ✅/⚠️/🆕/🔄 | 100/120 | +20 | 95% | ... |

### 🔒 Protected Surface Check
- `file1.py` — **LCTO Approval Required**
- `file2.py` — **Subsystem Protected**

### 🎯 Alignment & Suggested Fixes
- **Alignment Score:** {avg_alignment}%
- **Misalignment:** PR uses `print()`, repo uses `structlog`
- **Suggested Fix:** Replace `print` with `logger.info` in `file.py:45`

### 📐 Gap Analysis (vs target)

| Dimension | Coverage % | Gap % |
|-----------|------------|-------|
| Structure | N% | N% |
| Error handling | N% | N% |
| Security posture | N% | N% |
| Tests / verification | N% | N% |
| ... | ... | ... |

### 🔍 Deep Evaluation

| Metric | Score |
|--------|-------|
| Structure | N% |
| Quality | N% |
| Compliance | N% |
| Tech Debt | N% |

**Auto-Fix Candidates:**
- 🤖 AUTO: {list}
- 🔧 SEMI: {list}
- 👤 MANUAL: {list}

### 💥 Impact & Regression
- **Impact:** Affects {count} downstream files (via `imports.txt`)
- **Regression Check:** Touched files covered by {test_count} tests. Status: {test_status}

### 🚫 Merge Blockers ({count})
| # | Blocker | Source | Severity | Resolution |
|---|---------|--------|----------|------------|

### ⚠️ Merge Warnings ({count})
| # | Warning | Source | Notes |
|---|---------|--------|-------|

**Merge Verdict:** ✅ MERGE / ⚠️ MERGE WITH CONDITIONS / 🚫 BLOCKED

### /ynp

**YES:** Merge PR (zero blockers, alignment high)
**NO:** Block (blockers present — list what must be resolved)
**PROCEED:** `gh pr merge {number} --squash --delete-branch`
```

---

## FLOW (GATED)

```
/rules → MEMORY INJECT → CONFIG LOAD → DISCOVERY + REVIEW COMMENTS → INDEX SCAN → INTELLIGENCE ANALYSIS → GAP + DEEP EVAL → MERGE BLOCKERS → INLINE PRESENTATION → USER CONFIRM
         [GATE 1]        [GATE 2]      [GATE 3]                       [GATE 4]     [GATE 5]                [GATE 6]           [GATE 7]        [GATE 8]               [GATE 9]
```

---

## 🔒 PHASE 0: MEMORY INJECTION [GATE 1]

```bash
python3 agents/cursor/cursor_memory_client.py search "PR merge lessons errors"
python3 agents/cursor/cursor_memory_client.py search "{pr_component} patterns"
```

---

## 🔒 PHASE 1: CONFIG LOAD [GATE 2]

Load review policies, merge policy, and protected file lists:

```bash
cat config/policies/pr_merge_policy.yaml    # MANDATORY: Merge workflow rules
cat .github/pr_review_config.yaml           # Size limits, audit scopes
cat config/policies/protected_files.yaml    # Protected file definitions
```

**GATE 2:** Merge policy, size limits, protected files, and audit scopes loaded into context.

---

## 🔒 PHASE 2: DISCOVERY + REVIEW COMMENTS [GATE 3]

```bash
gh pr view {number} --json title,author,files,additions,deletions,baseRefName,headRefName
gh pr diff {number} --stat
gh pr diff {number}
```

### 🗨️ Code Review Comments (MANDATORY)

**Always read review comments before evaluating.** Reviewers may have flagged blockers, requested changes, or approved with conditions.

```bash
# Fetch all review comments (inline code comments)
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | {path: .path, line: .line, body: .body, author: .user.login, created: .created_at}'

# Fetch top-level review threads (approve/request-changes/comment)
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '.[] | {state: .state, body: .body, author: .user.login}'
```

Extract from review comments:
- **Requested changes** — these are potential merge blockers
- **Unresolved threads** — open conversations that need resolution
- **Approval conditions** — "LGTM but fix X first"
- **Flagged risks** — reviewer-identified concerns about security, performance, or correctness

Carry these forward into Phase 5 (Intelligence Analysis) and Phase 6 (Gap + Deep Eval).

**GATE 3:** PR metadata fetched, LOC deltas calculated, tier classified, **review comments extracted**.

---

## 🔒 PHASE 3: INDEX SCAN [GATE 4]

Query indexes to find existing versions and dependencies:

```bash
grep -i "{ClassName}" reports/repo-index/class_definitions.txt
grep -i "{function}" reports/repo-index/function_signatures.txt
grep "{path}" reports/repo-index/imports.txt
grep "{path}" reports/repo-index/test_catalog.txt
```

---

## 🔒 PHASE 4: INTELLIGENCE ANALYSIS [GATE 5]

Perform the 7-section intelligence audit:

1.  **Size Check:** Compare additions/deletions against `size_limits` in `pr_review_config.yaml`.
2.  **Protected Check:** Cross-reference changed files with `protected_files` in config.
3.  **LOC Delta:** Calculate per-file churn (repo vs PR).
4.  **Alignment Score:** Compare PR patterns (error handling, logging, async) with repo standards.
5.  **Suggested Fixes:** Identify ADR violations (e.g., ADR-0019 print check) and propose fixes.
6.  **Impact Analysis:** Trace downstream effects using `imports.txt`.
7.  **Regression Check:** Identify relevant tests from `test_catalog.txt`.
8.  **Review Comment Integration:** Cross-reference reviewer-flagged issues from Phase 2 with findings above. Reviewer concerns that align with detected gaps get elevated priority.

---

## 🔒 PHASE 5: GAP ANALYSIS + DEEP EVALUATION [GATE 6]

Combines `/gap-analysis` dimensions with `/analyze+evaluate` cross-referencing on PR-touched files.

### Gap Analysis (from /gap-analysis)

For each file touched by the PR, score against target state:

| Dimension | Coverage % |
|-----------|------------|
| Structure | N% |
| Lifecycle | N% |
| Async / Concurrency | N% |
| Error handling | N% |
| Observability | N% |
| Configuration | N% |
| Security posture | N% |
| Tests / verification | N% |

Report only gaps where **Gap % > 0** (target − current).

### Deep Evaluation (from /analyze+evaluate)

Cross-reference structure issues with compliance gaps:

| Metric | Score |
|--------|-------|
| Structure | N% |
| Quality | N% |
| Compliance | N% |
| Tech Debt | N% |

### Auto-Fix Classification

| Category | Time | Criteria |
|----------|------|----------|
| 🤖 AUTO | <1min | imports, formatting, bare except, missing `ondelete=` |
| 🔧 SEMI | 1-5min | docstrings, timeouts, packet logging, ACL tightening |
| 👤 MANUAL | >5min | refactoring, architecture, security model redesign |

---

## 🔒 PHASE 6: MERGE BLOCKERS [GATE 7]

Synthesize all prior phases into a definitive **merge/block** verdict.

### Blocker Sources

Aggregate blockers from ALL phases:

| Source | Blocker Type | Examples |
|--------|-------------|----------|
| **Review comments** (Phase 2) | Requested changes, unresolved threads | "Fix SQL injection on line 45" |
| **Protected files** (Phase 4) | Missing LCTO/subsystem approval | `executor.py` touched without approval |
| **Alignment** (Phase 4) | ADR violations in PR code | `print()` instead of `structlog` |
| **Gap analysis** (Phase 5) | Critical security/test gaps | 0% test coverage on new endpoints |
| **Deep eval** (Phase 5) | Quality below threshold | Structure < 50% or Compliance < 50% |
| **CI failures** (if applicable) | Code failures (not infra) | Test failures, lint errors |

### Merge Blocker Report

```markdown
### 🚫 Merge Blockers ({count})
| # | Blocker | Source | Severity | Resolution |
|---|---------|--------|----------|------------|
| 1 | ... | Review comment / Gap / Protected / CI | CRITICAL/HIGH/MEDIUM | What needs to happen |

### ⚠️ Merge Warnings ({count})
| # | Warning | Source | Notes |
|---|---------|--------|-------|
| 1 | ... | ... | Non-blocking but should be addressed |
```

**Merge verdict:**
- **✅ MERGE** — Zero blockers, warnings acceptable
- **⚠️ MERGE WITH CONDITIONS** — Zero blockers, warnings should be tracked
- **🚫 BLOCKED** — One or more blockers must be resolved first

---

## 🔒 PHASE 7: INLINE PRESENTATION [GATE 8]

**Present analysis INLINE using v12.0.0 format. NO file generation.**

Include ALL sections: file delta, protected check, alignment, gap analysis, deep eval, merge blockers, and /ynp recommendation.

---

## 🔒 PHASE 8: USER CONFIRMATION [GATE 9]

Wait for user to:
- **Confirm:** "yes" / "proceed" / "merge"
- **Modify:** User provides corrections
- **Reject:** "no" / "stop"

---

## 🔒 PHASE 9: EXECUTION [GATE 10]

After user confirms, use git-native adoption per `config/policies/pr_merge_policy.yaml`:

### Method 1: GitHub Merge (Preferred)

```bash
gh pr merge {number} --squash --delete-branch -b "{summary}"
```

Use when: PR is mergeable and CI passes (or CI failures are infrastructure-only).

### Method 2: Local Rebase Merge (Conflicts or CI Issues)

```bash
# 1. Stash local changes
git stash push -m "WIP before PR {number} merge"

# 2. Fetch and checkout PR branch
git fetch origin {pr_branch}:pr-{number}-branch
git checkout pr-{number}-branch

# 3. Rebase on main
git rebase origin/main
# Resolve conflicts if any, then: git add . && git rebase --continue

# 4. Merge to main
git checkout main
git merge pr-{number}-branch --no-edit -m "{commit_message}"

# 5. Push (triggers CI on main)
git push origin main

# 6. Cleanup
git branch -d pr-{number}-branch
git stash pop
```

Use when: PR has merge conflicts OR GitHub merge blocked by CI infrastructure issues.

### Method 3: Cherry-Pick (Partial Adoption)

```bash
gh pr diff {number} > /tmp/pr_{number}.diff
git apply --include='{path/to/wanted/*}' /tmp/pr_{number}.diff
```

Use when: Only specific files needed (via `/harvest`).

---

## 🚨 ENFORCEMENT RULES

| Rule | Response | Severity |
|------|----------|----------|
| Skip Config Load | ❌ BLOCK | HIGH |
| Skip Protected Check | ❌ BLOCK | HIGH |
| **Skip Review Comments** | ❌ BLOCK | **HIGH** |
| No LOC Delta | ❌ BLOCK | MEDIUM |
| No Alignment Score | ❌ BLOCK | MEDIUM |
| **No Gap Analysis** | ❌ BLOCK | **MEDIUM** |
| **No Merge Blocker Assessment** | ❌ BLOCK | **HIGH** |
| **Manual file write from PR diff** | ❌ VIOLATION | **CRITICAL** |
| Missing protected file approval | ❌ BLOCK | HIGH |

### Violation Response

If **manual file write** detected:
1. Revert the manual changes
2. Re-merge via git (Method 1, 2, or 3)
3. Write lesson to memory: `python3 agents/cursor/cursor_memory_client.py write "LESSON: ..." --kind lesson`

---

## 📋 CI FAILURE HANDLING

### Infrastructure Failures (Proceed with Local Merge)

Indicators:
- `steps: 0` in job details (job failed before running)
- Runner allocation timeout
- Workflow syntax errors

Action: Use Method 2 (Local Rebase Merge) — code is sound, CI infra is broken.

### Code Failures (Fix Before Merge)

Indicators:
- Test failures with stack traces
- Lint/type errors in changed files
- ADR violations in PR code

Action: Fix failures first, then merge.

--- End Command ---
