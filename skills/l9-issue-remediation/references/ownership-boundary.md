<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: ownership_boundary
tags: [issues, ownership, codebase, cross-repo]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-30
/L9_META -->

# Ownership Boundary

Classify before any edit. This skill repairs **codebase** defects at the
**obvious owning repo** only.

## CODEBASE

Defect in source, tests, fixtures, package dependencies, or normal runtime
artifacts in a single repo that owns the behavior.

**Action:** fix in that repo; local verify; one commit/push per cycle.

## CROSS_REPO

Same root cause spans multiple Quantum-L9 repos (shared package drift, duplicate
contracts, consumer vs SSOT mismatch). Example: SEO-Bot#5 llm-router divergence.

**Action:** pick owner via [cross-repo-routing.md](cross-repo-routing.md). Fix
once at the owner. Breadcrumb **all** linked issues. Do not patch every consumer
ad hoc.

## CI_PIPELINE

Repair would change CI orchestration, infra, or enforcement.

Read-only surfaces (never edit here): `.github/workflows/**`, action pins,
runners, permissions, secrets wiring, branch protection, required checks.

**Action:** cite evidence; note; continue other clusters.

## HUMAN

Needs product, architecture, legal, or security-exception judgment (e.g. where
PostHog credentials should live).

**Action:** name the decision; breadcrumb; leave issue open; do not fake-close.

## EXTERNAL

Third-party outage, missing org secret provisioning, upstream package registry
auth the agent cannot create (e.g. `NODE_AUTH_TOKEN` grant).

**Action:** document sourcing guidance without inventing secret values; breadcrumb.

## FALSE_POSITIVE

Current evidence disproves the issue on current main.

**Action:** comment with evidence. Close-now law (SKILL.md + issue-verify.md)
wins when verify emits `already-fixed` / `not-reproducible` / `does-not-exist`
/ `duplicate` / `superseded`: close in this turn via `close_resolved_issue.py`
with `--reason` and `--proof`. User confirm is required only when ownership is
FALSE_POSITIVE and verify cannot emit one of those reasons.

## Decision Test

1. Fixable by changing normal source/tests/fixtures/deps?
2. Is there a clearer shared owner than the issue’s repo?
3. Would the fix touch CI_PIPELINE surfaces?
4. Is it HUMAN/EXTERNAL?

Edit only when (1) yes, (3) no, and (4) no. Unknown ownership → do not edit.
