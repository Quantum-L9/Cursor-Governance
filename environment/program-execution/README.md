# Program Execution

This subsystem installs the sealed Program Execution System under `core/` and
keeps host-specific execution behind replaceable adapters.

- `core/` owns program truth, Program Locks, task readiness, canonical receipts,
  and independent convergence evaluation.
- `adapters/` translates exact Controller contracts into host operations.
- `integrations/` reuses existing Cursor-Governance runtimes without copying them.
- `conformance/` proves authority narrowing, digest binding, honest capability
  reporting, cancellation truthfulness, and separation of duties.
- `registry/` controls deterministic routing, concurrency, health, and failover.

Mutable runtime belongs under `$HOME/.l9/programs/` and
`$HOME/.l9/program-worktrees/`, never in this source tree.

Each execution adapter is the Controller-side peer of a surface adapter in
`environment/agents/adapters/`. The identity ↔ execution cross-link and the
universal peer-execution contract are documented in
`environment/agents/PEER_EXECUTION.md` and validated by
`make peer-execution-conformance` / `make peer-execution-probe`.
