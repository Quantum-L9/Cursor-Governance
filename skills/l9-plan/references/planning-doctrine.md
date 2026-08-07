<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, doctrine, anti-rework]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# Planning Doctrine

## Law

1. A minute of planning saves an hour of debugging.
2. Front-load maximum depth and correctness. Do not skip stress-test, critical path, rollback, unknowns, or Doc/Root Surface Impact to save tokens.
3. Token efficiency that omits planning depth is fake optimization. True efficiency is preventing rework.
4. Ask before inventing objective, success criteria, paths, or scope.
5. Fail closed: machine validation PASS is required for readiness. LLM aesthetic judgment is not a gate.
6. PLAN_DOCUMENT JSON/YAML is authoritative; markdown is a projection.

## Forbidden

- Omitting mandatory gates because the task "looks simple"
- Claiming ready on heading-complete prose without validator PASS
- Empty `scope.out`
- TODOs without files and without blocker
- `convergence.status=converged` while mandatory checks are pending/failed/unknown
