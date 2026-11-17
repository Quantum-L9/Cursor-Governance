---
name: Map polymer masters, LDPE grade A, form and source, and stop note profiles
overview: "On a feature branch cut from origin/Staging at 9ee917e7, add the six missing polymer masters, make the LDPE grade A wording family resolve to LDPE film grade A with clean and dry, import form and source-type tokens that match existing masters, make the ERP worksheet line use the same phrase rules as CRM, and stop call-note sentences from creating material profiles."
todos:
  - id: T1
    content: "Insert six plasticos.polymer records in the noupdate=1 block of polymer_data.xml: polymer_tpu code TPU name TPU full_name Thermoplastic Polyurethane category engineering sequence 191; polymer_tpv code TPV name TPV full_name Thermoplastic Vulcanizate category engineering sequence 192; polymer_pvb code PVB name PVB full_name Polyvinyl Butyral category specialty sequence 221; polymer_pu_foam code PU_FOAM name PU Foam full_name Polyurethane Foam category specialty sequence 222; polymer_textile code TEXTILE name Textile full_name Textile category specialty sequence 311; polymer_ubc code UBC name UBC full_name Used Beverage Containers category specialty sequence 312. Leave resin_id_code empty. Bump plasticos_material_profile to 19.0.5.10.11."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Add exact CRM phrases tpu, textile, pvb, ubc, and tpv to _CRM_EXACT with empty form, and add alias foam - pu to _CRM_ALIASES pointing at PU_FOAM with empty form."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "On the six CSV rows TPU, Textile, Foam - PU, PVB, UBC, and TPV, set status to mapped, fill polymer with TPU, TEXTILE, PU_FOAM, PVB, UBC, or TPV, set rule to crm_code except Foam - PU which is approved_alias, and set the note to master added 2026-11-03. Leave workbook_category as UNMAPPED. Bump plasticos_crm_sync to 19.0.1.9.16."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T4
    content: "In _SPECS, change ldpe film a to the same tuple as ldpe grade a film: LDPE, FILM, no source, attributes clean and dry, grade A. Add ldpe a film, ldpe film - grade a, ldpe film grade a, and 99% clear ldpe film with that same tuple. Update the LDPE Film A CSV attributes column to clean dry and add mapped worksheet_phrase rows for the four new keys. Update the normalizer test that currently expects LDPE Film A to have no attributes."
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "Delete the 27 call-note keys from _CRM_ALIASES. The closed set is every current alias key matched by the narrative markers has, had, generates, generate, mentioned, mention, they, quote, sold, marketing, offered, and got, plus and occ -, .01 fob grade a mrp, ext218 - pp sacks, and the MRP quantity sentence. Set each matching CSV row to status held, clear polymer, form, grade, and attributes, and set rule to note_not_material. Freeze those 27 source tokens in a test that asserts each stays unresolved."
    status: pending
    phase: execute
    depends_on: [T2]
  - id: T6
    content: "Add classify_form_token and classify_source_token in material_normalizer.py. A form token matches plasticos.material.form by name or code after whitespace collapse and case folding, with the extra alias rolls to ROLLSTOCK. A source token matches plasticos.source.type by name or code after treating hyphens as spaces, with virgin mapping to PRIME. A token that matches neither returns empty. Do not add masters."
    status: pending
    phase: execute
    depends_on: []
  - id: T7
    content: "Make _material_field_kind treat type and type ( the same way _material_slot does. Split every hint on commas and keep every token in both _material_inputs and _parse_material_sections. After a phrase profile exists, apply each form token: fill an empty form_id, and when the profile already has a different form reuse a second profile for the same polymer and that form. Apply each source token through the existing empty-or-conflict source write. A type token that matches a form and not a source is a form token. A token that matches neither is REQUIRED_MAPPING naming the token and creates no profile. Stop the optional unsupported type hint notice for a token that classified as form or source."
    status: pending
    phase: execute
    depends_on: [T6]
  - id: T8
    content: "Change _normalize_line to call normalize_crm_material. Bump plasticos_transaction to 19.0.2.3.50. Update both source assertions that currently require normalize_material( and forbid normalize_crm_material in native_document_import.py. Leave normalize_material itself as the _SPECS lookup."
    status: pending
    phase: execute
    depends_on: [T4, T5]
  - id: T9
    content: "Add tests for the six polymers, the six LDPE grade A phrases, the 27 unresolved note tokens, Bales plus Post Consumer on an LDPE section, Rolls to ROLLSTOCK, Virgin to PRIME, a comma pair Bales and Regrind as two forms, and Stacked as REQUIRED_MAPPING with no profile. Run ruff format on the edited Python."
    status: pending
    phase: execute
    depends_on: [T3, T4, T5, T7, T8]
  - id: T10
    content: "Run the V1, V2, V3, and V4 commands. If tests/test_phantom_enum_values.py flags one of the new polymer codes, add that code to GLOBAL_ALLOWLIST with a comment that it is a polymer master code."
    status: pending
    phase: execute
    depends_on: [T9]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Map polymer masters, LDPE grade A, form and source, and stop note profiles

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles_23d588cc.plan.md`
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
| plan_id | `plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| name | Map polymer masters, LDPE grade A, form and source, and stop note profiles |
| overview | On a feature branch cut from origin/Staging at 9ee917e7, add the six missing polymer masters, make the LDPE grade A wording family resolve to LDPE film grade A with clean and dry, import form and source-type tokens that match existing masters, make the ERP worksheet line use the same phrase rules as CRM, and stop call-note sentences from creating material profiles. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| created_at | 2026-11-03T15:06:06+00:00 |
| updated_at | 2026-11-03T15:06:06+00:00 |
| depth | `standard` |
| estimate | one feature branch from origin/Staging 9ee917e7, three module version bumps, no new model |

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
| captured_at | `2026-11-03T15:06:06+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `docs/campaign-reorg-multiload-audit` |
| commit_sha | `dbecab74df0f15593257a0fb0f1ee42df3e7562b` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

On a feature branch cut from origin/Staging at 9ee917e7, add the six missing polymer masters, make the LDPE grade A wording family resolve to LDPE film grade A with clean and dry, import form and source-type tokens that match existing masters, make the ERP worksheet line use the same phrase rules as CRM, and stop call-note sentences from creating material profiles.

### Scope in

- six plasticos.polymer seed records and their exact phrases
- the LDPE grade A phrase family in _SPECS and the material map
- removal of the 27 call-note aliases
- form and source token classification onto existing masters
- CRM section import of every comma-separated form and type token
- ERP worksheet description classification through normalize_crm_material
- version bumps of plasticos_material_profile, plasticos_crm_sync, and plasticos_transaction

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: ruff and the hooks in .pre-commit-config.yaml exit 0 on every touched file. | `quality_gate` | V1: `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py` → ruff and the .pre-commit-config.yaml hooks exit 0 on the touched files. | `true` |
| SP-02 | V2: normalize_crm_material resolves TPU, Textile, Foam - PU, PVB, UBC, and TPV to TPU, TEXTILE, PU_FOAM, PVB, UBC, and TPV, and resolves LDPE Grade A Film, LDPE Film A, LDPE A Film, LDPE Film - Grade A, LDPE Film Grade A, and 99% Clear LDPE Film to LDPE, form FILM, grade A, attributes clean and dry. | `quality_gate` | V2: `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync` → Both module test runs report zero failures. The six polymer phrases and the six LDPE grade A phrases resolve as named in the success criteria. The 27 note tokens stay unresolved. Bales and Post Consumer are stored. Stacked creates no profile. | `true` |
| SP-03 | V2: the 27 call-note alias keys stay unresolved and their CSV rows are status held. | `quality_gate` | V2: `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync` → Both module test runs report zero failures. The six polymer phrases and the six LDPE grade A phrases resolve as named in the success criteria. The 27 note tokens stay unresolved. Bales and Post Consumer are stored. Stacked creates no profile. | `true` |
| SP-04 | V2: a CRM section whose phrase is LDPE, whose Material Form is Bales, and whose Material Type is Post Consumer stores source POST_CONSUMER and a BALES form, and the token Stacked is a REQUIRED_MAPPING error with no new profile. | `quality_gate` | V2: `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync` → Both module test runs report zero failures. The six polymer phrases and the six LDPE grade A phrases resolve as named in the success criteria. The 27 note tokens stay unresolved. Bales and Post Consumer are stored. Stacked creates no profile. | `true` |
| SP-05 | V3: plasticos_transaction/models/native_document_import.py _normalize_line calls normalize_crm_material and a worksheet LDPE grade A description classifies as LDPE film grade A with clean and dry. | `quality_gate` | V1: `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py` → ruff and the .pre-commit-config.yaml hooks exit 0 on the touched files.; V3: `make test-module m=plasticos_transaction` → The transaction module tests report zero failures, and a worksheet description in the LDPE grade A family classifies as LDPE film grade A with clean and dry. | `true` |
| SP-06 | V4: tests/test_phantom_enum_values.py exits 0. | `quality_gate` | V4: `python3 -m pytest tests/test_phantom_enum_values.py -q` → The phantom-enum test exits 0. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| source_ref | `plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P1 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --porcelain` | Observed docs/campaign-reorg-multiload-audit at dbecab74 with 30 deleted campaign docs. origin/Staging 9ee917e7 is an ancestor. The feature branch is cut from 9ee917e7 and those deletions stay unstaged. | `true` |
| P2 | pre-validation (status `passed`) | `read polymer_data.xml, _SPECS, _CRM_ALIASES, and the six no_master CSV rows` | No code TPU, TEXTILE, PU_FOAM, PVB, UBC, or TPV exists. ldpe film a is grade A with empty attributes. ldpe grade a film and 99 clear ldpe film are grade A with clean and dry. The keys ldpe a film, ldpe film - grade a, ldpe film grade a, and 99% clear ldpe film are absent. Narrative aliases are present. The six CSV rows are status no_master. | `true` |
| P3 | pre-validation (status `passed`) | `test -f .pre-commit-config.yaml` | .pre-commit-config.yaml is the hook catalog for this governed workspace. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_material_profile/data/polymer_data.xml`, `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_crm_sync/data/vanillasoft_material_mapping.csv`, `plasticos_crm_sync/__manifest__.py`, `plasticos_crm_sync/services/orchestrator.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py`, `plasticos_transaction/models/native_document_import.py`, `plasticos_transaction/__manifest__.py`, `tests/test_phantom_enum_values.py`
- **write_deny:** `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)`
- **delete_allow:** `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_crm_sync/data/vanillasoft_material_mapping.csv`

