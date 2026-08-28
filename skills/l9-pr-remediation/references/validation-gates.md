<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: validation_gates
tags: [pr, validation, enforcement, checkpoints, artifacts, makefile]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-08-28
/L9_META -->

# Validation Gates (Enforcement Layer)

## Purpose

Prevent protocol violations with lightweight **inline** proofs at each step (logged in the cycle, not packaged as deliverables). No tarballs, run-report schemas, or issue-file bundles.

## Gate Architecture

```text
P_cmd ──→ [GATE A] ──→ ingest/classify ──→ [GATE B] ──→ fix ──→ [GATE C]
  ──→ make precommit-repo ──→ [GATE D] ──→ commit + git push ──→ [GATE E]
  ──→ replies ──→ [GATE F] ──→ next PR / MERGE_TRAIN (no CI poll)
```

Each gate requires a specific artifact. If the artifact is missing or invalid, the agent MUST NOT proceed.

## Gate A: Command surface discovered

**After `P_cmd`**

Required artifact:
```yaml
gate_registry:
  makefile: true
  public:
    verify: "make precommit-repo"
    publish: "git push"
    improve: "make improve"   # optional
  leftover_workflow_run: []   # only when makefile precommit-repo is absent
```

Validation:
- [ ] `verify` is `make precommit-repo` and remediator `publish` is `git push`
- [ ] Ceremony `make pr-check` / `PR_REMEDIATE=0 make pr` are named only as do-not-run
- [ ] INTERNAL targets (`pr-preflight`, `precommit`, `pr-full`) are not the cached shipping verbs
- [ ] Workflow `run:` leftover is empty when `precommit-repo` exists

**STOP if:** the agent cached ceremony `make pr` / `make pr-check` as this skill's verbs.

Repos with no Makefile and no workflows: ask whether CI is configured; record `Unknown`.

## Gate B: Ingestion and Classification Complete

**After ingest + classify**

Required artifact:
```yaml
classified_findings:
  blocking: [{count}]
  actionable: [{count}]
  discussion: [{count}]
  deferred: [{count}]
  total: {integer}

execution_plan:
  cycle_scope: ["{finding-id}", ...]
  estimated_files: ["{file_path}", ...]
  local_verify_commands: ["PR_BASE=origin/main make precommit-repo"]
  makefile_targets: ["precommit-repo"]
  cited_paths: ["{file_path}", ...]
```

Validation:
- [ ] This PR's ingest covers failed CI + humans + bots + code-review agents (lazy scanners)
- [ ] Every finding has `id`, `source`, `ownership`, `disposition`, `evidence`, `root_cause` ([remediation-plan.md](remediation-plan.md))
- [ ] Every `disposition: fix` has confidence `high` or `medium` (not `Unknown`)
- [ ] If `total == 0` and CI is green: conversation-only path — skip to replies / MERGE_TRAIN, **do not** treat as “already merged”
- [ ] `cycle_scope` is non-empty **or** all dispositions are reply/defer/note
- [ ] `cited_paths` lists every finding path (verified even if the default toolchain excludes it)
- [ ] `makefile_targets` is `precommit-repo` when a Makefile exists
- [ ] No file edits have been made yet

**STOP if:** Plan is incomplete — do not patch.

## Gate C: All Fixes Applied (Pre-Verify)

**After applying planned `disposition: fix` clusters**

Required artifact:
```bash
git diff --stat
```

Validation:
- [ ] If `cycle_scope` has `fix` items: `git diff --stat` is non-empty
- [ ] If `cycle_scope` is reply-only: empty diff is OK — skip to Gate F
- [ ] Number of files changed is reasonable (≤ `estimated_files` count + companions + hook autofix tolerance)
- [ ] No unrelated files modified (compare against `estimated_files`)
- [ ] ALL findings in `cycle_scope` have been addressed (internal tracking)

**STOP if:** Diff is empty **and** `fix` items remain.

## Gate D: Local Verify Passed (CRITICAL GATE)

**After `make precommit-repo`**

Required artifact:
```yaml
local_verify_log:
  iteration: {integer}  # which attempt (1-5)
  timestamp: "{ISO}"
  command: "PR_BASE=origin/main make precommit-repo"
  exit_code: 0
  cited_paths_checked: true
  result: Passed | Failed | Unknown
```

