# ADR-0013: Rule compilation fails closed on unresolved authority, conflict, scope widening, unsupported activation, context overflow, and projection drift

**Status:** Accepted  
**Date:** 2026-08-14

## Context

Moving authority into contracts does not solve drift if the compiler tolerates broken references, contradictory clauses, stale projections, or unsupported activation.

A contract-first repository requires the build step to behave like a compiler:

```text
invalid governance graph
        ↓
compile error
```

not:

```text
warning
        ↓
model decides what probably applies
```

This follows the enforcement direction already captured in ADR-0002, where an instruction that can simply be skipped is not treated as an effective control.

## Decision

Create a fail-closed rule compilation pipeline.

Conceptually:

```text
contracts
    │
bindings
    │
guidance
    ▼
[1] schema validation
    ▼
[2] contract resolution
    ▼
[3] binding validation
    ▼
[4] scope intersection
    ▼
[5] conflict detection
    ▼
[6] activation lowering
    ▼
[7] normative/advisory validation
    ▼
[8] context-budget validation
    ▼
[9] deterministic render
    ▼
[10] manifest build
    ▼
[11] projection parity
    ▼
generated rules
```

No output is committed/replaced until every blocking stage succeeds.

## Blocking compiler failures

- RULE-COMP-001 — Missing contract. Result: fail.
- RULE-COMP-002 — Invalid contract lifecycle. Result: fail.
- RULE-COMP-003 — Missing clause. Result: fail.
- RULE-COMP-004 — Contract digest mismatch. Result: fail.
- RULE-COMP-005 — Binding scope widening. Result: fail.
- RULE-COMP-006 — Unsupported activation lowering. Result: fail.
- RULE-COMP-007 — Simultaneously applicable semantic conflict. Result: fail.
- RULE-COMP-008 — Undeclared precedence. Result: fail.
- RULE-COMP-009 — Advisory contradiction. Result: fail.
- RULE-COMP-010 — Advisory hidden doctrine. Result: fail.
- RULE-COMP-011 — Context budget exceeded. Result: fail.
- RULE-COMP-012 — Projection drift. Result: fail.
- RULE-COMP-013 — Manifest drift. Result: fail.
- RULE-COMP-014 — Unbound generated rule. Result: fail.
- RULE-COMP-015 — Duplicate output ownership. Result: fail.
- RULE-COMP-016 — Ambiguous identity. Result: fail.

## Conflict resolution law

The compiler MUST NOT resolve normative conflict using filename order, numeric rule prefix, manifest order, lexical order, “last one wins,” model judgment, modification time, shortest or longest rule, or whichever rule is always-on.

Conflict is resolved only through canonical contract semantics such as declared authority, explicit supersession, scope disjointness, mutually exclusive conditions, or explicit canonical replacement.

Absent one of those, compilation stops.

## Scope law

For every projected clause the compiler must be able to derive:

```text
contract scope
binding scope
effective scope
```

and prove:

```text
effective scope ⊆ contract scope
```

Unknown scope is not permission to widen.

## Validation modes

### build
Produce candidate generated output after all validation.

### check
Generate expected state without mutating the workspace and compare.

### explain
For a rule, print activation, binding, contract versions, clauses, effective scope, provenance, and context cost.

### impact
For a contract/clause change, list affected rule projections.

These modes MAY share one implementation.

## No enforcement-critical warnings

Conditions listed as blocking in this ADR MUST never emit `WARN + continue`.

They are errors.

## Required negative tests

The compiler test suite MUST contain negative fixtures proving rejection of:

1. missing contract;
2. missing clause;
3. retired contract;
4. conflicting require/prohibit;
5. activation widening;
6. unsupported activation;
7. advisory MUST;
8. context overflow;
9. manually modified generated `.mdc`;
10. stale manifest;
11. duplicate output binding;
12. numeric-file-order conflict;
13. invalid digest;
14. hand-authored normative text injected into a generated projection.

## Options considered

### Warn on contradictions and continue
Rejected because that recreates model interpretation as the ultimate policy resolver.

### Give numeric rule order precedence
Rejected because filename organization is not semantic authority.

### Fail closed
Chosen.

## Invariants

- RULE-COMPILER-001 — Invalid governance graph cannot generate rules.
- RULE-COMPILER-002 — Conflict is explicit, never implicit.
- RULE-COMPILER-003 — Unknown does not become permit.
- RULE-COMPILER-004 — Projection drift is a build failure.
- RULE-COMPILER-005 — Blocking conditions never downgrade to warnings.
- RULE-COMPILER-006 — Identical inputs produce identical outputs.

## Consequences

The compiler becomes an assurance boundary.

A broken contract relationship fails before an agent can consume contradictory generated rules.

## Related

- ADR-0002
- ADR-0007 through ADR-0012
- `canonical.schema.contract_registry.v1`
- `canonical.schema.contract_projection_binding.v1`
