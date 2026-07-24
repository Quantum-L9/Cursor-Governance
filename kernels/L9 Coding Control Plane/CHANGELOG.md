# Changelog

All notable changes to `l9-assurance` will be documented in this file.

The project intends to follow semantic versioning once the first stable protocol release is established.

## Unreleased

### Added

* Repository-wide `AGENTS.md` aligned to the L9 Assurance trust-plane boundary.
* Human-facing AI Coding Control Plane guide under `docs/`.
* Canonically named AUDIT, PLAN, BUILD, CHANGE, VALIDATION, DEFINITION OF DONE, and RELEASE kernels.
* Package manifest and SHA-256 inventory.

* Added `ROADMAP.md`, a phased architecture, integration, migration, conformance, security, and acceptance roadmap for evolving the existing repository into the constellation trust plane.
* Root-level architectural definition of `l9-assurance` as the trust and decision plane of the Quantum-L9 CI constellation.
* Explicit constellation responsibility model covering:
  * `l9-ci-core`;
  * `l9-ci-sdk`;
  * `l9-ci-debt-resolver`;
  * `PR_Repair`;
  * `l9-ci-debt-intelligence`;
  * `l9-ci-debt-lsp`;
  * `l9-assurance`.
* Target assurance domain model for:
  * subjects;
  * producers;
  * observations;
  * findings;
  * evidence envelopes;
  * claims;
  * controls;
  * profiles;
  * waivers;
  * unknowns;
  * control results;
  * decisions;
  * attestations.
* Defined verdict semantics:
  * pass;
  * fail;
  * conditional;
  * indeterminate.
* Defined evidence-admission pipeline.
* Defined target CLI and programmatic interfaces.
* Defined repair-loop revision invalidation behavior.
* Defined prevention-pack assurance model.
* Added security threat model and trust-boundary requirements.
* Added contribution and architectural ownership guidance.
* Added Python project metadata for future schema tooling and generated bindings.

### Changed

* Narrowed the intended repository role from a broad assurance runtime to:
  * protocol authority;
  * evidence-admission boundary;
  * deterministic evaluator;
  * attestation issuer.
* Clarified that execution, repair, orchestration, intelligence, and editor capabilities belong in their respective constellation repositories.
* Established exact subject and revision binding as a mandatory invariant.
* Established immutable decisions as a mandatory invariant.
* Established explicit unknowns and indeterminate outcomes.
* Established that hard-gate failures dominate aggregate scores.

### Deprecated

* Assurance-owned generic test execution.
* Assurance-owned scanner execution.
* Assurance-owned GitHub workflow orchestration.
* Assurance-owned repair planning and mutation.
* Assurance-owned debt mining.
* Assurance-owned editor integration.
* Direct internal coupling to constellation repository implementations.

### Security

* Documented threats involving:
  * forged evidence;
  * subject substitution;
  * replay;
  * stale evidence;
  * unauthorized producers;
  * signature downgrade;
  * waiver forgery;
  * policy rollback;
  * redaction ambiguity;
  * test signer leakage.
* Defined testing-only signer isolation.
* Defined strict evidence-ingestion constraints.
* Defined immutable decision and digest-binding requirements.

## 1.0.0

### Existing baseline

* Existing npm workspace release baseline.
* Existing package workspace structure under `packages/*`.
* Existing repository package metadata.

This changelog does not claim that the target assurance architecture is fully implemented. The Unreleased section records the architectural contract introduced by the root documentation and metadata build.
