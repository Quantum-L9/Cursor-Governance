````markdown
---
title: Recursive Self-Check Protocol
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: ai_operator + governance system
tags: [validation, n8n, governance, audit, protocol]
domain: validation
type: protocol
production_ready: true
---

## 🎯 Purpose
This protocol is triggered during every build/execute cycle to ensure logic is validated recursively using prior learnings.

---

## 🔁 Core Steps

1. Cross-check fields with schema
2. Check for redundant logic
3. Validate all node inputs/outputs
4. Match structure with known-good patterns
5. Compare to `quick-fixes.md` and `repeated-mistakes.md`

---

## 🧠 Behavior

- Auto-trigger during:
  - Builds
  - Fixes
  - Modifications

- Output:
  - Confirms logic match
  - Warns on schema drift
  - Updates memory with pass/fail result

---

## ❌ Disabled

- No 5 Whys
- No sanity-check

---

## ✅ Enabled

- Field & pattern match
- Memory learning
- Telemetry tagging
````