Validation:
- [ ] `result: Passed` before commit on a code-changing PR
- [ ] Remote CI is not recorded here (independent later)
- [ ] `make precommit-repo` ran (hooks plus ruff). Did **not** run `make pr-check`
- [ ] cited/planned paths were checked even if the default toolchain excludes them
- [ ] `iteration <= 5`
- [ ] Commit will not use `--no-verify`
- [ ] Did **not** require `pre-commit --all-files` or replay every workflow `run:`

**STOP if:** `result` is not `Passed` after iteration 5 → defer problematic findings, re-run verify on remaining.

**This gate blocks commit and sanctioned publish.** Conversation-only PRs skip D when there is no diff.

## Gate E: Single Commit, Single Publish

**After commit + remediator `git push`**

Required artifact:
```yaml
push_record:
  commit_sha: "{full_sha}"
  commit_message: "fix(pr-remediation): resolve {count} findings"
  files_in_commit: {integer}
  publish_count_this_cycle: 1
  publish_command: "git push"
  branch: "{branch_name}"
  published_at: "{ISO timestamp}"
```

Validation:
- [ ] `publish_count_this_cycle == 1`
- [ ] `commit_sha` is a valid 40-char hex string
- [ ] Commit message follows `fix(pr-remediation): resolve {count} findings` plus `Remediation-Cycle:` trailer
- [ ] `git log --oneline HEAD~1..HEAD` returns exactly 1 line
- [ ] Publish was remediator `git push` of the already-open PR branch, not `make pr`

**STOP if:** Publish failed → check auth, remote, branch protection. Ask user if needed.

## Gate F: Review Replies Complete

**After reply + resolve**

Required artifact:
```yaml
reply_record:
  threads_total: {integer}          # paginated reviewThreads
  threads_replied: {integer}
  threads_resolved: {integer}
  human_deferred_issues: {integer}  # HUMAN Deferred only
  batch_summary_posted: true
  reply_breakdown:
    fixed: {count}
    deferred: {count}
    acknowledged: {count}
    disagreed: {count}
```

Validation:
- [ ] `threads_replied == threads_total` (every thread got a reply)
- [ ] Pagination complete (`hasNextPage` false)
- [ ] Every `github-code-quality[bot]` / Copilot thread is in that reply set
- [ ] `threads_resolved == threads_total` (every thread resolved, any author; HUMAN still resolved)
- [ ] HUMAN Deferred items have a linked issue; other defers do not require an issue
- [ ] `batch_summary_posted: true`
- [ ] Every reply follows canonical format (Format A/B/C/D)

**STOP if:** GitHub API rate limit hit → wait 60s, retry. If still failing, log partial and continue to convergence.

## Protocol Violation Detection

If at ANY point the agent:
- Publishes without Gate D `result: Passed` on a code-changing PR → **VIOLATION: publish-before-verify**
- Makes more than 1 publish per cycle → **VIOLATION: multi-push**
- Commits per-finding or publishes to probe CI → **VIOLATION: not-one-and-done**
- Edits before the plan gate → **VIOLATION: patch-before-plan**
- Skips `make precommit-repo` or uses `--no-verify` → **VIOLATION: skipped-local-verify**
- Uses `make pr-check` / `make pr` / `make precommit` / `--all-files` as the remediator gate → **VIOLATION: wrong-makefile-verb**
- Merges from Diagnose or emits `gh pr merge` in Diagnose YNP → **VIOLATION: diagnose-merge**
- Squash-merges a stack parent or `update-branch` after parent squash → **VIOLATION: stack-unsafe**
- Leaves threads unresolved after Step 7.5 → **VIOLATION: silent-fix**

Violations MUST be:
1. Logged in the convergence report under `protocol_violations`
2. Reported to the user
3. Used to improve the skill (feedback loop)

## Enforcement Mechanism

The agent MUST produce each gate artifact **in the response/working notes** before proceeding. The artifacts serve as:
1. **Proof of compliance** — auditable trail that the protocol was followed
2. **Self-check** — producing the artifact forces the agent to actually do the work
3. **Rollback anchor** — if something goes wrong, the artifacts show exactly where

If an artifact cannot be produced, the agent is stuck at that gate and MUST either:
- Fix the issue preventing artifact production
- Ask the user for help
- Emit a `blocked` convergence status
