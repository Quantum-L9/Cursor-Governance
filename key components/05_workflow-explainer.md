---
title: Workflow Architecture Annotator
version: 1.0.0
created: 2025-10-14
owner: Igor Beylin
source: n8n exports + reasoning_n8n.md + ai_reasoning blocks
tags: [n8n, explainer, annotation, reasoning, documentation]
domain: automation
type: explainer
production_ready: true
---

# 🔍 BLOCK 01 — Purpose & Summary

## Purpose
Provide human-readable explanation of any `.n8n.json` workflow: structure, nodes, logic flow, and failure paths.

## Summary
Analyzes node purposes, relationships, execution flow and reasoning layers (ai_reasoning). Outputs detailed architectural doc with reasoning highlights.

---

# 🧭 BLOCK 02 — Annotator Flow

1. Load `.n8n.json` file
2. Parse nodes and flows:
   - Identify entry points, LLM nodes, split/merge logic, terminal nodes
3. Annotate:
   - Each node's purpose
   - Expected I/O
   - Failure paths
   - Chain of thought or agent invocation
4. Generate Markdown doc:
   - Sectioned by flow
   - Includes metadata and logic commentary

---

# 📦 BLOCK 03 — YAML Parameters

```yaml
workflow_explainer:
  input: "workflows/*.n8n.json"
  output: "docs/workflow-explained.md"
  metadata: true
  node_analysis: true
  reasoning_overlay: true
```

---

# 📂 BLOCK 04 — Companion Assets

- `reasoning_n8n.md` — overlays logic heuristics per node
- `session_status.md` — links recent edits and reasoning notes
- `ai_reasoning/` — optional folder for node-level thoughts