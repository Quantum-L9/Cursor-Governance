---
name: confirm-wiring
version: "3.0.0"
description: "Verify a workspace or component is fully wired"
auto_chain: ynp
---

# /confirm-wiring — Confirm wiring

Delegates to skill **`l9-governance-wiring`** (mode `confirm-wiring`).

## EXECUTION

1. Read and follow skill `l9-governance-wiring` in mode `confirm-wiring`.
2. Auto-chain `/ynp`.

## FORBIDDEN

- Mutating wiring from this confirm-only slash (use `/wire`)
- Pasting a DAG body into this file
