# Recovery

Recovery preserves evidence before changing runtime ownership. It never erases an attempt to make the task appear clean.

Required artifact set:

- lease and task metadata;
- Program Lock, Source Contract, and Rendered Contract digests;
- base SHA, current HEAD, status, patch, and untracked file inventory;
- attempt and validation receipts if present;
- actor, reason, and timestamp.

After preservation, the task becomes `STALE`, the lease is released, and the target must be reconciled before a new claim.
