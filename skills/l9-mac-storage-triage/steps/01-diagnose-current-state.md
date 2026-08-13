# Step 01 — Diagnose Current State

**Input**: triage_request
**Output**: diagnosis_report
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Run `./bin/mac-storage-triage diagnose` before any planning or cleanup action.
- Collect APFS, free-space, snapshot, Spotlight-state, cloud-provider, Mail, Docker, Conda, and tool-availability evidence.
- Keep the default diagnosis non-recursive.
- Run `./bin/mac-storage-triage scan` only when `ncdu` is installed and targeted directory evidence is required.
- Save every result under a timestamped report directory and create the diagnosis completion receipt.

## Validation

Confirm the report directory contains `diagnosis.env`, `diagnosis.md`, `df.txt`, and `diagnosis.complete`.

## Failure Recovery

If a read command stalls, the built-in timeout records the failure and continues. If the Mac becomes unstable, stop and free working space before further diagnosis.

## Handoff

Emit `handoffs/diagnosis-report.schema.yaml`.
