<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: harvest-provenance
version: 1.3.0
status: active
-->

# Harvested Invariants

Load only when maintaining, auditing, or re-harvesting `l9-pr-audit`. Runtime audits should use the compiled laws in `SKILL.md`, `audit-protocol.md`, and `evidence-contract.md` instead of reloading donor material.

## Source identity

Donor repository: `Quantum-L9/Cursor-Governance`
Pinned donor revision: `10547a2017e488642194f749a172d320dfad7aee`
Harvest method: donor-to-beneficiary semantic transfer using the governing laws of `l9-intelligence-harvest`.

The harvesting runtime could not be executed against a local checkout in the build host because that host lacked network clone capability. The donor repository was inspected through the GitHub connector at the pinned revision. Therefore donor observations are evidence-bound, while local Harvest script execution is `NOT_EXECUTED` rather than falsely reported as `PASS`.

## Accepted nuggets

### H-01 Claim/evidence fit

Donors: `l9-intelligence-harvest`, `l9-auditing-performance`, GAR epistemic discipline.

Transfer: every material audit claim carries an epistemic state. Validation evidence records what property it discriminates. Performance claims require measurement when executable measurement exists.

Acceptance: the canonical schema requires `epistemic_state` and `properties_discriminated`; the validator rejects strong performance findings without measurement evidence.

### H-02 Source head is not tested revision

Donor: `l9-update-agent-docs` and its revision schemas/workflow binding.

Transfer: PR source identity and execution identity are distinct. CI, test, runtime, and measurement evidence records both when applicable.

Acceptance: observed `PASS`/`FAIL` validation evidence cannot omit a concrete `tested_revision_sha`; the handoff never rewrites it as the source head.

### H-03 Separate semantic, execution, mutation, and verdict axes

Donors: `l9-update-agent-docs`, `l9-pr-remediation` ownership boundary, `l9-bounded-autonomy`.

Transfer: each finding records `semantic_owner`, `execution_owner`, `mutation_guard`, and `remediation_owner_class`. Prompt prose is not authority. A valid finding does not itself grant mutation.

Acceptance: only `CODEBASE` work exposes implementation surfaces as Fable write scope; non-codebase classes are emitted as non-mutation work/handoffs.

### H-04 Existence does not prove reachability

Donor: `l9-dag-authoring` plus GAR evidence discipline.

Transfer: file/object existence is distinct from registration, discovery, reachability, enforcement, and runtime execution.

Acceptance: the audit protocol requires the stronger property to be evidenced whenever a PR claims an active registered/generated/bound behavior.

### H-05 Negative closure and anti-bypass proof

Donors: `l9-repository-renovation`, `l9-ci-ops`.

Transfer: green outcomes do not prove safety if the PR removed tests, weakened gates, added exclusions/suppressions, bypassed generators, or introduced unexplained dependency movement.

Acceptance: every PR gets explicit anti-bypass coverage in `audit.json`; unresolved anti-bypass state prevents a clean readiness claim.

### H-06 Current-head reconfirmation

Donors: `l9-repository-renovation`, `l9-pr-remediation` code-review-agent contract, `l9-pr-digest`.

Transfer: prior audit/review/bot claims are hypotheses until reconfirmed against the bound current head. All unresolved review threads must be accounted for; severity or author type is not a skip switch.

Acceptance: per-PR `review_thread_coverage` is mandatory and stale-head bundles are invalidated before remediation.

### H-07 Cold-resumable bounded Fable handoff

Donor: `l9-claude-coding-contract-compiler`.

Transfer: Fable starts from immutable identity, explicit scope, proof targets, and dependency order. A work unit that cannot fit one focused session is split, never semantically compressed.

Acceptance: the generated Fable contract includes the freshness gate, owner class, write eligibility, preservation obligations, and exact closure validation.

### H-08 Secret-safe audit evidence

Donors: `l9-auditing-security`, repository root invariants.

Transfer: evidence may prove exposure without reproducing the value. Secret values never enter audit JSON, Markdown projections, prompts, or log excerpts.

Acceptance: evidence carries `redaction_state`; the validator rejects common high-confidence secret material in packaged text fields.

## Rejected or merged donor concepts

- Generic expansion classification was not copied from `l9-pr-digest`; that skill remains the owner. `l9-pr-audit` consumes a same-head digest when useful and independently audits architecture/correctness only where material.
- Generic architecture-option ceremony was not copied from ADR tooling because GAR already provides a stronger smallest-coherent-architecture and simpler-alternative law.
- CI execution/remediation mechanics were not copied from `l9-ci-ops` or `l9-pr-remediation`; the audit consumes evidence and emits closure targets without becoming the mutation owner.
- Graph registries, command binding, and workflow machinery were not copied from `l9-dag-authoring`; only the portable evidence law `existence != reachability` was retained.
