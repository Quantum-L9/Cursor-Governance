<!-- L9_META
l9_schema: 1
origin: folded from governance-v2 ops-parallel-ci-triage
tags: [ci, triage, parallel, github-actions]
status: active
/L9_META -->

# Parallel CI Triage

Speed up fixing broken CI by splitting **independent failing jobs** across parallel subagents. Each owns one vertical slice: logs → root cause → fix → local verification.

## When to use / not use
Use when multiple GitHub Actions jobs fail and the failures look independent, or a long log is easier to split by job than fix sequentially. Do **not** use for a single clear error (fix in the main agent) or purely flaky infra (retry / fix workflow config first).

## Workflow

1. **Identify the run** — `gh run list --limit 5`; `gh run view <RUN_ID> --log-failed`. Group by failed **job** (not step). If `gh` is unavailable, paste logs from the UI.
2. **Split by job** — one subagent per failed job (e.g. `lint`, `test-node-18`, `e2e`). If two failures share one root cause in the same file, assign **one** subagent to both to avoid conflicting edits.
3. **Launch parallel subagents** — one `generalPurpose` Task per job in a single message. Give each the workflow run, branch, and the **exact** failed-step log excerpt (so it doesn't guess). Instruct: infer root cause from the log, edit only what this job needs, run the same failing command locally (or narrowest equivalent), and report what changed + local pass confirmation.
4. **Merge and verify** — collect changed files, resolve overlaps manually, run the CI-equivalent locally, commit (conventional message), push, and `gh run watch`.

## Notes
Redact secrets before pasting logs. If agents conflict on shared files, merge sequentially after the parallel pass.
