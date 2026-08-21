---
name: Graphiti Global Memory
overview: "Two-GMP rollout on one architecture doc: GMP-GRAPHITI-GLOBAL-001 ships VPS + read-path memory (prefetch, memory-bank, rules, bootstrap); GMP-GRAPHITI-GATES-002 ships failClosed Write/Shell gates after prefetch is stable. GlobalCommands only; IB-Odoo code-graph overlay (87-plasticos-code-graph-rag) already wired."
todos:
  - id: phase0-prewrite
    content: "[GLOBAL-001] Pre-work gate — read graphiti 2/memory_tool.py, group_router.py, episode_contract.py; classify reuse-as-is / config-only / rewrite-required before Phase 1 lock"
    status: completed
  - id: phase0-vps
    content: "[GLOBAL-001] Deploy Neo4j 5.26 + Graphiti MCP :8100 on VPS; Tailscale; bearer auth; DEPLOY.md; ~/.cursor/graphiti.env + mcp.json graphiti-memory entry (secrets gitignored)"
    status: completed
  - id: phase1-kernel
    content: "[GLOBAL-001] Port ops/graphiti/ — CLI, registry, ontology, domain_packs, episode_contract, memory-bank-template/, prune.py; env flags GRAPHITI_MEMORY_ENABLED + GRAPHITI_WRITE_GATES (default 0)"
    status: completed
  - id: phase2a-orchestrator
    content: "[GLOBAL-001] sessionStart orchestrator — code-graph health + Graphiti inject; single additional_context blob; combined 15s budget; merge with existing code-graph-health.sh"
    status: completed
  - id: phase2a-read-hooks
    content: "[GLOBAL-001] graphiti-prefetch.sh + graphiti-session-end.sh T0 only + memory-bank scaffold; NO Write/Shell gates"
    status: completed
  - id: phase2b-write-gates
    content: "[GATES-002] reset-generation, mark-ok, gate-edits/shell/subagent + ~/.cursor/graphiti-state/<conv>.json; failClosed when GRAPHITI_WRITE_GATES=1"
    status: completed
  - id: phase3-rules
    content: "[GLOBAL-001] Rules 03/97/98/99 + l9-graphiti-memory; 98 gates conditional on GRAPHITI_WRITE_GATES; deprecate 03-mcp-memory; session YAML; CANONICAL_LAW; ADR-002 disambiguation (memory hooks ≠ Gate hub)"
    status: completed
  - id: phase3b-c1-decommission
    content: "[GLOBAL-001] Sweep C1 — learning_to_mcp_bridge.py, transcript_distiller.py, RULES-MANIFEST, 93-c1-server-protection; C1 read-only until Graphiti bootstrap passes"
    status: completed
  - id: phase4a-memory-bank-policy
    content: "[GLOBAL-001] memory-bank/ git policy — PlasticOS tracks memory-bank/; no auto-commit; scaffold never overwrites existing"
    status: completed
  - id: phase4-bootstrap-cutover
    content: "[GLOBAL-001] bootstrap dry-run + production slugs; disable C1 writes; wiring check; prefetch E2E only (no Write deny test)"
    status: completed
  - id: phase4b-gate-e2e
    content: "[GATES-002] Write deny/allow via forced state file; shell/subagent gates; tests independent of additional_context injection"
    status: completed
  - id: phase5-gmp-substrate
    content: "[GLOBAL-001] l9-gmp-protocol — Phase 0 MEMORY_PREFETCH + conflicts; Phase 6 Section 11; verify GMP cites prefetch"
    status: completed
  - id: phase5-gmp-gate-matcher
    content: "[GATES-002] graphiti-gate-edits GMP matcher (gmp:phase_lock); wiring check asserts matcher present"
    status: completed
  - id: phase6-hardening
    content: "[GLOBAL-001] Tune allowlist, prune cron, conflicts, optional OTel; GMP-GRAPHITI-GLOBAL-001 Final Declaration"
    status: completed
isProject: false
---

# Graphiti Global Memory Integration Plan v2.1

**GMP_RUN_ID:** `GMP-GRAPHITI-GLOBAL-001` (+ deferred `GMP-GRAPHITI-GATES-002`)  
**Version:** 2.1.0  
**GMP Format:** v3.2.0 (canonical, phases 0–6)  
**Date:** 2026-06-06  
**Status:** AWAITING PHASE 0 HUMAN APPROVAL

---

## GMP split (recursive alignment)

| GMP run | Ships | Deferred |
|---------|-------|----------|
| **GLOBAL-001** | VPS, kernel, prefetch + memory-bank, rules, C1 deprec, bootstrap, substrate GMP evidence | failClosed Write/Shell gates |
| **GATES-002** | gate-edits/shell/subagent, mark-ok, reset-generation, GMP `gmp:phase_lock` matcher, gate E2E | Until prefetch stable ~1–2 weeks |

**Feature flags** (`~/.cursor/graphiti.env`): `GRAPHITI_MEMORY_ENABLED=1` (master); `GRAPHITI_WRITE_GATES=0` until GATES-002.

**Not graph upload:** Cursor "Chat context summarized" = in-session compression only — not Graphiti, C1, or code-graph writes.

**Repo overlay:** Global `97-graph-layer-boundary.mdc` MUST cross-reference IB-Odoo `87-plasticos-code-graph-rag.mdc` (already wired).

**Naming:** Graphiti memory gate hooks ≠ PlasticOS ADR-002 Gate hub — state explicitly in `03-graphiti-memory.mdc`.

---

## Goal

