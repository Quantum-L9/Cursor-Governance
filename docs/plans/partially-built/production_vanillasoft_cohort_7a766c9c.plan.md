---
name: Start the Production VanillaSoft contact import
overview: Change make import-vanillasoft and the shell it pipes so Production installs plasticos_crm_sync, binds the VanillaSoft API key, and fetches every ContactID named by Vanillasoft-Scrap-Management.csv plus the packaged approved crosswalk. MEMORY_PREFETCH .l9/memory/plan-prefetch.json status OK namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f con...
todos:
  - id: T1
    content: Add repository-cohort mode to make import-vanillasoft. When VANILLASOFT_CONTACT_EXPORT is set, refuse a call floor and a history census. Copy the export. Create the ledger parent. Install plasticos_crm_sync on the production database when ir_module_module.state is not installed. Put VANILLASOFT_API_KEY into the remote env file with printf %q and never echo it. Require VANILLASOFT_PRODUCTION_CONFIRM=1 for this mode. Leave MAX_IDS empty.
    status: completed
  - id: T2
    content: "In the piped shell, when the export path is set, build the census in the shell: every export ContactID, plus crosswalk ids missing from the export. Mark crosswalk ids and the four omitted duplicates YES. Mark every other id PENDING. Do not call load_census. verify_identity still runs against the server crosswalk. Replace the commercial-phase refusal with a same-database erp_partners witness whose final_status is not failed, and keep the partner_count_after_contacts check. When the API key parameter is empty, write VANILLASOFT_API_KEY into plasticos_crm_sync.vanillasoft_api_key. When the incremental cron is active, set it inactive before the fetch. When VANILLASOFT_PRODUCTION_CONFIRM=1 and no permit file is present, write a crm_history permit bound to the observed database uuid, release SHA, and generated census SHA-256, expiring inside 24 hours, then consume it through the existing one-use insert."
    status: completed
  - id: T3
    content: Add shell tests that the repository cohort contains the export ids plus the missing crosswalk ids, skips only the four omitted duplicates, refuses a failed erp_partners witness, accepts a partial erp_partners witness, and refuses a production confirm that does not mint a matching permit. Keep the existing 4876 census tests passing.
    status: completed
  - id: T4
    content: Run the production import with the tracked export, ledger .l9/pr/vanillasoft-production-ledger.jsonl, and VANILLASOFT_PRODUCTION_CONFIRM=1. No MAX_IDS. Stop only if the shell refuses before the first fetch.
    status: in_progress
isProject: false
status: partially-built
---

# PLAN: Start the Production VanillaSoft contact import

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `start_the_production_vanillasoft_contact_import_48e8e0ee.plan.md`
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
| plan_id | `plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| name | Start the Production VanillaSoft contact import |
| overview | Change make import-vanillasoft and the shell it pipes so Production installs plasticos_crm_sync, binds the VanillaSoft API key, and fetches every ContactID named by Vanillasoft-Scrap-Management.csv plus the packaged approved crosswalk. MEMORY_PREFETCH .l9/memory/plan-prefetch.json status OK namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f conflicts 0. Route depth deep. The piped shell is the file Production executes; historical_cohort.py on the server stays the current Production copy. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-09T21:29:50+00:00 |
| updated_at | 2026-11-09T21:29:50+00:00 |
| depth | `deep` |
| estimate | one session |

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
| captured_at | `2026-11-09T21:29:50+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `feat/erp-company-role-tags` |
| commit_sha | `7a766c9cc8d10b9c59d8e8f536ae18ced4f30b53` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Change make import-vanillasoft and the shell it pipes so Production installs plasticos_crm_sync, binds the VanillaSoft API key, and fetches every ContactID named by Vanillasoft-Scrap-Management.csv plus the packaged approved crosswalk. MEMORY_PREFETCH .l9/memory/plan-prefetch.json status OK namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f conflicts 0. Route depth deep. The piped shell is the file Production executes; historical_cohort.py on the server stays the current Production copy.

### Scope in

