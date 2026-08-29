# ADR-0027: Mission Acceptance Is Separate from Program Acceptance

* Status: Accepted
* Date: 2026-08-28
* Decision owner: L9 architecture

## Context

One Mission may require evidence from multiple Programs. A Program can
converge successfully while the durable Mission objective remains incomplete.

Treating Program convergence, Program-owner acceptance, Task completion, local
verification, or model claims as Mission acceptance would collapse distinct
authority and evidence boundaries.

## Decision

Mission acceptance is an independent evidence-backed evaluation over one exact
Mission Revision.

Program convergence and Program-owner acceptance may contribute evidence
toward Mission Acceptance Criteria. They do not constitute Mission acceptance.

Mission criterion results and Mission verdicts bind the exact Mission digest.

Canonical criterion result states:

```text
UNSATISFIED
PARTIALLY_SATISFIED
SATISFIED
WAIVED
BLOCKED
UNKNOWN
```

Only `SATISFIED` is unconditionally passing.

`WAIVED` is conditional on authorized waiver semantics.

`UNKNOWN` is non-passing.

Mission verdict values:

```text
SATISFIED
NOT_SATISFIED
INCONCLUSIVE
CANCELLED
```

The canonical Mission verdict owner is the Mission owner.

Controller recommendations concerning Mission satisfaction are advisory only.

Mission `SATISFIED` requires every required criterion to be either satisfied
or validly waived under applicable authorized policy.

The following collapses are prohibited:

```text
Program CONVERGED => Mission SATISFIED
Program ACCEPTED  => Mission SATISFIED
Task COMPLETED    => Mission SATISFIED
local verification => Mission SATISFIED
worker claim => Mission acceptance evidence by itself
unverified model statement => Mission acceptance evidence
```

Mission evidence extends the existing Program Execution evidence model and
preserves retrievability, exact-state binding, producer identity, production
time, expiration/invalidation handling, claim-scoped support, and UNKNOWN as
non-passing.

## Constraints

* Program verdict ownership remains unchanged.
* Mission verdict ownership remains with Mission owner.
* Mission acceptance never becomes Controller verification.
* Task completion never becomes Mission acceptance.
* No parallel Mission evidence plane is created.

## Consequences

A durable Mission can aggregate evidence across Programs without weakening
Program acceptance or runtime ownership boundaries.

## Rejected alternatives

### Program accepted implies Mission satisfied

Rejected because a Program may represent only one contribution to a larger
Mission.

### Controller issues Mission verdict

Rejected because runtime execution authority is not durable Mission acceptance
authority.

### Local verification proves Mission satisfaction

Rejected because local verification is not sufficient outcome-level Mission
evidence.

## Related

* ADR-0024 — Mission parent intent and Controller boundary
* ADR-0025 — Mission Revision immutability and lifecycle separation
* `environment/program-execution/core/shared/EVIDENCE_MODEL.yaml`
* `environment/program-execution/core/shared/OWNERSHIP_MATRIX.yaml`
