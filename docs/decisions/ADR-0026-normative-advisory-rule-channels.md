# ADR-0026: Normative and advisory content are separate channels in rule projections

**Status:** Accepted  
**Date:** 2026-08-14

## Context

Existing rules mix requirements and recommendations.

Some rules contain hard language such as `MUST`, `MUST NOT`, `NEVER`, `STOP`, `NO TOUCH`, and `REQUIRED`, while others contain workflow ergonomics and suggestions. For example, `70-tool-efficiency.mdc` includes package-script suggestions, Git workflow advice, and guidance concerning when heavy validation is unnecessary.

Converting every recommendation into a canonical invariant would create policy inflation.

Leaving both kinds of language visually indistinguishable causes agents to over-enforce advice or under-enforce law.

## Decision

Generated rules MUST contain separate normative and advisory channels.

The canonical generated order is:

```text
# <Rule title>
## Governing contracts
...
## Required
...
## Prohibited
...
## Constraints
...
## Guidance
...
```

Empty sections MAY be omitted.

### Normative channel

Only active contract clauses may produce normative rule text.

| Contract effect | Projection |
|---|---|
| require | Required |
| prohibit | Prohibited |
| constrain | Constraints |
| stop | Required / failure directive |
| permit | Permission/constraint text when needed |
| route | Routing directive |
| attest | Evidence/attestation directive |

### Advisory channel

Guidance may include examples, ergonomics, suggested command batching, preferred developer workflows, optional optimization advice, and explanatory references.

Advisory content MUST NOT introduce:

- MUST;
- MUST NOT;
- NEVER;
- PROHIBITED;
- REQUIRED;
- STOP;
- source-of-truth claims;
- authorization requirements;
- protected-resource policy;
- mandatory evidence;
- failure semantics.

### Advisory content cannot override normative content

Where guidance conflicts with a contract clause, the guidance is invalid.

The compiler MUST reject the projection rather than present both.

### Procedural material

Multi-step procedures that affect authorization, side effects, state transition, retry, or compensation SHOULD be promoted to workflow contracts rather than retained as rule guidance.

A rule MAY contain a short usage example for such a workflow but does not own the procedure.

### Rationale

Historical incidents, architectural rationale, and lengthy explanations SHOULD remain external references.

They SHOULD NOT consume always-on rule context unless necessary for correct execution.

## Options considered

### Convert all rule language into contracts
Rejected because recommendations would become artificial law.

### Leave normative/advisory distinction to wording
Rejected because models can interpret “should,” “always,” “prefer,” and emphatic prose inconsistently.

### Structurally separate the channels
Chosen.

## Invariants

- RULE-CHAN-001 — Normative generated text has contract-clause provenance.
- RULE-CHAN-002 — Advisory text has no semantic authority.
- RULE-CHAN-003 — Advisory text cannot contradict a projected contract.
- RULE-CHAN-004 — Advisory text containing hard normative signals fails validation.
- RULE-CHAN-005 — Procedural governance is not hidden inside guidance.

## Consequences

The repository keeps useful agent ergonomics without allowing convenience text to become accidental policy.

Rules also become easier to read because agents can immediately distinguish what must happen from what is merely useful.

## Related

- ADR-0024
- ADR-0025
- ADR-0028
- `canonical.schema.governance_contract.v1`
