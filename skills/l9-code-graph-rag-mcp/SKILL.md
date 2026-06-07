---
name: l9-code-graph-rag-mcp
description: operate @er77/code-graph-rag-mcp for repo-local code structure — token-safe tool selection, cli indexing, importers, impact analysis, cross-module discovery. use when code-graph, batch_index, semantic code search, list_module_importers, analyze_code_impact, or mcp indexing is needed.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, mcp, code-graph, rag, token_discipline, plasticos]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-07
sources:
  - er77/code-graph-rag-mcp@v2.7.15
  - assets/user-execution-guide.md
---

# Code Graph RAG MCP (L9)

## Purpose

Operate **@er77/code-graph-rag-mcp** as a **repo-local code structure** graph (AST, imports, impact). Answers *where in code* and *who imports what* — not episodic memory (Graphiti + `memory-bank/` handle decisions and session resume).

## Core Contract

`AUTHORITY → TOOL GATE → INDEX VIA CLI → SCOPED MCP QUERY`

1. **Rules / AGENTS.md / Grep / Read** — cheapest; use when symbol or path is known.
2. **Index in Terminal only** — never `batch_index` or `index` in agent chat.
3. **Structural MCP tools** — importers, impact, entity resolution.
4. **Scoped `semantic_search`** — last resort; always include module or path hint.

## Authority Order

1. Repo rule **`87-plasticos-code-graph-rag`** (when present) and `AGENTS.md`.
2. **Grep / Read** for known symbols.
3. PlasticOS wiring scripts (`scripts/check_module_wiring.py`, manifests) before graph importers.
4. Code-graph **structural** tools (this skill).
5. Code-graph **semantic** tools — scoped only.
6. `Unknown` — stop; do not dump `get_graph` or unscoped search.

## Compact Workflow

1. **Confirm index** — user runs Terminal (zero chat tokens):

   ```bash
   export REPO_ROOT="/path/to/repo"
   export GOV_SKILLS="$HOME/Dropbox/Cursor Governance/GlobalCommands/skills/l9-code-graph-rag-mcp/scripts"
   bash "$GOV_SKILLS/code_graph_health.sh" "$REPO_ROOT"
   ```

2. **Seed if unhealthy** — `bash "$GOV_SKILLS/code_graph_batch_index.sh" "$REPO_ROOT"` (never in chat).

3. **Query** — prefer chain: `resolve_entity` → `get_entity_source` (minimal context).

4. **Cross-module** — `list_module_importers` or `analyze_code_impact` before editing shared models.

5. **After large refactors** — user re-runs batch index script; agent uses incremental awareness only.

Full terminal guide: [`assets/user-execution-guide.md`](assets/user-execution-guide.md).

## Tool Gate

### Allow (structural — prefer these)

| Tool | Use for |
|------|---------|
| `resolve_entity` | Disambiguate symbol names |
| `get_entity_source` | Small snippet, not whole files |
| `list_module_importers` | Who imports this module |
| `list_entity_relationships` | Import/call graph for one entity |
| `analyze_code_impact` | Blast radius before shared-model edits |
| `list_file_entities` | Symbols in one file |
| `semantic_search` | Only with module/path scope |

### Deny in chat (CLI or skip)

| Tool | Reason |
|------|--------|
| `batch_index`, `index`, `clean_index`, `reset_graph` | Run [`scripts/code_graph_batch_index.sh`](scripts/code_graph_batch_index.sh) in Terminal |
| `get_graph` | Dumps entire graph into context |
| `detect_code_clones`, `jscpd_detect_clones` | Audit-only; huge output |
| `suggest_refactoring` | Extra token burn |
| Unscoped `semantic_search` | Whole-repo context explosion |

## Memory Layer Boundary

| Layer | Answers |
|-------|---------|
| **code-graph RAG** | Where in code? Who imports? Impact radius? |
| **`memory-bank/`** (git) | What task were we on? |
| **Graphiti** (VPS) | What did we decide? Cross-repo edges? |
| **AGENTS.md / rules** | CI, Odoo patterns, module map |

Do not store decisions in code-graph or confuse layers.

## CLI Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/code_graph_batch_index.sh`](scripts/code_graph_batch_index.sh) | Seed/resume index until `done:true` |
| [`scripts/code_graph_health.sh`](scripts/code_graph_health.sh) | Health check; exit 0 = ready |
| [`scripts/code_graph_cli.py`](scripts/code_graph_cli.py) | Single-tool JSON-RPC helper for debug |

Install binary default: `$HOME/.local/code-graph-rag-mcp/node_modules/.bin/code-graph-rag-mcp` (override with `CODE_GRAPH_BIN`).

MCP config: `~/.cursor/mcp.json` server `code-graph-rag`. Recommended env: `MCP_EMBEDDING_PROVIDER=memory`, `MCP_TIMEOUT=800000`.

Index cache: `<repo>/.code-graph-rag/vectors.db` — gitignore `.code-graph-rag/`.

## Scoped Prompt Patterns

Copy-paste for users (agent must follow scope):

- **Known symbol:** `Grep for X in module/ — do not use code-graph.`
- **Importers:** `code-graph list_module_importers for plasticos_intake only.`
- **Impact:** `code-graph analyze_code_impact on plasticos.material.profile only.`
- **Unknown location:** `resolve_entity → get_entity_source; scope: plasticos_web_leads/ only.`

## Resource Map

- [`assets/plasticos-trigger-matrix.md`](assets/plasticos-trigger-matrix.md) — **when to read from graph** vs grep/read; path patterns; GMP Phase 0 triggers.
- [`assets/user-execution-guide.md`](assets/user-execution-guide.md) — install, seed, verify, token-minimal prompts, troubleshooting.
- [`scripts/code_graph_gmp_baseline.sh`](scripts/code_graph_gmp_baseline.sh) — GMP Phase 0 evidence generator (CLI).
- [`scripts/code_graph_plasticos_gate.py`](scripts/code_graph_plasticos_gate.py) — shared hook/gate logic.
- [`scripts/code_graph_batch_index.sh`](scripts/code_graph_batch_index.sh) — deterministic index loop.
- [`scripts/code_graph_health.sh`](scripts/code_graph_health.sh) — health probe.
- [`scripts/code_graph_cli.py`](scripts/code_graph_cli.py) — low-level tool invocation.

## Validation

- `code_graph_health.sh` exits 0 for target repo.
- MCP server `code-graph-rag` connected in Cursor after reload.
- Agent used structural tools before semantic; no chat indexing in session log.

## Failure Handling

| Symptom | Action |
|---------|--------|
| `healthy: false`, 0 entities | User runs `code_graph_batch_index.sh` — not agent |
| MCP disconnected | Reload Cursor; check `/tmp/code-graph-rag-mcp/mcp-server-*.log` |
| `agent_busy` / timeout | Do not index in chat; use CLI scripts |
| Stale graph after refactor | User re-runs batch index |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: run health script or scoped grep).
