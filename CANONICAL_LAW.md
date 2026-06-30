# Cursor Governance — Canonical Law

**Status:** authoritative  
**Governance root (SSOT):** `$HOME/Dropbox/Cursor Governance/`  
**GlobalCommands (SSOT body):** `$HOME/.cursor-governance/`  
**GitHub backup:** `cryptoxdog/Cursor-Governance`  
**Updated:** 2026-06-06

## 1. Single source of truth

| Asset | Canonical path | Repo access |
|-------|----------------|-------------|
| **GlobalCommands body** | Dropbox `GlobalCommands/` | **`.cursor-commands/` only** |
| CANONICAL_LAW | Dropbox `CANONICAL_LAW.md` | `.cursor/governance/CANONICAL_LAW.md` (file symlink) |
| L9 skills | `GlobalCommands/skills/` | `@.cursor-commands/skills/` |
| Slash commands | `GlobalCommands/commands/` | `@.cursor-commands/commands/` |
| Global rules | `GlobalCommands/rules/` | `@.cursor-commands/rules/` |
| Ops scripts | `GlobalCommands/ops/scripts/` | `.cursor-commands/ops/scripts/` |

**Law:** GlobalCommands appears **once** in each repo: `.cursor-commands` → `GlobalCommands/`.  
**Never** expose GlobalCommands under `.cursor/governance/` — that path is local-only (law file + README).

## 2. Required symlinks — every coding repo

```bash
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh
```

| Repo path | Target | Purpose |
|-----------|--------|---------|
| `.cursor-commands` | `GlobalCommands/` | **sole global entry** |
| `.cursor/governance/CANONICAL_LAW.md` | Dropbox `CANONICAL_LAW.md` | law file only |
| `.cursor/governance/` | **local directory** | not a symlink to Dropbox root |

### Forbidden

| Path | Why |
|------|-----|
| `.cursor/governance` → Dropbox root | exposes duplicate `GlobalCommands/` tree |
| `.cursor/governance/GlobalCommands` | duplicate of `.cursor-commands` |
| `.cursor/commands` | duplicate of `.cursor-commands/commands` |
| `.cursor/skills` | duplicate of `.cursor-commands/skills` |

Repo `.cursor/rules/` — PlasticOS overlay only (real files, not global copies).

Validate:

```bash
bash .cursor-commands/ops/scripts/validate_governance_symlinks.sh
```

## 3. User-level Cursor (every machine)

| Path | Target |
|------|--------|
| `~/.cursor/skills` | `GlobalCommands/skills/` |
| `~/.cursor/commands` | `GlobalCommands/commands/` |

## 4. Naming

| Prefix | Location |
|--------|----------|
| `l9-*` | `GlobalCommands/skills/` |
| `plasticos-*` | repo `.claude/skills/` |
| repo rules | repo `.cursor/rules/` only |

## 5. GitHub backup (Cursor-Governance)

| Item | Value |
|------|-------|
| Remote | `https://github.com/cryptoxdog/Cursor-Governance.git` |
| Branch | `main` |
| Git root | Dropbox `GlobalCommands/` (same tree as `.cursor-commands/`) |
| Law file | Copied to repo root as `CANONICAL_LAW.md` on each backup |

**Manual:**

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
# or: /governance-backup
# or (PlasticOS): make governance-backup
```

**Automatic (every session end):**

1. Run once: `bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh`
2. Registers `sessionEnd` in `~/.cursor/hooks.json` → `ops/hooks/session_end_governance_backup.sh`
3. Log: `~/.cursor-governance/backup.log`

Skip one session: `GOVERNANCE_BACKUP_SKIP=1`

## 6. Wire skills

- New global skill → `l9-skill-compiler`, then `l9-wire-skill-into-repo`
- New PlasticOS skill → repo `.claude/skills/plasticos-*` (not GlobalCommands)

## 7. Anti-patterns

- Second GlobalCommands tree in any repo (`.cursor/governance/GlobalCommands`, `.cursor/skills`, etc.)
- Editing GitHub directly without syncing Dropbox SSOT first
- Committing `.cursor-commands` symlink into app repos (symlink only; content lives in Dropbox + Cursor-Governance)

## 8. Setup checklist

```bash
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh
bash .cursor-commands/ops/scripts/validate_governance_symlinks.sh
bash .cursor-commands/ops/scripts/backup_to_github.sh   # first GitHub sync
```

## 9. Graphiti memory (GLOBAL-001)

| Layer | SSOT | Path |
|-------|------|------|
| T0 resume | `memory-bank/` | repo root (gitignored scaffold via `setup_workspace_symlinks.sh`) |
| T1/T2 semantic | Graphiti VPS | `ops/graphiti/graphiti_memory_client.py` |
| Legacy read-only | C1 MCP | deprecated — `03-mcp-memory.mdc` |

**Rules:** `03-graphiti-memory.mdc`, `97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`  
**Skill:** `skills/l9-graphiti-memory/SKILL.md`  
**Flags:** `GRAPHITI_MEMORY_ENABLED`, `GRAPHITI_WRITE_GATES` (default off until GATES-002 proven)

Prefetch runs on `sessionStart` via `ops/hooks/session_start_memory_orchestrator.sh`. Writes to C1 from `learning_to_mcp_bridge.py` are deprecated — use Graphiti bootstrap after VPS deploy.
