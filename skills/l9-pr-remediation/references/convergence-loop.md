<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: convergence_loop
tags: [pr, convergence, loop, ci, local-verify]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-08-28
/L9_META -->

# Convergence Loop

## Purpose

After publishing the **single** planned commit (which has ALREADY passed `make precommit-repo`), continue the next independent PR, then MERGE_TRAIN. Do not poll CI.

A second cycle is **not** the normal path. It is only for signals that did not exist at census time. See [remediation-plan.md](remediation-plan.md).

## Key Principle: Local-First, Independently Confirmed

`make precommit-repo` is the remediator local gate. Remote CI is an **independent** confirmation, not a discovery loop and not implied by local `Passed`. Pytest and conformance stay on CI.

- Do not publish while local verify is `Failed` or `Unknown`.
- If a later snapshot already shows a red required check that names a source file this PR owns, classify the delta (`CODEBASE` / `ENVIRONMENT` / `CI_PIPELINE`). That is not automatic protocol failure.
- Document any local/remote delta as a finding for the next cycle.
- Status vocabulary: `Passed` / `Failed` / `Skipped` / `Unknown` / `NotApplicable`. Do not claim remote `Passed` until `gh run view` (or equivalent) shows it on the exact head SHA.

## Loop Architecture

```text
┌─────────────────────────────────────────────────────────┐
│              REMEDIATION CYCLE                            │
│                                                          │
│  census → plan (GATE) → fix ALL → make precommit-repo    │
│  commit (ONE) → git push (ONE)                           │
│                                                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              NEXT PR, THEN MERGE_TRAIN                    │
│                                                          │
│  1. Record head SHA                                      │
│  2. Re-query reviewThreads                               │
│  3. Continue REMEDIATE_ALL                               │
│  4. FIRST_MERGE_GATE then MERGE_TRAIN                    │
│                                                          │
│  → do not merge because this one PR is green             │
│  → do not wait for required checks                       │
│  → new post-push comments already present: one more      │
│  → skipped census / unrun local gate: protocol failure   │
│  → max cycles: STOP + partial report                     │
└─────────────────────────────────────────────────────────┘
```

## No wait

After remediator publish, record the head SHA and continue. Do not poll. Snapshot `gh pr view` once per PR at diagnose. Re-read CI only when a later snapshot already shows a red required check that names a source file this PR owns.

If CI is already red on a source file this PR owns:

1. Fetch the failure logs: `gh run view {RUN_ID} --log-failed`
2. Identify the **delta** — what's different between local ruff/hooks and CI.
3. If fixable locally in **source** → fix, re-run `make precommit-repo`, one more `git push` (counts as the exceptional next cycle if already published).
4. If environment-only → classify `ENVIRONMENT` or `CI_PIPELINE`. Note it. **Do not** edit workflows to skip or weaken the failing job.
5. If unfixable → defer with reason "CI environment delta". If MERGE_TRAIN is blocked, record the blocker and finish.

## Convergence Gate

This PR is ready for the train when ALL conditions are true:

| Condition | Check Method |
|-----------|-------------|
| Local verify Passed | `make precommit-repo` exited 0 |
| Head SHA recorded | `git rev-parse HEAD` after push |
| No new unresolved review comments already present | Compare comment count/timestamps before and after push |
| All review threads resolved | GraphQL `isResolved: false` count is 0 (any author) |
| All code-review agent threads answered | Every `github-code-quality[bot]` / Copilot thread has a canonical reply ([code-review-agents.md](code-review-agents.md)) |
| All blocking findings resolved | Internal tracking: all `blocking` findings have status `fixed` |
| All actionable findings resolved or deferred | Internal tracking |

Required-check success is **not** a remediator gate.

## Re-Ingestion (When Not Converged)

When convergence gate fails due to new review comments already present, re-ingest only NEW signals:

1. **New CI failures already red:** Only failures on the latest completed run that name a source file this PR owns.
2. **New review comments:** Only comments with `created_at` after the last push timestamp.
3. **Resolved comments:** Remove from finding list if a thread was resolved.

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
  local_verify_gates_count: 1
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

local_verify_iterations: {integer}  # total across all cycles
local_verify_green_before_every_push: true | false

local_verify: Passed | Failed | Unknown
remote_ci: Passed | Failed | Unknown | NotApplicable
new_comments_after_final_publish: {integer}

deferred_items:
  - id: "review-7"
    reason: "Requires architectural decision"

protocol_violations:
  - "None" | list of any batch/verify violations that occurred

minimum_safe_next_action: "wait_first_merge_gate" | "merge_train_oldest_first" | "manual review of deferred items" | "run another cycle"
```

## Stop Conditions

MUST stop the loop when:
- `cycles_run >= max_cycles` → emit `partial`
- Local verify Passed AND no new actionable codebase signals → emit `converged` for **this PR**. Do not merge until FIRST_MERGE_GATE. Then MERGE_TRAIN.
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
max_local_verify_iterations: 5
auto_fix_nits: true           # clear one-line nits; skip only true product forks
skip_bot_discussions: true     # skip non-actionable chatter from non-CRA bots only; NEVER skip github-code-quality or Copilot
parallel_clusters: true        # always parallelize independent clusters
forbid_no_verify: true
require_precommit_all_hooks: false
require_precommit_all_files: false
prefer_makefile: true
makefile_primary: precommit-repo
oldest_created_at_default: true
stack_safe: true
merge_on_converge: true
```
