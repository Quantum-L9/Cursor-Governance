# Controller Architecture

## Runtime components

- **Program Lock**: immutable normalized import of an exact Blueprint revision.
- **State DB**: mutable runtime projections for tasks, targets, decisions, Unknowns, gates, leases, attempts, approvals, and waivers.
- **Event Ledger**: append-only hash-chained transition record.
- **Contract Store**: operator-reviewed Source Contracts and exact-state Rendered Contracts.
- **Receipt Store**: attempts, independent verification, gate evaluations, approvals, recovery, and handoff receipts.
- **Worker Adapter Boundary**: host-neutral dispatch surface.

## Dependency direction

```text
Blueprint -> Program Lock -> Runtime Projection -> Source Contract -> Rendered Contract
                                                        -> Worker Attempt
                                                        -> Independent Verification
                                                        -> Task/Gate Runtime State
                                                        -> Handoff Receipt
```

No reverse dependency may mutate Blueprint files. Runtime evidence returns through a Handoff Receipt.

## State transition law

All task transitions are validated against `references/STATE_MACHINE.md` and appended to the ledger. An invalid transition is rejected rather than normalized silently.
