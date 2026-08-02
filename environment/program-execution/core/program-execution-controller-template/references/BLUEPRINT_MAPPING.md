# Blueprint Mapping

| Blueprint artifact | Controller projection |
|---|---|
| `PROGRAM.yaml` | immutable program identity and contract versions |
| `EXECUTION_TARGETS.yaml` | target registry and repository IDs |
| `AUTHORITY_REGISTRY.yaml` | read-only responsibility ownership |
| `DECISION_REGISTER.yaml` | runtime blocker projection; source remains authoritative |
| `UNKNOWN_REGISTER.yaml` | runtime blocker projection; source remains authoritative |
| `RISK_REGISTER.yaml` | risk context and approval obligations |
| `WAIVER_REGISTER.yaml` | scoped, expiring waiver projection |
| `EVIDENCE_CATALOG.yaml` | imported evidence identities and freshness |
| `DO_NOT_BUILD.yaml` | prohibited path checks |
| `CURRENT_STATE_DELTA.yaml` | freshness assumptions |
| `WORKSTREAMS.yaml` | task grouping |
| `DEPENDENCY_GRAPH.yaml` | sole task dependency source |
| `EXECUTION_WAVES.yaml` | wave barriers |
| `TASK_CARDS.yaml` | task definitions and authorization ceilings |
| `CONVERGENCE_GATES.yaml` | gate definitions; Controller owns evaluations |
| `OBSERVABILITY_PLAN.yaml` | post-change signal obligations |
| `CUTOVER_AND_ROLLBACK.yaml` | promotion and recovery obligations |
| `SOURCE_TRACEABILITY.yaml` | source provenance |
