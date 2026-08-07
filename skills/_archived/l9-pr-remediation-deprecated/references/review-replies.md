<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: review_replies
tags: [pr, review, replies, ownership, ci-signal, run-report]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-07-28
/L9_META -->

# Review Reply Protocol and Run Report

## Purpose

Reply once to every review thread with ownership-aware evidence. Resolve completed codebase or false-positive matters. Leave human-decision and CI-pipeline matters open while blocking.

## Non-Negotiable Rules

1. Every thread receives exactly one canonical reply.
2. Every reply carries the remediation idempotency marker.
3. Fixed and disproven threads may be resolved.
4. Human-decision threads remain open.
5. CI-pipeline threads remain open and reference a separate issue-file handoff.
6. CI issue files are not committed to the PR branch.
7. Post one batch summary per cycle.

## Idempotency Marker

```markdown
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Before posting, scan for the exact marker. Do not duplicate replies or state changes.

## Canonical Reply Formats

### Fixed Codebase Finding

```markdown
**Fixed** in `{sha_short}`

{one-line description}

Evidence: `{file}:{line}` and {verification}
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Resolve after the codebase fix is remotely confirmed.

### CI Pipeline Signal

```markdown
**Routed to CI remediation** - `{signal_id}`

Root cause: {concise cause}
Affected check: {check}
Handoff: `{issue_file_path}`

No CI-pipeline repair was attempted by this PR remediation run.
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Leave the thread open while the signal blocks PR readiness.

### Human Decision

```markdown
**Decision required**

Decision: {specific question}
Why codebase remediation cannot choose: {reason}
Independent work completed: {summary}
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Leave open.

### Deferred Codebase Work

```markdown
**Deferred**

Reason: {why outside the current codebase batch}
Minimum safe next action: {action}
Tracking: {terminal issue or fallback when created}
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Resolve only when the review concern is fully represented by a durable tracking artifact and repository policy permits resolution.

### Disagreed or Acknowledged

```markdown
**Disagree** - {reason category}

Evidence: {current code, test, type, or contract}
<!-- l9-remediation:{repo}:{pr}:{finding_id} -->
```

Resolve when evidence proves the finding is not actionable.

## Batch Summary

```markdown
## PR Remediation - Cycle {N}

Codebase fixes: {fixed_count}
CI pipeline signals: {ci_signal_count}
Human decisions: {human_count}
Commit: `{sha_or_none}`

### CI handoff files
- `{signal_id}` -> `{issue_file_path}`

Local codebase verification: {passed}/{total}
Threads: resolved {resolved}, CI-routed open {ci_open}, human open {human_open}
```

## Thread Accounting

The run report must satisfy:

```text
threads_replied == threads_total
threads_resolved + threads_requiring_human + threads_routed_ci == threads_total
ci_issue_files_created == unique CI root-cause fingerprints
```

## Machine-Readable Report

The normative shape is `schemas/run-report.schema.json`. Emit `run-report.json` once per PR and validate it with `scripts/validate_run_report.py`.

The report must contain:

- codebase applied/deferred/rejected findings;
- separate `ci_pipeline_signals` records;
- one issue-file path per CI root cause;
- zero CI repair attempts;
- final PR readiness;
- ownership-aware terminal escalation;
- final tarball metadata.

## Ordering

1. Render CI issue files. 2. Reply to fixed codebase threads. 3. Reply to CI pipeline threads. 4. Reply to human decisions. 5. Reply to deferred/rejected matters. 6. Resolve only eligible threads. 7. Post batch summary. 8. Emit and validate the run report.
