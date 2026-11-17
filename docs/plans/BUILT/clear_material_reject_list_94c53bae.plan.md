---
name: Clear material reject list
overview: Clear the eight material reject phrases on a branch cut from PR 450, then
  open the next stacked pull request. Weight gates and residential/drop-off source
  gates stay.
todos:
- id: branch
  content: From a clean worktree, branch from origin/feat/web-lead-location (PR 450
    at e08b6581)
  status: completed
- id: clear-list
  content: Empty reject_materials in the seed, field default, and view placeholder
  status: completed
- id: bump
  content: Set plasticos_web_leads manifest and README module_version to 19.0.2.9.1
  status: completed
- id: test
  content: Assert conduit and mattress film are not auto-COLD when the material list
    is empty
  status: completed
- id: publish
  content: Publish with make pr base=feat/web-lead-location from a clean tree after
    the parent chain still ends at Staging
  status: completed
isProject: false
built: true
status: built
---

# Clear the material reject list

The eight phrases are one configured list. Clearing it does not change weight gates, source gates, or the material catalog. This is the first of two web-lead pull requests. The vision handoff is the next plan and stacks on the pull request this one opens.

## Remote stack

Open chain, parent to child:

- [#448](https://github.com/cryptoxdog/IB-Odoo_19/pull/448) `Staging` <- `feat/screen-views`
- [#449](https://github.com/cryptoxdog/IB-Odoo_19/pull/449) `feat/screen-views` <- `feat/web-lead-readable-evidence`
- [#450](https://github.com/cryptoxdog/IB-Odoo_19/pull/450) `feat/web-lead-readable-evidence` <- `feat/web-lead-location` at `e08b6581`

This pull request stacks on #450. Cut the branch from `origin/feat/web-lead-location`. Do not cut it from `origin/Staging` or from `feat/screen-views`. Local `HEAD` is already `feat/web-lead-location` at `e08b6581`. Fetch before branching so the cut matches that remote SHA.

`scripts/pr_stack_parent.sh prove` walks every open parent until the chain ends at `Staging`. There is no depth cap. `make pr base=feat/web-lead-location` is the publish for this pull request. Record the opened number. The vision plan stacks on that number's head branch.

## Clean tree

Each publish starts from an empty `git status --porcelain`. [scripts/git_push_with_pr.sh](scripts/git_push_with_pr.sh) refuses a dirty work tree, index, or untracked file before it pushes. Use a new worktree for this branch. Do not carry uncommitted files from `feat/web-lead-location` or from the vision plan. Commit only the reject-list files, then run `make pr` with porcelain still empty.

## What changes

Set `reject_materials` to empty in all three copies, on top of the #450 tree:

- [plasticos_web_leads/data/web_lead_config_data.xml](plasticos_web_leads/data/web_lead_config_data.xml) — the singleton is in `noupdate="0"`. Write the field explicitly as empty (`eval="False"`). Omitting the tag would leave the live row unchanged.
- [plasticos_web_leads/models/web_lead_config.py](plasticos_web_leads/models/web_lead_config.py) — field default becomes empty, so a newly created config does not restore the list.
- [plasticos_web_leads/views/web_lead_config_views.xml](plasticos_web_leads/views/web_lead_config_views.xml) — replace the placeholder so the form no longer shows those phrases as the example.

`get_reject_materials()` on an empty value returns an empty set. [classification_engine.py](plasticos_web_leads/models/classification_engine.py) uses that set because the pipeline always passes it. The engine fallback (`metal`, `glass`, `wood`, and the rest) runs only when `reject_materials` is `None`. Leave that fallback in place.

Leave `reject_sources` as `residential|individual|homeowner|drop-off|drop off`. Leave `hot_min_lbs`, `cold_max_lbs`, and the weight parser alone. Do not touch `plasticos_material_profile` identity mappings. Do not start the vision handoff in this pull request.

## Version

#450's manifest is `19.0.2.9.0`. Its README `module_version` is still `19.0.2.8.12`. Set both [__manifest__.py](plasticos_web_leads/__manifest__.py) and [plasticos_web_leads/README.md](plasticos_web_leads/README.md) to `19.0.2.9.1`. Do not increment the stale README number. No migration script: the `noupdate="0"` seed is what clears the database row on `-u`. The vision plan then takes `19.0.2.9.2`.

## Regression

Add one pure-Python case in [tests/test_triage_pipeline.py](tests/test_triage_pipeline.py): `classify_lead(..., reject_materials=[], material_description` containing `conduit` and `mattress film`, with PVC, post-industrial, and a usable weight above 10,000 lb) is HOT and does not record `reject_material`.

## Publish

From the clean worktree, after the proof above passes:

`make pr base=feat/web-lead-location`

`HEAD` must contain `origin/feat/web-lead-location`. The opened pull request is the parent of the vision plan.

## After the code lands

`make update m=plasticos_web_leads` is what writes the empty list into the running database. CG-4-8938 stays COLD until someone re-runs triage on that lead. Do not add a migration that reclassifies stored leads.

## Build evidence (auto)

- detected_at: `2026-11-10T18:27:51Z`
- conversation_id: `3579d980-e56f-449e-b491-d903cad83db6`
- generation_id: `300da884-b128-4716-903e-61b40df30234`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/3579d980-e56f-449e-b491-d903cad83db6/3579d980-e56f-449e-b491-d903cad83db6.jsonl`
- todos at build time:
- `branch`: completed
- `clear-list`: completed
- `bump`: completed
- `test`: completed
- `publish`: completed

