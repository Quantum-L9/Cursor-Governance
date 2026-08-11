# ADR-0010: Program synthesis emits design-time authority; the Controller remains runtime authority

## Status

Accepted

## Date

2026-08-10

## Context

Intent resolution produces normalized intent, provenance, policy-derived requirements, decisions, and Unknowns. These facts still need to become executable Program Execution authority.

Letting the Controller interpret DPK facts or free-form intent directly would mix program compilation with mutable runtime execution and create multiple ways to define program authority.

Program Execution already separates sealed program truth from host-specific execution.

## Decision

1. A Program Synthesizer compiles program-execution.intent-resolution.v1 into the complete Program Execution Blueprint contract required by the active EXECUTION_INDEX.
2. Generated Blueprints must pass the official Blueprint validator before they are eligible for Program Lock.
3. The synthesizer derives workstreams, task definitions, dependencies, waves, evidence requirements, authorization ceilings, gates, risks, rollback, and source traceability from resolved authority.
4. The synthesizer emits design-time definitions only.
5. It must never emit Controller-owned runtime state, including attempts, leases, mutable task status, verification results, gate results, recovery state, or Handoff Receipts.
6. The Controller remains the sole owner of Program Lock execution state and advancement.
7. DPK and repository-truth artifacts are compiler inputs; they do not become a second Program Execution Controller.

## Options considered

1. Teach the Controller to execute DPK directly. Rejected: introduces a second design-time authority format at runtime.
2. Let each worker interpret resolved intent independently. Rejected: destroys deterministic task authority.
3. Compile a validator-clean Blueprint before runtime. Chosen: preserves the existing Program Execution ownership boundary.

## Consequences

### Positive

* Sparse intent converges onto one existing executable authority model.
* Runtime remains independent of how the program was authored.
* The official Blueprint validator remains the acceptance boundary.
* DPK can evolve as an upstream compiler without owning execution.

### Negative / costs

* Blueprint synthesis must track Program Execution contract versions.
* Schema evolution requires explicit compatibility handling.
* Generated authority needs strong source traceability.

## Related

* ADR-0007 — goal-level intent front door
* ADR-0008 — intent resolution provenance boundary
* environment/program-execution/core/
* environment/program-execution/ARCHITECTURE.md
