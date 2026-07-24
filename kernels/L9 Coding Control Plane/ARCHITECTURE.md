# L9 Assurance Architecture

## 1. Architectural role

`l9-assurance` is the trust plane of the Quantum-L9 CI constellation.

Its role is to evaluate whether an exact subject revision satisfies an explicit assurance profile under a specific policy version, using admitted evidence from authorized producers.

The repository must remain independent from the internal implementation details of execution, repair, intelligence, and editor systems.

## 2. System boundaries

### 2.1 In scope

The assurance boundary includes:

* protocol contracts;
* evidence admission;
* subject identity;
* revision binding;
* producer authorization;
* integrity validation;
* freshness validation;
* lineage validation;
* control definitions;
* profile composition;
* policy resolution;
* waiver validation;
* unknown-state handling;
* verdict reduction;
* decision issuance;
* attestation;
* audit export;
* conformance verification.

### 2.2 Out of scope

The assurance boundary excludes:

* source scanning;
* test execution;
* CI workflow execution;
* GitHub-specific event handling;
* repository mutation;
* repair planning;
* rollback;
* debt corpus mining;
* prevention-rule generation;
* editor protocol handling;
* job scheduling;
* general-purpose orchestration.

## 3. Constellation topology

```text
                           CONTROL PLANE
                  ┌──────────────────────────┐
                  │       l9-ci-core         │
                  │ workflows and publishing│
                  └────────────┬─────────────┘
                               │ invokes
                               ▼
                     EXECUTION PLANE
                  ┌──────────────────────────┐
                  │       l9-ci-sdk          │
                  │ checks and observations  │
                  └────────────┬─────────────┘
                               │ observations
                               ▼
                       TRUST PLANE
                  ┌──────────────────────────┐
                  │      l9-assurance        │
                  │ admission and decisions  │
                  └────────────┬─────────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │ failure                           │ pass
             ▼                                   ▼
       REMEDIATION PLANE                   l9-ci-core publishes
 ┌───────────────────────────┐             authoritative outcome
 │ l9-ci-debt-resolver       │
 │ PR_Repair                 │
 └─────────────┬─────────────┘
               │ operational findings
               ▼
       INTELLIGENCE PLANE
 ┌───────────────────────────┐
 │ l9-ci-debt-intelligence   │
 └─────────────┬─────────────┘
               │ approved prevention assets
               ▼
 ┌───────────────────────────┐
 │ l9-ci-sdk / debt-lsp      │
 └───────────────────────────┘
```

## 4. Architectural invariants

### 4.1 Exact subject binding

Every mandatory evidence artifact must apply to the exact subject in the decision.

For Git subjects:

```text
decision revision
  = mandatory evidence revision
  = evaluated commit
```

A branch name is not a sufficient subject identity.

### 4.2 Immutable decisions

An issued decision is immutable.

A later evaluation creates a new decision and may reference the earlier one using `supersedes`.

### 4.3 Protocol-based integration

Constellation repositories exchange versioned JSON artifacts.

They must not depend on one another's internal classes or private modules.

### 4.4 Pure evaluation

The evaluator should behave as a pure function:

```text
subject + profile + policy + admitted evidence
    → assurance decision
```

The evaluator must not:

* access the network;
* execute tests;
* invoke scanners;
* mutate repositories;
* depend on wall-clock time without injection;
* depend on filesystem iteration order;
* rely on mutable global state.

### 4.5 Admission precedes evaluation

Raw producer output is not automatically assurance evidence.

It must pass an admission pipeline before it can satisfy a control.

### 4.6 Hard gates dominate scores

Aggregate confidence, coverage, or quality scores must never override:

* a mandatory control failure;
* invalid required evidence;
* a subject mismatch;
* an expired or unauthorized waiver.

### 4.7 Explicit unknowns

Missing or unverifiable knowledge must be represented as an unknown.

Unknowns must not be silently converted into pass or fail.

## 5. Logical architecture

```text
┌─────────────────────────────────────────────┐
│ Public Interfaces                           │
│ CLI, library API, schemas, conformance API  │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│ Application Layer                           │
│ planning, admission orchestration,          │
│ evaluation orchestration, bundle generation │
└─────────────┬─────────────────┬─────────────┘
              │                 │
┌─────────────▼──────────┐  ┌──▼─────────────────────┐
│ Evidence Kernel       │  │ Policy and Control      │
│ validation, lineage,  │  │ profile resolution,     │
│ integrity, freshness  │  │ waivers, hard gates     │
└─────────────┬──────────┘  └──┬─────────────────────┘
              │                │
┌─────────────▼────────────────▼──────────────┐
│ Deterministic Evaluator                    │
│ control results, unknown propagation,      │
│ decision reduction                         │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│ Attestation and Audit                      │
│ signing, verification, bundle manifests,   │
│ redaction lineage                          │
└─────────────────────────────────────────────┘
```

## 6. Target package boundaries

### contracts

Owns stable protocol types and generated bindings.

It contains no I/O or evaluation logic.

### evidence

Owns evidence admission:

* schema validation;
* canonicalization;
* digest verification;
* producer authorization;
* subject validation;
* freshness;
* lineage;
* replay detection;
* signature verification adapters.

