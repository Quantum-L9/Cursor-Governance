# AI Coding Control Plane

## Overview

The AI Coding Control Plane is a reusable operating system for AI-assisted software work.

It separates software work into seven explicit responsibilities:

AUDIT
  ↓
PLAN
  ↓
BUILD or CHANGE
  ↓
VALIDATION
  ↓
DEFINITION OF DONE
  ↓
RELEASE

The pipeline is designed to prevent common AI coding failure modes:

* Editing before understanding the target.
* Solving symptoms rather than root causes.
* Expanding scope without authorization.
* Creating unnecessary files or architecture.
* Claiming tests passed when they were not run.
* Treating partial validation as complete validation.
* Confusing implementation completion with release readiness.
* Shipping a different state from the one that was validated.
* Hiding unresolved information instead of labeling it Unknown.

The control plane is language-, framework-, repository-, platform-, and provider-agnostic.

---

## Why the Pipeline Is Split

AI coding systems often combine analysis, planning, implementation, testing, and release into one opaque operation.

That creates several problems:

* The agent changes the evidence while auditing it.
* Plans are reported as completed work.
* Implementation agents perform release actions without lifecycle authorization.
* Test failures are repaired by weakening tests.
* New deliverables and modifications to existing systems become conflated.
* Readiness claims exceed the evidence.

The control plane assigns each responsibility to a distinct stage.

| Stage | Primary responsibility | Mutates target |
|---|---|---|
| AUDIT | Determine what is true | No |
| PLAN | Determine what should happen and in what order | No |
| BUILD | Create a new deliverable | Yes |
| CHANGE | Mutate an established deliverable | Yes |
| VALIDATION | Execute and preserve test evidence | No |
| DEFINITION OF DONE | Decide whether the result is complete | No |
| RELEASE | Integrate, package, publish, release, deploy, or recover | Lifecycle state only |

The stages share one evidence model, one Unknown policy, one validation vocabulary, and one traceability standard.

---

## Pipeline Stages

### AUDIT

AUDIT is the independent assurance stage.

Use it to:

* Understand an unfamiliar target.
* Resolve architecture and ownership boundaries.
* Inspect contracts, schemas, configuration, security, reliability, and validation.
* Identify evidence-backed defects, gaps, risks, and violations.
* Verify BUILD or CHANGE work independently.
* Assess merge, release, deployment, or operational readiness.
* Review deployed state after RELEASE.

AUDIT does not modify the target.

Its main outputs are:

* Target and scope binding.
* Authority and policy map.
* Artifact inventory.
* Boundary map.
* Evidence manifest.
* Domain assessments.
* Findings.
* Root-cause groups.
* Unknowns.
* Correction roadmap.
* Readiness conclusion.
* Downstream handoff.

---

### PLAN

PLAN converts an objective and verified context into an executable strategy.

Use it when work requires:

* Dependency ordering.
* Multiple workstreams.
* Architecture decisions.
* Contract changes.
* Migration sequencing.
* Rollback design.
* Validation design.
* Risk controls.
* Human approvals.
* Multi-repository coordination.
* Release sequencing.

A plan item should contain:

* Objective.
* Rationale.
* Ownership boundary.
* Affected artifacts.
* Prerequisites.
* Actions.
* Preserved invariants.
* Acceptance criteria.
* Validation.
* Rollback or recovery.
* Risk.
* Effort classification.
* Uncertainty.
* Parallelization status.
* Postconditions.

PLAN does not implement its own plan.

---

### BUILD

BUILD creates or materializes a deliverable.

Use BUILD for:

* Greenfield systems.
* New packages, services, libraries, tools, plugins, or workflows.
* New artifact packs.
* Reconstruction of incomplete artifact groups.
* Plan materialization.
* Derived artifact generation.
* Creation of a distinct new responsibility boundary.

BUILD creates only artifacts that are required for:

* Runtime behavior.
* Contracts.
* Validation.
* Integration.
* Operations.
* Traceability.
* Delivery.

BUILD avoids decorative manifests, duplicate summaries, speculative abstractions, and placeholder files.

---

### CHANGE

CHANGE replaces standalone FIX workflows.

Use CHANGE to modify an established target through:

