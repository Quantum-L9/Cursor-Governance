# Graphiti 2 Source Reuse Matrix — Pre-work Gate

**Date:** 2026-06-06  
**Source:** `Current Work - IGNORE/graphiti/graphiti 2/` (IgorBot WIP)

| Source file | Classification | Port action |
|-------------|----------------|-------------|
| `memory_tool.py` | **rewrite-required** | Extract `CircuitBreaker`, `RateLimiter`, token budget patterns into `circuit_breaker.py`, `rate_limiter.py`; MCP/HTTP client in `graphiti_memory_client.py`; drop IgorBot domain search helpers |
| `group_router.py` | **rewrite-required** | Replace igorbot namespace with `group_resolver.py` + `group_registry.yaml` repo slug resolution |
| `episode_contract.py` | **reuse-as-is** | Adapt `VALID_GROUP_PREFIXES` + forbidden groups; keep PII redaction |
| `domain_packs.yaml` | **config-only** | Extend with `coding` allowlist_only pack |
| `docker-compose.yml` | **reuse + adapt** | Dedicated DB `graphiti_cursor`, port 8100, `GRAPHITI_MCP_TOKEN` |
| Hook scripts | **new** | No equivalent in source — shell wrappers only |

**Gate verdict:** Phase 1 TODO lock approved. No unverified "reuse" claims remain.
