# ADR-0038: Canonical identity is projected from Quantum-L9/.github and governed by a local binding

## Status

Proposed

## Date

2026-10-03

## Supersedes

Nothing. This ADR introduces a projection path for ActorIdentity and SurfaceIdentity coordinates whose canonical source is now `Quantum-L9/.github` (`semantics/actor_registry.yaml`, `semantics/surface_registry.yaml`; `.github` ADR-013). ADR-0039 records the matching change to `environment/agents/agent_registry.yaml`.

## Context

Identity names are currently declared locally in Cursor-Governance. `environment/agents/agent_registry.yaml` holds `agent_id`, `source`, `surfaces` and `status` for every writer, and `ops/memory/agent_identity.py` resolves against those local declarations.

`Quantum-L9/.github` now publishes canonical, organization-wide actor and surface registries. If both sources stay authoritative, actor and surface names will drift between the two repositories. That drift would reach memory authorship, receipts and adapter selection.

Cursor-Governance still needs a local, verifiable copy of those coordinates for three reasons:

- Hooks and validators run offline, against the checkout.
- Resolution must fail closed when the upstream source is missing or stale.
- The authority for credentials, grants, roles and adapters must stay local, not move upstream.

## Options Considered

1. **Keep local identity declarations.** Zero migration cost, but this repository stays a second identity authority. Rejected: the dual-authority drift is the defect.
2. **Read `Quantum-L9/.github` live at runtime.** This has a single source, but adds a network dependency to every hook and resolution, and gives no pinned revision or digest to audit. Rejected.
3. **Commit a deterministic, receipted projection, governed by a local binding.** Resolution reads a committed artifact that is pinned to an exact upstream revision and digests. A local binding says what the projection governs and what it does not. CI verifies that the projection matches upstream and opens a refresh PR when it drifts. **Chosen.**

## Decision

**Cursor-Governance consumes canonical ActorIdentity and SurfaceIdentity only through a committed projection of `Quantum-L9/.github`. A local governing binding makes that verified projection authoritative for identity resolution in this repository, without making it canonical.**

The decision is implemented by these files:

| Artifact | Role |
|---|---|
| `generated/governance/canonical_identity.yaml` | Derived projection (`l9.projection/cursor-governance-identity@1`). Machine generated; never hand-edited. |
| `generated/governance/canonical_identity.receipt.yaml` | Projection receipt: source revision, source digests, profile digest, output digest. |
| `governance/authority-bindings/canonical-agent-identity.yaml` | Local governing binding (`l9.cursor-governance/identity-binding@1`): what is governed, what is not, and the fail-closed policy. |
| `tools/authority/project_canonical_identity.py` | Deterministic projector. `--check` verifies the committed projection. |
| `tools/assurance/check_canonical_identity_projection.py` | Assurance check over the binding, the projection, the receipt and the registry references. |
| `rules/64-canonical-identity-authority.mdc` | Agent-facing rule: reference form, prohibited local fields, projection law. |
| `.github/workflows/l9-canonical-identity-projection.yml` | Verify on PR/push. Refresh on schedule, dispatch or `l9-semantic-authority-updated`, opening a projection PR. |

## Invariants

- Actors are referenced as `l9.actor-registry/global@1#<id>`. Surfaces are referenced as `l9.surface-registry/global@1#<id>`.
- Missing, stale, malformed, conflicting or unverifiable projection state rejects. There is no local fallback, no local alias, and no local override.
- Identity is never inferred from adapter, model, environment variable, executable, repository, directory, provider or UI-label names.
- Canonical identity grants no credential, permission, memory grant, role, adapter, governance profile or provider binding. Those remain operating-plane concerns.

## Consequences

- The projection depends on `Quantum-L9/.github` publishing `l9.projection/cursor-governance-identity@1` in `semantics/projection_profiles.yaml`. It does not exist upstream yet. Until it does, `project_canonical_identity.py --check` fails, and the committed projection stays an `UNGENERATED` placeholder that assurance rejects by design.
- Changing an identity becomes an upstream change in `.github`, followed by a regenerated projection here. Identity is not edited in this repository.
- The rule takes prefix `64` (the security band), because `01` is held by `01-authority-chain.mdc` and the rules standard forbids shared prefixes.
