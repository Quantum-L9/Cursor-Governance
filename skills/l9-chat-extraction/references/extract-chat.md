<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-chat-extraction
layer: reference
role: memory_extraction_protocol
tags: [l9, memory, lessons, patterns, errors]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
--- /SKILL_META ---
-->

# /extract-chat — Memory Extraction

## WHAT IT DOES

Extract learnings from conversation → L9 memory:

- Lessons learned
- Patterns discovered
- Errors and fixes
- User preferences

---

## EXECUTION

### 1. SCAN CONVERSATION

```
EXTRACT:
├── Lessons (mistakes → corrections)
├── Patterns (reusable approaches)
├── Errors (issue → fix)
├── Preferences (user corrections)
└── Decisions (architectural choices)
```

### 2. WRITE TO MEMORY

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "LESSON: {content}" --kind lesson

python3 agents/cursor/cursor_memory_client.py write \
  "PATTERN: {content}" --kind pattern

python3 agents/cursor/cursor_memory_client.py write \
  "ERROR: {issue} → FIX: {solution}" --kind error
```

---

## OUTPUT

```markdown
## 📝 EXTRACTED TO MEMORY

| Type | Content | Status |
|------|---------|--------|
| lesson | {summary} | ✅ |
| pattern | {summary} | ✅ |
| error | {summary} | ✅ |

**Items:** N extracted
```
