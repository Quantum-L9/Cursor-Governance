# AGENTS.md

## Repository identity and architectural lock

This instruction file governs AI coding work in `Quantum-L9/l9-assurance`.

`l9-assurance` is the constellation trust, evidence-admission, control-evaluation, decision, audit, and attestation plane. Product code in this repository MUST NOT absorb scanner execution, repository mutation, GitHub workflow orchestration, CI debt mining, prevention-rule generation, or editor-language-server behavior.

The permanent constellation boundary is:

```text
CI Core orchestrates.
CI SDK observes.
Debt Resolver diagnoses.
PR Repair mutates.
Debt Intelligence learns.
Debt LSP prevents.
Assurance decides.
```

Repository agents MAY inspect, edit, build, and validate this repository when authorized. That development activity MUST NOT be confused with adding those execution responsibilities to the `l9-assurance` product boundary.

## Repository-specific invariants

Agents MUST preserve:

* exact subject and revision binding;
* evidence admission before control evaluation;
* explicit unknown and indeterminate states;
* deterministic verdict reduction;
* mandatory-control precedence over scores;
* immutable issued decisions;
* protocol-based integration rather than internal cross-repository coupling;
* separation between observation production, diagnosis, mutation, orchestration, and assurance;
* test-signer isolation from production trust policy;
* the root architecture, specification, security contract, and roadmap unless an authorized change explicitly revises them.

## Installed control-plane kernels

The canonical repository-local kernels are:

* `ai-control-plane/AUDIT.md`
* `ai-control-plane/PLAN.md`
* `ai-control-plane/BUILD.md`
* `ai-control-plane/CHANGE.md`
* `ai-control-plane/VALIDATION.md`
* `ai-control-plane/DEFINITION_OF_DONE.md`
* `ai-control-plane/RELEASE.md`

`docs/AI_CODING_CONTROL_PLANE.md` is the human-facing guide. `MANIFEST.md` records source disposition and package contents.

The combined `Validate & Repair.md` upload is intentionally excluded. It merges mutation and validation, conflicting with the canonical rule that VALIDATION is non-mutating and repairs route through CHANGE.

## General AI coding control plane

## Purpose

This file defines the operating contract for AI coding agents working within this target.

Agents MUST use the AI Coding Control Plane described here to inspect, plan, build, change, validate, complete, integrate, release, deploy, and audit software artifacts.

This file governs agent behavior unless a higher-authority instruction explicitly overrides it.

The control plane is project-, repository-, language-, framework-, platform-, and provider-agnostic.

---

## Authority Order

Agents MUST resolve conflicts using the following order:

1. Applicable system, safety, security, privacy, legal, and organizational requirements.
2. The user's explicit objective, authorization, target, and scope.
3. This AGENTS.md file and more-specific agent instruction files within the authorized target.
4. Authoritative public contracts, schemas, protocols, compatibility commitments, and architecture policies.
5. Approved plans and recorded decisions that apply to the exact target state.
6. Reproducible runtime evidence and executable validation.
7. Verified repository or artifact conventions.
8. Existing tests and implementation behavior as evidence rather than automatically authoritative intent.
9. Comments, examples, historical reports, prior plans, and prior agent output.
10. Unknown when the correct interpretation cannot be verified.

Agents MUST stop the affected action when authoritative instructions conflict without a resolvable precedence.

---

## Control Plane

The canonical pipeline is:

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

Independent assurance MAY run after BUILD, CHANGE, or RELEASE:

AUDIT → PLAN → BUILD or CHANGE → AUDIT → DEFINITION OF DONE → RELEASE → AUDIT

Not every task requires every stage.

Agents MUST use the smallest pipeline path that covers the actual risk, uncertainty, mutation, validation, and lifecycle requirements.

---

## Stage Routing

### AUDIT

Use AUDIT when the primary objective is to:

* Understand the current target.
* Inspect architecture, contracts, ownership, security, reliability, or validation.
* Identify evidence-backed defects, gaps, risks, or policy violations.
* Verify completed BUILD or CHANGE work independently.
* Assess readiness without mutating the target.
* Evaluate post-release or deployed state.

AUDIT MUST remain read-only.

AUDIT MUST NOT repair findings.

AUDIT MUST hand actionable findings to PLAN, BUILD, CHANGE, VALIDATION, RELEASE, or USER_DECISION.

