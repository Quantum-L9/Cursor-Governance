# Validation

Run from the distribution root:

```bash
python scripts/validate_pair.py . --mode template
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/run_negative_tests.py .
```

The validator checks both sibling manifests, JSON Schemas, Python compilation, canonical contract versions, cross-file references, ownership boundaries, forbidden legacy fields, package debris, and pair compatibility.

A passing template validation proves structural and contract coherence. It does not prove any instantiated program, repository, deployment, migration, or production behavior.

## Git-worktree test isolation

Run each Controller lifecycle test file in a fresh process. This prevents one intentionally failed Git-worktree fixture from influencing another fixture through repository housekeeping. `scripts/run_negative_tests.py` follows this rule.

## Final result

`APPROVED_EXECUTION_READY` for the reusable template pair and local Controller reference implementation. The validation evidence is under `validation/`. Production program behavior remains unproven until a completed Blueprint is instantiated and executed against its exact targets.