### controls

Owns declarative control definitions and evidence requirements.

It does not invoke commands.

### policy

Owns:

* mandatory versus advisory classification;
* organization overlays;
* repository overlays;
* waiver eligibility;
* expiry;
* hard-gate behavior;
* unknown handling.

### evaluator

Owns deterministic control and decision evaluation.

### attestations

Owns signing and verification abstractions.

Production signers are adapters. Test signers must remain isolated.

### audit

Owns complete and redacted audit bundles.

### conformance

Owns producer and consumer compatibility suites.

### cli

Owns user-facing protocol operations.

### testing

Owns fixtures, fake clocks, in-memory stores, and test-only signers.

## 7. Domain model

### 7.1 Subject

A subject is the immutable object being assured.

Supported target subject kinds include:

* Git revision;
* release artifact;
* rule pack;
* repair execution;
* release candidate.

### 7.2 Observation

An observation is a producer-generated statement about an execution.

Examples:

* a CI stage passed;
* a prohibited import was found;
* a repair respected protected paths;
* a rule pack met precision requirements.

### 7.3 Evidence

Evidence is an admitted, normalized, integrity-bound artifact.

Not every observation becomes evidence.

### 7.4 Claim

A claim is a statement assurance may support.

Examples:

* CI baseline satisfied;
* repair governance satisfied;
* release controls satisfied;
* prevention pack approved.

### 7.5 Control

A control defines what evidence is required to support part of a claim.

### 7.6 Profile

A profile is a versioned set of controls for one assurance context.

Examples:

* pull request;
* protected branch;
* release candidate;
* repair mutation;
* prevention-pack publication.

### 7.7 Decision

A decision is the immutable result of evaluating one subject under one profile and policy.

## 8. Evidence admission architecture

The admission pipeline is:

```text
artifact discovery
    ↓
media-type and size validation
    ↓
schema dispatch
    ↓
structural validation
    ↓
canonicalization
    ↓
digest verification
    ↓
producer lookup
    ↓
check authorization
    ↓
subject normalization
    ↓
revision matching
    ↓
freshness validation
    ↓
signature verification
    ↓
lineage validation
    ↓
replay detection
    ↓
policy admissibility
    ↓
accepted, rejected, quarantined, or duplicate
```

Rejected and quarantined evidence cannot satisfy mandatory controls.

## 9. Verdict reduction

### Pass

All applicable mandatory controls passed with admissible evidence.

### Fail

At least one mandatory control has admissible evidence demonstrating failure.

### Indeterminate

A mandatory result cannot be established because evidence is absent, invalid, stale, unauthorized, unverifiable, or bound to another subject.

### Conditional

A policy-approved waiver or limitation constrains an otherwise acceptable result.

## 10. CI integration

The canonical integration is:

```text
l9-ci-core receives event
    ↓
l9-ci-core invokes pinned l9-ci-sdk
    ↓
l9-ci-sdk emits observations
    ↓
l9-ci-core transports observations unchanged
    ↓
l9-assurance admits evidence
    ↓
l9-assurance evaluates profile
    ↓
l9-assurance emits decision
    ↓
l9-ci-core publishes decision
```

`l9-ci-core` must publish the decision, not reconstruct it.

## 11. Repair integration

```text
decision for commit A = fail
    ↓
resolver classifies failure
    ↓
PR_Repair creates approved bounded mutation
    ↓
commit B is created
    ↓
fresh CI runs for commit B
    ↓
fresh assurance decision for commit B
```

Evidence from commit A cannot satisfy revision-bound controls for commit B.

## 12. Intelligence integration

Debt intelligence produces candidate prevention packs.

Assurance evaluates whether a pack may be published.

The SDK and LSP should consume only approved, digest-bound, compatible packs.

## 13. Dependency direction

Allowed dependency direction:

```text
assurance contracts
      ▲
      │
SDK, PR_Repair, resolver, intelligence
      │
      └──── observations and evidence ────▶ assurance evaluator
                                              │
                                              ▼
                                         signed decision
                                              │
                                              ▼
                                           CI core
```

Forbidden dependencies:

* assurance evaluator depending on CI core;
* assurance evaluator depending on PR Repair;
* assurance evaluator depending on debt intelligence;
* CI SDK depending on the assurance evaluator;
* assurance implementation depending on GitHub Actions internals.

## 14. Deployment modes

### Local

For planning, validation, simulation, and unsigned local decisions.

### Hosted CI

For authoritative PR and branch decisions.

### Release

For signed artifact-bound decisions and audit bundles.

### Audit verification

For offline verification of decisions and bundles.

## 15. Migration architecture

The migration should proceed through:

1. package inventory;
2. protocol establishment;
3. SDK observation emission;
4. assurance shadow mode;
5. CI-core publication;
6. authoritative gate activation;
7. repair integration;
8. intelligence and LSP integration;
9. deletion of duplicated execution responsibilities.

## 16. End-state invariant

```text
CI Core orchestrates.
CI SDK observes.
Debt Resolver diagnoses.
PR Repair mutates.
Debt Intelligence learns.
Debt LSP prevents.
Assurance decides.
```
