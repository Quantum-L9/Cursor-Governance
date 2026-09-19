<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: audit-protocol
version: 2.0.0
status: active
-->

# Deep PR Audit Protocol

## Contents

- 1-3: target, authority, deterministic census
- 4-6: objective/scope, adversarial claims, alignment domains
- 7-10: proportionality, objective closure, failure paths, read-only validation
- 11-14: recursive findings, remediation surfaces, preservation, cross-PR state
- 15-17: obligation closure, readiness, recursive saturation
- 18-20: canonical output, bound-census build, deterministic closure completion

## 1. Bind target, immutable PR identity, and changed-file inventory

Resolve repository owner/name, default branch, exact audited default-branch SHA, frozen PR set, inspection scope, exclusions/inaccessible surfaces, exact base/head SHAs, and complete changed-file inventory per selected PR.

Inspection scope and correction scope are different. Inspect directly coupled surfaces only when needed to verify a boundary or material claim. Never infer compliance in uninspected areas.

## 2. Resolve authority and original intent provenance

Discover actual architecture law, scoped instructions, semantic owners, invariants, contracts, schemas, ADRs, policy, generators, mutation guards, and validation/merge enforcement.

Recover the original prompt/task contract used to create the PR when available. Treat it as strong historical evidence for requested objective, explicit scope, non-goals, acceptance criteria, failure behavior, and expected validation. It does not override current repository law or newer user authority. Record absence rather than guessing.

## 3. Run and bind the deterministic census

For every selected PR, collect the normalized read-only snapshot and run `scripts/build_change_ledger.py` before semantic grading. Bind the resulting ledger schema/generator version, exact PR head, and canonical ledger SHA-256 in `deterministic_census_binding`. The bundle builder receives the same ledger bytes through `--change-ledger`; the model may not silently replace them.

The census must enumerate changed files, changed symbols, CI failures, unresolved review threads, architectural-growth candidates, material failure-path candidates, test-discrimination obligations, machine claim seeds, and machine falsification seeds. Exact Python AST deltas are preferred when before/after source is available; heuristic or file-scope symbols remain explicitly labeled rather than promoted to exact facts.

Seed the audit obligation ledger from deterministic output, including one `CHANGED_SYMBOL` obligation per machine symbol. The model may add semantic obligations, claims, symbols, or falsification probes discovered from deeper analysis, but may not remove or rewrite machine-seeded rows.

Materialize `audit_coverage.artifact_inventory` for every changed file and every authority, implementation, validation, or directly coupled artifact actually inspected. Bind exact revision and evidence. This is the explicit inspection universe, not a decorative file list.

## 4. Build objective and scope contracts

Resolve active objectives and their provenance. Every active objective must later receive objective-closure disposition.

Every changed file must later receive exactly one scope-fidelity disposition: `REQUIRED`, `DIRECTLY_COUPLED`, `VALIDATION_REQUIRED`, `GENERATED_CONSEQUENCE`, `SCOPE_EXTENSION`, or `UNKNOWN`.

## 5. Materialize claims and adversarial falsification before positive closure

Create `changed_symbol_ledger`, `claim_validation_matrix`, and `falsification_ledger` from the bound machine seeds before free-form positive conclusions. Inspect full diff, every changed file/symbol, unresolved review thread, material check, and directly coupled surface capable of changing a verdict.

Every material positive claim must identify claim-specific evidence plus every applicable falsification probe. `SUPPORTED` means all applicable probes `SURVIVED`; any `FALSIFIED` probe refutes the claim; any `INCONCLUSIVE` probe prevents positive closure. Evidence closing a claim must discriminate `claim:<claim_id>` or an explicitly listed validation property. Evidence closing a falsification probe must discriminate `falsification:<claim_id>`. Generic "diff reviewed" evidence is insufficient.

Use `LLM_JUDGMENT` or `HYBRID` only when the machine-generated attack cannot be resolved from static, command, or check evidence. The judgment must record why deterministic closure was insufficient and cite the evidence considered. The LLM may adjudicate a machine candidate; it may not delete the candidate.

## 6. Audit alignment and change-discipline domains

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
- change discipline;
- cross-PR behavior when more than one PR is selected.

`CHANGE_DISCIPLINE` is mandatory. Load [change-discipline.md](change-discipline.md).

## 7. Audit proportionality and architectural economy

Record structural complexity delta from base to PR. Enumerate new services, managers, factories, adapters, registries, protocols/interfaces, compatibility layers, feature flags, control paths, dependencies, and config/state surfaces when observable.

Growth is not failure. Require evidence-backed justification for new architecture: an active objective or repository authority and proof the existing owner/capability was considered. Flag unjustified machinery, duplicate authority, or parallel paths rather than simply large diffs.

## 8. Audit objective closure and supersession

For each active objective classify `SATISFIED`, `UNPROVEN`, `NOT_IMPLEMENTED`, or `CONFLICTED`, with implementation and validation evidence.

