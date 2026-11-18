<!-- L9_META
l9_schema: 1
parent: l9-pipeline-audit
tags: [pipeline-audit, surfaces]
status: active
version: 1.4.0
/L9_META -->

# Pipeline-audit surfaces

Same component verdicts (`live_invariant`, `stale_wiring`,
`superseded_mission`, `spent`). `harvestable` = live + stale/superseded.

The live surface is plans. Program Execution campaigns are not scanned.
The slash report NEXT 1–3 fills from the plans queue. Cap 3.

| Surface | Root | Spent | Harvest emit |
|---|---|---|---|
| plans | tracked `docs/plans` via `.cursor/plans` → `~/.cursor/plans` | all todos done / `built` / `superseded` | `docs/plans/<concern>_compiled_M-D-YY.plan.md` |

SessionStart does not run this scan. A human slash (`/l9-pipeline-audit`
/ `/plan-audit` with `--archive-spent`) may move spent
root plans to `built/` or `archive/superseded/` (cap 8). Do not move mixed
harvestable donors. Do not instantiate a Program Lock. Do not run `make campaign`.
Acquire and hold the store clone's repo-write lock around `--archive-spent`.
Skip archive when that lock is already held.

`scripts/shelf_plans.py` is the reusable shelf for a slash that was asked to
move plans. It is dry-run unless `--apply` is passed. Todo-complete plans
count as built even when frontmatter was not updated. Root plans that were
never started leave the live root for `stale/`; started plans leave it for
`partially-built/`. README live-queue names, compiled packets, and
never-started plans edited in the last 7 days stay at the root. Do not draft
a replacement script.
