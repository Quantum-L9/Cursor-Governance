# ADR-0033: Compiler-owned structure, target resolution, and program owner

## Status

Accepted

## Date

2026-09-06

## Context

Program Execution consumes a rich campaign source and Blueprint contract, but operators should not have to provide representational fields the compiler can deterministically derive. Architecture lowering already creates program identity, target records, authorities, workstreams, task IDs, dependency edges, waves, gates, and ready evidence tasks. Some ingress paths still duplicate personal owner defaults, and architecture compilation still treats a missing target argument as an immediate input defect even when repository identity is locally discoverable.

## Decision

### Program owner

The canonical Program Execution default program owner is:

`Quantum AI Partners`

A supplied explicit owner may override the default. Compiler surfaces MUST consume one shared owner policy rather than independently hard-code a default. Program ownership is not human acknowledgment identity; PHASE0 `operator_ack.name` remains the authority for a human acknowledgment surface.

### Target resolution

Architecture compilation resolves the target before loading/lowering using this precedence:

1. explicit compiler invocation target;
2. declared architecture frontmatter target;
3. one unambiguous repository explicitly identified by a target/repository label or architecture-subject phrase;
4. target-checkout GitHub origin;
5. execution-workspace GitHub origin only when the source names no repository;
6. fail only if target identity remains genuinely ambiguous or unknowable.

Bare GitHub links are reference evidence, not mutation-target authority. All high-authority target evidence MUST agree: explicit target, declared target, source target/subject declarations, and an explicitly supplied target-checkout origin may establish precedence, but none may silently retarget contradictory authority evidence. Any such contradiction is a semantic authority conflict and MUST fail before side effects. Target resolution and semantic loading MUST be bound to the same normalized source digest.

### Gap ownership

Compiler behavior is classified into four categories:

1. **Derivable structure**: campaign/program IDs, program name, default owner, target IDs, authority IDs, task IDs, workstreams, waves, gates, default statuses, adapters, and other representational structure. The compiler MUST synthesize it.
2. **Discoverable fact**: repository locations, current implementation seams, validation commands, origin identity, and other facts obtainable by bounded inspection. The compiler MUST resolve them directly or materialize ready evidence work with dependency ordering.
3. **Implementation gap**: required capability absent from the repository. The gap MUST become executable work.
4. **Semantic impossibility**: equal-authority contradiction, genuinely ambiguous mutation target, or absence of executable intent. Compilation MUST fail before Blueprint/PEC state is minted.

A derivable or discoverable omission MUST NOT become a runtime blocker merely because the operator did not pre-fill compiler structure.

## Invariants

**PE-COMPILER-001**

> Intent supplies meaning. Compilation supplies structure.

**PE-COMPILER-002**

> Discoverable uncertainty becomes evidence work, not blockage.

**PE-COMPILER-003**

> Missing implementation becomes implementation work, not blockage.

**PE-COMPILER-004**

> Only genuine semantic impossibility may prevent an otherwise executable architecture intent from being minted.

**PE-OWNER-001**

> The Program Execution default program owner is `Quantum AI Partners` across architecture, brief, plan, and activation compiler surfaces.

**PE-OWNER-002**

> Program ownership MUST NOT be reused as the human operator acknowledgment identity. Human acknowledgment is read from the PHASE0 operator-ack contract.

## Consequences

- Operators do not supply `program.id`, `program.name`, `program.definition_status`, generated target/authority IDs, waves, or gates.
- `TARGET=` is optional when repository identity is deterministically resolvable.
- Probeable unknowns remain ready evidence tasks ordered by dependencies, consistent with ADR-0023.
- Owner identity no longer drifts between compiler paths.

## Rejected alternatives

- Requiring operators to hand-author campaign-source representational fields.
- Defaulting unresolved facts to `blocked` tasks.
- Guessing among multiple equally plausible repositories.
- Keeping `Igor Beylin` as a compiler-specific hard-coded default.
