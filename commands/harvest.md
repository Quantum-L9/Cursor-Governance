---
name: harvest
version: "1.0.0"
description: "Harvest reusable patterns from code/conversation"
auto_chain: ynp
---

# /harvest — Pattern Harvesting

## WHAT IT DOES

Extract reusable patterns from:
- Existing code
- Conversation context
- Prior implementations

---

## EXECUTION

### 1. SCAN SOURCES

```
SOURCES:
├── Current file context
├── Chat-provided files
├── Related modules
└── Prior GMP outputs
```

### 2. EXTRACT PATTERNS

| Pattern Type | Example |
|--------------|---------|
| Function | Reusable utility |
| Class | Base class to extend |
| Template | Boilerplate to copy |
| Config | Settings pattern |

### 3. CATALOG

```markdown
## Harvestable Patterns

| # | Pattern | Source | Lines | Reuse For |
|---|---------|--------|-------|-----------|
| 1 | error_handler() | utils.py | 20-40 | Error handling |
```

---

## OUTPUT

```markdown
## 🌾 HARVEST: {context}

### Patterns Found
| Pattern | Source | Reuse |
|---------|--------|-------|

### Code Snippets
```python
# Harvested from {source}
{code}
```

### Recommendation
Use pattern #N for {task}
```

→ **Auto-chains to /ynp**

--- End Command ---
