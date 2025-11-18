---
title: Refactor Assistant for Workflows & Prompts
version: 1.0.0
created: 2025-10-14
owner: Igor Beylin
source: lessons.learned.md + pattern registry
tags: [refactor, optimization, workflow, memory]
domain: engineering
type: suggestion-engine
production_ready: true
---

# 🔁 BLOCK 01 — Purpose & Summary

## Purpose
Identify inefficient or overcomplicated structures and propose optimized alternatives based on learned patterns.

## Summary
Analyzes workflows/prompts for structure bloat, redundant logic, and outdated node usage. Suggests known-good refactors using memory and telemetry.

---

# 📐 BLOCK 02 — Refactor Flow

1. Input: workflow file or prompt markdown
2. Load known-good patterns from `lessons.learned.md`
3. Apply logic:
   - Remove redundant logic
   - Suggest lighter or faster structures
   - Enforce naming / structure rules
4. Output:
   - Refactored candidate (diff-style)
   - Explanation and justification
   - Confidence rating

---

# 📋 BLOCK 03 — YAML Config

```yaml
refactor_assistant:
  input: "prompts/*.md or workflows/*.json"
  apply_suggestions: false
  output_diff: true
  log_changes: true
  companion_patterns: lessons.learned.md
```

---

# 🧠 BLOCK 04 — Companion Files

- `lessons.learned.md` — source of known-good patterns
- `change_log.md` — logs any applied refactor
- `memory_log.json` — stores new pattern recognitions