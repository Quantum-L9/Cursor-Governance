# Extraction Manifest

**Source:** `Quantum-L9/Cursor-Governance` (main branch, 2026-07-05)  
**Target:** `Quantum-L9/L9-Graphite-Memory`  
**Extracted by:** L9 Systems Agent  
**Date:** 2026-07-05

## File Mapping

| New Path | Original Path | Notes |
|----------|---------------|-------|
| `src/l9_graphite_memory/graphiti_memory_client.py` | `ops/graphiti/graphiti_memory_client.py` | Primary CLI + MCP client |
| `src/l9_graphite_memory/graphiti_gate_lib.py` | `ops/graphiti/graphiti_gate_lib.py` | Gate decision logic (SACRED) |
| `src/l9_graphite_memory/circuit_breaker.py` | `ops/graphiti/circuit_breaker.py` | Resilience pattern |
| `src/l9_graphite_memory/rate_limiter.py` | `ops/graphiti/rate_limiter.py` | Rate limiting |
| `src/l9_graphite_memory/episode_contract.py` | `ops/graphiti/episode_contract.py` | Schema contract (SACRED) |
| `src/l9_graphite_memory/group_resolver.py` | `ops/graphiti/group_resolver.py` | Group ID resolver (SACRED) |
| `src/l9_graphite_memory/graphiti_env_loader.py` | `ops/graphiti/graphiti_env_loader.py` | Env/Keychain loader |
| `src/l9_graphite_memory/ontology_coding.py` | `ops/graphiti/ontology_coding.py` | Custom entity types |
| `src/l9_graphite_memory/prune.py` | `ops/graphiti/prune.py` | Graph pruning utility |
| `hooks/graphiti-gate-edits.sh` | `ops/hooks/graphiti-gate-edits.sh` | Edit gate hook |
| `hooks/graphiti-gate-shell.sh` | `ops/hooks/graphiti-gate-shell.sh` | Shell gate hook |
| `hooks/graphiti-gate-subagent.sh` | `ops/hooks/graphiti-gate-subagent.sh` | Subagent gate hook |
| `hooks/graphiti-mark-ok.sh` | `ops/hooks/graphiti-mark-ok.sh` | Mark memory satisfied |
| `hooks/graphiti-prefetch.sh` | `ops/hooks/graphiti-prefetch.sh` | Session prefetch |
| `hooks/graphiti-reset-generation.sh` | `ops/hooks/graphiti-reset-generation.sh` | Reset generation state |
| `hooks/graphiti-session-end.sh` | `ops/hooks/graphiti-session-end.sh` | Session end episode write |
| `hooks/graphiti_common.sh` | `ops/hooks/graphiti_common.sh` | Shared utilities |
| `hooks/graphiti_gate_runner.sh` | `ops/hooks/graphiti_gate_runner.sh` | Gate orchestrator |
| `config/group_registry.yaml` | `ops/graphiti/group_registry.yaml` | Group ID mappings |
| `config/domain_packs.yaml` | `ops/graphiti/domain_packs.yaml` | Domain pack definitions |
| `config/graphiti.env.defaults` | `ops/graphiti/graphiti.env.defaults` | Default env values |
| `config/graphiti.env.example` | `ops/graphiti/graphiti.env.example` | Example env file |
| `config/mcp.json.example` | `ops/graphiti/mcp.json.example` | MCP config example |
| `config/memory-bank-template/` | `ops/graphiti/memory-bank-template/` | Memory bank templates |
| `intelligence/context-memory/context-extractor.py` | `intelligence/context-memory/context-extractor.py` | Bayesian extractor |
| `intelligence/context-memory/README.md` | `intelligence/context-memory/README.md` | Context memory docs |
| `intelligence/context-memory/INSTALLATION.md` | `intelligence/context-memory/INSTALLATION.md` | Install guide |
| `intelligence/context-memory/CRITICAL_FIX_NOTES.md` | `intelligence/context-memory/CRITICAL_FIX_NOTES.md` | Fix notes |
| `rules/03-graphiti-memory.mdc` | `rules/03-graphiti-memory.mdc` | Memory rule |
| `rules/97-graph-engine-architecture.mdc` | `rules/97-graph-engine-architecture.mdc` | Architecture rule |
| `rules/97-graph-layer-boundary.mdc` | `rules/97-graph-layer-boundary.mdc` | Layer boundary rule |
| `rules/98-graphiti-memory-gate.mdc` | `rules/98-graphiti-memory-gate.mdc` | Gate rule |
| `rules/99-graphiti-temporal.mdc` | `rules/99-graphiti-temporal.mdc` | Temporal rule |
| `tests/test_gate_e2e.sh` | `ops/graphiti/test_gate_e2e.sh` | Basic gate test |
| `tests/test_gate_e2e_full.sh` | `ops/graphiti/test_gate_e2e_full.sh` | Full gate test |
| `docs/DEPLOY.md` | `ops/graphiti/DEPLOY.md` | Deployment guide |
| `docs/GATES-002-ACTIVATION.md` | `ops/graphiti/GATES-002-ACTIVATION.md` | Gate activation doc |
| `docs/MEMORY_BANK_POLICY.md` | `ops/graphiti/MEMORY_BANK_POLICY.md` | Memory bank policy |
| `docs/REUSE_MATRIX.md` | `ops/graphiti/REUSE_MATRIX.md` | Reuse matrix |
| `docs/CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md` | `ops/graphiti/docs/CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md` | Instantiation brief |
| `docs/MACHINE-ENV-POLICY.md` | `ops/graphiti/docs/MACHINE-ENV-POLICY.md` | Machine env policy |
| `docs/prune_report_20260607.json` | `ops/graphiti/prune_report_20260607.json` | Prune report |
| `scripts/init_graphiti_machine_env.sh` | `ops/scripts/init_graphiti_machine_env.sh` | Machine init script |
| `skill/SKILL.md` | `skills/l9-graphiti-memory/SKILL.md` | Agent skill definition |
| `_archived/docker-compose.yml` | `ops/graphiti/docker-compose.yml` | Deprecated VPS compose |
| `_archived/ensure_graphiti_tunnel.sh` | `ops/hooks/ensure_graphiti_tunnel.sh` | Deprecated SSH tunnel |

## Files NOT Extracted (Remain in Cursor-Governance)

- `rules/RULES-MANIFEST.json` — References graphiti rules but is a manifest for ALL rules
- `ops/hooks/end-session.sh` — Calls graphiti hooks but is a general session hook
- `learning/graphiti-episodes/` — Created by PR #10 (not yet merged)
- `intelligence/context-memory/sessions/` — Runtime session data (not source code)
