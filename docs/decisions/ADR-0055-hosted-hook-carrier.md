# ADR-0055: Hosted hook carrier; relay becomes the fallback

## Status

Accepted

## Date

2026-11-17

## Context

ADR-0054 (CANONICAL_LAW §8.11) routed hook-lane writes on Claude cloud surfaces
through the `relay` carrier: each envelope-admitted record is queued in
`<repo>/.l9/memory/relay/outbox.jsonl`, and the Claude Stop hook blocked the
agent until it carried each entry through the account-managed L9 Memory
connector. That made every hook write depend on an agent turn, and the account
connector's tools are permissioned per tool in claude.ai, so each relayed
`memory.close` / `memory.ingest_governed_candidate` / `memory.write_agent` could
raise an operator approval prompt that no local allow rule suppresses.

Operator decisions, verbatim:

- "memory reads and writes must be frictionless and 90% + of the time triggered
  with a hook not manually written although there is the 10% which i don't want
  to manually approve either" (campaign L9-ORG-MEMORY-SSOT-01).
- "stop with the memories i'm tired of approving things just fix it up stream so
  i don't ever have to again" (2026-11-17).

The memory repository now provides the exit ADR-0054 named: a machine *hook
principal* — an Auth0 client-credentials token from the application
`l9-memory-hooks`, bound server-side to its envelope in
`L9_MEMORY_HOOK_PRINCIPALS_JSON`.

## Options Considered

1. **Hosted direct (chosen).** The hook lane calls the hosted `MemoryService`
   MCP endpoint itself, as the hook principal: one `initialize` (plus the
   `notifications/initialized` the MCP lifecycle requires before any request)
   and one `tools/call` per record. No agent, no connector, no approval prompt.
2. **CLI remote mode.** Bind the `l9-memory` CLI's remote mode against the
   hosted service and keep transport A. Keeps every byte on the stdio boundary,
   but depends on a memory CLI release with an OAuth client-credentials token
   source being deployed and bound here first; hook records keep relaying (and
   prompting) until then.
3. **Keep relay.** No change. Every hook write still waits on an agent turn and
   can still prompt the operator — the outcome both operator decisions reject.

## Decision

1. **One carrier decision**, still in `ops/memory/hook_carrier.py`: the
   `L9_MEMORY_HOOK_CARRIER` override wins (an unknown value is refused, never
   guessed); otherwise `hosted` when BOTH `L9_MEMORY_HOOK_CLIENT_ID` and
   `L9_MEMORY_HOOK_CLIENT_SECRET` bind through `ops/secrets/capability_bind.py`;
   otherwise `relay` when `CLAUDE_CODE_REMOTE=true`; otherwise `local`.
2. **Credentials.** Infisical project `cursor-governance`, path `/`. Both names
   are `root_env_keys` in `ops/secrets/infisical-cursor-governance.yaml`, not
   `operator_only_keys`: hosted surfaces are where the hook lane runs and must
   bind them. Their values are never printed, logged, or written to an env
   file, settings, the outbox, a receipt, or test output.
3. **Transport** — `ops/memory/hosted_hook_transport.py`. Endpoint and audience
   are `resource.identifier` of `ops/config/memory-auth0-onboarding.yaml`; the
   module names no host, so no egress allowlist changes. The token endpoint
   comes from the onboarding issuer when bound, otherwise from the resource's
   RFC 9728 protected-resource metadata and then that issuer's OIDC discovery,
   and must sit on the issuer's own host. HTTPS only, through
   `ops/lib/safe_https.py` (verified TLS 1.2+, no redirects). Client-credentials
   grant against the Memory audience; the token is cached in-process only. The
   tool names are the relay's `CONNECTOR_TOOLS` (`write` → `memory.write_agent`,
   `ingest_candidate` → `memory.ingest_governed_candidate`, `close` →
   `memory.close`), so the hosted service must offer `memory.write_agent` to
   hook principals.
4. **Envelope first.** `MemoryControlPlaneClient` still admits every record
   against `ops/config/memory-hook-envelopes.json` before it is sent; a hosted
   commit counts against `max_records` like a local one.
5. **`OK`** only when the hosted result carries a UUID receipt id and proves the
   commit (transport `hosted-mcp`, `canonical_receipt_id` = that id).
6. **Refusal is the verdict** (`REJECTED`, never rerouted or parked): an MCP
   tool error, a JSON-RPC error answering the `tools/call`, HTTP 403, or a
   receipt status `rejected` / `quarantined` / `failed`.
7. **Transport failure is not a verdict**: network error, 5xx, 401, any other
   4xx (the session or protocol failed before a tool ran — a refusal there
   would permanently settle a record the service never saw), a JSON-RPC error
   answering `initialize`, token or discovery failure, an unreadable response,
   or a missing receipt. The record goes to the relay outbox with the reason on
   the entry and the outcome is `RELAYED`. Idempotency keys and candidate ids
   make the retry converge; the parked arguments are byte-identical to the
   attempt, so a retry is never a payload drift.
8. **The Stop hook never blocks and never asks** (operator decision
   2026-11-17, superseding CANONICAL_LAW §8.11 item 4 "The agent carries it").
   On `hosted` it drains owed outbox entries through the hosted transport —
   acknowledging each with the hosted receipt or recording the refusal — and
   stops at the first transport failure. On `relay` it asks nothing: entries
   stay in the outbox, one non-blocking line per session reports the count, and
   `python -m ops.memory.relay status` keeps them visible. An empty outbox
   resolves no carrier and binds no credential.
9. **Tags.** Hosted `write` records carry `carrier:hosted` and
   `hook-surface:<surface>`; relayed ones keep `carrier:relay`.
10. **Supersession.** `close_session` supersedes a continuation only within one
    store; `relay` and `hosted` both land in the hosted `MemoryService`
    (`hook_carrier.store_of`), so they supersede each other, while `local` and
    either remote carrier never do.
11. **Boundary.** `ops/memory/hosted_hook_transport.py` is the one memory-path
    module allowed a network transport, and only `urllib` request/error types
    through `safe_https`; `tests/ops/memory/test_transport_boundary.py` and the
    `l9.memory-boundary-no-network-or-provider-transport` semgrep rule pin it to
    exactly that. The hosted `MemoryService` is the canonical store, not a
    provider, so INV-03 (no provider egress) holds.

## Consequences

- On a surface where the hook credential binds, hook records reach the shared
  store with no agent turn and no approval prompt; the relay outbox holds only
  records that met a transport failure, and the next Stop drains them.
- Where the credential does not bind, hook records stay in the relay outbox,
  unasked. Records owed by a container that is discarded before the credential
  binds are lost with it, as before ADR-0054, but are never reported committed.
- Records are attributed to the hook principal, so principal type `hook` is now
  representable.
- Distill still does not run on a remote carrier (`hosted` or `relay`); the
  hosted service distills server-side only.
- **Operator provisioning is outside this change.** Creating the
  `l9-memory-hooks` Auth0 application, binding it in
  `L9_MEMORY_HOOK_PRINCIPALS_JSON`, storing the two Infisical values, and adding
  its client row to `ops/config/memory-auth0-onboarding.yaml` are the operator
  provisioning runbook's job; until the values exist, `hosted` never resolves
  and the relay fallback applies.
- Prompting stops only once this ships to the SSOT; a session already running
  an older checkout keeps the old gate until it refreshes.

## Supersedes

CANONICAL_LAW §8.11 item 2 (the carrier set) and item 4 (the agent carries it);
ADR-0054 decision item 3 (the Stop hook blocks). ADR-0054 otherwise stands as
the relay fallback.
