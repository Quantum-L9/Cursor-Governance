---
name: Clear five OLS errors
overview: 'Clear the five Problems-panel errors with two edits on feat/odools-66-ownership:
  drop the duplicate constraint decorator from the transaction stub, and move the
  semantic-kernel collision tests onto the addon that owns those models.'
todos:
- id: drop-decorator
  content: Remove the commission_override_pct decorator from the transaction stub,
    bump plasticos_transaction to 19.0.2.3.49, and revise TD-CONSTRAINT-001.
  status: completed
- id: move-collision-tests
  content: Move TestCrmSyncSemanticKernelCollision plus a local harness into plasticos_semantic_kernel
    tests, depend on plasticos_crm_sync, bump kernel to 19.0.1.0.4.
  status: completed
- id: prove-panel
  content: Run ruff, circular-deps, wiring, the profit-snapshot pytest, and make odools-diagnostics.
    Do not publish.
  status: completed
isProject: false
built: true
status: built
---

# Clear the five OdooLS panel errors

Architecture is already settled. No new addon. The field check already lives on the commission inherit. The three models already live in `plasticos_semantic_kernel`. This plan only moves the references OdooLS can see.

Branch stays `feat/odools-66-ownership`. Do not publish. `make pr` would also ship the earlier ownership commit, which is still unproven at runtime.

Out of scope: the four `gate_config.py` OLS01008 rows, the two native-test warnings, Gate SDK edits, and adding `plasticos_semantic_kernel` to any manifest.

## 1. Drop the stub decorator

In [plasticos_transaction/models/transaction.py](plasticos_transaction/models/transaction.py) at line 515, remove `@api.constrains("commission_override_pct")`. Keep `_check_override_pct_range` and its docstring so [tests/test_transaction_profit_snapshot.py](tests/test_transaction_profit_snapshot.py) still finds the method name.

The enforcing decorator stays at [plasticos_commission/models/transaction_commission.py](plasticos_commission/models/transaction_commission.py) lines 87–94. Do not redeclare `commission_override_pct` on `plasticos.transaction`.

Bump [plasticos_transaction/__manifest__.py](plasticos_transaction/__manifest__.py) from `19.0.2.3.48` to `19.0.2.3.49`.

Revise the `TD-CONSTRAINT-001` object in [docs/campaigns/odoo_tech_debt/OPEN_REGISTER.json](docs/campaigns/odoo_tech_debt/OPEN_REGISTER.json). The `do_not` line currently says not to drop the decorator. Record that the decorator lives only on the commission override, the undecorated stub method remains, and the field is still not redeclared on `plasticos.transaction`.

## 2. Move the collision class

`TestCrmSyncSemanticKernelCollision` in [plasticos_crm_sync/tests/test_orchestrator_upsert.py](plasticos_crm_sync/tests/test_orchestrator_upsert.py) (line 2242) is the only class that names `plasticos.material.observation`, `plasticos.material.specification`, and `plasticos.supply.opportunity`. Those models are defined under `plasticos_semantic_kernel/models/`.

Add `plasticos_crm_sync` to [plasticos_semantic_kernel/__manifest__.py](plasticos_semantic_kernel/__manifest__.py) `depends`, after the existing PlasticOS entries. Do not add `plasticos_semantic_kernel` to `plasticos_crm_sync`. Kernel stays optional. `plasticos_crm_sync` does not depend on the kernel or on `plasticos_intake`, so this edge does not cycle. `plasticos.transaction` inside the second test is already accepted on `plasticos_crm_sync` through `plasticos_security_base` → `plasticos_transaction`; the new edge keeps that path.

Bump the kernel manifest from `19.0.1.0.3` to `19.0.1.0.4`. No bump for `plasticos_crm_sync` (test removal only).

New file `plasticos_semantic_kernel/tests/test_crm_sync_collision.py`. Copy the two test methods and the tag `post_install`, `-at_install`, `-standard`, `crm_sync_semantic_kernel`. Copy the small harness those methods call, from production imports, not from the 2,300-line test module:

- `CanonicalLead` from `plasticos_crm_sync.adapters.base`
- `SyncOrchestrator` and `_new_outcomes` from `plasticos_crm_sync.services.orchestrator`
- `OWNER_LOGIN_BY_SOURCE` from `plasticos_crm_sync.services.owner_crosswalk`
- `setUpClass` connection create, `setUp` salesperson mapping, `_lead`, and `_facility` (the body of `CrmSyncOrchestratorCase`, lines 34–87)

Importing `test_orchestrator_upsert.py` would load `TestCrmSyncOrchestrator` as well. Do not import it.

Wire the new module from [plasticos_semantic_kernel/tests/__init__.py](plasticos_semantic_kernel/tests/__init__.py). Delete the class from the crm_sync file. Update the run comment to `-i plasticos_semantic_kernel --test-tags crm_sync_semantic_kernel`.

## Proof

- `ruff check` and `ruff format` on the touched Python, using `.venv/bin/ruff` (0.16.0).
- `python3 ci/check_circular_deps.py` and `python3 scripts/check_module_wiring.py`.
- `python3 -m pytest tests/test_transaction_profit_snapshot.py`.
- `make odools-diagnostics`.

Done when the dump no longer contains OLS03014 on `transaction.py` or OLS03001 on `test_orchestrator_upsert.py`, and the new kernel test file does not add a replacement OLS03001. The Gate keyword errors and the other warnings stay.

## Build evidence (auto)

- detected_at: `2026-10-30T19:00:22Z`
- conversation_id: `06fa6ff5-82a5-4b90-bd44-c56e3e13c041`
- generation_id: `8e41dba5-2d83-49a2-b0cd-96ad6bcff811`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/06fa6ff5-82a5-4b90-bd44-c56e3e13c041/06fa6ff5-82a5-4b90-bd44-c56e3e13c041.jsonl`
- todos at build time:
- `drop-decorator`: completed
- `move-collision-tests`: completed
- `prove-panel`: completed