- Makefile import-vanillasoft: install plasticos_crm_sync when it is not installed, copy the tracked export, inject the API key without printing it, and select the repository cohort
- plasticos_crm_sync/scripts/import_vanillasoft_shell.py: build the cohort from the export plus the crosswalk, accept a committed partner phase, mint the confirm permit, set the API key parameter when empty, and deactivate the incremental cron if it is active
- tests/test_crm_history_cohort.py for those driver branches

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: python3 -m pytest tests/test_crm_history_cohort.py -q passes, including repository-cohort census construction, the partner-phase gate, and the one-use confirm permit | `quality_gate` | V1: `python3 -m pytest tests/test_crm_history_cohort.py -q` → exit 0 and the new repository-cohort, partner-phase, and confirm-permit tests pass; V3: `pre-commit run --config .pre-commit-config.yaml --files Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py tests/test_crm_history_cohort.py` → hook catalog .pre-commit-config.yaml reports pass on the changed files | `true` |
| SP-02 | V2: make import-vanillasoft with the repository export, a durable ledger, and VANILLASOFT_PRODUCTION_CONFIRM=1 prints crm_history.admitted and progress fetched=25 on cryptoxdog-ib-odoo-19-production-29882273 | `quality_gate` | V2: `make import-vanillasoft VANILLASOFT_CONTACT_EXPORT=plasticos_crm_sync/Vanillasoft-Scrap-Management.csv VANILLASOFT_HISTORY_CHECKPOINT=.l9/pr/vanillasoft-production-ledger.jsonl VANILLASOFT_PRODUCTION_CONFIRM=1` → shell output contains crm_history.admitted and progress fetched=25 | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.start_the_production_vanillasoft_contact_import.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| source_ref | `plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `MEMORY_PREFETCH .l9/memory/plan-prefetch.json and python3 skills/l9-plan/scripts/route_plan.py --risk irreversible --evidence partial` | prefetch status OK conflicts 0; route depth deep; omit_gates empty | `true` |
| P1 | pre-validation (status `passed`) | `bind feat/erp-company-role-tags at 7a766c9c; hook catalog .pre-commit-config.yaml` | HEAD is 7a766c9c and the Makefile SSH target is the only import change in that commit | `true` |
| P2 | pre-validation (status `passed`) | `count ContactIDs in plasticos_crm_sync/Vanillasoft-Scrap-Management.csv and plasticos_crm_sync/data/approved_contact_crosswalk.csv` | export unique ContactIDs 4818; crosswalk 759; 757 overlap; 2 crosswalk ids absent from the export; 4 omitted duplicates present; union 4820 | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `Makefile`, `plasticos_crm_sync/scripts/import_vanillasoft_shell.py`, `tests/test_crm_history_cohort.py`
- **write_deny:** `plasticos_partner_import/`, `plasticos_crm_sync/services/historical_cohort.py`, `docs/evidence/import-commercial-census.json`, `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`, `plasticos_crm_sync/data/approved_contact_crosswalk.csv`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/test_crm_history_cohort.py -q`, `make import-vanillasoft VANILLASOFT_CONTACT_EXPORT=plasticos_crm_sync/Vanillasoft-Scrap-Management.csv VANILLASOFT_HISTORY_CHECKPOINT=.l9/pr/vanillasoft-production-ledger.jsonl VANILLASOFT_PRODUCTION_CONFIRM=1`, `pre-commit run --config .pre-commit-config.yaml --files Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py tests/test_crm_history_cohort.py`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `Odoo.sh production SSH`, `VanillaSoft HTTPS API` |

### Secrets

