# compile_brief-admissible INTENT — PE EIE slice (inference + isolation)

Coverage cap: inference routing and tenant/Alembic isolation only (≤30% of the
EIE / Repair Order corpus). Execute remaining PE loop work via `/gmp` on
`docs/plans/pe_loop_compiled_8-28-26.plan.md`. Do not `make campaign`.
Do not admit a Program Lock from this memo.

## Intent

1. Keep model-level inference routing deferred (ADR-0020). Adapter routing stays
   `EXECUTION_ROUTING_POLICY` + capability probes. `tightly_scoped_mechanical`
   prefers `codex-cloud` and fail-closes while that adapter is dormant.
2. Isolation: campaign execute of `program-execution.intent.v1` stays refused
   until a separate W8+ plan after v3 control-plane reconstruction. Compiler
   ingress is the landed path. Tenant/Alembic schema mutation is out of this
   slice.

## Dual artifact

This memo is the compile_brief input. The executable packet remains
`docs/plans/pe_loop_compiled_8-28-26.plan.md` (`compiled: true`, `execute_via: gmp`).
