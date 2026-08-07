<!-- L9_META
l9_schema: 1
parent: l9-code-maintenance
layer: reference
role: dry_run_contract
tags: [dry-run, write-refusal, maintenance]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-06
/L9_META -->

# Dry-Run Contract

## Purpose

`--dry-run` makes maintenance modes analysis-only. No repo mutation.

## Forbidden under --dry-run

- In-place file edits (sed, ruff --fix, rewrite)
- Writing `.migrate_executor_state.json` or `.lint_fix_executor_state.json`
- Generating GMP report files under `reports/`
- `git add` / `git commit`
- Creating directories or moving trees

## Allowed under --dry-run

- Read-only `rg` / ruff check (without `--fix`)
- Printing plans and REFACTOR SWEEP REPORT to stdout
- Optional `--json` to stdout (not to disk unless user explicitly redirects)

## Mode rules

| Mode | Without --dry-run | With --dry-run |
|------|-------------------|----------------|
| refactor-sweep | N/A (always dry) | discovery + report |
| migrate | full DAG including apply+commit | stop after batch_generate |
| lint-fix | full DAG including apply+commit | stop after categorize |

## Fail-closed

If a code path cannot honor dry-run, refuse with non-zero exit and do not partially write.
