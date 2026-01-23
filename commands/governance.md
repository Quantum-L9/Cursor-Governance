---
name: governance
version: "1.0.0"
description: "Check and enforce governance rules"
auto_chain: ynp
---

# /governance — Governance Check

## WHAT IT DOES

Verify compliance with L9 governance:

1. Protected files respected
2. GMP phases followed
3. Approval gates passed
4. Audit trail exists

---

## CHECKS

### Protected Files

```
PROTECTED:
├── core/agents/executor.py
├── runtime/websocket_orchestrator.py
├── memory/substrate_service.py
├── docker-compose.yml
└── core/singleton_registry.py
```

Any modification → Requires KERNEL GMP

### GMP Compliance

| Requirement | Check |
|-------------|-------|
| Phase 0 plan locked | ✅ |
| No scope drift | ✅ |
| Validation passed | ✅ |
| Report generated | ✅ |

### Approval Gates

| Operation | Approval |
|-----------|----------|
| Protected file | Igor explicit |
| Destructive action | Igor explicit |
| Production deploy | Igor explicit |

---

## OUTPUT

```markdown
## 🛡️ GOVERNANCE CHECK

### Status: ✅ COMPLIANT | ❌ VIOLATIONS

### Protected Files
| File | Status |
|------|--------|
| executor.py | ✅ Untouched |

### GMP Compliance
| Check | Status |
|-------|--------|
| Plan locked | ✅ |

### Violations (if any)
| Violation | Location | Fix |
|-----------|----------|-----|
```

→ **Auto-chains to /ynp**

--- End Command ---
