<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: evidence-contract
version: 1.3.0
status: active
-->

# Evidence and Remediation Handoff Contract

## Prime directive

Make the audit directly consumable by remediation without forcing downstream rediscovery. Evidence strength must match the claim, and every readiness-relevant claim must trace to canonical evidence.

## Canonical structural owner

`schemas/audit-output.schema.json` owns the structural shape of `audit.json`. `scripts/build_audit_bundle.py` loads that schema with Draft 2020-12 validation, then applies cross-field semantic gates. Unknown fields are rejected. Do not create a second structural validator.

## Target coverage

`audit_coverage` records:

- explicit inspection scope;
- excluded or inaccessible surfaces and whether each blocks a finding, readiness, or convergence;
- applicable audit domains;
- completed domains;
- skipped domains as `NOT_APPLICABLE` or `UNKNOWN`.

`COMPLETE` is illegal when an applicable domain has no disposition, an `UNKNOWN` skipped domain remains, or an excluded surface blocks convergence. Partial inspection may still produce useful findings, but it cannot masquerade as whole-target convergence.

## Authority resolution

`authority_resolution.sources` assigns each material source an `authority_id`, kind, exact source, scope, precedence, and evidence IDs. Findings reference the authority by ID and must use the same source path.

`authority_resolution.status` is `RESOLVED`, `PARTIAL`, `CONFLICTED`, or `UNKNOWN`. A source other than current explicit user instruction requires evidence. Record conflicts instead of silently choosing when precedence cannot resolve them.

## Every remediation-relevant finding

Include:

- stable ID, class, severity, confidence, merge-blocking state, affected PRs, and audited repository baseline revision;
- exact PR source-head bindings;
- governing `authority_id`, rule, source, and enforcement refs;
- ownership axes: semantic owner, execution owner, mutation guard, remediation owner class;
- canonical evidence IDs;
- observed and expected behavior, mismatch, impact, root cause, and `root_cause_state`;
- behavioral closure condition and typed closing validation.

Finding classes: `COMPLETENESS`, `CORRECTNESS`, `ARCHITECTURE`, `INVARIANT`, `CONTRACT`, `SOURCE_OF_TRUTH`, `SECURITY`, `RELIABILITY`, `PERFORMANCE`, `TEST_QUALITY`, `CI`, `REVIEW`, `CROSS_PR`, `PRESERVATION`.

Remediation owner classes: `CODEBASE`, `CI_PIPELINE`, `ENVIRONMENT`, `HUMAN`, `VALIDATION_ONLY`, `UNKNOWN`.

Root-cause states: `CONFIRMED`, `INFERENCE`, `UNKNOWN`.

## Evidence states and types

Every material evidence entry carries `epistemic_state`: `CONFIRMED`, `INFERENCE`, or `UNKNOWN`.

Evidence types: `SOURCE`, `CONTRACT`, `INVARIANT`, `DIFF`, `TEST`, `CI`, `RUNTIME`, `MEASUREMENT`, `REVIEW_THREAD`, `GENERATED_ARTIFACT`, `CONFIGURATION`, `DEPENDENCY_GRAPH`, `CROSS_PR_INTERACTION`.

Validation result vocabulary: `PASS`, `FAIL`, `BLOCKED`, `NOT_EXECUTED`, `UNKNOWN`, `NOT_APPLICABLE`.

`properties_discriminated` names what the evidence can actually prove. A passing test/check is never global correctness evidence merely because it is green.

## Revision identity

For `TEST`, `CI`, `RUNTIME`, and `MEASUREMENT` evidence preserve separately:

- `source_head_sha`: PR source revision when applicable, else `UNKNOWN`;
- `tested_revision_sha`: exact revision actually executed, else `UNKNOWN`;
- `validation_result`.

An observed `PASS` or `FAIL` with `tested_revision_sha: UNKNOWN` is invalid. Never fill it with source head by assumption.

## Bidirectional evidence integrity

If a finding references evidence ID `E`, evidence `E.findings_using_this_evidence` must reference that finding. The reverse is also required. Evidence used only for authority, scope, review coverage, required-check resolution, anti-bypass, preservation, regression, or cross-PR proof may have no finding reference.

## Required-check and review evidence

Every PR binding carries evidence IDs for:

- `required_check_resolution` (`RESOLVED`, `NONE`, `UNKNOWN`);
- `review_thread_coverage` (`COMPLETE`, `INCOMPLETE`, `UNKNOWN`).

`RESOLVED`, `NONE`, and `COMPLETE` may support readiness only with at least one `CONFIRMED` evidence record that discriminates `required_check_identity` or `review_thread_coverage` respectively. `COMPLETE` review coverage requires integer discovered/classified/remaining counts; discovered must equal classified. READY additionally requires `unresolved_remaining == 0`.

