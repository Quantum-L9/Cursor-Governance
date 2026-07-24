# L9 Assurance Integration Roadmap Specification

**Role:** Elite architect
**Target repository:** `Quantum-L9/l9-assurance`
**Target ecosystem:** Quantum-L9 CI Constellation
**Document type:** Architecture, implementation, and migration roadmap specification
**Specification version:** `1.0.0-draft`
**Audience:** Principal engineers, repository owners, CI platform engineers, security engineers, governance owners, SDK maintainers, repair-platform maintainers, and assurance reviewers
**Normative language:** MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, SHALL, and SHALL NOT are normative requirements.

This roadmap evolves the current repository into the constellation's trust, control-evaluation, and attestation plane. It assumes `l9-ci-core` remains the thin GitHub Actions control plane, `l9-ci-sdk` remains the canonical execution and finding producer, and `PR_Repair` remains the governed mutation engine.

---

## 1. Executive summary

`l9-assurance` SHALL become the trust and decision plane of the Quantum-L9 CI constellation.

Its responsibility SHALL be to convert revision-bound, producer-attributed, policy-admissible evidence into deterministic, auditable, and optionally signed assurance decisions.

It SHALL NOT serve as:

- a general-purpose CI runner;
- a scanner host;
- a test harness;
- a GitHub Actions control plane;
- a repository mutation engine;
- a debt-mining platform;
- an editor language server;
- a repair agent;
- a generic workflow orchestrator.

The constellation SHALL follow this responsibility model:

```text
l9-ci-core
    orchestrates hosted CI and publishes outcomes
l9-ci-sdk
    executes checks and emits canonical observations
l9-ci-debt-resolver
    interprets CI failures and derives repair-oriented diagnoses
PR_Repair
    performs approved, bounded, isolated, and verifiable mutations
l9-ci-debt-intelligence
    mines historical failure patterns and compiles prevention assets
l9-ci-debt-lsp
    delivers approved prevention rules into developer editors
l9-assurance
    validates evidence, evaluates controls, resolves policy,
    records unknowns, and issues assurance decisions
```

The central architectural invariant SHALL be:

```text
Execution systems observe.
Repair systems mutate.
Intelligence systems learn.
Control-plane systems orchestrate and publish.
Assurance verifies and decides.
```

---

## 2. Problem statement

The current assurance repository spans testing, evidence, governance, trust, audit, CI policy, red-team capabilities, and release gates. That breadth creates overlapping responsibility with the CI SDK, CI core, repair, resolver, intelligence, and language-server repositories.

This overlap introduces:

1. duplicate execution engines;
2. duplicated policy interpretation;
3. incompatible result and evidence schemas;
4. unclear ownership of canonical findings;
5. circular repository dependencies;
6. inconsistent release decisions;
7. assurance logic coupled to individual scanners;
8. repair behavior embedded inside the trust layer;
9. weak distinction between logs, observations, evidence, and attestations;
10. excessive package and versioning surface;
11. difficulty proving that a decision applies to an exact commit;
12. difficulty adding non-TypeScript evidence producers;
13. inability to independently verify a decision;
14. confidence scores masking missing or invalid evidence;
15. unbounded growth of assurance into a general DevOps monolith.

The redesign SHALL establish a narrow and stable assurance boundary.

---

## 3. Mission

For an exact subject revision, under an exact assurance profile and policy version, `l9-assurance` SHALL determine which claims are supported by admissible evidence, which controls passed or failed, which facts remain unknown, which exceptions apply, and what decision may defensibly be issued.

The result SHALL be deterministic, revision-bound, evidence-backed, machine-readable, human-inspectable, policy-versioned, replay-verifiable, provenance-aware, immutable after issuance, and suitable for CI publication, release gating, repair routing, and audit.

---

## 4. Goals

### 4.1 Primary goals

`l9-assurance` MUST:

