<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: adapter
role: chatgpt-audit-binding
version: 2.0.0
status: active
-->

# ChatGPT Audit Adapter

Load when ChatGPT performs the audit.

## Tool binding

Prefer the connected GitHub capability for exact repository files, PR metadata/diffs, reviews, checks, commits, branches, rulesets, and current state. Use exact file/API evidence rather than search snippets when a material claim depends on full context.

Use web research only for genuinely external authority not owned by the repository. Use local file/container tools for user-supplied sources, deterministic census execution, or bundle construction. Do not clone repository content into the output ZIP.

## Deterministic-before-semantic law

Do not begin free-form audit judgment from a blank page.

1. Bind repository/default branch and exact PR heads.
2. Freeze exact changed-file inventory for every selected PR.
3. Collect current required-check identity, CI results, unresolved review-thread inventory, and full diff/patch evidence.
4. Recover the original PR-generation prompt/task contract when available. Record provenance; do not block solely because it is unavailable.
5. Build a normalized read-only snapshot for every selected PR and run `scripts/build_change_ledger.py`; bind the exact ledger hash/head in `deterministic_census_binding`.
6. Materialize machine-owned `changed_symbol_ledger`, `claim_validation_matrix`, `falsification_ledger`, and `audit_obligation_ledger` rows from the bound census. The model may add semantic rows, never remove or rewrite deterministic rows.
7. Attempt deterministic/static/check/command falsification first. Use LLM judgment only for probes that cannot be closed deterministically, recording rationale and evidence.
8. Only then perform semantic architecture/correctness/change-discipline adjudication.

The deterministic census is not a verdict. A detected factory, adapter, retry path, deleted test, or scope-pattern mismatch is a question the audit must close, not automatic failure.

## Evidence order

1. Declare `audit_coverage`: inspection scope, exclusions/inaccessibility, full artifact inventory, and exactly one canonical `domain_assessments` record for every audit domain. `CHANGE_DISCIPLINE` may never be `NOT_APPLICABLE`.
2. Resolve material authority sources and precedence before judging mismatch.
3. Build `intent_contract`: current user instruction, repository law, original PR prompt when available, PR body/issue as lower-authority provenance. Historical prompt intent never overrides current repository law.
4. Bind required-check resolution, review-thread discovered/classified/remaining counts, exact changed-file inventory, and per-PR mandatory validation to canonical evidence IDs.
5. Build objective closure, scope fidelity, complexity delta, architectural economy, supersession closure, failure-path coverage, test-discrimination, and required-control-adequacy records.
6. Collect directly coupled surfaces only when they can change a material conclusion.
7. For CI/test/runtime/measurement evidence, record exact tested revision separately from source head and state properties discriminated.
8. Populate canonical `architecture_policy_adapters` and `boundary_map` before grading ownership/routing/source-of-truth alignment. Build evidence-backed remediation surfaces and resolve each mutation guard through an admitted `MUTATION_GUARD` authority or mark it `NOT_APPLICABLE`.
9. Run anti-bypass and preservation checks before clean readiness.
10. Reconcile findings/root causes and determine audit convergence separately from merge readiness.
11. Redact secret values before canonical evidence, then continue scanning surrounding text.
12. Bind every closing validation procedure to `COMMAND`, `CHECK`, or `MANUAL`, its authority ID, and confirmed `validation_procedure` evidence.
13. Close every audit obligation as `PASS`, `FINDING`, `NOT_APPLICABLE`, or `UNKNOWN`. Represent remaining Unknowns explicitly.
14. Reconcile every material claim with claim-specific validation and all applicable falsification probes. A positive claim is not closed while any probe is `FALSIFIED` or `INCONCLUSIVE`.

Do not read the whole repository indiscriminately. Expand only when a touched owner, contract, caller/consumer, generator, registry, test, validation gate, superseded path, or enforcement surface can falsify a material conclusion.

## Current-head reconciliation

Treat PR prose, prior audits, review comments, bot suggestions, and historical task text as hypotheses until current source confirms them. If a head moves during the audit, invalidate affected evidence rather than carrying it forward.

## Output routing

Create canonical `audit.json` exactly to the bundled schema. Validate with `scripts/build_audit_bundle.py --audit audit.json --change-ledger <ledger.json> --validate-only` (repeat `--change-ledger` per PR), run `scripts/self_test.py` when maintaining the skill itself, then build and return the uniquely tagged ZIP emitted by the builder. Do not rename the generated ZIP.

The conversational response should stay compact: audit/readiness/convergence status, blocking finding count, change-discipline blockers, residual readiness-blocking Unknowns, and the ZIP.

## Recursive verification discipline

Do not finalize from the first semantic pass. After deterministic census and primary audit, perform a final adversarial verification pass over the exact `artifact_inventory`, retained findings, complete obligation ledger, material claim matrix, and falsification ledger. If that pass discovers new material information, add a bounded reconciliation pass and verify again. A converged audit requires final verification to discover zero new material information.

- v2.0: materialize bound deterministic closure rows and post-judgment closure; never replace machine closure seeds with prose.
