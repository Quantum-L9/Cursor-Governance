---
name: start-session
version: "2.3.0"
description: "Initialize Cursor session — governance wiring gate, Graphiti prefetch + memory-bank T0"
auto_chain: null
auto_chain_on_fail:
  check: governance_wiring
  chain: wire governance
---

# /start-session — Session Startup

## WHAT IT DOES

Full preflight check before starting work:

0. **Governance wiring gate** — `.cursor-commands` SSOT + `sessionEnd` hook (auto-chains `/wire governance` if FAIL)
1. **Graphiti memory** — health/resolve + read `memory-bank/activeContext.md` (T0 SSOT); sessionStart orchestrator prefetches when enabled
2. **Legacy C1** — read-only advisory health (deprecated writes)
3. **Redis session context** — resume from last `/end-session` handoff
4. Load Graphiti/C1 context (PICKUP packets, lessons)
5. Extract GMP Queue from TODO.md (if present)
6. Identify priorities

---

## EXECUTION

### 0. GOVERNANCE WIRING GATE (MANDATORY — blocking)

Run **before** any other step. Resolves the SSOT clone so it works even when `.cursor-commands` is missing.

```bash
GC="$HOME/.cursor-governance"                                   # SSOT: clone root == GlobalCommands
[ -d "$HOME/Dropbox/cursor governance/GlobalCommands" ] && [ ! -f "$GC/CANONICAL_LAW.md" ] && GC="$HOME/Dropbox/cursor governance/GlobalCommands"
[ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ] && [ ! -f "$GC/CANONICAL_LAW.md" ] && GC="$HOME/Dropbox/Cursor Governance/GlobalCommands"

bash "$GC/ops/scripts/check_governance_wiring.sh" "$(pwd)"
```

| Result | Action |
|--------|--------|
| Exit 0 (`RESULT: PASS`) | Continue to Step 0a |
| Exit 1 (`RESULT: FAIL`) | **Auto-chain `/wire governance`** — do not skip |

**On FAIL — run repair immediately (no user confirmation):**

```bash
bash "$GC/ops/scripts/wire_governance_workspace.sh" "$(pwd)"
```

This runs `setup_workspace_symlinks.sh` (repo symlinks + `~/.cursor/hooks.json` sessionEnd hook) and re-checks.

**Re-run check after repair.** Session is **blocked** until `RESULT: PASS`.

Pass criteria:
- `.cursor-commands` symlink → `~/.cursor-governance` (SSOT clone == GlobalCommands)
- `.cursor/governance/CANONICAL_LAW.md` → `~/.cursor-governance/CANONICAL_LAW.md`
- No `.cursor/commands` or `.cursor/skills` duplicates in repo
- `sessionEnd` hook registered in `~/.cursor/hooks.json`
- `~/.cursor/hooks/governance-backup.sh` → SSOT backup script

### 0. PREFLIGHT — Graphiti Memory + memory-bank (T0)