1. define the canonical assurance protocol for the constellation;
2. define portable schemas for observations, evidence, controls, profiles, decisions, waivers, unknowns, and attestations;
3. validate evidence independently of producer implementation;
4. bind all mandatory evidence to an exact subject revision;
5. evaluate declarative controls without invoking scanners directly;
6. support hard gates, advisory controls, exceptions, and indeterminate states;
7. distinguish failed evidence from absent, stale, malformed, or unauthorized evidence;
8. issue immutable assurance decisions;
9. support cryptographic verification without requiring cryptography in every local-development mode;
10. enable `l9-ci-core` to publish a decision without reconstructing it;
11. expose conformance tests for every evidence producer and decision consumer;
12. support local-first and hosted CI execution;
13. support TypeScript, Python, and future producer languages;
14. preserve auditable lineage from subject to observation to evidence to control result to decision;
15. support repair and intelligence feedback loops without owning their execution.

### 4.2 Secondary goals

`l9-assurance` SHOULD support multiple independent producers, incremental evaluation, policy simulation, evidence redaction, audit derivation, replay-safe ingestion, offline verification, multiple assurance profiles, repository extensions, organization overlays, future transparency logs, historical comparison, and selective disclosure.

---

## 5. Non-goals

`l9-assurance` MUST NOT execute repository tests as its core responsibility, scan source files directly, enumerate repository files for quality checks, interpret GitHub webhook payloads, write GitHub check runs directly from the evaluator, mutate repository contents, generate patches, approve mutations, run an editor language server, mine debt corpora, generate prevention rules, schedule arbitrary distributed jobs, replace the CI SDK, replace the CI control plane, replace `PR_Repair`, become a generic orchestration framework, issue pass when mandatory evidence is invalid or absent, or allow an aggregate score to override hard-gate failures.

---

## 6. Constellation context and repository responsibilities

### 6.1 `l9-ci-core`

SHALL own reusable GitHub Actions workflows, workflow inputs, permissions and secret boundaries, job topology, matrix coordination, artifact routing, immutable SDK provisioning, workflow summaries, GitHub check publication, cancellation and concurrency behavior, invocation of assurance evaluation, and transport of assurance decisions.

It SHALL NOT reconstruct SDK findings, reinterpret assurance controls, calculate assurance verdicts, generate repair patches, or maintain canonical evidence schemas.

### 6.2 `l9-ci-sdk`

SHALL own scanner execution, local-first pipeline execution, repository inspection, file enumeration, test and stage invocation, deterministic runtime setup, finding normalization, stage result aggregation, artifact creation, canonical observation emission, tool configuration validation, and local/hosted parity.

It SHALL NOT issue organization-level assurance decisions, sign release attestations, reinterpret assurance profiles, manage waivers, or mutate repositories during ordinary check execution.

### 6.3 `l9-ci-debt-resolver`

SHALL own CI log interpretation, root-cause classification, defect taxonomy, repair evidence extraction, bounded repair recommendations, resolver remediation metadata, repair routing to `PR_Repair`, and resolution outcome observations.

It SHALL NOT issue assurance verdicts, bypass mutation governance, or modify assurance decisions in place.

### 6.4 `PR_Repair`

SHALL own signal intake, normalization, deduplication, clustering, repair candidate generation, repair planning, approvals, protected-path policy, workspace isolation, exact-match patch application, mutation ceilings, verification, rollback, operational artifacts, and repair-loop state.

It SHALL emit observations assurance may admit as evidence. It SHALL NOT mark its own repair globally assured, reuse a pre-repair assurance decision, or bypass fresh CI evaluation after revision changes.

### 6.5 `l9-ci-debt-intelligence`

SHALL own findings corpus ingestion, normalization, recurrence and co-occurrence analysis, defect clustering, leverage scoring, rule and invariant candidate generation, scaffold and checklist generation, prevention-pack compilation, and publication candidate artifacts.

It SHALL NOT mutate repositories, issue final publication assurance, or serve editor diagnostics directly.

