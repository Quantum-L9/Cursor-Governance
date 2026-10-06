# ADR-0050: Compiler-owned structure, target resolution, and program owner

## Status

Accepted

## Date

2026-09-06

## Context

Org catalog pointer only. The canonical body is
`environment/contracts/execution/adr/ADR-0050-compiler-owned-structure-target-resolution-and-program-owner.md`.
Operators were still asked to supply representational fields the Program
Execution compiler can derive, and a missing target failed even when repository
identity was locally discoverable.

## Options Considered

1. Require operators to hand-author campaign-source representational fields.
   Rejected in the canonical body.
2. Default unresolved facts to `blocked` tasks, or guess among equally plausible
   repositories. Rejected in the canonical body.
3. Let compilation supply structure and resolve a target by the canonical
   precedence, failing only on genuine ambiguity. **Chosen.** Recorded in the
   canonical body. This file does not restate it.

## Decision

The decision is the canonical body named above. Do not fork a second full body
in `docs/decisions/`.

## Consequences

`docs/decisions/` names ADR-0050. Readers resolve the contract from
`environment/contracts/execution/adr/ADR-0050-compiler-owned-structure-target-resolution-and-program-owner.md`.
