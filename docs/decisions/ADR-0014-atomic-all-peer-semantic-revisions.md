# ADR-0014: Shared semantic revisions apply atomically to all registered peers

## Status

Accepted

## Date

2026-08-10

## Context

A canonical source prevents ownership forks, but drift can still occur if a semantic revision is activated for Claude Code today, Cursor next week, and other peers later.

The requirement is stronger than code reuse: a shared architectural change must become the active semantic revision across the entire peer set as one governed change.

Different hosts may have different capabilities. That difference must be represented as explicit capability truth, not by leaving one peer on older semantics.

## Decision

1. Every shared Program Execution semantic change receives a versioned semantic revision.
2. EXECUTION_ADAPTER_REGISTRY and the existing capability index are the canonical discovery sources for the peer set; no parallel peer registry is introduced.
3. Every registered peer participates in each shared semantic revision.
4. For each peer, the revision must produce one of:
    * a conformant generated projection;
    * an explicit fail-closed/unsupported projection when the host cannot provide the capability.
5. Remaining silently on the superseded semantic revision is not an allowed outcome.
6. Promotion of the new semantic revision is blocked until every registered peer has been regenerated and its conformance result is known.
7. Partial peer activation of a shared semantic revision is forbidden unless a later explicit ADR defines a controlled staged-migration mechanism.
8. Peer transport code may differ; semantic revision identity does not.

## Options considered

1. Best-effort propagation to peers. Rejected: eventually produces mixed governance generations.
2. Allow capability-limited peers to stay on old semantics. Rejected: old behavior becomes an implicit fork.
3. Move all peers atomically, with unsupported peers failing closed under the same revision. Chosen: preserves global semantic consistency.

## Consequences

### Positive

* “All peers” becomes an enforceable invariant rather than an operational intention.
* Capability limitations are visible.
* No agent surface silently executes an older authority model.
* Rollback can restore one coherent semantic revision.

### Negative / costs

* A broken peer adapter can block semantic promotion.
* Registry and capability metadata must stay healthy.
* Shared changes require broader validation before activation.

## Related

* ADR-0013 — canonical peer semantics
* ADR-0015 — golden semantic vectors and peer parity
* environment/program-execution/registry/
* environment/program-execution/adapters/