| Field | Value |
|-------|-------|
| access | `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- 4876 load_census partition stays intact for an explicit VANILLASOFT_HISTORY_CENSUS
- four omitted duplicate YES ids are not fetched
- YES binds only through the packaged crosswalk
- one-use permit consumption stays an atomic insert
- API key value is never printed

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `non_idempotent` | `manual_only` | `git restore -- Makefile` | `true` |
| T2 | `filesystem_mutation` | `non_idempotent` | `manual_only` | `git restore -- plasticos_crm_sync/scripts/import_vanillasoft_shell.py` | `true` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_crm_history_cohort.py` | `false` |
| T4 | `filesystem_mutation` | `non_idempotent` | `manual_only` | `git restore -- Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py` | `true` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `repository root` | `ops` | `4876 load_census partition stays intact for an explicit VANILLASOFT_HISTORY_CENSUS`, `four omitted duplicate YES ids are not fetched`, `YES binds only through the packaged crosswalk`, `one-use permit consumption stays an atomic insert`, `API key value is never printed` | `plasticos_partner_import/`, `plasticos_crm_sync/services/historical_cohort.py`, `docs/evidence/import-commercial-census.json`, `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`, `plasticos_crm_sync/data/approved_contact_crosswalk.csv` |
| T2 | `plasticos_crm_sync/scripts` | `runtime` | `4876 load_census partition stays intact for an explicit VANILLASOFT_HISTORY_CENSUS`, `four omitted duplicate YES ids are not fetched`, `YES binds only through the packaged crosswalk`, `one-use permit consumption stays an atomic insert`, `API key value is never printed` | `plasticos_partner_import/`, `plasticos_crm_sync/services/historical_cohort.py`, `docs/evidence/import-commercial-census.json`, `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`, `plasticos_crm_sync/data/approved_contact_crosswalk.csv` |
| T3 | `tests` | `assurance` | `4876 load_census partition stays intact for an explicit VANILLASOFT_HISTORY_CENSUS`, `four omitted duplicate YES ids are not fetched`, `YES binds only through the packaged crosswalk`, `one-use permit consumption stays an atomic insert`, `API key value is never printed` | `plasticos_partner_import/`, `plasticos_crm_sync/services/historical_cohort.py`, `docs/evidence/import-commercial-census.json`, `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`, `plasticos_crm_sync/data/approved_contact_crosswalk.csv` |
| T4 | `repository root` | `external_system` | `4876 load_census partition stays intact for an explicit VANILLASOFT_HISTORY_CENSUS`, `four omitted duplicate YES ids are not fetched`, `YES binds only through the packaged crosswalk`, `one-use permit consumption stays an atomic insert`, `API key value is never printed` | `plasticos_partner_import/`, `plasticos_crm_sync/services/historical_cohort.py`, `docs/evidence/import-commercial-census.json`, `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`, `plasticos_crm_sync/data/approved_contact_crosswalk.csv` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.start_the_production_vanillasoft_contact_import.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| source_execution_ref | `plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | C1 fails (V1 pytest exit 0) → do not open the production SSH import; C2 fails (crm_history.admitted and progress fetched=25 in the production shell output) → stop the shell, keep the ledger, and read the refusal or the first ledger class before another session |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Stop the shell. Leave the ledger in place. Do not drop the module. A later session resumes the same export and ledger; already durable external refs are not fetched again. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- T1: Add repository-cohort mode to make import-vanillasoft. When VANILLASOFT_CONTACT_EXPORT is set, refuse a call floor and a history census. Copy the export. Create the ledger parent. Install plasticos_crm_sync on the production database when ir_module_module.state is not installed. Put VANILLASOFT_API_KEY into the remote env file with printf %q and never echo it. Require VANILLASOFT_PRODUCTION_CONFIRM=1 for this mode. Leave MAX_IDS empty.
- T2: In the piped shell, when the export path is set, build the census in the shell: every export ContactID, plus crosswalk ids missing from the export. Mark crosswalk ids and the four omitted duplicates YES. Mark every other id PENDING. Do not call load_census. verify_identity still runs against the server crosswalk. Replace the commercial-phase refusal with a same-database erp_partners witness whose final_status is not failed, and keep the partner_count_after_contacts check. When the API key parameter is empty, write VANILLASOFT_API_KEY into plasticos_crm_sync.vanillasoft_api_key. When the incremental cron is active, set it inactive before the fetch. When VANILLASOFT_PRODUCTION_CONFIRM=1 and no permit file is present, write a crm_history permit bound to the observed database uuid, release SHA, and generated census SHA-256, expiring inside 24 hours, then consume it through the existing one-use insert.
- T4: Run the production import with the tracked export, ledger .l9/pr/vanillasoft-production-ledger.jsonl, and VANILLASOFT_PRODUCTION_CONFIRM=1. No MAX_IDS. Stop only if the shell refuses before the first fetch.

### Rollback verification

- re-run `python3 -m pytest tests/test_crm_history_cohort.py -q`
- re-run `make import-vanillasoft VANILLASOFT_CONTACT_EXPORT=plasticos_crm_sync/Vanillasoft-Scrap-Management.csv VANILLASOFT_HISTORY_CHECKPOINT=.l9/pr/vanillasoft-production-ledger.jsonl VANILLASOFT_PRODUCTION_CONFIRM=1`
- re-run `pre-commit run --config .pre-commit-config.yaml --files Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py tests/test_crm_history_cohort.py`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `critical` — highest todo risk across 4 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `critical` — Production gains the plasticos_crm_sync schema and one fetched contact writes a crm.lead or binds a res.partner. The ledger is the resume record. Commercial documents are not rewritten. |
| architectural_boundaries_crossed | `local make process to Odoo.sh production database`, `piped shell to the Production addon registry` |
| external_systems_touched | `Odoo.sh production`, `VanillaSoft` |
| migration_required | `true` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Activated — irreversible todo(s): T1, T2, T4.

- **gates (ordered):**
  1. human approval recorded for T1, T2, T4 before any of them runs
  2. every blocking capability probe and earlier checkpoint has passed
  3. the exact write is previewed (dry run or diff) and reviewed
  4. the write executes once
  5. a receipt of the write is recorded before the next todo starts
- **dedupe_before_non_idempotent_write:** `true`
- **bounded_write_count:** `3` — one attempt per irreversible todo; retry is `manual_only`
- **receipt_required:** `true`

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.start_the_production_vanillasoft_contact_import.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Add repository-cohort mode to make import-vanillasoft. When VANILLASOFT_CONTACT_EXPORT is set, refuse a call floor and a history census. Copy the export. Create the ledger parent. Install plasticos_crm_sync on the production database when ir_module_module.state is not installed. Put VANILLASOFT_API_KEY into the remote env file with printf %q and never echo it. Require VANILLASOFT_PRODUCTION_CONFIRM=1 for this mode. Leave MAX_IDS empty. | Cursor Build agent | `irreversible` | M | `[]` | `Makefile` |
| T2 | In the piped shell, when the export path is set, build the census in the shell: every export ContactID, plus crosswalk ids missing from the export. Mark crosswalk ids and the four omitted duplicates YES. Mark every other id PENDING. Do not call load_census. verify_identity still runs against the server crosswalk. Replace the commercial-phase refusal with a same-database erp_partners witness whose final_status is not failed, and keep the partner_count_after_contacts check. When the API key parameter is empty, write VANILLASOFT_API_KEY into plasticos_crm_sync.vanillasoft_api_key. When the incremental cron is active, set it inactive before the fetch. When VANILLASOFT_PRODUCTION_CONFIRM=1 and no permit file is present, write a crm_history permit bound to the observed database uuid, release SHA, and generated census SHA-256, expiring inside 24 hours, then consume it through the existing one-use insert. | Cursor Build agent | `irreversible` | L | `[T1]` | `plasticos_crm_sync/scripts/import_vanillasoft_shell.py` |
| T3 | Add shell tests that the repository cohort contains the export ids plus the missing crosswalk ids, skips only the four omitted duplicates, refuses a failed erp_partners witness, accepts a partial erp_partners witness, and refuses a production confirm that does not mint a matching permit. Keep the existing 4876 census tests passing. | Cursor Build agent | `medium` | M | `[T2]` | `tests/test_crm_history_cohort.py` |
| T4 | Run the production import with the tracked export, ledger .l9/pr/vanillasoft-production-ledger.jsonl, and VANILLASOFT_PRODUCTION_CONFIRM=1. No MAX_IDS. Stop only if the shell refuses before the first fetch. | Cursor Build agent | `irreversible` | L | `[T3]` | `Makefile`, `plasticos_crm_sync/scripts/import_vanillasoft_shell.py` |

**Critical path:** T1 → T2 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The piped shell can admit the 4820-id repository cohort on a partner-phase database | T4 production fetch |
| M2 | Production has started fetching ContactIDs and the ledger is appending | resume from the same ledger if the failure budget stops the session |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T3 | V1 pytest exit 0 | do not open the production SSH import |
| C2 | T4 | crm_history.admitted and progress fetched=25 in the production shell output | stop the shell, keep the ledger, and read the refusal or the first ledger class before another session |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`
- **Shared causes:** the wrapper cannot start a contact fetch from the files the repository already has
- **Deletions / consolidations:** the contact run no longer treats a failed erp_commercial witness as a contact-import refusal

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The command name stays make import-vanillasoft. Root agent docs are append-only and this change is the Makefile contract plus the piped shell. |
| workflow_state.md | `n_a` | — | The production ledger and summary are the run evidence. This plan does not edit the operational state page. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_crm_history_cohort.py -q` | exit 0 and the new repository-cohort, partner-phase, and confirm-permit tests pass | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `make import-vanillasoft VANILLASOFT_CONTACT_EXPORT=plasticos_crm_sync/Vanillasoft-Scrap-Management.csv VANILLASOFT_HISTORY_CHECKPOINT=.l9/pr/vanillasoft-production-ledger.jsonl VANILLASOFT_PRODUCTION_CONFIRM=1` | shell output contains crm_history.admitted and progress fetched=25 | `not_run` |
| E-V3 | SP-01 | `quality_gate_evidence` | command | `pre-commit run --config .pre-commit-config.yaml --files Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py tests/test_crm_history_cohort.py` | hook catalog .pre-commit-config.yaml reports pass on the changed files | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does a failed erp_commercial witness still stop the shell after T2?
- Does the generated YES set differ from the server crosswalk plus the four omitted duplicates?
- Does the env file echo the API key?
- Does installing plasticos_crm_sync leave cron_crm_sync_all active and block the history lock?
- Does the run set VANILLASOFT_HISTORY_MAX_IDS and stop after a sample?

### Assumption failure conditions

- The tracked export is the frozen 4876 census
- A commercial payment-term failure means the partner book cannot bind YES contacts
- Editing historical_cohort.py locally changes the module Production imports

### Blast radius notes

- Production gains the plasticos_crm_sync schema and one fetched contact writes a crm.lead or binds a res.partner. The ledger is the resume record. Commercial documents are not rewritten.

### Rollback constraints

- Stop the shell. Leave the ledger in place. Do not drop the module. A later session resumes the same export and ledger; already durable external refs are not fetched again.

### Risks

| risk | mitigation |
|------|------------|
| The server crosswalk differs from the local 759-row file and verify_identity refuses | Compare the file hash over SSH before the fetch. On mismatch, copy the local crosswalk path into the shell input instead of the server parameter. |
| Module install or the first fetches run long enough for the SSH session to drop | Keep ServerAliveInterval 30 and resume from the same ledger. Do not pass MAX_IDS. |

## Out of scope

- Rewriting the ERP commercial import or editing docs/evidence/import-commercial-census.json
- Changing historical_cohort.py COHORT or PARTITION on the server
- Inventing the 56 ContactIDs that are in neither the tracked export nor the crosswalk
- A rolling-window call floor
- VANILLASOFT_HISTORY_MAX_IDS on this run
- Pushing feat/erp-company-role-tags or merging to Production
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.start_the_production_vanillasoft_contact_import.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.start_the_production_vanillasoft_contact_import.v1` |
| source_ref | `plan.simple.start_the_production_vanillasoft_contact_import.v1` |
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
| `unknown` | U1 | Which 56 ContactIDs of the old 4876 freeze are absent from the export and the crosswalk? — Those ids are not fetched. The run covers the 4820 ids the repository can name. | `accept_bounded` |
| `open_blocker` | stop_reason | U1 is accepted as bounded. Build executes T1 through T4. | planning convergence `partial` |

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
  plan_id: "plan.simple.start_the_production_vanillasoft_contact_import.v1"
  name: "Start the Production VanillaSoft contact import"
  overview: "Change make import-vanillasoft and the shell it pipes so Production installs plasticos_crm_sync, binds the VanillaSoft API key, and fetches every ContactID named by Vanillasoft-Scrap-Management.csv plus the packaged approved crosswalk. MEMORY_PREFETCH .l9/memory/plan-prefetch.json status OK namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f conflicts 0. Route depth deep. The piped shell is the file Production executes; historical_cohort.py on the server stays the current Production copy."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "7a766c9cc8d10b9c59d8e8f536ae18ced4f30b53"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Change make import-vanillasoft and the shell it pipes so Production installs plasticos_crm_sync, binds the VanillaSoft API key, and fetches every ContactID named by Vanillasoft-Scrap-Management.csv plus the packaged approved crosswalk. MEMORY_PREFETCH .l9/memory/plan-prefetch.json status OK namespace ib-odoo-19 snapshot_digest d5dad630493379a8f4bfdc046c4abbb08befd4954f823755cff68775cf45733f conflicts 0. Route depth deep. The piped shell is the file Production executes; historical_cohort.py on the server stays the current Production copy."
  success_properties:
    - id: "SP-01"
      property: "V1: python3 -m pytest tests/test_crm_history_cohort.py -q passes, including repository-cohort census construction, the partner-phase gate, and the one-use confirm permit"
      evidence_type: "quality_gate"
      proof: ["V1", "V3"]
      blocking: true
    - id: "SP-02"
      property: "V2: make import-vanillasoft with the repository export, a durable ledger, and VANILLASOFT_PRODUCTION_CONFIRM=1 prints crm_history.admitted and progress fetched=25 on cryptoxdog-ib-odoo-19-production-29882273"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.start_the_production_vanillasoft_contact_import.v1"
