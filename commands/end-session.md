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

**Write atomic memories — one fact per write, not one big blob.**
See `.cursor/rules/87-cursor-memory-kernel.mdc` → "Memory Write Format" for the full spec.

```bash
# One write per fact. Pre-classify with --kind. Terse, no preamble.
python3 agents/cursor/cursor_memory_client.py write \
  "{terse fact 1}" \
  --kind lesson --scope cursor

python3 agents/cursor/cursor_memory_client.py write \
  "{terse fact 2}" \
  --kind insight --scope cursor
```

### 3. REDIS SESSION CONTEXT (cache_set_session_context)

**Call MCP tool `cache_set_session_context`** so the next window can resume from this handoff. Use the same structure as the handoff below.

- **context** (required): JSON object with:
  - `summary`: 1–2 sentence summary of session work
  - `completed`: list of tasks completed
  - `in_progress`: list with status if any
  - `next_steps`: 2–5 concrete next steps
  - `open_questions`: list if any
  - `files_touched`: list of paths modified (optional but useful)
- **session_id**: omit (daily session)
- **ttl**: omit (default 86400)

This step is mandatory: without it, the next window will not have this handoff in Redis.

### 3b. SESSION HOOKS TEARDOWN

If session hooks were activated at `/start-session`, close them now:

- Call `CursorSessionHooks.on_session_end(repo_id="l9", branch="main", promote=True)` to escalate high-confidence items to long-term memory
- This promotes recent decisions and errors-to-avoid into persistent storage
- Reference: `agents/cursor/cursor_session_hooks.py`

### 4. HANDOFF

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
- Redis session context saved (cache_set_session_context) ✅
- Next steps defined ✅

### When you open a new window
→ Use **/start-session** to load Redis context + workflow_state + memory and resume.
```

→ **Auto-chains to /extract-chat**

--- End Command ---