### 6.6 `l9-ci-debt-lsp`

SHALL own language-server behavior, document synchronization, diagnostics, ranges, code actions, rule-pack loading, topology detection, editor presentation, and approved-pack version reporting.

It SHALL NOT generate authoritative rule packs, issue release assurance, or treat editor diagnostics as hosted CI observations.

### 6.7 `l9-assurance`

SHALL exclusively own assurance schemas, claims, controls, profiles, admissibility, producer authorization, subject validation, freshness, lineage, waivers, unknowns, policy evaluation, verdict calculation, decision issuance, attestation, audit bundles, and conformance suites.

---

## 7. Architectural principles

1. **Evidence before conclusions:** no verdict without an evidence manifest.
2. **Exact subject binding:** every mandatory observation identifies the exact subject revision.
3. **Immutable decisions:** later evaluation issues a new decision and MAY reference `supersedes`.
4. **Pure evaluation:** `evaluate(subject, profile, policy, evidence) -> decision` without network, scanners, writes, hidden wall-clock access, or nondeterministic iteration.
5. **Protocol over coupling:** repositories exchange versioned artifacts rather than internal modules.
6. **Producer accountability:** accepted observations identify producer, version, execution, check, configuration digest, subject, interval, and status.
7. **Explicit unknowns:** missing knowledge is never silently converted to pass or fail.
8. **Hard gates dominate scores:** failed mandatory controls prevent pass.
9. **Revision changes invalidate evidence:** new commits require fresh revision-bound evidence.
10. **Admission and evaluation are separate stages.**

---

## 8. Target repository structure

```text
l9-assurance/
├── README.md
├── ARCHITECTURE.md
├── SPECIFICATION.md
├── ROADMAP.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── package.json
├── pyproject.toml
├── schemas/
│   ├── v1/
│   │   ├── subject.schema.json
│   │   ├── producer.schema.json
│   │   ├── finding.schema.json
│   │   ├── observation.schema.json
│   │   ├── evidence-envelope.schema.json
│   │   ├── evidence-admission.schema.json
│   │   ├── claim.schema.json
│   │   ├── control.schema.json
│   │   ├── control-result.schema.json
│   │   ├── profile.schema.json
│   │   ├── policy.schema.json
│   │   ├── waiver.schema.json
│   │   ├── unknown.schema.json
│   │   ├── decision.schema.json
│   │   ├── attestation.schema.json
│   │   └── audit-bundle.schema.json
│   └── registry.json
├── packages/
│   ├── contracts/
│   ├── evidence/
│   ├── controls/
│   ├── policy/
│   ├── evaluator/
│   ├── attestations/
│   ├── audit/
│   ├── conformance/
│   ├── cli/
│   └── testing/
├── bindings/
│   ├── typescript/
│   └── python/
├── profiles/
├── controls/
├── registry/
├── fixtures/
├── tests/
└── docs/
```

---

## 9. Package specification

- `@l9/assurance-contracts`: protocol types and generated bindings only; no I/O, policy, cryptography, scanner, or workflow logic.
- `@l9/assurance-evidence`: schema validation, canonicalization, digesting, producer/check authorization, subject validation, freshness, duplicate/replay hooks, lineage, signatures, redaction derivation, admission results.
- `@l9/assurance-controls`: declarative control loading, version resolution, claim mapping, evidence matching, severity, applicability, dependencies, supersession, profile composition. MUST NOT execute commands.
- `@l9/assurance-policy`: overlays, classifications, waiver rules, expiry, unknown handling, hard gates, conflicts, policy digests.
- `@l9/assurance-evaluator`: deterministic decision evaluation from subject, profile, policy, evidence, explicit time, and optional prior decision.
- `@l9/assurance-attestations`: signing and verification abstractions. Production signers are adapters; test signers remain isolated.
- `@l9/assurance-audit`: complete and redacted audit bundles with preserved lineage.
- `@l9/assurance-conformance`: producer and consumer suites.
- `@l9/assurance-cli`: protocol and evaluator operations without CI-provider-specific logic.
- `@l9/assurance-testing`: deterministic fixtures, fake clocks, in-memory registries, and fake signers, marked testing-only.

