<!-- L9_META
l9_schema: 1
parent: l9-pipeline-audit
tags: [pipeline-audit, surfaces]
status: active
version: 1.3.0
/L9_META -->

# Pipeline-audit surfaces

Same component verdicts (`live_invariant`, `stale_wiring`,
`superseded_mission`, `spent`). `harvestable` = live + stale/superseded.

Plans and campaigns are one family. The slash report NEXT 1–3 takes **one
slot per surface** first (plans, then campaigns), then fills leftover
slots. Cap 3.

| Surface | Root | Spent | Harvest emit |
|---|---|---|---|
| plans | tracked `docs/plans` via `.cursor/plans` → `~/.cursor/plans` | all todos done / `built` / `superseded` | `docs/plans/<concern>_compiled_M-D-YY.plan.md` |
| campaigns | `environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml` | lifecycle complete / cancelled | `<campaign>/HARVEST_INTENT.md` |

SessionStart does not run this scan. A human slash (`/l9-pipeline-audit`
/ `/plan-audit` with `--archive-spent`, or `/l9-audit-plans`) may move spent
root plans to `built/` or `archive/superseded/` (cap 8). Do not move mixed
harvestable donors. Do not move `CAMPAIGN_SOURCE.yaml`. Do not instantiate a
Program Lock.
Acquire and hold the store clone's repo-write lock around `--archive-spent`.
Skip archive when that lock is already held.