### Commands

- **allow:** `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction`, `pre-commit run --config .pre-commit-config.yaml --files <touched files>`, `make test-module m=plasticos_material_profile`, `make test-module m=plasticos_crm_sync`, `make test-module m=plasticos_transaction`, `python3 -m pytest tests/test_phantom_enum_values.py -q`, `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py`, `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| allowed_services | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |

### Secrets

| Field | Value |
|-------|-------|
| access | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- plasticos.polymer unique code constraint
- exact phrase match after whitespace collapse and case folding
- new xml ids live in the noupdate=1 block
- every remaining importer phrase stays listed as a mapped row
- a token with no master does not create a profile
- normalize_material remains the _SPECS lookup

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/__manifest__.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_normalizer.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv` | `false` |
| T5 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/tests/test_material_normalizer.py` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/tests/test_orchestrator_upsert.py` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/tests/test_orchestrator_upsert.py` | `false` |
| T10 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_crm_sync/__manifest__.py plasticos_transaction/__manifest__.py tests/test_phantom_enum_values.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `plasticos_material_profile` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T2 | `plasticos_material_profile/models` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T3 | `plasticos_crm_sync` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T4 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T5 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T6 | `plasticos_material_profile` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T7 | `plasticos_crm_sync` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T8 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T9 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |
| T10 | `repository root` | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` | `plasticos.polymer unique code constraint`, `exact phrase match after whitespace collapse and case folding`, `new xml ids live in the noupdate=1 block`, `every remaining importer phrase stays listed as a mapped row`, `a token with no master does not create a profile`, `normalize_material remains the _SPECS lookup` | `plasticos_material_profile/models/polymer.py`, `docs/campaigns/10-30-26/`, `packaging_type_id and origin_form_id`, `LDPE grade B and grade C phrases`, `the 38 pending_decision CSV rows`, `the held row Bottles (HD/PET)` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| source_execution_ref | `plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | C1 fails (polymer_data.xml contains exactly one record per new code and the manifest version is 19.0.5.10.11.) → Stop before phrase edits if any new code collides with an existing record.; C2 fails (Every remaining phrase-table key has a mapped CSV row, and every held note row is unresolved.) → Do not switch the ERP call until the note keys are gone from both tables.; C3 fails (A fixture with Material Form Bales and Material Type Post Consumer writes those masters, and Stacked writes no profile.) → Stop if a token with no master created a polymer or a form. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the feature branch. The new xml ids can be archived with active false if a database already loaded them. Do not drop columns or tables. Profiles already created by a note sentence are not deleted by this change. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction`
- re-run `pre-commit run --config .pre-commit-config.yaml --files <touched files>`
- re-run `make test-module m=plasticos_material_profile`
- re-run `make test-module m=plasticos_crm_sync`
- re-run `make test-module m=plasticos_transaction`
- re-run `python3 -m pytest tests/test_phantom_enum_values.py -q`
- re-run `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py`
- re-run `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 10 todo(s) |
| uncertainty | `medium` — 3 unknown(s), 0 blocking |
| blast_radius | `medium` — Installed databases gain six polymer rows on the next plasticos_material_profile upgrade. CRM imports gain profiles for the six tokens and for recognized form and source values, and they stop gaining profiles from the 27 note sentences. ERP worksheet lines that match a CRM phrase, including bare polymer codes and the LDPE grade A family, classify the same way CRM does. Grade B and grade C lines are unchanged. Tokens with no master stay unmapped. |
| architectural_boundaries_crossed | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| external_systems_touched | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| migration_required | unknown — not declared in PLAN_DOCUMENT; resolve before status `executable` |
| unknown_dependency_count | `3` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Insert six plasticos.polymer records in the noupdate=1 block of polymer_data.xml: polymer_tpu code TPU name TPU full_name Thermoplastic Polyurethane category engineering sequence 191; polymer_tpv code TPV name TPV full_name Thermoplastic Vulcanizate category engineering sequence 192; polymer_pvb code PVB name PVB full_name Polyvinyl Butyral category specialty sequence 221; polymer_pu_foam code PU_FOAM name PU Foam full_name Polyurethane Foam category specialty sequence 222; polymer_textile code TEXTILE name Textile full_name Textile category specialty sequence 311; polymer_ubc code UBC name UBC full_name Used Beverage Containers category specialty sequence 312. Leave resin_id_code empty. Bump plasticos_material_profile to 19.0.5.10.11. | Cursor Build agent | `low` | small | `[]` | `plasticos_material_profile/data/polymer_data.xml`, `plasticos_material_profile/__manifest__.py` |
| T2 | Add exact CRM phrases tpu, textile, pvb, ubc, and tpv to _CRM_EXACT with empty form, and add alias foam - pu to _CRM_ALIASES pointing at PU_FOAM with empty form. | Cursor Build agent | `low` | small | `[T1]` | `plasticos_material_profile/models/material_normalizer.py` |
| T3 | On the six CSV rows TPU, Textile, Foam - PU, PVB, UBC, and TPV, set status to mapped, fill polymer with TPU, TEXTILE, PU_FOAM, PVB, UBC, or TPV, set rule to crm_code except Foam - PU which is approved_alias, and set the note to master added 2026-11-03. Leave workbook_category as UNMAPPED. Bump plasticos_crm_sync to 19.0.1.9.16. | Cursor Build agent | `low` | small | `[T2]` | `plasticos_crm_sync/data/vanillasoft_material_mapping.csv`, `plasticos_crm_sync/__manifest__.py` |
| T4 | In _SPECS, change ldpe film a to the same tuple as ldpe grade a film: LDPE, FILM, no source, attributes clean and dry, grade A. Add ldpe a film, ldpe film - grade a, ldpe film grade a, and 99% clear ldpe film with that same tuple. Update the LDPE Film A CSV attributes column to clean dry and add mapped worksheet_phrase rows for the four new keys. Update the normalizer test that currently expects LDPE Film A to have no attributes. | Cursor Build agent | `low` | small | `[]` | `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_crm_sync/data/vanillasoft_material_mapping.csv` |
| T5 | Delete the 27 call-note keys from _CRM_ALIASES. The closed set is every current alias key matched by the narrative markers has, had, generates, generate, mentioned, mention, they, quote, sold, marketing, offered, and got, plus and occ -, .01 fob grade a mrp, ext218 - pp sacks, and the MRP quantity sentence. Set each matching CSV row to status held, clear polymer, form, grade, and attributes, and set rule to note_not_material. Freeze those 27 source tokens in a test that asserts each stays unresolved. | Cursor Build agent | `medium` | medium | `[T2]` | `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_crm_sync/data/vanillasoft_material_mapping.csv` |
| T6 | Add classify_form_token and classify_source_token in material_normalizer.py. A form token matches plasticos.material.form by name or code after whitespace collapse and case folding, with the extra alias rolls to ROLLSTOCK. A source token matches plasticos.source.type by name or code after treating hyphens as spaces, with virgin mapping to PRIME. A token that matches neither returns empty. Do not add masters. | Cursor Build agent | `low` | medium | `[]` | `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/tests/test_material_normalizer.py` |
| T7 | Make _material_field_kind treat type and type ( the same way _material_slot does. Split every hint on commas and keep every token in both _material_inputs and _parse_material_sections. After a phrase profile exists, apply each form token: fill an empty form_id, and when the profile already has a different form reuse a second profile for the same polymer and that form. Apply each source token through the existing empty-or-conflict source write. A type token that matches a form and not a source is a form token. A token that matches neither is REQUIRED_MAPPING naming the token and creates no profile. Stop the optional unsupported type hint notice for a token that classified as form or source. | Cursor Build agent | `medium` | medium | `[T6]` | `plasticos_crm_sync/services/orchestrator.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py` |
| T8 | Change _normalize_line to call normalize_crm_material. Bump plasticos_transaction to 19.0.2.3.50. Update both source assertions that currently require normalize_material( and forbid normalize_crm_material in native_document_import.py. Leave normalize_material itself as the _SPECS lookup. | Cursor Build agent | `medium` | small | `[T4, T5]` | `plasticos_transaction/models/native_document_import.py`, `plasticos_transaction/__manifest__.py`, `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py` |
| T9 | Add tests for the six polymers, the six LDPE grade A phrases, the 27 unresolved note tokens, Bales plus Post Consumer on an LDPE section, Rolls to ROLLSTOCK, Virgin to PRIME, a comma pair Bales and Regrind as two forms, and Stacked as REQUIRED_MAPPING with no profile. Run ruff format on the edited Python. | Cursor Build agent | `low` | medium | `[T3, T4, T5, T7, T8]` | `plasticos_material_profile/tests/test_material_normalizer.py`, `plasticos_crm_sync/tests/test_orchestrator_upsert.py` |
| T10 | Run the V1, V2, V3, and V4 commands. If tests/test_phantom_enum_values.py flags one of the new polymer codes, add that code to GLOBAL_ALLOWLIST with a comment that it is a polymer master code. | Cursor Build agent | `low` | small | `[T9]` | `plasticos_material_profile/models/material_normalizer.py`, `plasticos_material_profile/__manifest__.py`, `plasticos_crm_sync/__manifest__.py`, `plasticos_transaction/__manifest__.py`, `tests/test_phantom_enum_values.py` |

**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The six polymers, the LDPE grade A family, and the note-alias removal agree between the phrase tables and the CSV. | TestVanillaSoftMaterialMap can pass and both importers share one phrase result. |
| M2 | Recognized form and source tokens are stored on profiles, and the worksheet line uses the CRM phrase function. | A later CRM import and a later ERP import keep grade, form, and source that the current code drops. |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T1 | polymer_data.xml contains exactly one record per new code and the manifest version is 19.0.5.10.11. | Stop before phrase edits if any new code collides with an existing record. |
| C2 | T5 | Every remaining phrase-table key has a mapped CSV row, and every held note row is unresolved. | Do not switch the ERP call until the note keys are gone from both tables. |
| C3 | T7 | A fixture with Material Form Bales and Material Type Post Consumer writes those masters, and Stacked writes no profile. | Stop if a token with no master created a polymer or a form. |

### Leverage

- **Ranked todos:** `T1`, `T4`, `T5`, `T6`, `T2`, `T7`, `T8`, `T3`, `T9`, `T10`
- **Shared causes:** One missing master blocks each of the six tokens. The phrase and the map row move together.; One grade A tuple covers the six LDPE wordings. The ERP gap is the call site, not a second phrase table.; One classifier covers form and source. Unmatched tokens stay errors instead of becoming a second taxonomy.
- **Deletions / consolidations:** The 27 note aliases are deleted rather than rewritten. No new model, field, or packaging master is added.; ERP joins the existing CRM phrase function instead of copying _SPECS, _CRM_EXACT, and _CRM_ALIASES.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | No module is added or removed and the project structure list does not name polymer codes or phrase rules. |
| plasticos_material_profile/README.md | `n_a` | — | The README does not enumerate polymer codes or importer phrase rules. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-05 | `quality_gate_evidence` | command | `ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py` | ruff and the .pre-commit-config.yaml hooks exit 0 on the touched files. | `not_run` |
| E-V2 | SP-02, SP-03, SP-04 | `quality_gate_evidence` | command | `make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync` | Both module test runs report zero failures. The six polymer phrases and the six LDPE grade A phrases resolve as named in the success criteria. The 27 note tokens stay unresolved. Bales and Post Consumer are stored. Stacked creates no profile. | `not_run` |
| E-V3 | SP-05 | `quality_gate_evidence` | command | `make test-module m=plasticos_transaction` | The transaction module tests report zero failures, and a worksheet description in the LDPE grade A family classifies as LDPE film grade A with clean and dry. | `not_run` |
| E-V4 | SP-06 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_phantom_enum_values.py -q` | The phantom-enum test exits 0. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does a seeded master with no phrase still leave the VanillaSoft token unresolved, so the map test fails if only T1 lands?
- Does changing ldpe film a to clean and dry leave the CSV attributes column empty and fail the map comparison?
- Does removing a note alias while its CSV row stays mapped fail the unresolved-row assertion?
- Does a second form profile overwrite the phrase form FILM instead of keeping both?
- Does calling normalize_crm_material from the worksheet also import the 27 note sentences if T5 is skipped?