---

## 10. Canonical domain model

The canonical domain SHALL include:

- `SubjectReference`
- `ProducerIdentity`
- `Observation`
- `Finding`
- `EvidenceEnvelope`
- `EvidenceAdmissionResult`
- `ClaimDefinition`
- `ControlDefinition`
- `AssuranceProfile`
- `Waiver`
- `Unknown`
- `ControlResult`
- `AssuranceDecision`

Core rules:

1. subjects are immutable or content-addressed;
2. branch names are insufficient subject identities;
3. tags resolve to immutable revisions or digests;
4. all mandatory evidence binds to the same exact subject;
5. waivers never convert failed controls into ordinary pass;
6. decisions include profile and policy identity plus digest;
7. decision lineage is explicit through `supersedes` rather than mutation.

---

## 11. Verdict semantics

### Pass

Only when every applicable mandatory control passes, every mandatory evidence requirement is satisfied with admissible evidence, no decision-impacting unknown remains, no conditional waiver semantics apply, subject binding is exact, and policy permits pass.

### Fail

When valid evidence demonstrates failure of at least one mandatory control, or a policy-defined hard prohibition is triggered. Fail requires positive evidence of failure.

### Indeterminate

When a mandatory result cannot be established because evidence is absent, malformed, stale, unauthorized, unverifiable, inconsistent, bound to another subject, signature verification fails, policy cannot resolve, or evaluation cannot complete. Indeterminate MUST NOT collapse into fail.

### Conditional

When policy permits progress under an approved waiver, explicit limitation, accepted risk, or bounded exception.

---

## 12. Evidence admission pipeline

The admission pipeline SHALL execute in this order:

1. artifact discovery;
2. media-type validation;
3. maximum-size validation;
4. schema-version dispatch;
5. structural schema validation;
6. canonicalization;
7. payload digest verification;
8. producer lookup;
9. producer-version authorization;
10. check authorization;
11. subject normalization;
12. subject-revision comparison;
13. execution-time validation;
14. freshness validation;
15. signature verification when required;
16. lineage verification;
17. replay and duplicate checks;
18. policy admissibility;
19. acceptance, rejection, quarantine, or deduplication.

Stable rejection codes SHALL include:

```text
EVIDENCE_SCHEMA_UNSUPPORTED
EVIDENCE_SCHEMA_INVALID
EVIDENCE_PAYLOAD_DIGEST_MISMATCH
EVIDENCE_PRODUCER_UNKNOWN
EVIDENCE_PRODUCER_VERSION_REVOKED
EVIDENCE_CHECK_UNAUTHORIZED
EVIDENCE_SUBJECT_MISMATCH
EVIDENCE_REVISION_MISMATCH
EVIDENCE_STALE
EVIDENCE_SIGNATURE_REQUIRED
EVIDENCE_SIGNATURE_INVALID
EVIDENCE_LINEAGE_INVALID
EVIDENCE_REPLAY_DETECTED
EVIDENCE_TOO_LARGE
EVIDENCE_POLICY_INADMISSIBLE
```

Quarantined evidence MUST NOT satisfy mandatory controls.

---

## 13. Producer registry

The repository SHALL maintain a reviewed producer registry defining producer ID, repository, accepted versions, subject kinds, authorized checks, minimum check versions, signing requirements, and revocation state.

Initial producers SHOULD include:

- `l9-ci-sdk` for Git revision observations;
- `pr-repair` for repair plan, approval, protected-path, execution, verification, and rollback observations;
- `l9-ci-debt-intelligence` for rule-pack schema, provenance, precision, coverage, and leverage observations.

