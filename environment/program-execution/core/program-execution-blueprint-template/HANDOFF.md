# Program Handoff: {{PROGRAM_NAME}}

This file is a human-readable governance summary. Runtime facts must be sourced from the latest Controller Handoff Receipt.

## Program revision

- Program version: `{{PROGRAM_VERSION}}`
- Blueprint contract: `program-execution-blueprint.v2`
- Snapshot: `{{DATE}}`
- Accepted Controller Handoff Receipt: `NONE`

## Definition state

- Current wave authorized for admission: `W0`
- Accepted decisions: `NONE`
- Blocking decisions: `DEC-001`
- Blocking Unknowns: `UNK-001`

## Runtime evidence

- Imported Program Lock digest: `UNKNOWN`
- Last Controller Handoff Receipt digest: `UNKNOWN`
- Locally passed tasks: `NONE`
- Completed tasks: `NONE`
- Blocking gate evaluations: `UNKNOWN`

## Exact next action

Refresh evidence and resolve the authority lock before admitting `TASK-002`.

## Authority status

No action is authorized merely by this handoff document. Effective authority is computed by the Controller from the Blueprint ceiling, policy, exact approval, and Rendered Contract.

## Controller return path

Consume only a `program-execution-controller.handoff-receipt.v2` bound to the active Program Lock digest. Reconcile its tasks, gates, decisions, Unknowns, approvals, residual risks, and evidence references. The receipt may recommend a verdict; only the program owner may accept a terminal Program Verdict or issue a superseding Blueprint.
