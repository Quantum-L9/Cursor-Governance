---
name: evaluate
version: "8.0.0"
description: "Deep evaluation — compliance, health, gaps"
auto_chain: ynp
---

# /evaluate — Deep evaluation

Delegates to skill **`l9-code-analysis`** (mode `evaluate`).

When the user names a component, export, or API-instantiation check, also load **`l9-component-verification`** (mode `audit-component`).

## EXECUTION

1. Read and follow skill `l9-code-analysis` in mode `evaluate`.
2. If the target is a component audit, follow `l9-component-verification` mode `audit-component` as well.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Pasting a DAG or inventing a second evaluate protocol
- Duplicating the component-audit procedure here (`/audit-component` owns that slash)
