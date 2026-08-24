---
name: analyze_evaluate
version: "8.0.0"
description: "Combined analysis + evaluation in one pass"
auto_chain: ynp
---

# /analyze_evaluate — Combined analysis + evaluation

Delegates to skill **`l9-code-analysis`** (mode `analyze+evaluate`).

When the user names a component, import, or wiring check, also load **`l9-component-verification`** (mode `verify-component`).

## EXECUTION

1. Read and follow skill `l9-code-analysis` in mode `analyze+evaluate`.
2. If the target is a component verify ladder, follow `l9-component-verification` mode `verify-component` as well.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Pasting a DAG or inventing a second combined protocol
- Recreating `/verify-component` as a live slash
