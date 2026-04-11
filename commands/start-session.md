---
name: start-session
version: "2.1.0"
description: "Initialize Cursor session with full context + C1 memory health"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Full preflight check before starting work:

1. **Check C1 Memory Health**
2. **Load Memory Operations Reference** (`.cursor/memory/CURSOR-MEMORY-CLIENT.md`)
3. Read workflow_state.md
4. Load memory context from C1
5. Extract GMP Queue from TODO.md
6. Identify priorities

---

## EXECUTION

### 0. PREFLIGHT — C1 Memory Health + Reference Docs

**Step 0a: Check C1 MCP server**

```bash
# Check C1 MCP server is reachable
python3 agents/cursor/cursor_memory_client.py health
```

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ healthy | C1 MCP responding | Proceed normally |
| ⚠️ degraded | MCP down, API up | Note: Memory writes may fail |
| ❌ unhealthy | Both down | Warn user, proceed without memory |

**If unhealthy:** Continue session but note in output that memory operations are unavailable.

**Step 0b: Load Memory Operations Reference**

```bash
# Read memory client documentation for reference
cat agents/cursor/docs/CURSOR-MEMORY-CLIENT.md
```

This provides:
- C1 architecture diagram
- Write/Search/Retrieve flow
- All 27 commands available
- Troubleshooting steps
- Governance rules stored in memory

**Step 0c: Load Cursor system prompt identity**

```bash
# Read Cursor identity and memory scope rules
cat agents/cursor/cursor_system_prompt.md
```

This provides:
- Cursor's identity within L9
- Memory scope rules (write: `cursor`, search: `cursor`, `developer`, `global`)
- RLS enforcement details
- Required behaviors for memory operations

**Step 0d: Load governance reference**

```bash
# Read governance quick reference
cat agents/cursor/governance-reference.md
```

### 1. WORKFLOW STATE

```bash
# Read current state
cat workflow_state.md
```

Extract ALL fields per 85-workflow-state-bridge.mdc:
- **PHASE** (0-6)
- **Context summary**
- **Last 3 recent changes**
- **Open questions**
- **Next steps** (2-5 items)

### 2. GMP QUEUE — From TODO.md

```bash
# Parse TODO.md for pending GMPs
grep -E "^\s*-\s*\[.\]\s*(GMP|HIGH|MEDIUM)" TODO.md | head -10
```

Extract:
- Pending GMPs with priorities
- HIGH priority items (🔴)
- MEDIUM priority items (🟠)
- Blocked items

### 3. REDIS SESSION CONTEXT (resume from last window)

**Call MCP tool `cache_get_session_context`** (session_id optional). If the result has `success: true` and `data`, display it as "Previous session context" so we can resume:

- **summary**, **next_steps**, **in_progress**, **open_questions**, **files_touched**
- Use this to avoid amnesia when the user opened a new window after /end-session or a milestone save.

### 4. MEMORY INJECT — From C1

```bash
# Search C1 memory for context
python3 agents/cursor/cursor_memory_client.py search "recent lessons"
python3 agents/cursor/cursor_memory_client.py search "active context Igor"
python3 agents/cursor/cursor_memory_client.py inject "session startup"
```

### 5. TIME CONTEXT

Calculate time since last session:
- Parse "Recent Sessions" dates from workflow_state.md
- If >24h gap: Flag "context may be stale"
- If >7d gap: Recommend deeper memory search

### 6. PRIORITY CHECK

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
| C1 MCP Health | ✅ healthy / ⚠️ degraded / ❌ unhealthy |
| Memory Ops Reference | ✅ loaded (CURSOR-MEMORY-CLIENT.md) |
| System Prompt | ✅ loaded (cursor_system_prompt.md) |
| Governance Reference | ✅ loaded (governance-reference.md) |
| workflow_state.md | ✅ loaded |
| TODO.md | ✅ parsed |
| Neo4j Graph | ✅ {N} nodes / ⚠️ unavailable |
| Time since last | {X hours/days} |

### State (from workflow_state.md)
**Phase:** {0-6}
**Context:** {1-2 sentence summary}

**Last 3 Changes:**
1. {change 1}
2. {change 2}
3. {change 3}

**Open Questions:**
- {question 1}
- {question 2}

### GMP Queue (from TODO.md)
| Priority | GMP/Task | Status |
|----------|----------|--------|
| 🔴 | {HIGH item 1} | pending |
| 🔴 | {HIGH item 2} | pending |
| 🟠 | {MEDIUM item} | pending |

### Memory Context (from C1)
- Preferences: {count} loaded
- Lessons: {count} loaded
- Warnings: {any relevant}

### Next Steps (from workflow_state.md)
1. {next step 1}
2. {next step 2}
3. {next step 3}

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
1. Read workflow_state.md
2. Show Phase + Next Steps
3. Skip memory inject

---

## EXAMPLE OUTPUT

```markdown
## 🚀 SESSION STARTED

### Preflight
| Check | Status |
|-------|--------|
| C1 MCP Health | ✅ healthy |
| Memory Ops Reference | ✅ loaded |
| workflow_state.md | ✅ loaded |
| TODO.md | ✅ parsed |
| Time since last | 3 hours |

### State
**Phase:** 2 (IMPLEMENT)
**Context:** Working on C1 memory migration, updating rules and commands.

**Last 3 Changes:**
1. 2026-01-24: Updated 03-mcp-memory.mdc with C1 endpoints
2. 2026-01-24: Enhanced /start-session with health check
3. 2026-01-23: Completed GMP-119 singleton refactor

**Open Questions:**
- Should we migrate all scripts to C1 URLs?

### GMP Queue
| Priority | GMP/Task | Status |
|----------|----------|--------|
| 🔴 | GMP-121: C1 Memory Docs | in_progress |
| 🟠 | Legacy code cleanup | pending |

### Memory Context (from C1)
- Preferences: 5 loaded
- Lessons: 3 loaded
- Warnings: None relevant

### Next Steps
1. Complete C1 memory documentation
2. Test memory client against C1
3. Update /start-session command

### Ready For
→ `/ynp` — Get recommendation
→ `/gmp "test C1 memory"` — Execute next task
```

--- End Command ---
