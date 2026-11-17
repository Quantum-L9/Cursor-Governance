---
name: Prove Gate 6 on the newest 10% of worksheets
overview: "The rehearsal Gate 6 import uses the existing ERP_LIMIT=10% cap, and the Gate 6 judge treats a faithful import of that slice as a pass only when the importer's own census shows the cap excluded the rest. Partners, addresses, contacts, roles, and salespersons still load in full. Worksheets are the newest 10%, plus pinned worksheet 58699 when the source contains it. A pass must not claim every wo..."
todos:
  - id: T1
    content: "Pass ERP_LIMIT=10% as one make assignment on the Gate 6 make import-erp invocation, and record --limit 10% on check-erp. Do not call make import-erp-test. Leave make import-erp with no limit as the full import. Do not modify scripts/test_env.sh or Makefile; ERP_LIMIT already matches the import-erp forward allowlist and is already passed into the container. State in SPEC.md and README.md that this rehearsal imports every partner layer and the newest 10% of worksheets, plus pinned worksheet 58699 when the source contains it, and that a permitted production run still refuses the cap. The percent is not a count of every source row, and the pinned worksheet may add one number beyond the tenth."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Make the Gate 6 judge accept a faithful 10% slice only with the importer's own exclusion. When limit is 10%, census.payables_unselected.rows must be a positive integer or the result is erp-rehearsal-limit-unproven. That field is inside the nested census dict compact_census already copies; do not read the isolated full census. facts.scope must name the newest 10% plus pinned worksheet 58699 and must not say every worksheet. When limit is full, keep the current facts.scope sentence and do not require an exclusion. Any other limit, including empty, is erp-rehearsal-limit. erp-run-not-full stays for a partners-only or named-layer finished-line scope. A mapped-field mismatch inside the slice still returns erp-fidelity-discrepancy. Do not add unselected worksheets to the fidelity expected set: evaluate() walks the clone, so those worksheets are not missing comparison rows."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Update the stubbed Gate 6 success path. test_rehearsal_scripts.py must see ERP_LIMIT=10% on the make command and limit 10% on the receipt. ERP_CENSUS gains census.payables_unselected.rows greater than 0 so that success stub still passes. A 10% census with rows 0 fails erp-rehearsal-limit-unproven. A limit other than 10% or full fails erp-rehearsal-limit. A slice mismatch still fails. A partners-only log still fails erp-run-not-full. The library helper that passes limit full stays a full-book pass. Leave check_compact_acceptance.py judging the retained full snapshots."
    status: pending
    phase: execute
    depends_on: [T2]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Prove Gate 6 on the newest 10% of worksheets

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `prove_gate_6_on_the_newest_10_of_worksheets_934b2404.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| name | Prove Gate 6 on the newest 10% of worksheets |
| overview | The rehearsal Gate 6 import uses the existing ERP_LIMIT=10% cap, and the Gate 6 judge treats a faithful import of that slice as a pass only when the importer's own census shows the cap excluded the rest. Partners, addresses, contacts, roles, and salespersons still load in full. Worksheets are the newest 10%, plus pinned worksheet 58699 when the source contains it. A pass must not claim every worksheet was imported. A mapped-field mismatch inside the slice still fails. A partners-only or single-layer run still fails. The full import command and the production-permit refusal of ERP_LIMIT stay unchanged. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | workspace-operator |
| created_at | 2026-11-08T15:16:06+00:00 |
| updated_at | 2026-11-08T15:16:06+00:00 |
| depth | `standard` |
| estimate | one kit change set |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-08T15:16:06+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `fix/rehearsal-evidence-20261108` |
| commit_sha | `f74d14d52e90a50e49a4bbe5a6d4a3f31b31530e` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

The rehearsal Gate 6 import uses the existing ERP_LIMIT=10% cap, and the Gate 6 judge treats a faithful import of that slice as a pass only when the importer's own census shows the cap excluded the rest. Partners, addresses, contacts, roles, and salespersons still load in full. Worksheets are the newest 10%, plus pinned worksheet 58699 when the source contains it. A pass must not claim every worksheet was imported. A mapped-field mismatch inside the slice still fails. A partners-only or single-layer run still fails. The full import command and the production-permit refusal of ERP_LIMIT stay unchanged. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0.

### Scope in

- Gate 6 rehearsal invocation passes ERP_LIMIT=10% on make import-erp, not make import-erp-test
- The receipt records limit 10% and facts.scope names that slice
- The judge reads census.payables_unselected from the compact census the publisher already keeps
- A field mismatch inside the imported slice still fails
- Stub tests that currently require limit full, including ERP_CENSUS

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: the rehearsal import command passes ERP_LIMIT=10% as one make assignment and the Gate 6 receipt records limit 10% | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → ERP_LIMIT=10% is on the rehearsal command; a 10% census with payables_unselected.rows greater than 0 passes and does not claim every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes | `true` |
| SP-02 | V1: limit 10% passes only when census.payables_unselected.rows is greater than 0, facts.scope does not say every worksheet, a mapped-field mismatch inside the slice fails, and a partners-only or named-layer run still fails erp-run-not-full | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → ERP_LIMIT=10% is on the rehearsal command; a 10% census with payables_unselected.rows greater than 0 passes and does not claim every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes | `true` |
| SP-03 | V1: a limit other than 10% or full fails erp-rehearsal-limit, and limit full still passes with no diagnostic exclusion while facts.scope still names every worksheet | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → ERP_LIMIT=10% is on the rehearsal command; a 10% census with payables_unselected.rows greater than 0 passes and does not claim every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes | `true` |
| SP-04 | V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml | `quality_gate` | V2: `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py` → hook catalog .pre-commit-config.yaml reports pass on those files | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| source_ref | `plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind checkout fix/rehearsal-evidence-20261108 at f74d14d5; hook catalog .pre-commit-config.yaml; MEMORY_PREFETCH snapshot_digest f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2` | branch and HEAD recorded; catalog file present; prefetch conflicts=0; working tree dirty only at tests/production-rehearsal/evidence/latest | `true` |
| P1 | pre-validation (status `passed`) | `read limits.py, native_orders.selected_worksheets, import_erp_shell permit refusal, Makefile import-erp ERP_LIMIT, test_env.sh ERP_[A-Z_]+ forward, erp_slice.sh, and common.py check_erp` | ERP_LIMIT=10% is the newest tenth plus pinned worksheet 58699; a permit refuses the cap; test_env forwards ERP_LIMIT on make import-erp; the rehearsal records limit full; facts.scope always says every worksheet | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence sufficient` | depth standard and omit_gates empty | `true` |
| P3 | pre-validation (status `passed`) | `audit the plan against fidelity.evaluate, compact_census, and the census writer in run_erp_import.py` | field comparison walks the clone, so unselected worksheets are not fidelity rows; compact_census copies the nested census dict, which already holds payables_unselected; a receipt string alone cannot prove the cap | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py`
- **write_deny:** `plasticos_partner_import/erp/limits.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_partner_import/scripts/import_erp_shell.py`, `plasticos_partner_import/scripts/run_erp_import.py`, `plasticos_transaction/models/native_document_import.py`, `scripts/test_env.sh`, `Makefile`, `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/fidelity.py`, `tests/production-rehearsal/check_compact_acceptance.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q`, `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `none` |
| allowed_services | none |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- ERP_LIMIT=10% remains the newest tenth of worksheets plus pinned worksheet 58699 when present
- a production permit still refuses ERP_LIMIT
- make import-erp with no limit remains the full import
- partners, addresses, contacts, roles, and salespersons are not capped
- a partners-only or named-layer run still fails erp-run-not-full
- a mapped field discrepancy inside the imported slice still fails
- limit full remains a pass and check_compact_acceptance.py keeps the full-book verdict
- compact_census continues to copy the nested census dict and does not grow a second expected-identity set

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/common.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests/production-rehearsal` | `runtime` | `ERP_LIMIT=10% remains the newest tenth of worksheets plus pinned worksheet 58699 when present`, `a production permit still refuses ERP_LIMIT`, `make import-erp with no limit remains the full import`, `partners, addresses, contacts, roles, and salespersons are not capped`, `a partners-only or named-layer run still fails erp-run-not-full`, `a mapped field discrepancy inside the imported slice still fails`, `limit full remains a pass and check_compact_acceptance.py keeps the full-book verdict`, `compact_census continues to copy the nested census dict and does not grow a second expected-identity set` | `plasticos_partner_import/erp/limits.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_partner_import/scripts/import_erp_shell.py`, `plasticos_partner_import/scripts/run_erp_import.py`, `plasticos_transaction/models/native_document_import.py`, `scripts/test_env.sh`, `Makefile`, `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/fidelity.py`, `tests/production-rehearsal/check_compact_acceptance.py` |
| T2 | `tests/production-rehearsal` | `assurance` | `ERP_LIMIT=10% remains the newest tenth of worksheets plus pinned worksheet 58699 when present`, `a production permit still refuses ERP_LIMIT`, `make import-erp with no limit remains the full import`, `partners, addresses, contacts, roles, and salespersons are not capped`, `a partners-only or named-layer run still fails erp-run-not-full`, `a mapped field discrepancy inside the imported slice still fails`, `limit full remains a pass and check_compact_acceptance.py keeps the full-book verdict`, `compact_census continues to copy the nested census dict and does not grow a second expected-identity set` | `plasticos_partner_import/erp/limits.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_partner_import/scripts/import_erp_shell.py`, `plasticos_partner_import/scripts/run_erp_import.py`, `plasticos_transaction/models/native_document_import.py`, `scripts/test_env.sh`, `Makefile`, `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/fidelity.py`, `tests/production-rehearsal/check_compact_acceptance.py` |
| T3 | `tests/production-rehearsal` | `assurance` | `ERP_LIMIT=10% remains the newest tenth of worksheets plus pinned worksheet 58699 when present`, `a production permit still refuses ERP_LIMIT`, `make import-erp with no limit remains the full import`, `partners, addresses, contacts, roles, and salespersons are not capped`, `a partners-only or named-layer run still fails erp-run-not-full`, `a mapped field discrepancy inside the imported slice still fails`, `limit full remains a pass and check_compact_acceptance.py keeps the full-book verdict`, `compact_census continues to copy the nested census dict and does not grow a second expected-identity set` | `plasticos_partner_import/erp/limits.py`, `plasticos_partner_import/erp/native_orders.py`, `plasticos_partner_import/scripts/import_erp_shell.py`, `plasticos_partner_import/scripts/run_erp_import.py`, `plasticos_transaction/models/native_document_import.py`, `scripts/test_env.sh`, `Makefile`, `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/fidelity.py`, `tests/production-rehearsal/check_compact_acceptance.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| source_execution_ref | `plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (limit 10% with payables_unselected.rows greater than 0 passes and facts.scope does not say every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes) → Do not update the success stubs until those outcomes hold |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the kit files. No schema migration and no database rewrite. The next rehearsal then imports every worksheet again. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q`
- re-run `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 3 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — The rehearsal kit's Gate 6 invocation and its judge. make import-erp with no limit, the production permit, the importer's worksheet selector, fidelity_run.py, and the compact census writer stay as they are. No addon version bump. |
| architectural_boundaries_crossed | `rehearsal Gate 6 invocation to the existing ERP_LIMIT contract`, `rehearsal judge to census.payables_unselected as the proof of the 10% slice` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Pass ERP_LIMIT=10% as one make assignment on the Gate 6 make import-erp invocation, and record --limit 10% on check-erp. Do not call make import-erp-test. Leave make import-erp with no limit as the full import. Do not modify scripts/test_env.sh or Makefile; ERP_LIMIT already matches the import-erp forward allowlist and is already passed into the container. State in SPEC.md and README.md that this rehearsal imports every partner layer and the newest 10% of worksheets, plus pinned worksheet 58699 when the source contains it, and that a permitted production run still refuses the cap. The percent is not a count of every source row, and the pinned worksheet may add one number beyond the tenth. | Cursor Build agent | `low` | S | `[]` | `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md` |
| T2 | Make the Gate 6 judge accept a faithful 10% slice only with the importer's own exclusion. When limit is 10%, census.payables_unselected.rows must be a positive integer or the result is erp-rehearsal-limit-unproven. That field is inside the nested census dict compact_census already copies; do not read the isolated full census. facts.scope must name the newest 10% plus pinned worksheet 58699 and must not say every worksheet. When limit is full, keep the current facts.scope sentence and do not require an exclusion. Any other limit, including empty, is erp-rehearsal-limit. erp-run-not-full stays for a partners-only or named-layer finished-line scope. A mapped-field mismatch inside the slice still returns erp-fidelity-discrepancy. Do not add unselected worksheets to the fidelity expected set: evaluate() walks the clone, so those worksheets are not missing comparison rows. | Cursor Build agent | `medium` | M | `[T1]` | `tests/production-rehearsal/common.py` |
| T3 | Update the stubbed Gate 6 success path. test_rehearsal_scripts.py must see ERP_LIMIT=10% on the make command and limit 10% on the receipt. ERP_CENSUS gains census.payables_unselected.rows greater than 0 so that success stub still passes. A 10% census with rows 0 fails erp-rehearsal-limit-unproven. A limit other than 10% or full fails erp-rehearsal-limit. A slice mismatch still fails. A partners-only log still fails erp-run-not-full. The library helper that passes limit full stays a full-book pass. Leave check_compact_acceptance.py judging the retained full snapshots. | Cursor Build agent | `low` | S | `[T2]` | `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py` |

**Critical path:** T1 → T2 → T3

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The rehearsal import is capped with ERP_LIMIT=10% and the receipt says so | T2 |
| M2 | A 10% pass requires payables_unselected.rows greater than 0 and does not claim the full book | T3 and V1 |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T2 | limit 10% with payables_unselected.rows greater than 0 passes and facts.scope does not say every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes | Do not update the success stubs until those outcomes hold |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`
- **Shared causes:** The rehearsal asks for every worksheet, and the judge can label a slice as that full book
- **Deletions / consolidations:** No second sampler and no fidelity expected-set expansion. ERP_LIMIT=10% plus census.payables_unselected are the cap and its proof.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| tests/production-rehearsal/SPEC.md | `update` | `T1`, `T2` | — |
| tests/production-rehearsal/README.md | `update` | `T1` | — |
| AGENTS.md | `n_a` | — | The rehearsal contract lives in tests/production-rehearsal/SPEC.md. This change does not alter the addon set or the full import command. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-03 | `quality_gate_evidence` | command | `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` | ERP_LIMIT=10% is on the rehearsal command; a 10% census with payables_unselected.rows greater than 0 passes and does not claim every worksheet; rows 0 fails erp-rehearsal-limit-unproven; a slice mismatch fails; partners-only fails erp-run-not-full; limit full still passes | `not_run` |
| E-V2 | SP-04 | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py` | hook catalog .pre-commit-config.yaml reports pass on those files | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does erp-run-not-full already reject a 10% worksheet cap? No. The finished-line scope is empty unless the run is partners-only or a named layer.
- Does recording --limit 10% prove the importer capped the run? No. check_erp stores that string and facts.scope still says every worksheet. The proof is census.payables_unselected.rows, written by native_document_import for reason diagnostic_limit and copied by compact_census.
- Would newest-10% drop pinned worksheet 58699? No. selected_worksheets appends it when the source contains it, so a pass must not require a count of exactly one tenth.
- Should the fidelity expected set grow to the unselected 90% and then mark them excluded? No. evaluate() walks the clone. Adding those worksheets would invent a second population the comparison never read.

### Assumption failure conditions

- payables_unselected.rows can be 0 on a real 10% cut of this source. The historical book has thousands of worksheets and their payables. A stub that omits the field is erp-rehearsal-limit-unproven, which is the fail-closed case.
- The five empty price-basis rows fall inside the newest 10%. They are not this rehearsal's pass condition. The retained full snapshots still carry them.

### Blast radius notes

- The rehearsal kit's Gate 6 invocation and its judge. make import-erp with no limit, the production permit, the importer's worksheet selector, fidelity_run.py, and the compact census writer stay as they are. No addon version bump.

### Rollback constraints

- Revert the kit files. No schema migration and no database rewrite. The next rehearsal then imports every worksheet again.

### Risks

| risk | mitigation |
|------|------------|
| The receipt says 10% while the import still realized every worksheet. | limit 10% fails erp-rehearsal-limit-unproven unless census.payables_unselected.rows is greater than 0. |
| A 10% pass still says every worksheet was imported. | facts.scope is rewritten only when limit is 10%. The full-book sentence remains for limit full. |
| The retained full-snapshot acceptance starts failing because the judge now requires 10%. | limit full stays a pass with no diagnostic exclusion. check_compact_acceptance.py and fidelity_run.py are not rewritten. |

## Out of scope

- A new worksheet sampler, a random sample, or a change to selected_worksheets, PINNED_WORKSHEETS, or parse_limit
- Changing the production-permit refusal of ERP_LIMIT, Makefile, or make import-erp with no limit
- Calling make import-erp-test, which clones a different database
- Capping partners, addresses, contacts, roles, salespersons, or the SQL payload read
- Adding unselected worksheets to the fidelity expected set
- A default cap on Gate 7
- Rewriting check_compact_acceptance.py, fidelity_run.py, or the retained full snapshots under evidence/2026-11-08_124519
- Running a live ERP import as part of this change
- Committing the dirty evidence/latest pointer or the interrupted run 2026-11-08_144631
- Historical accounting, payments, opening balances, and QuickBooks
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| source_ref | `plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V1, E-V2
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Do the five empty price-basis rows fall inside the newest 10%? — They are not required for this rehearsal pass. The retained full snapshots remain the record of those five rows. | `accept_bounded` |
| `open_blocker` | stop_reason | Hardened in place after audit. The kit has not been edited. A 10% pass now requires the importer's payables_unselected exclusion and must not claim the full book. U1 stays bounded. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1"
  name: "Prove Gate 6 on the newest 10% of worksheets"
  overview: "The rehearsal Gate 6 import uses the existing ERP_LIMIT=10% cap, and the Gate 6 judge treats a faithful import of that slice as a pass only when the importer's own census shows the cap excluded the rest. Partners, addresses, contacts, roles, and salespersons still load in full. Worksheets are the newest 10%, plus pinned worksheet 58699 when the source contains it. A pass must not claim every worksheet was imported. A mapped-field mismatch inside the slice still fails. A partners-only or single-layer run still fails. The full import command and the production-permit refusal of ERP_LIMIT stay unchanged. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0."
  status: "draft"
  is_project: false
  owner: "workspace-operator"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "f74d14d52e90a50e49a4bbe5a6d4a3f31b31530e"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "The rehearsal Gate 6 import uses the existing ERP_LIMIT=10% cap, and the Gate 6 judge treats a faithful import of that slice as a pass only when the importer's own census shows the cap excluded the rest. Partners, addresses, contacts, roles, and salespersons still load in full. Worksheets are the newest 10%, plus pinned worksheet 58699 when the source contains it. A pass must not claim every worksheet was imported. A mapped-field mismatch inside the slice still fails. A partners-only or single-layer run still fails. The full import command and the production-permit refusal of ERP_LIMIT stay unchanged. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0."
  success_properties:
    - id: "SP-01"
      property: "V1: the rehearsal import command passes ERP_LIMIT=10% as one make assignment and the Gate 6 receipt records limit 10%"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V1: limit 10% passes only when census.payables_unselected.rows is greater than 0, facts.scope does not say every worksheet, a mapped-field mismatch inside the slice fails, and a partners-only or named-layer run still fails erp-run-not-full"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-03"
      property: "V1: a limit other than 10% or full fails erp-rehearsal-limit, and limit full still passes with no diagnostic exclusion while facts.scope still names every worksheet"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-04"
      property: "V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/production-rehearsal/erp_slice.sh", "tests/production-rehearsal/common.py", "tests/production-rehearsal/SPEC.md", "tests/production-rehearsal/README.md", "tests/production-rehearsal/test_rehearsal_scripts.py", "tests/production-rehearsal/test_rehearsal_kit_lib.py"]
    write_deny: ["plasticos_partner_import/erp/limits.py", "plasticos_partner_import/erp/native_orders.py", "plasticos_partner_import/scripts/import_erp_shell.py", "plasticos_partner_import/scripts/run_erp_import.py", "plasticos_transaction/models/native_document_import.py", "scripts/test_env.sh", "Makefile", "tests/production-rehearsal/fidelity_run.py", "tests/production-rehearsal/fidelity.py", "tests/production-rehearsal/check_compact_acceptance.py"]
  commands:
    allow: ["python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q", "pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py"]
  network:
    mode: "none"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1"
