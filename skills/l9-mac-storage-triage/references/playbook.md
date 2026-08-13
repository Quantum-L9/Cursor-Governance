<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: playbook_contract
tags: [macos, storage, playbook]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# mac-storage-triage playbook

Typed playbook contract preserved from the source pack. Control plane is `SKILL.md`; modes are in `references/modes.md`.

```yaml
id: mac-storage-triage
version: 1.1.0
domain: macos_storage_operations
use_case: Diagnose and remediate macOS disk-storage pressure through a read-first, variable-driven workflow.
```

## Overview

Evidence collection, operator configuration, planning, execution, and verification stay separated. Shell writes remain blocked until a diagnosis receipt exists, required environment values are concrete, and an approved plan has been generated.

Repair/autonomy auto-select only stale caches, unused Docker artifacts, and Trash. Mail, rclone offload, and verified-source delete remain extra HITL.

## Prerequisites

- macOS with Bash, `diskutil`, `df`, `tmutil`, and standard command-line utilities.
- Optional `ncdu` for reusable directory scans.
- Optional `rclone` for direct cloud offload without a second local copy.
- Optional Docker / Homebrew / conda / npm for noise inventory.
- Full Disk Access only when required for the inspected locations.

## Step Manifest

| Step | File | Input | Output |
|---|---|---|---|
| 01 | steps/01-diagnose-current-state.md | triage_request | diagnosis_report |
| 02 | steps/02-summarize-and-classify.md | diagnosis_report | diagnosis_summary |
| 03 | steps/03-populate-and-validate-env.md | diagnosis_summary | triage_configuration |
| 04 | steps/04-generate-remediation-plan.md | triage_configuration | remediation_plan |
| 05 | steps/05-execute-approved-actions.md | remediation_plan | execution_receipt |
| 06 | steps/06-verify-and-close.md | execution_receipt | verification_report |

Mode wrappers: `bin/mac-storage-triage run {diagnose|repair|autonomy}`.

## Success Criteria

- A timestamped read-only diagnosis exists.
- Repair/autonomy `APPROVED_ACTIONS` contain only allowlisted noise actions unless the operator edited `.env`.
- Every write action produces a receipt.
- Verification reconciles free space and action outcomes.
- Unknown or unsafe state causes a fail-closed stop.
