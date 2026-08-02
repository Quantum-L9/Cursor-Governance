# Alignment Report

## Canonical ownership

- Blueprint owns definitions.
- Controller owns runtime observations and transitions.
- Worker owns no authority beyond an attempt claim.
- Program owner owns terminal acceptance.

## Eliminated ambiguities

- `target` -> `target_id` plus `EXECUTION_TARGETS.yaml`.
- task `status` -> Blueprint `definition_status`; Controller `runtime_state`.
- gate `status` -> Blueprint gate definition; Controller gate evaluation result.
- duplicate task dependency declarations -> `DEPENDENCY_GRAPH.yaml` only.
- local pass vs program completion -> `PASSED_LOCAL` vs `COMPLETED`.
- remote capability vs permission -> exact approval and adapter required.
- evidence prose vs evidence identity -> stable catalog and receipt IDs.
- waiver as omission -> explicit, expiring, scoped waiver record.
- Controller result vs final program verdict -> Handoff Receipt vs owner acceptance.

## Compatibility decision

Both siblings are versioned at `2.0.0` and require the `v2` interface. The v1 formats are intentionally not treated as silently compatible because their ambiguous fields would weaken the new guarantees.

## Additional hardening

- Admission now revalidates the immutable Program Lock automatically.
- Wave dependency semantics are executable, not documentation-only.
- Waived gates are satisfiable only through an explicit active scoped waiver.
- Handoff convergence is impossible while accepted-decision or Unknown-resolution obligations remain open.
- Shared ownership, state, authorization, evidence, error, and handoff models are machine-readable.