### Assumption failure conditions

- A new xml id inside noupdate=1 is skipped on upgrade. It is not: noupdate skips later writes of an existing xml id, and a new id is inserted.
- Bales and Loose belong on packaging_type_id because a packaging master shares the name. They do not in this change: the source column is Material Form and the form master is the write target.
- Stacked, Stretch Film, and HMW can be assigned an existing polymer by similarity. They cannot: a token with no master is REQUIRED_MAPPING.
- normalize_material itself grows the alias table. It does not: the worksheet call switches to normalize_crm_material, and _SPECS stays the worksheet-phrase table.

### Blast radius notes

- Installed databases gain six polymer rows on the next plasticos_material_profile upgrade. CRM imports gain profiles for the six tokens and for recognized form and source values, and they stop gaining profiles from the 27 note sentences. ERP worksheet lines that match a CRM phrase, including bare polymer codes and the LDPE grade A family, classify the same way CRM does. Grade B and grade C lines are unchanged. Tokens with no master stay unmapped.

### Rollback constraints

- Revert the feature branch. The new xml ids can be archived with active false if a database already loaded them. Do not drop columns or tables. Profiles already created by a note sentence are not deleted by this change.

### Risks

| risk | mitigation |
|------|------------|
| Used Beverage Containers is a display expansion of UBC, not a chemical name confirmed by the workbook. | Code and source phrase stay UBC. Only full_name carries the expansion, and the plan records it as an accepted bound. |
| Bare LDPE on a worksheet line becomes LDPE film once the ERP call uses the CRM function. | That is the CRM rule the operator asked the worksheet path to follow. Grade B and grade C phrases stay on their current tuples. |
| An explicit Bales form beside a phrase that already inferred FILM creates two profiles. | The phrase profile is kept and the form token adds the second profile. The form token does not replace FILM. |
| Cutting the branch from the current docs checkout would publish unpublished campaign docs and the 30 deletions. | The feature branch base is origin/Staging 9ee917e7. The deletions stay unstaged. |

