---
name: Keep Gate 6 proof without the three full dumps
overview: "Stop the rehearsal evidence folder from needing 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, and 05-erp-summary-census.json as full dumps. The full importer census for a rehearsal is created only in an isolated directory outside the git checkout, and only a validated compact receipt is atomically published into the evidence folder. The compact verifier proves expected identities, observed i..."
todos:
  - id: T1
    content: "Keep the clone comparison in memory for this change. Do not write 05-erp-fidelity-odoo.json and do not write the full comparison ledger anywhere inside the evidence directory. Atomically publish 05-erp-fidelity.json with the FAIL rows, the compared and failed counts, and a digest of recorded comparisons. In the same receipt, publish a coverage ledger that is independent of that digest: expected identity count and digest, observed identity count and digest, missing-document count, digest, and bounded sample, duplicate-document count, digest, and bounded sample, the excluded field names and their counts, the rejected-record count and digest, and a source-coverage partition in which every expected identity is compared, rejected, or excluded and those counts sum. A present comparison digest does not pass an identity that is absent from that partition. Record in SPEC that batch-wise comparison with bounded memory per batch is a later plan and is not this change, because current memory consumption is not a demonstrated problem."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Point the rehearsal importer report at an isolated directory outside the git checkout, and mount that directory into the container. The unchanged importer then writes the full census beside that report, not beside the evidence summary. Read that outside file and atomically publish only the compact census receipt into the evidence directory: payload_kind, a sha256 of source_origin with the raw name omitted, the grouped census, classified anomaly counts, a per-class diagnostic sample capped so the receipt stays under 1000KB, unresolved_count, attributed_count for rows that have table and kind and key, unattributed_count, and a digest of the attributed keys. Do not publish a boolean in place of those counts. Leave the full census in the isolated directory so the anomaly rows remain locally inspectable. Do not delete it on success. A crash before the atomic rename must leave the evidence directory without the anomaly array and without the unresolved array. Do not change plasticos_partner_import/scripts/run_erp_import.py. A non-rehearsal summary path still receives the full census sibling."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Judge Gate 6 from the compact receipts. Fail erp-source-not-database unless payload_kind is database. Fail erp-source-unattributed unless the origin digest is present. Fail erp-unexpected-partial unless attributed_count equals unresolved_count and unattributed_count is zero. Fail source coverage when an expected identity is outside the compared, rejected, and excluded partition. Fail when a required document identity is missing or duplicated. Keep erp-native-documents-missing against the compact line counts. Keep erp-fidelity-discrepancy for each stored FAIL row. Update SPEC.md and README.md so the evidence tree names the compact receipts, the isolated census directory, and the decision that this change still compares the clone in memory."
    status: pending
    phase: execute
    depends_on: [T1, T2]
  - id: T4
    content: "Update the stubbed Gate 6 tests for the compact receipts. Assert the failure codes in V1, including a coverage miss that still has a comparison digest, an unresolved count that does not match the attributed count, and an interrupted publish that leaves none of the three full dumps in the evidence directory. Keep the summary-equation, duplicates, production-permit, and web-lead tests unchanged."
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "Add tests/production-rehearsal/check_compact_acceptance.py and run it as V3. It reads the retained full-size snapshots from evidence/2026-11-08_124519 and re-reads odoo_test_cutover. It does not start a second import and it is not collected by pytest tests/. It fails closed when the clone or the retained snapshots are absent. It must show that every expected source identity and mapped field was examined, that the five PriceBasis mismatches remain detectable, that the three full-size dumps are absent from the evidence directory after a completed publish and after an interrupted publish, that the compact receipts reproduce the gate verdict, and that the new verifier's counts agree with the previous implementation on those same snapshots."
    status: pending
    phase: execute
    depends_on: [T3, T4]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Keep Gate 6 proof without the three full dumps

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `keep_gate_6_proof_without_the_three_full_dumps_f9f6a89e.plan.md`
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
| plan_id | `plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| name | Keep Gate 6 proof without the three full dumps |
| overview | Stop the rehearsal evidence folder from needing 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, and 05-erp-summary-census.json as full dumps. The full importer census for a rehearsal is created only in an isolated directory outside the git checkout, and only a validated compact receipt is atomically published into the evidence folder. The compact verifier proves expected identities, observed identities, missing and duplicate documents, excluded fields, rejected records, and source coverage. A digest of recorded comparisons is not that proof. Classified anomaly counts and bounded diagnostics stay. Unresolved-row attribution is a count of every row, not a boolean. This change may still materialize the clone comparison in memory. Batch-wise comparison is a separate later plan. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | workspace-operator |
| created_at | 2026-11-08T13:57:28+00:00 |
| updated_at | 2026-11-08T13:57:28+00:00 |
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
| captured_at | `2026-11-08T13:57:28+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `fix/rehearsal-evidence-20261108` |
| commit_sha | `3b6d9e02fa15e20f333a7a73cb4af18c94229ca7` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Stop the rehearsal evidence folder from needing 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, and 05-erp-summary-census.json as full dumps. The full importer census for a rehearsal is created only in an isolated directory outside the git checkout, and only a validated compact receipt is atomically published into the evidence folder. The compact verifier proves expected identities, observed identities, missing and duplicate documents, excluded fields, rejected records, and source coverage. A digest of recorded comparisons is not that proof. Classified anomaly counts and bounded diagnostics stay. Unresolved-row attribution is a count of every row, not a boolean. This change may still materialize the clone comparison in memory. Batch-wise comparison is a separate later plan. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0.

