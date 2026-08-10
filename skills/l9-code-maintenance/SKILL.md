---
name: l9-code-maintenance
description: lint-fix, migrate, clean/compress, consolidate, and refactor-sweep via dag executors with a --dry-run CLI. use for systematic lint fixes, pattern migrations, or read-only refactor impact analysis before mutating.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, lint, migrate, refactor, maintenance, dag, dry-run]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-06
disable-model-invocation: true
---

# Code Maintenance

## Purpose

Trigger-only skill for systematic code maintenance: lint fixing, pattern migration,
cleanup, consolidation planning, and read-only refactor impact sweeps. Prefer the
CLI with `--dry-run` before any mutating mode.

## Core Contract

| Mode | Executor / path | Mutates | Dry-run |
|------|-----------------|---------|---------|
| lint-fix | `workflows/lint_fix_executor.py` | yes | `--dry-run` scan+categorize only |
| migrate | `workflows/migrate_executor.py` | yes (sed) | `--dry-run` index+plan only |
| clean_compress | ruff/vulture | yes | agent must not auto-run without user |
| consolidate | plan → gmp | plan only | n/a |
| refactor-sweep | `scripts/refactor_sweep.py` | no | always dry-run |
| refactor | `workflows/dags/refactoring_dag.py` | yes | escalate via GMP when sweep says so |

## Invocation

```bash
python3 skills/l9-code-maintenance/scripts/code_maintenance.py \
  --mode refactor-sweep --dry-run "<intent>"

python3 skills/l9-code-maintenance/scripts/code_maintenance.py \
  --mode migrate --dry-run -- "old_pattern" "new_pattern"

python3 skills/l9-code-maintenance/scripts/code_maintenance.py \
  --mode lint-fix --dry-run
```

Load [references/maintenance-workflows.md](references/maintenance-workflows.md) for
DAG paths. Load [references/dry-run-contract.md](references/dry-run-contract.md) for
write-refusal rules. Load [references/refactor-sweep-protocol.md](references/refactor-sweep-protocol.md)
for discovery → governance decision.

## Resource Map

- [references/maintenance-workflows.md](references/maintenance-workflows.md) — mode invocation
- [references/dry-run-contract.md](references/dry-run-contract.md) — `--dry-run` write refusal
- [references/refactor-sweep-protocol.md](references/refactor-sweep-protocol.md) — sweep phases + report
- [references/protected-paths.md](references/protected-paths.md) — fail-closed protected set
- `scripts/code_maintenance.py` — single CLI entry
- `scripts/refactor_sweep.py` — deterministic sweep analyzer
- `scripts/self_test.py` — pack gate

## Authority Order

1. User pattern / scope / explicit `--dry-run`.
2. Executor DAGs under `workflows/` (via `.cursor-commands` symlink).
3. PlasticOS: `make push` never raw git push; executors commit locally only (NO PUSH).

## Validation

```bash
python3 skills/l9-code-maintenance/scripts/self_test.py
python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode refactor-sweep --dry-run "toy rename"
```

Lint-fix and migrate executors MUST run py_compile / validation before commit when not dry-run.
Refactor-sweep MUST NOT write code. Dry-run MUST NOT write state files, reports, or commits.

## Failure Handling

Protected file in migrate/wire path → escalate to `l9-gmp-protocol`.
Sweep non-mechanical or protected → Governance Decision = GMP REQUIRED; STOP.
