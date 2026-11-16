# ADR-0054: Relay hook carrier for the shared Memory 3.0 store

## Status

Accepted

## Date

2026-11-16

## Context

`l9-graphiti-memory` 3.0 is deployed as the shared `MemoryService` on the Hetzner
host (Postgres). Its hosted door admits only an Auth0 OAuth principal that is a
person bound to an actor; client-credentials tokens are refused by design
(memory ADR-100, ADR-102, ADR-103). The account-managed L9 Memory connector is
such a principal, and a dry-run `memory.write_agent` to `cursor-governance` from
a Claude Code cloud session was admitted ("namespace matched write grant").

The hook lane (ADR-0033) reaches memory only through `MemoryControlPlaneClient`,
which spawns the bound local `l9-memory` runtime. On a cloud container that
runtime's store is the default `~/.local/share/l9-memory/memory.sqlite3`, which
is discarded with the container. Observed in session
`session_017xwbxvXyayxm4D9cQotHWu`: the `make pr` publish fact and both Stop
handoffs were reported `OK` and existed only in that file, while the shared store
held two records.

## Decision

Operator decision (2026-11-16): relay now, then a hook principal.

1. `ops/memory/hook_carrier.py` decides the carrier once: `relay` or `local`
   (`L9_MEMORY_HOOK_CARRIER`, else `relay` when `CLAUDE_CODE_REMOTE=true`).
   An unknown value fails closed.
2. On `relay`, the client keeps envelope admission and then queues the record
   in `.l9/memory/relay/outbox.jsonl` with the account-connector arguments
   (`write`→`memory.write_agent`, `ingest_candidate`→`memory.ingest_governed_candidate`,
   `close`→`memory.close`). No local store is opened. The outcome is `RELAYED`
   (fault class none, not `OK`). A queued record counts against `max_records`.
3. The Claude Stop hook blocks, at most three times per entry, until each
   entry is acknowledged with the connector's receipt id
   (`python -m ops.memory.relay ack`).
4. SessionStart says so: the local health line is container scratch, and
   shared hydration is `memory_hydrate` on the account connector.

## Consequences

- Hook records on cloud sessions now reach the shared store, at the cost of
  one agent turn per Stop that has owed entries.
- They are attributed to the agent's actor, tagged `carrier:relay` and
  `hook-surface:<surface>`; principal type `hook` is not representable until
  the memory service has a hook principal.
- A session that ends without a Stop (or a SessionEnd-only close) leaves its
  entries in the container's outbox; they are lost with it, as before, but are
  never reported as committed.
- Transcript distill does not run on relay surfaces.
- The pasted Setup-script stub is unchanged: the default already selects relay
  on cloud containers.

## Exit

A memory ADR adds an envelope-bound hook principal (client-credentials token
bound server-side to its envelope); Cursor-Governance then binds 3.0 with the
CLI's `--remote-url` against the hosted service and retires this carrier.
