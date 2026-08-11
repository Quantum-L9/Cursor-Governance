# ADR-0015: Golden semantic vectors and a peer-parity gate prove cross-peer equivalence

## Status

Accepted

## Date

2026-08-10

## Context

Generating every peer from one source does not by itself prove equivalent behavior. Different adapters can incorrectly map a permission, treat an Unknown differently, widen a replan, or escalate under different conditions.

Comparing generated text is also insufficient because each host may require different syntax and transport details.

Conformance therefore needs host-independent semantic test cases.

## Decision

1. Introduce canonical golden semantic vectors for shared Program Execution behavior.
2. A vector defines:
    * starting authority and state;
    * relevant evidence;
    * requested or observed event;
    * expected semantic decision;
    * allowed actions;
    * prohibited actions;
    * expected blocker/escalation behavior.
3. The same vector set runs against every registered peer projection.
4. Peer output need not be textually identical; the normalized semantic result must be equivalent.
5. Required negative vectors include:
    * permission widening;
    * missing authority;
    * scoped Unknown behavior;
    * architecture conflict;
    * structural evidence presented as runtime proof;
    * replan outside Program Lock;
    * peer capability unsupported;
    * attempt to create a local semantic override.
6. Introduce a blocking cross-peer parity gate.
7. A semantic revision cannot activate until:
    * canonical validation passes;
    * every peer projection validates;
    * all applicable semantic vectors pass;
    * unsupported capability results fail closed as declared.
8. Conformance evidence is retained with the semantic revision.

## Options considered

1. Trust shared-source generation. Rejected: generator or adapter bugs can still change behavior.
2. Compare generated files byte-for-byte. Rejected: host-specific syntax is legitimately different.
3. Validate normalized semantic behavior with shared vectors. Chosen: tests what matters while permitting transport variation.

## Consequences

### Positive

* Cross-peer equivalence becomes measurable.
* Semantic regressions are detected before rollout.
* New peers can demonstrate compatibility against the same contract.
* Architecture changes gain executable acceptance criteria.

### Negative / costs

* Golden vectors become a governed test corpus.
* Normalization logic must itself be kept small and trustworthy.
* Every new semantic rule may require new positive and negative vectors.

## Related

* ADR-0013 — canonical peer semantics
* ADR-0014 — atomic all-peer semantic revisions
* environment/program-execution/conformance/
* environment/program-execution/registry/
