# Step 03 — Populate and Validate Environment

**Input**: diagnosis_summary
**Output**: triage_configuration
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Run `./bin/mac-storage-triage init-env` to create `.env` from detected machine facts.
- Edit `.env` and the referenced configuration files.
- Replace only the action-specific `UNKNOWN` values supported by diagnosis evidence.
- Select approved actions explicitly.
- Run `./bin/mac-storage-triage validate`.

## Validation

The validator must confirm diagnosis existence, environment syntax, path boundaries, action prerequisites, and explicit approval fields.

## Failure Recovery

If validation fails, correct only the reported values. Do not bypass the validator or infer a missing path, cloud remote, mailbox status, or approval.

## Handoff

Emit `handoffs/triage-configuration.schema.yaml`.