When a path/owner/entrypoint/config/dependency/subsystem is replaced, search for residual live references and classify supersession `CLOSED`, `RESIDUAL`, `NOT_APPLICABLE`, or `UNKNOWN`.

## 9. Audit failure paths and test discrimination

For material changed error/retry/timeout/auth/rollback/cleanup/external-call behavior, require `TESTED`, `STRUCTURALLY_PROVEN`, `NOT_APPLICABLE`, or `UNKNOWN`.

For materially changed production behavior, classify validation as `DISCRIMINATING`, `WEAK`, `ABSENT`, `NOT_APPLICABLE`, or `UNKNOWN`. A test that merely executes or asserts existence is not automatically discriminating. Selective mutation testing is strong evidence when repository-safe and available.

## 10. Run read-only validation when useful

Prefer repository-native tests/checks that discriminate the governed behavior. Record exact command/check, source head, exact tested revision, result, and properties discriminated.

`NOT_EXECUTED` is never `PASS`. A green result cannot prove properties outside its discriminating scope.

## 11. Reconcile findings recursively

Reconfirm old reviews/audits against current heads. Remove stale or disproven findings. Split mixed failures by root cause and owner. Consolidate duplicate symptoms under root causes.

Each finding must bind exact heads, governing authority ID, direct evidence, owner axes, root-cause state, closure condition, and closing validation.

## 12. Prove remediation surfaces

Build the smallest repair surface from evidence. Every implementation path needs confirmed `IMPLEMENTATION` surface evidence. Keep authoritative/coupled surfaces read-only by default.

Do not provide mutation eligibility from a label alone. Confirmed CODEBASE finding + confirmed root cause + resolvable dependency order + confirmed implementation path is the minimum mutation gate.

## 13. Prove preservation and negative closure

When public/API/data/release behavior moves, create preservation obligations. Every selected PR must classify all anti-bypass classes exactly once.

A green PR is not clean if success comes from weaker gates, disabled tests, new ignores/suppressions, generator bypasses, or unexplained dependency movement.

## 14. Reconcile dependency and cross-PR state

`depends_on_findings` is canonical. Derive reverse blockers rather than authoring them separately. Cycles/order-blocked findings receive no mutation authority.

For multiple PRs, classify material relationships and produce evidence-backed exact merge order before combined READY.

## 15. Close the audit obligation ledger

Every obligation ends as `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN`, with evidence. At minimum cover every changed file, every machine changed symbol, active objective, architecture-growth candidate, material supersession, material failure path, test-discrimination obligation, in-scope CI failure, and unresolved review thread.

A known defect may remain as a `FINDING` while the audit itself converges. An undisposed or unrepresented `UNKNOWN` may not.

## 16. Assess readiness and convergence separately

Readiness evaluates whether the proposed PR state can merge safely. Convergence evaluates whether the audit itself has complete evidence, authority, coverage, change-discipline, and obligation reconciliation.

READY requires open non-draft state, `MERGEABLE`, zero unresolved review threads, claim-specific mandatory validation evidence, resolved change discipline, and no blocking finding/Unknown.

## 17. Prove search saturation with recursive passes

Record `audit_passes`. Run at least one `DISCOVERY` pass and one final `VERIFICATION` pass. Additional `RECONCILIATION` passes are warranted only when new evidence, findings, obligations, contradictions, or Unknowns create a concrete high-value objective.

The final verification pass must re-observe every retained finding, every audit obligation, every material claim, and every falsification probe. `CONVERGED` requires `new_information_count == 0`, no next-pass objective, no material `UNKNOWN` claim, and no unresolved applicable `INCONCLUSIVE` falsification probe. If verification discovers new material information, reconcile it and verify again rather than stopping on pass count or narrative confidence.

## 18. Emit one canonical audit and one next action

Create `audit.json` to the bundled schema. `executive_verdict` must contain audit status, readiness status, convergence status, concise summary, and exactly one minimum safe next action with expected evidence.

Validate before rendering. All downstream artifacts are deterministic projections from canonical audit truth and run control.

## 19. Build only from the bound census

Validate and build with the exact deterministic ledger used during the audit, for example `python scripts/build_audit_bundle.py --audit audit.json --change-ledger pr-123-change-ledger.json --validate-only`, repeating `--change-ledger` for multi-PR audits. Bundle verification must prove that the packaged `change-ledger.json`, canonical audit binding, manifest hash, machine symbol rows, machine claim seeds, and machine falsification seeds all agree byte-for-byte/field-for-field where owned by deterministic code.

## 20. Deterministic closure completion

After materializing the red-team ledgers, materialize every bound `closure_seed` into `deterministic_closure_ledger` and apply `references/deterministic-closure.md`. Keep machine identity immutable. Use bounded LLM judgment only for semantic dispositions the machine cannot decide. Populate `post_judgment_closure` after findings are stable, then include every closure ID in the final verification pass.
