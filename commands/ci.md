---
name: ci
version: "1.0.0"
description: "CI/CD pipeline operations"
auto_chain: ynp
---

# /ci — CI/CD Operations

## USAGE

```
/ci status              # Check pipeline status
/ci run                 # Trigger CI run
/ci fix                 # Fix CI failures
/ci gates               # List required gates
```

---

## GATES

| Gate | Command | Required |
|------|---------|----------|
| Lint | `ruff check .` | ✅ |
| Types | `mypy .` | ✅ |
| Tests | `pytest` | ✅ |
| Security | `semgrep` | ✅ |
| Build | `docker build` | For deploy |

---

## FIX WORKFLOW

### 1. IDENTIFY FAILURES

```bash
gh run list --limit 5
gh run view {id} --log-failed
```

### 2. CATEGORIZE

| Type | Fix |
|------|-----|
| Lint | `ruff check --fix` |
| Type | Fix annotations |
| Test | Fix code or test |
| Security | Address finding |

### 3. FIX & VERIFY

```bash
ruff check --fix .
pytest tests/ -v
git add . && git commit -m "fix: CI failures"
```

---

## OUTPUT

```markdown
## 🔄 CI STATUS

| Gate | Status | Details |
|------|--------|---------|
| Lint | ✅ | 0 errors |
| Tests | ❌ | 2 failed |

### Failures
| Test | Error |
|------|-------|
| test_x | AssertionError |

### Fix Plan
1. {action}
```

--- End Command ---
