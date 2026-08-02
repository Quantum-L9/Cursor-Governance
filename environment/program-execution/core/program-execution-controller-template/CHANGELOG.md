# Changelog

## 2.0.0

See the distribution root `CHANGELOG.md` for the aligned system changes.

## 2.0.0 alignment hardening

- Reject task admission when the imported Blueprint source digest drifts.
- Enforce predecessor-wave task completion and predecessor exit-gate satisfaction.
- Validate required task evidence before admission.
- Treat `NOT_APPLICABLE_WITH_REASON` as satisfying only when backed by an active, scoped, evidence-valid waiver.
- Prevent convergence recommendations while decisions remain pending or Unknowns remain open.
- Correct CLI error handling for rejected Source Contracts.
- Permit the legal `ELIGIBLE -> COMPLETED` transition for program-control tasks.
- Add isolated hostile tests for authority inflation, exact changed files, leases, T4 approval, ledger tampering, recovery, wave order, source drift, and waivers.
