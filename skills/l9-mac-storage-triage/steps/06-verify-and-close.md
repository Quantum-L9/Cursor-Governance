# Step 06 — Verify and Close

**Input**: execution_receipt
**Output**: verification_report
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Run `./bin/mac-storage-triage verify`.
- Compare before-and-after free space.
- Verify removed paths are absent, offloaded content passed remote checks, and exclusion markers exist where supported.
- Record manual Finder or Spotlight checks when GUI action was required.
- Leave unresolved outcomes as Unknown.

## Validation

Confirm verification evidence exists for every executed action and no success claim relies only on command exit status when state can be inspected directly.

## Failure Recovery

If verification is incomplete, preserve the playbook state and repeat only the verification needed for the affected action.

## Handoff

Emit `handoffs/verification-report.schema.yaml`.
