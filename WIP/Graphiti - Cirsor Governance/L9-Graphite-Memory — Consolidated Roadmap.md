# L9-Graphite-Memory — Consolidated Roadmap

**Scope:** `Quantum-L9/L9-Graphite-Memory` only  
**Date:** 2026-07-05  
**Sources:** UnpackThis Analysis, Strategic Reasoning Bundle, BlueSky Expansion Analysis  
**Secrets Architecture:** `@quantum-l9/infisical-config` (Universal Auth, rotation-aware)  
**Deployment Target:** Zep Cloud (Managed Graphiti)

---

## Strategic Identity

L9-Graphite-Memory is the **Universal Memory Fabric for Autonomous Intelligence**. It is a standalone, deployable memory middleware that any AI agent framework (Cursor, Claude, Windsurf, LangChain, AutoGen, CrewAI, Manus) can route through via standard MCP protocol. It solves stochastic amnesia by forcing agents to consult a bi-temporal knowledge graph of past decisions before executing destructive actions.

---

## Architecture Principles (Non-Negotiable)

1. **IDE-Agnostic:** No dependency on any specific IDE or agent framework.
2. **Transport-Only Changes:** Gate logic, episode contracts, and group resolution are sacred. Only the transport layer (how we reach the graph) changes.
3. **Zero Committed Secrets:** All credentials flow through Infisical Universal Auth at runtime.
4. **Fail-Soft by Default:** If Infisical or Zep Cloud is unreachable, the system degrades gracefully — gates open, memory is skipped, operations continue.
5. **MCP-Native:** Any agent that speaks MCP protocol gets memory. No per-agent auth config.

---

## Current State (As-Is)

| Component | Status |
|-----------|--------|
| `graphiti_memory_client.py` | Functional code, targets dead VPS (`127.0.0.1:8100/mcp/`) |
| `graphiti_gate_lib.py` | Production-grade, no changes needed |
| `episode_contract.py` | Production-grade, no changes needed |
| `group_resolver.py` | Production-grade, no changes needed |
| `circuit_breaker.py` / `rate_limiter.py` | Production-grade, no changes needed |
| `graphiti_env_loader.py` | **DEPRECATED** — macOS Keychain + local `.env` files |
| `ensure_graphiti_tunnel.sh` | **DEPRECATED** — SSH tunnel to dead VPS |
| `config/graphiti.env.example` | **DEPRECATED** — references Hetzner C1 VPS |
| Secrets management | **BROKEN** — `GRAPHITI_MCP_TOKEN` is empty |
| MCP endpoint | **DEAD** — Hetzner VPS returns 404 on `/mcp/` |

---

## Target State (To-Be)

| Component | Target |
|-----------|--------|
| `graphiti_memory_client.py` | Targets Zep Cloud SDK (`zep-python`) |
| `graphiti_env_loader.py` | **REPLACED** by `@quantum-l9/infisical-config` |
| `config/graphiti.env.example` | **REPLACED** by Infisical project config |
| Secrets management | Infisical Universal Auth → `process.env` hydration |
| MCP endpoint | Zep Cloud managed endpoint (zero infrastructure) |
| SSH tunnel / VPS | Fully decommissioned, archived |

---

## Execution Phases

### Phase 0 — Infisical Secrets Integration (CURRENT PRIORITY)

**Objective:** Replace the deprecated `graphiti_env_loader.py` (macOS Keychain + flat `.env` files) with `@quantum-l9/infisical-config` Universal Auth.

**Deliverables:**
- [ ] ADR documenting the secrets architecture decision
- [ ] New `src/l9_graphite_memory/secrets.py` — thin wrapper calling `loadSecrets()` from `@quantum-l9/infisical-config` (or Python equivalent using `@infisical/sdk` patterns)
- [ ] Remove `graphiti_env_loader.py` (move to `_archived/`)
- [ ] Remove `config/graphiti.env.example`, `config/graphiti.env.defaults` (move to `_archived/`)
- [ ] Remove `scripts/init_graphiti_machine_env.sh` (move to `_archived/`)
- [ ] Update `config/mcp.json.example` to remove VPS references
- [ ] Update `README.md` with new secrets setup (3 env vars only)
- [ ] Update `AGENTS.md` to reflect new boundaries

**Contract:**
- Boot requires only: `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`
- All other secrets (`ZEP_API_KEY`, `GRAPHITI_MCP_TOKEN`, `OPENAI_API_KEY`) are pulled from vault at runtime
- Fail-soft: if Infisical is unreachable and `INFISICAL_REQUIRED` is not set, fall back to `process.env` / `os.environ`
- Rotation-aware: SIGHUP or interval refresh for long-running MCP server processes

**No-Touch:**
- `graphiti_gate_lib.py`
- `episode_contract.py`
- `group_resolver.py`
- `circuit_breaker.py`
- `rate_limiter.py`
- `ontology_coding.py`
- All rules in `rules/`
- All hooks in `hooks/`

---

### Phase 1 — Zep Cloud Transport Migration

**Objective:** Replace raw HTTP calls to `127.0.0.1:8100/mcp/` with the `zep-python` SDK targeting Zep Cloud.

**Prerequisite:** Phase 0 complete (secrets available via Infisical).

**Deliverables:**
- [ ] `src/l9_graphite_memory/zep_transport.py` — Zep Cloud SDK adapter
- [ ] Refactor `graphiti_memory_client.py` to use `zep_transport.py` instead of raw `httpx` calls
- [ ] `ZEP_API_KEY` stored in Infisical project, pulled at runtime
- [ ] Preserve all existing CLI commands: `search`, `write`, `bootstrap`, `health`
- [ ] `test_gate_e2e_full.sh` passes against Zep Cloud
- [ ] Archive `_archived/ensure_graphiti_tunnel.sh` (already done)
- [ ] Archive `_archived/docker-compose.yml` (already done)

