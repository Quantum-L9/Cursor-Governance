# Verification and Receipts

The worker reports an Attempt Receipt. The Controller independently verifies:

- Program Lock, ledger, lease, contract, and base SHA;
- exact equality between declared and observed changed files;
- writable-path scope and symlink safety;
- independent rerun of every validation command;
- residual Unknowns and required evidence;
- candidate revision and provenance;
- local `make pr` / `make pr-check` PASS evidence before push or PR admission;
- Phase 0 completeness when `program_deploying` is true.

`PASSED_LOCAL` means the local attempt satisfies the exact Rendered Contract. It is not a remote publication, deployment, migration, or final program verdict.

**Ordering:** local Core-CI-mirror gate first; remote CI is confirmation; PR remediation loops are exceptional after local PASS (or documented remote-only failure class).
