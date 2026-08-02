# Controller Runbook

## 1. Validate and instantiate

```bash
python scripts/validate_controller.py . --mode template
python scripts/instantiate.py --name "Program Controller" --id program-controller --owner "Owner" --date 2026-08-01T00:00:00Z --target ../program-controller
```

## 2. Bootstrap

```bash
python scripts/pec.py bootstrap --workspace ../runtime --blueprint ../program-blueprint
python scripts/pec.py validate --workspace ../runtime
```

## 3. Reconcile repositories

```bash
python scripts/pec.py reconcile --workspace ../runtime --repository repo-a=/path/to/repo
```

The mapping key must match `EXECUTION_TARGETS.yaml.repository_id`.

## 4. Inspect readiness

```bash
python scripts/pec.py status --workspace ../runtime
python scripts/pec.py next --workspace ../runtime
```

## 5. Resolve runtime blockers

```bash
python scripts/pec.py set-decision DEC-001 accepted --workspace ../runtime --evidence-id EVID-010 --actor owner
python scripts/pec.py set-unknown UNK-001 resolved --workspace ../runtime --evidence-id EVID-011 --actor owner
python scripts/pec.py evaluate-gate GATE-001 PASS --workspace ../runtime --evidence-id EVID-012 --method inspection --actor verifier
```

These commands record runtime projections and receipts. They do not rewrite Blueprint source files.

## 6. Admit exact task scope

```bash
python scripts/pec.py draft-contract TASK-002 --workspace ../runtime --output TASK-002.source-contract.json
# edit exact paths, actions, and validation obligations
python scripts/pec.py register-contract TASK-002 --workspace ../runtime --file TASK-002.source-contract.json --actor operator
```

## 7. Execute

```bash
python scripts/pec.py claim TASK-002 --workspace ../runtime --holder worker-01
python scripts/pec.py prepare TASK-002 --workspace ../runtime
python scripts/pec.py render-contract TASK-002 --workspace ../runtime
```

Give only the Rendered Contract, Worker Brief, and worktree to the worker.

## 8. Record and verify

```bash
python scripts/pec.py record-attempt TASK-002 --workspace ../runtime --receipt attempt.json
python scripts/pec.py verify TASK-002 --workspace ../runtime
```

## 9. Recovery and handoff

```bash
python scripts/pec.py recover --workspace ../runtime --actor operator
python scripts/pec.py export-handoff --workspace ../runtime --actor controller --output handoff.json
```

A Handoff Receipt recommends a program verdict but never declares it authoritative.

## Admission integrity

Every `next` and `claim` operation rechecks the Program Lock against the imported Blueprint source digests. A changed Blueprint source blocks admission with `program_lock_stale_or_invalid` until a new workspace or explicit relock workflow is created.

Wave admission also verifies all declared predecessor-wave tasks are `COMPLETED` and predecessor exit gates are satisfied. Runtime scheduling may narrow concurrency but may not bypass Blueprint wave order.
