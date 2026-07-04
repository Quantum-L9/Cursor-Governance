# L9 Governance — Canonical Law

**Status:** authoritative  
**Runtime:** L9 Governance  
**Governance root (SSOT):** `$HOME/.cursor-governance/` — the GitHub clone  
**GitHub origin (SSOT remote):** `Quantum-L9/Cursor-Governance`  
**Updated:** 2026-07-04 (Post-Suite-6 / Graphiti-native rewrite)

---

## 1. Single Source of Truth

| Asset | Canonical path | Access method |
|-------|----------------|---------------|
| **Governance body** | `~/.cursor-governance/` (clone root) | `.cursor-commands/` symlink |
| CANONICAL_LAW | `~/.cursor-governance/CANONICAL_LAW.md` | `.cursor/governance/CANONICAL_LAW.md` (file symlink) |
| L9 skills | `skills/` | `@.cursor-commands/skills/` |
| Workflows/DAGs | `workflows/dags/` | Executed by DAG runner |
| Global rules | `rules/` | `@.cursor-commands/rules/` |
| Ops scripts | `ops/scripts/` | `.cursor-commands/ops/scripts/` |
| Intelligence | `intelligence/` | Active signal corpus (never archive) |

**Law:** The governance repo appears **once** in each workspace: `.cursor-commands` → clone root.  
**Never** expose the governance root under `.cursor/governance/` — that path holds only the law file + README.

---

## 2. IDE Adapter Model

This governance layer is **IDE-agnostic**. The `.cursor-commands/` symlink is one adapter. Future adapters (Windsurf, VS Code, CLI) will consume the same root via their own conventions.

| Adapter | Entry point | Status |
|---------|-------------|--------|
| Cursor | `.cursor-commands/` → clone root | Active |
| Windsurf | TBD | Planned |
| VS Code | TBD | Planned |
| CLI | Direct path reference | Active |

### Required symlinks — every coding workspace

| Workspace path | Target | Purpose |
|----------------|--------|---------|
| `.cursor-commands` | `~/.cursor-governance/` | Sole global entry |
| `.cursor/governance/CANONICAL_LAW.md` | `~/.cursor-governance/CANONICAL_LAW.md` | Law file only |
| `.cursor/governance/` | **local directory** | Not a symlink to governance root |

### Forbidden

| Path | Why |
|------|-----|
| `.cursor/governance` → governance root | Exposes duplicate tree |
| `.cursor/governance/GlobalCommands` | Legacy duplicate |
| `.cursor/commands` | Duplicate of `.cursor-commands/commands` |
| `.cursor/skills` | Duplicate of `.cursor-commands/skills` |

---

## 3. User-Level Configuration (every machine)

| Path | Target |
|------|--------|
| `~/.cursor/skills` | `~/.cursor-governance/skills/` |
| `~/.cursor/commands` | `~/.cursor-governance/commands/` |

---

## 4. Naming Conventions

| Prefix | Location |
|--------|----------|
| `l9-*` | `skills/` |
| `plasticos-*` | Repo-local `.claude/skills/` |
| Repo rules | Repo `.cursor/rules/` only |

---

## 5. GitHub SSOT

| Item | Value |
|------|-------|
| Remote (origin) | `https://github.com/Quantum-L9/Cursor-Governance.git` |
| Branch | `main` |
| Git root | `~/.cursor-governance` |
| Pull (session start) | `governance_sync.sh` — guarded ff-only |
| Push (session end) | `backup_to_github.sh` — commits + rebases + pushes |
| Law file | Clone root: `CANONICAL_LAW.md` |

**Manual:**

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
```

**Automatic (every session end):**

1. `sessionEnd` hook → `ops/hooks/session_end_governance_backup.sh`
2. Log: `~/.cursor-governance/backup.log`

Skip one session: `GOVERNANCE_BACKUP_SKIP=1`

---

## 6. Skill Wiring

- New global skill → `l9-skill-compiler`, then `l9-wire-skill-into-repo`
- New repo-local skill → `.claude/skills/plasticos-*` (not governance root)

---

## 7. Anti-Patterns

- Second governance tree in any repo
- Hard-resetting or force-pushing the SSOT clone
- Committing `.cursor-commands` symlink target into app repos (symlink only; content lives in `~/.cursor-governance`)
- Referencing archived scripts (`ops/scripts/_archived/`) as active dependencies
- Using `cursor_memory_client.py` — deprecated, use Graphiti

---

## 8. Memory Layer (Graphiti-Native)

| Layer | SSOT | Interface |
|-------|------|-----------|
| Durable episodes | Graphiti (Neo4j on VPS) | `intelligence/context-memory/graphiti_sink.py` |
| Graph query | Graphiti (Neo4j on VPS) | `intelligence/context-memory/show_context_graphiti.py` |
| Local cache | `intelligence/context-memory/sessions/*.json` | Fallback only |
| MCP interface | `ops/graphiti/graphiti_memory_client.py` | L9-Ops-MCP |

**Rules:** `03-graphiti-memory.mdc`, `97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`  
**Skill:** `skills/l9-graphiti-memory/SKILL.md`  
**Flags:** `GRAPHITI_MEMORY_ENABLED`, `GRAPHITI_WRITE_GATES`

Session start prefetch: `ops/hooks/session_start_memory_orchestrator.sh`

### Deprecated (archived)

- `cursor_memory_client.py` — replaced by `graphiti_memory_client.py`
- `learning_to_mcp_bridge.py` — archived
- All `install_*.sh` scripts (except `install_export_job.sh`) — archived
- All recursive learning daemon scripts — archived

---

## 9. Intelligence & Signal Mining

The `intelligence/` directory is a **permanent, active signal corpus**. All data within it — including exported chats, logs, reasoning traces, and meta-learning artifacts — is valuable and will be mined for knowledge graph enrichment.

**Active mining scripts (do not archive):**
- `ops/scripts/export_chats.sh`
- `ops/scripts/parse_chat_exports.py`
- `ops/scripts/transcript_distiller.py`
- `ops/scripts/run_distiller.sh`
- `ops/scripts/install_export_job.sh`

---

## 10. Governance Enforcement

| Flag | Purpose | Default |
|------|---------|---------|
| `GOVERNANCE_HARDENING_ENABLED` | Lock production environment | `false` |
| `GOVERNANCE_BACKUP_SKIP` | Skip one session backup | `false` |
| `GOVERNANCE_SYNC_HARD_RESET` | Allow hard reset on sync (dangerous) | `false` |
| `GRAPHITI_MEMORY_ENABLED` | Enable Graphiti memory layer | `true` |
| `GRAPHITI_WRITE_GATES` | Enable write-through to graph | `true` |
