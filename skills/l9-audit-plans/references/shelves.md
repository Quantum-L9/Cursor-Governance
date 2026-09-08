<!-- L9_META
l9_schema: 1
parent: l9-audit-plans
tags: [audit-plans, shelves]
status: active
version: 1.0.0
/L9_META -->

# Plans-store shelves

Live names only:

| Folder | Meaning |
|---|---|
| *(root)* | Current unbuilt |
| `partially-built/` | Started, not finished |
| `built/` | Done |
| `stale/` | Written, never started, not current |
| `archive/` | Leftover companions |
| `archive/superseded/` | Superseded copies |

Retired. Do not create. Fold then delete:

| Retired | Fold into |
|---|---|
| `partial/` | `partially-built/` |
| `backlog/` | `stale/` |
| `pending/` | `stale/` |

Current = README live-queue name, this week's `_*_M-D-YY` stamp, `compiled: true`
with remaining todos, or an operator-named hex. Do not treat a bulk mtime bump
as current. Companions (`.plan.json`, `.activate.yaml`, `.harvest.json`,
`.section-receipt.json`) move with their `.plan.md`.