Registry changes are trust-boundary changes and MUST receive architecture and security review.

---

## 14. Check registry

Each check SHALL have a stable ID, version, owning producer, output schema, semantic description, determinism declaration, and revision-binding requirement.

Check IDs remain stable across implementation refactors. Behaviorally incompatible changes require a new major version.

---

## 15. Control definitions

Controls SHOULD be declarative and specify:

- stable ID and version;
- claim;
- title and description;
- mandatory or advisory severity;
- applicability;
- evidence requirements;
- dependencies;
- declarative or registered evaluation;
- freshness;
- waiver policy.

Controls MUST NOT invoke commands.

---

## 16. Assurance profiles

The repository SHOULD define:

- `l9.pull-request`
- `l9.protected-branch`
- `l9.release-candidate`
- `l9.repair-mutation`
- `l9.prevention-pack-publication`
- `l9.repository-bootstrap`

Each profile SHALL be versioned and bind a subject kind, control set, default policy, output claims, and compatibility requirements.

---

## 17. CI integration protocol

Canonical flow:

```text
pull-request event
    ↓
l9-ci-core resolves workflow and governance inputs
    ↓
l9-ci-core provisions pinned l9-ci-sdk
    ↓
l9-ci-sdk executes stages and emits observations
    ↓
l9-ci-core transports observations unchanged
    ↓
l9-assurance admits evidence
    ↓
l9-assurance evaluates the selected profile
    ↓
l9-assurance emits an immutable decision
    ↓
l9-ci-core publishes the authoritative GitHub check
```

Artifact layout SHOULD include `observations/`, `supporting/`, and `assurance/` with admission report, decision, summary, evidence manifest, and optional attestation.

Stable exit codes:

```text
0  pass
10 conditional
20 fail
30 indeterminate
40 input or schema error
41 policy resolution error
42 evidence admission system error
43 signature verification system error
50 internal invariant violation
```

---

## 18. Repair-loop integration

A failed decision MAY include remediation routing metadata, but assurance SHALL NOT generate patches.

Required flow:

```text
decision A for commit A = fail
    ↓
resolver emits diagnosis
    ↓
PR_Repair creates and governs a bounded repair
    ↓
commit B is created
    ↓
fresh SDK execution for commit B
    ↓
fresh assurance decision B
```

Mandatory invariant:

```text
decision.subject.revision
  == every mandatory evidence revision
  == current evaluated commit
```

Evidence from commit A MUST NOT satisfy revision-bound controls for commit B.

---

## 19. Debt-intelligence integration

Debt intelligence MAY consume normalized findings, failed controls, diagnoses, repair outcomes, recurrence fingerprints, false-positive annotations, and waiver patterns.

Candidate prevention packs SHALL be evaluated under the prevention-pack publication profile. SDK and LSP SHOULD consume only approved, digest-matching, compatible, non-revoked packs.

---

## 20. Language-server integration

The LSP SHALL report loaded pack ID, version, digest, assurance decision ID, and compatibility result.

Editor findings are normally advisory and MUST NOT satisfy hosted CI controls unless re-emitted by an authorized producer under an approved check identity.

---

## 21. Security model

The threat model SHALL include forged or tampered observations, revision substitution, replay, stale evidence, unauthorized or compromised producers, malicious extensions, archive traversal, decompression bombs, signature confusion, downgrade, hash ambiguity, canonicalization mismatch, waiver forgery, policy rollback, profile substitution, selective omission, misleading redaction, test signer use, overwrite, parser exhaustion, and malicious rendered content.

The implementation MUST use collision-resistant digests, explicit algorithms, canonical signed payloads, downgrade resistance, separate test and production identities, and signature binding to schema, subject, profile, policy, and decision digest.

Test signers MUST remain in testing-only packages and be rejected by production trust policy.

---

## 22. Redaction and audit

Redacted evidence SHALL be a derivative, not a replacement. A derivation manifest SHALL bind source evidence, transformation, removed and replaced fields, source and derivative digests, operator, and time.

