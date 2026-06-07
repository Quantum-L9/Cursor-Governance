<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [maintenance, lint, migrate, refactor]
status: active
/L9_META -->

# Maintenance Workflows

## lint-fix

```bash
python3 .cursor-commands/workflows/lint_fix_executor.py
python3 .cursor-commands/workflows/lint_fix_executor.py --only B904 N811
```

Autonomous: scan → categorize AUTO/SEMI/MANUAL → fix → validate → rescan → GMP report → local commit (no push).

## migrate

```bash
python3 .cursor-commands/workflows/migrate_executor.py "old_pattern" "new_pattern"
```

sed-based replacements only — NOT manual rewriting. State: `.migrate_executor_state.json` (`--resume`).

## clean_compress

```bash
ruff check --fix . && ruff format .
vulture . --min-confidence 80  # optional dead code
```

## consolidate

Find duplicates with `rg`, plan extraction to shared module, execute via l9-gmp-protocol.

## refactor-sweep (READ-ONLY)

Analyze refactor intent → discovery → classification → impact → governance decision → report → STOP. NO code changes.

## refactor

DAG: `.cursor-commands/workflows/dags/refactoring_dag.py` (`refactoring-v1`).
