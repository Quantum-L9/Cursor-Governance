# ADR-0024: Contracts own rule semantics; Cursor rules are activation and projection surfaces

**Status:** Accepted  
**Date:** 2026-08-14

## Context

`rules/**` currently contains both delivery metadata and substantive governance doctrine. Individual `.mdc` files can define source-of-truth claims, prohibitions, approval requirements, protected resources, workflow instructions, evidence expectations, security constraints, and architectural invariants.

For example, `03-graphiti-memory.mdc` is globally and always activated and directly describes Graphiti memory authority and SSOT behavior. `93-c1-server-protection.mdc` combines protected-resource policy with explicit authorization requirements and procedural STOP/ASK/WAIT behavior. Other rules are primarily advisory; `70-tool-efficiency.mdc`, for example, contains recommendations concerning development workflow, package scripts, Git ergonomics, and validation efficiency.

This creates multiple semantic owners for the same concepts. A rule can disagree with a skill, `AGENTS.md`, `CANONICAL_LAW.md`, a workflow, or another rule. Agents then reconstruct effective policy from prose rather than resolving explicit contracts.

The canonical governance contract schemas now provide first-class semantic owners for invariants, policies, capabilities, workflows, evidence obligations, projections, and extraction provenance.

A decision is required concerning whether rules remain independent governance authorities or become consumers of those contracts.

## Decision

Contracts are the sole semantic owners of shared normative governance. Cursor rules do not independently own shared governance semantics.

A Cursor rule has exactly three permitted responsibilities:

1. **Activation**
   - determine when governance should enter the Cursor context;
   - express Cursor-compatible activation metadata;
   - bind repository/file/domain activation to contract clauses.
2. **Projection**
   - deliver resolved contract semantics in a compact human/model-readable form;
   - preserve exact clause provenance;
   - carry deterministic projection integrity information.
3. **Bounded non-normative guidance**
   - examples;
   - ergonomics;
   - local explanatory guidance;
   - hints that do not establish authority, permission, prohibition, required evidence, or failure semantics.

Rules MUST NOT independently establish shared:

- MUST / MUST NOT requirements;
- authorization or approval requirements;
- protected-resource definitions;
- source-of-truth or authority claims;
- precedence rules;
- destructive-operation constraints;
- Git mutation/publish policy;
- deployment policy;
- memory authority;
- secrets policy;
- evidence requirements;
- fail-open/fail-closed semantics;
- architecture boundaries;
- externally meaningful capability claims.

Those semantics MUST be owned by canonical contracts.

### No separate “rule contract” semantic layer

The repository MUST NOT create a second contract class whose purpose is merely to move existing rule prose into objects called “rule contracts.”

The authority topology is:

```text
canonical contract
       │
       │ owns semantics
       ▼
rule activation binding
       │
       │ selects + projects
       ▼
generated Cursor .mdc
```

Not:

```text
canonical contract
       │
rule contract
       │
Cursor rule
```

The latter recreates semantic duplication.

### Rule numbers do not establish authority

Filename prefixes such as `00-`, `03-`, `45-`, `60-`, and `93-` MUST NOT be interpreted as authority precedence.

They MAY remain for familiar repository organization, stable filenames, historical continuity, and Cursor loading ergonomics. They MUST NOT resolve semantic conflict.

### Existing legacy rules

Existing hand-authored rules remain valid migration sources until converted under ADR-0031.

Their current normative statements are grandfathered migration debt, not an endorsement of rule-owned authority as the future architecture.

### New rules

After the contract-first rule compiler becomes active, every newly introduced rule MUST be contract-bound at creation.

A new rule containing shared normative semantics without an owning contract is invalid.

## Options considered

### Option 1 — Keep rules as independent authority

Rejected.

Advantages:
- minimum immediate migration effort;
- preserves current editing workflow.

Disadvantages:
- perpetuates duplicate semantic ownership;
- requires agents to interpret conflicting prose;
- prevents reliable impact analysis;
- makes contract-first governance cosmetic rather than structural.

### Option 2 — Convert every rule directly into a contract

Rejected.

Rules contain several distinct content types: activation, normative policy, procedure, guidance, examples, and historical context. Treating the whole rule as one contract would canonize advisory or procedural material incorrectly.

### Option 3 — Contracts own semantics; rules become activation/projection surfaces

Chosen.

It preserves Cursor rule delivery while eliminating rules as independent semantic owners.

## Invariants

- RULE-SEM-001 — Shared normative behavior has exactly one semantic owner.
- RULE-SEM-002 — A generated rule cannot redefine a contract clause.
- RULE-SEM-003 — Rule filename ordering is not policy precedence.
- RULE-SEM-004 — Rules may narrow delivery scope only according to their binding.
- RULE-SEM-005 — Rules may not silently widen contract authority.
- RULE-SEM-006 — A contract remains authoritative if every `.mdc` projection is deleted and regenerated.

## Consequences

Positive:
- rule conflicts become machine-detectable;
- contract changes can identify affected rules mechanically;
- Cursor remains supplied with readable directives;
- shared governance ceases to depend on prose archaeology;
- rule files become disposable projections rather than irreplaceable law.

Costs:
- current rules must be classified and migrated;
- contract extraction requires deliberate semantic review;
- generated rules can no longer accept convenient direct edits.

## Related

- ADR-0002 — enforcement rather than advisory context
- ADR-0006 — single memory front door
- `canonical.schema.governance_contract.v1`
- `canonical.schema.contract_projection_binding.v1`
- `rules/RULES-MANIFEST.yaml`
- ADR-0025 through ADR-0031
