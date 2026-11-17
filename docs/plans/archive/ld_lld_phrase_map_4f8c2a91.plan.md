---
name: LD LLD phrase map
overview: "On a new branch from feat/seed-five-polymers at 093a2813, add nine exact worksheet phrases to _SPECS and the same nine material_mapping.csv rows as mapped names_one_polymer. Seven LD/LLD phrases resolve to LDPE_LLDPE, with a second master only when the phrase names one seeded value. spc-a resolves to PP, grade TUBS_LIDS, source POST_CONSUMER, packaging bales. new opti bins resolves to HDPE, gra..."
todos:
  - id: T1
    content: "Create a child branch from 093a2813 and add the nine exact _SPECS entries: seven LD/LLD phrases to LDPE_LLDPE with the named secondary masters, spc-a to PP TUBS_LIDS POST_CONSUMER packaging bales, and new opti bins to HDPE CRATES."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Set those nine material_mapping.csv rows to mapped names_one_polymer with the same polymer, grade, form, source, attribute, color, and packaging cells. Do not rebuild the matrix."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Assert worksheet resolution for the nine phrases and that a bare buckets phrase has no polymer. Bump plasticos_material_profile to 19.0.5.11.19 in the manifest and the README module_version."
    status: pending
    phase: execute
    depends_on: [T1, T2]
isProject: false
kind: simple
execute_via: cursor-build
status: current
kernel_pass:
  bound_path: /Users/ib-mac/Cursor-Governance/docs/plans/ld_lld_phrase_map_4f8c2a91.plan.md
  improve:
    ran_at: "2026-11-11T22:24:10+00:00"
    deltas:
      - "Bound the written plan and recorded that an empty pull-request board does not authorize a branch from Staging."
  recursive_alignment:
    ran_at: "2026-11-11T22:24:20+00:00"
    deltas:
      - "Aligned execution with the objective parent feat/seed-five-polymers at 093a2813."
  validate_repair:
    ran_at: "2026-11-11T22:24:30+00:00"
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Corrected the projected file name to ld_lld_phrase_map_4f8c2a91.plan.md."
---

# PLAN: LD LLD phrase map

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `ld_lld_phrase_map_4f8c2a91.plan.md`
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

This build starts at feat/seed-five-polymers `093a2813`. An empty pull-request board is a blocker for branching from Staging, because these phrases depend on that unpushed seed. Publication is `make pr base=feat/seed-five-polymers` only after that parent pull request exists.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.ld_lld_phrase_map.v1` |
| name | LD LLD phrase map |
| overview | On a new branch from feat/seed-five-polymers at 093a2813, add nine exact worksheet phrases to _SPECS and the same nine material_mapping.csv rows as mapped names_one_polymer. Seven LD/LLD phrases resolve to LDPE_LLDPE, with a second master only when the phrase names one seeded value. spc-a resolves to PP, grade TUBS_LIDS, source POST_CONSUMER, packaging bales. new opti bins resolves to HDPE, grade CRATES. A grade-only phrase still has no polymer. The ledger hold stays. plasticos_material_profile becomes 19.0.5.11.19. Publication waits until feat/seed-five-polymers has an open pull request, then make pr base=feat/seed-five-polymers. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-11T22:23:51+00:00 |
| updated_at | 2026-11-11T22:23:51+00:00 |
| depth | `standard` |
| estimate | S |

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
| captured_at | `2026-11-11T22:23:51+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `docs/candidate-add-ons` |
| commit_sha | `6959f249e82944ae8ef8588cddf0060072b35595` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

On a new branch from feat/seed-five-polymers at 093a2813, add nine exact worksheet phrases to _SPECS and the same nine material_mapping.csv rows as mapped names_one_polymer. Seven LD/LLD phrases resolve to LDPE_LLDPE, with a second master only when the phrase names one seeded value. spc-a resolves to PP, grade TUBS_LIDS, source POST_CONSUMER, packaging bales. new opti bins resolves to HDPE, grade CRATES. A grade-only phrase still has no polymer. The ledger hold stays. plasticos_material_profile becomes 19.0.5.11.19. Publication waits until feat/seed-five-polymers has an open pull request, then make pr base=feat/seed-five-polymers.

