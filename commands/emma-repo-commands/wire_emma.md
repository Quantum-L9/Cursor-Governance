---
name: wire_emma
version: "1.0.0"
description: "Emma-specific wiring verification — uses repo-index"
auto_chain: ynp
---

# /wire_emma — Emma Wiring Verification

## WHAT IT DOES

Uses `reports/repo-index/entrypoints.txt` and `route_handlers.txt` to verify:

1. **Router coverage** — Every v1 router from route_handlers is registered in `routes.py`
2. **Import validation** — All router modules import successfully (requires venv)

Produces a pass/fail report at `reports/wire_emma_report.txt`.

---

## INVOCATION

```bash
# From repo root (with venv for full validation)
source venv/bin/activate && python scripts/wire_emma.py

# Without venv (router coverage only; import check skipped)
python scripts/wire_emma.py
```

---

## INDEX FILES USED

| File | Purpose |
|------|---------|
| `reports/repo-index/route_handlers.txt` | Source of truth for API routes (METHOD /path -> handler @ path) |
| `reports/repo-index/entrypoints.txt` | Supplementary; API + Script entrypoints |
| `src/emma/api/routes.py` | Target — must include all v1 routers |

---

## OUTPUT

```
============================================================
EMMA WIRE VERIFICATION REPORT
============================================================

1. ROUTER COVERAGE
----------------------------------------
[PASS] or [FAIL] Missing from routes.py: ...

2. IMPORT VALIDATION
----------------------------------------
[PASS] or [FAIL] or [SKIP] (venv required)

Report saved to: reports/wire_emma_report.txt
```

---

## EXIT CODES

| Code | Meaning |
|------|---------|
| 0 | All checks pass |
| 1 | Missing routers and/or import failures |

---

## REGENERATING INDEX FILES

Before running wire_emma, ensure indexes are current:

```bash
python tools/export_repo_indexes.py
```

---

## DIFFERENCES FROM /wire (L9)

- No `wire_executor.py` DAG — single script
- No auto-fix — verification only; fix wiring manually
- Emma-specific: routes.py, v1 routers, repo-index
- No protected-files escalation
