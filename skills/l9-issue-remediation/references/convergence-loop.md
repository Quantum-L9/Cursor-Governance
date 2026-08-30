<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: convergence_loop
tags: [issues, converge, open_issues, pr-remediation]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
/L9_META -->

# Convergence Loop

Re-ingest after each cycle. Drain the **leverage-ranked queue** (all
automatable clusters). Re-count open issues after every close.

PR green/merge is owned by `l9-pr-remediation` and may start **only** when
`open_issues == 0`. See [handoff-to-pr-remediation.md](handoff-to-pr-remediation.md).

## After each cycle

1. Re-run `issue_ingest` for the bound target (fleet or named repo).
2. Re-run `cluster_rank.py`. Continue with the next automatable cluster
   (highest remaining leverage). Per-cluster cycles still cap at 3.
3. Close resolved issues (`close_resolved_issue.py`) when the fix is on a PR
   or already landed.
4. Re-count open issues. Decide:

| State | Action |
|-------|--------|
| `open_issues == 0` (intent=converge) | **Chain** `/l9-pr-remediation` |
| `open_issues > 0` and automatable clusters remain | Next cluster / next cycle |
| `open_issues > 0` and only HUMAN / ARCHITECTURE / EXTERNAL remain | Present [human-blocker-mcq.md](human-blocker-mcq.md) (**A** = recommended). Status `BLOCKED_OPEN_ISSUES` until the letter. Resume the queue after the answer. Do **not** chain |
| PICKUP failed | `BLOCKED_PICKUP` — not converged |
| Cluster cycles == 3 with remaining codebase work | Stop that cluster; continue others |

```bash
python3 skills/l9-issue-remediation/scripts/open_issues_gate.py \
  --intent converge --issues issues.json
```

`chain: true` is the only allow for `/l9-pr-remediation`. Diagnose never
evaluates this for the purpose of starting remediator.

## Early stop vs chain

Do not burn cycles on HUMAN product forks, ARCHITECTURE approval, or
EXTERNAL secret provisioning. Drain every other automatable cluster first.
Then ask the recommended-A questions. They keep `open_issues > 0` and
**block** the remediator chain until evidence-closed or actually resolved.
Do not weaken the gate to “automatable subset = 0.” Do not idle the invoke
waiting on one blocker while other clusters can still move.
