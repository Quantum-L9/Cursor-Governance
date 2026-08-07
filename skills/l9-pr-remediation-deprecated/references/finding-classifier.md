<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: finding_classifier
tags: [pr, classification, ownership, ci-signal, validation, confidence-gate]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-07-28
/L9_META -->

# Finding Classifier and Validation Doctrine

## Purpose

Classify ownership before severity or fix strategy. Review and CI signals are claims to validate, not permission to edit.

## First Axis: Repair Ownership

| Ownership | Meaning | Allowed action |
|---|---|---|
| `CODEBASE_REPAIR` | Defect is in source, tests, fixtures, package dependencies, or normal repository behavior | Validate, repair, verify, commit |
| `CI_PIPELINE_SIGNAL` | Defect is in workflow orchestration, shared CI, runner, action, permission, secret, OIDC, policy, check wiring, cache, service, or CI-only configuration | Render one issue file per root cause; no repair |
| `HUMAN_DECISION` | Product, architecture, security-exception, legal, or business decision is required | Reply, keep open, escalate |
| `FALSE_POSITIVE` | Current evidence disproves or supersedes the signal | Reply with evidence; no edit |

Load `ci-signal-boundary.md` for the normative decision test. Ownership must be established before assigning a disposition.

## Second Axis: Severity

| Severity | Definition | Action |
|---|---|---|
| `blocking` | Prevents PR readiness | Repair only if ownership is `CODEBASE_REPAIR`; otherwise signal or escalate |
| `actionable` | Clear validated codebase change | Fix after blocking codebase items |
| `discussion` | Question or alternative proposal | Acknowledge; no mutation |
| `deferred` | Safe action is outside current codebase scope | Record reason and handoff |

## Third Axis: Disposition

| Disposition | Meaning |
|---|---|
| `AUTO_APPLY` | Deterministic, safe, codebase-owned change |
| `VALIDATE` | Plausible codebase change requiring current-code proof |
| `SIGNAL_CI` | CI-pipeline-owned root cause; issue-file handoff only |
| `DEFER` | Correct but out of codebase scope or below confidence |
| `IGNORE` | False positive, already handled, or discussion |
| `HUMAN_DECISION` | Irreducible human choice |

`SIGNAL_CI` is incompatible with `AUTO_APPLY` or `VALIDATE`.

## CI Failure Ownership Examples

| Evidence | Ownership | Action |
|---|---|---|
| linter reports a source violation and the configured rule is valid | `CODEBASE_REPAIR` | fix source |
| type checker reports an implementation type mismatch | `CODEBASE_REPAIR` | fix source/types |
| tests fail because implementation is wrong | `CODEBASE_REPAIR` | fix code first |
| package build fails from missing source import | `CODEBASE_REPAIR` | fix code/package metadata |
| workflow expression, reusable-workflow input, or action pin is wrong | `CI_PIPELINE_SIGNAL` | issue file |
| runner image lacks a tool or uses the wrong runtime | `CI_PIPELINE_SIGNAL` | issue file |
| secret, permission, OIDC, environment, or branch-protection mismatch | `CI_PIPELINE_SIGNAL` | issue file |
| cache, service container, external scanner, or CI vendor is unavailable | `CI_PIPELINE_SIGNAL` | issue file |
| quality config is invalid or CI invokes it inconsistently | `CI_PIPELINE_SIGNAL` | issue file; do not relax config |
| dependency vulnerability is fixed by a normal package update | `CODEBASE_REPAIR` | update dependency and verify |
| security scanner policy or pipeline integration is wrong | `CI_PIPELINE_SIGNAL` | issue file |

## Validation Doctrine

Read the actual current file and exact failing command. Reject or reroute a suggestion when it:

- references code that no longer exists;
- would break a passing gate or introduce a compile/type error;
- contradicts a valid repository convention;
- proposes changing CI rather than correcting code;
- changes enforcement to hide a defect;
- touches a signal-only surface;
- conflicts with higher-authority evidence;
- requires ownership or intent that is not established.

Never silently skip. Record evidence and a reason.

## Confidence Gate

Assign each `VALIDATE` codebase finding a confidence score from 0.0 to 1.0. If confidence is below `confidence_gate` (default 0.75), reclassify as `DEFER`. Confidence does not convert a CI-pipeline finding into a codebase finding.

For bot reviewers:

```text
effective_gate(reviewer) = clamp(confidence_gate + 0.30 * fp_rate, 0.60, 0.90)
```

Human suggestions retain authority precedence but still require ownership validation.

## Root-Cause Grouping for CI Signals

Normalize every `CI_PIPELINE_SIGNAL`, then group only identical causal mechanisms and owning surfaces. One root cause produces one fingerprint and one issue file. Multiple symptoms from one runner-image defect may share a file. A runner-image defect and a permissions defect require separate files even when they fail the same job.

## Conflict Resolution

Use this order:

1. latest explicit user instruction;
2. current source and tests;
3. valid codebase configuration;
4. required-check evidence;
5. human review;
6. blocking automated review;
7. higher confidence;
8. more recent signal;
9. unknown.

A CI system may prove a failure exists, but it does not expand this Skill's mutation authority.

## Mandatory Output Per Finding

```yaml
id: stable-id
ownership: CODEBASE_REPAIR | CI_PIPELINE_SIGNAL | HUMAN_DECISION | FALSE_POSITIVE
severity: blocking | actionable | discussion | deferred
disposition: AUTO_APPLY | VALIDATE | SIGNAL_CI | DEFER | IGNORE | HUMAN_DECISION
confidence: 0.0
current_evidence: []
reason: string
root_cause_fingerprint: string | null
```
