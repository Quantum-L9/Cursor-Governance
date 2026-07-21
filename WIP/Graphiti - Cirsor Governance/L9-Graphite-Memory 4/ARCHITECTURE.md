# Architecture — L9-Graphite-Memory

## System Overview

L9-Graphite-Memory is a **Bi-Temporal Knowledge Graph** for AI agents. It solves the "stochastic amnesia" problem of LLMs by forcing them to consult a Neo4j-backed graph of past decisions before executing destructive actions.

## Layer Model

```
┌──────────────────────────────────────────────────────────┐
│ Layer 4: IDE Hooks (hooks/)                              │
│   Bash scripts that intercept IDE actions                │
├──────────────────────────────────────────────────────────┤
│ Layer 3: Gate Logic (graphiti_gate_lib.py)               │
│   Local-only decision engine (allow/deny)                │
├──────────────────────────────────────────────────────────┤
│ Layer 2: Memory Client (graphiti_memory_client.py)       │
│   CLI + MCP transport (search, write, health)            │
├──────────────────────────────────────────────────────────┤
│ Layer 1: Backend (Zep Cloud / Self-hosted Graphiti)      │
│   Neo4j temporal knowledge graph                         │
└──────────────────────────────────────────────────────────┘
```

## Data Flow

### Read Path (Prefetch)

```
Session Start → graphiti-prefetch.sh
  → group_resolver.py (resolve group_id from cwd)
  → graphiti_memory_client.py search (MCP call)
  → Write prefetch hash to state file
  → Gate is now satisfied
```

### Write Path (Episode Ingestion)

```
Session End → graphiti-session-end.sh
  → context-extractor.py (Bayesian signal detection)
  → episode_contract.py (validate + PII redaction)
  → graphiti_memory_client.py write (MCP call)
  → Episode stored in temporal graph
```

### Gate Path (Action Blocking)

```
Shell/Write/Subagent Action → graphiti-gate-*.sh
  → graphiti_gate_lib.py
    ├─ Check: prefetch_fresh? (TTL 30 min)
    ├─ Check: memory_satisfied_for task_signature?
    ├─ YES → ALLOW (exit 0)
    └─ NO  → DENY (exit 1, force prefetch)
```

## Key Design Decisions

1. **Gate logic never makes network calls.** It reads only local state files. This ensures gate decisions are instant and never blocked by network failures.

2. **Transport is an implementation detail.** The memory client abstracts the backend behind a stable CLI interface. Swapping from self-hosted to Zep Cloud requires changing only the URL and auth mechanism.

3. **Episodes are immutable once ingested.** The `Supersedes` edge type allows corrections without mutation.

4. **Group IDs provide namespace isolation.** Each repo maps to a `group_id` via `group_registry.yaml`, preventing cross-contamination while enabling deliberate cross-repo knowledge sharing.

## Resilience Patterns

- **Circuit Breaker:** Opens after 3 consecutive failures, half-opens after 60s cooldown
- **Rate Limiter:** Token-bucket algorithm, configurable per-minute limits
- **Graceful Degradation:** If backend is unreachable, gates default to ALLOW (fail-open) to avoid blocking development

## File Ownership

| File | Owner | Stability |
|------|-------|-----------|
| `graphiti_gate_lib.py` | Gate Team | SACRED |
| `episode_contract.py` | Schema Team | SACRED |
| `group_resolver.py` | Platform Team | SACRED |
| `graphiti_memory_client.py` | Transport Team | MUTABLE |
| `graphiti_env_loader.py` | Platform Team | MUTABLE |
| `hooks/*` | Integration Team | STABLE |
| `config/*` | Ops Team | MUTABLE |
