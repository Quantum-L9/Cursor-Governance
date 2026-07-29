# Optimize CLI Product Contract

## Purpose

Raise utilization of capability a repository already owns — activating dormant or miswired code, off-by-default features, unread config, and unused signals — and, as one branch, increase CLI throughput by removing a verified repository-owned bottleneck, all while preserving correctness, safety, compatibility, and external service contracts.

Optimization is not quota bypass, and it is not capability manufacture. A valid change improves the local implementation, configuration, or execution path. It does not evade provider limits, billing controls, licensing, authorization, abuse prevention, or externally imposed backpressure.

## Utilization-Gap Ownership Test

Classify every suspected utilization gap before editing. The taxonomy has two peer branches — a throughput branch and a capability branch — plus the boundary rows:

| Class | Examples | Action |
|---|---|---|
| Repository-owned artificial delay | fixed sleeps, unnecessary pacing, polling interval chosen locally | Remove, shorten, or make adaptive after proving safety |
| Repository-owned serialization | one-at-a-time loop, global lock, sequential subprocess calls | Parallelize or pipeline within bounded resource limits |
| Repository-owned low cap | undersized worker pool, queue, batch, chunk, connection, or inflight limit | Raise or make configurable with evidence and safe defaults |
| Blocking implementation | sync I/O in async path, per-item process startup, repeated initialization | Convert to native async, reuse processes/connections, or batch work |
| Duplicate work | repeated parsing, validation, downloads, scans, or recomputation | Reuse verified results or cache with correct invalidation |
| Buffering bottleneck | full materialization before output, non-streaming copy, tiny chunks | Stream or tune buffering without changing content semantics |
| Retry/backoff drag | repository-owned delays that exceed observed failure needs | Tune using measured failure behavior and preserve failure safety |
| Lock contention | coarse critical section, hot shared mutex, serialized state update | Narrow lock scope or partition state with race tests |
| External limit | API 429, provider quota, account plan, license, server-side cap | Do not bypass; create a blocker or downstream issue |
| Unknown ownership | incomplete evidence or mixed local/external cause | Fail closed and gather the smallest missing evidence |
| **Capability: inactive_component** | defined/exported but never imported or instantiated | Wire to a real consumer after proving reachability |
| **Capability: miswired_file** | registered under an unread key or wrong consumer | Correct the wiring edge |
| **Capability: dormant_capability** | complete code behind an off-by-default flag, unmounted route, or unsurfaced command | Activate only if NOT `dormant_by_design` |
| **Capability: unused_signal** | produced value/event/return field with no consumer | Connect the consumer |
| **Capability: orphaned_config_schema** | config defined-but-unread or read-but-never-set | Wire the read/write path |
| **Capability: broken_partial_wiring** | producer and consumer exist but the edge is absent | Restore the missing edge |

### utilization_gap_class ↔ finding kind crosswalk

Throughput classes map to finding `kind: performance_bottleneck`; the six capability classes map to finding `kind: latent_capability`; `external_limit` maps to `kind: external_limit`; documentation disagreements are `kind: docs_code_divergence`. Every capability activation additionally requires the reachability proof (`PO-REACHABILITY`) and a `dormant_by_design: false` decision.

## Evidence Contract

Do not optimize from intuition alone. Record:

1. workload and environment;
2. exact baseline command or trace source;
3. metric, unit, sample count, and observed value;
4. bottleneck evidence such as profile, timing trace, queue depth, lock wait, process count, or code path;
5. candidate command using the same workload and comparable environment;
6. candidate value and improvement calculation;
7. correctness and resource checks run alongside the benchmark;
8. limitations and residual unknowns.

Prefer multiple samples and median or percentile values when variance is material. Never compare unlike workloads, warmed and cold states without disclosure, or different correctness modes.

## Safe Optimize Patterns

Choose the smallest pattern that addresses the proven bottleneck:

### Remove fixed delay

