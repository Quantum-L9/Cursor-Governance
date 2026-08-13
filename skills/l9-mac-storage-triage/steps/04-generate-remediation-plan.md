# Step 04 — Generate Remediation Plan

**Input**: triage_configuration
**Output**: remediation_plan
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Run `./bin/mac-storage-triage plan`.
- Generate an exact action list from `APPROVED_ACTIONS`.
- Show each path, detected state, intended change, guard conditions, and verification method.
- Hash the plan and store the digest in playbook state.
- Review the plan before enabling execution approval.

## Validation

Confirm the plan includes no action absent from `APPROVED_ACTIONS` and no required value remains `UNKNOWN`.

## Failure Recovery

If the plan reveals an unsafe or unintended action, edit `.env`, rerun validation, and regenerate the plan. Never edit the generated plan as a substitute for configuration.

## Handoff

Emit `handoffs/remediation-plan.schema.yaml`.
