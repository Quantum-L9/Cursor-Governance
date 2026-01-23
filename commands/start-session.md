---
name: start-session
version: "1.0.0"
description: "Initialize Cursor session with context"
auto_chain: null
---

# /start-session — Session Startup

## WHAT IT DOES

Load context at session start:

1. Read workflow_state.md
2. Load memory context
3. Check active TODOs
4. Identify priorities

---

## EXECUTION

### 1. WORKFLOW STATE

```bash
# Read current state
cat workflow_state.md
```

Extract:
- Current PHASE
- Active TODOs
- Recent changes
- Open questions

### 2. MEMORY INJECT

```bash
python3 agents/cursor/cursor_memory_client.py search "recent lessons"
python3 agents/cursor/cursor_memory_client.py search "active context"
```

### 3. PRIORITY CHECK

```
🔴 HIGH — Blocking issues
🟠 MEDIUM — Current sprint
🟡 LOW — Backlog
```

---

## OUTPUT

```markdown
## 🚀 SESSION STARTED

### State
**Phase:** {0-6}
**Active TODOs:** {count}

### Priorities
| Priority | Task |
|----------|------|
| 🔴 | {high} |
| 🟠 | {medium} |

### Context Loaded
- workflow_state.md ✅
- Memory context ✅

### Ready for
→ /ynp (get recommendation)
→ /gmp (execute TODO)
```

--- End Command ---
