<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, gates, validation]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# Plan Quality Gates

Gate IDs are enforced by `scripts/validate_plan_document.py`.

| Gate ID | Failure condition |
|---------|-------------------|
| G_SCOPE_OUT | empty `scope.out` |
| G_SUCCESS | empty or non-falsifiable `success_criteria` |
| G_TODO_GROUND | todo lacks `files` and `blocker` |
| G_PLACEHOLDER | TBD/TODO/maybe/should without blocker |
| G_CRITICAL_PATH | missing/empty/unknown todo ids |
| G_DEPS_ACYCLIC | dependency cycle |
| G_STRESS | missing disconfirming questions or blast_radius |
| G_ROLLBACK | high/irreversible risk without rollback |
| G_DOC_SURFACE | missing impact entries or N/A without reason |
| G_PRE_FINAL | missing pre_validation or final_validation |
| G_PR_CHECK | code in scope but no `make pr-check` in final_validation |
| G_UNKNOWN_HONESTY | material ambiguity with empty unknowns |
| G_CONVERGENCE | converged while mandatory status pending/failed/unknown |
| G_LEVERAGE | leverage.ranked_todo_ids empty |
| G_GMP_LOCK | handoff missing may/must-not-modify when code_in_scope |
| G_SCHEMA | JSON Schema validation failure |
