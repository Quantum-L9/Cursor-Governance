<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: convergence_loop
tags: [pr, convergence, loop, polling, ci, local-verify]
owner: igor_beylin
status: active
version: 3.4.0
updated: 2026-08-18
/L9_META -->

# Convergence Loop

## Purpose

After publishing the **single** planned commit (which has ALREADY passed `make pr-check` + cited-path verify), short-poll CI to confirm, check for new reviews, then decide: converge, exceptional next cycle, or early stop.

A second cycle is **not** the normal path. It is only for signals that did not exist at census time. See [remediation-plan.md](remediation-plan.md).

## Key Principle: Local-First, Independently Confirmed

`make pr-check` is the local gate. Remote CI is an **independent** confirmation, not a discovery loop and not implied by local `Passed`.

- Do not publish while local verify is `Failed` or `Unknown`.
- If remote CI finds something local verify missed, classify the delta (`CODEBASE` / `ENVIRONMENT` / `CI_PIPELINE`). That is not automatic protocol failure.
- Document any local/remote delta as a finding for the next cycle.
- Status vocabulary: `Passed` / `Failed` / `Skipped` / `Unknown` / `NotApplicable`. Do not claim remote `Passed` until `gh run view` (or equivalent) shows it on the exact head SHA.

## Loop Architecture

```text
┌─────────────────────────────────────────────────────────┐
│              REMEDIATION CYCLE                            │
│                                                          │
│  census → plan (GATE) → fix ALL → make pr-check (GATE)   │
│  commit (ONE) → sanctioned publish (ONE)                 │
│                                                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              CONVERGENCE CHECK                            │
│                                                          │
│  1. Wait for CI completion (confirmation only)           │
│  2. Check CI status                                      │
│  3. Check for new review comments                        │
│  4. Evaluate convergence gate                            │
│                                                          │
│  → this PR green: do not merge; continue REMEDIATE_ALL   │
│  → set ready for MERGE_TRAIN after FIRST_MERGE_GATE      │
│  → new post-push comments only: re-census NEW, one more  │
│  → CI failed on env delta: investigate, one more commit  │
│  → skipped census / unrun local gate: protocol failure   │
│  → max cycles: STOP + partial report                     │
└─────────────────────────────────────────────────────────┘
```

## Wait Protocol

### Polling CI Status

After sanctioned publish, poll for CI completion:

```bash
# Get the latest run on the PR branch
gh run list --branch {branch} --limit 1 --json databaseId,status,conclusion
```

Poll interval: **15 seconds**. Max wait: **8 minutes** per cycle.
Prefer `gh run watch` when a run ID is known — do not idle between polls.

If CI hasn't started after 90 seconds, check workflows:
```bash
gh workflow list --json name,state
```

### Prefer watch

```bash
gh run watch {RUN_ID} --exit-status
```

Use when a single run ID is known. Returns exit code 0 on success, non-zero on failure.

### CI Failure After Local Verify Passed

If CI fails despite local verify passing:

1. Fetch the failure logs: `gh run view {RUN_ID} --log-failed`
2. Identify the **delta** — what's different between local and CI:
   - Missing env vars / secrets (expected in CI but not locally)
   - Different Node/Python version
   - Missing system dependencies
   - Network-dependent steps (API calls, package installs)
   - Race conditions in parallel jobs
3. If fixable locally in **source** → fix, re-verify, one more sanctioned publish (counts as the exceptional next cycle if already published).
4. If environment-only → classify `ENVIRONMENT` or `CI_PIPELINE`. Note it. **Do not** edit workflows to skip or weaken the failing job.
5. If unfixable → defer with reason "CI environment delta". Do not merge that PR.

## Convergence Gate

Convergence is reached when ALL conditions are true:

| Condition | Check Method |
|-----------|-------------|
| CI status is `success` | `gh run view --json conclusion` → `"success"` |
| No new unresolved review comments | Compare comment count/timestamps before and after push |
| All review threads resolved | GraphQL `isResolved: false` count is 0 (any author) |
| All code-review agent threads answered | Every `github-code-quality[bot]` / Copilot thread has a canonical reply ([code-review-agents.md](code-review-agents.md)) |
| All blocking findings resolved | Internal tracking: all `blocking` findings have status `fixed` |
| All actionable findings resolved or deferred | Internal tracking |

## Re-Ingestion (When Not Converged)

When convergence gate fails due to new review comments, re-ingest only NEW signals:

1. **New CI failures**: Only failures on the latest run (not carried over from previous).
2. **New review comments**: Only comments with `created_at` after the last push timestamp.
3. **Resolved comments**: Remove from finding list if a thread was resolved.

Do NOT re-process findings already fixed or deferred in previous cycles.

## Cycle Tracking

Maintain state across cycles:

```yaml
cycle_state:
  current_cycle: 1
  max_cycles: 3
  push_timestamps: ["2026-06-17T10:00:00Z"]
  findings_fixed: ["ci-1", "review-3"]
  findings_deferred: ["review-7"]
  findings_remaining: ["ci-2"]
  ci_status_history: ["success"]  # should be success since local verify passed
  local_verify_gates_count: 6
  local_verify_passed_before_push: true
```

## Convergence Report

When converged OR max cycles reached, emit:

```yaml
convergence_status: converged | partial | blocked
cycles_run: {integer}
max_cycles: 3
cycles_exhausted: true | false
pushes_total: {integer}  # should equal cycles_run
commits_total: {integer}  # should equal cycles_run

findings_summary:
  total_ingested: {integer}
  fixed: {integer}
  deferred: {integer}
  remaining: {integer}

ci_gates_discovered: {integer}
local_verify_iterations: {integer}  # total across all cycles
local_verify_green_before_every_push: true | false

local_verify: Passed | Failed | Unknown
remote_ci: Passed | Failed | Unknown
new_comments_after_final_publish: {integer}

deferred_items:
  - id: "review-7"
    reason: "Requires architectural decision — Express vs Fastify"
  - id: "ci-5"
    reason: "Fix caused regression; reverted"

protocol_violations:
  - "None" | list of any batch/verify violations that occurred

minimum_safe_next_action: "wait_first_merge_gate" | "merge_train_oldest_first" | "manual review of deferred items" | "run another cycle"
```

## Stop Conditions

MUST stop the loop when:
- `cycles_run >= max_cycles` → emit `partial`
- CI passes AND no new actionable codebase signals → emit `converged` for **this PR**. Do not merge until FIRST_MERGE_GATE. Then MERGE_TRAIN.
- Only `CI_PIPELINE` / `HUMAN` / `ENVIRONMENT` blockers remain → emit `partial` early (more cycles cannot help); do not merge that PR
- Poll worker `merge_eligible` on a stale SHA → ignore; never merge from it
- A fix causes an unrecoverable regression → emit `blocked`
- GitHub API is rate-limited and retry fails → emit `blocked`
- User sends a stop signal → emit `partial` with current state

## Configuration

Defaults (overridable by user):

```yaml
max_cycles: 3                  # safety valve; success path is 1 commit
one_and_done: true
poll_interval_seconds: 15
max_wait_per_cycle_minutes: 8
max_local_verify_iterations: 5
auto_fix_nits: true           # clear one-line nits; skip only true product forks
skip_bot_discussions: true     # skip non-actionable chatter from non-CRA bots only; NEVER skip github-code-quality or Copilot
parallel_clusters: true        # always parallelize independent clusters
forbid_no_verify: true
require_precommit_all_hooks: false
require_precommit_all_files: false
prefer_makefile: true
makefile_primary: pr-check
oldest_created_at_default: true
stack_safe: true
```
