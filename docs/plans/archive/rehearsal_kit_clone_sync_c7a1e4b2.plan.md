---
name: Run the rehearsal kit on the checkout
overview: "Make tests/production-rehearsal execute the go-live data sync on the code in the checkout that invokes it. A ready verdict means that sync completed. It does not mean Staging may be promoted. Branch name, equality with origin/Staging, a fetch failure, a dirty tree, a merge-tree conflict, and movement of Staging or Production during the run are recorded and do not fail or skip the sync. The kit ..."
todos:
  - id: T1
    content: "Record branch, HEAD, dirty paths, the fetch result, the Production/Staging merge-tree, and the ending remote SHAs. Do not fail or skip later gates for not-on-staging, head-not-origin-staging, worktree-dirty, remote-fetch-failed, a merge-tree conflict, staging-ref-drifted, or production-ref-drifted. State in SPEC and README that ready means this checkout's sync completed, not that Staging may be promoted. Keep the production-stage, permit, secret-scan, install-smoke, cutover-ownership, and web-lead failures."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Point Gate 7 at plasticos_crm_sync/Vanillasoft-Scrap-Management.csv in the checkout. Hash that file at run time and pass the hash only because scripts/test_env.sh requires VANILLASOFT_HISTORY_CENSUS_SHA256. Store no digest in the kit. A missing file fails the gate. Do not pass VANILLASOFT_HISTORY_MAX_IDS unless REHEARSAL_HISTORY_MAX_IDS is already set. Remove the census-unbound and digest-unbound blocker entries. Keep the key-unbound blocker, the rolling-floor refusal, the production-permit refusal, and the kit's own evidence ledger."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Call make import-erp with no LIMIT. Unset ERP_LIMIT is the full import. Update the ERP receipt so its scope and execution_path no longer say 10 percent or not a full historical import. Keep the summary equation, duplicates, payload_kind database, fidelity, native-document checks, and the production-permit refusal."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Make historical_cohort.report stamp the length of the census it was given, and judge completeness against that length. Do not change COHORT for the two-column loader or the tracked-export digest refusal. Make the Gate 7 checker compare the report to that reported length, not to a literal 4876 or 4818. Keep the two-column census tests passing."
    status: pending
    phase: execute
    depends_on: [T2]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Run the rehearsal kit on the checkout

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `run_the_rehearsal_kit_on_the_checkout_85e93b3e.plan.md`
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
| plan_id | `plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| name | Run the rehearsal kit on the checkout |
| overview | Make tests/production-rehearsal execute the go-live data sync on the code in the checkout that invokes it. A ready verdict means that sync completed. It does not mean Staging may be promoted. Branch name, equality with origin/Staging, a fetch failure, a dirty tree, a merge-tree conflict, and movement of Staging or Production during the run are recorded and do not fail or skip the sync. The kit stores no digest and no cohort size. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | workspace-operator |
| created_at | 2026-11-07T22:35:22+00:00 |
| updated_at | 2026-11-07T22:35:22+00:00 |
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
| captured_at | `2026-11-07T22:35:22+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `fix/vanillasoft-tracked-export` |
| commit_sha | `ca21e0093df264e514557fc9bfd9577391bc7f7b` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make tests/production-rehearsal execute the go-live data sync on the code in the checkout that invokes it. A ready verdict means that sync completed. It does not mean Staging may be promoted. Branch name, equality with origin/Staging, a fetch failure, a dirty tree, a merge-tree conflict, and movement of Staging or Production during the run are recorded and do not fail or skip the sync. The kit stores no digest and no cohort size.

### Scope in

