<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: harvest-provenance
version: 2.0.0
status: active
-->

# Harvested Invariants

## Contents

- Source identity
- Accepted nuggets H-01 through H-13
- Rejected or bounded donor concepts
- Recursive architecture alignment kernel harvest

Load only when maintaining, auditing, or re-harvesting `l9-pr-audit`. Runtime audits use the compiled laws in `SKILL.md`, `audit-protocol.md`, `change-discipline.md`, and `evidence-contract.md` instead of reloading donor material.

## Source identity

Donor repository: `Quantum-L9/Cursor-Governance`
Pinned donor revision: `acf3baa58c4703a875e412841a9806c04e22b6b7`
Harvest date: `2026-09-18`

The donors were inspected through the connected GitHub capability at the pinned revision. Runtime dependency on donor skills is intentionally absent.

## Accepted nuggets

### H-01 Claim/evidence fit

Transfer: every material audit claim carries epistemic state and names the property its evidence discriminates. Performance claims require measurement when executable measurement exists.

### H-02 Source head is not tested revision

Transfer: PR source identity and execution identity remain distinct. CI/test/runtime/measurement evidence records both.

### H-03 Separate semantic, execution, mutation, and verdict axes

Transfer: each finding records semantic owner, execution owner, mutation guard, and remediation owner class. Prompt prose is not mutation authority.

### H-04 Existence does not prove reachability

Transfer: file/object existence is distinct from registration, discovery, reachability, enforcement, and runtime execution.

### H-05 Negative closure and anti-bypass proof

Transfer: green outcomes do not prove safety if the PR removed tests, weakened gates, added exclusions/suppressions, bypassed generators, or introduced unexplained dependency movement.

### H-06 Current-head reconfirmation

Transfer: prior audit/review/bot claims are hypotheses until reconfirmed against the bound current head. All unresolved review threads are accounted for regardless of author.

### H-07 Cold-resumable bounded remediation handoff

Transfer: remediation starts from immutable identity, explicit scope, proof targets, dependency order, strict write surfaces, preservation obligations, and exact closure validation.

### H-08 Secret-safe evidence

Transfer: evidence may prove exposure without reproducing values. Secret values never enter audit JSON, projections, contracts, or excerpts.

### H-09 Deterministic signal census from PR remediation

Donor: `skills/l9-pr-remediation`, especially its unified signal-ingestion, plan-completeness, review-thread, board/evidence, and convergence contracts.

Transfer: audit collection should enumerate current CI failures and unresolved review threads deterministically before semantic judgment. Every discovered signal receives an explicit disposition. The mutation/convergence/merge machinery itself is not copied into audit.

Acceptance: `audit_obligation_ledger` covers in-scope CI failures and every unresolved review thread; the downstream PR Remediation Contract separately requires CI/review convergence while keeping `MERGE=False`.

### H-10 Scope/expansion detectors from PR digest

Donor: `skills/l9-pr-digest/scripts/pr_digest_core.py` and `pr_evidence.py`.

Harvested detectors include changed-file census, deleted tests, suppression/ignore growth, dependency/lockfile anomalies, generated-only movement, architecture-growth candidates (registry/factory/adapter/service/compatibility/feature-flag), and deterministic expansion questions.

Transfer: these become self-contained audit census patterns in `scripts/build_change_ledger.py` and change-discipline gates. `l9-pr-audit` does not invoke or require `l9-pr-digest` at runtime.

### H-11 Intent provenance from original task contract

Donors: PR-digest intent extraction plus current audit authority law.

Transfer: when the original PR-generation prompt/task contract is available, use it as strong historical evidence for requested objective, explicit scope/non-goals, acceptance criteria, proportionality, failure expectations, and expected validation. It does not override current repository law or newer user authority.

Acceptance: `intent_contract.original_pr_prompt` records availability, provenance, and what audit dimensions used it.

### H-12 Obligation-ledger completeness

Transfer: deterministic evidence collection is insufficient unless every enumerated fact that can affect the verdict is dispositioned. A model may add semantic obligations, but may not silently omit deterministic ones.

Acceptance: exact changed-file inventory must match scope-fidelity records and changed-surface obligations; active objectives and detected change-discipline candidates also require ledger coverage before audit convergence.

### H-13 Deterministic red-team separation

Transfer: machine code should enumerate changed semantic surfaces, canonical claim obligations, and counterexample attacks before LLM judgment. The model may adjudicate ambiguous machine candidates but may not erase them. A material positive claim requires claim-specific validation and must survive every applicable falsification probe; deterministic/static/check/command evidence is preferred over LLM judgment whenever sufficient.

Acceptance: `build_change_ledger.py` seeds changed symbols, claims, falsification probes, and `CHANGED_SYMBOL` obligations; `audit.json` preserves those rows in `changed_symbol_ledger`, `claim_validation_matrix`, and `falsification_ledger`; final verification re-observes all three; bundle verification binds the exact packaged ledger bytes.

## Rejected or bounded donor concepts

- `l9-pr-digest` remains a donor only. No runtime dependency, mandatory invocation, or external READY gate survives in this skill.
- `l9-pr-remediation` mutation lanes, fleet scheduling, merge execution, and campaign behavior are not imported. Audit remains read-only.
- Generic architecture-option ceremony is not imported. Architectural economy asks whether new machinery is justified against actual objectives and existing owners.
- CI pipeline mutation is not imported. Audit classifies evidence; the downstream remediation contract may repair codebase-owned CI failures but may not weaken or rewrite CI-owned infrastructure merely to obtain green.

## Recursive architecture alignment kernel harvest

Harvested from the operator-supplied recursive architecture alignment auditor and adapted to PR-audit ownership rather than copied mechanically:

- keep architecture-policy adapters explicit, scoped, evidence-backed, and separate from provider/tool adapters;
- represent component responsibilities and material boundaries canonically instead of relying on prose reconstruction;
- give every audit domain one explicit outcome rather than parallel completed/skipped bookkeeping;
- distinguish PR-introduced, PR-exposed, pre-existing, and unknown finding provenance with evidence;
- require release/merge-blocking status to have a governing authority and direct risk evidence rather than follow severity rhetoric;
- audit underbuilt controls as well as overbuilt machinery, with deterministic coverage for mapped security/policy/validation/source-of-truth boundaries;
- keep remediation projections actionable without forcing rediscovery of governing rules or mismatch semantics.

- v2.0 deterministic-closure invariant: enumerable public-contract, SSOT, bypass, supersession, failure-edge, config, dependency, hunk, CI, generated-provenance, architecture-economy, root-cause, severity, and validation-coverage work is machine-enumerated and cannot be satisfied by reviewer prose alone.