A complete audit bundle SHOULD contain decision, attestation, profile, policy, controls, evidence, admission records, waivers, unknowns, manifest, and verification instructions.

Selective-disclosure bundles MUST declare omissions, redactions, verification impact, and whether the bundle is complete, partial, or review-limited.

---

## 23. Determinism requirements

Equivalent normalized inputs MUST produce byte-equivalent canonical decision payloads, excluding explicitly injected issuance fields.

Requirements include explicit evaluation time, sorted references and results, stable reason ordering, canonical JSON, no hidden random IDs, no locale dependence, no filesystem-order dependence, deterministic map handling, and explicit policy precedence.

Replay tests MUST detect any mismatch.

---

## 24. Performance requirements

Initial objectives:

| Operation | Target |
|---|---:|
| Validate one observation under 1 MB | p95 under 100 ms |
| Admit 1,000 observations | p95 under 5 seconds |
| Evaluate 500 controls | p95 under 2 seconds |
| Verify one signed decision | p95 under 250 ms excluding remote lookup |
| Generate decision summary | p95 under 500 ms |
| Memory for 1,000 normal observations | under 512 MB |
| Deterministic replay mismatch rate | 0 |

The architecture SHOULD support streaming admission and avoid loading binary support artifacts unless controls require their content.

---

## 25. Reliability and failure handling

Infrastructure failures generally produce `indeterminate`; positive violation evidence produces `fail`.

The evaluator SHALL preserve partial results, mark dependent controls indeterminate, never synthesize evidence, support offline operation, and treat repeated identical evidence idempotently as duplicate rather than additional accepted evidence.

---

## 26. Observability

Operational telemetry SHALL remain distinct from assurance evidence.

Metrics SHOULD include evaluation totals and latency, decision counts by verdict, evidence admission counts by status and reason, controls by status, signature verification, unknowns, waivers, and replay detections.

Logs SHOULD include correlation ID, run ID, decision ID, subject digest, profile, policy, and reason codes. Logs MUST NOT leak secrets or unrestricted evidence payloads.

---

## 27. CLI specification

Target commands:

```text
l9-assurance plan
l9-assurance evidence admit
l9-assurance evaluate
l9-assurance verify
l9-assurance bundle
l9-assurance conformance
l9-assurance simulate
```

Simulation output MUST be marked non-authoritative.

---

## 28. Programmatic API

```ts
interface AssuranceEngine {
  plan(request: PlanRequest): Promise<AssurancePlan>;
  admit(request: AdmissionRequest): Promise<AdmissionReport>;
  evaluate(request: EvaluationRequest): Promise<AssuranceDecision>;
  verify(request: VerificationRequest): Promise<VerificationReport>;
  bundle(request: BundleRequest): Promise<AuditBundle>;
}
```

The engine SHOULD support dependency injection for clock, registries, signer, verifier, stores, and telemetry.

---

## 29. Compatibility and versioning

Schemas SHALL use semantic versioning. Controls and profiles MUST change versions when evidence, severity, applicability, waiver, control membership, or policy meaning changes.

Producer compatibility MUST be registry-driven. Security-sensitive top-level protocol objects SHOULD reject unknown fields by default.

---

## 30. Conformance testing

Producer suites MUST cover valid and invalid observations, missing or mismatched subjects, unsupported versions, invalid statuses and counts, malformed locations, digest mismatch, duplicates, stale timestamps, unauthorized checks, oversized payloads, and invalid extension namespaces.

Consumer suites MUST prove byte-preserving decision transport, accurate verdict publication, mandatory-failure and indeterminate display, no reinterpretation, digest preservation, and safe handling of unsupported schemas.

Repair suites MUST prove revision-bound observations and fresh evaluation. Intelligence suites MUST include pack digest, corpus provenance, metrics, sample identity, compatibility, and generator version.

---