* Repair.
* Completion.
* Refactoring.
* Hardening.
* Optimization.
* Migration.
* Deprecation.
* Dependency changes.
* Controlled evolution.

CHANGE requires:

* A verified target.
* Expected behavior.
* A bounded scope.
* Evidence-backed findings or requirements.
* Root-cause analysis.
* Contract-impact analysis.
* Incremental validation.
* Complete final validation.
* Convergence.
* A verified handoff.

CHANGE does not perform merge, release, or deployment actions.

---

### VALIDATION

VALIDATION is the non-mutating execution stage for test and preflight evidence.

Use it to execute:

* Environment preflight.
* Dependency checks.
* Credential and endpoint checks.
* Integration tests.
* Functional tests.
* System tests.
* End-to-end tests.
* Environment-specific validation.

The preflight gate is strict:

All blocking preflight checks pass
                ↓
       E2E execution may begin

VALIDATION accounts for every discovered item as one of:

* Passed.
* Failed.
* Error.
* Timeout.
* Blocked.
* Not Executed.
* Authoritatively Skipped.
* Unknown.

Its final verdict is:

* PASS
* FAIL
* INCOMPLETE

VALIDATION preserves raw evidence and does not repair the implementation under test.

---

### Definition of Done

The Definition of Done is the shared terminal acceptance contract.

It determines whether BUILD or CHANGE work is actually complete.

A result is Done only when:

* Target and scope are verified.
* Requirements are resolved.
* Implementation is complete.
* Root causes are resolved.
* Contracts are preserved or authorized.
* No scope drift exists.
* No required incomplete artifacts remain.
* Security, reliability, and data integrity are preserved.
* Mandatory validation passes.
* Regression protection is sufficient.
* Final state is clean.
* Convergence is verified.
* Handoff matches the validated state.

The Definition of Done does not automatically grant merge, release, or deployment readiness.

---

### RELEASE

RELEASE owns lifecycle transitions.

Use it for:

* Lifecycle preflight.
* Isolated integration.
* Merge.
* Packaging.
* Publication.
* Release records.
* Deployment.
* Promotion.
* Rollback.
* Recovery.
* Post-deployment verification.

RELEASE verifies:

* Exact candidate revisions.
* Exact integration targets.
* Required checks.
* Check freshness.
* Required approvals.
* Merge order.
* Immutable artifact identity.
* Source-to-artifact provenance.
* Publication destination.
* Environment identity.
* Active execution identity.
* Migration state.
* Health criteria.
* Rollback or recovery readiness.

RELEASE does not patch source.

Defects discovered during RELEASE return to CHANGE.

---

## Common Pipeline Paths

Small bounded change

CHANGE
  ↓
DEFINITION OF DONE

Use this for an explicit, low-risk change with straightforward validation.

Normal multi-file change

PLAN
  ↓
CHANGE
  ↓
VALIDATION
  ↓
DEFINITION OF DONE

High-risk change

AUDIT
  ↓
PLAN
  ↓
CHANGE
  ↓
AUDIT
  ↓
VALIDATION
  ↓
DEFINITION OF DONE

New deliverable

PLAN
  ↓
BUILD
  ↓
VALIDATION
  ↓
DEFINITION OF DONE

High-risk new deliverable

AUDIT
  ↓
PLAN
  ↓
BUILD
  ↓
AUDIT
  ↓
VALIDATION
  ↓
DEFINITION OF DONE

Release

BUILD or CHANGE
       ↓
DEFINITION OF DONE
       ↓
RELEASE

Release with independent assurance

BUILD or CHANGE
       ↓
AUDIT
       ↓
DEFINITION OF DONE
       ↓
RELEASE
       ↓
AUDIT

---

## Router

A simple router can select the correct stage:

route:
  inspect_or_assess: AUDIT
  design_or_sequence: PLAN
  create_new_deliverable: BUILD
  mutate_existing_target: CHANGE
  execute_tests_or_preflight: VALIDATION
  determine_completion: DEFINITION_OF_DONE
  integrate_or_ship: RELEASE
  unresolved_human_choice: USER_DECISION

The router should select the smallest safe composition rather than loading every kernel for every task.

---

## Adaptive Depth

Each kernel supports adaptive execution depth.

Typical depth levels are:

