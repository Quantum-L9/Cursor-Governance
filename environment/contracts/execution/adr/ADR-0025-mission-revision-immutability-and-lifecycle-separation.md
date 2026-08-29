# ADR-0025: Mission Revision Is Immutable; Mission Lifecycle Is a Separate State Domain

* Status: Accepted
* Date: 2026-08-28
* Decision owner: L9 architecture

## Context

A durable Mission needs stable identity across multiple Programs while also
supporting lifecycle changes such as activation, waiting, satisfaction,
failure, cancellation, and supersession.

Embedding mutable lifecycle into the Mission definition would make the same
Mission Revision change meaning over time and would undermine digest-bound
Program provenance.

## Decision

Every Mission definition is an immutable, digest-bound Mission Revision.

Changing authoritative Mission semantics creates a superseding Mission
Revision rather than rewriting an existing revision.

Mission lifecycle state is separate from Mission Revision definition.

Canonical lifecycle values:

```text
PROPOSED
ACTIVE
WAITING
SATISFIED
FAILED
CANCELLED
SUPERSEDED
```

Conceptual transitions:

```text
PROPOSED  -> ACTIVE | CANCELLED | SUPERSEDED
ACTIVE    -> WAITING | SATISFIED | FAILED | CANCELLED | SUPERSEDED
WAITING   -> ACTIVE | SATISFIED | FAILED | CANCELLED | SUPERSEDED
SATISFIED -> []
FAILED    -> []
CANCELLED -> []
SUPERSEDED-> []
```

`SATISFIED` requires Mission verdict `SATISFIED`.

`FAILED` requires explicit authorized Mission termination and a Mission that
is not satisfied.

`CANCELLED` requires authorized Mission cancellation.

`SUPERSEDED` requires a successor Mission Revision.

`INCONCLUSIVE` does not imply a terminal lifecycle state.

`NOT_SATISFIED` alone does not imply `FAILED`.

Mission lifecycle state must not substitute for Program definition state,
Runtime Task state, evidence result, Program verdict, or Controller
verification state.

Mission cancellation or supersession does not directly mutate an already
locked Program runtime. Existing Programs remain bound to the exact Mission
Revision under which they were admitted.

Changing Mission owner requires a superseding Mission Revision.

## Constraints

* Mission definition history is append-only.
* Mission state must be durably representable outside agent conversation.
* Mission state changes cannot directly mutate Program Lock, Runtime Task,
  lease, or Controller state.
* Mission supersession never silently rebinds historical Programs.

## Consequences

Mission continuity can evolve without rewriting historical execution authority.
Lifecycle status can change while exact Mission definition identity remains
stable and reproducible.

## Rejected alternatives

### Keep lifecycle inside the Mission definition document

Rejected because ordinary state transitions would mutate digest-bound
authoritative semantics.

### Resolve the newest Mission Revision during Program execution

Rejected because a running Program must remain bound to the exact authority
under which it was admitted.

## Related

* ADR-0024 — Mission parent intent and Controller boundary
* ADR-0026 — Exact Mission Program Binding
* `environment/program-execution/core/shared/STATE_MODEL.yaml`
