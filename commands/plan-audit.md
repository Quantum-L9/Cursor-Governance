---
name: plan-audit
version: "1.6.0"
description: "Compatibility alias of /l9-pipeline-audit (plans + PE campaigns)"
auto_chain: null
---

# /plan-audit → /l9-pipeline-audit

Compatibility alias. **Do not** run a plans-only display path.

1. Read [`skills/l9-pipeline-audit/SKILL.md`](../skills/l9-pipeline-audit/SKILL.md).
2. Execute that protocol (multi-surface scan; harvest only when donors are named).

SessionStart does not run this pack. `/l9-audit-plans` is leftover-todo
refine only and moves no plans; this slash may pass `--archive-spent`.

Shelving built, partial, or stale plans is
`skills/l9-pipeline-audit/scripts/shelf_plans.py` (dry-run; add `--apply`
only when the operator asked to move them). Do not draft a replacement
script.
