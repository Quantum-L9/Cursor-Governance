# ADR-0027: Rule activation is explicit, faithfully representable, and context-budgeted

**Status:** Accepted  
**Date:** 2026-08-14

## Context

The current generated manifest reports 63 rule files, of which 27 are `always_apply: true`. Individual entries also carry qualitative context-cost classifications, and current rules span both global always-on behavior and file/request-scoped activation.

Always-on context is operationally expensive and architecturally dangerous:

- unrelated doctrine enters every task;
- duplicated policy consumes context repeatedly;
- stale law has maximal blast radius;
- broad activation can turn a domain constraint into global behavior.

`alwaysApply` therefore requires explicit governance.

## Decision

Treat activation and context consumption as first-class compiled properties.

### Allowed v1 activation modes

Each Rule Activation Binding MUST declare exactly one primary activation mode:

- `always`
- `glob`
- `agent_requested`

Additional platform capabilities require schema evolution.

### `always` is scarce

`always` is reserved for governance that must be available before narrower routing can safely occur.

Appropriate categories include authority/conflict behavior, core execution safety, bootstrap routing, globally applicable mutation constraints, and minimal evidence-honesty requirements.

“Important” alone is not sufficient justification.

### Always-on justification

Every `always` binding MUST declare:

```yaml
activation:
  mode: always
  justification_ref: <contract-or-ADR>
```

The justification must explain why delayed or narrower activation is unsafe or structurally impossible.

### Prefer narrowing

Where semantics apply only to language families, file paths, CI configuration, deployment files, tests, infrastructure, or specific operations, the rule SHOULD use an applicable narrowing mode.

### Context budgets

Each generated binding MUST declare:

```yaml
render:
  context_budget_tokens: <integer>
```

Compilation measures actual rendered context.

The manifest records measured tokens, budget tokens, and budget status.

Exceeding an individual hard budget blocks generation.

### Global always-on budget

A separate machine configuration defines the total maximum rendered token budget of the always-on rule set.

The numeric value is configuration, not an architectural constant in this ADR.

Compilation MUST calculate:

```text
sum(measured_tokens for all always bindings)
```

and fail if the configured hard limit is exceeded.

### Context expansion requires reviewable evidence

A generated rule that grows materially SHOULD identify which contract clauses caused growth, old token count, new token count, and delta.

This turns context expansion into visible architectural cost.

### No silent activation widening

If a binding requires a scope that cannot be faithfully represented by Cursor, the compiler fails.

It MUST NOT use `alwaysApply: true` as a fallback.

## Options considered

### Keep `alwaysApply` as ordinary author preference
Rejected because it encourages context accumulation and broad authority projection.

### Eliminate all always-on rules
Rejected because some bootstrap and constitutional governance must exist before task-specific routing.

### Treat always-on context as a finite governed budget
Chosen.

## Invariants

- RULE-ACT-001 — Activation mode is explicit.
- RULE-ACT-002 — `always` requires machine-visible justification.
- RULE-ACT-003 — Context budget is measured from rendered output.
- RULE-ACT-004 — Individual budget excess blocks generation.
- RULE-ACT-005 — Global always-on hard budget excess blocks generation.
- RULE-ACT-006 — Unsupported activation cannot silently widen.
- RULE-ACT-007 — Important-but-scoped doctrine remains scoped.

## Consequences

The current always-on population is expected to shrink over migration.

No specific target count is mandated. The desired state is the smallest set consistent with safe activation.

## Related

- ADR-0025
- ADR-0028
- ADR-0029
- `rules/RULES-MANIFEST.yaml`