### Scope in

- The rehearsal importer report path is an isolated directory outside the git checkout, mounted into the container because the checkout bind mount is the only default write path
- Atomic publish of the compact census receipt, the compact fidelity receipt, and the compact identity ledger into the evidence directory
- A coverage ledger of expected identities, observed identities, missing documents, duplicate documents, excluded fields, rejected records, and source coverage
- Classified anomaly counts, bounded per-class diagnostics, and unresolved attribution counts
- SPEC.md, README.md, the stubbed Gate 6 tests, and one local acceptance command against the cutover clone
- In-memory clone comparison for this change only

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: a stored FAIL row still returns erp-fidelity-discrepancy, a report whose failed count does not equal the stored FAIL rows returns erp-fidelity-unproven, and a present comparison digest with a missing expected identity still fails source coverage | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → all tests passed | `true` |
| SP-02 | V1: a compact census with payload_kind grid fails erp-source-not-database, an empty origin digest fails erp-source-unattributed, and a partial status whose attributed unresolved count does not equal the unresolved count fails erp-unexpected-partial | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → all tests passed | `true` |
| SP-03 | V1: native-document checks fail erp-native-documents-missing when persisted lines are below realized lines, fail when a required identity is missing or duplicated, and fail erp-native-snapshot-unreadable when the compact identity ledger is absent | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → all tests passed | `true` |
| SP-04 | V1: an interrupted writer leaves the evidence directory without 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, or a census that contains the anomaly or unresolved arrays | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` → all tests passed | `true` |
| SP-05 | V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml | `quality_gate` | V2: `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/production-rehearsal/check_compact_acceptance.py` → hook catalog .pre-commit-config.yaml reports pass on those files | `true` |
| SP-06 | V3: on the retained full-size snapshots and odoo_test_cutover, every expected source identity and mapped field was examined, the five empty PriceBasis values stored as incoterm FOB remain detectable, the three full-size dumps are absent from the evidence directory including after an interrupted publish, the compact receipts reproduce the gate verdict, and the new verifier's counts agree with the previous implementation | `quality_gate` | V3: `python3 tests/production-rehearsal/check_compact_acceptance.py` → the command exits 0 against odoo_test_cutover and evidence/2026-11-08_124519, the five PriceBasis mismatches are present, the three full dumps are absent from the evidence directory after both a completed publish and an interrupted publish, and the compact counts agree with the retained snapshots | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| source_ref | `plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind checkout fix/rehearsal-evidence-20261108 at 3b6d9e02; hook catalog .pre-commit-config.yaml; MEMORY_PREFETCH snapshot_digest f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2` | branch and HEAD recorded; catalog file present; prefetch conflicts=0 | `true` |
| P1 | pre-validation (status `passed`) | `read fidelity_run.py main, erp_slice.sh fidelity invocation, common.py fidelity_failures and native_document_census, and run_erp_import.py _write_census` | the kit writes the three full files into the evidence directory and reads each once; the container bind mount is the checkout; the importer census writer is the sibling of any summary path and is not rehearsal-only | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence sufficient` | depth standard and omit_gates empty | `true` |
| P3 | pre-validation (status `passed`) | `apply the three architectural corrections and the cutover acceptance requirement to this plan` | the full census is outside the checkout, coverage is independent of the comparison digest, in-memory comparison stays only for this change, and V3 names the cutover clone | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py`, `tests/production-rehearsal/test_erp_census_source.py`, `tests/production-rehearsal/check_compact_acceptance.py`
- **write_deny:** `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q`, `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/production-rehearsal/check_compact_acceptance.py`, `python3 tests/production-rehearsal/check_compact_acceptance.py`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `read_only` |
| allowed_services | `local docker database odoo_test_cutover` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- payload_kind database is still required
- a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count
- a mapped field discrepancy still fails and the failing rows stay in the evidence
- source coverage fails when an expected identity was not compared, rejected, or excluded
- the clone must still account for the native documents the importer realized
- the summary equation, duplicates, and the production-permit refusal stay
- the importer still writes a full census sibling for a summary path outside this rehearsal
- this change may materialize the clone comparison in memory and does not implement batch-wise comparison

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/check_compact_acceptance.py tests/production-rehearsal/SPEC.md` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests/production-rehearsal` | `runtime` | `payload_kind database is still required`, `a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count`, `a mapped field discrepancy still fails and the failing rows stay in the evidence`, `source coverage fails when an expected identity was not compared, rejected, or excluded`, `the clone must still account for the native documents the importer realized`, `the summary equation, duplicates, and the production-permit refusal stay`, `the importer still writes a full census sibling for a summary path outside this rehearsal`, `this change may materialize the clone comparison in memory and does not implement batch-wise comparison` | `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T2 | `tests/production-rehearsal` | `assurance` | `payload_kind database is still required`, `a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count`, `a mapped field discrepancy still fails and the failing rows stay in the evidence`, `source coverage fails when an expected identity was not compared, rejected, or excluded`, `the clone must still account for the native documents the importer realized`, `the summary equation, duplicates, and the production-permit refusal stay`, `the importer still writes a full census sibling for a summary path outside this rehearsal`, `this change may materialize the clone comparison in memory and does not implement batch-wise comparison` | `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T3 | `tests/production-rehearsal` | `assurance` | `payload_kind database is still required`, `a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count`, `a mapped field discrepancy still fails and the failing rows stay in the evidence`, `source coverage fails when an expected identity was not compared, rejected, or excluded`, `the clone must still account for the native documents the importer realized`, `the summary equation, duplicates, and the production-permit refusal stay`, `the importer still writes a full census sibling for a summary path outside this rehearsal`, `this change may materialize the clone comparison in memory and does not implement batch-wise comparison` | `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T4 | `tests/production-rehearsal` | `assurance` | `payload_kind database is still required`, `a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count`, `a mapped field discrepancy still fails and the failing rows stay in the evidence`, `source coverage fails when an expected identity was not compared, rejected, or excluded`, `the clone must still account for the native documents the importer realized`, `the summary equation, duplicates, and the production-permit refusal stay`, `the importer still writes a full census sibling for a summary path outside this rehearsal`, `this change may materialize the clone comparison in memory and does not implement batch-wise comparison` | `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T5 | `tests/production-rehearsal` | `assurance` | `payload_kind database is still required`, `a partial import fails unless every unresolved row is attributed and the attributed count equals the unresolved count`, `a mapped field discrepancy still fails and the failing rows stay in the evidence`, `source coverage fails when an expected identity was not compared, rejected, or excluded`, `the clone must still account for the native documents the importer realized`, `the summary equation, duplicates, and the production-permit refusal stay`, `the importer still writes a full census sibling for a summary path outside this rehearsal`, `this change may materialize the clone comparison in memory and does not implement batch-wise comparison` | `plasticos_partner_import/scripts/run_erp_import.py`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| source_execution_ref | `plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 passes, including the interrupted publish and a coverage miss that still has a comparison digest) → stop before treating the compact receipt as proof of the full-size import; C2 fails (V2 and V3 pass) → do not treat the evidence contract as changed |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the kit files. No schema migration and no production write. The retained full dumps under evidence/2026-11-08_124519 stay untracked. The isolated census outside the checkout can be removed by deleting that directory. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q`
- re-run `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/production-rehearsal/check_compact_acceptance.py`
- re-run `python3 tests/production-rehearsal/check_compact_acceptance.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 5 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `medium` — A compact receipt that treats a comparison digest as coverage can hide an unexamined source identity. A census path that stays on the checkout bind mount puts the full census back in the evidence directory. The importer writer outside the rehearsal stays, so other import reports still receive the full census sibling. |
| architectural_boundaries_crossed | `rehearsal evidence contract to the Gate 6 verdict`, `rehearsal report path to an isolated directory outside the checkout`, `compact coverage ledger to the native-document checks` |
| external_systems_touched | `local docker database odoo_test_cutover` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Keep the clone comparison in memory for this change. Do not write 05-erp-fidelity-odoo.json and do not write the full comparison ledger anywhere inside the evidence directory. Atomically publish 05-erp-fidelity.json with the FAIL rows, the compared and failed counts, and a digest of recorded comparisons. In the same receipt, publish a coverage ledger that is independent of that digest: expected identity count and digest, observed identity count and digest, missing-document count, digest, and bounded sample, duplicate-document count, digest, and bounded sample, the excluded field names and their counts, the rejected-record count and digest, and a source-coverage partition in which every expected identity is compared, rejected, or excluded and those counts sum. A present comparison digest does not pass an identity that is absent from that partition. Record in SPEC that batch-wise comparison with bounded memory per batch is a later plan and is not this change, because current memory consumption is not a demonstrated problem. | Cursor Build agent | `medium` | M | `[]` | `tests/production-rehearsal/fidelity_run.py`, `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md` |
| T2 | Point the rehearsal importer report at an isolated directory outside the git checkout, and mount that directory into the container. The unchanged importer then writes the full census beside that report, not beside the evidence summary. Read that outside file and atomically publish only the compact census receipt into the evidence directory: payload_kind, a sha256 of source_origin with the raw name omitted, the grouped census, classified anomaly counts, a per-class diagnostic sample capped so the receipt stays under 1000KB, unresolved_count, attributed_count for rows that have table and kind and key, unattributed_count, and a digest of the attributed keys. Do not publish a boolean in place of those counts. Leave the full census in the isolated directory so the anomaly rows remain locally inspectable. Do not delete it on success. A crash before the atomic rename must leave the evidence directory without the anomaly array and without the unresolved array. Do not change plasticos_partner_import/scripts/run_erp_import.py. A non-rehearsal summary path still receives the full census sibling. | Cursor Build agent | `medium` | M | `[T1]` | `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py` |
| T3 | Judge Gate 6 from the compact receipts. Fail erp-source-not-database unless payload_kind is database. Fail erp-source-unattributed unless the origin digest is present. Fail erp-unexpected-partial unless attributed_count equals unresolved_count and unattributed_count is zero. Fail source coverage when an expected identity is outside the compared, rejected, and excluded partition. Fail when a required document identity is missing or duplicated. Keep erp-native-documents-missing against the compact line counts. Keep erp-fidelity-discrepancy for each stored FAIL row. Update SPEC.md and README.md so the evidence tree names the compact receipts, the isolated census directory, and the decision that this change still compares the clone in memory. | Cursor Build agent | `medium` | M | `[T1, T2]` | `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md` |
| T4 | Update the stubbed Gate 6 tests for the compact receipts. Assert the failure codes in V1, including a coverage miss that still has a comparison digest, an unresolved count that does not match the attributed count, and an interrupted publish that leaves none of the three full dumps in the evidence directory. Keep the summary-equation, duplicates, production-permit, and web-lead tests unchanged. | Cursor Build agent | `medium` | M | `[T3]` | `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py`, `tests/production-rehearsal/test_erp_census_source.py` |
| T5 | Add tests/production-rehearsal/check_compact_acceptance.py and run it as V3. It reads the retained full-size snapshots from evidence/2026-11-08_124519 and re-reads odoo_test_cutover. It does not start a second import and it is not collected by pytest tests/. It fails closed when the clone or the retained snapshots are absent. It must show that every expected source identity and mapped field was examined, that the five PriceBasis mismatches remain detectable, that the three full-size dumps are absent from the evidence directory after a completed publish and after an interrupted publish, that the compact receipts reproduce the gate verdict, and that the new verifier's counts agree with the previous implementation on those same snapshots. | Cursor Build agent | `medium` | M | `[T3, T4]` | `tests/production-rehearsal/check_compact_acceptance.py`, `tests/production-rehearsal/SPEC.md` |

