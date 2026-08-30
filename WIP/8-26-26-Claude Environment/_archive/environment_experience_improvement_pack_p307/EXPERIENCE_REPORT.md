# Environment Experience Improvement Pack — Canonical Report

## Executive state

Nine unique environment-experience packs were confirmed in the accessible corpus. Two additional archives are byte-identical reuploads of Packs 1 and 2. The family is not a linear nine-revision document: it is a series of parallel observations across repositories and sessions. Pack 9 explicitly supersedes an archive generated at 2026-08-24T01:18Z, but exact byte identity with accessible Pack 3 remains unproven because the reported archive sizes differ.

The recurring architecture problem is fragmentation of authority and health: repository ownership, environment-variable provenance, interpreter/toolchain selection, bootstrap receipt freshness, GitHub transport capability, MCP/broker exposure, and memory continuity are each represented too coarsely or by multiple owners. This produces false "invalid", "degraded", or "ready" states and forces repeated archaeology.

## Highest-confidence converged findings

- Bootstrap must not project over consumer-owned tracked paths. Pack 9 converts the older generic gitignore advice into an ownership-aware rule.
- GitHub REST and GraphQL are separate capabilities. `gh auth status` or a blanket `gh unavailable` claim is not a safe health model on these surfaces.
- Bootstrap receipts must be lifecycle/revision bound and must re-probe degraded components.
- Authority-sensitive drift cannot be silently corrected without an explicit policy value. `L9_AUTONOMY_AUTONOMOUS_MERGE` remains an open policy decision.
- A one-time breakglass grant requires issuer/scope/expiry semantics; a persistent string is not acceptable evidence of exceptional authority.
- Toolchain readiness must resolve the project interpreter and prove importability, not just binary presence.
- Memory continuity must distinguish transport health, writeback outcome, and task-bearing hydration.
- Safety guardrails remain fail-closed for ambiguous destructive paths; the repair is better diagnostics and reachable scoped authorization, not weaker safety.

## Canonical surfaces

See `ARCHITECTURE.md`, `LAWS_AND_INVARIANTS.md`, `failures.yaml`, `friction.yaml`, and `improvements.yaml` for the active reconciled model. Source-level traceability and every source-object disposition live under `_reconciliation/`.

## Current status

The pack is **reconciled with explicit open decisions**. The canonical architecture and current roadmap are stable; unresolved policy/cause questions are isolated in `OPEN_DECISIONS.yaml` and `CONFLICTS.yaml` rather than being guessed.