dependency_topology_ref: "dag.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1"
validation_evidence_refs: ["E-V1", "E-V2"]
stress_and_disconfirm:
  disconfirming_cases: ["Does erp-run-not-full already reject a 10% worksheet cap? No. The finished-line scope is empty unless the run is partners-only or a named layer.", "Does recording --limit 10% prove the importer capped the run? No. check_erp stores that string and facts.scope still says every worksheet. The proof is census.payables_unselected.rows, written by native_document_import for reason diagnostic_limit and copied by compact_census.", "Would newest-10% drop pinned worksheet 58699? No. selected_worksheets appends it when the source contains it, so a pass must not require a count of exactly one tenth.", "Should the fidelity expected set grow to the unselected 90% and then mark them excluded? No. evaluate() walks the clone. Adding those worksheets would invent a second population the comparison never read."]
  assumption_failure_conditions: ["payables_unselected.rows can be 0 on a real 10% cut of this source. The historical book has thousands of worksheets and their payables. A stub that omits the field is erp-rehearsal-limit-unproven, which is the fail-closed case.", "The five empty price-basis rows fall inside the newest 10%. They are not this rehearsal's pass condition. The retained full snapshots still carry them."]
out_of_scope: ["A new worksheet sampler, a random sample, or a change to selected_worksheets, PINNED_WORKSHEETS, or parse_limit", "Changing the production-permit refusal of ERP_LIMIT, Makefile, or make import-erp with no limit", "Calling make import-erp-test, which clones a different database", "Capping partners, addresses, contacts, roles, salespersons, or the SQL payload read", "Adding unselected worksheets to the fidelity expected set", "A default cap on Gate 7", "Rewriting check_compact_acceptance.py, fidelity_run.py, or the retained full snapshots under evidence/2026-11-08_124519", "Running a live ERP import as part of this change", "Committing the dirty evidence/latest pointer or the interrupted run 2026-11-08_144631", "Historical accounting, payments, opening balances, and QuickBooks"]
convergence_contract_ref: "conv.plan.simple.prove_gate_6_on_the_newest_10_of_worksheets.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Pass ERP_LIMIT=10% as one make assignment on the Gate 6 make import-erp invocation, and record --limit 10% on check-erp. Do not call make import-erp-test. Leave make import-erp with no limit as the full import. Do not modify scripts/test_env.sh or Makefile; ERP_LIMIT already matches the import-erp forward allowlist and is already passed into the container. State in SPEC.md and README.md that this rehearsal imports every partner layer and the newest 10% of worksheets, plus pinned worksheet 58699 when the source contains it, and that a permitted production run still refuses the cap. The percent is not a count of every source row, and the pinned worksheet may add one number beyond the tenth."
    status: "pending"
  - id: "T2"
    content: "Make the Gate 6 judge accept a faithful 10% slice only with the importer's own exclusion. When limit is 10%, census.payables_unselected.rows must be a positive integer or the result is erp-rehearsal-limit-unproven. That field is inside the nested census dict compact_census already copies; do not read the isolated full census. facts.scope must name the newest 10% plus pinned worksheet 58699 and must not say every worksheet. When limit is full, keep the current facts.scope sentence and do not require an exclusion. Any other limit, including empty, is erp-rehearsal-limit. erp-run-not-full stays for a partners-only or named-layer finished-line scope. A mapped-field mismatch inside the slice still returns erp-fidelity-discrepancy. Do not add unselected worksheets to the fidelity expected set: evaluate() walks the clone, so those worksheets are not missing comparison rows."
    status: "pending"
  - id: "T3"
    content: "Update the stubbed Gate 6 success path. test_rehearsal_scripts.py must see ERP_LIMIT=10% on the make command and limit 10% on the receipt. ERP_CENSUS gains census.payables_unselected.rows greater than 0 so that success stub still passes. A 10% census with rows 0 fails erp-rehearsal-limit-unproven. A limit other than 10% or full fails erp-rehearsal-limit. A slice mismatch still fails. A partners-only log still fails erp-run-not-full. The library helper that passes limit full stays a full-book pass. Leave check_compact_acceptance.py judging the retained full snapshots."
    status: "pending"
```
