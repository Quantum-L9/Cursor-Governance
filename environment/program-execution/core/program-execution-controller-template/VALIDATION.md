# Controller Validation

```bash
python scripts/validate_controller.py . --mode template
python -m unittest discover -s scripts/tests -p 'test_*.py' -v
python scripts/run_negative_tests.py
```

Runtime validation:

```bash
python scripts/pec.py validate --workspace /path/to/runtime
```

Validation covers structure, schemas, manifests, Program Lock integrity, Blueprint compatibility, state transitions, decision and Unknown blockers, authorization subset enforcement, one-writer leases, exact path scope, attempt binding, changed-file equality, validation reruns, gate receipts, recovery, handoff export, and remote-action denial.

## Runtime hostile matrix

Run each lifecycle fixture in a fresh process:

```bash
python scripts/tests/test_controller_success.py -v
python scripts/tests/test_changed_files.py -v
python scripts/tests/test_authority_inflation.py -v
python scripts/tests/test_decision_unknown.py -v
python scripts/tests/test_leases_and_approval.py -v
python scripts/tests/test_approval.py -v
python scripts/tests/test_program_lock_drift.py -v
python scripts/tests/test_wave_dependency.py -v
python scripts/tests/test_waived_gate.py -v
python scripts/tests/test_ledger_tamper.py -v
python scripts/tests/test_recovery.py -v
python scripts/tests/test_scope.py -v
python scripts/tests/test_state_transition.py -v
python scripts/tests/test_program_control.py -v
```

Fresh-process isolation is intentional because several fixtures create and intentionally abandon or fail Git worktrees.
