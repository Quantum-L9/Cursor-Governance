# Phase 5–6 Deep Implementation Section

## Mission
Close the only intentional gap between a trustworthy corpus graph and Cursor-Governance Program Execution.

```text
Graphiti / canonical Memory / Topology
        ↓
PHASE 5 — WorkContextCompiler
        ↓ WorkContextPacket / CompiledTaskContext projection
PHASE 6A — WorkUnitCompiler
        ↓ WorkUnit[]
PHASE 6B — LeveragePlanner
        ↓ prioritized WorkUnit[] + counterfactual unlock evidence
PHASE 6C — BuildWavePlanner
        ↓ BuildWavePlan
        ↓
Program Execution handoff
```

The implementation target is `Quantum-L9/l9-cognitive-runtime`. These components belong there because they compile task-scoped context and bounded execution intent. They MUST NOT write Dropbox, mutate Graphiti canonical memory, execute builds, schedule workers, merge PRs, or own Program Execution campaign state.

## Phase 5 responsibilities

`WorkContextCompiler` owns six decisions:

1. resolve focal entities from the objective;
2. retrieve candidate records through a narrow memory-query port;
3. expand only canonical traversable topology edges;
4. hydrate canonical records so Graphiti projection loss cannot become authority loss;
5. classify every candidate as REQUIRED / SUPPORTING / OPTIONAL / CONFLICTING / SUPERSEDED / EXCLUDED / UNRESOLVED;
6. emit a bounded packet or fail with `BLOCKED_CONTEXT_BUDGET`.

### Non-negotiable laws

- Graphiti is discovery/navigation; canonical Memory hydration supplies evidence, provenance, confidence method and lifecycle.
- `REFERENCES` and `DUPLICATE_OF` do not expand dependency context by default.
- unresolved conflict is carried, not silently adjudicated.
- historical versions collapse to the current authoritative artifact plus lineage summary unless history is task-relevant.
- REQUIRED + CONFLICTING records are never silently truncated.
- every excluded artifact must have a reason.

## Phase 6 responsibilities

### WorkUnitCompiler
Converts file/claim/roadmap/task evidence into bounded work objectives. One work unit must have one coherent completion condition. Files are evidence, never the thing being prioritized.

### LeveragePlanner
Computes evidence-backed ordinal dimensions, never fake precision. Initial dimensions are 0–5:

- dependency centrality
- unblock fan-out
- capability unlock
- reuse potential
- strategic alignment
- readiness
- effort
- risk
- unknown burden

Priority classes:
`FOUNDATIONAL_UNLOCK`, `QUICK_HIGH_LEVERAGE`, `DEPENDENCY_REQUIRED`, `READY_VALUE`, `STRATEGIC_BET`, `WAITING`, `LOW_RETURN`, `OBSOLETE`, `UNKNOWN`.

### BuildWavePlanner
Produces dependency-correct waves, not a flat list. Independent ready work may run in parallel. Counterfactual completion is used to estimate opportunity radius.

## Reference target filetree

The Claude Code contracts MUST first inspect current `main` and reuse existing extension points. If current package names differ, preserve these logical boundaries rather than blindly creating duplicate packages.

```text
src/l9_cognitive_runtime/
  context/
    ports.py
    models.py
    work_context_compiler.py
  planning/
    models.py
    work_unit_compiler.py
    leverage_planner.py
    build_wave_planner.py
    handoff.py
  service/
    planning_service.py             # thin orchestration only, if a service layer already exists

tests/
  unit/context/
  unit/planning/
  integration/test_graph_to_build_wave.py

contracts/
  work_context_packet.schema.json
  work_unit.schema.json
  build_wave_plan.schema.json
  program_execution_handoff.schema.json
```

## Implementation sequence

### PR-01 — Phase 5 context compilation
Build the memory-query port, models, WorkContextCompiler, authority collapse, budget fail-closed behavior and tests.

### PR-02 — Work-unit compilation
Build deterministic bounded work-unit synthesis from explicit work evidence and canonical graph structure. No leverage ranking yet.

### PR-03 — Leverage planning
Add ordinal leverage dimensions, priority classes and counterfactual unlock simulation over the work-unit DAG.

### PR-04 — Build waves + PE handoff
Compile dependency-correct waves, emit the existing handoff schema and integration-test Graphiti/Memory-shaped fixtures through to a Program Execution packet.

## Finish criterion

Phase 5–6 is done when a planning agent can be denied direct Dropbox browsing, given only an objective plus governed memory/topology access, and still produce:

- the correct minimum authoritative context;
- explicit exclusions;
- bounded work units;
- correct prerequisites/blockers;
- a defensible high-leverage build-wave plan;
- a machine-valid Program Execution handoff;
- no execution side effects.