execution_envelope:
  filesystem:
    write_allow: ["Makefile", "plasticos_crm_sync/scripts/import_vanillasoft_shell.py", "tests/test_crm_history_cohort.py"]
    write_deny: ["plasticos_partner_import/", "plasticos_crm_sync/services/historical_cohort.py", "docs/evidence/import-commercial-census.json", "plasticos_crm_sync/Vanillasoft-Scrap-Management.csv", "plasticos_crm_sync/data/approved_contact_crosswalk.csv"]
  commands:
    allow: ["python3 -m pytest tests/test_crm_history_cohort.py -q", "make import-vanillasoft VANILLASOFT_CONTACT_EXPORT=plasticos_crm_sync/Vanillasoft-Scrap-Management.csv VANILLASOFT_HISTORY_CHECKPOINT=.l9/pr/vanillasoft-production-ledger.jsonl VANILLASOFT_PRODUCTION_CONFIRM=1", "pre-commit run --config .pre-commit-config.yaml --files Makefile plasticos_crm_sync/scripts/import_vanillasoft_shell.py tests/test_crm_history_cohort.py"]
  network:
    mode: "bounded_external_write"
  secrets:
    access: "runtime_injected_only"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "non_idempotent"
    retry: "manual_only"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "non_idempotent"
    retry: "manual_only"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "filesystem_mutation"
    idempotency: "non_idempotent"
    retry: "manual_only"
