# L9 Assurance

`l9-assurance` is the trust, control-evaluation, and attestation plane of the Quantum-L9 CI constellation.

It converts revision-bound, producer-attributed, policy-admissible evidence into deterministic, auditable assurance decisions.

It does not execute tests, scan repositories, repair source code, run GitHub Actions, mine CI debt, or serve editor diagnostics.

## Position in the CI constellation

```text
l9-ci-core
  orchestrates hosted CI and publishes assurance outcomes
l9-ci-sdk
  executes checks and emits canonical observations
l9-ci-debt-resolver
  diagnoses CI failures and derives repair-oriented classifications
PR_Repair
  performs approved, bounded, isolated, and verified mutations
l9-ci-debt-intelligence
  mines historical failure patterns and compiles prevention assets
l9-ci-debt-lsp
  presents approved prevention rules in developer editors
l9-assurance
  validates evidence, evaluates controls, records unknowns,
  resolves policy, and issues assurance decisions
```

The governing invariant is:

```text
CI Core orchestrates.
CI SDK observes.
Debt Resolver diagnoses.
PR Repair mutates.
Debt Intelligence learns.
Debt LSP prevents.
Assurance decides.
```

## Purpose

For an exact subject revision, assurance answers:

* What claims are being evaluated?
* What controls apply?
* What evidence is required?
* Which evidence is valid and admissible?
* Which controls passed, failed, or remain indeterminate?
* Which waivers or unknowns constrain the result?
* What decision may defensibly be issued?
* Can that decision be independently verified?

## Responsibilities

`l9-assurance` owns:

* assurance protocol schemas;
* subject identity and revision binding;
* producer and check registries;
* evidence admission;
* evidence integrity and lineage;
* claim definitions;
* control definitions;
* assurance profiles;
* policy evaluation;
* waiver semantics;
* unknown-state semantics;
* deterministic verdict calculation;
* immutable decision issuance;
* attestation generation and verification;
* audit bundle generation;
* producer and consumer conformance tests.

## Non-responsibilities

`l9-assurance` does not own:

* repository scanning;
* file enumeration;
* test execution;
* process execution;
* GitHub workflow orchestration;
* check-run publication;
* repair planning or patching;
* mutation approval;
* rollback;
* CI debt mining;
* rule generation;
* language-server behavior;
* editor code actions.

## Assurance model

The primary processing flow is:

```text
raw producer artifact
    ↓
schema validation
    ↓
producer authorization
    ↓
subject and revision validation
    ↓
integrity validation
    ↓
freshness validation
    ↓
lineage validation
    ↓
policy admissibility
    ↓
accepted evidence
    ↓
control evaluation
    ↓
assurance decision
    ↓
optional attestation and audit bundle
```

## Verdicts

### pass

All applicable mandatory controls passed with admissible evidence.

### fail

At least one mandatory control has valid evidence demonstrating failure.

### indeterminate

A decision cannot be established because required evidence is missing, invalid, stale, unverifiable, unauthorized, or bound to the wrong subject.

### conditional

Mandatory controls are satisfied subject to approved waivers, declared limitations, or policy-approved constraints.

A failed mandatory control always dominates aggregate scores. A numerical confidence value must never convert a failed mandatory control into a pass.

## Core artifacts

### Observation

A producer-generated statement about a check execution.

Typical producers include:

* `l9-ci-sdk`;
* `PR_Repair`;
* `l9-ci-debt-resolver`;
* `l9-ci-debt-intelligence`.

### Evidence envelope

A normalized, integrity-bound wrapper around an observation or other admissible assurance artifact.

### Control result

The result of evaluating one control against admitted evidence.

### Assurance decision

The immutable result for:

* one exact subject;
* one assurance profile;
* one policy version;
* one evidence manifest.

### Attestation

A signed representation of an assurance decision.

## Repository scope

This repository is being narrowed to a protocol and trust-plane architecture.

The intended end-state structure is:

```text
l9-assurance/
├── README.md
├── AGENTS.md
├── MANIFEST.md
├── MANIFEST.sha256
├── ARCHITECTURE.md
├── SPECIFICATION.md
├── ROADMAP.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── package.json
├── pyproject.toml
├── ai-control-plane/
│   ├── AUDIT.md
│   ├── PLAN.md
│   ├── BUILD.md
│   ├── CHANGE.md
│   ├── VALIDATION.md
│   ├── DEFINITION_OF_DONE.md
│   └── RELEASE.md
├── docs/
│   └── AI_CODING_CONTROL_PLANE.md
├── schemas/
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
├── profiles/
├── controls/
├── registry/
├── fixtures/
└── tests/
```

This documentation pack establishes the root architecture contract and the repository-local AI coding control plane. It does not claim that target packages, workflows, schemas, or runtime implementation are already complete.

## Planned command surface

The intended command model is:

```text
l9-assurance plan
l9-assurance evidence admit
l9-assurance evaluate
l9-assurance verify
l9-assurance bundle
l9-assurance conformance
l9-assurance simulate
```

These commands are specification targets. Their presence in documentation does not imply that all commands are implemented.

## Initial integration slice

The first integration target is deliberately narrow:

```text
Subject:
  one Git revision
Producer:
  l9-ci-sdk
Profile:
  l9.pull-request@1
Consumer:
  l9-ci-core
```

The intended flow is:

```text
l9-ci-sdk emits canonical observations
    ↓
l9-assurance admits observations
    ↓
l9-assurance evaluates a pull-request profile
    ↓
l9-ci-core publishes the resulting decision
```

## Repository AI coding control plane

Repository-wide agent behavior is governed by [`AGENTS.md`](AGENTS.md).

The human operating guide is [`docs/AI_CODING_CONTROL_PLANE.md`](docs/AI_CODING_CONTROL_PLANE.md), with canonical stage kernels under [`ai-control-plane/`](ai-control-plane/):

* [`AUDIT.md`](ai-control-plane/AUDIT.md)
* [`PLAN.md`](ai-control-plane/PLAN.md)
* [`BUILD.md`](ai-control-plane/BUILD.md)
* [`CHANGE.md`](ai-control-plane/CHANGE.md)
* [`VALIDATION.md`](ai-control-plane/VALIDATION.md)
* [`DEFINITION_OF_DONE.md`](ai-control-plane/DEFINITION_OF_DONE.md)
* [`RELEASE.md`](ai-control-plane/RELEASE.md)

These files govern how agents work on this repository. They do not broaden the product boundary of `l9-assurance` into execution, repair, orchestration, intelligence, or editor responsibilities.

## Documentation

* [Architecture](ARCHITECTURE.md)
* [Specification](SPECIFICATION.md)
* [Roadmap](ROADMAP.md)
* [Security](SECURITY.md)
* [Contributing](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)
* [Agent operating contract](AGENTS.md)
* [AI coding control plane](docs/AI_CODING_CONTROL_PLANE.md)
* [Manifest](MANIFEST.md)

## Status

This repository is in architectural transition.

The target contract is stable in principle:

```text
Harnesses produce observations.
Assurance converts admissible evidence into governed claims.
```

Implementation details, package boundaries, schemas, and compatibility guarantees remain subject to versioned delivery.
