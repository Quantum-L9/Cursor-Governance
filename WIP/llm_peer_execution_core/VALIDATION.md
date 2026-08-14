# Validation

## Exact v3 pack state

Observed 2026-08-14 on `feat/kernel-pack-new-branch-default` after L9 harden
(`.DS_Store` removed; inventory walker excludes `.DS_Store` / `._*`;
`CanonicalExecutionRequest` / `CanonicalProviderResult` are pydantic v2;
subprocess calls have timeouts; `structlog` is used for library diagnostics).

Bound pack baseline SHA (pack metadata, not this branch HEAD):

`Quantum-L9/Cursor-Governance@0fbd477e507d33ee52f2a87c2d9eb77c15b6a492`

- pack inventory: 123 files tracked by the self-excluded manifest; `.DS_Store` excluded;
- `scripts/validate_pack.py`: 692 checks PASS, 0 errors (re-run 2026-08-14);
- `scripts/test_blocker_repairs.py`: 7/7 PASS (invoked from validate_pack);
- Python source is AST-parseable through pack validation and has no lines over the
  pack's 100-character Python gate;
- JSON/YAML/schema and manifest integrity checks PASS;
- no `__pycache__`, `.pyc`, `.pyo`, or `.DS_Store` artifacts are permitted in the
  delivered inventory;
- no remote mutation was performed.

## Blocker coverage

The blocker regression suite covers only the five authorized repair areas:

1. Peer Execution import ownership after the declared common-module migration.
2. Controller-owned abort/retry recovery requests after admitted failures.
3. Atomic isolated-worktree pack staging and failed-apply rollback.
4. Durable Attempt Receipt persistence before successful collect lifecycle evidence.
5. Thin-driver conformance for every routable registry adapter kind.

## Not claimed in this build environment

`scripts/validate_applied_repo.py` remains the required post-apply repository gate
on the landing branch after the governed porter. Missing Ruff remains SKIPPED per
operator instruction and is not represented as PASS.
