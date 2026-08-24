---
name: lint
version: "2.0.0"
description: "Systematic lint fixes via l9-code-maintenance (no commit)"
auto_chain: ynp
---

# /lint — Lint fix

Delegates to skill **`l9-code-maintenance`** (mode `lint-fix`).

`/lint-fix` is an alias of this command.

## EXECUTION

1. Read and follow skill `l9-code-maintenance`.
2. Run dry-run first: `python3 skills/l9-code-maintenance/scripts/code_maintenance.py --mode lint-fix --dry-run`.
3. Apply fixes only after dry-run. Do **not** commit.
4. Auto-chain `/ynp`.

## FORBIDDEN

- Creating a local commit from this slash
- Auto-staging or treating lint as a publish step
- Skipping `--dry-run`
- Recreating `/lint-fix` as a live command file
