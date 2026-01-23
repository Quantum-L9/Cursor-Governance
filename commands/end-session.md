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
2. Extract learnings to memory
3. Create handoff summary
4. List next steps

---

## EXECUTION

### 1. UPDATE WORKFLOW STATE

Add to Recent Sessions:
```markdown
- {date}: {summary of work done}
```

Update Next Steps:
```markdown
- [ ] {next action 1}
- [ ] {next action 2}
```

### 2. EXTRACT LEARNINGS

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
