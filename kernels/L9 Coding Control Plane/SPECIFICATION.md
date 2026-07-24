# L9 Assurance Integration Specification

## 1. Status

Specification type: Architecture and implementation contract
Version: 1.0.0-draft
Target: Quantum-L9 CI constellation
Normative terms: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY

## 2. Mission

`l9-assurance` MUST act as the protocol authority, evidence-admission boundary, deterministic control evaluator, and decision issuer for the CI constellation.

For one exact subject, one assurance profile, one policy version, and one evidence set, it MUST produce one immutable assurance decision.

## 3. Functional requirements

### 3.1 Protocol contracts

The repository MUST define versioned schemas for:

* subject;
* producer;
* check;
* finding;
* observation;
* evidence envelope;
* evidence admission result;
* claim;
* control;
* control result;
* profile;
* policy;
* waiver;
* unknown;
* assurance decision;
* attestation;
* audit bundle.

### 3.2 Evidence admission

The repository MUST validate:

* schema compatibility;
* payload structure;
* payload digest;
* producer identity;
* producer version;
* check authorization;
* subject identity;
* revision binding;
* timestamps;
* evidence freshness;
* signatures where required;
* evidence lineage;
* duplicate state;
* replay state;
* policy admissibility.

### 3.3 Control evaluation

The repository MUST:

* resolve applicable controls;
* match admitted evidence to requirements;
* distinguish pass, fail, conditional, indeterminate, and not applicable;
* propagate unknowns;
* apply waiver rules;
* preserve reason codes;
* calculate a deterministic overall verdict.

### 3.4 Decision issuance

Every decision MUST contain:

* schema version;
* decision ID;
* subject;
* profile identity and digest;
* policy identity and digest;
* overall verdict;
* control results;
* claim results;
* evidence manifest;
* waiver references;
* unknowns;
* evaluator identity;
* issuance time;
* optional supersession reference;
* optional signature.

## 4. Non-functional requirements

The implementation MUST be:

* deterministic;
* auditable;
* revision-bound;
* language-neutral at the protocol boundary;
* compatible with offline evaluation;
* safe for untrusted artifact ingestion;
* independent of GitHub-specific runtime behavior;
* independent of scanner internals;
* independent of repair internals.

## 5. Canonical types

### 5.1 Subject

```ts
interface SubjectReference {
  kind:
    | "git-revision"
    | "artifact"
    | "rule-pack"
    | "repair-execution"
    | "release"
    | "repository-state";
  repository?: {
    host: string;
    owner: string;
    name: string;
  };
  revision?: {
    commit: string;
    treeDigest?: Digest;
  };
  artifact?: {
    name: string;
    digest: Digest;
    mediaType?: string;
  };
  metadata?: Record<string, string>;
}
```

Requirements:

1. A subject MUST be immutable or content-addressed.
2. Branch names MUST NOT be sufficient identifiers.
3. Tags MUST resolve to immutable revisions or digests.
4. All mandatory evidence MUST bind to the same exact subject.

### 5.2 Producer

```ts
interface ProducerIdentity {
  id: string;
  version: string;
  buildDigest?: Digest;
  executionIdentity?: string;
  repository?: string;
}
```

### 5.3 Observation

```ts
interface Observation {
  schema: "l9.observation";
  schemaVersion: string;
  observationId: string;
  producer: ProducerIdentity;
  subject: SubjectReference;
  check: {
    id: string;
    version: string;
    configurationDigest: Digest;
    mode?: string;
  };
  execution: {
    runId: string;
    attempt: number;
    status: "passed" | "failed" | "error" | "skipped";
    startedAt: string;
    completedAt: string;
    environmentDigest?: Digest;
    invocationDigest?: Digest;
  };
  summary: {
    findingCount: number;
    errorCount: number;
    warningCount: number;
    informationalCount: number;
  };
  findings: Finding[];
  artifacts: ArtifactReference[];
  provenance?: Provenance;
  extensions?: Record<string, unknown>;
}
```

### 5.4 Finding

```ts
interface Finding {
  findingId: string;
  ruleId: string;
  ruleVersion?: string;
  severity:
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "informational";
  disposition:
    | "open"
    | "accepted"
    | "suppressed"
    | "resolved"
    | "not-applicable";
  message: string;
  location?: {
    path?: string;
    lineStart?: number;
    columnStart?: number;
    lineEnd?: number;
    columnEnd?: number;
  };
  fingerprint?: string;
  evidence?: ArtifactReference[];
  remediation?: RemediationReference;
  metadata?: Record<string, unknown>;
}
```

### 5.5 Evidence envelope

