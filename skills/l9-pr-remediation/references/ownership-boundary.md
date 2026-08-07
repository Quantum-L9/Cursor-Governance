<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: ownership_boundary
tags: [pr, ownership, codebase, ci-pipeline]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-06
/L9_META -->

# Ownership Boundary

Classify before any edit. This skill repairs **codebase** defects only.

## CODEBASE

Defect in source, tests, fixtures, package dependencies, or normal runtime artifacts.

Examples: type errors, implementation bugs, stale fixtures, missing imports, lint/format violations in source, dependency bumps that do not change CI policy, build failures caused by repo code.

## CI_PIPELINE

Repair would change CI orchestration, infra, or enforcement — not compliant code.

Read-only surfaces (never edit here):

- `.github/workflows/**`, `.github/actions/**`, reusable workflows
- action pins, runners, permissions, secrets, OIDC, environments
- branch protection, required-check names, merge queue, check wiring
- CI-only scripts, caches, service containers, centralized CI templates
- contradictory lint/type config when the needed change alters enforcement rather than code
- missing secrets / provisioning / third-party outages

**Action:** cite evidence in the cycle status. Do not edit. Do not emit issue-file bundles or tarballs. Continue every independent codebase cluster.

## HUMAN

Needs product, architecture, legal, or security-exception judgment.

**Action:** name the decision, leave the thread open, finish all independent codebase work.

## FALSE_POSITIVE

Current evidence disproves the signal on the evaluated head.

**Action:** reply with evidence; resolve when appropriate.

## Decision Test

1. Fixable by changing normal source/tests/fixtures/deps without changing how CI is orchestrated?
2. Would the fix touch a CI_PIPELINE surface or policy?
3. Does the same source command fail locally for the same code reason?
4. Is the failure CI-environment / credentials / workflow-expression specific?

Edit only when (1) yes and (2) no. Unknown ownership → do not edit that cluster.

## Mixed Jobs

Split one failed job into multiple root causes. Repair codebase pieces; note pipeline pieces. Never modify CI to expose or bypass a code failure.