**Contract:**
- The 4 MCP tools remain identical: `memory_get_budget_slice`, `memory_ingest_episode`, `memory_query_context`, `memory_invalidate_fact`
- Gate logic unchanged — only transport swapped
- Circuit breaker and rate limiter still wrap the new transport

---

### Phase 2 — MCP Server Packaging

**Objective:** Package L9-Graphite-Memory as a standalone MCP server that any agent can connect to.

**Deliverables:**
- [ ] `src/l9_graphite_memory/server.py` — MCP server exposing the 4 tools
- [ ] `pyproject.toml` entry point: `l9-graphite-memory-server`
- [ ] Config writers: `scripts/write_cursor_config.py`, `scripts/write_claude_config.py`
- [ ] Docker image for remote deployment (optional, Zep Cloud handles the graph)
- [ ] Preflight script: `scripts/preflight.sh` (validates connectivity, auth, tools)

**Contract:**
- stdio transport for local agents (Cursor, Claude Desktop)
- SSE transport for remote agents (cloud-hosted, CI)
- Secrets injected via `@quantum-l9/infisical-config` at server boot
- No per-client auth — the MCP server is the single auth boundary

---

### Phase 3 — CI/CD and Publishing

**Objective:** Automated testing, type checking, and package publishing.

**Deliverables:**
- [ ] `.github/workflows/ci.yml` — lint, typecheck, unit tests on push/PR
- [ ] `.github/workflows/publish.yml` — version-gated publish to GitHub Packages (or PyPI)
- [ ] Integration test workflow (requires `INFISICAL_*` secrets in repo settings)
- [ ] Branch protection: require CI green before merge to `main`
- [ ] CodeQL security scanning

---

### Phase 4 — Gate Activation and Rollout

**Objective:** Enable write gates in production across repos.

**Deliverables:**
- [ ] Bootstrap Graphiti graph with `CANONICAL_LAW.md` seed data
- [ ] Soak with `GRAPHITI_WRITE_GATES=0` for 72 hours
- [ ] Flip to `GRAPHITI_WRITE_GATES=1` (hard blocking of destructive actions)
- [ ] Activate `GATES-002` (full memory-before-commit enforcement)
- [ ] Telemetry: track gate pass/fail rates

---

### Phase 5 — Custom Ontology and Cross-Repo Learning

**Objective:** Activate domain-specific entity types and enable cross-repo knowledge sharing.

**Deliverables:**
- [ ] Activate `ontology_coding.py` entities: `RepoManifest`, `Module`, `ADRDecision`, `CIGotcha`
- [ ] Verify Zep Cloud supports custom entity types
- [ ] Enable `group_registry.yaml` cross-repo resolution in production
- [ ] Close the feedback loop: constellation-linter violations → Graphiti episodes → dynamic prompt adjustment

---

## Decommission List

| Item | Action | When |
|------|--------|------|
| Hetzner C1 VPS (`46.62.243.82`) | Terminate | After Phase 1 e2e passes |
| `graphiti_env_loader.py` | Archive to `_archived/` | Phase 0 |
| `config/graphiti.env.example` | Archive to `_archived/` | Phase 0 |
| `config/graphiti.env.defaults` | Archive to `_archived/` | Phase 0 |
| `scripts/init_graphiti_machine_env.sh` | Archive to `_archived/` | Phase 0 |
| macOS Keychain pattern | Deprecated | Phase 0 |
| SSH tunnel hooks | Already archived | Done |
| Local `.env` file pattern | Deprecated | Phase 0 |

---

## Known Unknowns

| Item | Status | Blocker? |
|------|--------|----------|
| Zep Cloud API key | Not yet provisioned | Blocks Phase 1 |
| Zep Cloud custom ontology support | Unverified | Blocks Phase 5 |
| Infisical project ID for `quantum-l9` | UNKNOWN | Blocks Phase 0 implementation |
| Infisical machine identity credentials | UNKNOWN | Blocks Phase 0 runtime |
| `@quantum-l9/infisical-config` published to GitHub Packages | PRs open, not merged | Blocks npm install |
| Python equivalent of `@quantum-l9/infisical-config` | Does not exist yet | Phase 0 must create it |

---

## Boundaries (No-Drift Rules)

1. **No changes to gate logic** — `graphiti_gate_lib.py` is sacred.
2. **No changes to episode contract** — `episode_contract.py` is sacred.
3. **No changes to rules** — `rules/*.mdc` are sacred.
4. **No changes to hooks** — `hooks/*.sh` are sacred (except removing VPS references).
5. **No L9-Ops-MCP references** — that repo is WIP/concept, not a dependency.
6. **No local `.env` files** — all secrets via Infisical.
7. **No macOS-specific code** — must work on any platform.
8. **No per-agent auth config** — MCP server is the single auth boundary.

---

## References

- [Zep Cloud Pricing](https://www.getzep.com/pricing/) — $25/mo Flex plan
- [Zep Graphiti MCP Server](https://help.getzep.com/graphiti/getting-started/mcp-server)
- [Composio Zep Integration](https://composio.dev/toolkits/zep/framework/claude-code)
- [`@quantum-l9/infisical-config`](https://github.com/Quantum-L9/infisical-config) — rotation-aware secrets
- [Infisical Universal Auth](https://infisical.com/docs/documentation/platform/identities/universal-auth)
