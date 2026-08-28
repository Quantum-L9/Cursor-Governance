---
name: l9-pipeline-audit
description: "audit plans, WIP, and PE campaigns; harvest via l9-intelligence-harvest. use when /l9-pipeline-audit runs."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pipeline-audit, plans, wip, campaigns, harvest]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-08-28
---

# l9-pipeline-audit

On-demand orchestrator. Slash `/l9-pipeline-audit` (alias `/plan-audit`) is the
explicit invoke. SessionStart `l9-plan-audit` stays plans-only and display-only.

## Skills this workflow calls

| Step | Owner | Must not substitute |
|---|---|---|
| Plans live-queue | `l9-plan-audit` `scripts/audit_plans.py` | a second plans scanner |
| WIP inventory | `ops/scripts/wip_corpus.py` (read `WIP/INVENTORY.yaml`; do not write) | walking Legal Defense |
| Campaigns | `environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml` | `make campaign` |
| Harvest | `l9-intelligence-harvest` bind + inventory + qualify + validate | `l9-harvest-pipeline`, inventing `l9-intelligence-harvest` |
| Emit | this pack `scripts/emit_compiled.py` | PE Controller / Program Lock |
| Execute packet | `/gmp` (`l9-gmp-protocol`) | `make campaign` |

`l9-global-architect` stays STANDALONE if invoked. Repository presence does not
flip it to PE-integrated mode.

## Compact workflow

1. Run `scripts/audit_pipeline.py --workspace "$(pwd)" --format markdown`.
2. List `harvestable` by surface and concern. Do not auto-shelf mixed donors.
3. Harvest only named donors through `scripts/run_intelligence_harvest.py`.
4. Emit compiled packets to `docs/plans/`, `WIP/<M-D-YY>/<concern>/`, or a
   campaign `HARVEST_INTENT.md`. Donors get `compiled_into` only.
5. Execute a compiled packet with `/gmp`. Do not run `make campaign`.

## Validation

```bash
python3 scripts/self_test.py
```