rollback_contract_ref: "rollback.plan.simple.start_the_production_vanillasoft_contact_import.v1"
dependency_topology_ref: "dag.plan.simple.start_the_production_vanillasoft_contact_import.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3"]
stress_and_disconfirm:
  disconfirming_cases: ["Does a failed erp_commercial witness still stop the shell after T2?", "Does the generated YES set differ from the server crosswalk plus the four omitted duplicates?", "Does the env file echo the API key?", "Does installing plasticos_crm_sync leave cron_crm_sync_all active and block the history lock?", "Does the run set VANILLASOFT_HISTORY_MAX_IDS and stop after a sample?"]
  assumption_failure_conditions: ["The tracked export is the frozen 4876 census", "A commercial payment-term failure means the partner book cannot bind YES contacts", "Editing historical_cohort.py locally changes the module Production imports"]
out_of_scope: ["Rewriting the ERP commercial import or editing docs/evidence/import-commercial-census.json", "Changing historical_cohort.py COHORT or PARTITION on the server", "Inventing the 56 ContactIDs that are in neither the tracked export nor the crosswalk", "A rolling-window call floor", "VANILLASOFT_HISTORY_MAX_IDS on this run", "Pushing feat/erp-company-role-tags or merging to Production"]
convergence_contract_ref: "conv.plan.simple.start_the_production_vanillasoft_contact_import.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Add repository-cohort mode to make import-vanillasoft. When VANILLASOFT_CONTACT_EXPORT is set, refuse a call floor and a history census. Copy the export. Create the ledger parent. Install plasticos_crm_sync on the production database when ir_module_module.state is not installed. Put VANILLASOFT_API_KEY into the remote env file with printf %q and never echo it. Require VANILLASOFT_PRODUCTION_CONFIRM=1 for this mode. Leave MAX_IDS empty."
    status: "pending"
  - id: "T2"
    content: "In the piped shell, when the export path is set, build the census in the shell: every export ContactID, plus crosswalk ids missing from the export. Mark crosswalk ids and the four omitted duplicates YES. Mark every other id PENDING. Do not call load_census. verify_identity still runs against the server crosswalk. Replace the commercial-phase refusal with a same-database erp_partners witness whose final_status is not failed, and keep the partner_count_after_contacts check. When the API key parameter is empty, write VANILLASOFT_API_KEY into plasticos_crm_sync.vanillasoft_api_key. When the incremental cron is active, set it inactive before the fetch. When VANILLASOFT_PRODUCTION_CONFIRM=1 and no permit file is present, write a crm_history permit bound to the observed database uuid, release SHA, and generated census SHA-256, expiring inside 24 hours, then consume it through the existing one-use insert."
    status: "pending"
  - id: "T3"
    content: "Add shell tests that the repository cohort contains the export ids plus the missing crosswalk ids, skips only the four omitted duplicates, refuses a failed erp_partners witness, accepts a partial erp_partners witness, and refuses a production confirm that does not mint a matching permit. Keep the existing 4876 census tests passing."
    status: "pending"
  - id: "T4"
    content: "Run the production import with the tracked export, ledger .l9/pr/vanillasoft-production-ledger.jsonl, and VANILLASOFT_PRODUCTION_CONFIRM=1. No MAX_IDS. Stop only if the shell refuses before the first fetch."
    status: "pending"
```