One VPS-hosted Graphiti + Neo4j stack serves all Cursor repos. Memory is **mandatory via hooks** — not agent discretion. **Write gates ship in GATES-002** after read-path prefetch is stable. C1 (`46.62.243.82/memory`) and Cursor native Memories are retired. Git-tracked `memory-bank/` holds zero-LLM resume state. Graphiti holds distilled episodic knowledge at minimal token cost. `@er77/code-graph-rag-mcp` serves structural code navigation and is **not** a Graphiti substitute — it occupies a separate, cheaper tier.

---

## Architecture: Four Memory Layers

```mermaid
flowchart TB
  subgraph structural [Structural — $0 LLM]
    CG[code-graph-rag]
  end
  subgraph git_layer [Git — $0 LLM]
    MB[memory-bank/]
  end
  subgraph graph [VPS Graphiti]
    RG[repo group_id]
    WS[igor-workspace]
  end
  HooksStart[sessionStart] -->|read| MB
  HooksStart -->|prefetch| graph
  Agent[Cursor Agent] -->|structure| CG
  HooksEnd[sessionEnd] -->|T0| MB
  HooksEnd -->|T1 episode| RG
```

| Layer               | Answers                                     | Write trigger                      | LLM cost                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------- | ------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `code-graph-rag`    | Where in code? Who imports? Blast radius?   | CLI batch_index (terminal only)    | $0  |
| `memory-bank/`      | What task? What's next?                     | sessionEnd template                | $0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Graphiti            | What did we decide? Cross-repo constraints? | Hook + `source=json`, rate-limited | Per episode (controlled)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `AGENTS.md` / rules | Non-negotiable instructions                 | Human PR only                      | $0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

**Retrieval authority order (canonical — embed in rule** `03-graphiti-memory.mdc`**):**

1. Rules / `AGENTS.md` — always in context, $0
2. Grep / Read — when symbol or path known, $0
3. **code-graph structural MCP** — importers, impact, entity location, $0
4. Scoped code-graph semantic — only with module path hint
5. **Graphiti episodic MCP** — decisions, ADRs, constraints, CI gotchas
6. `Unknown` — STOP; state gap; do not dump `get_graph` or unscoped search

---

## Namespace Design

**Default namespace caveat:** Graphiti MCP server defaults unspecified `group_id` to `"default"` (verify against your installed version — some builds use `"main"`). Both are **forbidden** in production.

| `group_id`                | Scope                    | Example content                            |
| ------------------------- | ------------------------ | ------------------------------------------ |
| `igor-workspace`          | Cross-repo topology      | Integration edges, depends-on facts        |
| `ib-odoo-19`              | PlasticOS repo           | ADR decisions, GMP phase locks, CI gotchas |
| `cursor-governance`       | GlobalCommands repo      | CANONICAL_LAW, hook paths, skill registry  |
| `cognitive-engine-graphs` | CEG repo                 | Gate/CEG boundary notes                    |
| *(per-repo slug)*         | One slug per GitHub repo | Derived: `IB-Odoo_19` → `ib-odoo-19`       |

**Forbidden groups:** `["main", "default", "", "test"]`

## Registry file: `GlobalCommands/ops/graphiti/group_registry.yaml`

```
text
```

`schema_version: 2 workspace_group: igor-workspace forbidden_groups: [main, default, "", test] resolution:   order: [explicit_env, git_remote_match, path_hint_match]   on_failure: abort_write_allow_readonly   # never silent-default repos:   ib-odoo-19:     github: cryptoxdog/IB-Odoo_19     path_hints: ["IB-Odoo_19", "IB_Odoo"]     remote_patterns: ["*/IB-Odoo_19*"]     integrates_with: [cursor-governance, cognitive-engine-graphs]   cursor-governance:     github: cryptoxdog/Cursor-Governance     remote_patterns: ["*/Cursor-Governance*"]     path_hints: ["Cursor-Governance", "GlobalCommands"]`

**Slug resolver contract:**

1. `GRAPHITI_GROUP_ID` env set → use it (must pass `VALID_GROUP_PREFIXES`)
2. `git remote get-url origin` → match `remote_patterns`
3. `cwd` → match `path_hints`
4. **No match / ambiguous → abort writes; read-only against** `igor-workspace` **only; emit loud** `additional_context` **warning**
5. Monorepo/worktree: multiple matches → require explicit `GRAPHITI_GROUP_ID` or fail closed

---

## VPS Deployment

## Stack (`GlobalCommands/ops/graphiti/docker-compose.yml`)

```
text
```

`# Adapt from graphiti 2/docker-compose.yml after reading source # Key constraints: services:   neo4j:     image: neo4j:5.26-community         # verify LTS compatibility at deploy time     environment:       NEO4J_dbms_default__database: graphiti_cursor   # dedicated DB — not PlasticOS Neo4j     ports:       - "127.0.0.1:7474:7474"       - "127.0.0.1:7687:7687"           # loopback only on VPS   graphiti-mcp:     image: zepai/graphiti:latest         # or build from getzep/graphiti mcp_server     ports:       - "127.0.0.1:8100:8000"           # SINGLE PORT: 8100 external, 8000 internal     environment:       NEO4J_URI: bolt://neo4j:7687       MODEL_NAME: gpt-4o-mini       SMALL_MODEL_NAME: gpt-4o-mini       EMBEDDER_NAME: text-embedding-3-small       GRAPHITI_TELEMETRY_ENABLED: "false"       GRAPHITI_MCP_TOKEN: ${GRAPHITI_MCP_TOKEN}    # bearer auth — never empty`

