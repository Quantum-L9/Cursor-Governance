# Step 05 — Execute Approved Actions

**Input**: remediation_plan
**Output**: execution_receipt
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Set the exact execution confirmation value in `.env` after reviewing the plan.
- Run `./bin/mac-storage-triage apply`.
- Execute only action modules named in the approved plan.
- Write a separate receipt for every attempted action.
- Stop on the first blocking failure.

## Validation

Confirm the current plan hash matches the approved plan hash and every dispatched module reports success or a concrete failure.

## Failure Recovery

If an action fails, preserve its logs and receipts. Do not continue with dependent deletion or reindex operations until the failed prerequisite is resolved.

## Handoff

Emit `handoffs/execution-receipt.schema.yaml`.
