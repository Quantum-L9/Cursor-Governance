---
name: lint-fix
version: "1.0.0"
description: "TRIGGER ONLY — Invokes lint_fix_executor.py for systematic lint fixes"
auto_chain: ynp
dag_executor: workflows/lint_fix_executor.py
---

# /lint-fix — Systematic Lint Fixing (v1.0.0)

## THIS IS A TRIGGER ONLY

`/lint-fix` invokes the Lint-Fix Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 workflows/lint_fix_executor.py
python3 workflows/lint_fix_executor.py --only B904 N811
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  SCAN-ERRORS      │ Run ruff to find all errors        │
├─────────────────────────────────────────────────────────┤
│  CATEGORIZE       │ Sort into AUTO/SEMI/MANUAL         │
├─────────────────────────────────────────────────────────┤
│  APPLY-AUTO       │ ruff --fix for auto-fixable        │
├─────────────────────────────────────────────────────────┤
│  APPLY-SEMI       │ sed patterns for known patterns    │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile on modified files       │
├─────────────────────────────────────────────────────────┤
│  RESCAN           │ Count remaining errors             │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **Category-aware** — Handles AUTO, SEMI, MANUAL differently
- **B904 pattern** — Adds `from e` to raises in except blocks
- **Safe validation** — Ensures fixes don't break syntax
- **Auto-report** — Uses canonical report generator

## FIX CATEGORIES

| Category | How | Examples |
|----------|-----|----------|
| AUTO | `ruff --fix` | I001, I002, F401, UP*, W*, E* |
| SEMI | sed patterns | B904 (raise from) |
| MANUAL | Report only | Complex issues |

## USAGE

```bash
# Fix all lint errors
python3 workflows/lint_fix_executor.py

# Fix only specific codes
python3 workflows/lint_fix_executor.py --only B904 N811

# Check status
python3 workflows/lint_fix_executor.py --status

# Resume if interrupted
python3 workflows/lint_fix_executor.py --resume
```

## OUTPUT

Produces:
- Terminal progress showing before/after counts
- GMP report with fix statistics
- Local commit (no push)

## EXAMPLE

```
Found 189 lint errors:
| Code | Count |
|------|-------|
| B904 |   186 |
| N811 |     3 |

Results:
  Before: 189 errors
  After:  0 errors
  Fixed:  189 errors
```
