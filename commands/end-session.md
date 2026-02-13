---
name: end-session
version: "1.0.0"
description: "Close session — save context, create handoff"
auto_chain: extract-chat
---

# /end-session — Session Close

## WHAT IT DOES

Clean session close:

1. Update workflow_state.md
2. Extract learnings to memory (via canonical pipeline; see `docs/MEMORY_PIPELINE_MAP.md`)
3. Create handoff summary
4. List next steps

---

## EXECUTION

### 1. UPDATE WORKFLOW STATE

**Use the workflow state script** to append to Recent Sessions (7-day window):

```bash
python3 scripts/workflow/update_workflow_state.py end-session --summary "{summary of work done}"
```

Example:
```bash
python3 scripts/workflow/update_workflow_state.py end-session --summary "Executed /end-session (workflow_state + memory write). Handoff + extract-chat chained."
```

Then, if needed, update **Next Steps** in `workflow_state.md` (add or adjust items under `## Next Steps (Next Session)`).

### 2. EXTRACT LEARNINGS (canonical memory pipeline)

Session learnings MUST be written through the **canonical memory path** so they get governance, audit, DAG (packet_store → graph_sync → semantic_embed → insights), and persistence. See `docs/MEMORY_PIPELINE_MAP.md`.

- **Path:** `cursor_memory_client.py write` → MCP `save_memory` → main pipeline (`write_packet` → SubstrateDAG) → PostgreSQL + Neo4j + pgvector.

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "SESSION: {date}. WORK: {summary}. LESSONS: {lessons}" \
  --kind note
```

### 3. HANDOFF

```markdown
## Session Handoff

### Completed
- {task 1}
- {task 2}

### In Progress
- {task} — {status}

### Next Steps
1. {action}
2. {action}

### Open Questions
- {question}
```

---

## OUTPUT

```markdown
## 👋 SESSION CLOSED

### Summary
**Work completed:** {count} items
**Reports generated:** {list}

### Handoff
- workflow_state.md updated ✅
- Memory written ✅
- Next steps defined ✅

### Resume with
→ /start-session
```

→ **Auto-chains to /extract-chat**

--- End Command ---
