# Before and After Delta

| Dimension | Previous siblings | Aligned v2 system |
|---|---|---|
| Target identity | overloaded prose or repository name | stable `target_id` plus typed execution target |
| Task dependencies | repeated across task and graph surfaces | `DEPENDENCY_GRAPH.yaml` is sole owner |
| Task state | definition and runtime language overlapped | `definition_status` and `runtime_state` are separate domains |
| Gate state | Blueprint looked mutable | Blueprint defines; Controller evaluates and receipts |
| Authorization | boolean intent without subset proof | runtime contract must be a strict subset of Blueprint ceiling |
| Evidence | prose and paths | stable IDs, revisions, digests, methods, freshness, results |
| Worker claims | could resemble verdicts | Attempt Receipt is a claim; Controller independently verifies |
| File scope | worker declaration trusted too easily | declared and observed changed-file sets must match exactly |
| Decisions and Unknowns | imported but weakly enforced | evidence-bound readiness blockers |
| Waivers | implicit omission risk | explicit, scoped, expiring, evidence-backed records |
| Return path | informal handoff | digest-bound Controller Handoff Receipt |
| Final verdict | Controller could appear conclusive | Controller recommends; program owner accepts |
