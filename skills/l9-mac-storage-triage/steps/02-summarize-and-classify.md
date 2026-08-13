# Step 02 — Summarize and Classify

**Input**: diagnosis_report
**Output**: diagnosis_summary
**Skill**: None
**Kernels active**: [diagnose_first_kernel@1]

## Action

- Run `./bin/mac-storage-triage summarize`.
- Classify evidence as confirmed allocation, apparent sparse allocation, inaccessible scope, cloud-managed content, reclaimable cache, archive candidate, or Unknown.
- Separate nested totals from independent totals to prevent double counting.
- Record the largest confirmed branches and unresolved accounting gaps.
- Do not recommend write actions inside the summary.

## Validation

Confirm each classification points to evidence in the diagnosis report and every unresolved fact is marked Unknown.

## Failure Recovery

If directory totals are incomplete, narrow the next scan root and exclude cloud-provider temporary trees rather than rerunning a whole-disk scan.

## Handoff

Emit `handoffs/diagnosis-summary.schema.yaml`.
