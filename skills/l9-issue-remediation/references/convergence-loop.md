<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: convergence_loop
tags: [issues, converge, early-stop]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Convergence Loop

Re-ingest issue state after each cycle. No CI short-poll as primary loop
(PR green is owned by `l9-pr-remediation`).

## After each cycle

1. Re-run `issue_ingest` for the sticky cluster’s repos.
2. Confirm root-cause items are addressed or reclassified.
3. Apply breadcrumbs per [unblock-breadcrumb.md](unblock-breadcrumb.md).
4. Decide:

| State | Action |
|-------|--------|
| Codebase done + PICKUP ok + comments posted | **Converged** |
| New CODEBASE/CROSS_REPO work and cycles < 3 | Next cycle |
| Only HUMAN / EXTERNAL / CI_PIPELINE remain | **Stop early** (more cycles cannot help) |
| PICKUP failed | Status `BLOCKED_PICKUP` — not converged |
| Cycles == 3 with remaining codebase work | Stop; report remainder; do not start cycle 4 |

## Early stop

Do not burn cycles on HUMAN product forks or EXTERNAL secret provisioning.
Breadcrumb the decision and exit.
