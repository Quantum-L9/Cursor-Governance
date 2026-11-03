<!-- L9_META
l9_schema: 1
parent: l9-audit-plans
tags: [audit-plans, shelves]
status: active
version: 1.0.0
/L9_META -->

# Plans-store shelves

`scripts/shelf_plans.py` is retired. These names are vocabulary for plans that
already sit in a folder. This skill does not move a plan into a folder, and it
does not fold `partial/`, `backlog/`, or `pending/`.

Live names only:

| Folder | Meaning |
|---|---|
| *(root)* | Current unbuilt |
| `partially-built/` | Started, not finished |
| `built/` | Done |
| `stale/` | Written, never started, not current |
| `archive/` | Leftover companions |
| `archive/superseded/` | Superseded copies |

Do not create:

| Name | |
|---|---|
| `partial/` | not a shelf |
| `backlog/` | not a shelf |
| `pending/` | not a shelf |

Current = README live-queue name, this week's `_*_M-D-YY` stamp, `compiled: true`
with remaining todos, or an operator-named hex. Do not treat a bulk mtime bump
as current. Companions (`.plan.json`, `.activate.yaml`, `.harvest.json`,
`.section-receipt.json`) stay beside the plan that owns them.
