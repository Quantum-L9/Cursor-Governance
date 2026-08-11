# ADR-0013: Shared agent semantics have one canonical source; peer-local semantic forks are forbidden

## Status

Accepted

## Date

2026-08-10

## Context

Program Execution spans multiple surfaces and execution peers. A useful new behavior implemented directly in one peer — for example Claude Code replanning, Cursor intent resolution, or Codex recovery policy — can quickly become a second governance implementation.

Cursor-Governance already follows a build-inward, wrap-outward model: shared capability belongs in Cursor-primary or adapter-neutral governance, while peer environments are bindings.

Intent compilation and replanning increase the risk of semantic drift because they influence planning, authority, and escalation behavior.

## Decision

1. Intent semantics, autonomy policy, replanning semantics, evidence law, authorization interpretation, recovery rules, and peer-parity requirements have exactly one canonical shared source.
2. A shared semantic capability must be implemented first in Program Execution core/shared or another adapter-neutral/Cursor-primary governance home.
3. Direct semantic implementation or modification in a single peer is prohibited.
4. Peer adapters may:
    * translate transport;
    * render host-specific syntax;
    * map capabilities;
    * narrow authority;
    * fail closed where the host cannot comply.
5. Peer adapters may not:
    * redefine canonical decisions;
    * widen authority;
    * change escalation semantics;
    * maintain an independent replan brain;
    * carry local semantic overrides.
6. A peer-specific defect is fixed at the canonical layer when it exposes a shared semantic defect. Only transport-specific defects are fixed in the peer adapter.
7. Generated peer artifacts are projections and are not hand-edited.

## Options considered

1. Implement features independently per peer. Rejected: duplicate brains and inevitable semantic drift.
2. Use one peer as implementation and import it from others. Rejected: makes a dependent adapter the owner of shared architecture.
3. Own semantics centrally and project thin bindings to every peer. Chosen: matches Cursor-Governance ownership law.

## Consequences

### Positive

* Architecture evolves once instead of N times.
* Agent surfaces remain behaviorally comparable.
* A shared fix automatically has a path to every peer.
* Peer folders remain replaceable adapters rather than capability owners.

### Negative / costs

* Shared abstractions must accommodate different host capabilities.
* Peer-specific experiments cannot silently become production semantics.
* Generation and conformance tooling become mandatory.

## Related

* ADR-0009 — named autonomy policy profiles
* ADR-0014 — atomic all-peer semantic revisions
* ADR-0015 — golden semantic vectors and peer parity
* CANONICAL_LAW.md §2 and §2.1
