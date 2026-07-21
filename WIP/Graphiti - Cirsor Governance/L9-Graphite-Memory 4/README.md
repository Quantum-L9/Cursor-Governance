# L9-Graphite-Memory

> Bi-Temporal Knowledge Graph Memory Substrate for Autonomous AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## Overview

L9-Graphite-Memory is the extracted, standalone memory subsystem from the [L9 Governance](https://github.com/Quantum-L9/Cursor-Governance) architecture. It provides a gate-enforced, semantic memory layer that replaces flat JSON/Markdown chat logs with a Neo4j-backed temporal knowledge graph via [Graphiti](https://github.com/getzep/graphiti) (by Zep).

The system intercepts IDE actions (shell commands, file writes, tool use) via hooks, enforces "search-before-write" discipline, and extracts temporal episodes (lessons, ADRs, CI gotchas) into a persistent graph that compounds intelligence over time.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  IDE (Cursor / Windsurf / Any)                                  │
│   └─ Bash Hooks (hooks/graphiti-*.sh)                           │
│        └─ Gate Logic (graphiti_gate_lib.py)                     │
│             ├─ ALLOW → proceed with action                      │
│             └─ DENY  → force memory prefetch first              │
│        └─ Memory Client (graphiti_memory_client.py)             │
│             └─ MCP Protocol → Graphiti Backend                  │
│                  ├─ Option A: Zep Cloud (api.getzep.com)        │
│                  ├─ Option B: Self-hosted (Neo4j + MCP server)  │
│                  └─ Option C: Composio MCP bridge               │
│                                                                 │
│  Context Extraction (intelligence/context-memory/)              │
│   └─ context-extractor.py (Bayesian signal detection)           │
│   └─ graphiti_sink.py (episode writer)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| Memory Client | `src/l9_graphite_memory/graphiti_memory_client.py` | CLI + MCP client (search, write, bootstrap, health) |
| Gate Logic | `src/l9_graphite_memory/graphiti_gate_lib.py` | Block actions if memory prefetch not satisfied |
| Episode Contract | `src/l9_graphite_memory/episode_contract.py` | Pydantic schema + PII redaction for episodes |
| Group Resolver | `src/l9_graphite_memory/group_resolver.py` | Maps Git repo → Graphiti `group_id` |
| Circuit Breaker | `src/l9_graphite_memory/circuit_breaker.py` | Resilience pattern for MCP connection |
| Rate Limiter | `src/l9_graphite_memory/rate_limiter.py` | Token-bucket rate limiting |
| Secrets | `src/l9_graphite_memory/secrets.py` | Infisical Universal Auth secrets adapter |
| Ontology | `src/l9_graphite_memory/ontology_coding.py` | Custom entity/edge types (RepoManifest, CIGotcha) |
| Context Extractor | `intelligence/context-memory/context-extractor.py` | Bayesian engine for signal detection in chat logs |
| Hooks | `hooks/` | Bash scripts intercepting IDE actions |
| Rules | `rules/` | `.mdc` governance rules for agent compliance |

## Quick Start

### 1. Install Dependencies

```bash
pip install l9-graphite-memory
# or from source:
pip install pydantic pyyaml httpx infisical-python
```

### 2. Configure Secrets (Infisical Universal Auth)

```bash
# Set the 3 bootstrap env vars (machine identity from Infisical dashboard)
export INFISICAL_CLIENT_ID="your-machine-identity-client-id"
export INFISICAL_CLIENT_SECRET="your-machine-identity-client-secret"
export INFISICAL_PROJECT_ID="your-project-id"

# Optional overrides:
export INFISICAL_ENV="prod"           # default: prod
export INFISICAL_SECRET_PATH="/"      # default: /
export INFISICAL_REQUIRED="0"         # set to 1 for hard-fail in production
```

Secrets (ZEP_API_KEY, OPENAI_API_KEY, etc.) are fetched from Infisical at runtime.
See `docs/adr/ADR-001-infisical-secrets-architecture.md` for full details.

### 3. Verify Health

```bash
python3 src/l9_graphite_memory/graphiti_memory_client.py health
```

### 4. Search Memory

```bash
python3 src/l9_graphite_memory/graphiti_memory_client.py search "CI pipeline failures"
```

### 5. Write Episode

```bash
python3 src/l9_graphite_memory/graphiti_memory_client.py write \
  --source "lesson" \
  --content "Always run type-check before push"
```

## Configuration

Secrets are loaded via Infisical Universal Auth (`secrets.py`):
1. **Boot:** 3 env vars (`INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`)
2. **Runtime:** `load_secrets_sync()` fetches all secrets from Infisical vault → injects into `os.environ`
3. **Fallback:** If Infisical is not configured, reads directly from `os.environ` (fail-soft)
4. **Rotation:** SIGHUP handler + interval refresh for long-running servers

### Backend Options

| Backend | Config | Cost | Maintenance |
|---------|--------|------|-------------|
| Zep Cloud | `GRAPHITI_MCP_URL=https://api.getzep.com/mcp/` | $25/mo | Zero |
| Self-hosted | `GRAPHITI_MCP_URL=http://127.0.0.1:8100/mcp/` | VPS cost | High |
| Composio Bridge | Use Composio MCP URL | Composio plan | Low |

## Gate System

The gate system enforces "search-before-write" discipline:

1. **Prefetch:** On session start, `graphiti-prefetch.sh` queries the graph for relevant context
2. **Gate Check:** Before shell/write/subagent actions, `graphiti_gate_lib.py` verifies memory was consulted
3. **Allow/Deny:** If `GRAPHITI_WRITE_GATES=1` and prefetch is stale, the action is blocked
4. **Mark OK:** After successful prefetch, `graphiti-mark-ok.sh` updates the state file

## Episode Contract

All episodes ingested into the graph must conform to the schema in `episode_contract.py`:

- Strict Pydantic validation
- Automatic PII redaction (emails, API keys, paths)
- Required fields: `source`, `content`, `group_id`, `timestamp`
- Optional: `metadata`, `tags`, `supersedes`

## Group Resolution

The `group_resolver.py` maps the current working directory to a Graphiti `group_id` using `config/group_registry.yaml`. This enables:

- Cross-repo knowledge sharing
- Namespace isolation between projects
- Automatic context scoping

## Extracted From

This module was extracted from [`Quantum-L9/Cursor-Governance`](https://github.com/Quantum-L9/Cursor-Governance) (paths: `ops/graphiti/`, `ops/hooks/graphiti-*`, `intelligence/context-memory/`, `rules/*graphiti*`, `skills/l9-graphiti-memory/`).

## Migration Status

| Phase | Status |
|-------|--------|
| Extract to standalone repo | Done |
| Phase 0: Infisical secrets integration | **Done** |
| Phase 1: Zep Cloud transport migration | Pending (requires API key) |
| Phase 2: MCP server packaging | Pending |
| Phase 3: CI/CD and publishing | Pending |

See `ROADMAP.md` for full execution plan.

## License

MIT

---

*Part of the [L9 Constellation](https://github.com/Quantum-L9) architecture.*
