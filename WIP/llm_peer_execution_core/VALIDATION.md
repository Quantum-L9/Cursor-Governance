# Validation

## Exact v3 pack state

Performed against the blocker-sealed v3 source tree bound to:

`Quantum-L9/Cursor-Governance@0fbd477e507d33ee52f2a87c2d9eb77c15b6a492`

- pack inventory: 124 files total, with 123 files tracked by the self-excluded manifest;
- `scripts/validate_pack.py`: 692 checks PASS, 0 errors;
- `scripts/test_blocker_repairs.py`: 7/7 PASS;
- Python source is AST-parseable through pack validation and has no lines over the
  pack's 100-character Python gate;
- JSON/YAML/schema and manifest integrity checks PASS;
- no `__pycache__`, `.pyc`, or `.pyo` artifacts are permitted in the delivered pack;
- no remote mutation was performed.

## Blocker coverage

The blocker regression suite covers only the five authorized repair areas:

1. Peer Execution import ownership after the declared common-module migration.
2. Controller-owned abort/retry recovery requests after admitted failures.
3. Atomic isolated-worktree pack staging and failed-apply rollback.
4. Durable Attempt Receipt persistence before successful collect lifecycle evidence.
5. Thin-driver conformance for every routable registry adapter kind.

## Not claimed in this build environment

A complete pinned `Cursor-Governance` checkout is not available in this container.
Therefore this pack does not claim that the full post-apply repository suite,
`make pr`, live Claude/Cursor probes, or environment-dependent provider execution
has passed here.

`scripts/validate_applied_repo.py` remains the required post-apply repository gate
on an exact clean clone. Missing Ruff remains SKIPPED per operator instruction and
is not represented as PASS.
