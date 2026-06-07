---
name: l9-code-maintenance
description: lint-fix, migrate, clean/compress, consolidate, and refactor-sweep operations via dag executors. use for systematic lint fixes, pattern migrations, or read-only refactor impact analysis.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, lint, migrate, refactor, maintenance, dag]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# Code Maintenance

## Purpose

Trigger-only skill for systematic code maintenance: lint fixing, pattern migration, cleanup, consolidation planning, and read-only refactor impact sweeps.

## Core Contract

| Mode | Executor | Mutates |
|------|----------|---------|
| lint-fix | `lint_fix_executor.py` | yes |
| migrate | `migrate_executor.py` | yes (sed-based) |
| clean_compress | ruff/vulture | yes |
| consolidate | plan → gmp | plan only |
| refactor-sweep | read-only analysis | no |
| refactor | `refactoring_dag.py` | yes |

Load [references/maintenance-workflows.md](references/maintenance-workflows.md) for invocation and DAG paths.

## Resource Map

- [references/maintenance-workflows.md](references/maintenance-workflows.md) — lint-fix, migrate, clean/compress, consolidate, refactor-sweep, refactor DAG.

## Authority Order

1. User pattern / scope.
2. Executor DAGs under `.cursor-commands/workflows/`.
3. PlasticOS: `make push` never raw git push; executors commit locally only (NO PUSH).

## Validation

Lint-fix and migrate executors MUST run py_compile / validation step before commit.

## Failure Handling

Protected file in migrate/wire path → escalate to l9-gmp-protocol. Refactor-sweep MUST NOT write code.
