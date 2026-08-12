<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, doctrine, anti-rework]
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# Planning Doctrine

## Law

1. A minute of planning saves an hour of debugging.
2. Front-load maximum depth and correctness. Do not skip stress-test, critical path, rollback, unknowns, or Doc/Root Surface Impact to save tokens.
3. Token efficiency that omits planning depth is fake optimization. True efficiency is preventing rework.
4. Ask before inventing objective, success criteria, paths, or scope.
5. Fail closed: machine validation PASS is required for readiness. LLM aesthetic judgment is not a gate.
6. Dual artifact: PLAN_DOCUMENT JSON/YAML is the depth-gate machine artifact; the default deliverable is the PE+autonomy Cursor `.plan.md` from `canonical.template.executable_plan.v1`.
7. Execute via `@environment/program-execution` then subordinate `@autonomy` under a Program lease. Do not free-form mutate from plan markdown alone.
8. `.cursor/plans/_TEMPLATE.plan.md` is a local mirror of the git SSOT template — sync with `scripts/sync_cursor_plan_template.py`; never fork content.

## Forbidden

- Omitting mandatory gates because the task "looks simple"
- Claiming ready on heading-complete prose without validator PASS
- Treating legacy `plan-workflow.md` / `render_plan_markdown.py` as the default plan-mode deliverable
- Empty `scope.out`
- TODOs without files and without blocker
- `convergence.status=converged` while mandatory checks are pending/failed/unknown
