# Terminal Escalation

## Ownership-Aware Trigger

Use separate routes for codebase/human blockers and CI-pipeline blockers.

## CI Pipeline Route

Render one issue file per distinct CI root cause as soon as the cause is classified. Always include every file in the final tar.gz, even when the PR later converges.

If only CI-pipeline blockers remain:

- stop codebase remediation without consuming unnecessary cycles;
- set `terminal_escalation.mode: ci_signal_bundle`;
- record all issue-file paths;
- do not create a GitHub issue in the consumer repository;
- do not attempt to repair the CI cause.

A live CI issue may be created only with explicit user authorization and an independently resolved owning CI repository. That action is outside the default contract.

## Codebase and Human Blocker Route

Run once when the PR is not ready after three cycles or an unrecoverable codebase/human blocker prevents safe progress.

Create marker:

```text
<!-- l9-pr-remediation-blocker:{repo}#{pr}:{fingerprint} -->
```

Search open issues before creation. Reuse a matching issue. The fingerprint is SHA-256 over repository, PR, final head, and sorted non-CI blocker IDs.

When GitHub issue creation is available:

1. attempt exactly once;
2. use title `[PR Remediation Blocked] PR #{pr}: {short blocker}`;
3. include final head, cycles, evidence, residual codebase/human blockers, CI signal file paths, and minimum safe next action;
4. store the issue URL;
5. do not place CI repair instructions in the consumer codebase issue except as linked handoff files.

If creation is unavailable or fails, render `issues/pr-{pr}-terminal-blocker.md`.

## Mixed Route

Mixed runs include:

- one terminal codebase/human issue or fallback artifact;
- one separate issue file for each CI-pipeline root cause;
- no CI-pipeline repairs.

## Final Tarball

Always package:

- `run-report.json`;
- `CONVERGENCE_REPORT.yaml`;
- `PR_READY_EVIDENCE.json`;
- `CYCLE_LOG.jsonl` when present;
- summary files when present;
- every `issues/ci-pipeline/*.md` file;
- terminal fallback issue when applicable;
- deterministic `MANIFEST.json` with SHA-256 digests.

Do not package raw CI logs, tokens, credentials, `.env` files, or unredacted scanner payloads.
