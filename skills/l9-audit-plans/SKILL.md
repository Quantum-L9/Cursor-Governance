---
name: l9-audit-plans
description: "shelf then refine the Cursor plans store: root stays current unbuilt only; leftover todos fold or compile; harvested donors are omitted. use when /l9-audit-plans, a plans-store shelf audit, or leftover-todo refine runs."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, audit-plans, plans, shelf, stale, refine, harvested]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-09-05
---

# l9-audit-plans

Plans-store shelf organizer and leftover-todo refine. Slash `/l9-audit-plans`
is the explicit invoke. This is **not** `l9-pipeline-audit` (live-queue +
harvest) and **not** `l9-plan` (author a plan).

Do **not** auto-Build. Do **not** `make campaign`. SessionStart must not call
refine. `l9-intelligence-harvest` stays read-only.

Law: [references/shelves.md](references/shelves.md),
[references/refine.md](references/refine.md),
[references/concerns.md](references/concerns.md).

## Shelves (binding)

| Location | Who belongs there |
|---|---|
| *(root)* | Current unbuilt only. `_TEMPLATE.plan.md` stays. `status: current` |
| `partially-built/` | Started: ≥1 todo `completed` or `in_progress`, not all done |
| `built/` | All todos done, or `built: true` / `status: completed` |
| `stale/` | Unbuilt, not current (written, never started) |
| `archive/` | Leftover companions |
| `archive/superseded/` | `status: superseded` or older same-slug copy |

`partial/` is not a shelf. Fold it into `partially-built/` and delete it.
`backlog/` and `pending/` are not shelves. Fold them into `stale/` and delete them.

`harvested: true` is a tag, never a status.

## Compact workflow

1. Run `scripts/run_audit_plans.py --workspace "$(pwd)"` (shelf → refine → shelf → README).
2. If `L9_AUDIT_PLANS_REFINE=0`, refine is skipped (diagnose).
3. Present the script stdout. Do not invent paths it omitted.
4. Run `../l9-pipeline-audit/scripts/audit_plans.py --workspace "$(pwd)" --format markdown` as the live-queue display only.
5. Do not call `l9-intelligence-harvest` as a writer from this skill.

## Validation

```bash
python3 scripts/self_test.py
```
