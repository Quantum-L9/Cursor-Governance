<!-- L9_META
l9_schema: 1
parent: l9-graphite-memory
layer: adr
role: architecture_decision
tags: [adr, zep_cloud, transport, migration]
owner: igor_beylin
status: accepted
version: 1.0.0
updated: 2026-07-05
/L9_META -->

# ADR-002: Zep Cloud as Primary Transport Backend

## Status

Accepted

## Context

The L9-Graphite-Memory system previously relied on a self-hosted Graphiti stack running on a Hetzner VPS, accessed via SSH tunnel and raw HTTP JSON-RPC. This architecture had several critical issues:

1. **Single point of failure** — VPS goes down, all memory operations fail.
2. **SSH tunnel fragility** — `ensure_graphiti_tunnel.sh` frequently dropped connections.
3. **Operational burden** — Neo4j, Graphiti server, and the MCP layer all required manual maintenance.
4. **No multi-agent access** — only the machine with the SSH tunnel could use memory.

The project needs a managed service that provides the same knowledge graph capabilities without operational overhead, accessible by any agent that speaks MCP or has the API key.

## Decision

Adopt **Zep Cloud** as the primary transport backend for all knowledge graph operations. The existing HTTP MCP transport is retained as a fallback for environments where Zep Cloud is unavailable.

### Architecture

```
Agent (any) → CLI / MCP Server → Transport Abstraction → Zep Cloud SDK → Zep Cloud
                                                       ↘ HttpMcpTransport → Self-hosted (fallback)
```

### Transport Selection

Controlled by `GRAPHITI_TRANSPORT` environment variable:
- `"zep"` (default) — Uses `ZepCloudTransport` via `zep-python` SDK
- `"http"` — Uses `HttpMcpTransport` (legacy raw JSON-RPC)

### Concept Mapping

| L9 Concept | Zep Cloud Concept |
|---|---|
| `group_id` | `session_id` |
| `add_episode` | `memory.add(messages=[...])` |
| `search_facts` | `memory.search_sessions(search_scope="facts")` |
| `get_episodes` | `memory.get_session_messages(limit=N)` |
| `health` | `memory.list_sessions(page_size=1)` |

### Secrets

`ZEP_API_KEY` is loaded from Infisical Universal Auth at boot time (see ADR-001). No local `.env` files or Keychain entries are needed.

## Consequences

### Positive

- **Zero operational burden** — Zep manages Neo4j, entity extraction, and graph maintenance.
- **Multi-agent access** — Any agent with the API key (via Infisical) can use memory.
- **Built-in entity extraction** — Zep handles NLP/entity resolution server-side.
- **Automatic fact rating** — Zep provides relevance scoring out of the box.
- **Horizontal scaling** — Zep Cloud scales independently of L9 infrastructure.

### Negative

- **Vendor dependency** — Tied to Zep Cloud availability and pricing.
- **Concept mismatch** — Zep's session/message model differs from Graphiti's episode/node model; the transport layer must bridge this gap.
- **Feature subset** — Some advanced Graphiti features (custom ontology, direct Neo4j queries) may not be available through the Zep SDK.

### Mitigations

- `HttpMcpTransport` fallback ensures continuity if Zep is unavailable.
- Transport abstraction (`MemoryTransport` Protocol) allows future backends without client changes.
- Circuit breaker protects against cascading failures from either backend.

## Alternatives Considered

1. **Keep self-hosted VPS** — Rejected due to operational burden and single-point-of-failure.
2. **Composio MCP bridge** — Rejected; adds an unnecessary proxy layer when Zep SDK is available directly.
3. **Direct Neo4j on managed cloud (Aura)** — Rejected; still requires maintaining the Graphiti application layer.
4. **graphiti-core self-hosted on Kubernetes** — Rejected; over-engineered for current scale.
