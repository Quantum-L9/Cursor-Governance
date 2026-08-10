<!-- L9_META
l9_schema: 1
parent: l9-code-maintenance
layer: reference
role: workflow_map
tags: [maintenance, lint, migrate, refactor, dry-run]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-06
/L9_META -->

# Maintenance Workflows

Prefer the skill CLI. Paths below also work via `.cursor-commands/workflows/` symlink.

## Unified CLI

```bash
python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode <mode> [flags]
```

Modes: `refactor-sweep` | `migrate` | `lint-fix` | `status`

## lint-fix

```bash
python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode lint-fix --dry-run
python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode lint-fix --only B904 N811
python3 workflows/lint_fix_executor.py --dry-run
python3 workflows/lint_fix_executor.py --only B904 N811
```

Autonomous (no dry-run): scan → categorize AUTO/SEMI/MANUAL → fix → validate → rescan → GMP report → local commit (no push).

Dry-run: scan → categorize → print plan → STOP (no apply, no state file, no commit).

## migrate

```bash
python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode migrate --dry-run -- "old" "new"
python3 workflows/migrate_executor.py --dry-run "old_pattern" "new_pattern"
python3 workflows/migrate_executor.py "old_pattern" "new_pattern"
```

sed-based replacements only — NOT manual rewriting. State: `.migrate_executor_state.json` (`--resume`) — skipped under `--dry-run`.

Dry-run: index → pattern extract → batch plan → STOP.

## clean_compress

```bash
ruff check --fix . && ruff format .
vulture . --min-confidence 80  # optional dead code
```

## consolidate

Find duplicates with `rg`, plan extraction to shared module, execute via l9-gmp-protocol.

## refactor-sweep (ALWAYS READ-ONLY)

```bash
python3 skills/l9-code-maintenance/scripts/code_maintenance.py \
  --mode refactor-sweep --dry-run "<intent>"
```

`--dry-run` is the default and required posture for this mode. See
[refactor-sweep-protocol.md](refactor-sweep-protocol.md).

## refactor

DAG: `workflows/dags/refactoring_dag.py` (`refactoring-v1`).
Only after a sweep (or explicit GMP) permits mutation.
