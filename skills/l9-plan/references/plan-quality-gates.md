<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, gates, validation]
status: active
version: 4.0.0
updated: 2026-08-12
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
| G_PLAN_KERNEL_PASS | `.plan.md` missing `kernel_pass` / improve / validate_repair |
| G_PLAN_BOUND | `kernel_pass.bound_path` basename does not match the file |
| G_PLAN_SHA | `validate_repair.body_sha256` unset or not the canonical file sha |
| G_PLAN_DELTAS | a kernel pass has empty `deltas` |
| G_PLAN_RAN_AT | `ran_at` missing or unparseable |
| G_PLAN_ORDER | Improve `ran_at` is not earlier than Validate & Repair |
| G_PLAN_ETC | `etc.` / ellipsis / `and similar` on an exclusive / owned_paths line |
| G_PLAN_EITHER_OR | `either` / `drop or keep` / `fold or exempt` without a `blocker` |
| G_PLAN_SUPERSEDED | a newer same-slug plan is the live target |
| G_PLAN_EXECUTABLE | `status: executable` while the receipt checker FAILs |
