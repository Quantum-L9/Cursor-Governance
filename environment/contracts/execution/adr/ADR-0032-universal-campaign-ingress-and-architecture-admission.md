# ADR-0032: Universal campaign ingress and typed architecture admission

## Status

Accepted

## Date

2026-09-06

## Context

Program Execution already has a rich architecture compiler that preserves source-grounded obligations, prohibitions, validation, dependencies, evidence, and provenance into `l9.program-execution.campaign-source.v2`. The public `make campaign` front door, however, still routes undeclared Markdown through the weaker brief compiler even when deterministic diagnostics identify architecture-grade structure. The legacy architecture-specific path compensates with a boolean force-admission shortcut, coupling representation admission to an implementation bypass and forcing operators to know which compiler command to select.

This violates the desired operator boundary: the operator supplies semantic intent; Program Execution classifies and compiles it.

## Decision

1. `make campaign INTENT=<artifact>` is the universal production ingress for Program Execution.
2. Explicit structured schemas remain authoritative and are classified before prose heuristics.
3. Raw prose that satisfies the deterministic architecture-classification contract is promoted to `ARCHITECTURE_INTENT_V1` automatically.
4. Automatic promotion MUST NOT rewrite the operator source or insert synthetic frontmatter.
5. Architecture representation admission is typed by `ArchitectureAdmission`:
   - `DECLARED`: source declares `l9.program-execution.architecture-intent.v1` itself.
   - `CLASSIFIED`: the universal front door deterministically classified unchanged prose as architecture intent.
6. Boolean `forced`, explicit-kind overrides, and equivalent bypass states are forbidden.
7. A declared conflicting schema MUST NOT be overridden by `CLASSIFIED` admission.
8. Classification evidence MUST be deterministic, local, explainable, and available in the classification result/receipt.
9. `make campaign-architecture` may remain only as a compatibility alias to the universal classifier. It MUST NOT force a representation. Its `--architecture` flag is retained as an accepted no-op: the runner parses it and never reads it, so it cannot select or influence a kind. The flag exists solely because the repository-root `Makefile` is `additive_only` (`ops/config/root-file-protection.json`) and this change does not rewrite it; removing the flag and its Makefile call site is tracked as separate follow-up work under that protection contract. `test_the_deprecated_architecture_flag_cannot_force_a_representation` fails if it is ever wired back into routing.
10. Once admitted, every architecture path enters the same canonical sequence:

   `architecture source -> campaign-source.v2 -> Blueprint v2 -> PEC -> execute`

## Deterministic promotion contract

Architecture promotion is based on the canonical architecture parser and requires all of:

- at least 3 normative source units;
- at least 2 headings;
- at least 3 architecture feature families such as authority/ownership, implementation, validation/acceptance, prohibitions, rollback, architecture/control-plane language, or implementation surfaces.

Counting uses normative source units, not only unique signal words. Multiple independent `MUST` obligations therefore remain multiple pieces of routing evidence.

## Invariant

**PE-INGRESS-001**

> The operator supplies semantic intent. The universal Program Execution front door owns deterministic input classification. Architecture classification changes the compiler envelope, never the operator source.

## Consequences

- Long microscope audits and architecture designs can be passed directly to `make campaign`.
- The brief compiler no longer silently flattens architecture-grade prose.
- Provenance distinguishes source-declared and classifier-authorized architecture admission.
- Existing campaign-source, activate, plan, and program-intent schemas retain precedence over prose classification.

## Rejected alternatives

- Injecting required architecture frontmatter into the source.
- Keeping warning-only route confusion and requiring `make campaign-architecture` for normal use.
- LLM-based input routing.
- Treating file extension as architecture authority.
