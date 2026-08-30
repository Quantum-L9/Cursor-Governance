<!-- L9_META
l9_schema: 1
parent: l9-pipeline-audit
tags: [pipeline-audit, surfaces]
status: active
version: 1.0.0
/L9_META -->

# Pipeline-audit surfaces

Same component verdicts (`live_invariant`, `stale_wiring`,
`superseded_mission`, `spent`). `harvestable` = live + stale/superseded.

Plans, WIP, and campaigns are one family. SessionStart NEXT 1–3 takes **one
slot per surface** first (plans, then wip, then campaigns), then fills leftover
slots. Eligible WIP is harvestable (`possible-landed`) or pending-active — not
inventory-`landed`. Cap 3.

| Surface | Root | Spent | Harvest emit |
|---|---|---|---|
| plans | tracked `docs/plans` via `.cursor/plans` → `~/.cursor/plans` | all todos done / `built` / `superseded` | `docs/plans/<concern>_compiled_M-D-YY.plan.md` |
| wip | `WIP/` except Legal Defense and secret globs | inventory `landed` (sha match or `landed:`); `possible-landed` is leftover | `WIP/<M-D-YY>/<concern>/` |
| campaigns | `environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml` | lifecycle complete / cancelled | `<campaign>/HARVEST_INTENT.md` |

SessionStart (`--archive-spent`, fail-open, cap 8) may `shutil.move` spent
root plans to `built/` or `archive/superseded/` and inventory-`landed` WIP to
`WIP/_archived/`. Do not move mixed harvestable donors. Do not move
`CAMPAIGN_SOURCE.yaml`. Do not instantiate a Program Lock.
Do not write `WIP/INVENTORY.yaml` from this scan (that is `wip_corpus inventory`).
Acquire and hold the store clone's repo-write lock (`$GC` when SessionStart
falls back to the governance plans/WIP trees) around `--archive-spent`.
Skip archive when that lock is already held.