## Out of scope

- new masters for tokens that match none: Stacked, Stretch Film (Thin), HMW, Frac Melt, Injection, Scrap/Cut, Thick Gauge, Rigid, and the rest of the no-master tail
- the 38 pending_decision tokens and the held row Bottles (HD/PET)
- LDPE grade B, LDPE grade C, and LDPE A Film (Clear Film In Bales)
- packaging_type_id and origin_form_id
- custom-table outage handling, skipped rows, and the two facility resolvers
- the 30 deleted campaign docs on the current checkout
- publication
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
| source_ref | `plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1` |
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
| `unknown` | U1 | What full_name does UBC display? — Display text only. The code and the source phrase stay UBC either way. | `accept_bounded` |
| `unknown` | U2 | Is Textile a resin or a catalog class? — Category and full_name. The code stays TEXTILE and no form is inferred. | `accept_bounded` |
| `unknown` | U3 | Which form and type tokens with no current master become new masters? — Only tokens that already match a master are imported. Stacked, Stretch Film (Thin), HMW, Frac Melt, Injection, Scrap/Cut, Thick Gauge, Rigid, and the remaining unmatched tail stay REQUIRED_MAPPING until a later decision names a master. | `accept_bounded` |
| `open_blocker` | stop_reason | Plan is ready for Build. V1 through V4 have not run because this step is planning only. U1, U2, and U3 are accepted bounds: unmatched form and type tokens are reported and not guessed. | planning convergence `partial` |

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
  plan_id: "plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1"
  name: "Map polymer masters, LDPE grade A, form and source, and stop note profiles"
  overview: "On a feature branch cut from origin/Staging at 9ee917e7, add the six missing polymer masters, make the LDPE grade A wording family resolve to LDPE film grade A with clean and dry, import form and source-type tokens that match existing masters, make the ERP worksheet line use the same phrase rules as CRM, and stop call-note sentences from creating material profiles."
  status: "draft"
  is_project: false
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "dbecab74df0f15593257a0fb0f1ee42df3e7562b"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "On a feature branch cut from origin/Staging at 9ee917e7, add the six missing polymer masters, make the LDPE grade A wording family resolve to LDPE film grade A with clean and dry, import form and source-type tokens that match existing masters, make the ERP worksheet line use the same phrase rules as CRM, and stop call-note sentences from creating material profiles."
  success_properties:
    - id: "SP-01"
      property: "V1: ruff and the hooks in .pre-commit-config.yaml exit 0 on every touched file."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: normalize_crm_material resolves TPU, Textile, Foam - PU, PVB, UBC, and TPV to TPU, TEXTILE, PU_FOAM, PVB, UBC, and TPV, and resolves LDPE Grade A Film, LDPE Film A, LDPE A Film, LDPE Film - Grade A, LDPE Film Grade A, and 99% Clear LDPE Film to LDPE, form FILM, grade A, attributes clean and dry."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V2: the 27 call-note alias keys stay unresolved and their CSV rows are status held."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-04"
      property: "V2: a CRM section whose phrase is LDPE, whose Material Form is Bales, and whose Material Type is Post Consumer stores source POST_CONSUMER and a BALES form, and the token Stacked is a REQUIRED_MAPPING error with no new profile."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-05"
      property: "V3: plasticos_transaction/models/native_document_import.py _normalize_line calls normalize_crm_material and a worksheet LDPE grade A description classifies as LDPE film grade A with clean and dry."
      evidence_type: "quality_gate"
      proof: ["V1", "V3"]
      blocking: true
    - id: "SP-06"
      property: "V4: tests/test_phantom_enum_values.py exits 0."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_material_profile/data/polymer_data.xml", "plasticos_material_profile/models/material_normalizer.py", "plasticos_material_profile/tests/test_material_normalizer.py", "plasticos_material_profile/__manifest__.py", "plasticos_crm_sync/data/vanillasoft_material_mapping.csv", "plasticos_crm_sync/__manifest__.py", "plasticos_crm_sync/services/orchestrator.py", "plasticos_crm_sync/tests/test_orchestrator_upsert.py", "plasticos_transaction/models/native_document_import.py", "plasticos_transaction/__manifest__.py", "tests/test_phantom_enum_values.py"]
    write_deny: ["plasticos_material_profile/models/polymer.py", "docs/campaigns/10-30-26/", "packaging_type_id and origin_form_id", "LDPE grade B and grade C phrases", "the 38 pending_decision CSV rows", "the held row Bottles (HD/PET)"]
  commands:
    allow: ["ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction", "pre-commit run --config .pre-commit-config.yaml --files <touched files>", "make test-module m=plasticos_material_profile", "make test-module m=plasticos_crm_sync", "make test-module m=plasticos_transaction", "python3 -m pytest tests/test_phantom_enum_values.py -q", "ruff check plasticos_material_profile plasticos_crm_sync plasticos_transaction && ruff format --check plasticos_material_profile plasticos_crm_sync plasticos_transaction && pre-commit run --config .pre-commit-config.yaml --files plasticos_material_profile/data/polymer_data.xml plasticos_material_profile/models/material_normalizer.py plasticos_material_profile/__manifest__.py plasticos_material_profile/tests/test_material_normalizer.py plasticos_crm_sync/data/vanillasoft_material_mapping.csv plasticos_crm_sync/__manifest__.py plasticos_crm_sync/services/orchestrator.py plasticos_crm_sync/tests/test_orchestrator_upsert.py plasticos_transaction/models/native_document_import.py plasticos_transaction/__manifest__.py", "make test-module m=plasticos_material_profile && make test-module m=plasticos_crm_sync"]
  network:
    mode: "unknown — not declared in PLAN_DOCUMENT; resolve before status `executable`"
  secrets:
    access: "unknown — not declared in PLAN_DOCUMENT; resolve before status `executable`"
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
    side_effects: "destructive_filesystem_mutation"
    idempotency: "unsafe_blind_repeat"
    retry: "manual_only"
  - todo_id: "T6"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T7"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T8"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T9"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T10"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1"
