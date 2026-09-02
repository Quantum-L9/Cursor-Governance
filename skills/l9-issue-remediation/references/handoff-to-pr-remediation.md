<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: pr_handoff
tags: [issues, pr, handoff, l9-pr-remediation]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-09-02
/L9_META -->

# Handoff to l9-pr-remediation

This skill **never merges**. Remediator Converge may load `l9-pr-remediation`
**only** after the bound target reports `open_issues == 0`.

Issues opened by `l9-pr-remediation` above-paygrade handoff
(`skills/l9-pr-remediation/references/issue-handoff.md`) are ordinary issues.
Converge drains them. Do not bounce them back to the PR remediator until
`open_issues=0`.

Diagnose / auditor **never** calls this path.

## Hard gate

```bash
python3 skills/l9-issue-remediation/scripts/open_issues_gate.py \
  --intent converge --issues issues.json
```

- `chain: true` / `open_issues: 0` → invoke `/l9-pr-remediation` Converge on
  each owning repo that has the stacked PRs.
- Any other result (`BLOCKED_OPEN_ISSUES`, `DIAGNOSE_NO_CHAIN`) → **do not**
  start that skill. Zero means zero. Do not start early to babysit PRs.

Close resolved issues **before** this gate (fix already on a PR). Waiting for
GitHub `Fixes #n` auto-close on merge deadlocks the gate.

## How (only after the gate)

1. Load **`l9-pr-remediation`** Converge (`commands/l9-pr-remediation.md`) for
   each owning repo that has open PRs.
2. That command writes `authorize_merge.py --all-open`, remediates, then
   `stack_safe_merge.py`. This skill does not merge.
3. Do not run a second CI babysit loop inside this skill.
4. Breadcrumb law for issues must already be satisfied (PICKUP + comments +
   close-if-fixed + conditional session-ref).

## Forbidden

- `gh pr merge` from `l9-issue-remediation`
- Invoking `/l9-pr-remediation` while `open_issues != 0`
- Invoking `/l9-pr-remediation` from Diagnose
- Duplicating Sonar/CodeQL/debt remediation paths here
