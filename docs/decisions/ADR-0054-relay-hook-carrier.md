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

## Options Considered

1. **Relay through the agent now, hook principal later (chosen; operator
   decision 2026-11-16).** Works today with no memory-service change: the
   account connector's person principal is already admitted. Costs one agent
   turn per Stop with owed entries, and records are attributed to the agent's
   actor rather than a hook principal until the second step ships.
2. **Hook principal only.** Narrow ADR-103 in `l9-graphiti-memory` to admit
   an envelope-bound client-credentials principal and give the CLI an OAuth
   token source, then point the hook lane at the hosted service. The right
   end state, but hooks keep writing to container scratch and losing records
   until a memory release is deployed on C1 and bound here.
3. **Relay through the agent permanently.** Keeps ADR-103's machine-access
   closure intact and needs no memory-service change, but every hook write
   depends on the agent completing it and principal type `hook` is never
   representable.
4. **Rejected outright:** a person's OAuth refresh token for hooks (forbidden
   on hosted surfaces, which strip OAuth credentials) and pointing the CLI's
   signed-agent `--remote-url` at the hosted service (refused there by
   ADR-100).

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

## Amendment (2026-11-17) — connector refusals

Observed: an outbox entry for namespace `seo-bot` was refused twice by the
hosted connector (`memory.write_agent` → `status: rejected`, "namespace did not
match any write grant"). The relay had no verb for that verdict. An `ack` would
claim a hosted write that never landed (L9-EVIDENCE-001), so nothing the agent
could correctly do cleared the entry, which rule 42 "Satisfiability" forbids.

`python -m ops.memory.relay refuse <id> --receipt <rejection receipt_id>
--reason "..."` records the refusal in an append-only
`.l9/memory/relay/refusals.jsonl`. A refused entry no longer blocks Stop. It is
still listed by `pending` (with its latest `refusal`) and counted by `status`
(`refused`), and the Stop hook announces it on every Stop. The model is
`session_debt.py defer`: the turn is discharged but the item stays open. A
later `ack` supersedes the refusal. A refusal never supersedes an `ack`, and it
needs the connector's receipt id and stated reason. The rule against retrying
through another door is unchanged. Fixing the grant itself is a separate
change on the memory service side.
