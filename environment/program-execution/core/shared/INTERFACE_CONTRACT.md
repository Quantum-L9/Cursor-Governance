# Blueprint–Controller Interface Contract

## Contract identity

- Pair: `program-execution-system.v2`
- Blueprint: `program-execution-blueprint.v2`
- Controller: `program-execution-controller.v2`
- Compatibility rule: major versions must match exactly; minor versions may advance only when declared backward-compatible.

## Ownership matrix

| Concern | Canonical owner | Runtime projection | Update path |
|---|---|---|---|
| Program identity and target state | Blueprint | Program Lock | superseding Blueprint |
| Responsibility authority | Blueprint | read-only Program Lock projection | accepted decision + superseding Blueprint |
| Execution target identity | Blueprint | repository/adapter registration | reconcile exact current state |
| Task definition | Blueprint | runtime task projection | superseding task definition |
| Task runtime state | Controller | SQLite + ledger | validated state transition |
| Gate definition | Blueprint | runtime gate record | superseding gate definition |
| Gate evaluation | Controller | gate receipt + ledger | independent evaluation command |
| Decision result | Blueprint authority | read-only decision projection | accepted decision + Blueprint reseal |
| Unknown resolution | Blueprint authority | Controller blocker projection | evidence-backed resolution + Blueprint reseal |
| Authorization ceiling | Blueprint | Source/Rendered Contract subset | may only narrow at runtime |
| Action approval | Operator/approval authority | Controller approval receipt | exact, expiring approval |
| Attempt result | Worker claim only | Attempt Receipt | independent verification required |
| Verification verdict | Controller | Verification Receipt | rerun against exact state |
| Execution attempt identity and pre-dispatch baseline | Controller | execution_attempts record + baseline artifact | new attempt only; a baseline is never recaptured |
| Execution recovery and attempt fencing | Controller | recovery evidence + fenced attempt | `pec recover-execution` / `pec fresh-workspace` only |
| Local terminal closure | Controller | Closure Receipt | `pec close` only |
| Final program verdict | Program owner | Controller Handoff Receipt is advisory evidence | named acceptance decision |
| Provider retry and failover | Peer Execution Core | retry receipt | fencing-aware front door only |

## Import contract

The Controller imports all files listed in `EXECUTION_INDEX.yaml`, records SHA-256 for each, validates cross-file references, normalizes them into a Program Lock, and refuses advancement when any imported source changes.

A Program Lock digest is authoritative only when the lock's complete frozen semantics have been admitted against the exact source state represented by its source digests. Caller-specified relock scope (`pec relock --task`) is a requested maximum scope, not evidence of actual source-change scope: the Controller computes the full semantic delta between the lock and the Blueprint (`pec.blueprint.semantic_delta`) and admits a task-scoped relock only when every difference is a task definition inside that scope. Any wider difference is refused with `RELOCK_SCOPE_INSUFFICIENT` or `PROGRAM_LOCK_GLOBAL_DRIFT` and the lock is left byte-for-byte unchanged; source digests are refreshed only after the whole delta is admitted.

A resumed runtime executes only after `pec admit-resume` classifies the active lock against the Blueprint on disk as `EXACT_MATCH`; `TASK_SCOPED_DRIFT` must pass through the canonical relock and be re-admitted, and `WIDER_PROGRAM_DRIFT`, `SCHEMA_INCOMPATIBLE`, `TARGET_MISMATCH`, `LOCK_INVALID` and `SOURCE_UNAVAILABLE` stop the resume.

## Authorization law

The effective permission for an action is the intersection of:

1. applicable safety, legal, security, and organizational rules;
2. latest exact action approval, when required;
3. Blueprint task authorization ceiling;
4. Controller policy;
5. Source Contract request;
6. Rendered Contract exact-state binding.

No lower layer may widen a higher layer.

## Execution attempt and recovery law

Every worker dispatch has a durable execution attempt (`execution_attempts`) and an immutable pre-dispatch effect baseline, both committed in the same transaction that moves the task to EXECUTING; no provider may run before that commit. A result is accepted only from the task's live, unfenced attempt under its own active lease (`STALE_ATTEMPT_RESULT`, `STALE_LEASE_RESULT`, `RUNTIME_RECONCILIATION_REQUIRED` otherwise). An interrupted attempt is judged against its persisted baseline, never against the worktree as it currently stands.

Recovery must preserve and fence execution-attempt identity before successor mutation authority is issued. `pec recover-execution` (and `pec fresh-workspace`, which is a presentation over it) captures worktree evidence first, then in one transaction re-checks identity, fences the live attempt, releases the lease and lands the task on STALE; readiness is recomputed by the next claim and never forced. Recovery never widens authorization.

## Gate law

Callers provide evidence; the Controller derives the gate verdict. `pec evaluate-gate` takes evidence references only and derives PASS / FAIL / UNKNOWN / NOT_APPLICABLE_WITH_REASON deterministically from the gate's frozen definition (`pec.gates`). A caller's expected result is compared after the derivation is recorded and a mismatch is `GATE_EXPECTATION_MISMATCH`; an unsupported gate class is UNKNOWN, never PASS; a changed gate definition invalidates its prior result.

## Persistence law

The Controller's SQLite runtime is the canonical transaction boundary. Every canonical mutation is one serializable Controller transaction (`BEGIN IMMEDIATE`) that carries the state change, its immutable event record and, where a receipt backs the transition, the canonical receipt record. `ledger/events.jsonl` and receipt files are projections materialized after commit; their order is the committed sequence. `open_runtime` reconciles deterministically at every open: it completes pending projections, rematerializes receipts from their records, imports a pre-existing file chain once only if that chain verifies, and never adopts an artifact that has no canonical record. A believable PASS cannot exist without its receipt record.

## Evidence law

Every material advancement must cite an `EVIDENCE_CATALOG.yaml` record or a Controller-generated receipt with:

- stable evidence ID;
- artifact or source location;
- exact revision or digest;
- method and environment;
- producer and timestamp;
- result and scope;
- freshness or expiry;
- claims supported and contradicted.

## Handoff law

The Controller exports a `program-execution-controller.handoff-receipt.v2` document. It may report local task passes and gate evaluations, but it may not declare the program converged. Exporting a Handoff Receipt does not mutate campaign lifecycle. Only `pec close` may assert local terminal Program Execution state; it does so by producing a `program-execution-controller.closure-receipt.v1`, which external campaign projections must consume and validate (schema, producer, digest, program identity) instead of accepting a caller-supplied verdict. Controller local closure is not final Program acceptance: the program owner accepts a terminal verdict through an explicit Blueprint decision or closure record.

## Peer Execution law

Live campaign execution enters Peer Execution through one public front door (`peer_execution.front_door.execute`). Peer Execution Core owns provider selection, health-aware ordering, retry classification and failover; provider selection never changes Program, task, contract or lease authority. A retry after any dispatch of a mutating contract requires the prior attempt to be fenced by the Controller; a timeout or connection loss with unconfirmed termination is never retried or failed over (`PROVIDER_FAILOVER_UNSAFE`). A provider result is a claim; only Controller verification produces task PASS.
