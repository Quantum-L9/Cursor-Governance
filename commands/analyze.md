---
name: analyze
version: "8.0.0"
description: "Rapid exploration — structure, flows, hotspots"
auto_chain: ynp
---

# /analyze — Rapid exploration

Delegates to skill **`l9-code-analysis`** (mode `analyze`).

When the user names a component, import, or wiring check, also load **`l9-component-verification`** (mode `probe`).

## EXECUTION

1. Read and follow skill `l9-code-analysis` in mode `analyze`.
2. If the target is a component / import / wiring check, follow `l9-component-verification` mode `probe` as well.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Pasting a DAG or inventing a second analyze protocol
- Recreating `/probe` as a live slash