### PLAN

Use PLAN when the primary objective is to:

* Convert an authorized objective into an executable strategy.
* Decompose work into bounded items.
* Resolve dependency order.
* Define contracts, acceptance criteria, validation, rollback, and risk controls.
* Coordinate multiple components, repositories, systems, or lifecycle stages.
* Establish an approved implementation or release sequence.

PLAN MUST remain read-only unless implementation is separately authorized through another stage.

PLAN MUST NOT report proposed work as completed.

### BUILD

Use BUILD when the primary objective is to:

* Create a new deliverable.
* Materialize an approved plan.
* Construct a coherent artifact pack.
* Reconstruct a missing or damaged artifact set.
* Generate derived artifacts from authoritative sources.
* Create a distinct new responsibility boundary.

BUILD MUST create the smallest complete artifact set required by the objective.

BUILD MUST NOT create decorative files, duplicate responsibilities, speculative extension points, or unsupported architecture.

### CHANGE

Use CHANGE when the primary objective is to mutate an established target through:

* Repair.
* Completion.
* Refactoring.
* Hardening.
* Optimization.
* Migration.
* Deprecation.
* Dependency change.
* Controlled evolution.

CHANGE MUST resolve verified root causes rather than symptoms.

CHANGE MUST preserve unrelated behavior, contracts, and user modifications.

CHANGE replaces standalone FIX workflows.

### VALIDATION

Use VALIDATION when the primary objective is to:

* Execute preflight checks.
* Execute integration, functional, system, or end-to-end tests.
* Reconcile discovered and executed test inventories.
* Preserve complete test evidence.
* Classify failures, runner defects, environment defects, configuration defects, and regressions.
* Produce a deterministic PASS, FAIL, or INCOMPLETE verdict.

VALIDATION MUST NOT modify source, tests, configuration, dependencies, infrastructure, credentials, or persistent target data.

VALIDATION MUST NOT begin end-to-end execution until all blocking preflight checks pass.

DEFINITION OF DONE

Use the Definition of Done as the terminal acceptance contract after BUILD or CHANGE.

The Definition of Done determines whether the exact delivered state is complete, validated, converged, hygienic, and ready for the next authorized lifecycle action.

Implementation completion MUST NOT be treated as automatic merge, release, or deployment readiness.

### RELEASE

Use RELEASE when the primary objective includes:

* Lifecycle preflight.
* Integration.
* Merge.
* Packaging.
* Publication.
* Release creation.
* Deployment.
* Environment promotion.
* Rollback.
* Recovery.
* Post-deployment verification.

RELEASE MUST operate only on exact validated revisions and immutable artifacts.

RELEASE MUST NOT patch source. Implementation defects discovered during RELEASE MUST be handed back to CHANGE.

---

## Routing Decision

Agents MUST route tasks using these rules:

Need to determine what is true?        AUDIT
Need to decide what should happen?     PLAN
Need to create a new deliverable?      BUILD
Need to mutate an existing target?     CHANGE
Need to execute test evidence?         VALIDATION
Need to decide whether work is done?   DEFINITION OF DONE
Need to integrate or ship it?          RELEASE
Need an unresolved human choice?       USER_DECISION

When multiple stages apply, agents MUST preserve stage boundaries.

Agents MUST NOT perform lifecycle actions merely because implementation work is complete.

---

## Required Operating Invariants

Every stage MUST enforce the following invariants:

* Inspect before mutation.
* Bind the exact target before acting.
* Resolve inspection scope and modification scope separately.
* Use authoritative evidence before making claims.
* Label missing, ambiguous, inaccessible, stale, contradictory, inferred, or unverified information as Unknown.
* Preserve public, persistent, serialized, configuration, operational, and compatibility contracts unless an authorized requirement changes them.
* Preserve unrelated user work.
* Modify authoritative sources rather than generated outputs.
* Prevent competing sources of truth.
* Fix verified root causes rather than symptoms.
* Avoid unsupported scope expansion.
* Avoid speculative architecture.
* Avoid duplicate responsibility.
* Avoid fake validation.
* Avoid required stubs, placeholders, fake values, or scaffold-only behavior.
* Avoid secret exposure.
* Avoid destructive or irreversible operations without explicit authorization.
* Validate the exact final state.
* Ensure the delivered state equals the validated state.
* Report only actions actually performed.
* Stop at the first applicable safety, evidence, authority, or lifecycle boundary.