## 31. Testing strategy

Required layers:

- unit;
- contract;
- integration;
- replay;
- adversarial;
- property-based;
- performance.

Critical properties include order independence, duplicate non-amplification, advisory irrelevance to mandatory status, revision invalidation, waiver expiry, failed mandatory precedence, and missing-evidence semantics.

---

## 32. Package-disposition migration

Every current assurance package SHALL be classified using:

```yaml
package: "@l9/example"
current_responsibility: "..."
target_disposition: KEEP | MOVE | MERGE | DEPRECATE | ARCHIVE
target_repository: "..."
replacement_package: "..."
migration_owner: "..."
compatibility_window: "..."
removal_version: "..."
```

Disposition rules:

- execution and scanning move to `l9-ci-sdk`;
- GitHub workflow behavior moves to `l9-ci-core`;
- mutation capabilities move to `PR_Repair`;
- corpus analysis and prevention generation move to debt intelligence;
- contracts, evidence, controls, policy, evaluator, attestations, audit, and conformance remain.

The next required architecture artifact is a package-by-package disposition matrix for the existing 52 assurance workspaces.

---

## 33. Migration phases

### Phase 0: Freeze expansion

Freeze package growth and new execution capabilities. Inventory packages, dependency graph, public exports, consumers, and owners.

### Phase 1: Establish canonical protocols

Deliver observation, evidence, decision, producer, and check schemas; TypeScript/Python bindings; and fixture suites. Exit when SDK and assurance validate the same fixtures and cross-language round trips pass.

### Phase 2: SDK observation emission

Emit one observation per canonical stage, implement artifact layout and conformance, retain legacy output temporarily. Exit when no finding reconstruction is required in assurance.

### Phase 3: Assurance shadow mode

Keep existing gates authoritative while assurance decisions are informational. Measure mismatches, missing and invalid evidence, overhead, unknowns, false failures, and false passes.

### Phase 4: CI-core publication

Add final assurance job, artifact upload, summary renderer, and non-authoritative check. Exit when decisions are transported byte-for-byte.

### Phase 5: Authoritative pull-request gate

Make assurance the required check, retain direct gates temporarily, and maintain rollback. Exit after a sustained reliability window.

### Phase 6: Repair integration

Add remediation projection, resolver adapter, `PR_Repair` observations, repair profile, and invalidation tests. Exit with end-to-end fail, repair, new revision, fresh decision.

### Phase 7: Intelligence and LSP integration

Add prevention-pack profile, approved manifest, verification, and revocation. Exit when only approved digest-bound packs are consumed.

### Phase 8: Remove duplicated runtime functions

Remove scanners, generic harnesses, GitHub orchestration, mutation logic, debt mining, overlapping types, and obsolete compatibility packages. Exit when assurance has no reverse dependency on execution repositories and matches the target API.

---

## 34. Deployment modes

- **Local:** planning, inspection, replay, and unsigned non-production decisions.
- **Hosted CI:** authoritative PR and branch evaluation with immutable provisioning and exact revision.
- **Release:** stronger signing, artifact subjects, supply-chain evidence, audit bundles, retention.
- **Audit verification:** offline verification without repository checkout when bundles are complete.

---

## 35. Governance

Recommended ownership:

| Area | Owner |
|---|---|
| Protocol schemas | Assurance maintainers |
| Producer contracts | Assurance plus producer owner |
| CI workflows | CI-core maintainers |
| Check semantics | SDK maintainers |
| Repair semantics | PR_Repair and resolver maintainers |
| Intelligence metrics | Debt-intelligence maintainers |
| Assurance profiles | Assurance plus governance owners |
| Trust policy | Security and platform owners |
| Waiver policy | Governance owners |

Architecture and security review are mandatory for schema major changes, producer or signer additions, waiver relaxation, mandatory-to-advisory changes, profile control removal, freshness relaxation, and unknown-to-pass behavior.

---