```ts
interface EvidenceEnvelope {
  schema: "l9.evidence-envelope";
  schemaVersion: string;
  evidenceId: string;
  subject: SubjectReference;
  producer: ProducerIdentity;
  evidenceType: string;
  observedAt: string;
  issuedAt: string;
  payload: unknown;
  payloadDigest: Digest;
  sourceObservationId?: string;
  lineage: EvidenceReference[];
  admissionContext?: {
    receivedAt: string;
    channel: "local" | "ci-artifact" | "api" | "bundle";
    transportDigest?: Digest;
  };
  signature?: Signature;
  redaction?: RedactionDescriptor;
}
```

### 5.6 Admission result

```ts
interface EvidenceAdmissionResult {
  evidenceId?: string;
  status:
    | "accepted"
    | "rejected"
    | "quarantined"
    | "duplicate";
  reasons: AdmissionReason[];
  validations: {
    schema: ValidationResult;
    producer: ValidationResult;
    subject: ValidationResult;
    integrity: ValidationResult;
    freshness: ValidationResult;
    authorization: ValidationResult;
    replay: ValidationResult;
    lineage: ValidationResult;
  };
}
```

### 5.7 Control

```ts
interface ControlDefinition {
  id: string;
  version: string;
  claim: string;
  title: string;
  description: string;
  severity: "mandatory" | "advisory";
  applicability?: Expression;
  evidenceRequirements: EvidenceRequirement[];
  dependencies?: ControlReference[];
  evaluation:
    | DeclarativeEvaluation
    | RegisteredEvaluatorReference;
  freshness?: FreshnessRequirement;
  waiver?: WaiverPolicy;
}
```

### 5.8 Profile

```ts
interface AssuranceProfile {
  id: string;
  version: string;
  title: string;
  subjectKinds: string[];
  controls: ControlReference[];
  defaultPolicy: PolicyReference;
  outputClaims: ClaimReference[];
  compatibility?: {
    minimumAssuranceVersion?: string;
    minimumSchemaVersion?: string;
  };
}
```

### 5.9 Waiver

```ts
interface Waiver {
  waiverId: string;
  controlId: string;
  subjectScope: SubjectScope;
  rationale: string;
  riskAcceptance: string;
  authorizedBy: IdentityReference;
  issuedAt: string;
  expiresAt: string;
  constraints?: Record<string, unknown>;
  signature?: Signature;
}
```

A waiver MUST NOT rewrite a failed control as an ordinary pass.

### 5.10 Unknown

```ts
interface Unknown {
  unknownId: string;
  category:
    | "missing-evidence"
    | "invalid-evidence"
    | "stale-evidence"
    | "unsupported-check"
    | "unverified-producer"
    | "policy-ambiguity"
    | "environment-uncertainty"
    | "external-dependency"
    | "other";
  description: string;
  impact: "none" | "advisory" | "control" | "decision";
  relatedControls: string[];
  resolvableBy?: string[];
}
```

### 5.11 Control result

```ts
interface ControlResult {
  controlId: string;
  controlVersion: string;
  status:
    | "pass"
    | "fail"
    | "conditional"
    | "indeterminate"
    | "not-applicable";
  severity: "mandatory" | "advisory";
  evidenceRefs: string[];
  waiverRefs: string[];
  unknownRefs: string[];
  reasons: DecisionReason[];
  evaluatedAt: string;
}
```

### 5.12 Decision

```ts
interface AssuranceDecision {
  schema: "l9.assurance-decision";
  schemaVersion: string;
  decisionId: string;
  subject: SubjectReference;
  profile: {
    id: string;
    version: string;
    digest: Digest;
  };
  policy: {
    id: string;
    version: string;
    digest: Digest;
  };
  verdict:
    | "pass"
    | "fail"
    | "conditional"
    | "indeterminate";
  controlResults: ControlResult[];
  claims: ClaimResult[];
  evidenceManifest: EvidenceReference[];
  waivers: WaiverReference[];
  unknowns: Unknown[];
  dimensions?: {
    controlSatisfaction?: number;
    evidenceCompleteness?: number;
    evidenceFreshness?: number;
    producerTrust?: number;
  };
  issuedAt: string;
  evaluator: ProducerIdentity;
  supersedes?: string;
  signature?: Signature;
}
```

## 6. Admission pipeline

The implementation MUST process evidence in this order:

1. artifact discovery;
2. media-type validation;
3. size validation;
4. schema version dispatch;
5. structural validation;
6. canonicalization;
7. digest verification;
8. producer lookup;
9. producer-version authorization;
10. check authorization;
11. subject normalization;
12. revision comparison;
13. execution-time validation;
14. freshness validation;
15. signature verification;
16. lineage validation;
17. replay and duplicate checks;
18. policy admissibility;
19. acceptance, rejection, quarantine, or deduplication.

