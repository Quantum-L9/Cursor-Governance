<!-- L9_META
l9_schema: 1
parent: l9-pipeline-audit
tags: [pipeline-audit, surfaces]
status: active
version: 1.0.0
/L9_META -->

# Pipeline-audit surfaces

Same component verdicts as `l9-plan-audit` (`live_invariant`, `stale_wiring`,
`superseded_mission`, `spent`). `harvestable` = live + stale/superseded.

| Surface | Root | Spent | Harvest emit |
|---|---|---|---|
| plans | `docs/plans/` top-level `*.plan.md` | all todos done / `built` / `superseded` | `docs/plans/<concern>_compiled_M-D-YY.plan.md` |
| wip | `WIP/` except Legal Defense and secret globs | inventory `landed` / `possible-landed` with sha match | `WIP/<M-D-YY>/<concern>/` |
| campaigns | `environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml` | lifecycle complete / cancelled | `<campaign>/HARVEST_INTENT.md` |

Do not `git mv` a mixed donor to archive. Do not instantiate a Program Lock.
Do not write `WIP/INVENTORY.yaml` from this scan (that is `wip_corpus inventory`).