**Step 0a: Graphiti health + group resolve**

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve
```

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ healthy | Graphiti VPS reachable | Proceed; prefetch runs via sessionStart hook when `GRAPHITI_MEMORY_ENABLED=1` |
| ❌ unhealthy | VPS down or env missing | Warn; read `memory-bank/activeContext.md` only; see `ops/graphiti/DEPLOY.md` |

**Step 0b: T0 resume SSOT**

```bash
cat memory-bank/activeContext.md 2>/dev/null || echo "(scaffold on first wire)"
```

**Step 0c: Legacy C1 (advisory, read-only)**

```bash
python3 .cursor/memory/cursor_memory_client.py health 2>/dev/null || true
```

C1 writes are deprecated — use Graphiti `graphiti_memory_client.py` per `03-graphiti-memory.mdc`.

### 1. REDIS SESSION CONTEXT (resume from last window)

**Call MCP tool `cache_get_session_context`** (session_id optional). If the result has `success: true` and `data`, display it as "Previous session context" so we can resume:

- **summary**, **next_steps**, **in_progress**, **open_questions**, **files_touched**
- Use this to avoid amnesia when the user opened a new window after /end-session or a milestone save.

### 2. GMP QUEUE — From TODO.md (optional)

```bash
# Parse TODO.md for pending GMPs (skip if file absent)
grep -E "^\s*-\s*\[.\]\s*(GMP|HIGH|MEDIUM)" TODO.md | head -10
```

Extract:
- Pending GMPs with priorities
- HIGH priority items (🔴)
- MEDIUM priority items (🟠)
- Blocked items

### 3. MEMORY INJECT — From C1

```bash
# Search C1 memory for context
python3 agents/cursor/cursor_memory_client.py search "PICKUP|" --limit 3
python3 agents/cursor/cursor_memory_client.py search "recent lessons"
python3 agents/cursor/cursor_memory_client.py search "active context Igor"
python3 agents/cursor/cursor_memory_client.py inject "session startup"
```

### 4. TIME CONTEXT

Calculate time since last session:
- Parse `date=` from the most recent `PICKUP|` memory hit, or Redis session context timestamp
- If >24h gap: Flag "context may be stale"
- If >7d gap: Recommend deeper memory search

### 5. PRIORITY CHECK

```
🔴 HIGH — Blocking issues, active GMPs
🟠 MEDIUM — Current sprint items
🟡 LOW — Backlog, future work
```

### 6. INDEX FRESHNESS CHECK (Optional)

Check if repo indexes need refresh:

```bash
# Check index file ages
ls -la reports/repo-index/*.txt | head -5

# If indexes older than 24h or significant code changes detected:
python3 tools/export_repo_indexes.py
# This automatically runs:
#   1. Generate index files
#   2. Ingest to memory (pgvector)
#   3. Load to Neo4j (if configured)
```

**Neo4j graph awareness:**

```bash
# Check graph node counts for awareness
python3 agents/cursor/cursor_neo4j_query.py --count-nodes
```

This gives the agent awareness of the current graph state (node counts by type: File, Class, Function, Module) at session start. Requires `NEO4J_PASSWORD` env var.

**When to refresh indexes:**
- After major code changes (new files, refactors)
- If indexes >24h old
- Before deep codebase exploration

**Skip if:**
- Quick session
- Indexes recently updated
- Working on single file

---

## OUTPUT — STATE_SYNC Block

```markdown
## 🚀 SESSION STARTED

### Preflight
| Check | Status |
|-------|--------|
| Governance wiring + sessionEnd hook | ✅ PASS / 🔧 repaired via /wire governance |
| C1 MCP Health | ✅ healthy / ⚠️ degraded / ❌ unhealthy |
| Memory Ops Reference | ✅ loaded (CURSOR-MEMORY-CLIENT.md) |
| System Prompt | ✅ loaded (cursor_system_prompt.md) |
| Governance Reference | ✅ loaded (governance-reference.md) |
| Redis session context | ✅ loaded / ⚠️ none |
| TODO.md | ✅ parsed / ⚠️ absent |
| Neo4j Graph | ✅ {N} nodes / ⚠️ unavailable |
| Time since last | {X hours/days} |

### Resume Context
**Summary:** {from Redis or latest PICKUP|}

**Next Steps:**
1. {next step 1}
2. {next step 2}
3. {next step 3}

**In Progress:**
- {item} — {status}

**Open Questions:**
- {question 1}
- {question 2}

### GMP Queue (from TODO.md, if present)
| Priority | GMP/Task | Status |
|----------|----------|--------|
| 🔴 | {HIGH item 1} | pending |
| 🔴 | {HIGH item 2} | pending |
| 🟠 | {MEDIUM item} | pending |

### Memory Context (from C1)
- PICKUP packets: {count} loaded
- Preferences: {count} loaded
- Lessons: {count} loaded
- Warnings: {any relevant}

### Ready For
→ `/ynp` — Get recommendation on what to do next
→ `/gmp "{task}"` — Execute specific GMP
→ `/forge` — Rapid multi-GMP execution
```

---

## QUICK MODE

For fast startup without full memory load:

```bash
/start-session --quick
```

Only does:
1. Load Redis session context (if any)
2. Search latest `PICKUP|` from C1
3. Skip full memory inject

---

## EXAMPLE OUTPUT

```markdown
## 🚀 SESSION STARTED

### Preflight
| Check | Status |
|-------|--------|
| C1 MCP Health | ✅ healthy |
| Memory Ops Reference | ✅ loaded |
| Redis session context | ✅ loaded |
| TODO.md | ⚠️ absent |
| Time since last | 3 hours |

### Resume Context
**Summary:** Working on C1 memory migration, updating rules and commands.

**Next Steps:**
1. Complete C1 memory documentation
2. Test memory client against C1
3. Update /start-session command

**Open Questions:**
- Should we migrate all scripts to C1 URLs?

### GMP Queue
| Priority | GMP/Task | Status |
|----------|----------|--------|
| 🔴 | GMP-121: C1 Memory Docs | in_progress |
| 🟠 | Legacy code cleanup | pending |

### Memory Context (from C1)
- PICKUP packets: 1 loaded
- Preferences: 5 loaded
- Lessons: 3 loaded
- Warnings: None relevant

### Ready For
→ `/ynp` — Get recommendation
→ `/gmp "test C1 memory"` — Execute next task
```

--- End Command ---
