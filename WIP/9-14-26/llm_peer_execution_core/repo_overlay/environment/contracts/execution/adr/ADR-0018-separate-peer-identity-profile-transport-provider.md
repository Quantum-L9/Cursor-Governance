# ADR-0018: Separate Peer Identity, Execution Profile, Transport, and Provider

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

The current Executable Peer Contract binds peer topology to Program adapter IDs, and adapter descriptors can carry `identity.agent_ref`. That couples agent identity to provider implementation. A provider change therefore risks becoming an identity/topology change, while one provider cannot cleanly serve multiple peers without duplicated descriptors.

## Decision

The canonical binding model is:

```text
Program Controller
  -> Peer Runtime Binding
  -> Execution Profile
  -> Peer Execution Core
  -> Shared Transport
  -> Thin Provider Adapter
  -> Provider or Host
```

Responsibilities are orthogonal:

- **Peer Runtime Binding** answers WHO and WHERE: `agent_ref`, surface, `provider_ref`, `execution_profile_ref`, readiness reference.
- **Execution Profile** answers WHICH reusable policy applies: permissions, budgets, context policy, timeout/retry/concurrency limits.
- **Shared Transport** answers HOW requests move: subprocess, HTTP, MCP, or another reusable protocol implementation.
- **Provider Adapter** answers HOW this provider maps canonical requests/results to its specific invocation format.

Provider descriptors MUST NOT own canonical peer identity. A single provider may serve multiple peers. A peer may change provider without changing its canonical identity.

## Schema migration

`PEER_RUNTIME_BINDINGS` should move from provider-coupled `adapter_id` bindings toward `provider_ref` plus `execution_profile_ref` in a new versioned schema. Migration MUST be deterministic and cut over once. Long-lived dual-read identity/topology shims are forbidden.

## Consequences

- Provider substitution becomes configuration/topology instead of identity surgery.
- The same Claude Code provider can serve different peer identities under different execution profiles.
- Future direct API providers can reuse the same peer identities and profiles.
- Provider adapters become reusable infrastructure components rather than agent-specific components.

## Rejected alternatives

### Keep `agent_ref` as provider-adapter ownership

Rejected because identity and implementation have different lifecycles and cardinality.

### Duplicate providers per peer

Rejected because it creates semantic duplicates and guarantees drift.
