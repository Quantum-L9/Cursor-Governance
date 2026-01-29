---
name: start-session
version: "2.0.0"
description: "Initialize Cursor session with full context + C1 memory health"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Full preflight check before starting work:

1. **Check C1 Memory Health**
2. **Load Memory Operations Reference** (`agents/cursor/docs/CURSOR-MEMORY-CLIENT.md`)
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

### 3. MEMORY INJECT — From C1

```bash
# Search C1 memory for context
python3 agents/cursor/cursor_memory_client.py search "recent lessons"
python3 agents/cursor/cursor_memory_client.py search "active context Igor"
python3 agents/cursor/cursor_memory_client.py inject "session startup"
```

### 4. TIME CONTEXT

Calculate time since last session:
- Parse "Recent Sessions" dates from workflow_state.md
- If >24h gap: Flag "context may be stale"
- If >7d gap: Recommend deeper memory search

### 5. PRIORITY CHECK

```
🔴 HIGH — Blocking issues, active GMPs
🟠 MEDIUM — Current sprint items
🟡 LOW — Backlog, future work
```

---

## OUTPUT — STATE_SYNC Block

```markdown
## 🚀 SESSION STARTED

### Preflight
| Check | Status |
|-------|--------|
| C1 MCP Health | ✅ healthy / ⚠️ degraded / ❌ unhealthy |
| Memory Ops Reference | ✅ loaded (CURSOR-MEMORY-CLIENT.md) |
| workflow_state.md | ✅ loaded |
| TODO.md | ✅ parsed |
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
