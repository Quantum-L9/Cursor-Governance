# ADR-0008: Rule Activation Binding is the canonical intermediate representation between contracts and platform rules

**Status:** Accepted  
**Date:** 2026-08-14

## Context

The contract layer answers: What is true, permitted, prohibited, required, or evidenced?

Cursor `.mdc` files answer a different question: When should particular governance enter model context, and how should Cursor receive it?

Binding those two concerns directly inside generated Markdown would make generation platform-specific and prevent reuse across other agent environments.

Cursor activation currently relies on metadata including fields such as description, activation mode, `alwaysApply`, and globs. The existing manifest already inventories those properties.

A canonical intermediate representation is required.

## Decision

Introduce:

`contracts/schemas/canonical.schema.rule_activation_binding.v1.yaml`

and store canonical binding instances under:

```text
contracts/
└── projections/
    └── rules/
        ├── <binding>.yaml
        └── ...
```

A Rule Activation Binding is not a semantic contract.

It is a projection-binding artifact identifying:

1. the delivery target;
2. activation conditions;
3. exact governing contract clauses;
4. permitted advisory guidance;
5. lowering/rendering requirements;
6. context budget;
7. lifecycle state.

## Canonical shape

A binding MUST be structurally equivalent to:

```yaml
binding_id: RULE.CURSOR.GRAPHITI_MEMORY.001
schema_ref: canonical.schema.rule_activation_binding.v1
version: 1.0.0
status: active
target:
  platform: cursor
  format: mdc
  output_path: rules/03-graphiti-memory.mdc
rule_identity:
  rule_id: l9.rule.graphiti.memory
  rule_version: 2.0.0
  domain: memory
activation:
  mode: always
  globs: []
  description: >
    Inject Graphiti episodic-memory governance into Cursor context.
  justification_ref: MEM.FRONTDOOR.001
contract_bindings:
  - contract_id: MEM.FRONTDOOR.001
    version_constraint: "^2.0"
    clauses:
      - C01
      - C02
  - contract_id: MEM.GROUP_ID.001
    version_constraint: "^1.0"
    clauses:
      - C01
      - C02
guidance:
  refs: []
render:
  renderer: cursor_mdc_v1
  context_budget_tokens: 220
  include_rationale: false
  include_examples: false
lifecycle:
  migration_state: generated
```

Exact schema structure MAY evolve through schema versioning. The architectural responsibilities above do not.

## Binding rules

### Contract references are clause-level

A binding SHOULD reference the minimum contract clauses required for its purpose.

Avoid broad wildcard clause selection when only a small number of clauses apply. Clause-level references provide context minimization, impact analysis, conflict precision, and projection provenance.

### Binding cannot modify semantics

The binding may select contract clauses. It may not rewrite them into alternate normative meaning.

### Scope intersection

Effective projected scope is:

```text
effective_scope =
    contract_scope
    ∩ binding_activation_scope
    ∩ target_platform_scope
```

A binding may narrow delivery. A binding MUST NOT widen contract authority.

### Version resolution

Bindings MUST resolve against the canonical contract registry.

A binding MUST NOT point silently to missing contracts, draft contracts when active authority is required, retired contracts, deprecated contracts without an explicit migration allowance, or nonexistent clause IDs.

### Platform separation

The neutral binding is canonical. Cursor `.mdc` syntax is not.

A future platform adapter may consume the same semantic contracts through a different projection binding.

The contract system MUST NOT encode Cursor frontmatter as global governance semantics.

### Initial activation vocabulary

Version 1 supports only activation semantics that can be represented honestly by the current delivery mechanism:

- `always`
- `glob`
- `agent_requested`

Richer future predicates such as `intent`, `operation`, `workflow_state`, and `runtime_capability` MAY be added only when there is an actual resolver capable of enforcing or faithfully lowering them.

The schema MUST NOT claim activation precision the runtime does not possess.

### Unsupported lowering

If a target cannot faithfully represent a binding’s required activation semantics, compilation MUST fail.

The compiler MUST NOT silently convert specific activation into `alwaysApply: true` merely because the target cannot express the specific condition.

## Options considered

### Put contract IDs directly into hand-authored `.mdc`
Rejected because `.mdc` remains both source and output.

### Make the manifest itself the source binding model
Rejected because the manifest is a generated inventory and registry. A generated artifact should not own source configuration.

### Introduce a canonical Rule Activation Binding
Chosen.

It cleanly separates semantic truth, activation/delivery configuration, and platform rendering.

## Invariants

- RULE-BIND-001 — Every generated rule has exactly one canonical binding.
- RULE-BIND-002 — Every contract and clause reference resolves.
- RULE-BIND-003 — Effective binding scope never exceeds contract scope.
- RULE-BIND-004 — Unsupported target lowering blocks generation.
- RULE-BIND-005 — Bindings do not become semantic owners.
- RULE-BIND-006 — Binding changes invalidate the generated projection digest.

## Consequences

This introduces one new canonical artifact type but removes semantic responsibility from `.mdc`.

It also creates the point at which future IDE/agent adapters can diverge without duplicating policy.

## Related

- ADR-0007
- ADR-0010
- ADR-0011
- `canonical.schema.contract_projection_binding.v1`
