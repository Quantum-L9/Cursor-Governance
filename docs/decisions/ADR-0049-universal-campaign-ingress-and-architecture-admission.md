# ADR-0049: Universal campaign ingress and typed architecture admission

## Status

Accepted

## Date

2026-09-06

## Context

Org catalog pointer only. The canonical body is
`environment/contracts/execution/adr/ADR-0049-universal-campaign-ingress-and-architecture-admission.md`.
Program Execution already classifies architecture-grade intent, but `make campaign`
still sent undeclared Markdown through the brief compiler.

## Options Considered

1. Inject required architecture frontmatter into the operator source. Rejected
   in the canonical body.
2. Keep `make campaign-architecture` as the normal path for architecture-grade
   prose. Rejected in the canonical body.
3. One `make campaign` ingress with typed `ArchitectureAdmission`, leaving the
   operator source unchanged. **Chosen.** Recorded in the canonical body. This
   file does not restate it.

## Decision

The decision is the canonical body named above. Do not fork a second full body
in `docs/decisions/`.

## Consequences

`docs/decisions/` names ADR-0049. Readers resolve the contract from
`environment/contracts/execution/adr/ADR-0049-universal-campaign-ingress-and-architecture-admission.md`.
