# Verification and Receipts

The worker reports an Attempt Receipt. The Controller independently verifies:

- Program Lock, ledger, lease, contract, and base SHA;
- exact equality between declared and observed changed files;
- writable-path scope and symlink safety;
- independent rerun of every validation command;
- residual Unknowns and required evidence;
- candidate revision and provenance.

`PASSED_LOCAL` means the local attempt satisfies the exact Rendered Contract. It is not a remote publication, deployment, migration, or final program verdict.
