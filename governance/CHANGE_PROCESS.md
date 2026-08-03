# Organization-Invariant Change Process

## Objective

Change organization policy without creating semantic drift, false enforcement
claims, or incompatible downstream behavior.

## Required sequence

### 1. Inspect

Inspect:

- CANONICAL_LAW.md;
- ORG_INVARIANTS.yaml;
- governance/ASSERTION_TYPES.yaml;
- the policy schema;
- existing tests;
- active workflows;
- open policy-related pull requests;
- downstream compatibility commitments.

Do not edit from memory.

### 2. Identify impact

Record:

- invariants affected;
- assertion types affected;
- schema sections affected;
- downstream consumers affected;
- whether semantics change;
- whether enforcement requirements change;
- whether a migration is required.

### 3. Update policy and grammar together

A policy field must not be introduced without schema support.

A schema field must not silently alter existing policy meaning.

### 4. Version assertion semantics

An assertion version must change when evaluation semantics change in a way that
can alter pass, fail, or unknown outcomes for an existing input.

Documentation-only clarification does not require a version change when it does
not alter evaluation.

### 5. Preserve identifiers

Released invariant IDs and assertion type/version pairs are immutable.

Do not reuse a retired ID for a different meaning.

### 6. Version the policy

Use semantic versioning:

- patch: clarification or non-semantic correction;
- minor: backward-compatible policy addition;
- major: incompatible policy or interpretation change.

### 7. Validate

Run all repository-supported validation, including:

- YAML parsing;
- JSON parsing;
- schema validation;
- identifier uniqueness;
- assertion reference resolution;
- positive tests;
- negative-path tests;
- deterministic repeated validation.

Do not report validation that was not executed.

### 8. Obtain independent approval

Governance-sensitive changes require authorized human review.

The author must not self-approve.

Agent approval is insufficient.

### 9. Produce release metadata

After approval, produce a release record containing immutable source identity
and digests.

Do not fabricate:

- commits;
- digests;
- signatures;
- attestations;
- approval references;
- validation results.

### 10. Publish dependent updates separately

Platform bindings, assurance implementations, CI runtimes, and consumer
bindings should update in their owning repositories.

Do not copy their implementation into Cursor-Governance.

## Backward compatibility

A change is backward compatible only when an existing valid consumer can
continue to interpret the policy without changing the meaning of an existing
requirement.

Adding a required field is not backward compatible.

Changing an assertion outcome is not backward compatible.

Changing canonicalization rules is not backward compatible.

## Deprecation

Deprecation requires:

- the deprecated identifier;
- replacement guidance;
- effective date;
- supported transition period;
- downstream impact statement.

Deprecated identifiers remain reserved.

## Emergency changes

Emergency policy changes still require:

- exact incident reference;
- smallest safe change;
- independent authorized approval;
- explicit expiration or follow-up review;
- validation evidence;
- retrospective review.

Emergency status does not authorize fake validation.

## Rollback

Rollback must restore a previously approved policy release.

A rollback must not:

- reuse a version number for different content;
- remove audit history;
- hide the cause of rollback;
- claim restored enforcement without current platform evidence.

## Consumer impact analysis

Every semantic change must state:

- affected policy IDs;
- affected invariant IDs;
- affected assertion versions;
- required consumer action;
- minimum compatible policy version;
- expected failure behavior for stale consumers.

## Enforcement claims

A policy change may require blocking enforcement immediately while assurance
still reports current enforcement as unverified.

Do not weaken the requirement to match incomplete rollout.

Do not strengthen the assurance claim to match the requirement.