- Kit identity, fetch, merge-tree, and remote-drift become evidence
- Gate 6 limit and the 10 percent wording in the ERP checker
- Gate 7 contact source, digest transport, and history cap
- historical_cohort.report cohort length for the census it was given
- SPEC, README, blockers, and the tests that lock the old pins

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: a non-Staging dirty checkout still runs past Gate 1 when origin cannot be fetched or origin/Staging moves, and the verdict does not contain not-on-staging, head-not-origin-staging, worktree-dirty, remote-fetch-failed, staging-ref-drifted, or production-ref-drifted | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` → all tests passed | `true` |
| SP-02 | V1: run.sh and common.py contain no 64-hex digest and no pass condition that the cohort is 4876 or 4818 | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` → all tests passed; V2: `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py` → hook catalog .pre-commit-config.yaml reports pass on those files | `true` |
| SP-03 | V1: Gate 6 invokes make import-erp with no LIMIT, and the ERP receipt scope is a full import | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` → all tests passed | `true` |
| SP-04 | V1: Gate 7 passes plasticos_crm_sync/Vanillasoft-Scrap-Management.csv from the checkout, with a run-time hash and no default history cap, and a missing file fails the gate | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` → all tests passed | `true` |
| SP-05 | V1: historical_cohort.report stamps the length of the census it was given, and the two-column 4876 census tests still pass | `quality_gate` | V1: `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` → all tests passed | `true` |
| SP-06 | V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml | `quality_gate` | V2: `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py` → hook catalog .pre-commit-config.yaml reports pass on those files | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| source_ref | `plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `bind checkout fix/vanillasoft-tracked-export at ca21e009; hook catalog .pre-commit-config.yaml` | branch and HEAD recorded; catalog file present | `true` |
| P1 | pre-validation (status `passed`) | `bash tests/production-rehearsal/run.sh` | evidence/2026-11-07_214831 verdict failed at Gate 1 not-on-staging and skipped Gates 2-7 | `true` |
| P2 | pre-validation (status `passed`) | `read SPEC.md execution table, common.py check_erp scope, and historical_cohort.report` | rehearsal is LIMIT=10% and a bounded sample; report stamps COHORT 4876; unset ERP_LIMIT is a full import | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/production-rehearsal/run.sh`, `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/expected/blockers.yaml`, `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py`, `tests/production-rehearsal/test_erp_census_source.py`, `plasticos_crm_sync/services/historical_cohort.py`, `tests/test_crm_history_cohort.py`
- **write_deny:** `plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q`, `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py`
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