## 7. Admission reason codes

The implementation MUST expose stable reason codes including:

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

## 8. Verdict semantics

### pass

The implementation MUST issue pass only when:

* all applicable mandatory controls pass;
* all mandatory evidence is admitted;
* no decision-impacting unknown remains;
* no conditional waiver rule applies;
* subject binding is exact.

### fail

The implementation MUST issue fail when admissible evidence demonstrates that one or more mandatory controls failed.

### indeterminate

The implementation MUST issue indeterminate when a mandatory result cannot be established because evidence is:

* missing;
* malformed;
* stale;
* unauthorized;
* unverifiable;
* inconsistent;
* bound to another subject.

### conditional

The implementation MUST issue conditional when policy permits progress under:

* an approved waiver;
* an explicit limitation;
* an accepted risk;
* a bounded exception.

## 9. Producer registry requirements

A producer registry MUST define:

* producer ID;
* producer repository;
* accepted versions;
* accepted subject kinds;
* authorized checks;
* minimum check versions;
* signing requirements;
* revocation state.

Registry changes MUST be reviewed as trust-boundary changes.

## 10. Check registry requirements

Each check MUST have:

* stable ID;
* version;
* owning producer;
* output schema;
* semantic description;
* determinism declaration;
* revision-binding requirement.

Behaviorally incompatible changes require a new major version.

## 11. Profile requirements

The repository SHOULD define these profiles:

* `l9.pull-request`;
* `l9.protected-branch`;
* `l9.release-candidate`;
* `l9.repair-mutation`;
* `l9.prevention-pack-publication`;
* `l9.repository-bootstrap`.

## 12. CI artifact layout

The intended artifact structure is:

```text
artifacts/
├── observations/
├── supporting/
└── assurance/
    ├── admission-report.json
    ├── decision.json
    ├── decision.summary.md
    ├── evidence-manifest.json
    └── decision.attestation.json
```

The Markdown summary is a projection of `decision.json`. It is not an independent authority.

## 13. CLI contract

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

Target exit codes:

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

## 14. Programmatic API

```ts
interface AssuranceEngine {
  plan(request: PlanRequest): Promise<AssurancePlan>;
  admit(
    request: AdmissionRequest
  ): Promise<AdmissionReport>;
  evaluate(
    request: EvaluationRequest
  ): Promise<AssuranceDecision>;
  verify(
    request: VerificationRequest
  ): Promise<VerificationReport>;
  bundle(
    request: BundleRequest
  ): Promise<AuditBundle>;
}
```

## 15. Determinism requirements

Equivalent normalized inputs MUST produce equivalent canonical decision payloads.

The evaluator MUST use:

* explicit evaluation time;
* stable ordering;
* canonical JSON;
* deterministic reason ordering;
* deterministic control ordering;
* deterministic evidence ordering.

It MUST NOT depend on:

* locale;
* filesystem ordering;
* wall-clock access;
* nondeterministic map iteration;
* random IDs generated inside the pure evaluator.

## 16. Repair-loop requirements

When a repair creates a new revision:

1. the prior decision remains immutable;
2. the new revision requires fresh evidence;
3. evidence from the prior revision cannot satisfy revision-bound controls;
4. the new decision may reference the earlier decision using `supersedes`.

## 17. Prevention-pack requirements

A prevention pack MUST NOT be consumed as approved solely because it was generated.

It SHOULD require evidence for:

* schema validity;
* corpus provenance;
* precision;
* false-positive rate;
* topology coverage;
* leverage;
* compatibility;
* required human approval;
* digest creation.

## 18. Security requirements

The implementation MUST protect against:

* forged observations;
* revision substitution;
* replay;
* stale evidence;
* unauthorized producers;
* signature downgrade;
* canonicalization mismatch;
* waiver forgery;
* policy rollback;
* profile substitution;
* artifact bombs;
* path traversal;
* malicious Markdown or log rendering;
* test signer use in production.

## 19. Conformance requirements

Every producer MUST pass fixtures for:

* valid observation;
* invalid schema;
* missing subject;
* mismatched revision;
* unsupported version;
* incorrect digest;
* unauthorized check;
* stale evidence;
* duplicate evidence;
* oversized evidence.

Every consumer MUST prove it does not reinterpret or alter the decision.

## 20. Initial delivery scope

The first vertical slice MUST include:

* one Git revision subject;
* `l9-ci-sdk` as producer;
* `l9.pull-request@1` as profile;
* `l9-ci-core` as consumer;
* admission report;
* decision;
* evidence manifest;
* human-readable summary.

Advanced repair, intelligence, redaction, and signing capabilities SHOULD follow after this slice is stable.
