# Improvement Report

## Baseline findings

1. Blueprint schemas mostly checked file presence and a few required keys, leaving allowed values, failure behavior, nested structures, and authorization semantics under-specified.
2. `target` was overloaded as repository identity, system identity, and human-readable target.
3. Task dependencies existed in multiple places without an explicit source-of-truth rule.
4. Blueprint gate definitions carried mutable-looking status while the Controller also owned runtime gate status.
5. Runtime state names were documented more richly than they were enforced.
6. The rendered task-contract schema incorrectly identified itself as a source-contract schema.
7. Decision and Unknown records were imported but not fully projected into runtime readiness.
8. Authorization was boolean-heavy and did not explicitly prove that runtime contracts were a subset of Blueprint ceilings.
9. Worker-declared changed files and validation claims were not required to exactly match Controller-observed state.
10. The pair lacked a canonical return channel from Controller runtime evidence to program governance.

## Accepted improvements

- Introduced a machine-readable pair interface and ownership matrix.
- Added `EXECUTION_TARGETS.yaml` to separate target identity from execution binding.
- Made `DEPENDENCY_GRAPH.yaml` the sole owner of task-to-task dependencies.
- Removed runtime gate status from Blueprint definitions.
- Added `EVIDENCE_CATALOG.yaml`, `WAIVER_REGISTER.yaml`, `OBSERVABILITY_PLAN.yaml`, and `CUTOVER_AND_ROLLBACK.yaml`.
- Added explicit task authorization ceilings, risk, reversibility, evidence obligations, and completion gates.
- Added deep JSON Schemas and schema execution to validators.
- Added Controller decision and Unknown projections, gate receipts, authorization subset checks, exact changed-file comparison, and handoff export.
- Added state-transition enforcement and stale-state invalidation.
- Added pair-level compatibility and hostile tests.

## Result

The pair is now a coherent execution system rather than two adjacent templates that happen to exchange files.
