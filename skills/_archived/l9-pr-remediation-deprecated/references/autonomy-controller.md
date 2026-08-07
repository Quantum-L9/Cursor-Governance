# Autonomy Controller

## Objective

Run PR remediation as a bounded, resumable state machine. Maximize independent codebase progress while preserving the hard CI signal boundary.

## Capability Preflight

Resolve and record before mutation:

| Capability | Required evidence | Behavior when absent |
|---|---|---|
| Target repository | owner/name or repository URL | no mutation; package known signals |
| Target PR | PR number and current head SHA | no mutation; report unresolved scope |
| GitHub connection | successful authenticated read | use local-only dry-run if unavailable |
| Branch write | authenticated permission | produce codebase patch; do not retry blind |
| Issue write | issue-create capability | used only for terminal codebase/human blockers |
| Local checkout | clean repository at PR head | use complete connector writes or patch |
| Mutation authorization | explicit fix/remediate/converge intent | dry-run when absent |

CI signal-file generation requires no repository mutation and remains available in dry-run or disconnected execution.

## Autonomous Decision Policy

Proceed without asking only when the action is:

- classified `CODEBASE_REPAIR`;
- inside resolved PR scope;
- reversible by normal commit or reply;
- supported by current source, tests, required-check output, or codebase policy;
- unrelated to CI orchestration, infrastructure, policy, or shared CI ownership;
- not dependent on product, architecture, security-exception, legal, or business intent.

For `CI_PIPELINE_SIGNAL`, collect evidence and render the handoff file without repairing the cause.

## State Machine

```text
PREFLIGHT -> INGEST -> OWNERSHIP_CLASSIFY
  -> RENDER_CI_SIGNALS
  -> FIX_CODEBASE -> LOCAL_VERIFY -> COMMIT_PUSH?
  -> REPLY -> REMOTE_CONFIRM -> PR_READY?
      yes -> CONVERGED -> PACKAGE
      no and codebase work remains and cycle < 3 -> CHECKPOINT -> INGEST
      no and only CI signals remain -> CI_SIGNAL_BUNDLE -> PACKAGE
      no and cycle == 3 -> TERMINAL_CODEBASE_ESCALATION -> PACKAGE
      unrecoverable -> OWNERSHIP_ROUTING -> PACKAGE
```

No transition may enter cycle 4. A signal-only blocker does not require wasting the remaining cycles.

## Checkpoint and Resume

Write a redacted checkpoint after every gate and before waiting on remote CI:

```text
$RUNNER_TEMP/l9-pr-remediation/{owner}-{repo}/pr-{number}/state.json
```

Checkpoint fields:

```yaml
run_id: string
repo: owner/name
pr: integer
cycle: 0..3
observed_head_sha: sha
last_completed_gate: P | A | B | C | D | E | F | G | H
finding_ids: []
ci_signal_fingerprints: []
ci_issue_paths: []
commit_shas: []
reply_markers: []
terminal_issue_marker: string | null
updated_at: ISO-8601
```

On resume, compare the checkpoint head with the remote PR head. If different, discard planned edits, re-ingest, and preserve only confirmed markers and still-valid CI fingerprints.

## Cycle Semantics

A cycle starts when signals are ingested for one observed head and ends after remote confirmation or an ownership-proven stop. Local verification retries are not separate cycles and are limited to three iterations. A cycle may have zero commits and pushes when it is already ready, signal-only, or has no safe codebase change.

## Mutation Budget

Per PR per cycle:

- codebase commits: 0 or 1;
- pushes: 0 or 1;
- batch comments: 0 or 1;
- reply per finding marker: 0 or 1;
- CI pipeline mutations: exactly 0;
- CI issue file per fingerprint: 0 or 1;
- terminal codebase blocker issue per fingerprint: 0 or 1 across the run.

## Required-Check Integrity

Read CI configuration to discover commands and evidence. Never edit it. Run all locally reproducible commands against the codebase. If the same command proves a code defect, repair code. If the cause is orchestration, environment, policy, permissions, service, shared CI, or configuration ownership, render a CI signal.

## Ownership Routing

- `CODEBASE_REPAIR`: eligible for fix batch.
- `CI_PIPELINE_SIGNAL`: issue file, no repair, no PR commit.
- `HUMAN_DECISION`: reply, remain open, terminal codebase/human escalation after bounded work.
- `FALSE_POSITIVE`: evidence-backed reply; resolve when appropriate.

## Terminal Routing

1. Package CI issue files immediately after classification and include them in every final tar.gz.
2. If only CI-pipeline blockers remain, use `terminal_escalation.mode: ci_signal_bundle`; do not create a GitHub issue in the consumer repository.
3. If residual codebase or human blockers remain after cycle 3, use the GitHub issue or fallback artifact path.
4. Mixed runs include both the terminal codebase/human escalation and all separate CI issue files.

## Output Truth

Use `converged` only when `pr_readiness.ready` is true. Use `partial` when codebase progress landed but external CI still blocks. Use `blocked` when no safe codebase mutation path or required evidence exists. Never substitute green CI for PR-ready or a CI issue file for a code fix.