**Critical path:** T1 → T2 → T3 → T4 → T5

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The evidence directory receives only atomically published compact receipts, and the full census exists only outside the checkout | the stubbed tests can lock coverage, attribution counts, and the interrupt path |
| M2 | The cutover acceptance command agrees with the retained full-size snapshots and still detects the five PriceBasis mismatches | the kit can be published without the three full dumps |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 passes, including the interrupted publish and a coverage miss that still has a comparison digest | stop before treating the compact receipt as proof of the full-size import |
| C2 | M2 | V2 and V3 pass | do not treat the evidence contract as changed |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`, `T5`
- **Shared causes:** the evidence directory persists populations the gate only needs to judge; counts and a comparison digest are not proof that every required record was examined
- **Deletions / consolidations:** Stop creating the clone snapshot and the full comparison ledger inside the evidence directory; Move the rehearsal's full census to an isolated directory outside the checkout and publish a compact receipt with an atomic rename; Replace the unresolved attribution boolean with attributed and unattributed counts

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| tests/production-rehearsal/SPEC.md | `update` | `T1`, `T3`, `T5` | — |
| tests/production-rehearsal/README.md | `update` | `T3` | — |
| AGENTS.md | `n_a` | — | The kit contract is SPEC.md. The importer census writer for non-rehearsal reports stays. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-03, SP-04 | `quality_gate_evidence` | command | `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q` | all tests passed | `not_run` |
| E-V2 | SP-05 | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/production-rehearsal/check_compact_acceptance.py` | hook catalog .pre-commit-config.yaml reports pass on those files | `not_run` |
| E-V3 | SP-06 | `quality_gate_evidence` | command | `python3 tests/production-rehearsal/check_compact_acceptance.py` | the command exits 0 against odoo_test_cutover and evidence/2026-11-08_124519, the five PriceBasis mismatches are present, the three full dumps are absent from the evidence directory after both a completed publish and an interrupted publish, and the compact counts agree with the retained snapshots | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can a crash during census generation still leave the full census inside the evidence directory?
- Can a digest of recorded comparisons pass while an expected source identity was never examined?
- Can a partial import pass because unresolved_attributed is true while some of the unresolved rows have no table, kind, or key?
- Do the classified anomaly counts and the bounded diagnostics disappear, leaving the anomaly rows inspectable only if someone still has the unpublished dump?
- Does this change rewrite fidelity_run.py into a batch-wise streaming comparison?
- Does moving the rehearsal report path also move the census written for a non-rehearsal import?
- Does V3 skip when the cutover clone or the retained snapshots are absent?