### Scope in

- Nine _SPECS keys in plasticos_material_profile/models/material_normalizer.py
- The same nine rows in plasticos_material_profile/data/material_mapping.csv set to mapped and names_one_polymer
- Worksheet assertions in plasticos_material_profile/tests/test_material_normalizer.py
- Version 19.0.5.11.19 in plasticos_material_profile/__manifest__.py and the README module_version
- A child branch of feat/seed-five-polymers at 093a2813

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves each of the nine phrases resolves through normalize_material with crm_aliases left false, including the grade, form, color, source, attribute, and packaging named for that phrase. | `quality_gate` | V1: `plasticos_material_profile/tests/test_material_normalizer.py` → Each of the nine phrases resolves on the worksheet call with the polymer and the secondary masters named in the objective. | `true` |
| SP-02 | V2 proves a bare buckets phrase still has no polymer. | `quality_gate` | V2: `plasticos_material_profile/tests/test_material_normalizer.py` → A bare buckets phrase has no polymer. | `true` |
| SP-03 | V3 proves the nine material_mapping.csv rows are mapped names_one_polymer with the same cells, and tests/test_material_ledger_resolution.py still applies 16 ledger rows. | `quality_gate` | V3: `tests/test_material_ledger_resolution.py` → The ledger test still applies 16 rows, and the nine matrix rows are mapped names_one_polymer. | `true` |
| SP-04 | V4 proves plasticos_material_profile is 19.0.5.11.19 in the manifest and the README module_version, and .pre-commit-config.yaml remains the hook catalog. | `quality_gate` | V4: `.pre-commit-config.yaml` → The manifest and README module_version are 19.0.5.11.19, and the changed Python is formatted with the repo ruff pin. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.ld_lld_phrase_map.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.ld_lld_phrase_map.v1` |
| source_ref | `plan.simple.ld_lld_phrase_map.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.ld_lld_phrase_map.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git status and git rev-parse on the workspace` | Branch feat/seed-five-polymers at 093a2813. The only untracked path is docs/campaigns/candidate-add-ons/, which this change does not add. No open pull request exists for the parent. | `true` |
| P1 | pre-validation (status `passed`) | `Read _SPECS, the seven LD/LLD matrix rows, spc-a, new opti bins, and the ledger hold` | normalize_material without crm_aliases reads _SPECS only. The seven phrases and the two named rows are unknown. ld/lldpe thick/stretch is already LDPE_LLDPE. OPERATOR_HOLDS keeps ldpe/lldpe clear repro. | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk low --evidence sufficient --json` | depth standard and omit_gates empty. Hook catalog is .pre-commit-config.yaml. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/data/material_mapping.csv`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_material_profile/README.md`
- **write_deny:** `plasticos_crm_sync/services/orchestrator.py`, `Makefile`, `plasticos_facility_profile/migrations/19.0.5.4.12/pre-migrate.py`, `plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv`, `plasticos_material_profile/data/material_mapping_resolution_remaining.csv`, `tests/test_material_ledger_resolution.py`, `pipeline_v2.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `.venv/bin/python -m pytest plasticos_material_profile/tests/test_material_normalizer.py tests/test_material_mapping_masters.py tests/test_material_ledger_resolution.py`, `.venv/bin/ruff check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py`, `.venv/bin/ruff format --check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `tests/test_material_ledger_resolution.py`, `.pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `github` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- OPERATOR_HOLDS keeps ldpe/lldpe clear repro
- Grade-only phrases do not receive a polymer
- make import-erp and make import-vanillasoft are not run and their targets stay unchanged

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_normalizer.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/data/material_mapping.csv` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/tests/test_material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/README.md` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `plasticos_material_profile/models` | `runtime` | `OPERATOR_HOLDS keeps ldpe/lldpe clear repro`, `Grade-only phrases do not receive a polymer`, `make import-erp and make import-vanillasoft are not run and their targets stay unchanged` | `plasticos_crm_sync/services/orchestrator.py`, `Makefile`, `plasticos_facility_profile/migrations/19.0.5.4.12/pre-migrate.py`, `plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv`, `plasticos_material_profile/data/material_mapping_resolution_remaining.csv`, `tests/test_material_ledger_resolution.py`, `pipeline_v2.py` |
| T2 | `plasticos_material_profile/data` | `data_plane` | `OPERATOR_HOLDS keeps ldpe/lldpe clear repro`, `Grade-only phrases do not receive a polymer`, `make import-erp and make import-vanillasoft are not run and their targets stay unchanged` | `plasticos_crm_sync/services/orchestrator.py`, `Makefile`, `plasticos_facility_profile/migrations/19.0.5.4.12/pre-migrate.py`, `plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv`, `plasticos_material_profile/data/material_mapping_resolution_remaining.csv`, `tests/test_material_ledger_resolution.py`, `pipeline_v2.py` |
| T3 | `plasticos_material_profile` | `assurance` | `OPERATOR_HOLDS keeps ldpe/lldpe clear repro`, `Grade-only phrases do not receive a polymer`, `make import-erp and make import-vanillasoft are not run and their targets stay unchanged` | `plasticos_crm_sync/services/orchestrator.py`, `Makefile`, `plasticos_facility_profile/migrations/19.0.5.4.12/pre-migrate.py`, `plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv`, `plasticos_material_profile/data/material_mapping_resolution_remaining.csv`, `tests/test_material_ledger_resolution.py`, `pipeline_v2.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.ld_lld_phrase_map.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.ld_lld_phrase_map.v1` |
| source_execution_ref | `plan.simple.ld_lld_phrase_map.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (The nine keys are exact collapsed phrases and ld/lldpe thick/stretch is unchanged.) → Stop. Do not assign a polymer from a grade template.; C2 fails (csv.DictReader shows each of the nine rows mapped, names_one_polymer, and equal to its _SPECS cells.) → Stop. Do not run scripts/build_material_mapping.py across the matrix.; C3 fails (.venv/bin/python -m pytest tests/test_material_mapping_masters.py tests/test_material_ledger_resolution.py and the new normalizer assertions pass. The ledger hold remains.) → Stop. Do not remove the ledger hold or edit orchestrator.py, the Makefile, or the facility-profile migration. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the child branch commit. The parent at 093a2813 keeps the fourteen earlier polymer phrases and version 19.0.5.11.18. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `.venv/bin/python -m pytest plasticos_material_profile/tests/test_material_normalizer.py tests/test_material_mapping_masters.py tests/test_material_ledger_resolution.py`
- re-run `.venv/bin/ruff check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py`
- re-run `.venv/bin/ruff format --check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py`
- re-run `plasticos_material_profile/tests/test_material_normalizer.py`
- re-run `tests/test_material_ledger_resolution.py`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` — highest todo risk across 3 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `low` — Nine worksheet keys and nine matrix rows in plasticos_material_profile. The ledger, the orchestrator, the Makefile, and the facility migration stay as they are. Import commands are not run. |
| architectural_boundaries_crossed | `The worksheet resolver and the committed matrix stay the same seam the ERP and VanillaSoft importers already call` |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.ld_lld_phrase_map.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.ld_lld_phrase_map.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Create a child branch from 093a2813 and add the nine exact _SPECS entries: seven LD/LLD phrases to LDPE_LLDPE with the named secondary masters, spc-a to PP TUBS_LIDS POST_CONSUMER packaging bales, and new opti bins to HDPE CRATES. | Cursor Build agent | `low` | S | `[]` | `plasticos_material_profile/models/material_normalizer.py` |
| T2 | Set those nine material_mapping.csv rows to mapped names_one_polymer with the same polymer, grade, form, source, attribute, color, and packaging cells. Do not rebuild the matrix. | Cursor Build agent | `low` | S | `[T1]` | `plasticos_material_profile/data/material_mapping.csv` |
| T3 | Assert worksheet resolution for the nine phrases and that a bare buckets phrase has no polymer. Bump plasticos_material_profile to 19.0.5.11.19 in the manifest and the README module_version. | Cursor Build agent | `low` | S | `[T1, T2]` | `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_material_profile/README.md` |

**Critical path:** T1 → T2 → T3

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The nine phrases are in _SPECS and the child branch exists from 093a2813. | the matrix cells |
| M2 | The nine CSV rows match those specs and stay length 20. | the worksheet assertions |
| M3 | The normalizer test and the version 19.0.5.11.19 agree, and the ledger test still applies 16 rows. | a later stacked publication after the parent pull request exists |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | The nine keys are exact collapsed phrases and ld/lldpe thick/stretch is unchanged. | Stop. Do not assign a polymer from a grade template. |
| C2 | M2 | csv.DictReader shows each of the nine rows mapped, names_one_polymer, and equal to its _SPECS cells. | Stop. Do not run scripts/build_material_mapping.py across the matrix. |
| C3 | M3 | .venv/bin/python -m pytest tests/test_material_mapping_masters.py tests/test_material_ledger_resolution.py and the new normalizer assertions pass. The ledger hold remains. | Stop. Do not remove the ledger hold or edit orchestrator.py, the Makefile, or the facility-profile migration. |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`
- **Shared causes:** Both importers already call the worksheet table. Nine exact keys cover the named rows without a second resolver.
- **Deletions / consolidations:** Do not add a CRM alias for these phrases. The worksheet path is the one make import-erp calls, and VanillaSoft checks _SPECS first.; Do not rebuild the matrix. A full rebuild can treat PET as a prefix of PETG and MDPE inside blend text.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The addon set and the importer commands do not change. |
| INVARIANTS.md | `n_a` | — | No invariant changes. The worksheet table remains the importer authority. |
| CLAUDE.md | `n_a` | — | CLAUDE.md points at AGENTS.md for the addon snapshot. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `plasticos_material_profile/tests/test_material_normalizer.py` | Each of the nine phrases resolves on the worksheet call with the polymer and the secondary masters named in the objective. | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `plasticos_material_profile/tests/test_material_normalizer.py` | A bare buckets phrase has no polymer. | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `tests/test_material_ledger_resolution.py` | The ledger test still applies 16 rows, and the nine matrix rows are mapped names_one_polymer. | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | The manifest and README module_version are 19.0.5.11.19, and the changed Python is formatted with the repo ruff pin. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does lifting the ledger hold force _SPECS to copy the old LLDPE, pellets, post-industrial, gaylords proposal for ldpe/lldpe clear repro? The hold stays, so the live row can be LDPE_LLDPE while the closed ledger stays untouched.
- Does a grade word such as buckets create a profile? _store_normalized_materials returns when polymer is empty, and this plan does not give those rows a polymer.
- Does ldpe/lldpe blue/white purge pick one color? Both colors are named, so color stays empty and only form PURGE is set.
- Does make pr base=feat/seed-five-polymers succeed before that parent has an open pull request? scripts/pr_stack_parent.sh refuses it, so publication waits.

