---
name: governance
version: "2.0.0"
description: "Governance check, wiring, and violation report"
auto_chain: ynp
---

# /governance — Governance check

Delegates to skill **`l9-governance-wiring`** (mode `governance check`).

`/violation` is an alias of this command. Report-violation is a **mode**, not a second slash.

## EXECUTION

1. Read and follow skill `l9-governance-wiring` in mode `governance check`.
2. If the user asked to report a violation (`/violation` or explicit report), emit the report format from archived `commands/_archived/violation.md` and follow that skill's logging path. Do not recreate `/violation`.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Recreating `/violation` as a live command file
- Weakening protected-path or approval gates