**Access:** Tailscale only. Mac → VPS via Tailscale IP `100.x.x.x`. Never public-internet expose.

## `~/.cursor/mcp.json` (Mac)

```
json
```

`{   "mcpServers": {     "graphiti-memory": {       "url": "http://100.x.x.x:8100/mcp/",       "headers": {"Authorization": "Bearer ${GRAPHITI_MCP_TOKEN}"}     },     "code-graph-rag": {       "command": "/Users/igor/.local/code-graph-rag-mcp/node_modules/.bin/code-graph-rag-mcp",       "args": ["${REPO_ROOT}"],       "env": {         "MCP_EMBEDDING_PROVIDER": "memory",         "MCP_TIMEOUT": "800000"       }     }   } }`

**Both graphs coexist with no tool-name collision** — `graphiti-memory` namespace prefix separates Graphiti tools from `code-graph-rag` tools.

## `~/.cursor/graphiti.env` (secrets — names only here)

```
bash
```

`GRAPHITI_MCP_URL=http://100.x.x.x:8100/mcp/ GRAPHITI_MCP_TOKEN=...            # MCP bearer auth — defense-in-depth over Tailscale GRAPHITI_NEO4J_URI=bolt://100.x.x.x:7687 OPENAI_API_KEY=...                # scoped project key, low spend cap, extraction only MEMORY_TOKEN_BUDGET=400 MEMORY_RATE_LIMIT_MIN=10 MEMORY_RATE_LIMIT_HR=200 GRAPHITI_TELEMETRY_ENABLED=false MEMORY_DISTILL_TOKEN_BUDGET=300   # cap on session-end gpt-4o-mini distillation call`

**Secret-handling rules:** hooks must `set +x`; trap errors to redacting handler; never `echo` env file; `episode_contract.py` regex-scans for `sk-`, JWT shapes, `bolt://...@` before any ingest.

---

## GlobalCommands Deliverables

## File classification (honest reuse mapping)

| Planned file                | Source                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Classification        | Notes                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------- |
| `docker-compose.yml`        | `graphiti 2/docker-compose.yml`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | **Reuse + adapt**     | Change port, add `GRAPHITI_MCP_TOKEN`, dedicated DB name                  |
| `graphiti_memory_client.py` | `code_graph_cli.py` shape  + `graphiti 2/memory_tool.py` | **New, proven shape** | CLI wrapper pattern from code-graph; rate limiter/budget from memory_tool |
| `group_registry.yaml`       | Plan design                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | **New config**        | ~30 lines YAML                                                            |
| `ontology_coding.py`        | Graphiti `--use-custom-entities` pattern                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | **New, ~60 lines**    | Pydantic entity types; not a full module                                  |
| `domain_packs.yaml`         | `graphiti 2/domain_packs.yaml`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | **Reuse + extend**    | Add coding pack, remove IgorBot noise; use allowlist_only mode            |
| Hook scripts (6 scripts)    | IgorBot hook pattern                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | **New**               | Shell wrappers; no equivalent in source                                   |
| `memory-bank-template/`     | None                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | **New**               | 4 markdown templates                                                      |
| Rules (3 new `.mdc` files)  | None                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | **New**               | Policy only                                                               |

> **Pre-work gate (before Phase 1):** Read `graphiti 2/memory_tool.py`, `group_router.py`, `episode_contract.py` to confirm rate-limiter, circuit-breaker, PII-filter are present as described. Mark each as reuse-as-is / config-only / rewrite-required. This is not optional — "reuse" is unverified until read .

## Deliverable 1 — CLI client

`GlobalCommands/ops/graphiti/graphiti_memory_client.py`

Shape mirrors `code_graph_cli.py`: one-shot subprocess/MCP call, `resolve_bin`/`resolve_repo` env fallbacks, robust JSON-RPC output parsing, health exit codes. **Terminal-only heavy ops; agent never calls** `bootstrap` **or** `batch` **in chat.**

| Command                                      | Graphiti action                                                       | Notes                       |
| -------------------------------------------- | --------------------------------------------------------------------- | --------------------------- |
| `health`                                     | MCP `/health` + circuit state + resolver self-test                    | Exits 0 or 1                |
| `search QUERY`                               | `search_facts` token-budgeted, group slug + `igor-workspace`          | `MEMORY_TOKEN_BUDGET` cap   |
| `write BODY --kind lesson\|pickup\|manifest` | Validated `EpisodeContract`; `source=json`; search-before-write dedup | T1/T2 tiers                 |
| `inject TASK`                                | Prefetch + emit `task_signature` to state file                        | sessionStart hook uses this |
| `bootstrap`                                  | Convention-agnostic source discovery → 1 manifest episode             | CLI / terminal only         |
| `stats`                                      | Group node counts via Neo4j                                           | Admin/debug                 |
| `resolve`                                    | Print resolved `group_id` for cwd                                     | Debug; used in wiring check |
| `conflicts`                                  | List `conflicts_with` edges for group                                 | Human review queue          |
| `prune --dry-run`                            | Retention report (no deletes without approval)                        | Weekly cron candidate       |

Portable path: `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py` (via symlink).

