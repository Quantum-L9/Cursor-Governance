# ADR-0030: The memory control plane is the single front door

## Status

Accepted

## Date

2026-09-06

## Context

Until the memory realignment campaign
(`CURSOR_GOVERNANCE_MEMORY_CONTROL_PLANE_REALIGNMENT_BUILD_PLAN`), Cursor-Governance
reached agent memory by calling the Graphiti provider directly:
`ops/graphiti/graphiti_memory_client.py` spoke MCP-over-HTTP to a provider URL
with a bearer it resolved from a machine env file or the keychain, resolved a
`group_id` on its own, wrote episodes on its own, and the session hooks,
bootstraps, GMP workflows, skills and adapters all embedded that path. The
`l9-graphite-memory` package meanwhile grew a canonical `MemoryService`
(admission, identity, supersession, receipts, projection) that this repository
bypassed. Two authorities, one store, and a credential on every surface.

ADR-0005 (one agent memory, product graphs out of band) and ADR-0006 (one front
door) named the goal; they were written when the only front door available was
the provider client. ADR-0028 fixed close visibility on that same client.

## Decision

1. **Authority.** `MemoryService` in `l9-graphite-memory` (contract
   `memory-control-plane/v1`, release 2.3.0) is the sole authority over agent
   memory: admission, storage, identity, supersession, authorization, receipts.
   Graphiti is a projection memory owns. Cursor-Governance never knows how to
   call it (INV-03).
2. **Boundary.** Every memory byte leaving or entering this repository crosses
   `ops/memory/control_plane_client.py`, one `l9-memory <op>` per call over
   stdio, against the exact runtime `ops/memory/runtime_binding.py` proves from
   `ops/config/memory-binding.json` (INV-11). The operator and workflow CLI is
   `python -m ops.memory.cli`; the MCP transport is the package-owned
   `l9-graphite-memory` stdio server installed by `l9-memory client cursor
   install` (stage C7). Both are transports to the same store.
3. **Resume SSOT.** The `ContinuationCapsuleV2` record (`session_continuation`
   class) admitted at close and retrieved at hydrate is the resume evidence.
   The `PICKUP|…` string, `memory-bank/`, and any provider read are not.
   Current git state wins over a stale capsule.
4. **Secrets.** No surface holds a provider URL or bearer. Hooks load switches
   only; the runtime resolves its own configuration (memory ADR-016); the
   control-plane client strips provider variables from the child environment.
5. **Deletion.** The provider client is a tombstone at its historical path
   (fails loudly, performs nothing). The env plane, the shadow reader, the
   resolver shim, the outcome labeler, the prune tool, the distiller wrapper
   and their tests are deleted. The egress scanner runs in `enforce` mode:
   every remaining allowlist entry is a negative check, a self-reference, or an
   operator-owned file.
6. **Legacy history.** Provider-only records enter canonical memory only
   through `ops/memory/legacy_reconciliation.py` (classes A–G, tag
   `legacy_unverified`, producer `Cursor-Governance/legacy-reconciliation`).
   `ops/config/memory-canonical-epoch.json` records the epoch.

## Consequences

- `rules/03`, `87`, `98`, `skills/l9-graphiti-memory`, `l9-end-session`,
  `l9-chat-extraction`, `l9-gmp-protocol`, `commands/end-session.md`,
  `end-session.yaml`, the GMP workflows and the Program Execution context
  reader invoke `python -m ops.memory.cli`; `CANONICAL_LAW.md` §8.2 and
  `AGENTS.md` carry the dated amendment.
- `make graphiti-health` reaches the tombstone and exits non-zero with the
  replacement named; `make memory-readiness` is the health surface.
- `~/.cursor/graphiti.env` is read for `L9_MEMORY_ENABLED` /
  `L9_MEMORY_WRITE_GATES` (legacy `GRAPHITI_*` aliases) only; any URL or token
  line in it is ignored and reported by the bootstrap as residue.
- The protected `ops/graphiti/docker-compose.yml` and the Infisical inventory
  row for the provider bearer are operator-owned and retired with the provider
  deployment; no Cursor code path reads either.
- The Wave 3 generated-data outbox adapter
  (`environment/agents/generated-data/adapters/graphiti_memory.py`) delivers
  governed candidates to a configured HTTPS endpoint; its target is the memory
  HTTP transport, not the provider, and it spells no provider token. It stays
  under the generated-data conformance suite.

## Supersedes

- ADR-0006's identification of the front door with `graphiti_memory_client.py`
  (the door is now `ops/memory`); ADR-0006's single-front-door principle
  stands.
- ADR-0028's "write-primary repair" as a `graphiti_memory_client.py write`:
  the repair is `hydration.cli repair-write` over the canonical client.
- `CANONICAL_LAW.md` §8 "Memory Layer (Graphiti-Native)" interface rows, via
  §8.2 (2026-09-06).

## References

- `ops/memory/README.md`, `ops/config/memory-binding.json`,
  `ops/config/memory-canonical-epoch.json`
- `ops/scripts/validate_memory_egress_boundary.py`,
  `ops/config/memory-egress-allowlist.json`
- `tests/ops/memory/test_cross_repo_lifecycle.py` (plan §35 exact-head proof)
- `Quantum-L9/l9-graphiti-memory` ADR-016 (runtime-owned configuration),
  ADR-082 (governed candidates)
