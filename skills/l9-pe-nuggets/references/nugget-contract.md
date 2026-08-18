<!-- L9_META
l9_schema: 1
parent: l9-pe-nuggets
layer: reference
role: nugget_contract
tags: [campaign, pe, plan-window, nuggets]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-17
/L9_META -->

# Nugget contract

`extract_nuggets.py` is the only writer of primed `nuggets.json`.
`run_campaign.py` loads it through `l9-pe-nuggets`. Campaign activate
does not own the script.

## Payload

```json
{
  "schema": "l9.program-execution.nuggets.v1",
  "campaign_id": "<id>",
  "nuggets": []
}
```

Each task becomes one nugget. `nugget_id` is `NUG-00N` when omitted.
A stack nugget is appended when `stack-proof.json` exists.

## Seal

`infer_plan_status` maps:

| Seed | Result |
|---|---|
| Ready / ConditionallyReady | keep |
| Draft | Partial |
| Partial / Blocked / Failed | keep |
| all tasks have actions, consumers, entrypoints, validation, nugget_id | Ready |
| some tasks | Partial |
| no tasks | Blocked |

Sealable statuses are Ready and ConditionallyReady only.

## Refuse

- empty `campaign_id`
- zero nuggets
- missing PyYAML on `project_plan_window`
