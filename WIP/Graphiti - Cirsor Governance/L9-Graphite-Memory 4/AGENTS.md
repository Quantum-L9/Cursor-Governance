# AGENTS.md — L9-Graphite-Memory

## Identity

This repository is the **standalone memory substrate** for the L9 Constellation. It provides temporal knowledge graph memory to autonomous AI agents via the Graphiti/Zep protocol.

## Boundaries

### Sacred Files (NO-TOUCH without explicit approval)

- `src/l9_graphite_memory/graphiti_gate_lib.py` — Gate decision logic
- `src/l9_graphite_memory/episode_contract.py` — Episode schema contract
- `src/l9_graphite_memory/group_resolver.py` — Group ID resolution
- `hooks/graphiti_common.sh` — Shared hook utilities
- `hooks/graphiti_gate_runner.sh` — Gate execution orchestrator

### Modification-Safe Files

- `src/l9_graphite_memory/graphiti_memory_client.py` — Transport layer (refactor target)
- `src/l9_graphite_memory/graphiti_env_loader.py` — Environment loading (update for new backends)
- `config/` — All configuration files
- `_archived/` — Deprecated infrastructure

## Architecture Contracts

1. **Gate logic is local-only.** The gate decision (`allow`/`deny`) must never depend on network calls. It reads local state files only.
2. **Episode contract is immutable.** All episodes must pass `episode_contract.py` validation before ingestion.
3. **Group resolution is deterministic.** Given the same `cwd` and `group_registry.yaml`, the output must always be the same `group_id`.
4. **Transport is swappable.** The memory client's backend (Zep Cloud, self-hosted, Composio) is an implementation detail. The CLI interface (`search`, `write`, `health`, `bootstrap`) must remain stable.

## CI Requirements

- All Python files must pass `ruff check` and `mypy --strict`
- `tests/test_gate_e2e_full.sh` must pass on every PR
- No secrets in committed files — all credentials via Infisical Universal Auth

## Upstream Dependencies

- `Quantum-L9/Cursor-Governance` — Governance rules reference this module
- `Quantum-L9/infisical-config` — Secrets architecture contract (TypeScript reference implementation)

## Downstream Consumers

- Any IDE hook system that calls `graphiti_memory_client.py`
- Any agent that needs temporal graph memory

## Active Migration

The primary active work is:
1. **Phase 0 (current):** Replace `graphiti_env_loader.py` with Infisical Universal Auth (`secrets.py`)
2. **Phase 1 (next):** Migrate transport from dead VPS to Zep Cloud managed service

See `ROADMAP.md` for full execution plan.
