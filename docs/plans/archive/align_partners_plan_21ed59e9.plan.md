---
name: Align partners plan
overview: Point Validate & Fill Gaps at the Partners-first plan and revise that file only, binding the logistics ownership split into the existing contract without adding a BRS feature or inventing test results.
todos:
  - id: bind-kernel
    content: Apply Validate & Fill Gaps to the Partners-first plan only. Confirm the logistics section is an alignment gap against the plan's own out-of-scope and write_deny contract.
    status: pending
  - id: revise-contract
    content: Fill that gap in place. Update Out of scope, write_deny, the doc-surface row, and the machine stub. Do not add a todo, a follow-on implementation, or a claimed V1-V7 result.
    status: pending
isProject: false
---

# Fill the Partners-first plan gaps

Target, and the only file to edit: [docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md](docs/campaigns/11-03-26/PLAN%20Partners%20First%20Native%20Opportunity%20Matching%20Canonical%20Revision.md).

Kernel: [.cursor-commands/kernels/Validate & Fill Gaps.md](.cursor-commands/kernels/Validate%20%26%20Fill%20Gaps.md). It extends [.cursor-commands/kernels/Validate & Repair.md](.cursor-commands/kernels/Validate%20%26%20Repair.md) and does not replace it. Do not edit either kernel. Do not write a second audit file, a zip, or a download link.

Authorized change: revise the target plan in place. No addon edits, no BRS chapter copies, no stash pop.

## Confirmed gap

The plan's public contract is the native Opportunity path, todos T02 through T10, and proofs V1 through V7, all still `not_run`. The logistics section at lines 425-436 is accurate and stays. It is not wired to the contract that Build reads:

- `## Out of scope` and the machine-stub `out_of_scope` list do not mention BRS installation or chapter moves.
- `write_deny` names four logistics model files and does not name `plasticos_logistics/business_rules/` or `plasticos_documents/business_rules/`.
- T02-T10 do not install `BRS-POS-10`.

That is an alignment gap. An unbound section can be read as in-scope work. It is not a missing feature. Validate & Fill Gaps forbids new feature families, new architecture layers, and invented test outcomes.

Evidence already in the tree, read only:

- [plasticos_logistics/business_rules/README.md](plasticos_logistics/business_rules/README.md) already owns `BRS-01` through `BRS-07`. Do not copy that pack again.
- [plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md](plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md) already says only Linda sends the external chase.
- [plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv](plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv) marks `BRS-POS-10` out of Documents scope. No `BRS-POS-10-*.md` exists.

`BRS-POS-09-R006` through `R012` stay recorded as Linda behavior still filed under Documents. `BRS-POS-04`, `05`, `06` through `08`, `11`, and `12` stay with their current owners. Installing those chapters is a later plan, not a gap this file is allowed to fill.

## In-place fill

Keep the logistics prose. Close the wiring gap.

- Add the same exclusions to `## Out of scope` and to the machine-stub `out_of_scope` array: installing `BRS-POS-10`, moving `BRS-POS-09-R006` through `R012`, and moving `BRS-POS-04`, `05`, `06` through `08`, `11`, and `12`.
- Add `plasticos_logistics/business_rules/` and `plasticos_documents/business_rules/` to `write_deny` in the envelope and in the machine stub.
- Add one doc-surface row: this plan records the ownership split. T10 still only appends the native Opportunity correction to `AGENTS.md`.
- Leave `## Follow-on milestone` inactive. Do not add a T11 todo. A BRS install would be a new feature family.

Do not change T02-T10, the schema ledger, or the V1-V7 commands. Do not mark any of V1-V7 as passed. Do not rewrite the baseline SHA. After the edit, re-read the file and confirm the exclusions match in the prose and the machine stub, and that every proof status is still `not_run`.

Unknown, left as Unknown: this file is untracked on `fix/documents-loop-query-batch`, while probe P0 still names worktree `7d23e632` containing Staging `4a6af0b`. Execution must reverify that probe. This fill does not claim that probe passed.
