---
name: rules
version: "1.0.0"
description: "List and manage governance rules"
auto_chain: null
---

# /rules — Governance Rules

## WHAT IT DOES

List and check governance rules.

---

## RULE CATEGORIES

### KERNEL_TIER
- Protected files require approval
- Full GMP phases required
- No shortcuts

### RUNTIME_TIER
- GMP recommended
- Tests required
- Docs for public APIs

### INFRA_TIER
- Deployment manifest required
- Rollback plan required
- Smoke tests required

### UX_TIER
- Standard GMP
- Tests recommended

---

## PROTECTED FILES

```
runtime/websocket_orchestrator.py
core/agents/executor.py
memory/substrate_service.py
memory/substrate_dag.py
docker-compose.yml
core/singleton_registry.py
```

---

## REQUIRED PATTERNS

| Pattern | Required |
|---------|----------|
| structlog | Yes |
| httpx | Yes |
| async I/O | Yes |
| pydantic v2 | Yes |
| type hints | Yes |

---

## FORBIDDEN PATTERNS

| Pattern | Why |
|---------|-----|
| Bare except | Hides errors |
| sync in async | Blocks event loop |
| global state | Hard to test |
| print() | Use structlog |

---

## OUTPUT

```markdown
## 📜 RULES

### Active Rules
| Rule | Scope | Enforcement |
|------|-------|-------------|

### Violations in Scope
| Violation | File | Fix |
|-----------|------|-----|
```

--- End Command ---
