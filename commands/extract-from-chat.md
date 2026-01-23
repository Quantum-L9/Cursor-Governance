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
