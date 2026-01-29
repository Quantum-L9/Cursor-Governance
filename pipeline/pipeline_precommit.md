---
name: pipeline_precommit
version: "1.0.0"
description: "Pre-commit checks before commit"
auto_chain: null
---

# /pipeline_precommit — Pre-Commit Checks

## WHAT IT DOES

Run all checks before committing:

1. Lint (ruff)
2. Types (mypy)
3. Tests (pytest)
4. Security (semgrep)

---

## EXECUTION

```bash
# All checks
ruff check . && mypy . && pytest tests/ -v && semgrep --config .sec/semgrep.yaml .
```

Or individually:

```bash
ruff check .              # Lint
ruff check --fix .        # Auto-fix
mypy .                    # Types
pytest tests/ -v          # Tests
semgrep --config .sec/    # Security
```

---

## CHECKLIST

| Gate | Command | Required |
|------|---------|----------|
| Lint | `ruff check .` | ✅ |
| Format | `ruff format --check .` | ✅ |
| Types | `mypy .` | ✅ |
| Tests | `pytest` | ✅ |
| Security | `semgrep` | ✅ |

---

## OUTPUT

```markdown
## ✅ PRE-COMMIT: PASSED | ❌ FAILED

| Gate | Status | Details |
|------|--------|---------|
| Lint | ✅/❌ | N issues |
| Types | ✅/❌ | N errors |
| Tests | ✅/❌ | N passed |
| Security | ✅/❌ | N findings |

### Failures (if any)
{details}

### Ready to Commit
✅ Yes | ❌ Fix issues first
```

--- End Command ---