* Quick: small, bounded, low-risk work.
* Standard: normal multi-file work.
* Deep: architecture, security, migration, shared-contract, or multi-system work.
* Critical: production, regulated, irreversible, broad-impact, or severe-risk lifecycle work.

The shallowest depth that covers all material risk should be used.

Depth should increase when the work introduces:

* Security impact.
* Persistent-data impact.
* Shared contracts.
* Multiple repositories.
* Production or production-like environments.
* Irreversible operations.
* Broad compatibility impact.
* Complex rollback.
* Significant uncertainty.

---

## Shared Evidence Model

Every kernel uses the same evidence classes:

evidence_classes:
  Observed:
    meaning: "Directly inspected or executed evidence."
  Derived:
    meaning: "A reproducible conclusion based on observed evidence."
  Hypothesis:
    meaning: "A plausible explanation that still requires verification."
  Unknown:
    meaning: "Missing, inaccessible, stale, ambiguous, contradictory, or inconclusive information."

Unknown is not a failure to reason.

It is a required state that prevents invented certainty.

---

## Shared Validation States

All checks use:

validation_states:
  - Passed
  - Failed
  - Skipped
  - NotApplicable
  - Unknown

A mandatory result that is Failed or Unknown blocks successful completion.

Static inspection cannot be reported as runtime validation.

Partial checks cannot be reported as whole-target validation.

---

## Shared Traceability

The pipeline maintains traceability across stages:

Requirement
  ↓
Finding or Plan Item
  ↓
Build or Change
  ↓
Artifact
  ↓
Validation
  ↓
Definition of Done Gate
  ↓
Lifecycle Readiness
  ↓
Release Artifact or Environment State

A material change should be traceable to:

* A requirement.
* A finding.
* A plan item.
* An affected artifact.
* A contract impact.
* Closing validation.
* Final readiness.

---

## Shared Objects

Implementations may use shared schemas for interoperability.

Target context

target_context:
  roots: []
  artifact_types: []
  revisions: []
  objective: ""
  inspection_scope: []
  modification_scope: []
  excluded_scope: []
  authority_sources: []
  environment: Unknown

Finding

finding:
  id: ""
  category: ""
  severity: "Critical | High | Medium | Low"
  confidence: "Confirmed | Probable | Possible | Unknown"
  evidence: []
  expected_behavior: ""
  observed_behavior: ""
  root_cause: Unknown
  affected_artifacts: []
  status: "Open | Resolved | Blocked | FalsePositive | OutOfScope | Unknown"

Validation result

validation_result:
  id: ""
  action: ""
  target_state: ""
  result: "Passed | Failed | Skipped | NotApplicable | Unknown"
  evidence: []
  warnings: []

Unknown

unknown:
  id: ""
  description: ""
  reason: ""
  affected_decisions: []
  minimum_resolution_evidence: ""
  blocks_execution: false
  blocks_completion: false

Handoff

handoff:
  form: "files | patch | tree | commit | pull_request | package | deployment"
  artifacts: []
  revision: Unknown
  validated_revision: Unknown
  integrity_verified: false

---

## Recommended Layout

The pipeline may be stored anywhere authoritative to the project.

A recommended layout is:

ai-control-plane/
├── AUDIT.yaml
├── PLAN.yaml
├── BUILD.yaml
├── CHANGE.yaml
├── VALIDATION.yaml
├── DEFINITION_OF_DONE.yaml
├── RELEASE.yaml
└── adapters/
    ├── architecture-policy.yaml
    ├── security-policy.yaml
    └── lifecycle-policy.yaml

Repository-wide instructions can be placed in:

AGENTS.md

Project-specific policies should be adapters rather than modifications to the generic kernels.

---

## Policy Adapters

Adapters let the generic pipeline enforce target-specific rules.

Examples include:

* Architecture ownership laws.
* Message or transport contracts.
* Schema requirements.
* Security policies.
* Regulatory controls.
* Source-of-truth rules.
* Release and deployment policies.
* Required metadata.
* Repository structure rules.

An adapter should define:

policy_adapter:
  id: ""
  version: Unknown
  governing_source: ""
  applies_to: []
  mandatory_rules: []
  prohibited_patterns: []
  ownership_rules: []
  contract_rules: []
  security_rules: []
  validation_methods: []
  release_blocking_rules: []

