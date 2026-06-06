<!--
--- SKILL_META ---
skill_schema: 1
origin: structured-reasoning
layer: reference
role: reasoning_kernel
tags: [reasoning, planning, implementation, rollback]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - harvested: core-thinking-mode Block 9 (Suite-5 legacy, stripped n8n/memory refs)
--- /SKILL_META ---

Purpose:
YAML skeleton for Block 9 implementation plans before non-trivial coding.
-->

# Implementation Plan Template

Use before writing code on moderate+ complexity. Required by `references/reasoning-protocol.md` Block 9.

```yaml
Implementation Plan:
  Critical Path:
    - step: 1
      action: "[Concrete action]"
      est_min: N
      risk: safe | moderate | high
      depends_on: []
    - step: 2
      action: "[Next action]"
      est_min: N
      depends_on: [1]

  Files Modified:
    - path: "path/to/file"
      lines: "XX-YY or entire"
      change: "[description]"

  Files Created:
    - path: "path/to/new"
      purpose: "[why]"

  Files Deleted:
    - path: "path/to/old"
      reason: "[why]"

  Rollback Plan:
    trigger: "[Step or condition that triggers rollback]"
    steps:
      - "[Restore / revert / disable]"
      - "[Verify restoration]"
    verify: "[How to confirm rollback succeeded]"

  Testing Strategy:
    unit: "[components]"
    integration: "[flows]"
    manual: "[scenarios]"

  Deployment Order:
    - "[Tier 1 — e.g. schema/migrations first]"
    - "[Tier 2 — services / modules]"
    - "[Tier 3 — UI / config last]"
```

## Rules

- Every destructive or irreversible step MUST have a rollback branch.
- Critical path steps MUST name dependencies explicitly.
- If plan cannot be filled without guessing → label gaps `Unknown` and halt Block 9 until verified.
