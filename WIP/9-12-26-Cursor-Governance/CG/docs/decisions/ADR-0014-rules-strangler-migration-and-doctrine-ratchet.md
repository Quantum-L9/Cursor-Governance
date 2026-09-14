# ADR-0014: Existing Cursor rules migrate through a strangler lifecycle with a monotonic hidden-doctrine ratchet

**Status:** Accepted  
**Date:** 2026-08-14

## Context

The current manifest inventories 63 `.mdc` rules. They contain a mixture of shared normative doctrine, skill/rule routing, domain constraints, workflow procedure, capability statements, advisory guidance, examples, historical state, and superseded doctrine.

Converting all rules in one rewrite would create unnecessary semantic risk.

At the same time, allowing new hidden doctrine while legacy rules are migrated would prevent convergence.

A strangler migration is required.

## Decision

Every rule progresses through a machine-visible migration lifecycle:

```text
legacy
   ↓
extracted
   ↓
hybrid
   ↓
contract_bound
   ↓
generated
   ↓
retired
```

Backward movement is forbidden except through an explicit ADR superseding this decision.

## Lifecycle definitions

### legacy
Current hand-authored rule.

Characteristics:
- may own grandfathered normative prose;
- included in doctrine census;
- hidden doctrine counted as migration debt;
- new doctrine increase forbidden.

### extracted
Every candidate normative/procedural/advisory block has an extraction record.

No claim is yet made that canonical contracts preserve all semantics.

### hybrid
Some doctrine has canonical contract ownership and projection references, while unresolved legacy doctrine remains.

The remaining debt is explicit.

### contract_bound
Every normative statement has exactly one resolved semantic owner.

No hidden shared normative doctrine remains.

Rule may still be hand-rendered temporarily while parity is proven.

### generated
`.mdc` is deterministic output under ADR-0011.

Normative rule-owned prose is zero.

Manual normative edits are impossible to land because parity validation fails.

### retired
Rule no longer participates in active delivery.

Its history may remain in Git.

Active references and regenerators must be extinguished.

## Migration lifecycle

For each rule:

```text
EXTRACT
   ↓
CLASSIFY
   ↓
CANONIZE
   ↓
BIND
   ↓
PROVE
   ↓
GENERATE
   ↓
EXTINGUISH OLD OWNERSHIP
```

### Extract
Produce exact-provenance extraction records. Do not edit source semantics first.

### Classify
Every meaningful block is classified as one of:

- activation
- shared_normative
- skill_or_domain_local_normative
- workflow_procedure
- capability_claim
- evidence_requirement
- advisory_guidance
- rationale
- example
- historical_state
- obsolete
- unknown
- conflict

### Canonize
Shared normative doctrine becomes or binds to canonical contracts.

Conflicts are reviewed; they are not reconciled automatically.

### Bind
Create canonical Rule Activation Binding referencing exact contract clauses.

### Prove
Demonstrate semantic parity using contract validation, projection validation, positive fixtures, negative fixtures, doctrine scan, and human review for ambiguous extraction.

### Generate
Render deterministic `.mdc`.

### Extinguish
Remove old independent normative ownership and prove that no generator or active source recreates it.

## Monotonic doctrine ratchet

Rules receive their own migration baseline:

`ops/config/doctrine-baseline.rules.yaml`

The rules doctrine engine may share the extraction/clustering infrastructure established for skills.

Policy:

```text
existing hidden doctrine may remain temporarily
existing hidden doctrine may decrease
existing hidden doctrine may never increase
new hidden doctrine = fail
new unbound rule = fail
new unresolved contract ref = fail
new conflict = fail
generated-rule drift = fail
```

There is no routine command to enlarge the baseline.

Increasing the baseline is a governance-policy change requiring explicit reviewed modification.

## New-rule law

After ADR-0014 implementation reaches enforcement:

New `.mdc` files MUST start at `contract_bound` or `generated`.

No new file may enter as `legacy`.

## No destructive semantic migration

Original rule prose MUST NOT be deleted merely because an extraction candidate exists.

Required order:

