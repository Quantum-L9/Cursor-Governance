---
name: clean_compress
version: "2.0.0"
description: "Clean and compress code via l9-code-maintenance"
auto_chain: ynp
---

# /clean_compress — Clean / compress

Delegates to skill **`l9-code-maintenance`** (mode `clean_compress`).

## EXECUTION

1. Read and follow skill `l9-code-maintenance` in mode `clean_compress`.
2. Dry-run first. Do not auto-run mutating cleanup without user intent.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Auto-running ruff/vulture without the skill's dry-run
- Auto-commit
