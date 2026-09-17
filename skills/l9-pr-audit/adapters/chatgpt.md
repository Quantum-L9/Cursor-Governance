<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: adapter
role: chatgpt-audit-binding
version: 1.3.0
status: active
-->

# ChatGPT Audit Adapter

Load when ChatGPT performs the audit.

## Tool binding

Prefer the connected GitHub capability for repository files, PR metadata/diffs, reviews, checks, commits, branches, rulesets, and current state. Use exact file/API evidence rather than search snippets when a material claim depends on full context.

Use web research only for genuinely external authority not owned by the repository. Use local file tools for user-supplied sources or bundle construction. Do not clone repository content into the output ZIP.

## Evidence order

1. Bind repository/default branch and freeze exact PR source heads.
2. Declare `audit_coverage`: inspection scope, exclusions/inaccessibility, applicable domains.
3. Resolve material authority sources and precedence before judging mismatch.
4. Bind required-check resolution, review-thread discovered/classified/remaining counts, and per-PR mandatory validation to canonical evidence IDs.
5. Collect directly coupled surfaces only when they can change a material conclusion.
6. For CI/test/runtime/measurement evidence, record exact tested revision separately from source head and state properties discriminated. Mark mandatory validation evidence explicitly; structural proof is valid only for the property it actually discriminates.
7. Build owner/boundary map and evidence-backed remediation surfaces. Resolve each mutation guard through an admitted `MUTATION_GUARD` authority or mark it `NOT_APPLICABLE`; never use an unbound prose label.
8. Run anti-bypass and preservation checks before clean readiness.
9. Reconcile findings/root causes and determine audit convergence separately from merge readiness.
10. Redact secret values before they enter canonical evidence, then continue scanning the surrounding text rather than treating the redaction marker as a safe-harbor for the whole string.
11. Bind every closing validation procedure to `COMMAND`, `CHECK`, or `MANUAL`, its authority ID, and confirmed `validation_procedure` evidence.

Do not read the whole repository indiscriminately. Expand only when a touched owner, contract, caller/consumer, generator, registry, test, validation gate, or enforcement path can falsify a material conclusion.

## Current-head reconciliation

Treat PR prose, prior audits, review comments, and bot suggestions as hypotheses until current source confirms them. If a head moves during the audit, invalidate affected evidence rather than carrying it forward.

## Output routing

Create canonical `audit.json` exactly to the bundled schema. Validate with `scripts/build_audit_bundle.py --validate-only`, run `scripts/self_test.py` when maintaining the skill itself, then build and return `l9-pr-audit-output.zip`.

The conversational response should stay compact: audit/readiness/convergence status, blocking finding count, residual readiness-blocking Unknowns, and the ZIP.
