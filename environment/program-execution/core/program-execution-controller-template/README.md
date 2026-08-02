# Program Execution Controller Template

The Program Execution Controller is the runtime sibling of the Program Execution Blueprint. It imports an accepted Blueprint into an immutable Program Lock, projects Task Cards into runtime tasks, binds executable work to exact repository state, constrains workers, independently verifies attempts, preserves failures, and exports a Handoff Receipt.

## What it owns

- Program Lock and source digests;
- repository and environment reconciliation;
- runtime task state;
- leases, worktrees, Source Contracts, and Rendered Contracts;
- attempt, gate-evaluation, verification, approval, recovery, and handoff receipts;
- append-only event history.

It does not own target-state meaning, responsibility assignment, task definition, authorization ceilings, gate definitions, or final program acceptance.

## Quick start

1. Instantiate the Controller.
2. Bootstrap from an instantiated v2 Blueprint.
3. Reconcile exact targets.
4. Resolve Blueprint blockers and set evidence-backed gate evaluations.
5. Draft and register a Source Contract that is a strict subset of the Task Card ceiling.
6. Claim, prepare, render, execute, record, and verify.
7. Export a Handoff Receipt for program-owner acceptance.

See `RUNBOOK.md` for commands and `../shared/INTERFACE_CONTRACT.md` when using the paired distribution.