### Assumption failure conditions

- The 51 grade-known rows receive a polymer from a grade template. They stay unknown.
- The other no-evidence rows are mapped in this change. Only spc-a and new opti bins are added.
- This change repairs the eight roster failures that blocked the parent. It does not.

### Blast radius notes

- Nine worksheet keys and nine matrix rows in plasticos_material_profile. The ledger, the orchestrator, the Makefile, and the facility migration stay as they are. Import commands are not run.

### Rollback constraints

- Revert the child branch commit. The parent at 093a2813 keeps the fourteen earlier polymer phrases and version 19.0.5.11.18.

### Risks

| risk | mitigation |
|------|------------|
| A short CSV row shifts color or the attribute into the wrong column. | Each edited row is checked at 20 fields and compared with the _SPECS cells before the test run. |
| Removing the ledger hold would make the applied-row test demand the old LLDPE proposal. | Leave OPERATOR_HOLDS and both ledger files untouched. The applied count stays 16. |
| Publishing this branch into Staging would skip the seed parent that these phrases depend on. | The child starts at 093a2813. make pr uses base=feat/seed-five-polymers only after that parent pull request is open. |

## Out of scope

- The closed ledger files and the OPERATOR_HOLDS entry for ldpe/lldpe clear repro
- The 51 grade-known polymer-unknown rows, including buckets, totes, dunnage, trays, strapping, and bumpers
- The other no-evidence rows besides spc-a and new opti bins
- ld/lldpe thick/stretch, which is already LDPE_LLDPE
- plasticos_crm_sync/services/orchestrator.py, the Makefile, and the facility-profile migration
- scripts/build_material_mapping.py run across the matrix
- The eight roster failures that blocked the parent
- A pull request before feat/seed-five-polymers has an open pull request
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.ld_lld_phrase_map.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.ld_lld_phrase_map.v1` |
| source_ref | `plan.simple.ld_lld_phrase_map.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | When will feat/seed-five-polymers have an open pull request to stack on? — The mapping commit can land on the child now. Publication is refused until the parent pull request exists. | `accept_bounded` |
| `open_blocker` | stop_reason | The nine phrases are specified. V1 through V4 run when the child branch is built, so this plan is not converged. | planning convergence `partial` |

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
  plan_id: "plan.simple.ld_lld_phrase_map.v1"
  name: "LD LLD phrase map"
  overview: "On a new branch from feat/seed-five-polymers at 093a2813, add nine exact worksheet phrases to _SPECS and the same nine material_mapping.csv rows as mapped names_one_polymer. Seven LD/LLD phrases resolve to LDPE_LLDPE, with a second master only when the phrase names one seeded value. spc-a resolves to PP, grade TUBS_LIDS, source POST_CONSUMER, packaging bales. new opti bins resolves to HDPE, grade CRATES. A grade-only phrase still has no polymer. The ledger hold stays. plasticos_material_profile becomes 19.0.5.11.19. Publication waits until feat/seed-five-polymers has an open pull request, then make pr base=feat/seed-five-polymers."
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
  commit_sha: "6959f249e82944ae8ef8588cddf0060072b35595"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "On a new branch from feat/seed-five-polymers at 093a2813, add nine exact worksheet phrases to _SPECS and the same nine material_mapping.csv rows as mapped names_one_polymer. Seven LD/LLD phrases resolve to LDPE_LLDPE, with a second master only when the phrase names one seeded value. spc-a resolves to PP, grade TUBS_LIDS, source POST_CONSUMER, packaging bales. new opti bins resolves to HDPE, grade CRATES. A grade-only phrase still has no polymer. The ledger hold stays. plasticos_material_profile becomes 19.0.5.11.19. Publication waits until feat/seed-five-polymers has an open pull request, then make pr base=feat/seed-five-polymers."
  success_properties:
    - id: "SP-01"
      property: "V1 proves each of the nine phrases resolves through normalize_material with crm_aliases left false, including the grade, form, color, source, attribute, and packaging named for that phrase."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves a bare buckets phrase still has no polymer."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 proves the nine material_mapping.csv rows are mapped names_one_polymer with the same cells, and tests/test_material_ledger_resolution.py still applies 16 ledger rows."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 proves plasticos_material_profile is 19.0.5.11.19 in the manifest and the README module_version, and .pre-commit-config.yaml remains the hook catalog."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.ld_lld_phrase_map.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_material_profile/models/material_normalizer.py", "plasticos_material_profile/data/material_mapping.csv", "plasticos_material_profile/tests/test_material_normalizer.py", "plasticos_material_profile/__manifest__.py", "plasticos_material_profile/README.md"]
    write_deny: ["plasticos_crm_sync/services/orchestrator.py", "Makefile", "plasticos_facility_profile/migrations/19.0.5.4.12/pre-migrate.py", "plasticos_material_profile/data/material_mapping_resolution_ledger_11-04-26.csv", "plasticos_material_profile/data/material_mapping_resolution_remaining.csv", "tests/test_material_ledger_resolution.py", "pipeline_v2.py"]
  commands:
    allow: [".venv/bin/python -m pytest plasticos_material_profile/tests/test_material_normalizer.py tests/test_material_mapping_masters.py tests/test_material_ledger_resolution.py", ".venv/bin/ruff check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py", ".venv/bin/ruff format --check plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py", "plasticos_material_profile/tests/test_material_normalizer.py", "tests/test_material_ledger_resolution.py", ".pre-commit-config.yaml"]
  network:
    mode: "named_services_only"
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
rollback_contract_ref: "rollback.plan.simple.ld_lld_phrase_map.v1"
dependency_topology_ref: "dag.plan.simple.ld_lld_phrase_map.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Does lifting the ledger hold force _SPECS to copy the old LLDPE, pellets, post-industrial, gaylords proposal for ldpe/lldpe clear repro? The hold stays, so the live row can be LDPE_LLDPE while the closed ledger stays untouched.", "Does a grade word such as buckets create a profile? _store_normalized_materials returns when polymer is empty, and this plan does not give those rows a polymer.", "Does ldpe/lldpe blue/white purge pick one color? Both colors are named, so color stays empty and only form PURGE is set.", "Does make pr base=feat/seed-five-polymers succeed before that parent has an open pull request? scripts/pr_stack_parent.sh refuses it, so publication waits."]
  assumption_failure_conditions: ["The 51 grade-known rows receive a polymer from a grade template. They stay unknown.", "The other no-evidence rows are mapped in this change. Only spc-a and new opti bins are added.", "This change repairs the eight roster failures that blocked the parent. It does not."]