Adapters should be loaded only when their applicability is verified.

---

## Stage Handoffs

Each stage should hand off structured evidence rather than only narrative.

AUDIT to PLAN or CHANGE

Include:

* Findings.
* Governing rules.
* Evidence.
* Root causes or hypotheses.
* Boundaries.
* Dependencies.
* Unknowns.
* Closing validation.

PLAN to BUILD or CHANGE

Include:

* Ordered plan items.
* Workstreams.
* Execution waves.
* Contracts.
* Acceptance criteria.
* Validation matrix.
* Rollback or recovery.
* Decisions and blockers.

BUILD or CHANGE to Definition of Done

Include:

* Exact final artifact set.
* Requirements implemented.
* Contracts preserved or changed.
* Validation results.
* Regression assessment.
* Residual risks.
* Convergence evidence.

Definition of Done to RELEASE

Include:

* Exact validated revision.
* Completion gates.
* Highest readiness state.
* Required checks.
* Compatibility and migration information.
* Artifact or packaging requirements.
* Residual risks.

RELEASE to AUDIT

Include:

* Source revision.
* Integrated revision.
* Immutable artifact identity.
* Publication references.
* Environment identity.
* Deployment result.
* Health evidence.
* Rollback or recovery state.

---

## Status and Readiness

Execution status and lifecycle readiness are separate.

An implementation may be:

change_status: Succeeded
lifecycle_readiness: ReviewReady

This does not mean:

merge_ready: true
release_ready: true
deployment_ready: true

Later readiness states require their own evidence.

The pipeline should always report the highest state directly supported by evidence.

---

## Safety Model

The pipeline is safe by default.

It does not assume authorization to:

* Write files.
* Commit.
* Push.
* Publish.
* Merge.
* Release.
* Deploy.
* Promote.
* Roll back.
* Modify production data.
* Change branch protection.
* Change permissions.
* Access or expose secrets.

Each action must be explicitly authorized or governed by an authoritative higher-level workflow.

---

## Convergence

A stage has converged when:

* Required scope is covered.
* Material findings are reconciled.
* Required implementation is complete.
* Mandatory validation passes.
* No unresolved Critical or High blocker remains.
* Contracts and ownership are coherent.
* Unknowns are explicit.
* Another pass has no concrete material objective.

A fixed pass count does not prove convergence.

Repeated identical output does not prove convergence.

Convergence is an evidence-backed state.

---

## Minimal-Effort, Maximum-Leverage Principles

The control plane favors:

* Shared root-cause fixes over repeated local patches.
* Clear contracts over duplicated conventions.
* Executable checks over repeated manual review.
* Existing authoritative mechanisms over new infrastructure.
* Deletion of unnecessary work over automation of unnecessary work.
* Small complete changes over broad rewrites.
* Conditional supporting artifacts over mandatory report sprawl.
* Adaptive depth over ceremonial process.
* One shared evidence vocabulary over per-prompt reporting formats.

The pipeline should remain rigorous without becoming bureaucratic.

---

## Getting Started

For a new task:

1. Bind the exact target and objective.
2. Route the task to the correct stage.
3. Select the minimum safe depth.
4. Load only applicable policy adapters.
5. Execute the stage contract.
6. Preserve evidence.
7. Hand off to the next required stage.
8. Apply the Definition of Done before lifecycle progression.
9. Use RELEASE only for explicitly authorized lifecycle actions.

A typical request such as:

Repair the failing authentication flow and prepare it for review.

routes to:

PLAN
  ↓
CHANGE
  ↓
VALIDATION
  ↓
DEFINITION OF DONE

A request such as:

Assess whether this release candidate is safe to deploy.

routes to:

AUDIT
  ↓
VALIDATION
  ↓
AUDIT readiness conclusion

A request such as:

Deploy the approved immutable artifact to the verified staging environment.

routes to:

### RELEASE

provided that authorization, Definition of Done, artifact provenance, environment identity, preflight, and rollback readiness are already verified.

---

## Guiding Principle

The AI Coding Control Plane optimizes for one outcome:

Produce the strongest complete result supported by evidence, while preserving scope, contracts, safety, traceability, and truthful lifecycle state.

The pipeline should never trade correctness or evidence integrity for the appearance of speed.
