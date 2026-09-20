<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: adapter
role: claude-code-fable-handoff
version: 2.0.0
status: active
-->

# Claude Code / Fable PR Remediation Adapter

Load when the validated audit bundle is intended for Claude Code Fable or another authorized remediation executor.

## Boundary

Treat the remediation executor as cold-started with only capabilities actually available in its session. Core audit truth remains provider-neutral. The audit phase is read-only and defaults to `autoremediate=0`; bundle creation does not silently launch mutation.

When the operator explicitly invokes remediation, `PR_REMEDIATION_CONTRACT.md` is the execution contract, subordinate to the latest explicit user instruction and repository-local authority. `change-ledger.json` and the handoff's `adversarial_assurance` are audit provenance only: remediation must not rerun, reinterpret, delete, or override the audit's machine symbol/claim/falsification closure as a way to widen mutation scope.

## Primary mission and mandatory addenda

The remediation contract has one primary mission:

- resolve every freshness-valid, mutation-eligible audit finding at its root cause.

That mission is not replaced by CI babysitting or review cleanup. Two additional convergence obligations are mandatory by default for every affected PR:

- resolve current codebase-owned CI failures, then re-run/poll required checks on the repaired head;
- inspect every unresolved current code-review thread regardless of author, validate it against current code, fix confirmed code defects, reply with the disposition, resolve the thread when appropriate, and re-query after publication.

`MERGE=False`. The executor converges affected PRs to audit-closed, CI-resolved, review-resolved, merge-ready state and stops before merge.

External `CI_PIPELINE`, `ENVIRONMENT`, or `HUMAN` blockers are reported precisely; they do not authorize editing unrelated infrastructure, weakening gates, or expanding source scope.

## Mutation eligibility

Use the deterministic handoff field `mutation_eligible`. The builder may set it true only when the finding is Confirmed, the root cause is CONFIRMED, owner class is CODEBASE, origin is not `PRE_EXISTING` or `UNKNOWN`, the mutation guard is `NOT_APPLICABLE` or resolves to an admitted `MUTATION_GUARD` authority, dependency order is resolvable, and confirmed evidence specifically discriminates at least one `implementation_surface`.

Each work unit carries its finding origin, origin evidence, governing authority, observed/expected behavior, mismatch proof, impact, blocking basis, root cause, closure condition, exact surfaces, and validation contract. The handoff also carries an adversarial-assurance summary proving that audit-side machine claims/falsification gates were closed. Use those derived fields directly; open `audit.json` only for cited evidence detail, not to rediscover or re-adjudicate the finding semantics.

Other work remains non-authorizing:

- `VALIDATION_ONLY`: collect proof only.
- `CI_PIPELINE`: report the external blocker; do not rewrite source merely to compensate.
- `ENVIRONMENT`: diagnose environment; do not rewrite source merely to compensate.
- `HUMAN`: preserve the named decision gap.
- `UNKNOWN`: no mutation.
- `PRE_EXISTING` origin: report the finding and any proven merge relevance, but do not mutate it without separately authorized scope.

## Strict write scope

`write_surfaces` is a strict file allowlist. Authoritative, coupled, enforcement, validation, and non-authorizing candidate surfaces are read-only unless the same path is explicitly present in `write_surfaces`.

If an unlisted file is required, stop that unit as `SCOPE_EXTENSION_REQUIRED`. Return the path, direct-coupling evidence, mutation guard, and why closure cannot be achieved within the current allowlist. Do not self-authorize expansion.

## Publication contract

After required work-unit validation succeeds, publish the validated commit to the existing affected PR branch through the canonical SSOT Makefile `make pr` surface.

Hard rules:

1. The SSOT Makefile is the publication authority. The target repository Makefile is not.
2. Resolve the canonical SSOT Makefile location and its existing `make pr` invocation contract from current operator/session/governance authority.
3. Invoke `make pr` from that SSOT Makefile surface, passing repository/branch context only through the interface the SSOT already defines.
4. Do not fall back to the target repository Makefile, raw `gh pr`, a new replacement PR, or a parallel branch merely because the SSOT path is unavailable.
5. If the SSOT publication surface or invocation contract cannot be proven, return `PUBLICATION_BLOCKED` for the affected PR.
6. Preserve PR identity. Do not force-push unless current repository governance explicitly requires and authorizes it.
7. `merge_authorized=false`. Never merge under this contract.

## Contract requirements

The generated `PR_REMEDIATION_CONTRACT.md` must encode:

- `autoremediate` run control;
- target repository identity and pack-bounded PR scope;
- pack authority and read order;
- authority order;
- exact mutation scope law;
- freshness gate for current open PR heads;
- work-unit selection and dependency order;
- minimal complete repair constraints;
- provenance-bound validation;
- scope-extension and stale-audit handling;
- mandatory current-CI convergence;
- mandatory all-author review-thread convergence;
- SSOT Makefile `make pr` publication law;
- `MERGE=False`;
- convergence sequence and terminal rule;
- final remediation deliverables and statuses.

## Return contract

Per attempted work unit return the finding ID, owner class, independently observed starting source head, mutation eligibility and allowlist used, files changed, root-cause action, preservation obligations, validation evidence and tested revision, closure status, residual blockers/Unknowns, `SCOPE_EXTENSION_REQUIRED` evidence when applicable, and resulting commit/head when applicable.

Per affected PR also return initial source head, final source head, publication result, final CI failure disposition, required post-publication check results, final unresolved review-thread count, and explicit `merge_attempted=false`.

Never claim closure when required validation did not run, ran on an unidentified revision, failed to discriminate the closure property, required CI remains codebase-red, review threads remain silently unresolved, or merge was attempted.

- v2.0 handoff remains finding-driven; deterministic closure is audit evidence and does not expand remediation write authority.
