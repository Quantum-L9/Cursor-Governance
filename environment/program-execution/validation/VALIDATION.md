# Program Execution Adapter Layer Validation

## Verdict

- Module status: **PASS**
- Overall status: **BLOCKED_ON_VALIDATION**
- Base: `Quantum-L9/Cursor-Governance@3c9ba5c675b91e5d1d2b20d777ff14fcb669a48c`
- Registered adapters: **11**
- Dynamic conformance tests: **57 passed**
- Standard discovery tests: **35 passed**

## Proven

- The sealed core validates and is excluded from the adapter manifest.
- Adapter descriptors, lifecycle receipts, and terminal receipts validate.
- Authority widening, self-verification, stale locks, forged receipts, missing
  deployment targets, credential leakage, and merge escalation are rejected.
- Root autonomy, Claude bounded autonomy, agent identity, Graphiti, and the
  generated-data pipeline are reused rather than duplicated.
- Python compilation writes bytecode outside the source tree.
- The source tree contains no cache, bytecode, SQLite, or runtime debris.
- Repository alignment is restricted to the five permitted files and is
  idempotent.

## Unproven or blocked

- The repository-pinned Ruff binary is not available in this container.
- A full Cursor-Governance checkout is unavailable, so `make pr` cannot run.
- GitHub branch creation returned `403 Resource not accessible by integration`.
- The five permitted external edits are therefore packaged as an idempotent
  installer rather than applied to a published branch.

## Publication gate

Apply the module to the current authenticated Cursor-Governance worktree, run:

```bash
python3 -B environment/program-execution/scripts/apply_repository_alignment.py .
make program-execution-core-validate
make program-execution-adapters
make program-execution-conformance
make program-execution-probe
make pr
```

Only after all commands pass may the prepared commit be pushed and a draft PR
opened. Merge remains human-only.
