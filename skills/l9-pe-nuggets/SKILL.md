---
name: l9-pe-nuggets
description: extract primed campaign nuggets.json and seal plan_status after stack-proof. use when the PLAN window runs, make campaign needs nuggets, or extract_nuggets.py is invoked. do not use as a campaign front door (use l9-pe-campaign-activate / make campaign).
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, program-execution, campaign, plan-window, nuggets]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-08-17
---

# PE Nuggets

## Purpose

Own the PE PLAN window. After stack-proof and before emit, write primed
`nuggets.json` and project `plan_status`. Compile refuses stub seeds and
unsealed status. This skill is not a campaign front door.

## Core Contract

| Item | Value |
|---|---|
| Caller | `make campaign` via `run_campaign.py` `default_plan_window` |
| Script | [scripts/extract_nuggets.py](scripts/extract_nuggets.py) |
| Output | `$HOME/.l9/primed/<id>/nuggets.json` |
| Seal | `plan_status` in `{Ready, ConditionallyReady}` |
| Schema | `l9.program-execution.nuggets.v1` |

## Authority Order

1. Explicit PLAN-window / nugget request
2. Campaign seed + primed `stack-proof.json`
3. [references/nugget-contract.md](references/nugget-contract.md)
4. `Unknown` — refuse empty PLAN windows; do not invent tasks

## Compact Workflow

1. Require `campaign_id` and at least one task or stack citation.
2. Run:

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  skills/l9-pe-nuggets/scripts/extract_nuggets.py
```

The runner loads `project_plan_window(seed, primed_dir, stack_proof_path)`.
Do not call this as a substitute for `make campaign INTENT=`.

3. Refuse when nuggets are empty or `plan_status` is unsealed.

## MUST

- Write `nuggets.json` only under the primed campaign dir
- Assign `nugget_id` when the seed omitted it
- Cite `stack-proof.json` when that file exists
- Leave campaign emit, pec, and merge to `l9-pe-campaign-activate`

## MUST NOT

- Invent tasks, campaign ids, or essay summaries
- Seal `Draft` / `Partial` / `Blocked` / `Failed`
- Live under `l9-pe-campaign-activate/scripts/` as the owner
- Open or merge PRs

## Resource Map

- [references/nugget-contract.md](references/nugget-contract.md)
- [scripts/extract_nuggets.py](scripts/extract_nuggets.py)
- [scripts/test_extract_nuggets.py](scripts/test_extract_nuggets.py)

## Validation

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  skills/l9-pe-nuggets/scripts/test_extract_nuggets.py
```

## Failure Handling

- Missing `campaign_id` → `NuggetError`
- No nuggets → refuse empty PLAN window
- PyYAML missing during `project_plan_window` → `NuggetError`
