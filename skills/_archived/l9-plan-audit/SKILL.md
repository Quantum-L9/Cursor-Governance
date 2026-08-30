---
name: l9-plan-audit
description: "deprecated — do not activate. use l9-pipeline-audit. archived out of live skills/ discovery."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, plan, audit, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 1.2.0
  updated: 2026-08-29
  superseded_by: l9-pipeline-audit
---

# l9-plan-audit (deprecated)

Do not activate. Superseded by **`l9-pipeline-audit`**. The plans scanner lives at
`skills/l9-pipeline-audit/scripts/audit_plans.py`. SessionStart `### Plan audit`
is `audit_pipeline.py --format session-start`.
