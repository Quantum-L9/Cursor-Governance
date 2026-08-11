# Deliverable — l9-devpack-compiler (out of scope)

The intent-compiler contract's mutable target `l9-devpack-compiler` is **not
reachable** in the session that produced this registration, so the compiler
cannot be implemented or validated in place. `UNK-001` blocks the work until the
repository is attached and bound to an exact base SHA.

This directory captures the repo-aligned build plan so the work can be applied
manually, or executed automatically once the repository is attached.

| File | Purpose |
|---|---|
| `IMPLEMENTATION_DESIGN.md` | Component build plan (schemas, resolver, synthesizer, validator adapter, CLI, tests) mapped to the contract's §4–§19, with the §21 prohibited actions and §20 stop conditions preserved. |

## To execute in place (when the repo is reachable)

1. Attach `l9-devpack-compiler` to the session / Controller.
2. Inspect the repo first (contract §17): locate existing Program Execution
   contracts, DPK integration points, schema conventions, validators, policy
   mechanisms, CLI entrypoints, tests/fixtures — **reuse**, do not fork.
3. Bind the target base SHA (resolving `UNK-001`).
4. Implement under `quantum-l9.safe-autonomy.v1` (local_write only; no
   commit/push/PR/merge/release/deploy).
5. Run the §18 test matrix, §19 Quality Gates A–F, and §23 independent
   verification; validate generated Blueprints with the **official** validator.

No mutation of `l9-devpack-compiler` is performed or authorized here.
