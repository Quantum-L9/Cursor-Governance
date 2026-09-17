<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: audit-protocol
version: 1.3.0
status: active
-->

# Deep PR Audit Protocol

## 1. Bind target, scope, and coverage

Resolve repository owner/name, default branch, exact audited default-branch SHA, frozen PR set, inspection scope, exclusions/inaccessible surfaces, and applicable audit domains.

Inspection scope and correction scope are different. Inspect directly coupled surfaces only when needed to verify a boundary or material claim. Do not infer compliance in uninspected areas.

## 2. Resolve authority before grading

Discover actual architecture law, scoped instructions, semantic owners, invariants, contracts, schemas, ADRs, policy, generators, mutation guards, and validation/merge enforcement. Do not assume filenames.

Record each material authority source with stable ID, kind, scope, precedence, and evidence. Follow pointers to their semantic owner. Record unresolved conflicts rather than choosing silently.

## 3. Bind immutable PR source identity

For every selected PR record number, URL, state, draft flag, base branch/SHA, head branch, exact source `head_sha`, mergeability, required-check resolution, review-thread discovered/classified/remaining counts, and canonical mandatory-validation evidence IDs.

Required-check and complete-review claims require confirmed evidence IDs. Source head is not automatically the revision executed by CI. A moved PR head invalidates old head-bound evidence.

## 4. Reconstruct intent and boundaries

Resolve claimed behavior, governing requirement, pre-PR behavior, intended post-PR behavior, producers/consumers, orchestration, routing, state, source-of-truth, generated relationships, security boundaries, observability, and validation ownership where material.

Treat current implementation and tests as evidence, not automatic intended behavior.

## 5. Collect evidence by falsification value

Inspect full diff, every changed file, unresolved review threads, material checks, and directly coupled surfaces. Prioritize evidence capable of changing a verdict. Do not pre-filter review signals by author or tone.

For every material claim ask what exact evidence would disprove it. Record the property each evidence item discriminates.

## 6. Audit alignment domains

Assess applicable domains:

- intent/scope;
- communication/contracts;
- routing/integration;
- ownership/authority;
- structure/source-of-truth;
- schema/configuration;
- security;
- reliability/observability;
- testing/validation;
- leverage/simplicity;
- cross-PR behavior when more than one PR is selected.

Skip inapplicable domains explicitly. Unknown applicability cannot be silently treated as pass.

## 7. Run read-only validation when useful

Prefer repository-native tests/checks that discriminate the governed behavior. Record exact command/check, source head, exact tested revision, result, and properties discriminated.

`NOT_EXECUTED` is never `PASS`. A green result cannot prove properties outside its discriminating scope.

## 8. Reconcile findings recursively

Reconfirm old reviews/audits against current heads. Remove stale or disproven findings. Split mixed failures by root cause and owner. Consolidate duplicate symptoms under root causes.

Each finding must bind exact heads, governing authority ID, direct evidence, owner axes, root-cause state, closure condition, and closing validation.

## 9. Prove remediation surfaces

Build the smallest repair surface from evidence. Every implementation path needs confirmed `IMPLEMENTATION` surface evidence. Keep authoritative/coupled surfaces read-only by default.

Do not provide mutation eligibility from a label alone. Confirmed CODEBASE finding + confirmed root cause + resolvable dependency order + confirmed implementation path is the minimum mutation gate.

## 10. Prove preservation and negative closure

When public/API/data/release behavior moves, create preservation obligations. Every selected PR must classify all anti-bypass classes exactly once.

A green PR is not clean if success comes from weaker gates, disabled tests, new ignores/suppressions, generator bypasses, or unexplained dependency movement. Each anti-bypass verdict must cite confirmed evidence that discriminates that exact anti-bypass class, not one generic "diff reviewed" assertion.

## 11. Reconcile dependency and cross-PR state

`depends_on_findings` is canonical. Derive reverse blockers rather than authoring them separately. Cycles/order-blocked findings receive no mutation authority.

For multiple PRs, classify material relationships and produce evidence-backed exact merge order before combined READY.

## 12. Assess readiness and convergence separately

Readiness evaluates whether the proposed PR state can merge safely. Convergence evaluates whether the audit itself has complete evidence, authority, coverage, and reconciliation. READY additionally requires open non-draft state, `MERGEABLE`, zero unresolved review threads, and claim-specific mandatory validation evidence; required checks must each have confirmed PASS evidence on the bound source head.

A NotReady PR may have a Converged audit. READY cannot coexist with merge blockers, readiness-blocking Unknowns, unresolved check identity, incomplete review coverage, insufficient validation, unresolved preservation/anti-bypass state, or incomplete required cross-PR evidence.

## 13. Emit one canonical audit and one next action

Create `audit.json` to the bundled schema. `executive_verdict` must contain audit status, readiness status, convergence status, concise summary, and exactly one minimum safe next action with expected evidence.

Validate before rendering. All human/Fable artifacts are projections from the canonical audit and are re-derived during ZIP verification. A manually edited projection cannot be made authoritative by updating hashes.