### Assumption failure conditions

- A digest of 282223 recorded comparisons proves every required source record was examined
- A boolean attribution flag proves all unresolved rows are attributed
- The container can write outside the checkout without an extra mounted directory
- Current memory consumption is already a demonstrated problem that requires a streaming refactor in this change

### Blast radius notes

- A compact receipt that treats a comparison digest as coverage can hide an unexamined source identity. A census path that stays on the checkout bind mount puts the full census back in the evidence directory. The importer writer outside the rehearsal stays, so other import reports still receive the full census sibling.

### Rollback constraints

- Revert the kit files. No schema migration and no production write. The retained full dumps under evidence/2026-11-08_124519 stay untracked. The isolated census outside the checkout can be removed by deleting that directory.

### Risks

| risk | mitigation |
|------|------------|
| The container bind mount is the checkout, so a report path inside the evidence directory still creates the full census there | Mount an isolated host directory into the container and point only the rehearsal report at it. The evidence directory receives the compact receipt by atomic rename from the host. |
| The in-memory comparison still holds the clone and the source rows for this change | Accept that for this change. Do not start the batch-wise refactor unless a measured run shows the memory is a problem. SPEC records that limit. |
| Capping the anomaly diagnostics hides a class | Publish the count of every class, and keep the full census in the isolated directory for local inspection. The cap applies only to the published sample, and the receipt records the cap. |
| Open pull request 404 already publishes the small Gate 6 receipts from the run that still has the five discrepancies | Build stacks on that open pull request. This plan does not republish the three full dumps and does not change those five rows. |