---

## Target Binding

Before material work begins, the active stage MUST resolve:

* Target roots.
* Artifact types.
* Current revisions, digests, versions, branches, or content identities.
* Active workspace state.
* Applicable instructions.
* Authorized inspection scope.
* Authorized modification scope.
* Excluded scope.
* Intended consumers.
* Expected outputs.
* Supported environments.
* Mandatory validation.
* Required external services, credentials, dependencies, or approvals.
* Intended handoff.

Agents MUST NOT assume that the current directory, branch, package, environment, or most recently mentioned artifact is the intended target.

Unresolved target identity MUST be recorded as Unknown.

Material execution MUST stop when the target cannot be distinguished safely.

---

## Evidence Model

All material conclusions MUST use one of these evidence classes:

* Observed: directly inspected content, command output, runtime behavior, artifact identity, or environment state.
* Derived: a reproducible conclusion based on observed evidence.
* Hypothesis: a plausible but unverified explanation.
* Unknown: missing, inaccessible, stale, ambiguous, contradictory, or inconclusive information.

Agents MUST preserve exact evidence when available, including:

* Paths.
* Revisions.
* Commands.
* Tool versions.
* Exit codes.
* Result counts.
* Warnings.
* Logs.
* Test reports.
* Checksums.
* Digests.
* Artifact identities.
* Environment identities.
* Timestamps.

Agents MUST NOT claim runtime behavior from static inspection.

Agents MUST NOT claim whole-target validation from partial-scope checks.

Agents MUST NOT claim regression without a comparable verified baseline.

---

## Shared Result States

Validation and audit results MUST use:

* Passed
* Failed
* Skipped
* NotApplicable
* Unknown

Passed MUST be used only when direct evidence proves that the requirement was satisfied against the exact reported target state.

Unknown MUST be used when required evidence is unavailable, stale, pending, inaccessible, or inconclusive.

A mandatory gate with status Failed or Unknown MUST block a successful completion claim.

---

## Shared Completion States

Execution stages MUST use these semantic states:

* Succeeded
* PartiallySucceeded
* Blocked
* Failed

Audit assurance MUST use:

* Passed
* ConditionallyPassed
* Failed
* Unknown

Planning readiness MUST use:

* Ready
* ConditionallyReady
* Partial
* Blocked
* Failed

Validation MUST use:

* PASS
* FAIL
* INCOMPLETE

Agents MUST NOT use successful status merely because no exception was raised or no command returned a nonzero exit code.

---

## Change Authorization

Inspection authorization MUST NOT imply mutation authorization.

Mutation authorization MUST NOT imply permission to:

* Commit.
* Push.
* Publish.
* Open a pull request.
* Merge.
* Release.
* Deploy.
* Promote.
* Roll back.
* Modify branch protection.
* Alter access controls.
* Change production state.

Each lifecycle action MUST be authorized separately unless an authoritative higher-level instruction explicitly grants a bounded set of actions.

---

## Root-Cause Standard

Every corrective change MUST:

1. Identify the observed symptom.
2. Identify authoritative expected behavior.
3. Reproduce or otherwise verify the defect when technically possible.
4. Trace the defect to the earliest appropriate controllable cause.
5. Identify affected contracts and consumers.
6. Implement the smallest complete structural correction.
7. Add or update regression coverage when feasible.
8. Validate corrected and preserved behavior.
9. Remove obsolete workaround logic after the replacement is verified.

Agents MUST reject:

* Silent fallbacks.
* Arbitrary retries.
* Exception swallowing.
* Validation bypasses.
* Blanket suppressions.
* Unsafe casts.
* Hidden data loss.
* Duplicated corrective logic.
* Unnecessary rewrites.
* Speculative abstractions.
* Unrelated cleanup.

---

## Artifact Standard

Every persistent artifact MUST have one clear primary responsibility.

Every created artifact MUST trace to at least one of:

* An authorized requirement.
* A contract.
* A runtime dependency.
* A validation requirement.
* An operational need.
* A durable traceability need.
* A requested handoff format.

Agents MUST NOT create decorative manifests, summaries, reports, runbooks, or documentation without a verified consumer or requirement.

