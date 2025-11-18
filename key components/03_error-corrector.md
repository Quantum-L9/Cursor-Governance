---
title: Error Pattern Recall & Auto-Correction Engine
version: 1.0.0
created: 2025-10-14
owner: Igor Beylin
source: repeated-mistakes.md + quick-fixes.md + session_status.md
tags: [error-correction, memory, governance, cursor]
domain: learning
type: system-module
production_ready: true
---

# 🔁 BLOCK 01 — Purpose & Summary

## Purpose
Recall known error patterns and auto-apply corrections from memory to prevent recurring logic failures in workflows or prompts.

## Summary
This module loads `repeated-mistakes.md` and `quick-fixes.md`, matches current issues to prior ones, and applies structured fixes based on learned patterns.

---

# 🔍 BLOCK 02 — Pattern Detection Engine

1. Load session context from `session_status.md`
2. Read:
   - `@.GlobalCommands/learning/failures/repeated-mistakes.md`
   - `@.GlobalCommands/learning/patterns/quick-fixes.md`
3. Match new errors (regex, key phrases, node paths)
4. For each match:
   - Apply fix template
   - Log patch to `memory_log.json`

---

# 🛠️ BLOCK 03 — Application Pipeline

```yaml
error_corrector:
  sources:
    - repeated-mistakes.md
    - quick-fixes.md
  apply_fix: true
  logging:
    enabled: true
    output: memory_log.json
```

---

# 🧠 BLOCK 04 — Companion Files (Autoloaded)

- `memory_log.json` — updated with new fix applications
- `change_log.md` — if structural fixes are applied
- `repeated-mistakes.md` — read-only match base
- `quick-fixes.md` — fix template source