# ADR-0028: Cursor .mdc files are deterministic generated projections with clause-level provenance

**Status:** Accepted  
**Date:** 2026-08-14

## Context

The contract layer will be ineffective if projected `.mdc` files can drift independently afterward.

At the same time, simply projecting contract IDs is insufficient. Cursor needs actual directives in context, not instructions to search elsewhere.

Therefore `.mdc` must remain readable and self-contained while ceasing to be hand-authored semantic authority.

## Decision

Once a rule reaches `migration_state: generated`, its `.mdc` file is produced deterministically from:

```text
active contracts
    +
rule activation binding
    +
permitted guidance
    +
renderer version
```

### Generated header

Every generated rule MUST contain a machine-detectable header equivalent to:

```text
GENERATED FILE — DO NOT EDIT
binding: RULE.CURSOR.GRAPHITI_MEMORY.001
renderer: cursor_mdc_v1
contract-bundle-sha256: <digest>
binding-sha256: <digest>
```

The exact comment syntax is renderer-defined.

### Frontmatter

The renderer produces Cursor-compatible frontmatter from the activation binding.

No other source manually controls frontmatter for a generated rule.

### Clause-level provenance

Every normative directive MUST preserve provenance.

Example:

```text
- Resume state MUST come from Graphiti. [MEM.FRONTDOOR.001:C01]
```

A directive synthesized from multiple clauses MUST enumerate all contributing clauses.

### Human readability remains required

Generated rules MUST NOT become opaque bundles such as “Apply contracts MEM.001, MEM.002, MEM.003.”

The effective directives themselves must be rendered.

### Determinism

For identical contracts, contract versions, contract digests, binding, and renderer version, the resulting `.mdc` bytes MUST be identical.

Generation MUST NOT depend on wall-clock timestamps inside output, filesystem iteration order, locale, network availability, or nondeterministic LLM output.

LLMs MAY assist contract extraction before canonization.

LLMs MUST NOT be required to regenerate canonical rule projections.

### Canonical projection digest

The manifest stores the SHA-256 of generated output.

Validation compares deterministic regenerated output rather than file mtime.

### No hand edits

A hand edit to a generated rule is projection drift.

The supported repair path is:

```text
change contract
or
change binding/guidance
or
change renderer
then regenerate
```

not: edit generated `.mdc`.

### Atomic generation

The compiler SHOULD:

1. render to temporary output;
2. validate all outputs;
3. build the proposed manifest;
4. compare/check;
5. atomically replace generated files only after global success.

Partial generation is forbidden.

### Check mode

CI/pre-commit MUST support a no-write mode:

```text
generate expected output in memory/temp
compare against tracked output
fail on diff
```

## Options considered

### Generated `.mdc` contains only contract references
Rejected because it adds runtime lookup burden and weakens context delivery.

### Hand-maintained prose plus contract IDs
Rejected because IDs do not prevent semantic drift.

### Deterministic self-contained projection with provenance
Chosen.

## Invariants

- RULE-PROJ-001 — Generated rule bytes are deterministic.
- RULE-PROJ-002 — Every normative directive has clause provenance.
- RULE-PROJ-003 — Generated output is readable without opening contract files.
- RULE-PROJ-004 — Manual edits fail parity validation.
- RULE-PROJ-005 — mtime is not correctness evidence.
- RULE-PROJ-006 — Generation is atomic across the rule set.
- RULE-PROJ-007 — LLM generation is not required for reproducibility.

## Consequences

The `.mdc` directory becomes reproducible.

Deleting generated files is recoverable because semantic authority remains elsewhere.

## Related

- ADR-0024
- ADR-0025
- ADR-0029
- ADR-0030
- `canonical.schema.contract_projection_binding.v1`
