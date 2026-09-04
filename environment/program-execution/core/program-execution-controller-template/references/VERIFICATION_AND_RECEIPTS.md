# Verification and Receipts

The worker reports an Attempt Receipt. The Controller independently verifies:

- Program Lock, ledger, lease, contract, and base SHA;
- exact equality between declared and observed changed files;
- writable-path scope and symlink safety;
- independent rerun of every validation command;
- residual Unknowns and required evidence;
- candidate revision and provenance.

`PASSED_LOCAL` means the local attempt satisfies the exact Rendered Contract. It is not a remote publication, deployment, migration, or final program verdict.

## Evidence is bound to its claim

Validity is not relevance. `pec evaluate-gate ... PASS` requires every evidence
id the gate definition declares in `required_evidence_ids`, at least one item
that `supports` a task in the gate's `scope.task_ids`, and — for `execution`
and `validation` class gates — the Controller's own verification evidence
(`method: independent_controller_verification`, `result: PASS`) for an in-scope
task; catalog or planning evidence cannot close an execution gate.
`pec complete` requires the current attempt's verification evidence id
(`EVID-RUNTIME-<task>-<attempt>`), still supporting the task and still carrying
the receipt's digest.

## The integrated candidate is the verified state

The verification receipt records `observed_file_digests` (sha256 per observed
path, or `absent`/`directory`/`symlink`). Under a campaign integration branch
`_integrate_candidate` refuses unless the candidate's `base..tip` diff names
exactly the receipt's `observed_changed_files`, the task worktree holds no
uncommitted change, and every committed blob carries the digest the verdict
recorded. A mismatch leaves the task PASSED_LOCAL with its candidate preserved.
`export-handoff` only recommends; `pec close` accepts a terminal verdict and
refuses a success verdict the Controller's own recommendation (pending
decisions, open Unknowns, a halt, a broken ledger) does not support. Every
Program-state transition first verifies the ledger chain.
