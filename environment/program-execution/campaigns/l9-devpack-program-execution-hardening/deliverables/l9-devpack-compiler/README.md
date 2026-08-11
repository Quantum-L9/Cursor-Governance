# Deliverable — l9-devpack-compiler (out of scope)

The Program's mutable target `repository_id=l9-devpack-compiler` is **not
reachable** in the session that produced this registration, so its remediation
could not be applied or pushed in place. `UNK-001` blocks `TASK-002`–`TASK-007`
until the repository is attached and bound to an exact base SHA.

This directory captures the **design-time authority** for that work so it can be
applied manually, or re-executed automatically once the repository is attached
and the Program advances past `GATE-001`.

| File | Purpose |
|---|---|
| `REMEDIATION_DESIGN.md` | Per-task (TASK-002…TASK-007) change design mapped to concrete `l9-devpack-compiler` files, acceptance, and negative cases. |

## To execute in place (when the repo is reachable)

1. Attach `l9-devpack-compiler` to the session / Controller.
2. Re-run the reproduction sequence in `../../VALIDATION_EVIDENCE.md` to
   materialize the Blueprint + Controller pair under the external program root.
3. Bind the target: record its exact base SHA and clean working tree (produces
   `EVID-005`), resolving `UNK-001` and passing `GATE-001`.
4. Admit `W1` and apply `REMEDIATION_DESIGN.md` task-by-task, gating each wave on
   its convergence gate, keeping every change reversible and repo-local.

No commit/push/PR/merge/release/deploy against `l9-devpack-compiler` is
authorized by the Blueprint; those remain owner-approved actions.