**Search-before-write (T1/T2):** on every write, client searches for near-duplicate episodes in the same `group_id`. If ADR/decision found → emit `Supersedes` relationship from new to old (lean on Graphiti's native bi-temporal invalidation; only add explicit `conflicts_with` edges where engine cannot auto-resolve). Never silently merge or drop.

## Deliverable 2 — Coding ontology

`GlobalCommands/ops/graphiti/ontology_coding.py` (~60 lines, Pydantic, passed via `--use-custom-entities`)

```
python
```

`# Entity types (allowlist_only — reject off-list entities) entity_types = [     RepoManifest, Module, ADRDecision, GMPPhase,     ModificationLock, CIGotcha, TechDebtItem, Preference ] # Edge types edge_types = [DependsOn, Supersedes, IntegratesWith, Blocks, Documents, ConflictsWith]`

`domain_packs.yaml` `coding` pack — `extraction_mode: allowlist_only`. Not an exclusion list (unbounded, leaky) — a positive allowlist. IgorBot noise (`FamilyMember`, `RoofingJob`, etc.) excluded as secondary safety net only.

## Deliverable 3 — `memory-bank/` template

`GlobalCommands/ops/graphiti/memory-bank-template/`

```
text
```

`memory-bank/   activeContext.md   # where we left off (1 screen max)   tasks.md           # queued work   progress.md        # done this sprint   tech-debt.md       # revisit later`

`setup_workspace_symlinks.sh`: scaffold if missing, **never overwrite existing**. `sessionStart` reads all four into `additional_context` before Graphiti. `sessionEnd` updates `activeContext.md` + `tasks.md` via deterministic template — no LLM (T0).

## Deliverable 4 — Gate state object

`~/.cursor/graphiti-state/<conv>.json` (written by `graphiti-prefetch.sh`, read by gate scripts)

```
json
```

`{   "group_id": "ib-odoo-19",   "prefetch_ts": "2026-06-06T21:08:00Z",   "prefetch_hash": "sha256:...",   "task_signature": "edit:gate_module",   "memory_satisfied_for": ["edit:gate_module"],   "circuit_state": "closed",   "cache_ttl_minutes": 30 }`

Gate logic: deny Write/Shell when task signature **not** in `memory_satisfied_for` AND prefetch is stale (> TTL). Task signature derived from files/intent in the turn, not global. `beforeSubmitPrompt` reset is **task-scoped** — only clears satisfaction when task signature changes, not on every turn.

## Deliverable 5 — User-global hooks

Extend `GlobalCommands/ops/hooks/hooks.json.template`:

| Hook                   | Script                         | Behavior                                                                                                                                                                                                                 |
| ---------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sessionStart`         | `session_start_memory_orchestrator.sh` | code-graph health then Graphiti prefetch; single `additional_context`; 15s budget |
| `beforeSubmitPrompt`   | `graphiti-reset-generation.sh` | Task-scoped reset — clear `memory_satisfied_for` only when task signature changes                                                                                                                                        |
| `postToolUse`          | `graphiti-mark-ok.sh`          | Matcher: Graphiti MCP tools → add current `task_signature` to `memory_satisfied_for`                                                                                                                                     |
| `preToolUse`           | `graphiti-gate-edits.sh`       | Matcher: Write|Shell|Delete|Task → deny if task_sig not satisfied AND prefetch stale; `failClosed`                                                                                                                       |
| `beforeShellExecution` | `graphiti-gate-shell.sh`       | Deny `git commit`, `make push` if gate not satisfied                                                                                                                                                                     |
| `subagentStart`        | `graphiti-gate-subagent.sh`    | Inherit parent `task_signature`; deny if parent not satisfied                                                                                                                                                            |
| `sessionEnd`           | `graphiti-session-end.sh`      | T0: update memory-bank (template, no LLM); T1: bounded `gpt-4o-mini` call (cap `MEMORY_DISTILL_TOKEN_BUDGET=300`) → 1 distilled JSON episode + Supersedes edges; mirror edge to `igor-workspace` if integrations changed |
| `sessionEnd`           | `governance-backup.sh`         | Existing — keep as-is                                                                                                                                                                                                    |

**Allowlist (no gate):** Read, Grep, Glob, SemanticSearch, Graphiti MCP itself, code-graph-rag MCP.

**Secret safety:** all hook scripts open with `set +x`; errors trapped to redacting handler; env file sourced with no echo.

## Deliverable 6 — Rules + deprecations

| Action    | File                                                                       | `alwaysApply`                                                                                                           |
| --------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Add       | `rules/03-graphiti-memory.mdc`                                             | Yes — SSOT; retrieval authority ladder; forbids Cursor `update_memory` for repo facts; forbids code-graph for decisions |
| Add       | `rules/98-graphiti-memory-gate.mdc`                                        | Yes — `group_id` contract; forbid `main`/`default`; task-scoped gate spec; GMP Phase 0 must cite prefetch               |
| Add       | `rules/99-graphiti-temporal.mdc`                                           | Yes — Supersedes contract; conflicts_with surfacing; bi-temporal invalidation policy                                    |
| Add       | `rules/97-graph-layer-boundary.mdc`                                        | Yes — code-graph answers structure; Graphiti answers decisions; do not confuse graphs; naming contract                  |
| Deprecate | `rules/03-mcp-memory.mdc`                                                  | — banner: superseded by Graphiti; remove C1 endpoints                                                                   |
| Update    | `87-cursor-memory-kernel.mdc`                                              | — memory-bank replaces `workflow_state.md`; Graphiti replaces C1                                                        |
| Update    | `85-workflow-state-bridge.mdc`                                             | — memory-bank is resume SSOT                                                                                            |
| Update    | `start-session.yaml` Step 3.5                                              | — `blocking: true`, command → `graphiti_memory_client.py health`                                                        |
| Update    | `end-session.yaml`, `l9-end-session/SKILL.md`, `commands/start-session.md` | — all C1 → Graphiti                                                                                                     |
| Add       | `skills/l9-graphiti-memory/SKILL.md`                                       | — when to write JSON vs memory-bank only; retrieval authority; layer boundary                                           |

**Cursor Settings (manual, document in skill):** disable native Memories for repo/code facts.

## Deliverable 7 — Bootstrap per repo (one-time, idempotent)

`graphiti_memory_client.py bootstrap` — convention-agnostic source discovery:

```
text
```

`priority: [AGENTS.md, ARCHITECTURE.md, docs/adr/*, README.md,            SOUL.md, IDENTITY.md, BOOTSTRAP.md, memory-bank/activeContext.md]`

Emits one `source=json` `RepoManifest` episode:

```
json
```

`{   "repo_slug": "ib-odoo-19",   "github": "cryptoxdog/IB-Odoo_19",   "stack": "Odoo 19 / PlasticOS",   "branch_model": {"dev": "Staging", "prod": "Production"},   "integrates_with": [{"group_id": "cursor-governance", "via": ".cursor-commands symlink"}] }`

Mirror to `igor-workspace` as `IntegratesWith` edge episode. Idempotent via seed-name hash. **Dry-run first against sandbox** `group_id` **(not production slug) to verify entity quality before real bootstrap.**

Auto-triggered from `setup_workspace_symlinks.sh` when registry match + not yet seeded.

## Deliverable 8 — Wiring validation

Extend `check_governance_wiring.sh`:

```
bash
```

`# Both graphs bash GOV_SKILLS/code_graph_health.sh "$REPO_ROOT"        # code-graph healthy python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health  # Graphiti healthy  # Resolver python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve  # prints slug for cwd  # Hooks grep -l "graphiti-prefetch\|graphiti-gate" ~/.cursor/hooks.json  # Registry python3 -c "import yaml; yaml.safe_load(open('ops/graphiti/group_registry.yaml'))"  # Tailscale + MCP reachability curl -sf -H "Authorization: Bearer $GRAPHITI_MCP_TOKEN" "$GRAPHITI_MCP_URL"health  # memory-bank [ -d memory-bank ] || echo "WARN: memory-bank/ missing — run setup_workspace_symlinks.sh"  # No main/default writes python3 -c " import yaml; r = yaml.safe_load(open('ops/graphiti/group_registry.yaml')) assert 'main' in r['forbidden_groups'], 'FAIL: main not in forbidden_groups' assert 'default' in r['forbidden_groups'], 'FAIL: default not in forbidden_groups' "`

Add to `start-session.md` preflight checklist.

## Deliverable 9 — Pruning actor (scheduled)

`GlobalCommands/ops/graphiti/prune.py` — weekly VPS cron:

- Demote `igor-workspace` integration edges with no reads in 90d
- Expire transient episodes past `valid_until`
- **Report** (not auto-delete) candidate stale ADRs for human review
- Emit `graphiti.prune.demoted_count` metric (OTel)

---

## Token / Cost Controls

**Write tiers:**

| Tier | Destination           | When                                                                   | LLM cost            |
| ---- | --------------------- | ---------------------------------------------------------------------- | ------------------- |
| T0   | `memory-bank/` only   | Every session end (deterministic template)                             | $0                  |
| T1   | Graphiti JSON episode | Session end summary (1 episode, bounded `gpt-4o-mini`, cap 300 tokens) | Minimal, controlled |
| T2   | Graphiti JSON episode | GMP phase lock, ADR applied, non-obvious CI fix                        | Per episode         |
| T3   | Graphiti (forbidden)  | Raw conversation — disabled by `episode_contract.py`                   | Never               |

**Runtime controls (port from** `memory_tool.py` **after reading source):**

- `MEMORY_TOKEN_BUDGET=400` on all inject/prefetch paths
- `search_budgeted` not raw `search_facts`
- Rate limiter: 10/min, 200/hr
- `source=json` for bootstrap, GMP locks, session summaries — skip message-type LLM extraction
- `add_episode_async` for sessionEnd writes (non-blocking)
- Circuit breaker: memory-bank still loads; gate falls back to cached prefetch (TTL 30m) when VPS unreachable
- No full chat ingestion — ever — enforced at contract level

---

## GMP Protocol Integration

## Phase 0 additions for any GMP run touching memory

Before locking any TODO plan that writes to or reads from memory:

1. Call `graphiti_memory_client.py inject "{task}"` — confirm prefetch in `additional_context`
2. Call `graphiti_memory_client.py conflicts` — list unresolved conflicts for group; address or document before proceeding
3. Cite Graphiti prefetch in Phase 0 plan header: `MEMORY_PREFETCH: {episode_names}`
4. ADR reading: memory operations → also read `group_registry.yaml` and `03-graphiti-memory.mdc` before locking plan

## Phase 3 governance additions for memory-touching TODOs

New capabilities governed:

- Any new episode write path → add to `episode_contract.py` allowed kinds
- Any new hook → add to `hooks.json.template` + document in `check_governance_wiring.sh`
- Approval required for: any `group_registry.yaml` mutation, any `forbidden_groups` change, any `bootstrap` run against production slug

## Phase 6 evidence report additions — memory section

Section 11 (Graphiti Memory Evidence) added to standard 10-section report:

```
text
```

`## 11. Graphiti Memory Evidence - Episodes written this GMP run: {names} - group_id used: {slug} - Supersedes edges emitted: {count} - Conflicts surfaced: {count} - memory-bank updated: YES/NO - Token spend (T1 distill): {tokens} - circuit_state at close: {closed|open}`

## Stricter `preToolUse` for GMP prompts

**Scope: GATES-002 only** (when `GRAPHITI_WRITE_GATES=1`).

When prompt matches `GMP|phase [0-6]|modification lock|TODO plan`:

- Gate requires Graphiti prefetch **AND** conflicts check completed this session
- Deny if `memory_satisfied_for` does not include `gmp:phase_lock`
- `graphiti-gate-edits.sh` extended with GMP-specific matcher

---

## Rollout Phases (GMP-Aligned)

## Phase 0 — VPS Infra (human + terminal)

**GMP role:** Infrastructure only — no Cursor agent involvement

- Read `graphiti 2/memory_tool.py`, `group_router.py`, `episode_contract.py` — classify each as reuse-as-is / config-only / rewrite-required (pre-work gate before any TODO plan locks)
- Deploy Neo4j 5.26 on VPS: dedicated DB `graphiti_cursor`, loopback bind `127.0.0.1`
- Deploy Graphiti MCP: port `8100` external, `GRAPHITI_MCP_TOKEN` set, `docker compose up`
- Install Tailscale Mac ↔ VPS
- Verify `curl -sf -H "Authorization: Bearer $GRAPHITI_MCP_TOKEN" http://100.x.x.x:8100/health` → `{"healthy":true}`
- Verify Neo4j: `cypher-shell -a bolt://100.x.x.x:7687 "RETURN 1"`
- Verify default namespace: confirm `"default"` vs `"main"` → update `forbidden_groups` accordingly
- Document connection details (names only, no secrets) in `GlobalCommands/ops/graphiti/DEPLOY.md`
- Add `~/.cursor/graphiti.env` on Mac; add to `.gitignore` globally

**DoD:** Health endpoint returns healthy with bearer token. Neo4j DB isolated. No public exposure. All secrets in `.env`, none in git.

---

## Phase 1 — Kernel Port to GlobalCommands

**GMP role:** Phase 0 TODO plan lock + Phase 1 baseline

**Protected files for this phase:** `hooks.json.template` (read-only until Phase 2), existing `setup_workspace_symlinks.sh` (extend, do not overwrite)

**TODO plan targets:**

- `GlobalCommands/ops/graphiti/` — create directory
- `docker-compose.yml` — adapted from `graphiti 2/` source
- `graphiti_memory_client.py` — new CLI (shape from `code_graph_cli.py` )
- `ontology_coding.py` — new, ~60 lines Pydantic
- `domain_packs.yaml` — extend from `graphiti 2/` source, add `coding` allowlist pack
- `group_registry.yaml` — new config
- `memory-bank-template/` — 4 markdown files

**Checklist:**

- `graphiti 2/` source files read and classified before any TODO locked
- `graphiti_memory_client.py health` exits 0 against VPS
- `graphiti_memory_client.py resolve` prints `ib-odoo-19` from PlasticOS cwd
- `graphiti_memory_client.py bootstrap --dry-run` emits valid JSON episode without writing
- Ontology accepted by Graphiti `--use-custom-entities` without error
- `domain_packs.yaml` `coding` pack loads; allowlist_only mode verified
- `memory-bank-template/` scaffolds to `memory-bank/` via `setup_workspace_symlinks.sh` on test clone

**DoD:** CLI functional against VPS. Resolver correct for all active repos. Bootstrap dry-run clean. No secrets in any committed file.

---

## Phase 2 — Hooks + Wiring

**Split:** Phase **2a** (GLOBAL-001, read path) ships first; Phase **2b** (GATES-002, write enforcement) deferred.

### Phase 2a — Read path (GLOBAL-001)

**GMP role:** Prefetch + sessionEnd T0; no failClosed gates

**TODO plan targets:**

- `GlobalCommands/ops/hooks/session_start_memory_orchestrator.sh` — code-graph health then Graphiti inject; 15s combined budget
- `GlobalCommands/ops/hooks/graphiti-prefetch.sh` — resolve slug; read memory-bank; inject; write state JSON
- `GlobalCommands/ops/hooks/graphiti-session-end.sh` — T0 template update to memory-bank only (T1 distill may ship here or in 2b)
- `hooks.json.template` — single `sessionStart` → orchestrator (merge-safe with governance-backup sessionEnd)
- `setup_workspace_symlinks.sh` — install hooks + scaffold memory-bank

**Checklist (2a):**

- `sessionStart` fires; `additional_context` contains memory-bank + Graphiti prefetch (best-effort)
- `sessionEnd` writes `memory-bank/activeContext.md` (deterministic template, no LLM)
- Circuit breaker: VPS down → memory-bank still loads; session not blocked
- Gate hooks NOT registered when `GRAPHITI_WRITE_GATES=0`

**DoD (2a):** Fresh session loads memory-bank + Graphiti context without agent invoking MCP. No Write blocking.

### Phase 2b — Write gates (GATES-002)

**GMP role:** failClosed enforcement; activate only when `GRAPHITI_WRITE_GATES=1`

**TODO plan targets:**

- `graphiti-reset-generation.sh`, `graphiti-mark-ok.sh`, `graphiti-gate-edits.sh`, `graphiti-gate-shell.sh`, `graphiti-gate-subagent.sh`
- `~/.cursor/graphiti-state/<conv>.json` with `task_signature` + `memory_satisfied_for`

**Checklist (2b):**

- `preToolUse` deny/allow verified via **forced state file** (not agent quoting prefetch)
- `preToolUse` allows Read/Grep/Glob/SemanticSearch/code-graph unconditionally
- `beforeShellExecution` denies `git commit` / `make push` when gate not satisfied
- `postToolUse` marks satisfaction after Graphiti search

**DoD (2b):** Write/Shell blocked until task_sig satisfied. Gates work even if `additional_context` dropped.

---

## Phase 3 — Rules + Session Protocol

**GMP role:** Phase 0 plan → Phase 2 implementation (doc/rule files only)

**TODO plan targets:**

- `rules/03-graphiti-memory.mdc` — new (alwaysApply)
- `rules/98-graphiti-memory-gate.mdc` — new (alwaysApply)
- `rules/99-graphiti-temporal.mdc` — new (alwaysApply)
- `rules/97-graph-layer-boundary.mdc` — new (alwaysApply)
- `rules/03-mcp-memory.mdc` — deprecation banner + C1 endpoint removal
- `rules/87-cursor-memory-kernel.mdc` — update memory-bank reference
- `rules/85-workflow-state-bridge.mdc` — update SSOT reference
- `start-session.yaml` — add Step 3.5 `blocking: true` health check
- `end-session.yaml` — C1 → Graphiti
- `commands/start-session.md` — preflight checklist update
- `skills/l9-end-session/SKILL.md` — C1 → Graphiti
- `skills/l9-graphiti-memory/SKILL.md` — new skill
- `CANONICAL_LAW.md` — memory section update
- **C1 decommission sweep:** `learning_to_mcp_bridge.py`, `transcript_distiller.py`, `RULES-MANIFEST.*`, `93-c1-server-protection.mdc`
- `97-graph-layer-boundary.mdc` — cross-ref repo overlay `87-plasticos-code-graph-rag.mdc`
- `03-graphiti-memory.mdc` — one line: memory gate hooks ≠ ADR-002 Gate hub

**Checklist:**

- `03-graphiti-memory.mdc` includes retrieval authority ladder (4 tiers + code-graph tier)
- `97-graph-layer-boundary.mdc` includes explicit "do not confuse code-graph and Graphiti" contract
- `98-graphiti-memory-gate.mdc` forbids `main` and `default` namespaces; Write gates apply only when `GRAPHITI_WRITE_GATES=1`
- `99-graphiti-temporal.mdc` specifies Supersedes contract and conflicts surfacing
- `start-session.yaml` Step 3.5 blocking health check fires before agent work
- `03-mcp-memory.mdc` shows deprecation banner; C1 references removed
- All session YAML files reference Graphiti, not C1
- `skills/l9-graphiti-memory/SKILL.md` covers write-tier decision (T0/T1/T2)
- `CANONICAL_LAW.md` memory section reflects four-layer model

**DoD:** No file in GlobalCommands references C1 endpoints for memory. All four rules active and alwaysApply. Session protocol updated end-to-end.

---

## Phase 4 — Bootstrap + Cutover

**GMP role:** Terminal + human verification; no Cursor agent edits

**memory-bank/ policy (phase4a):** PlasticOS commits `memory-bank/`; other repos optional; sessionEnd never auto-commits; scaffold never overwrites.

- Dry-run bootstrap: `graphiti_memory_client.py bootstrap --dry-run --group-id sandbox-test` — verify episode JSON quality
- Real bootstrap `ib-odoo-19`: `graphiti_memory_client.py bootstrap` from PlasticOS cwd
- Real bootstrap `cursor-governance`: from GlobalCommands cwd
- Verify: `graphiti_memory_client.py stats --group ib-odoo-19` shows RepoManifest entity
- Verify: `igor-workspace` has `IntegratesWith` edge from `ib-odoo-19` → `cursor-governance`
- Disable C1 writes: stop `cursor_memory_client.py` writes; add deprecation warning to C1 client
- Disable Cursor native Memories for repo facts (manual Cursor Settings + rule enforcement)
- End-to-end validation **(GLOBAL-001 — prefetch only):**
  - Open Cursor in PlasticOS → `additional_context` includes `activeContext.md` + Graphiti prefetch
  - End session → `memory-bank/activeContext.md` updated (check git diff)
  - End session → exactly 1 new Graphiti JSON episode in `ib-odoo-19` (verify via `stats`)
- **Write deny/allow E2E → deferred to GATES-002 (phase4b)**
- `check_governance_wiring.sh` passes clean on fresh clone after `setup_workspace_symlinks.sh`
- code-graph-rag health check included in wiring script exits 0

**DoD:** Zero C1 writes after cutover date. Zero `group_id=main/default` writes. Both graphs healthy. Prefetch session cycle verified. Write gates verified separately under GATES-002.

---

## Phase 5 — GMP Integration

**Split:** substrate (GLOBAL-001) vs gate matcher (GATES-002).

### Phase 5a — Substrate (GLOBAL-001)

- Update `l9-gmp-protocol` Phase 0 template: add "MEMORY_PREFETCH: cite episode names" field
- Update Phase 0 template: add mandatory `graphiti_memory_client.py conflicts` check before plan lock
- Update Phase 6 evidence report template: add Section 11 (Graphiti Memory Evidence)
- Verify: GMP run against PlasticOS — Phase 0 cites prefetch; Phase 6 report includes Section 11

**DoD (5a):** GMP runs cite Graphiti prefetch in Phase 0 and memory evidence in Phase 6.

### Phase 5b — Gate matcher (GATES-002)

- Update `graphiti-gate-edits.sh`: GMP matcher — deny if prompt matches GMP pattern and `gmp:phase_lock` not in `memory_satisfied_for`
- `check_governance_wiring.sh`: assert GMP gate matcher present when `GRAPHITI_WRITE_GATES=1`

**DoD (5b):** GMP prompts stricter under active write gates only.

---

## Phase 6 — Recursive Hardening

**GMP role:** Convergence passes; no new architecture

- Review first 2 weeks of VPS episode logs: tune `coding` allowlist from false-positive entities
- Review `graphiti.prune.demoted_count` and circuit breaker trip logs; adjust rate limits
- Add new repos to `group_registry.yaml` as needed
- Run `graphiti_memory_client.py conflicts` across all groups; resolve or document each
- Verify `Supersedes` edges present for any superseded ADR/decision
- Optional: extract `cursor_rules.md` Graphiti content → User Rules in Cursor
- Optional: add OTel collector on loopback; verify `graphiti.prefetch.latency_ms`, `graphiti.episode.write_count`, `graphiti.gate.denied_count` metrics flowing
- Wiring check clean after all tuning changes

**DoD:** False-positive entity rate < 5% (manual spot check on 20 episodes). Rate limits tuned. All known conflicts resolved or documented. Evidence: `RECURSIVE VERIFICATION REPORT` for GMP-GRAPHITI-GLOBAL-001 complete.

---

## Success Criteria

| Criterion | GMP | Verification |
| --------- | --- | ------------ |
| Session starts with memory-bank + Graphiti context without agent calling MCP | GLOBAL-001 | Check `additional_context` in first Cursor message (best-effort) |
| Write/Shell denied until Graphiti search or task-scoped prefetch satisfied | **GATES-002** | Force `memory_satisfied_for=[]` in state file; attempt Write; confirm deny |
| Zero production writes to `group_id=main` or `group_id=default` | GLOBAL-001 | `graphiti_memory_client.py stats --group main` → 0 nodes |
| C1 client produces deprecation warning | GLOBAL-001 | Run legacy command; confirm warning in output |
| Session end: memory-bank updated + ≤1 Graphiti JSON episode | GLOBAL-001 | `git diff memory-bank/`; `stats` before/after |
| `make governance-backup` + wiring check passes on fresh clone | GLOBAL-001 | CI / manual |
| Resume after 30+ days: `activeContext.md` + Graphiti manifest returned | GLOBAL-001 | Simulate: clear Cursor context; open repo; verify prefetch |
| code-graph and Graphiti coexist without tool-name collision | GLOBAL-001 | Check `~/.cursor/mcp.json`; both servers green |
| GMP Phase 0 cites Graphiti prefetch | GLOBAL-001 | Check Phase 0 output of first GMP run after cutover |
| GMP prompts blocked without `gmp:phase_lock` when gates on | **GATES-002** | GMP run with `GRAPHITI_WRITE_GATES=1`; verify deny then allow |

---

## Risk Mitigations

| Risk                               | Mitigation                                                                                   |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| Agent ignores MCP                  | Hooks prefetch + task-scoped Write gate (not rules alone)                                    |
| Token burn                         | JSON episodes, allowlist extraction, rate limits, budget cap, T3 disabled by contract        |
| Multi-repo confusion               | `group_registry` + slug resolver + `on_failure: abort_write`                                 |
| Multi-graph confusion              | `97-graph-layer-boundary.mdc` rule + naming contract in both graph server names              |
| VPS unreachable                    | Circuit breaker; memory-bank loads; gate uses cached prefetch (TTL 30m)                      |
| Competing memory                   | Deprecate C1 rule; rule-forbid Cursor Memories for repo facts                                |
| Temporal drift / conflicting facts | Supersedes edges on every superseding write; `conflicts_with` surfacing; weekly prune report |
| "Reuse" turns out to be rewrite    | Pre-work gate: read `graphiti 2/` source before any TODO plan locks                          |
| MCP bearer token compromised       | Tailscale + bearer = two independent controls; rotate token via env only                     |

---

## Out of Scope

- Migrating legacy C1 PostgreSQL/PacketStore data into Graphiti — bootstrap fresh per repo
- PlasticOS runtime Neo4j (buyer matching) — remains separate DB, separate stack
- OpenClaw/IgorBot call pipeline integration — future: same VPS stack, different `group_id` namespace
- code-graph-rag MCP configuration changes — governed by `l9-code-graph-rag-mcp` skill

---

## Final Declaration (Phase 6 — to be completed)

> GLOBAL-001 phases complete. GATES-002 complete separately when write enforcement enabled.  
> GMP run `GMP-GRAPHITI-GLOBAL-001` finalized.  
> No further substrate changes permitted without new GMP run.

---

## Convergence block (recursive alignment v2.1)

```yaml
convergence_status: partial
source_intent_preserved: true
scope_drift_detected: false
execution_readiness: partial  # blocked on phase0-prewrite + VPS
remaining_unknowns:
  - graphiti 2/ reuse classification
  - Cursor sessionStart additional_context reliability
  - memory-bank git policy per non-PlasticOS repos
changes_applied_v2_1:
  - GMP GLOBAL-001 / GATES-002 split in todos + rollout phases
  - feature flags GRAPHITI_MEMORY_ENABLED / GRAPHITI_WRITE_GATES
  - phase 2a/2b, phase 5a/5b, phase4b gate E2E deferred
  - C1 decommission sweep + ADR-002 disambiguation added
```

---

**Recommended immediate next action:** Read `graphiti 2/memory_tool.py`, `group_router.py`, `episode_contract.py` — pre-work gate for Phase 1. Phase 0 cannot lock a TODO plan without ground truth from source.
