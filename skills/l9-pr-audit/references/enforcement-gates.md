<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: enforcement-gates
version: 1.3.0
status: active
-->

# Enforcement Gates

## G1 Target and coverage lock

Pass only when repository identity, frozen PR set, inspection scope, exclusions, applicable audit domains, and exact default-branch/source-head revisions are explicit. `COMPLETE` cannot hide Unknown domains or convergence-blocking exclusions.

## G2 Authority resolution

Pass only when material governing sources have authority IDs, scope, precedence, and evidence. Pointer/index artifacts must be followed to canonical owners when resolvable. Unresolved authority conflict blocks the affected conclusion.

## G3 PR evidence bindings

Pass only when required-check resolution, review-thread discovered/classified/remaining counts, and mandatory validation evidence are explicit. `RESOLVED`, `NONE`, and `COMPLETE` require confirmed claim-specific evidence. Source head is never silently substituted for tested revision.

## G4 Evidence closure

Pass only when every retained finding has direct canonical evidence, exact locator, epistemic state, and claim/evidence fit. TEST/CI/RUNTIME/MEASUREMENT pass/fail claims require exact tested revision and properties discriminated.

## G5 Finding and authority closure

Pass only when each finding references a known authority ID, exact current PR heads, owner axes, root-cause state, behavioral closure condition, and closing validation. Confirmed claims require confirmed evidence.

## G6 Remediation surface proof

Pass only when every finding has exactly one surface record and every implementation path has confirmed `IMPLEMENTATION` surface evidence that discriminates `implementation_surface`. Unsafe or host-specific write paths fail closed.

## G7 Mutation eligibility

Pass only when generated Fable mutation authority is restricted to Confirmed CODEBASE findings with CONFIRMED root cause, a resolved mutation guard, resolvable dependency order, and claim-specifically confirmed implementation paths. All other work has empty `write_surfaces`.

## G8 Architecture and reachability

Pass only when touched ownership/boundary/source-of-truth relationships are resolved. File existence does not prove discovery, registration, routing, enforcement, or execution.

## G9 Negative closure

Pass only when each PR covers every anti-bypass class exactly once with evidence that discriminates that exact class, and no material test/gate weakening, skip/ignore growth, suppression/exclusion growth, generator/owner bypass, or unexplained dependency movement is hidden behind green status.

## G10 Preservation closure

Pass only when affected public APIs, data contracts, externally consumed behavior, and release surfaces have evidence-backed preservation/migration status.

## G11 Dependency and constellation closure

`depends_on_findings` is the sole dependency SSOT. Cycles/order-blocked findings receive no mutation authority. Multi-PR combined readiness requires complete cross-PR relationships and exact merge order.

## G12 Readiness consistency

Pass only when per-PR blocking finding IDs and blocking Unknown IDs exactly match canonical records. READY requires open non-draft state, MERGEABLE state, sufficient claim-specific mandatory validation, PASS evidence for every resolved required check, complete review coverage with zero unresolved remaining threads, no blocking finding/Unknown, no unresolved preservation/bypass condition, and complete required cross-PR evidence.

## G13 Audit convergence

Pass only when audit coverage is complete, authority is resolved, dependency order is reconciled, applicable domains are disposed, and cross-PR evidence is complete when relevant. Audit convergence is separate from code readiness.

## G14 Canonical output contracts

Pass only when `audit.json` validates against `schemas/audit-output.schema.json` plus cross-field semantic gates, and derived `remediation-handoff.json` validates against `schemas/remediation-handoff.schema.json`. Derived Markdown/prompt text never becomes authority.

## G15 Package integrity

Pass only when `MANIFEST.json` validates against its schema, binds builder version plus builder-byte and schema digests, every packaged file hash matches, the file set is exact, deterministic projections re-derive byte-identically from canonical audit truth, and secret-safe scanning passes.

## G16 Adversarial regression

Before packaging the skill itself, `scripts/self_test.py` must prove at minimum: unknown-field rejection, evidence-backed readiness inputs, surface-evidence enforcement, unconfirmed finding mutation denial, dependency-cycle mutation denial, strict Fable scope-extension behavior, secret rejection, schema-bound manifest integrity, and a positive end-to-end bundle build.
