---
name: l9-pipeline-audit
description: "audit plans and harvest via l9-intelligence-harvest. use when /l9-pipeline-audit or /plan-audit runs. SessionStart does not run this pack. Program Execution campaigns are not a live audit surface."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pipeline-audit, plans, campaigns, harvest]
  owner: igor_beylin
  status: active
  version: 1.5.0
  updated: 2026-11-17
---

# l9-pipeline-audit

Sole live-queue + harvest orchestrator. Slash `/l9-pipeline-audit` (alias
`/plan-audit`) is the explicit invoke. SessionStart does **not** read, scan,
analyze, archive, or emit this pack. Run `scripts/audit_pipeline.py` from the
slash only (plans hop `.cursor/plans` → `~/.cursor/plans`). Program Execution
campaigns are not scanned. `--archive-spent` is opt-in on that CLI.

## Skills this workflow calls

| Step | Owner | Must not substitute |
|---|---|---|
| Plans live-queue | this pack `scripts/audit_plans.py` | a second plans scanner |
| Shelf built / partial / stale | this pack `scripts/shelf_plans.py` | a one-off shelf script |
| Harvest | `l9-intelligence-harvest` bind + inventory + qualify + validate | `l9-harvest-pipeline`, inventing `l9-intelligence-harvest` |
| Emit | this pack `scripts/run_intelligence_harvest.py` | a Program Execution controller |
| Execute packet | `/gmp` (`commands/gmp.md`) | `make campaign` |

`l9-global-architect` stays STANDALONE if invoked. Repository presence does not
flip it to PE-integrated mode.

Plans-store refine (fold/compile leftover todos, `harvested: true` omit) is
`/l9-audit-plans`. SessionStart does not call this pack. Omit
`harvested: true` donors from the live queue.

## Compact workflow

1. Run `scripts/audit_pipeline.py --workspace "$(pwd)" --gov-root "$HOME/.cursor-governance" --format markdown`.
   Add `--archive-spent` only when you intend the run to archive spent
   plans — it is opt-in and mutates the plans store; the default run is
   read-only. `--archive-spent` is the capped spent-root move. It is not
   the shelf below.
2. Shelf only when the operator asked to move built, partial, or stale
   plans. Run `scripts/shelf_plans.py --workspace "$(pwd)" --gov-root "$HOME/.cursor-governance"`.
   That command is a dry-run. Add `--apply` only to mutate. Todo-complete
   plans are built even when frontmatter has no `status` or `built` field;
   `--apply` writes that frontmatter as it shelves. Do not draft a
   replacement script.
3. List `harvestable` by surface and concern. Do not auto-shelf mixed donors.
4. Harvest only named donors through `scripts/run_intelligence_harvest.py`.
5. Emit compiled packets to `docs/plans/` or a campaign `HARVEST_INTENT.md`.
   Donors get `compiled_into` only.
6. Execute a compiled packet with `/gmp`. Do not run `make campaign`.

## Validation

```bash
python3 scripts/self_test.py
```
