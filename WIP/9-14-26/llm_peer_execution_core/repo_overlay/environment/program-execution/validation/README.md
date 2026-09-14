# Program Execution validation evidence

Validation evidence is revision-bound. The pre-Peer-Execution validation ledger
is preserved under `history/` during migration and MUST NOT be used as proof for
the new architecture.

Current merge evidence must be produced from the applied worktree by the live
validation gates, including thin-provider conformance, Program Execution
conformance, peer-binding validation, autonomy-contract validation, manifest
integrity, and `git diff --check`.

The PR application pack provides `scripts/validate_applied_repo.py` to run this
set without remote mutation. Live peer capability probes remain environment
dependent and must be recorded separately from structural conformance.