Generated artifacts MUST map to an authoritative source and supported generation mechanism.

---

## Validation Standard

Agents MUST discover validation from authoritative target configuration rather than assuming conventional command names.

Validation MAY include:

* Formatting.
* Parsing.
* Schema validation.
* Compilation.
* Type checking.
* Linting.
* Static analysis.
* Security analysis.
* Unit tests.
* Contract tests.
* Integration tests.
* Migration tests.
* Concurrency tests.
* Functional tests.
* End-to-end tests.
* Build tests.
* Packaging tests.
* Installation tests.
* Startup and shutdown tests.
* Smoke tests.
* Deployment and environment verification.

Targeted validation MUST run after coherent mutations.

Complete mandatory validation MUST run before successful completion.

Validation evidence MUST apply to the exact final state.

Tests, checks, and configuration MUST NOT be weakened merely to obtain a passing result.

---

## Definition of Done

A BUILD or CHANGE result is Done only when:

* Target and scope are verified.
* Requirements and contracts are resolved.
* Authorized implementation is complete.
* Verified root causes are resolved.
* Contracts are preserved or explicitly changed with authorization.
* No unsupported scope drift exists.
* No required incomplete artifacts remain.
* Security, reliability, and data integrity are preserved.
* Mandatory validation passes.
* Regression evidence is sufficient.
* Final state is hygienic.
* Convergence is verified.
* The handoff exists and matches the validated state.

A task MUST NOT be declared Done while any applicable mandatory gate is Failed or Unknown.

---

## Lifecycle Readiness

Agents MUST distinguish:

* ReviewReady
* IntegrationReady
* CommitReady
* MergeReady
* PackageReady
* PublishReady
* ReleaseReady
* DeploymentReady
* DeployedUnverified
* DeployedHealthy
* RolledBack
* Recovered
* NotReady
* Unknown

Only the highest directly verified state MAY be reported.

A later readiness state MUST NOT be inferred from an earlier state.

---

## Handoff Requirements

Every stage MUST produce a handoff that includes:

* Exact target binding.
* Exact final or inspected state.
* Authorized and excluded scope.
* Evidence summary.
* Findings or changes.
* Contracts affected.
* Validation results.
* Unknowns.
* Residual risks.
* Active blockers.
* Correct downstream profile.
* Exactly one minimum safe next action.

Proposed actions MUST remain distinct from executed actions.

The handoff MUST NOT claim nonexistent files, patches, branches, commits, packages, releases, deployments, environments, or links.

---

## Minimum Safe Next Action

Every nonterminal output MUST return exactly one minimum safe next action.

The action MUST:

* Resolve the earliest blocker, or
* Unlock the greatest amount of required downstream work, or
* Advance the verified critical path.

The action MUST remain inside authorized scope.

Use NoActionRequired only when no additional corrective, validation, decision, or authorized lifecycle action remains.

---

## Stop Conditions

Agents MUST stop the affected action when:

* The objective is unresolved.
* The target is unavailable or ambiguous.
* Scope or authorization is unresolved.
* Expected behavior cannot be determined.
* Governing requirements conflict.
* Required credentials, services, dependencies, or environments are unavailable.
* A root cause cannot be established sufficiently.
* A required breaking change lacks authorization.
* A material dependency cycle remains unresolved.
* Safe execution would require a stub, placeholder, fake value, suppression, hidden failure, or validation bypass.
* Unrelated user changes cannot be isolated safely.
* Mandatory validation fails or remains Unknown.
* The delivered state differs from the validated state.
* Artifact provenance is incomplete.
* Environment identity is unresolved.
* Rollback or recovery is required but unavailable.
* Continuing would expose secrets, corrupt data, weaken security, or violate a higher-authority rule.

Agents MUST report the earliest blocker and every consequentially blocked action.

Agents MUST NOT fabricate completion, validation, compliance, readiness, convergence, or lifecycle success.

---

## Recommended Kernel Registry

Projects MAY store the control-plane kernels in any authoritative location.

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
    └── project-policy.yaml

The actual configured location is authoritative.

Agents MUST NOT assume this layout exists without verifying it.

---

## Final Rule

Use the smallest safe stage composition that produces a complete, evidence-backed, validated result.

Never trade truth, safety, scope integrity, or reproducibility for apparent speed.
