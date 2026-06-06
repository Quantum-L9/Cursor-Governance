---
name: l9-forge
description: /forge — Autonomous Execution
disable-model-invocation: true
---

---
name: forge
version: "7.0.0"
description: "Autonomous execution — NO PAUSES, maximum velocity"
auto_chain: ynp
---

# /forge — Autonomous Execution

## WHAT IT DOES

**Maximum velocity execution** — ZERO pauses for approval:

1. Execute autonomously (no manual checkpoints)
2. Auto-fix issues silently
3. Governance compliant by default
4. Complete delivery: code + tests + docs

---

## VELOCITY RULES

| Rule | Behavior |
|------|----------|
| NO PAUSES | Don't ask, execute |
| AUTO-FIX | Fix issues, proceed |
| BATCH | Multiple GMPs per forge |
| COMPLETE | Code + tests + docs |

---

## EXECUTION

### 1. SCOPE LOCK

```markdown
## FORGE SCOPE
**Task:** {description}
**GMPs:** {count}
**Files:** {list}
**Tier:** KERNEL | RUNTIME | INFRA | UX

⚡ EXECUTING (no confirmation needed)
```

### 2. EXECUTE GMPs

For each GMP in scope:
- Phase 0-6 (no pauses)
- Auto-fix validation failures
- Generate report

### 3. DELIVER

| Artifact | Required |
|----------|----------|
| Code | ✅ |
| Tests | ✅ |
| Docs | If new API |
| Report | ✅ |

---

## STOP CONDITIONS (ONLY)

| Condition | Action |
|-----------|--------|
| Protected file | STOP → Request KERNEL approval |
| Destructive op | STOP → Request explicit approval |
| Circular dependency | STOP → Report issue |

Everything else → AUTO-FIX and proceed

---

## OUTPUT

```markdown
## ⚡ FORGE COMPLETE

**GMPs:** N executed
**Files:** N modified
**Tests:** ✅ passing

### Deliverables
- [x] Code implemented
- [x] Tests added
- [x] Reports generated

### Reports
- reports/GMP-XXX.md
- reports/GMP-YYY.md
```

→ **Auto-chains to /ynp**

--- End Command ---
