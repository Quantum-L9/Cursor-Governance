---
name: migrate
version: "1.0.0"
description: "TRIGGER ONLY — Invokes migrate_executor.py for autonomous code migration"
auto_chain: ynp
dag_executor: .cursor-commands/workflows/migrate_executor.py
---

In plain English: 
When you need to rename something across the entire codebase (a function name, import path, class name, variable, etc.), /migrate finds every occurrence using rg, replaces them all using sed, validates the changes compile, and commits locally.

When to use it: 
Use /migrate when you have a pattern like old_name that needs to become new_name across many files — function renames, import path changes, class renames, etc.

Example:
python3 .cursor-commands/workflows/migrate_executor.py "from core.old_module" "from core.new_module"

This will find all 47 files with that import, sed-replace them all, validate with py_compile, and commit (no push).

----

# /migrate — Code Migration (v1.0.0)

## THIS IS A TRIGGER ONLY

`/migrate` invokes the Migrate Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor-commands/workflows/migrate_executor.py "old_pattern" "new_pattern"
```

## WHAT THE DAG DOES (FULLY AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  INDEX-ANALYSIS   │ Find ALL occurrences with rg       │
├─────────────────────────────────────────────────────────┤
│  PATTERN-EXTRACT  │ Analyze migration type             │
├─────────────────────────────────────────────────────────┤
│  BATCH-GENERATE   │ Group changes by file              │
├─────────────────────────────────────────────────────────┤
│  APPLY-CHANGES    │ sed/cp ONLY (NO manual rewrite)    │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile + import test           │
├─────────────────────────────────────────────────────────┤
│  WIRE-REFS        │ Update dependent imports           │
├─────────────────────────────────────────────────────────┤
│  CONFIRM-WIRING   │ Verify old pattern removed         │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **sed-based** — Uses sed for replacements, NOT manual rewriting
- **Protected file awareness** — Warns but continues
- **Auto-wiring** — Updates dependent imports
- **Auto-report** — Uses canonical report generator
- **Safe commit** — Commits locally, does NOT push

## USAGE

```bash
# Simple replacement
python3 .cursor-commands/workflows/migrate_executor.py "old_name" "new_name"

# Import migration
python3 .cursor-commands/workflows/migrate_executor.py "from old.module" "from new.module"

# Function rename
python3 .cursor-commands/workflows/migrate_executor.py "old_function(" "new_function("

# Check status
python3 .cursor-commands/workflows/migrate_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/migrate_executor.py --resume

# Reset state
python3 .cursor-commands/workflows/migrate_executor.py --reset
```

## STATE FILE

Execution state is persisted to `.migrate_executor_state.json`

If interrupted, resume with `--resume`.

## KEY PRINCIPLE

**sed, NOT manual rewriting.**

The executor uses `sed -i` for all replacements. This ensures:
- Exact pattern matching
- No accidental modifications
- Reproducible results
- Audit trail in commit

## OUTPUT

The executor produces:
1. Terminal progress for each step
2. GMP report at `reports/GMP-Report-*.md`
3. Local commit (no push)

## ENFORCEMENT

The DAG is MANDATORY. The slash command is just a trigger.

All step ordering, validation, and reporting is handled by the executor.
