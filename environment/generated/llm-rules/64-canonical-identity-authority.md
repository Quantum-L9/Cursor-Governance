---
description: Canonical ActorIdentity and SurfaceIdentity projection authority
---

<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: rules/64-canonical-identity-authority.mdc
layer: governance
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-10-03
/L9_META -->
# Canonical Identity Authority
`Quantum-L9/.github` is the canonical authority for organization-level
ActorIdentity and SurfaceIdentity coordinates.
Cursor-Governance MUST consume those coordinates through:
- `generated/governance/canonical_identity.yaml`
- `generated/governance/canonical_identity.receipt.yaml`
- `governance/authority-bindings/canonical-agent-identity.yaml`
The generated identity projection is globally derived and non-canonical.
The local governing binding makes that verified projection authoritative for
identity resolution inside Cursor-Governance.
## Required behavior
Agents MUST reference actors using:
`l9.actor-registry/global@1#<actor-id>`
Agents MUST reference surfaces using:
`l9.surface-registry/global@1#<surface-id>`
`environment/agents/agent_registry.yaml` owns only operating-plane bindings.
It MAY own:
- actor-to-surface assignment
- local role assignment
- memory principal coordinates
- namespace grants
- token environment variable names
- adapter selection
- local operating binding state
It MUST NOT own:
- canonical actor ids
- canonical actor kinds
- canonical actor lifecycle
- canonical surface ids
- canonical surface lifecycle
- actor aliases
- surface aliases
## Prohibited local identity declarations
Do not add these fields to an operating agent binding:
- `agent_id`
- `source`
- `surfaces`
- `actor_kind`
- `actor_status`
- `surface_status`
- `aliases`
Use `actor_ref` and `surface_refs`.
## Projection law
Never manually edit:
- `generated/governance/canonical_identity.yaml`
- `generated/governance/canonical_identity.receipt.yaml`
Regenerate them from `Quantum-L9/.github`.
Missing, stale, malformed, conflicting, or unverifiable projection state fails
closed.
Do not infer identity from:
- adapter names
- model names
- environment variable names
- executable names
- repository names
- directory names
- provider names
- UI labels
## Authority boundary
Canonical identity does not imply:
- credentials
- permissions
- execution authority
- memory grants
- role assignment
- adapter assignment
- governance profile
- provider binding
Those remain operating-plane concerns.
A downstream projection may govern local resolution without becoming the
canonical source of the projected semantics.

<!-- generated-from: rules/64-canonical-identity-authority.mdc; do-not-edit -->