## Secret-safe evidence

Every evidence entry carries `redaction_state`: `NOT_APPLICABLE`, `REDACTED`, or `UNKNOWN`.

Never preserve a secret value to prove exposure. Keep repository/path/line/symbol/check identifiers, a redacted excerpt when needed, and the fact proven. The packager rejects common high-confidence secret shapes.

## Remediation surface evidence

For every finding record:

- authoritative read surfaces;
- implementation surfaces;
- coupled read surfaces;
- excluded false leads when useful;
- `surface_evidence` records linking a path and role to canonical evidence IDs.

Every implementation path must have `IMPLEMENTATION` surface evidence with at least one `CONFIRMED` evidence record whose `properties_discriminated` includes `implementation_surface`. Repository write paths must be relative and may not contain `..`, absolute prefixes, or host-specific paths.

## Fable mutation gate

A finding becomes default mutation work only when all are true:

1. `remediation_owner_class == CODEBASE`;
2. `confidence == Confirmed`;
3. `root_cause_state == CONFIRMED`;
4. `mutation_guard` is `NOT_APPLICABLE` or an admitted authority ID of kind `MUTATION_GUARD`;
5. dependency order is resolvable and not `UNKNOWN`;
6. at least one implementation path has confirmed evidence that discriminates `implementation_surface`.

Anything else remains evidence-bearing but non-authorizing. `write_surfaces` is a strict allowlist. An unlisted required path yields `SCOPE_EXTENSION_REQUIRED`; Fable must stop that unit rather than expand scope itself.

## Finding dependency graph

`depends_on_findings` is the single canonical dependency direction. `blocks_findings` is derived into the handoff and must not be independently authored in `audit.json`.

Dependency cycles or downstream nodes blocked behind a cycle receive no mutation authority until the audit reconciles them. Shared-root-cause text does not waive this gate by itself.

## Regression, preservation, and anti-bypass proof

Correctness findings should record existing regression tests, missing negative boundaries, reproduction commands, pre-remediation result, expected post-remediation result, and evidence IDs when applicable.

When public API, data/persistence, externally consumed behavior, or release compatibility moves, create a preservation obligation. `PRESERVED` and `MIGRATION_AUTHORIZED` require confirmed evidence.

Each selected PR must contain exactly one anti-bypass record for each required class: test removal/disablement, skip/ignore growth, gate weakening, exclusion/suppression growth, generated/owner bypass, and unexplained dependency movement. `PASS`, `FINDING`, and `NOT_APPLICABLE` require confirmed evidence whose `properties_discriminated` contains `anti_bypass:<KIND>` for that exact class.

## Cross-PR proof

Single-PR audits use `cross_pr_evidence_pack.status: NOT_APPLICABLE` with empty relationships/order.

Multi-PR audits classify relationships and carry evidence. `COMPLETE` requires a merge order containing every bound PR exactly once. Combined ready states require `COMPLETE` cross-PR proof.

## Residual Unknowns

Every residual Unknown records ID, description, affected PRs, affected conclusion, whether it blocks readiness, whether it blocks audit convergence, minimum evidence needed to resolve it, and owner class. Readiness-blocking Unknowns prevent READY; convergence-blocking Unknowns prevent CONVERGED.

## Executive verdict

Keep three independent states:

- `audit_status`: whether the audit execution succeeded;
- `readiness_status`: whether the proposed PR state is ready;
- `convergence_status`: whether the audit itself has reconciled its applicable scope.

A NotReady PR may have a Converged audit. A high aggregate confidence or green check cannot override a merge blocker or readiness-blocking Unknown.

`minimum_safe_next_action` is exactly one immediate action chosen for highest dependency unlock or highest-risk uncertainty reduction.


## Mandatory validation and closing-procedure provenance

Each per-PR verdict carries `mandatory_validation_evidence_ids`. Evidence may be structural or executable, but it must be `CONFIRMED` and discriminate `mandatory_validation`; execution evidence must bind the exact PR source head. READY requires every mandatory execution result to be `PASS`, and each resolved required check must have matching confirmed CI PASS evidence.

Every finding and preservation closing-validation item carries `execution_kind` (`COMMAND`, `CHECK`, or `MANUAL`), `authority_id`, and confirmed evidence that discriminates `validation_procedure`. This prevents repository/PR prose from smuggling arbitrary commands into the downstream Fable contract.

## Handoff quality gate

Pass only when schema validation, semantic validation, derived handoff schema validation, and manifest verification all succeed. Fail when remediation would need to rediscover basic bug location, governing authority, ownership class, already-triaged CI failure, write surface proof, or exact closure target.
