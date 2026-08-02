# Security

## Trust boundaries

- Blueprint definitions are trusted only after validation and Program Lock creation.
- Workers are untrusted executors.
- Worker receipts are claims, not proof.
- Repository state is trusted only after exact reconciliation and re-check.
- Connector, token, shell, or API availability is capability, never authorization.

## Required protections

- Reject absolute, traversal, `.git`, controller-internal, device, and ambiguous glob paths.
- Reject changed symlinks and scope escapes.
- Bind contracts and approvals to task, target, base SHA, Program Lock digest, action set, actor, and expiry.
- Enforce one active writer lease per repository.
- Compare worker-declared changed files to Controller-observed changed files exactly.
- Rerun declared validation independently.
- Preserve attempt evidence before recovery.
- Keep remote credentials outside worker environments by default.
- Hash-chain every state-changing event.