- ready is this checkout's sync, not permission to promote Staging
- ODOO_STAGE=production and a production permit still fail before any import
- A call floor or contact floor still fails Gate 7
- The summary equation, duplicates, payload_kind database, and fidelity still fail Gate 6
- Web-lead receipt still requires decision hot and state intake_created
- A cutover database owned by another worktree is not replaced
- The two-column census loader still requires 4876 rows
- The harness still requires a census path, a sha256 argument, and a checkpoint; the kit supplies them at run time

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/run.sh tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/run.sh tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/expected/blockers.yaml tests/production-rehearsal/common.py tests/production-rehearsal/test_rehearsal_scripts.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_sync/services/historical_cohort.py tests/test_crm_history_cohort.py tests/production-rehearsal/common.py tests/production-rehearsal/test_rehearsal_kit_lib.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests/production-rehearsal` | `assurance` | `ready is this checkout's sync, not permission to promote Staging`, `ODOO_STAGE=production and a production permit still fail before any import`, `A call floor or contact floor still fails Gate 7`, `The summary equation, duplicates, payload_kind database, and fidelity still fail Gate 6`, `Web-lead receipt still requires decision hot and state intake_created`, `A cutover database owned by another worktree is not replaced`, `The two-column census loader still requires 4876 rows`, `The harness still requires a census path, a sha256 argument, and a checkpoint; the kit supplies them at run time` | `plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T2 | `tests/production-rehearsal` | `assurance` | `ready is this checkout's sync, not permission to promote Staging`, `ODOO_STAGE=production and a production permit still fail before any import`, `A call floor or contact floor still fails Gate 7`, `The summary equation, duplicates, payload_kind database, and fidelity still fail Gate 6`, `Web-lead receipt still requires decision hot and state intake_created`, `A cutover database owned by another worktree is not replaced`, `The two-column census loader still requires 4876 rows`, `The harness still requires a census path, a sha256 argument, and a checkpoint; the kit supplies them at run time` | `plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T3 | `tests/production-rehearsal` | `runtime` | `ready is this checkout's sync, not permission to promote Staging`, `ODOO_STAGE=production and a production permit still fail before any import`, `A call floor or contact floor still fails Gate 7`, `The summary equation, duplicates, payload_kind database, and fidelity still fail Gate 6`, `Web-lead receipt still requires decision hot and state intake_created`, `A cutover database owned by another worktree is not replaced`, `The two-column census loader still requires 4876 rows`, `The harness still requires a census path, a sha256 argument, and a checkpoint; the kit supplies them at run time` | `plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |
| T4 | `repository root` | `runtime` | `ready is this checkout's sync, not permission to promote Staging`, `ODOO_STAGE=production and a production permit still fail before any import`, `A call floor or contact floor still fails Gate 7`, `The summary equation, duplicates, payload_kind database, and fidelity still fail Gate 6`, `Web-lead receipt still requires decision hot and state intake_created`, `A cutover database owned by another worktree is not replaced`, `The two-column census loader still requires 4876 rows`, `The harness still requires a census path, a sha256 argument, and a checkpoint; the kit supplies them at run time` | `plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal`, `ci/check_banned_identifier.py`, `plasticos_transaction/`, `scripts/test_env.sh` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| source_execution_ref | `plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (a non-Staging fixture reaches the later gates and the production-stage refusal still fails) → stop before changing import volume or the history report; C2 fails (V1 passes, including the two-column census tests) → do not treat the kit as runnable |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the kit files and the report() length change. No schema migration and no production write. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q`
- re-run `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 4 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `medium` — A wrong contact file imports the wrong people. A full import-erp writes only the disposable cutover database. A report length change that breaks the two-column census fails V1. |
| architectural_boundaries_crossed | `rehearsal kit to make import-erp`, `rehearsal kit to make import-vanillasoft`, `history report length to the census it was given` |
| external_systems_touched | none |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Record branch, HEAD, dirty paths, the fetch result, the Production/Staging merge-tree, and the ending remote SHAs. Do not fail or skip later gates for not-on-staging, head-not-origin-staging, worktree-dirty, remote-fetch-failed, a merge-tree conflict, staging-ref-drifted, or production-ref-drifted. State in SPEC and README that ready means this checkout's sync completed, not that Staging may be promoted. Keep the production-stage, permit, secret-scan, install-smoke, cutover-ownership, and web-lead failures. | Cursor Build agent | `medium` | M | `[]` | `tests/production-rehearsal/run.sh`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py` |
| T2 | Point Gate 7 at plasticos_crm_sync/Vanillasoft-Scrap-Management.csv in the checkout. Hash that file at run time and pass the hash only because scripts/test_env.sh requires VANILLASOFT_HISTORY_CENSUS_SHA256. Store no digest in the kit. A missing file fails the gate. Do not pass VANILLASOFT_HISTORY_MAX_IDS unless REHEARSAL_HISTORY_MAX_IDS is already set. Remove the census-unbound and digest-unbound blocker entries. Keep the key-unbound blocker, the rolling-floor refusal, the production-permit refusal, and the kit's own evidence ledger. | Cursor Build agent | `medium` | M | `[T1]` | `tests/production-rehearsal/run.sh`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/expected/blockers.yaml`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/test_rehearsal_scripts.py` |
| T3 | Call make import-erp with no LIMIT. Unset ERP_LIMIT is the full import. Update the ERP receipt so its scope and execution_path no longer say 10 percent or not a full historical import. Keep the summary equation, duplicates, payload_kind database, fidelity, native-document checks, and the production-permit refusal. | Cursor Build agent | `medium` | M | `[T1]` | `tests/production-rehearsal/erp_slice.sh`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/SPEC.md`, `tests/production-rehearsal/README.md`, `tests/production-rehearsal/test_rehearsal_scripts.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py`, `tests/production-rehearsal/test_erp_census_source.py` |
| T4 | Make historical_cohort.report stamp the length of the census it was given, and judge completeness against that length. Do not change COHORT for the two-column loader or the tracked-export digest refusal. Make the Gate 7 checker compare the report to that reported length, not to a literal 4876 or 4818. Keep the two-column census tests passing. | Cursor Build agent | `medium` | M | `[T2]` | `plasticos_crm_sync/services/historical_cohort.py`, `tests/test_crm_history_cohort.py`, `tests/production-rehearsal/common.py`, `tests/production-rehearsal/test_rehearsal_kit_lib.py` |

**Critical path:** T1 → T2 → T4 → T3

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | Identity, fetch, and remote movement no longer fail or skip the sync, and ready is not a promotion approval | the import commands can be retargeted |
| M2 | ERP is a full import and VanillaSoft history follows the checkout file without a stored digest or cohort size | kit tests prove the contract |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | a non-Staging fixture reaches the later gates and the production-stage refusal still fails | stop before changing import volume or the history report |
| C2 | M2 | V1 passes, including the two-column census tests | do not treat the kit as runnable |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T4`, `T3`
- **Shared causes:** promotion identity used as a sync precondition; cohort size and the 10 percent slice copied into the kit
- **Deletions / consolidations:** Delete the fail-closed branch, HEAD-equality, dirty-tree, fetch, and remote-drift checks; Delete the kit-held digest, the default history cap, and the copied cohort size

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| tests/production-rehearsal/SPEC.md | `update` | `T1`, `T2`, `T3`, `T4` | — |
| tests/production-rehearsal/README.md | `update` | `T1`, `T2`, `T3` | — |
| AGENTS.md | `n_a` | — | BAN001 and the import commands stay. The kit contract is SPEC.md. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-02, SP-03, SP-04, SP-05 | `quality_gate_evidence` | command | `python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q` | all tests passed | `not_run` |
| E-V2 | SP-02, SP-06 | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py` | hook catalog .pre-commit-config.yaml reports pass on those files | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does a failed fetch or a Staging advance during the run still skip the remaining gates?
- Can a reader still treat verdict ready as permission to promote Staging?
- Does hashing the checkout file at run time become a second stored digest?
- Does report() still stamp 4876 when the file it was given has another length, so Gate 7 fails a completed sync?
- Does removing LIMIT also remove the summary equation, fidelity, or the production-permit refusal?

### Assumption failure conditions

- Go-live sync is the 10 percent slice plus a 100-contact cap
- The checkout must be named Staging before its own code can be imported
- The two-column census loader can drop its 4876 check because the report length changed

### Blast radius notes

- A wrong contact file imports the wrong people. A full import-erp writes only the disposable cutover database. A report length change that breaks the two-column census fails V1.

### Rollback constraints

- Revert the kit files and the report() length change. No schema migration and no production write.

### Risks

| risk | mitigation |
|------|------------|
| odoo_test_cutover is owned by another worktree, so a live run can still stop at the clone | Keep that ownership refusal. Prove the contract with the kit tests, not by taking the database. |
| Changing report() length breaks the two-column census | A 4876-row census still reports 4876 because that is its length. V1 includes tests/test_crm_history_cohort.py. |
| A full ERP import is long and compares every imported native document | That is the go-live command. The fidelity and summary checks stay fail-closed. |

## Out of scope

- TRACKED_EXPORT_SHA256 and load_tracked_export's digest refusal
- BAN001 and any rewrite of the customer export
- Historical accounting, payments, opening balances, and QuickBooks
- Replacing another worktree's odoo_test_cutover
- Deleting the production-stage, production-permit, rolling-floor, summary-equation, fidelity, or web-lead checks
- Publication
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
| source_ref | `plan.simple.run_the_rehearsal_kit_on_the_checkout.v1` |
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
| `open_blocker` | stop_reason | Revised plan is ready for Build. The kit has not been edited. | planning convergence `partial` |

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
  plan_id: "plan.simple.run_the_rehearsal_kit_on_the_checkout.v1"
  name: "Run the rehearsal kit on the checkout"
  overview: "Make tests/production-rehearsal execute the go-live data sync on the code in the checkout that invokes it. A ready verdict means that sync completed. It does not mean Staging may be promoted. Branch name, equality with origin/Staging, a fetch failure, a dirty tree, a merge-tree conflict, and movement of Staging or Production during the run are recorded and do not fail or skip the sync. The kit stores no digest and no cohort size."
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
  commit_sha: "ca21e0093df264e514557fc9bfd9577391bc7f7b"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make tests/production-rehearsal execute the go-live data sync on the code in the checkout that invokes it. A ready verdict means that sync completed. It does not mean Staging may be promoted. Branch name, equality with origin/Staging, a fetch failure, a dirty tree, a merge-tree conflict, and movement of Staging or Production during the run are recorded and do not fail or skip the sync. The kit stores no digest and no cohort size."
  success_properties:
    - id: "SP-01"
      property: "V1: a non-Staging dirty checkout still runs past Gate 1 when origin cannot be fetched or origin/Staging moves, and the verdict does not contain not-on-staging, head-not-origin-staging, worktree-dirty, remote-fetch-failed, staging-ref-drifted, or production-ref-drifted"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V1: run.sh and common.py contain no 64-hex digest and no pass condition that the cohort is 4876 or 4818"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-03"
      property: "V1: Gate 6 invokes make import-erp with no LIMIT, and the ERP receipt scope is a full import"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-04"
      property: "V1: Gate 7 passes plasticos_crm_sync/Vanillasoft-Scrap-Management.csv from the checkout, with a run-time hash and no default history cap, and a missing file fails the gate"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-05"
      property: "V1: historical_cohort.report stamps the length of the census it was given, and the two-column 4876 census tests still pass"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-06"
      property: "V2: the changed kit files pass the pre-commit catalog in .pre-commit-config.yaml"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/production-rehearsal/run.sh", "tests/production-rehearsal/erp_slice.sh", "tests/production-rehearsal/common.py", "tests/production-rehearsal/SPEC.md", "tests/production-rehearsal/README.md", "tests/production-rehearsal/expected/blockers.yaml", "tests/production-rehearsal/test_rehearsal_scripts.py", "tests/production-rehearsal/test_rehearsal_kit_lib.py", "tests/production-rehearsal/test_erp_census_source.py", "plasticos_crm_sync/services/historical_cohort.py", "tests/test_crm_history_cohort.py"]
    write_deny: ["plasticos_crm_sync/services/historical_cohort.py TRACKED_EXPORT_SHA256 and load_tracked_export digest refusal", "ci/check_banned_identifier.py", "plasticos_transaction/", "scripts/test_env.sh"]
  commands:
    allow: ["python3 -m pytest tests/production-rehearsal/test_rehearsal_scripts.py tests/production-rehearsal/test_rehearsal_kit_lib.py tests/production-rehearsal/test_erp_census_source.py tests/test_crm_history_cohort.py -q", "pre-commit run --config .pre-commit-config.yaml --files tests/production-rehearsal/run.sh tests/production-rehearsal/erp_slice.sh tests/production-rehearsal/common.py tests/production-rehearsal/SPEC.md tests/production-rehearsal/README.md plasticos_crm_sync/services/historical_cohort.py"]
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
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1"
dependency_topology_ref: "dag.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1"
validation_evidence_refs: ["E-V1", "E-V2"]
stress_and_disconfirm:
  disconfirming_cases: ["Does a failed fetch or a Staging advance during the run still skip the remaining gates?", "Can a reader still treat verdict ready as permission to promote Staging?", "Does hashing the checkout file at run time become a second stored digest?", "Does report() still stamp 4876 when the file it was given has another length, so Gate 7 fails a completed sync?", "Does removing LIMIT also remove the summary equation, fidelity, or the production-permit refusal?"]
  assumption_failure_conditions: ["Go-live sync is the 10 percent slice plus a 100-contact cap", "The checkout must be named Staging before its own code can be imported", "The two-column census loader can drop its 4876 check because the report length changed"]
out_of_scope: ["TRACKED_EXPORT_SHA256 and load_tracked_export's digest refusal", "BAN001 and any rewrite of the customer export", "Historical accounting, payments, opening balances, and QuickBooks", "Replacing another worktree's odoo_test_cutover", "Deleting the production-stage, production-permit, rolling-floor, summary-equation, fidelity, or web-lead checks", "Publication"]
convergence_contract_ref: "conv.plan.simple.run_the_rehearsal_kit_on_the_checkout.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Record branch, HEAD, dirty paths, the fetch result, the Production/Staging merge-tree, and the ending remote SHAs. Do not fail or skip later gates for not-on-staging, head-not-origin-staging, worktree-dirty, remote-fetch-failed, a merge-tree conflict, staging-ref-drifted, or production-ref-drifted. State in SPEC and README that ready means this checkout's sync completed, not that Staging may be promoted. Keep the production-stage, permit, secret-scan, install-smoke, cutover-ownership, and web-lead failures."
    status: "pending"
  - id: "T2"
    content: "Point Gate 7 at plasticos_crm_sync/Vanillasoft-Scrap-Management.csv in the checkout. Hash that file at run time and pass the hash only because scripts/test_env.sh requires VANILLASOFT_HISTORY_CENSUS_SHA256. Store no digest in the kit. A missing file fails the gate. Do not pass VANILLASOFT_HISTORY_MAX_IDS unless REHEARSAL_HISTORY_MAX_IDS is already set. Remove the census-unbound and digest-unbound blocker entries. Keep the key-unbound blocker, the rolling-floor refusal, the production-permit refusal, and the kit's own evidence ledger."
    status: "pending"
  - id: "T3"
    content: "Call make import-erp with no LIMIT. Unset ERP_LIMIT is the full import. Update the ERP receipt so its scope and execution_path no longer say 10 percent or not a full historical import. Keep the summary equation, duplicates, payload_kind database, fidelity, native-document checks, and the production-permit refusal."
    status: "pending"
  - id: "T4"
    content: "Make historical_cohort.report stamp the length of the census it was given, and judge completeness against that length. Do not change COHORT for the two-column loader or the tracked-export digest refusal. Make the Gate 7 checker compare the report to that reported length, not to a literal 4876 or 4818. Keep the two-column census tests passing."
    status: "pending"
```