## Out of scope

- A batch-wise source and target comparison with bounded memory per batch
- Changing plasticos_partner_import census writer for reports outside the rehearsal
- Publishing the three existing full dumps from evidence/2026-11-08_124519
- Deleting the isolated full census that remains outside the checkout for local investigation
- Fixing the five empty price-basis rows that stored incoterm FOB
- Historical accounting, payments, opening balances, and QuickBooks
- Replacing another worktree's database
- BAN001 and the customer export
- A second full ERP import
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
| source_ref | `plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `open_blocker` | stop_reason | Revised plan is ready for Build. The kit has not been edited. Batch-wise comparison remains a separate later plan. | planning convergence `partial` |

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
  plan_id: "plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1"
  name: "Keep Gate 6 proof without the three full dumps"
  overview: "Stop the rehearsal evidence folder from needing 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, and 05-erp-summary-census.json as full dumps. The full importer census for a rehearsal is created only in an isolated directory outside the git checkout, and only a validated compact receipt is atomically published into the evidence folder. The compact verifier proves expected identities, observed identities, missing and duplicate documents, excluded fields, rejected records, and source coverage. A digest of recorded comparisons is not that proof. Classified anomaly counts and bounded diagnostics stay. Unresolved-row attribution is a count of every row, not a boolean. This change may still materialize the clone comparison in memory. Batch-wise comparison is a separate later plan. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0."
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
  commit_sha: "3b6d9e02fa15e20f333a7a73cb4af18c94229ca7"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Stop the rehearsal evidence folder from needing 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, and 05-erp-summary-census.json as full dumps. The full importer census for a rehearsal is created only in an isolated directory outside the git checkout, and only a validated compact receipt is atomically published into the evidence folder. The compact verifier proves expected identities, observed identities, missing and duplicate documents, excluded fields, rejected records, and source coverage. A digest of recorded comparisons is not that proof. Classified anomaly counts and bounded diagnostics stay. Unresolved-row attribution is a count of every row, not a boolean. This change may still materialize the clone comparison in memory. Batch-wise comparison is a separate later plan. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0."
  success_properties:
    - id: "SP-01"
      property: "V1: a stored FAIL row still returns erp-fidelity-discrepancy, a report whose failed count does not equal the stored FAIL rows returns erp-fidelity-unproven, and a present comparison digest with a missing expected identity still fails source coverage"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V1: a compact census with payload_kind grid fails erp-source-not-database, an empty origin digest fails erp-source-unattributed, and a partial status whose attributed unresolved count does not equal the unresolved count fails erp-unexpected-partial"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-03"
      property: "V1: native-document checks fail erp-native-documents-missing when persisted lines are below realized lines, fail when a required identity is missing or duplicated, and fail erp-native-snapshot-unreadable when the compact identity ledger is absent"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-04"
      property: "V1: an interrupted writer leaves the evidence directory without 05-erp-fidelity.json, 05-erp-fidelity-odoo.json, or a census that contains the anomaly or unresolved arrays"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-05"
      property: "V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-06"
      property: "V3: on the retained full-size snapshots and odoo_test_cutover, every expected source identity and mapped field was examined, the five empty PriceBasis values stored as incoterm FOB remain detectable, the three full-size dumps are absent from the evidence directory including after an interrupted publish, the compact receipts reproduce the gate verdict, and the new verifier's counts agree with the previous implementation"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/production-rehearsal/fidelity_run.py", "tests/production-rehearsal/erp_slice.sh", "tests/production-rehearsal/common.py", "tests/production-rehearsal/SPEC.md", "tests/production-rehearsal/README.md", "tests/production-rehearsal/test_rehearsal_scripts.py", "tests/production-rehearsal/test_rehearsal_kit_lib.py", "tests/production-rehearsal/test_erp_census_source.py", "tests/production-rehearsal/check_compact_acceptance.py"]
    write_deny: ["plasticos_partner_import/scripts/run_erp_import.py", "ci/check_banned_identifier.py", "plasticos_transaction/", "scripts/test_env.sh"]
  commands:
    allow: ["python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py -q", "pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/fidelity_run.py tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/production-rehearsal/check_compact_acceptance.py", "python3 tests/production-rehearsal/check_compact_acceptance.py"]
  network:
    mode: "read_only"
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
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T5"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1"
dependency_topology_ref: "dag.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3"]
stress_and_disconfirm:
  disconfirming_cases: ["Can a crash during census generation still leave the full census inside the evidence directory?", "Can a digest of recorded comparisons pass while an expected source identity was never examined?", "Can a partial import pass because unresolved_attributed is true while some of the unresolved rows have no table, kind, or key?", "Do the classified anomaly counts and the bounded diagnostics disappear, leaving the anomaly rows inspectable only if someone still has the unpublished dump?", "Does this change rewrite fidelity_run.py into a batch-wise streaming comparison?", "Does moving the rehearsal report path also move the census written for a non-rehearsal import?", "Does V3 skip when the cutover clone or the retained snapshots are absent?"]
  assumption_failure_conditions: ["A digest of 282223 recorded comparisons proves every required source record was examined", "A boolean attribution flag proves all unresolved rows are attributed", "The container can write outside the checkout without an extra mounted directory", "Current memory consumption is already a demonstrated problem that requires a streaming refactor in this change"]
out_of_scope: ["A batch-wise source and target comparison with bounded memory per batch", "Changing plasticos_partner_import census writer for reports outside the rehearsal", "Publishing the three existing full dumps from evidence/2026-11-08_124519", "Deleting the isolated full census that remains outside the checkout for local investigation", "Fixing the five empty price-basis rows that stored incoterm FOB", "Historical accounting, payments, opening balances, and QuickBooks", "Replacing another worktree's database", "BAN001 and the customer export", "A second full ERP import"]
convergence_contract_ref: "conv.plan.simple.keep_gate_6_proof_without_the_three_full_dumps.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Keep the clone comparison in memory for this change. Do not write 05-erp-fidelity-odoo.json and do not write the full comparison ledger anywhere inside the evidence directory. Atomically publish 05-erp-fidelity.json with the FAIL rows, the compared and failed counts, and a digest of recorded comparisons. In the same receipt, publish a coverage ledger that is independent of that digest: expected identity count and digest, observed identity count and digest, missing-document count, digest, and bounded sample, duplicate-document count, digest, and bounded sample, the excluded field names and their counts, the rejected-record count and digest, and a source-coverage partition in which every expected identity is compared, rejected, or excluded and those counts sum. A present comparison digest does not pass an identity that is absent from that partition. Record in SPEC that batch-wise comparison with bounded memory per batch is a later plan and is not this change, because current memory consumption is not a demonstrated problem."
    status: "pending"
  - id: "T2"
    content: "Point the rehearsal importer report at an isolated directory outside the git checkout, and mount that directory into the container. The unchanged importer then writes the full census beside that report, not beside the evidence summary. Read that outside file and atomically publish only the compact census receipt into the evidence directory: payload_kind, a sha256 of source_origin with the raw name omitted, the grouped census, classified anomaly counts, a per-class diagnostic sample capped so the receipt stays under 1000KB, unresolved_count, attributed_count for rows that have table and kind and key, unattributed_count, and a digest of the attributed keys. Do not publish a boolean in place of those counts. Leave the full census in the isolated directory so the anomaly rows remain locally inspectable. Do not delete it on success. A crash before the atomic rename must leave the evidence directory without the anomaly array and without the unresolved array. Do not change plasticos_partner_import/scripts/run_erp_import.py. A non-rehearsal summary path still receives the full census sibling."
    status: "pending"
  - id: "T3"
    content: "Judge Gate 6 from the compact receipts. Fail erp-source-not-database unless payload_kind is database. Fail erp-source-unattributed unless the origin digest is present. Fail erp-unexpected-partial unless attributed_count equals unresolved_count and unattributed_count is zero. Fail source coverage when an expected identity is outside the compared, rejected, and excluded partition. Fail when a required document identity is missing or duplicated. Keep erp-native-documents-missing against the compact line counts. Keep erp-fidelity-discrepancy for each stored FAIL row. Update SPEC.md and README.md so the evidence tree names the compact receipts, the isolated census directory, and the decision that this change still compares the clone in memory."
    status: "pending"
  - id: "T4"
    content: "Update the stubbed Gate 6 tests for the compact receipts. Assert the failure codes in V1, including a coverage miss that still has a comparison digest, an unresolved count that does not match the attributed count, and an interrupted publish that leaves none of the three full dumps in the evidence directory. Keep the summary-equation, duplicates, production-permit, and web-lead tests unchanged."
    status: "pending"
  - id: "T5"
    content: "Add tests/production-rehearsal/check_compact_acceptance.py and run it as V3. It reads the retained full-size snapshots from evidence/2026-11-08_124519 and re-reads odoo_test_cutover. It does not start a second import and it is not collected by pytest tests/. It fails closed when the clone or the retained snapshots are absent. It must show that every expected source identity and mapped field was examined, that the five PriceBasis mismatches remain detectable, that the three full-size dumps are absent from the evidence directory after a completed publish and after an interrupted publish, that the compact receipts reproduce the gate verdict, and that the new verifier's counts agree with the previous implementation on those same snapshots."
    status: "pending"
```
