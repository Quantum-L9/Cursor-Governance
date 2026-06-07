<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-chat-extraction
layer: reference
role: content_extraction_protocol
tags: [l9, chat, code, decisions, requirements]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
--- /SKILL_META ---
-->

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
