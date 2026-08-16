<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: pr_handoff
tags: [issues, pr, handoff, l9-pr-remediation]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Handoff to l9-pr-remediation

This skill **never merges**. When unblock requires a green PR, hand off to
`l9-pr-remediation` Converge — that skill remediates and merges:

## When to hand off

- A fix commit needs review/CI before the issue can close
- An existing open PR already addresses the sticky cluster
- Local verify is green but remote required checks are not yet observed

## How

1. Ensure the PR exists on the owning repo (open if needed with a clear body
   linking every issue in the cluster: `Fixes #n` / `Related to org/repo#n`).
2. Load **`l9-pr-remediation`** Converge (or Diagnose then Converge on mutate
   authority) for `{owner}/{repo}#{pr}`.
3. Do not run a second CI babysit loop inside this skill.
4. After PR converges (or while waiting), still fulfill breadcrumb law for the
   **issues** (PICKUP + comments + conditional session-ref).

## Forbidden

- `gh pr merge` from `l9-issue-remediation`
- Duplicating Sonar/CodeQL/debt remediation paths here — those live in
  `l9-pr-remediation`