dependency_topology_ref: "dag.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Does a seeded master with no phrase still leave the VanillaSoft token unresolved, so the map test fails if only T1 lands?", "Does changing ldpe film a to clean and dry leave the CSV attributes column empty and fail the map comparison?", "Does removing a note alias while its CSV row stays mapped fail the unresolved-row assertion?", "Does a second form profile overwrite the phrase form FILM instead of keeping both?", "Does calling normalize_crm_material from the worksheet also import the 27 note sentences if T5 is skipped?"]
  assumption_failure_conditions: ["A new xml id inside noupdate=1 is skipped on upgrade. It is not: noupdate skips later writes of an existing xml id, and a new id is inserted.", "Bales and Loose belong on packaging_type_id because a packaging master shares the name. They do not in this change: the source column is Material Form and the form master is the write target.", "Stacked, Stretch Film, and HMW can be assigned an existing polymer by similarity. They cannot: a token with no master is REQUIRED_MAPPING.", "normalize_material itself grows the alias table. It does not: the worksheet call switches to normalize_crm_material, and _SPECS stays the worksheet-phrase table."]
out_of_scope: ["new masters for tokens that match none: Stacked, Stretch Film (Thin), HMW, Frac Melt, Injection, Scrap/Cut, Thick Gauge, Rigid, and the rest of the no-master tail", "the 38 pending_decision tokens and the held row Bottles (HD/PET)", "LDPE grade B, LDPE grade C, and LDPE A Film (Clear Film In Bales)", "packaging_type_id and origin_form_id", "custom-table outage handling, skipped rows, and the two facility resolvers", "the 30 deleted campaign docs on the current checkout", "publication"]
convergence_contract_ref: "conv.plan.simple.map_polymer_masters_ldpe_grade_a_form_and_source_and_stop_note_profiles.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Insert six plasticos.polymer records in the noupdate=1 block of polymer_data.xml: polymer_tpu code TPU name TPU full_name Thermoplastic Polyurethane category engineering sequence 191; polymer_tpv code TPV name TPV full_name Thermoplastic Vulcanizate category engineering sequence 192; polymer_pvb code PVB name PVB full_name Polyvinyl Butyral category specialty sequence 221; polymer_pu_foam code PU_FOAM name PU Foam full_name Polyurethane Foam category specialty sequence 222; polymer_textile code TEXTILE name Textile full_name Textile category specialty sequence 311; polymer_ubc code UBC name UBC full_name Used Beverage Containers category specialty sequence 312. Leave resin_id_code empty. Bump plasticos_material_profile to 19.0.5.10.11."
    status: "pending"
  - id: "T2"
    content: "Add exact CRM phrases tpu, textile, pvb, ubc, and tpv to _CRM_EXACT with empty form, and add alias foam - pu to _CRM_ALIASES pointing at PU_FOAM with empty form."
    status: "pending"
  - id: "T3"
    content: "On the six CSV rows TPU, Textile, Foam - PU, PVB, UBC, and TPV, set status to mapped, fill polymer with TPU, TEXTILE, PU_FOAM, PVB, UBC, or TPV, set rule to crm_code except Foam - PU which is approved_alias, and set the note to master added 2026-11-03. Leave workbook_category as UNMAPPED. Bump plasticos_crm_sync to 19.0.1.9.16."
    status: "pending"
  - id: "T4"
    content: "In _SPECS, change ldpe film a to the same tuple as ldpe grade a film: LDPE, FILM, no source, attributes clean and dry, grade A. Add ldpe a film, ldpe film - grade a, ldpe film grade a, and 99% clear ldpe film with that same tuple. Update the LDPE Film A CSV attributes column to clean dry and add mapped worksheet_phrase rows for the four new keys. Update the normalizer test that currently expects LDPE Film A to have no attributes."
    status: "pending"
  - id: "T5"
    content: "Delete the 27 call-note keys from _CRM_ALIASES. The closed set is every current alias key matched by the narrative markers has, had, generates, generate, mentioned, mention, they, quote, sold, marketing, offered, and got, plus and occ -, .01 fob grade a mrp, ext218 - pp sacks, and the MRP quantity sentence. Set each matching CSV row to status held, clear polymer, form, grade, and attributes, and set rule to note_not_material. Freeze those 27 source tokens in a test that asserts each stays unresolved."
    status: "pending"
  - id: "T6"
    content: "Add classify_form_token and classify_source_token in material_normalizer.py. A form token matches plasticos.material.form by name or code after whitespace collapse and case folding, with the extra alias rolls to ROLLSTOCK. A source token matches plasticos.source.type by name or code after treating hyphens as spaces, with virgin mapping to PRIME. A token that matches neither returns empty. Do not add masters."
    status: "pending"
  - id: "T7"
    content: "Make _material_field_kind treat type and type ( the same way _material_slot does. Split every hint on commas and keep every token in both _material_inputs and _parse_material_sections. After a phrase profile exists, apply each form token: fill an empty form_id, and when the profile already has a different form reuse a second profile for the same polymer and that form. Apply each source token through the existing empty-or-conflict source write. A type token that matches a form and not a source is a form token. A token that matches neither is REQUIRED_MAPPING naming the token and creates no profile. Stop the optional unsupported type hint notice for a token that classified as form or source."
    status: "pending"
  - id: "T8"
    content: "Change _normalize_line to call normalize_crm_material. Bump plasticos_transaction to 19.0.2.3.50. Update both source assertions that currently require normalize_material( and forbid normalize_crm_material in native_document_import.py. Leave normalize_material itself as the _SPECS lookup."
    status: "pending"
  - id: "T9"
    content: "Add tests for the six polymers, the six LDPE grade A phrases, the 27 unresolved note tokens, Bales plus Post Consumer on an LDPE section, Rolls to ROLLSTOCK, Virgin to PRIME, a comma pair Bales and Regrind as two forms, and Stacked as REQUIRED_MAPPING with no profile. Run ruff format on the edited Python."
    status: "pending"
  - id: "T10"
    content: "Run the V1, V2, V3, and V4 commands. If tests/test_phantom_enum_values.py flags one of the new polymer codes, add that code to GLOBAL_ALLOWLIST with a comment that it is a polymer master code."
    status: "pending"
```
