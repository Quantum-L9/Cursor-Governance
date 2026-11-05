---
name: l9-audit-plans
description: "refine leftover plan todos already in stale/ or built/: fold or compile onto a same-concern plan; harvested donors are omitted. use when /l9-audit-plans or leftover-todo refine runs. shelf_plans.py is retired and must not run."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, audit-plans, plans, stale, refine, harvested]
  owner: igor_beylin
  status: active
  version: 2.1.0
  updated: 2026-11-03
---

# l9-audit-plans

Leftover-todo refine for the Cursor plans store. Slash `/l9-audit-plans`
is the explicit invoke. This is **not** `l9-pipeline-audit` (live-queue +
harvest) and **not** `l9-plan` (author a plan).

`shelf_plans.py` is retired (archived at `scripts/_archived/shelf_plans.py`). Do not run it. Do not restore it.
This skill does not move `.plan.md` files between folders.

Do **not** auto-Build. Do **not** `make campaign`. SessionStart must not call
refine. `l9-intelligence-harvest` stays read-only.

Law: [references/shelves.md](references/shelves.md),
[references/refine.md](references/refine.md),
[references/concerns.md](references/concerns.md).

## Status vocabulary

These names describe where a plan already lives. This skill does not place a
plan into them.

| Location | Who belongs there |
|---|---|
| *(root)* | Current unbuilt only. `_TEMPLATE.plan.md` stays. `status: current` |
| `partially-built/` | Started: ≥1 todo `completed` or `in_progress`, not all done |
| `built/` | All todos done, or `built: true` / `status: completed` |
| `stale/` | Unbuilt, not current (written, never started) |
| `archive/` | Leftover companions |
| `archive/superseded/` | `status: superseded` or older same-slug copy |

`partial/`, `backlog/`, and `pending/` are not shelves. Do not create them.
This skill does not fold them into another folder.

`harvested: true` is a tag, never a status.

## Compact workflow

1. Run `scripts/run_audit_plans.py --workspace "$(pwd)"` (refine → README).
   Do not run `shelf_plans.py`.
2. If `L9_AUDIT_PLANS_REFINE=0`, refine is skipped (diagnose).
3. Present the script stdout. Do not invent paths it omitted.
4. Run `../l9-pipeline-audit/scripts/audit_plans.py --workspace "$(pwd)" --format markdown` as the live-queue display only.
5. Do not call `l9-intelligence-harvest` as a writer from this skill.

## Validation

```bash
python3 scripts/self_test.py
```
