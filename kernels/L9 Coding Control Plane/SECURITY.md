# Security Policy

## 1. Security posture

`l9-assurance` is a trust-boundary component.

A defect in evidence admission, subject binding, policy evaluation, waiver handling, or decision issuance may cause an incorrect CI or release decision.

Security review must therefore treat the repository as a high-integrity decision system rather than an ordinary reporting library.

## 2. Supported versions

During the architectural transition, only explicitly maintained release branches and tagged versions should be considered supported.

Support policy will be formalized when the first stable protocol release is published.

Until then:

* security fixes may be applied only to the current mainline;
* compatibility guarantees are limited;
* draft schemas and interfaces may change;
* consumers should pin exact versions or immutable digests.

## 3. Reporting vulnerabilities

Do not disclose suspected vulnerabilities in public issues.

Report privately through the repository's configured security advisory channel.

A useful report includes:

* affected version or commit;
* affected component;
* reproduction steps;
* expected behavior;
* observed behavior;
* security impact;
* proof-of-concept artifact where safe;
* whether subject binding, signatures, waivers, or decisions are affected.

Do not include production credentials, private keys, personal data, or sensitive customer evidence.

## 4. Threat model

The system must assume that evidence inputs may be malicious.

Threats include:

* forged producer identities;
* fabricated observations;
* tampered payloads;
* incorrect digests;
* revision substitution;
* branch-to-commit confusion;
* replayed evidence;
* stale evidence;
* unauthorized producer versions;
* revoked producer versions;
* unauthorized check IDs;
* signature stripping;
* signature downgrade;
* algorithm confusion;
* canonicalization ambiguity;
* policy rollback;
* profile substitution;
* waiver forgery;
* waiver expiry bypass;
* selective evidence omission;
* misleading redaction;
* archive traversal;
* decompression bombs;
* deeply nested JSON;
* oversized findings;
* malicious Markdown;
* log injection;
* test signer use in production;
* decision overwrite;
* duplicate evidence with alternate identifiers.

## 5. Security invariants

### 5.1 Exact revision binding

A decision must apply only to the exact revision identified by mandatory evidence.

Evidence for commit A must not satisfy controls for commit B.

### 5.2 Immutable decisions

An issued decision must not be modified.

Corrections require a new decision.

### 5.3 Admission before evaluation

Unvalidated producer output must not satisfy controls.

### 5.4 Explicit trust policy

Producer and signer trust must be registry-driven.

The latest version must not be trusted automatically.

### 5.5 Test signer isolation

Test signers must:

* live in testing-only modules;
* identify themselves as test identities;
* be rejected by production trust policy;
* never be exported from the default production entrypoint.

### 5.6 Hard-gate integrity

No score may override:

* a failed mandatory control;
* an invalid signature;
* a subject mismatch;
* missing mandatory evidence;
* an expired waiver.

## 6. Evidence ingestion controls

The admission layer must enforce:

* media-type allowlists;
* maximum artifact size;
* maximum decompressed size;
* maximum JSON depth;
* maximum array length;
* maximum string length;
* maximum finding count;
* maximum lineage depth;
* strict schema validation;
* unknown-field policy;
* canonical serialization;
* digest verification;
* subject normalization;
* producer authorization;
* replay protection.

Archive extraction must prevent:

* path traversal;
* symbolic-link escape;
* absolute-path extraction;
* device file creation;
* decompression bombs.

## 7. Cryptographic requirements

Cryptographic operations must:

* use explicit algorithm identifiers;
* use collision-resistant digests;
* canonicalize signed payloads;
* reject unsupported algorithms;
* reject algorithm downgrade;
* bind signatures to schema version;
* bind signatures to subject;
* bind signatures to profile and policy;
* bind signatures to decision digest;
* separate signing from evaluation;
* support revocation.

Private keys must not be stored in the repository.

Production key access should be delegated to an external key-management adapter.

## 8. Waiver security

Waivers are risk-acceptance artifacts and must include:

* waiver ID;
* control ID;
* subject scope;
* rationale;
* accepted risk;
* authorizing identity;
* issue time;
* expiry time;
* optional constraints;
* signature where required.

Expired waivers must be rejected.

A waiver must not silently convert a failed control into an ordinary pass.

## 9. Policy security

Policy artifacts must be:

* versioned;
* digest-bound;
* reviewable;
* immutable once referenced by a decision;
* protected against rollback.

Changes that relax controls require elevated review.

Examples include:

* mandatory to advisory;
* shorter evidence requirements;
* longer freshness windows;
* weaker signer requirements;
* broader waiver eligibility;
* unknown-to-pass behavior.

## 10. Redaction security

Redacted evidence is a derivative artifact.

A redaction record must identify:

* source evidence;
* source digest;
* derivative digest;
* transformation identity;
* removed fields;
* replaced fields;
* operator identity;
* transformation time.

A redacted bundle must declare whether it is:

* complete;
* partial;
* review-limited.

Redaction must not conceal information that changes the decision without explicitly declaring that limitation.

## 11. Output rendering

Decision summaries, logs, findings, and Markdown must be treated as untrusted content.

Renderers must escape or sanitize:

* HTML;
* control characters;
* terminal escape sequences;
* Markdown links;
* embedded images;
* code fences;
* user-controlled headings.

The canonical JSON decision remains authoritative.

## 12. Dependency security

Dependencies should be minimized.

Security-sensitive packages should prefer:

* mature libraries;
* narrow APIs;
* reproducible versions;
* lockfile verification;
* provenance-aware publishing;
* regular vulnerability review.

New dependencies used for:

* cryptography;
* schema validation;
* canonicalization;
* archive extraction;
* signature verification

require explicit security review.

## 13. Build and release security

Release builds should:

* run from a clean checkout;
* use pinned toolchains;
* verify generated artifacts;
* inspect package tarballs;
* reject untracked generated output;
* generate checksums;
* produce provenance;
* avoid embedding local absolute paths;
* verify no test keys or fixtures ship in production exports.

## 14. Logging and telemetry

Logs must not include:

* secrets;
* private keys;
* authorization tokens;
* unrestricted evidence payloads;
* personal data without explicit need;
* full source files by default.

Logs should include:

* correlation ID;
* run ID;
* decision ID;
* subject digest;
* profile;
* policy version;
* machine-readable reason codes.

## 15. Incident classes

Security runbooks should exist for:

* signer compromise;
* producer compromise;
* producer-version revocation;
* waiver compromise;
* policy rollback;
* schema confusion;
* evidence-store corruption;
* replay detection;
* test signer in production;
* decision publication mismatch;
* audit bundle tampering.

## 16. Security testing

Required security tests include:

* revision substitution;
* signature stripping;
* signature downgrade;
* digest mismatch;
* duplicate evidence;
* replayed evidence;
* stale evidence;
* malformed Unicode;
* excessive nesting;
* oversized input;
* archive traversal;
* selective evidence omission;
* expired waiver;
* unauthorized producer;
* revoked producer;
* profile digest mismatch;
* policy digest mismatch;
* test signer rejection.

## 17. Security review triggers

Mandatory security review is required for:

* schema major-version changes;
* trust-registry changes;
* signer additions;
* cryptographic changes;
* waiver relaxation;
* control severity reduction;
* evidence freshness relaxation;
* profile control removal;
* new archive or parser dependencies;
* new production output formats.
