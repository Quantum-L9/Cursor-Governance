# Runtime Task State Machine

```text
BLOCKED <-> ELIGIBLE -> LEASED -> PREPARED -> CONTRACTED -> EXECUTING -> SUBMITTED -> VERIFYING
                                                                               |          |
                                                                               |          +-> PASSED_LOCAL
                                                                               |          +-> FAILED
                                                                               |          +-> STALE
                                                                               +-> STALE

PASSED_LOCAL -> COMPLETED only when every Task Card completion gate passes and all required action receipts exist.
Any active state -> CANCELLED only through accepted program authority.
FAILED -> EXECUTING or SUBMITTED to retry the same lease, contract, and worktree once the cause is fixed.
FAILED or STALE -> ELIGIBLE when a new lease and a fresh contract are required.
```

Definition states, evidence results, and program verdicts are not runtime task states.
