<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, convergence]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# Convergence Block

```yaml
convergence:
  status: converged | partial | blocked
  remaining_unknown_ids: []
  next_skill: l9-ynp | l9-gmp-protocol | none
  stop_reason: string
```

Rules:

- `converged` only when validate_plan_document would PASS and no material unknowns remain unresolved.
- `partial` when the plan is usable but unknowns/blockers remain.
- `blocked` when ground truth or authorization is missing.
- Never mark converged while pre/final validation items are pending/failed/unknown for mandatory checks.
