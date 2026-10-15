# ADR-0053: Remote Memory MCP consumer binding (memory-remote-mcp/v1)

## Status

Accepted

## Date

2026-10-15

## Supersedes

- [ADR-0030](ADR-0030-memory-control-plane-single-front-door.md) item 9 ("no provider
  transport on any model surface"), **only** where it is read to forbid the admitted
  Memory service's own remote MCP transport. Provider transports stay forbidden.
- [ADR-0031](ADR-0031-signed-agent-mcp-write-classes.md) "HTTP stays sealed", for the
  same single route.
- `memory-enforcement.contract.json` 3.x `interactive_memory_write.http_transport:
  forbidden`, replaced in contract 4.0.0 by `admitted_remote_only` plus a
  `remote_transport` block.

Those records stay on disk. Everything else in them stands.

## Context

Memory 3.0.0 (`Quantum-L9/l9-graphiti-memory` #96, its ADR-098) adds a remote
transport to the one canonical `MemoryService`: stateless MCP Streamable HTTP at
`POST /mcp`, contract `memory-remote-mcp/v1`, `memory-control-plane/v1` unchanged.
Its `signed-agent` mode authenticates every request with the same ADR-0031
credentials this repository already mints: an HMAC token
(`agent_id.exp.nonce.sig`) and the sealed `l9.identity-assertion/v1`, carried as
the `Authorization`, `L9-Identity-Assertion` and `L9-Identity-Assertion-HMAC`
headers. Grants and signing keys are server-side. The human door and every
`is_admin` grant are unreachable over HTTP.

This repository's own law forbade any of it. The 3.x contract fixed
`http_transport: forbidden` (schema const, validator, pin test), and
CANONICAL_LAW §8.2 item 2 and §8.5 item 4 sealed agent HTTP. Memory's remote
contract says outright that a Cursor-Governance ADR is required before any
adapter may select HTTP. This is that ADR.

The forbidden HTTP doors were provider side doors: `L9_MEMORY_HTTP_*`
variables, a shared bearer, a model-visible URL, and the retired hosts and
ports. The admitted service is none of these. It is the canonical service on a
second transport, with per-agent identity and server-owned grants.

## Decision

1. **One more route, not an open door.** Agent memory may cross HTTP only as
   `memory-remote-mcp/v1` to the admitted Memory release, in `signed-agent`
   mode. Every other HTTP route (provider, shared bearer, retired host or port,
   any path but `/mcp`) stays forbidden.
2. **The model-visible entry does not change.** Cursor and Claude Code keep
   the stdio entry that launches `ops/memory/run_memory_mcp.sh`, with no URL,
   headers or env block. When an operator names an endpoint, the wrapper execs
   the consumer bridge `ops/memory_remote/bridge.py` instead of the local
   server. Tool definitions and envelopes are the service's own: the bridge
   relays and adds nothing.
3. **Operator selection, admitted release.** The endpoint is per-machine
   operator input: `L9_MEMORY_REMOTE_MCP_ENDPOINT`, or
   `~/.config/l9-memory/remote-endpoint.json` = `{"endpoint": …}` for hosts
   that launch without a shell environment. It is never repository content.
   The bridge serves only when `ops/config/memory-remote-binding.json` names an
   admitted release with full evidence (version, source SHA, tag, wheel
   digest, admission receipt). Before relaying anything, it then proves the
   live service reports that exact package version and both contract versions.
   A release candidate can be reached only on loopback, under an explicit
   `L9_MEMORY_REMOTE_CANDIDATE_QUALIFICATION` reason, for consumer
   qualification.
4. **Identity is the agent's own.** The door is minted exactly as for the
   local server: actor derived from host markers, sealed canonical identity
   assertion. The bridge keeps only `{agent_id: key}` and the sealed identity,
   mints a fresh short-lived token for each request (TTL 300s by default),
   drops the door secret and grants from its own environment, and refuses the
   human principal.
5. **Durable keys only.** The hosted container self-mint
   (`materialize_agent_authority --provision-hosted`) makes a key only that
   container knows. That key is valid against an in-process server and never
   against a remote one. In remote mode the wrapper refuses it and requires an
   operator-provisioned per-agent key (`L9_MEMORY_AGENT_AUTHORITY_JSON` or the
   workstation key map), held by both the agent and the service.
6. **Fail closed, never fall back.** These all refuse to launch, and none of
   them is ever served from the local store:
   - an invalid, retired or non-HTTPS-off-loopback endpoint;
   - an unadmitted binding;
   - service identity drift;
   - a refused credential;
   - an unreachable service;
   - `L9_MEMORY_ALLOW_LOCAL_OPERATOR=1`.

   Mid-session, a 401 gets one fresh-token retry. After that the client gets a
   JSON-RPC error that names the refusal.
7. **Unchanged.** One `MemoryService`; `memory-control-plane/v1`; ordinary
   writes are `memory.write_agent`; conflict-sensitive writes are
   `memory.phase_lock` → `memory.write_governed`; `repository_authority:
   false` (a write the service accepts is never permission to edit a
   repository); no provider-direct write; no generic-ingest bypass; namespace
   grants decided by memory alone; worktree, L4 and publication governance;
   the hook lane.

## Consequences

- Machine form: contract 4.0.0 `interactive_memory_write.http_transport:
  admitted_remote_only` and `remote_transport` (every value is a schema const
  and a validator const). `test_memory_front_door.py` pins the new values and
  rejects `allowed`, an endpoint in the contract, a fallback, and admin over
  HTTP.
- Until a 3.0.0 release is admitted, `release.admission` is `pending`, and
  every hosted endpoint is refused by construction.
- The hook lane (`ops/memory/control_plane_client.py`: SessionStart health,
  sessionEnd close, the operator CLI) still talks to the locally bound
  runtime. On a machine that selects the remote MCP transport, model-authored
  writes go to the service while hook-lane records stay local until the
  package CLI gains a remote client. That gap is recorded here and is not
  hidden.
- Hosted Claude Code surfaces have no lawful durable-key delivery yet. The
  environment settings are model-readable, and no memory secret is in the
  Infisical inventory (`ops/secrets/capabilities.yaml`). Delivering a key
  needs a separate secret-plane change.

## Verification

- `tests/ops/memory_remote/test_bridge.py`: endpoint, binding, credential and
  relay refusals, network-free.
- `tests/ops/memory/test_run_memory_mcp.py`: transport selection and launcher
  refusals.
- `tests/ops/memory_remote/test_candidate_interop.py`: the consumer bridge
  against a real `l9-graphite-memory` 3.0.0 candidate server on loopback.
  Two agents, shared namespace, authorship, refusals. It skips with a named
  reason when no candidate runtime is supplied
  (`L9_MEMORY_REMOTE_CANDIDATE_PYTHON`).
