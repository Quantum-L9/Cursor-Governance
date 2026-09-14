# Canonical Architecture

## Ownership chain

### l9-meta-injector: observation compiler
Owns acquisition, hashing, decoding, explicit work-signal extraction, duplicate/candidate analysis, readiness evidence, and corpus packet emission. It answers what exists and what the source explicitly says.

### l9-constellation-topology: topology compiler
Owns entity resolution, canonical edge taxonomy, evidence reconciliation, candidate/canonical separation, impact analysis, validation, publication eligibility, and lowering into memory intents. It answers how observed entities are related and which relations are canonical enough to request memory admission.

### l9-graphiti-memory: governed memory control plane
Owns authorization, normalization, consent/admission, canonical persistence, temporal lifecycle, outbox, Graphiti projection, retrieval planning, and bounded hydration. Graphiti is rebuildable projection, not canonical truth.

### WorkContextCompiler: task relevance compiler
Uses graph/memory retrieval to compile the minimum sufficient authoritative context for one objective.

### WorkUnitCompiler: work abstraction compiler
Groups artifacts, tasks, dependencies, readiness, blockers, and capability goals into bounded executable units.

### LeveragePlanner: program design
Compares WorkUnits using dependency centrality, unblock fan-out, capability unlock, reuse, readiness, effort, risk, strategic alignment, and unknown burden. It may use counterfactual unlock simulation.

### Cursor-Governance Program Execution: execution authority
Receives a bounded BuildWavePlan and owns campaign execution, providers/workers, CI, retries, branch/PR convergence, repair, and completion receipts.

## Core separation
```text
Fact discovery != topology truth
Topology truth != memory admission
Memory admission != projection
Projection != task context
Task context != priority
Priority != execution
```
