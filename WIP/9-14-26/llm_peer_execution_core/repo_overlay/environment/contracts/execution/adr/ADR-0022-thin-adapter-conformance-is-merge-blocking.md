# ADR-0022: Thin-Adapter Conformance Is Merge-Blocking

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

A doctrine that is only prose will drift. The current adapter gap emerged because shared behavior could accumulate inside one provider without a gate forcing extraction upstream.

## Decision

Thin-adapter conformance is a merge-blocking architecture check for peer/provider execution changes.

Validation MUST prove:

1. adapters contain no Program-state, lease, worktree, verification, convergence, memory, deployment, or autonomy authority;
2. agent identity resolves from peer bindings rather than provider implementation ownership;
3. canonical request/result contracts are used at the provider boundary;
4. a shared transport is reused when an existing transport matches the provider;
5. duplicate reusable execution behavior is absent from provider directories;
6. provider unavailability produces `BLOCKED` or `CAPABILITY_UNSUPPORTED` without corrupting Program state;
7. adding a provider does not introduce provider-specific branches into Program Controller, canonical receipts, change IR, memory, or autonomy;
8. provider-specific exceptions have an accepted ADR and remain non-authoritative.

The conformance implementation MAY combine schema validation, AST/import checks, forbidden-pattern scans, fixture providers, and end-to-end tests. Validation evidence, not file naming, determines compliance.

## Required regression fixtures

At least two synthetic or real thin providers must be exercisable through the same canonical lifecycle in conformance tests. Their outputs may differ, but lifecycle semantics, authority boundaries, error handling, receipt creation, and Program-state behavior must remain identical.

## Consequences

- Architecture drift becomes a test failure instead of a future cleanup project.
- Provider additions remain small by construction.
- Shared capability improvements compound across all peers.
- An adapter PR cannot quietly create another execution plane.

## Rejected alternatives

### Documentation-only enforcement

Rejected because it already proved insufficient.

### Line-count limits

Rejected because small files can still own forbidden authority and legitimate provider translation size varies. Conformance checks responsibility, not cosmetics.