out_of_scope: ["The closed ledger files and the OPERATOR_HOLDS entry for ldpe/lldpe clear repro", "The 51 grade-known polymer-unknown rows, including buckets, totes, dunnage, trays, strapping, and bumpers", "The other no-evidence rows besides spc-a and new opti bins", "ld/lldpe thick/stretch, which is already LDPE_LLDPE", "plasticos_crm_sync/services/orchestrator.py, the Makefile, and the facility-profile migration", "scripts/build_material_mapping.py run across the matrix", "The eight roster failures that blocked the parent", "A pull request before feat/seed-five-polymers has an open pull request"]
convergence_contract_ref: "conv.plan.simple.ld_lld_phrase_map.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Create a child branch from 093a2813 and add the nine exact _SPECS entries: seven LD/LLD phrases to LDPE_LLDPE with the named secondary masters, spc-a to PP TUBS_LIDS POST_CONSUMER packaging bales, and new opti bins to HDPE CRATES."
    status: "pending"
  - id: "T2"
    content: "Set those nine material_mapping.csv rows to mapped names_one_polymer with the same polymer, grade, form, source, attribute, color, and packaging cells. Do not rebuild the matrix."
    status: "pending"
  - id: "T3"
    content: "Assert worksheet resolution for the nine phrases and that a bare buckets phrase has no polymer. Bump plasticos_material_profile to 19.0.5.11.19 in the manifest and the README module_version."
    status: "pending"
```