```text
extract
→ canonical owner accepted
→ binding created
→ projection generated
→ parity/evidence passes
→ old independent prose ownership removed
```

This prevents semantic loss.

## Migration prioritization

Migration is ordered by leverage, not filename.

Suggested score:

```text
migration_priority =
    risk
  × normative_strength
  × activation_blast_radius
  × occurrence_duplication
  × conflict_density
  × execution_frequency
```

The exact scoring function is implementation policy, but high-blast-radius always-on governance outranks low-risk advisory material.

## Initial proving set

The first three migrated rules SHOULD deliberately cover different shapes.

### `03-graphiti-memory.mdc`
Represents dense, always-on shared normative doctrine and memory authority.

It proves shared contract extraction, clause projection, always-on justification, SSOT/authority migration, and memory doctrine consolidation.

### `93-c1-server-protection.mdc`
Represents mixed protected-resource policy, authorization, procedure, and historical/state material.

It proves policy extraction, protected-resource contracts, approval policy, procedure separation, and rationale/state separation.

### `70-tool-efficiency.mdc`
Represents primarily advisory and procedural material and is currently agent-requested rather than always applied.

It proves avoiding contract inflation, advisory channel behavior, guidance retention, and separation of actual governance from preferred ergonomics.

Migration architecture is not considered proven until all three shapes can be represented without semantic loss or artificial canonization.

## Rule-specific definition of done

A rule is generated only when all are true:

1. every normative block has an owner;
2. every owner resolves to an active contract;
3. every projected clause exists;
4. activation is explicit;
5. activation is representable by Cursor;
6. no scope widening exists;
7. no unresolved conflicts exist;
8. advisory text contains no hidden doctrine;
9. context budget passes;
10. deterministic generation produces the tracked `.mdc`;
11. manifest entry matches;
12. generated doctrine scanner reports zero hidden normative ownership;
13. negative fixtures prove reopening the seam fails.

## Repository convergence conditions

The rule migration is complete when:

```text
legacy_rules                         == 0
extracted_rules                      == 0
hybrid_rules                         == 0
unowned_rule_doctrine                == 0
unresolved_rule_contract_refs        == 0
unresolved_rule_conflicts            == 0
generated_projection_drift           == 0
rule_context_budget_violations       == 0
new_rule_owned_shared_doctrine       == 0
```

`contract_bound` MAY remain temporarily only where an external rendering limitation prevents generation and that limitation is explicitly documented. The desired steady state is generated projection.

## Rollback

Before a rule reaches generated, migration may revert to the last proven state.

After a rule reaches generated, rollback means reverting the contracts/binding/compiler commit, not reintroducing hand-authored semantic ownership.

A migration defect is not an authorization to reopen the original architectural seam.

## Options considered

### Rewrite all 63 rules at once
Rejected because semantic extraction risk is too high.

### Migrate opportunistically with no baseline
Rejected because new hidden doctrine could arrive as quickly as old doctrine is removed.

### Strangler migration plus monotonic ratchet
Chosen.

## Invariants

- RULE-MIG-001 — Legacy debt may only decrease.
- RULE-MIG-002 — New rules cannot enter legacy state.
- RULE-MIG-003 — Extraction never automatically creates authority.
- RULE-MIG-004 — Conflict is preserved until explicitly resolved.
- RULE-MIG-005 — Old ownership is extinguished only after parity proof.
- RULE-MIG-006 — Generated rules cannot regress to hand-owned semantics.
- RULE-MIG-007 — Migration completeness is machine measurable.

## Consequences

This allows the repository to become contract-first incrementally without freezing ordinary work.

Most importantly, the migration has a one-way direction:

```text
prose-owned governance
        ↓
contract-owned governance
```

and no approved path quietly moves it back.

## Related

- ADR-0007 through ADR-0013
- doctrine extraction schema family
- skills doctrine census/ratchet
- `rules/RULES-MANIFEST.yaml`
- `03-graphiti-memory.mdc`
- `93-c1-server-protection.mdc`
- `70-tool-efficiency.mdc`
