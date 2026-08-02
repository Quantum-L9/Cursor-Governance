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
FAILED or STALE -> ELIGIBLE only after the cause is resolved, the target is reconciled, and a fresh contract is rendered.
```

Definition states, evidence results, and program verdicts are not runtime task states.
