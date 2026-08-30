<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: issue_verify
tags: [issues, verify, recreate, phantom, diagnose-first]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-29
/L9_META -->

# Issue verify (before any remediator trust)

Agents write bad issues. An OPEN GitHub row is not proof the defect exists.
**Recreate the live issue, then verify the defect.** Do this on every cluster
item before Lesson Recall or a patch. Diagnose-first is not optional.

## Recreate (live snapshot)

Do not reuse chat text, a prior ingest JSON, or the issue author's certainty.

```bash
gh issue view {n} --repo {owner}/{repo} --json number,title,state,body,closedAt,url
```

| Live state | Action |
|------------|--------|
| 404 / not found | skip — do not open a replacement issue |
| `state=CLOSED` | skip (already gone). Do not reopen to "fix" it |
| `state=OPEN` | continue to defect verify |

Re-run `issue_ingest.py` after this if the snapshot is older than this turn.

## Verify the defect

In the owning repo (current default branch, or the claimed path):

1. Search the code/tests for the claimed symbol, path, error, or missing contract.
2. Reproduce the failure if the issue names a command or test.
3. Classify:

| Verdict | Meaning | Next |
|---------|---------|------|
| `exists` | Defect is present in source or a failing local gate | Remediate (fix-engine) |
| `already-fixed` | Code already has the fix; issue is stale | Close with `--commit` or `--merged-pr` |
| `not-reproducible` | Claimed failure does not happen; no matching defect | Close with `--reason not-reproducible --proof {what you ran}` |
| `does-not-exist` | Issue describes a file/API/behavior that is not in this repo (wrong target or invented) | Close with `--reason does-not-exist --proof {search}` |

Close via `scripts/close_resolved_issue.py` (`--status fixed` + evidence).
Do not mass-close HUMAN/EXTERNAL: those still need
`superseded|duplicate|already-fixed|not-reproducible|does-not-exist` plus proof.

## Forbidden

- Remediate from the issue body alone
- Treat labels or an agent's title as ground truth
- Open a new issue to replace a 404
- Skip verify because ingest already listed the number
