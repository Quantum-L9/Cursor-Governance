---
name: mem
version: "1.0.0"
description: "Memory operations — read, search, write"
auto_chain: null
---

# /mem — Memory Operations

## USAGE

```
/mem read "query"           # Search memory
/mem write "content"        # Write to memory
/mem inject "task"          # Load context for task
```

---

## OPERATIONS

### READ (Search)

```bash
python3 agents/cursor/cursor_memory_client.py search "query"
```

### WRITE

```bash
python3 agents/cursor/cursor_memory_client.py write \
  "content" --kind lesson|pattern|error|note
```

### INJECT (Pre-task)

Load relevant context before execution:

```bash
# Preferences
python3 agents/cursor/cursor_memory_client.py search "preferences"

# Lessons for task
python3 agents/cursor/cursor_memory_client.py search "{task} lessons errors"

# Patterns
python3 agents/cursor/cursor_memory_client.py search "{domain} patterns"
```

---

## MEMORY TYPES

| Kind | Use For |
|------|---------|
| lesson | Mistakes → corrections |
| pattern | Reusable approaches |
| error | Issue → fix mapping |
| note | General context |
| gmp_completion | GMP outcomes |

---

## OUTPUT

```markdown
## 🧠 MEMORY

### Search Results
| # | Kind | Content | Score |
|---|------|---------|-------|

### Written
| Kind | Content | Status |
|------|---------|--------|
| lesson | {summary} | ✅ |
```

--- End Command ---
