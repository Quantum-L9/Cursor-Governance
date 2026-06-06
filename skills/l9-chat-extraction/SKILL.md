---
name: l9-chat-extraction
description: Extract learnings and specific content from chat conversations to memory or structured output
disable-model-invocation: true
---

---
name: extract-chat
version: "1.0.0"
description: "Extract learnings from chat to memory"
auto_chain: null
---

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

--- End Command ---

---

<!-- migrated-from: extract-from-chat.md -->

---
name: extract-from-chat
version: "1.0.0"
description: "Extract specific content from chat"
auto_chain: null
---

# /extract-from-chat — Content Extraction

## WHAT IT DOES

Extract specific content types from conversation:

- Code blocks
- Decisions
- Requirements
- Action items

---

## EXTRACTION TYPES

| Type | What |
|------|------|
| code | Code blocks |
| decisions | Choices made |
| requirements | Specs gathered |
| actions | TODOs identified |
| files | File references |

---

## OUTPUT

```markdown
## 📤 EXTRACTED: {type}

### Code Blocks
```python
{extracted code}
```

### Decisions
- {decision 1}
- {decision 2}

### Requirements
- {req 1}
- {req 2}

### Action Items
- [ ] {action 1}
- [ ] {action 2}
```

--- End Command ---