## 36. Operational runbooks

Required runbooks:

1. unsupported schema version;
2. producer version revoked;
3. signature verification outage;
4. evidence artifact missing;
5. CI-core publication discrepancy;
6. decision replay mismatch;
7. policy registry corruption;
8. profile rollback;
9. waiver compromise;
10. signer compromise;
11. rule-pack revocation;
12. repair-loop runaway;
13. evidence-store corruption;
14. accidental test-signer use.

Each SHALL define detection, containment, user-visible behavior, decision semantics, recovery, and preservation of retrospective evidence.

---

## 37. Acceptance criteria

Integration is complete when:

1. SDK emits canonical observations for the PR profile.
2. Assurance evaluates without invoking SDK internals.
3. CI core publishes without reconstruction.
4. Mandatory evidence is exact-revision-bound.
5. Missing mandatory evidence yields indeterminate.
6. Demonstrated mandatory violations yield fail.
7. Repairs force fresh evaluation for new revisions.
8. `PR_Repair` emits conformant observations.
9. Intelligence can submit candidate packs.
10. LSP and SDK verify approved manifests.
11. Decisions replay deterministically.
12. Decisions are immutable.
13. Test signers are rejected in production.
14. Producer and consumer conformance suites run in each repository.
15. Assurance contains no generic scanner, orchestration, repair, LSP, or debt-mining responsibility.
16. Package count and public surface are materially reduced.
17. Decisions are independently verifiable from audit bundles.
18. GitHub checks map exactly to assurance verdicts.
19. Schema and profile compatibility are documented.
20. Migration and rollback are validated.

---

## 38. Initial vertical slice

The first production-oriented slice SHALL remain deliberately narrow:

- one subject: `git-revision`;
- one producer: `l9-ci-sdk`;
- one profile: `l9.pull-request@1`;
- one consumer: `l9-ci-core`;
- minimum controls: repository metadata, transport packet, SDK validation, lint, tests, absence of mandatory findings, and revision consistency;
- minimum outputs: admission report, decision, Markdown projection, and evidence manifest.

Advanced red-team, privacy, external audit, multi-signer, repair, and intelligence capabilities SHOULD follow only after this slice is stable.

---

## 39. Decision summary projection

The Markdown summary SHALL be generated from canonical `decision.json` and SHALL never be an independent authority.

It SHOULD display verdict, subject, profile, policy, decision ID, mandatory controls, evidence counts, unknowns, and remediation routing.

---

## 40. Final target state

```text
Developer edits
    ↓
LSP provides preventive diagnostics from an approved rule pack
    ↓
Pull request triggers l9-ci-core
    ↓
l9-ci-core invokes pinned l9-ci-sdk
    ↓
l9-ci-sdk emits canonical observations
    ↓
l9-assurance admits and evaluates evidence
    ↓
l9-assurance issues an immutable decision
    ↓
l9-ci-core publishes the decision
    ↓
On failure, resolver and PR_Repair may create a bounded repair
    ↓
The new revision receives fresh CI and assurance
    ↓
Historical outcomes feed debt intelligence
    ↓
Debt intelligence produces candidate prevention packs
    ↓
Assurance approves or rejects pack publication
    ↓
Approved packs return to SDK and LSP
```

Permanent invariant:

```text
CI Core orchestrates.
CI SDK observes.
Debt Resolver diagnoses.
PR Repair mutates.
Debt Intelligence learns.
Debt LSP prevents.
Assurance decides.
```

`l9-assurance` SHALL be understood as the protocol authority, evidence-admission boundary, deterministic control evaluator, and attestation issuer for the Quantum-L9 CI constellation.

---

## Next required artifact

Create a package-by-package disposition matrix for the existing 52 assurance workspaces, mapping every package to `KEEP`, `MOVE`, `MERGE`, `DEPRECATE`, or `ARCHIVE`, with target repository, replacement package, migration owner, compatibility window, and removal version.