Use when a repository-owned sleep or pacing interval is not required for correctness or an external contract. Replace it with event-driven readiness, adaptive waiting, or no delay. Preserve cancellation and timeout behavior.

### Bounded parallelism

Use when independent work is unnecessarily serialized. Bound workers and inflight work. Expose configuration only when the repository convention supports it. Test ordering requirements, shared state, cancellation, and partial failure.

### Batching

Use when per-item overhead dominates. Define maximum batch size, payload size, latency tradeoff, failure attribution, and retry behavior. Do not exceed external request limits.

### Pipeline and streaming

Use when stages can overlap or output can begin before full materialization. Bound buffers and preserve backpressure. Verify byte-for-byte or semantic output equivalence.

### Reuse and cache

Use when initialization or computation repeats. Define cache key, invalidation, lifetime, storage, concurrency behavior, and correctness fallback. Never cache secrets or authorization decisions unsafely.

### Async I/O or connection reuse

Use when blocking I/O or setup dominates. Preserve timeout, cancellation, error mapping, and connection limits. Do not create unbounded tasks or sockets.

### Lock narrowing or partitioning

Use when contention is proven. Maintain data-race safety, atomicity, consistency, and deterministic failure handling.

## Resource Envelope

Every implementation must name or derive applicable ceilings:

- worker and subprocess count;
- inflight task and queue depth;
- memory and buffer bounds;
- file descriptor and connection limits;
- CPU utilization expectations;
- request and payload limits;
- disk and temporary-file growth;
- timeout and cancellation behavior.

A speedup that merely shifts failure into memory pressure, connection exhaustion, provider errors, or corrupted ordering is invalid.

## Configuration Rules

- Preserve existing precedence and naming conventions.
- Keep safe defaults unless evidence justifies a default change.
- Validate bounds and reject zero, negative, nonsensical, or dangerous values.
- Record migration when behavior changes.
- Support an immediate rollback path, preferably a configuration reversal or feature flag when repository conventions allow it.
- Do not create a new configuration system solely for this change.

## CLI and Subprocess Rules

When wrapping or spawning commands:

- pass argument vectors, not interpolated shell strings;
- preserve stdout, stderr, signals, cancellation, and child exit code;
- define timeout and partial-failure behavior;
- avoid orphaned children and process leaks;
- maintain cross-platform behavior supported by the repository;
- test invalid input and interrupted execution.

## Performance Acceptance

A change is acceptable only when:

- the bottleneck is locally owned and evidenced;
- candidate measurements are comparable to baseline;
- improvement is material for the target workload or the proven hard bottleneck is removed;
- correctness and compatibility checks pass;
- resource use remains within the declared envelope;
- deployment and rollback are executable;
- unsupported claims are labeled `UNKNOWN` rather than promoted to fact.

## Forbidden Outcomes

Reject changes that:

- evade or automate around provider quotas, account restrictions, or billing limits;
- disable protective backpressure without replacement safeguards;
- use unbounded concurrency, queues, retries, or subprocess creation;
- hide errors, drop work, reorder contractual output, or falsify success;
- benchmark only a happy path while ignoring failure and resource behavior;
- alter CI or tests only to make the optimization appear valid;
- replace a measured local bottleneck with a new throttling subsystem unrelated to the objective.


## Latent Capability and Wiring

When an existing throughput path appears defined but disconnected, load `latent-capability-activation.md`. Treat reachability as a separate proof dimension from correctness and performance. Resolve CLI entrypoints, registries, feature flags, dynamic dispatch, and expected signal consumers before selecting an activation.

Allowed strategies include `activate_latent_capability`, `repair_wiring`, `connect_signal_consumer`, and `surface_existing_cli_path`. These strategies require a converged wiring record, at least one selected `DWA-NNN` finding with verdict `activate`, bidirectional definition-and-consumer evidence, and no unresolved material reachability unknown. Activation still must pass the normal performance, correctness, resource, deployment, and rollback gates.
