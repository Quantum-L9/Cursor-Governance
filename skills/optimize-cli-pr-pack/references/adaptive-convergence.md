# Adaptive Convergence

Keep the absolute ceiling of three cycles, but do not run a fixed ritual.

For each cycle:

1. Reconcile remote or sandbox state and the prior ledger.
2. Re-run the router only when evidence, risk, ownership, or available capabilities changed.
3. Select the smallest unresolved proof obligation with the highest decision value.
4. Run one bounded implementation, probe, or validation action.
5. Update claims, options, unknowns, proof status, and convergence evidence.
6. Stop immediately when all active obligations are satisfied or a material blocker is proven.

Cycle three is the terminal closure cycle. It may package `PR_READY`, `READY_WITH_HUMAN_STEP`, or `BLOCKED`. A fourth cycle is forbidden.
