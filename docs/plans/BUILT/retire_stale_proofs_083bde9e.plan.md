---
name: Retire stale test proofs
overview: Delete the superseded CRM4 constraint proof, the four-repo Gate driver,
  the Cypher alignment scanner, the replica tests in tests/test_gap_fixes.py, and
  the vacuous phantom-enum printer. Keep the runtime tests that already lock material
  identity, CRM4 profile reuse, Gate contracts, intake partner sync, web-lead auth,
  and the absence of local Neo4j matching. Replace only the two claims that would...
todos:
- id: T1
  content: Delete the three CRM4 constraint proof files together. Do not execute tests/crm4_constraint_compat.sh.
    A failed run deletes tests/crm4_selected_constraint.sql.
  status: completed
- id: T2
  content: Delete tests/e2e/four_repo/run_odoo_driver.py and tests/e2e/four_repo/README.md,
    and remove the directory.
  status: completed
- id: T3
  content: In the same change as T2, remove run_odoo_driver.py from NON_TEST_FILES
    and delete the four-repo comment in tests/test_suite_structure.py.
  status: completed
- id: T4
  content: Delete tests/test_cypher_schema_alignment.py. Remove its row and pytest
    example from tests/README.md. Remove it from the pure-Python include list in .coderabbit.yaml.
    Do not turn the drift skip into a failure.
  status: completed
- id: T5
  content: Delete tests/test_gap_fixes.py. Do not replace it with a source-text scan.
    Intake sync and web-lead auth already have runtime tests.
  status: completed
- id: T6
  content: Add plasticos_base/tests/test_matching_engine_gate_url.py and import it
    from plasticos_base/tests/__init__.py. Do not import tests from plasticos_base/__init__.py.
    Use PlasticosTestCase and post_install,-at_install. Save and restore GATE_URL.
    Unset and whitespace-only values make matching_engine_is_enabled false, matching_engine_should_skip_cron
    true, and matching_engine_require_enabled_for_ui raise UserError. A non-empty
    URL reverses those three results. Do not assert that _param_truthy is absent.
  status: completed
- id: T7
  content: Add plasticos_admin_dashboard/tests/__init__.py and test_rep_performance_view.py.
    Leave plasticos_admin_dashboard/__init__.py as from . import models. TransactionCase,
    post_install,-at_install. Call plasticos.rep.performance.init(), then assert pg_class.relkind
    v for plasticos_rep_performance, information_schema columns rep_name, deals_closed,
    revenue_closed, gm_pct, commission, and period_sort, and search limit 1. Parameterize
    the relation name. Do not paste CREATE VIEW into the test.
  status: completed
- id: T8
  content: Remove class TestPhantomAuditReport from tests/test_phantom_enum_values.py.
    Leave the rest of the phantom-enum scanner.
  status: completed
- id: T9
  content: Run V1 through V6. Search only the live tree. Exclude filetree.md, docs/reports/repo-index/,
    docs/campaigns/, and .cursor-commands/. Do not edit those paths to clear a hit.
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Retire stale test proofs

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `retire_stale_test_proofs_59961a48.plan.md`
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
| plan_id | `plan.simple.retire_stale_test_proofs.v1` |
| name | Retire stale test proofs |
| overview | Delete the superseded CRM4 constraint proof, the four-repo Gate driver, the Cypher alignment scanner, the replica tests in tests/test_gap_fixes.py, and the vacuous phantom-enum printer. Keep the runtime tests that already lock material identity, CRM4 profile reuse, Gate contracts, intake partner sync, web-lead auth, and the absence of local Neo4j matching. Replace only the two claims that would otherwise have no owner by calling matching_engine_is_enabled, matching_engine_should_skip_cron, matching_engine_require_enabled_for_ui, and plasticos.rep.performance.init() on the Docker test fixture. Do not add a source-text contract. Product architecture is already settled: the material identity is the partial unique index, Gate converge stays the three contract tests, and local Neo4j matching stays retired. GAR does not select a new architecture. The L9 architecture profile is not the product law for this Odoo suite, and the integrated cognitive runtime is not activated. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. Those records are unrelated GMP work and stay out of this change. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T15:55:18+00:00 |
| updated_at | 2026-11-05T15:55:18+00:00 |
| depth | `standard` |
| estimate | one Build session |

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
| captured_at | `2026-11-05T15:55:18+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `fix/documents-loop-query-batch` |
| commit_sha | `2803c087e373d0ca6b871a35d44b14210b683e91` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Delete the superseded CRM4 constraint proof, the four-repo Gate driver, the Cypher alignment scanner, the replica tests in tests/test_gap_fixes.py, and the vacuous phantom-enum printer. Keep the runtime tests that already lock material identity, CRM4 profile reuse, Gate contracts, intake partner sync, web-lead auth, and the absence of local Neo4j matching. Replace only the two claims that would otherwise have no owner by calling matching_engine_is_enabled, matching_engine_should_skip_cron, matching_engine_require_enabled_for_ui, and plasticos.rep.performance.init() on the Docker test fixture. Do not add a source-text contract. Product architecture is already settled: the material identity is the partial unique index, Gate converge stays the three contract tests, and local Neo4j matching stays retired. GAR does not select a new architecture. The L9 architecture profile is not the product law for this Odoo suite, and the integrated cognitive runtime is not activated. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. Those records are unrelated GMP work and stay out of this change.

### Scope in

- tests/crm4_constraint_compat.sh
- tests/crm4_constraint_compat_negative.sh
- tests/crm4_selected_constraint.sql
- tests/e2e/four_repo/
- tests/test_suite_structure.py
- tests/test_cypher_schema_alignment.py
- tests/test_gap_fixes.py
- tests/test_phantom_enum_values.py
- tests/README.md
- .coderabbit.yaml
- plasticos_base/tests/__init__.py
- plasticos_base/tests/test_matching_engine_gate_url.py
- plasticos_admin_dashboard/tests/__init__.py
- plasticos_admin_dashboard/tests/test_rep_performance_view.py

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | The three CRM4 proof files and tests/e2e/four_repo are absent, and tests/test_suite_structure.py does not name run_odoo_driver.py. Proved by V5. | `quality_gate` | V1: `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py` → Both commands exit 0.; V2: `pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py` → Exit 0 and TestPhantomAuditReport is not collected.; V5: `rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat\|crm4_selected_constraint\|four_repo\|run_odoo_driver\|test_gap_fixes\|test_cypher_schema_alignment\|test_source_contracts' .` → No hits. Hits under the excluded paths are ignored and are not edited. | `true` |
| SP-02 | tests/test_cypher_schema_alignment.py and tests/test_gap_fixes.py are absent, and tests/README.md plus .coderabbit.yaml do not name the Cypher test. Proved by V5. | `quality_gate` | V5: `rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat\|crm4_selected_constraint\|four_repo\|run_odoo_driver\|test_gap_fixes\|test_cypher_schema_alignment\|test_source_contracts' .` → No hits. Hits under the excluded paths are ignored and are not edited. | `true` |
| SP-03 | TestPhantomAuditReport is absent and pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py passes. Proved by V2. | `quality_gate` | V1: `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py` → Both commands exit 0.; V2: `pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py` → Exit 0 and TestPhantomAuditReport is not collected. | `true` |
| SP-04 | Unset, blank, and set GATE_URL drive the three matching-engine helpers under make test-module m=plasticos_base. Proved by V3. | `quality_gate` | V3: `make test-module m=plasticos_base` → The fixture clone runs the new Gate URL tests and the module summary has no failure. Attached wait 600000 ms. Do not start V4 until this exits. | `true` |
| SP-05 | plasticos.rep.performance.init() leaves relkind v, the six columns, and a successful search under make test-module m=plasticos_admin_dashboard. Proved by V4. | `quality_gate` | V4: `make test-module m=plasticos_admin_dashboard` → The fixture clone named in config/test_env_fixture.conf runs test_rep_performance_view and the summary has no failure. Attached wait 600000 ms. | `true` |
| SP-06 | ruff check and ruff format pass on the touched Python files. Proved by V1. | `quality_gate` | V1: `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py` → Both commands exit 0. | `true` |
| SP-07 | The hook catalog .pre-commit-config.yaml names the ruff and ruff-format hooks that cover the touched Python files. Proved by V6. | `quality_gate` | V6: `test -f .pre-commit-config.yaml && rg -n 'id: ruff\|id: ruff-format' .pre-commit-config.yaml` → The hook catalog exists and names the ruff and ruff-format hooks. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.retire_stale_test_proofs.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.retire_stale_test_proofs.v1` |
| source_ref | `plan.simple.retire_stale_test_proofs.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.retire_stale_test_proofs.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short` | Planning baseline is fix/documents-loop-query-batch at 2803c087e373d0ca6b871a35d44b14210b683e91 with one untracked campaign file that this plan must not touch. | `true` |
| P1 | pre-validation (status `passed`) | `python3 ops/hooks/plan_memory_prefetch.py --workspace . --task retire stale test proofs` | MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence sufficient --json` | depth=standard and omit_gates=[] | `true` |
| P3 | pre-validation (status `passed`) | `Name .pre-commit-config.yaml as the hook catalog for the Python edits` | The catalog exists and ruff plus ruff-format apply to the new and edited test files. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/crm4_constraint_compat.sh`, `tests/crm4_constraint_compat_negative.sh`, `tests/crm4_selected_constraint.sql`, `tests/e2e/four_repo/`, `tests/test_suite_structure.py`, `tests/test_cypher_schema_alignment.py`, `tests/test_gap_fixes.py`, `tests/test_phantom_enum_values.py`, `tests/README.md`, `.coderabbit.yaml`, `plasticos_base/tests/__init__.py`, `plasticos_base/tests/test_matching_engine_gate_url.py`, `plasticos_admin_dashboard/tests/__init__.py`, `plasticos_admin_dashboard/tests/test_rep_performance_view.py`
- **write_deny:** `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py`
- **delete_allow:** `tests/crm4_constraint_compat.sh`, `tests/crm4_constraint_compat_negative.sh`, `tests/crm4_selected_constraint.sql`, `tests/e2e/four_repo/run_odoo_driver.py`, `tests/e2e/four_repo/README.md`, `tests/test_cypher_schema_alignment.py`, `tests/README.md`, `.coderabbit.yaml`, `tests/test_gap_fixes.py`

### Commands

- **allow:** `ruff check and ruff format --check on the touched Python files`, `pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py`, `make test-module m=plasticos_base`, `make test-module m=plasticos_admin_dashboard`, `scoped rg for the deleted names`, `test -f .pre-commit-config.yaml && rg ruff hooks`, `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py`, `rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat\|crm4_selected_constraint\|four_repo\|run_odoo_driver\|test_gap_fixes\|test_cypher_schema_alignment\|test_source_contracts' .`, `test -f .pre-commit-config.yaml && rg -n 'id: ruff\|id: ruff-format' .pre-commit-config.yaml`
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

- UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL
- Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py
- tests/contracts/test_no_local_intelligence.py
- plasticos_intake/tests/test_intake_partner_sync_access.py
- plasticos_web_leads/tests/test_web_lead_inbound_http.py
- Docker tests clone only the database in config/test_env_fixture.conf
- No module version bump and no make update

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- tests/crm4_constraint_compat.sh tests/crm4_constraint_compat_negative.sh tests/crm4_selected_constraint.sql` | `false` |
| T2 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- tests/e2e/four_repo/run_odoo_driver.py tests/e2e/four_repo/README.md` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_suite_structure.py` | `false` |
| T4 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- tests/test_cypher_schema_alignment.py tests/README.md .coderabbit.yaml` | `false` |
| T5 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- tests/test_gap_fixes.py` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_admin_dashboard/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_phantom_enum_values.py` | `false` |
| T9 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_suite_structure.py tests/test_phantom_enum_values.py plasticos_base/tests/test_matching_engine_gate_url.py plasticos_admin_dashboard/tests/test_rep_performance_view.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T2 | `tests/e2e/four_repo` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T3 | `tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T4 | `repository root` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T5 | `tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T6 | `plasticos_base/tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T7 | `plasticos_admin_dashboard/tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T8 | `tests` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |
| T9 | `repository root` | `assurance` | `UniqueIndex (partner_id, polymer_id, form_id, material_grade_id) NULLS NOT DISTINCT WHERE partner_id IS NOT NULL`, `Gate contract tests tests/test_gate_canonical_contract.py, tests/test_gate_sdk_invocation.py, tests/test_gate_single_egress.py`, `tests/contracts/test_no_local_intelligence.py`, `plasticos_intake/tests/test_intake_partner_sync_access.py`, `plasticos_web_leads/tests/test_web_lead_inbound_http.py`, `Docker tests clone only the database in config/test_env_fixture.conf`, `No module version bump and no make update` | `plasticos_material_profile/models/material_profile.py`, `plasticos_gate/`, `pipeline_v2.py`, `tests/runtime_gates/`, `tests/integration/test_gate_external_authority_e2e.py`, `filetree.md`, `docs/reports/repo-index/`, `docs/campaigns/`, `.cursor-commands/`, `plasticos_base/__init__.py`, `plasticos_admin_dashboard/__init__.py`, `plasticos_base/__manifest__.py`, `plasticos_admin_dashboard/__manifest__.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.retire_stale_test_proofs.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.retire_stale_test_proofs.v1` |
| source_execution_ref | `plan.simple.retire_stale_test_proofs.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | C1 fails (The CRM4 files, tests/e2e/four_repo, the Cypher test, and test_gap_fixes.py are gone, and NON_TEST_FILES does not name run_odoo_driver.py.) → Stop. Do not run the CRM4 shell to recreate the SQL receipt.; C2 fails (The new tests call the helpers and init(). Neither test parses source for GATE_URL or column names.) → Delete the source-text test if one was added and write the runtime tests instead.; C3 fails (V1, V2, V3, V4, V5, and V6 are passed.) → Do not publish. Do not skip a failed module test and do not point it at a database other than the fixture. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Restore the deleted files from 2803c087e373d0ca6b871a35d44b14210b683e91 and remove the new test files. There is no migration to reverse. Do not run the CRM4 shell as a rollback. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `ruff check and ruff format --check on the touched Python files`
- re-run `pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py`
- re-run `make test-module m=plasticos_base`
- re-run `make test-module m=plasticos_admin_dashboard`
- re-run `scoped rg for the deleted names`
- re-run `test -f .pre-commit-config.yaml && rg ruff hooks`
- re-run `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py`
- re-run `rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat|crm4_selected_constraint|four_repo|run_odoo_driver|test_gap_fixes|test_cypher_schema_alignment|test_source_contracts' .`
- re-run `test -f .pre-commit-config.yaml && rg -n 'id: ruff|id: ruff-format' .pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 9 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — A leftover run_odoo_driver.py fails tests/test_suite_structure.py. A syntax error in the phantom-enum file fails the pure pytest gate. A failed admin-dashboard upgrade spends a fixture run and blocks V4. No production schema, constraint, or Gate contract changes. |
| architectural_boundaries_crossed | `tests/ pure pytest`, `plasticos_base Odoo tests`, `plasticos_admin_dashboard Odoo tests` |
| external_systems_touched | `local Docker test fixture named in config/test_env_fixture.conf` |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.retire_stale_test_proofs.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.retire_stale_test_proofs.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Delete the three CRM4 constraint proof files together. Do not execute tests/crm4_constraint_compat.sh. A failed run deletes tests/crm4_selected_constraint.sql. | Cursor Build agent | `low` | S | `[]` | `tests/crm4_constraint_compat.sh`, `tests/crm4_constraint_compat_negative.sh`, `tests/crm4_selected_constraint.sql` |
| T2 | Delete tests/e2e/four_repo/run_odoo_driver.py and tests/e2e/four_repo/README.md, and remove the directory. | Cursor Build agent | `low` | S | `[]` | `tests/e2e/four_repo/run_odoo_driver.py`, `tests/e2e/four_repo/README.md` |
| T3 | In the same change as T2, remove run_odoo_driver.py from NON_TEST_FILES and delete the four-repo comment in tests/test_suite_structure.py. | Cursor Build agent | `low` | S | `[T2]` | `tests/test_suite_structure.py` |
| T4 | Delete tests/test_cypher_schema_alignment.py. Remove its row and pytest example from tests/README.md. Remove it from the pure-Python include list in .coderabbit.yaml. Do not turn the drift skip into a failure. | Cursor Build agent | `low` | S | `[]` | `tests/test_cypher_schema_alignment.py`, `tests/README.md`, `.coderabbit.yaml` |
| T5 | Delete tests/test_gap_fixes.py. Do not replace it with a source-text scan. Intake sync and web-lead auth already have runtime tests. | Cursor Build agent | `low` | S | `[]` | `tests/test_gap_fixes.py` |
| T6 | Add plasticos_base/tests/test_matching_engine_gate_url.py and import it from plasticos_base/tests/__init__.py. Do not import tests from plasticos_base/__init__.py. Use PlasticosTestCase and post_install,-at_install. Save and restore GATE_URL. Unset and whitespace-only values make matching_engine_is_enabled false, matching_engine_should_skip_cron true, and matching_engine_require_enabled_for_ui raise UserError. A non-empty URL reverses those three results. Do not assert that _param_truthy is absent. | Cursor Build agent | `low` | S | `[T5]` | `plasticos_base/tests/test_matching_engine_gate_url.py`, `plasticos_base/tests/__init__.py` |
| T7 | Add plasticos_admin_dashboard/tests/__init__.py and test_rep_performance_view.py. Leave plasticos_admin_dashboard/__init__.py as from . import models. TransactionCase, post_install,-at_install. Call plasticos.rep.performance.init(), then assert pg_class.relkind v for plasticos_rep_performance, information_schema columns rep_name, deals_closed, revenue_closed, gm_pct, commission, and period_sort, and search limit 1. Parameterize the relation name. Do not paste CREATE VIEW into the test. | Cursor Build agent | `medium` | M | `[T5]` | `plasticos_admin_dashboard/tests/__init__.py`, `plasticos_admin_dashboard/tests/test_rep_performance_view.py` |
| T8 | Remove class TestPhantomAuditReport from tests/test_phantom_enum_values.py. Leave the rest of the phantom-enum scanner. | Cursor Build agent | `low` | S | `[]` | `tests/test_phantom_enum_values.py` |
| T9 | Run V1 through V6. Search only the live tree. Exclude filetree.md, docs/reports/repo-index/, docs/campaigns/, and .cursor-commands/. Do not edit those paths to clear a hit. | Cursor Build agent | `medium` | M | `[T1, T2, T3, T4, T5, T6, T7, T8]` | `tests/test_suite_structure.py`, `tests/test_phantom_enum_values.py`, `plasticos_base/tests/test_matching_engine_gate_url.py`, `plasticos_admin_dashboard/tests/test_rep_performance_view.py` |

**Critical path:** T1 → T2 → T3 → T4 → T5 → T8 → T6 → T7 → T9

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | Superseded proofs and the vacuous printer are gone, and the suite-structure exemption matches the tree. | T6 and T7 can replace the deleted replica without a second owner |
| M2 | The Gate URL helpers and the rep-performance view are exercised by Odoo tests. | V3 and V4 |
| M3 | Ruff, pure pytest, both module tests, the hook catalog, and the scoped name search pass. | Build may publish |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | The CRM4 files, tests/e2e/four_repo, the Cypher test, and test_gap_fixes.py are gone, and NON_TEST_FILES does not name run_odoo_driver.py. | Stop. Do not run the CRM4 shell to recreate the SQL receipt. |
| C2 | M2 | The new tests call the helpers and init(). Neither test parses source for GATE_URL or column names. | Delete the source-text test if one was added and write the runtime tests instead. |
| C3 | M3 | V1, V2, V3, V4, V5, and V6 are passed. | Do not publish. Do not skip a failed module test and do not point it at a database other than the fixture. |

### Leverage

- **Ranked todos:** `T5`, `T1`, `T6`, `T7`, `T4`, `T2`, `T3`, `T8`, `T9`
- **Shared causes:** Proofs that cannot fail because they encode a superseded contract or a copy of retired code
- **Deletions / consolidations:** Delete the CRM4 shell trio instead of retargeting it at UniqueIndex; Delete the four-repo driver instead of repairing hop_trace and egress; Delete the Cypher scanner instead of failing an empty corpus; Delete tests/test_gap_fixes.py instead of maintaining its pasted copies; Do not add tests/test_source_contracts.py

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| tests/README.md | `update` | `T4` | It names the Cypher test and tells the reader to run it. |
| .coderabbit.yaml | `update` | `T4` | Its pure-Python include list names the Cypher test. |
| AGENTS.md | `n_a` | — | No command, module count, or CI contract changes. |
| INVARIANTS.md | `n_a` | — | No invariant text changes. The no-local-intelligence tests stay. |
| plasticos_*/__manifest__.py | `n_a` | — | Tests-only edits do not bump a module version and do not need make update. |
| filetree.md | `n_a` | — | March 2026 snapshot. Not a CI test list. |
| docs/reports/repo-index/ | `n_a` | — | The catalog already points at tests/modules/test_cypher_schema_alignment.py, which does not exist. Regenerating the index is a separate job. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01, SP-03, SP-06 | `quality_gate_evidence` | command | `ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py` | Both commands exit 0. | `not_run` |
| E-V2 | SP-01, SP-03 | `quality_gate_evidence` | command | `pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py` | Exit 0 and TestPhantomAuditReport is not collected. | `not_run` |
| E-V3 | SP-04 | `quality_gate_evidence` | command | `make test-module m=plasticos_base` | The fixture clone runs the new Gate URL tests and the module summary has no failure. Attached wait 600000 ms. Do not start V4 until this exits. | `not_run` |
| E-V4 | SP-05 | `quality_gate_evidence` | command | `make test-module m=plasticos_admin_dashboard` | The fixture clone named in config/test_env_fixture.conf runs test_rep_performance_view and the summary has no failure. Attached wait 600000 ms. | `not_run` |
| E-V5 | SP-01, SP-02 | `quality_gate_evidence` | command | `rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat\|crm4_selected_constraint\|four_repo\|run_odoo_driver\|test_gap_fixes\|test_cypher_schema_alignment\|test_source_contracts' .` | No hits. Hits under the excluded paths are ignored and are not edited. | `not_run` |
| E-V6 | SP-07 | `quality_gate_evidence` | command | `test -f .pre-commit-config.yaml && rg -n 'id: ruff\|id: ruff-format' .pre-commit-config.yaml` | The hook catalog exists and names the ruff and ruff-format hooks. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- If matching_engine_is_enabled reads an ICP string again, does the GATE_URL runtime test fail?
- If init() leaves a table, or omits one of the six columns, does the relkind and information_schema test fail?
- If the CRM4 shell is executed while the files are being deleted, can its failure trap remove the SQL receipt before git records the deletion?
- If tests/test_source_contracts.py is added instead of the Odoo tests, can a broken view still pass?

### Assumption failure conditions

- plasticos_material_profile/tests/test_nullable_form_uniqueness.py and plasticos_crm_bridge/tests/test_crm4_profile_reuse.py still lock the current identity and reuse behavior
- tests/conftest.py collect-ignores a module that imports odoo, so pure pytest does not prove the new Odoo tests
- The CRM4 shell is not executed

### Blast radius notes

- A leftover run_odoo_driver.py fails tests/test_suite_structure.py. A syntax error in the phantom-enum file fails the pure pytest gate. A failed admin-dashboard upgrade spends a fixture run and blocks V4. No production schema, constraint, or Gate contract changes.

### Rollback constraints

- Restore the deleted files from 2803c087e373d0ca6b871a35d44b14210b683e91 and remove the new test files. There is no migration to reverse. Do not run the CRM4 shell as a rollback.

### Risks

| risk | mitigation |
|------|------------|
| Executing the CRM4 shell deletes tests/crm4_selected_constraint.sql on failure. | T1 deletes the three files and forbids running the script. |
| plasticos_admin_dashboard has no tests package today. make test-module must upgrade it on the fixture clone. | V4 is that upgrade. A load failure stops the plan. Do not skip the test and do not use another database. |
| The GATE_URL test can leak a URL into later tests in the same process. | T6 saves and restores os.environ in try/finally for unset, blank, and set. |

## Out of scope

- Rewriting the CRM4 shell against UniqueIndex
- Repairing tests/e2e/four_repo or adding assertions to the GATE_URL-skipped live Gate test
- A tests/test_source_contracts.py source-text scan
- A second Odoo suite for intake partner sync or web-lead auth
- tests/runtime_gates/
- Module version bumps and make update
- filetree.md, docs/reports/repo-index/, docs/campaigns/, and .cursor-commands/
- plasticos_material_profile, plasticos_gate, and pipeline_v2.py
- The untracked docs/campaigns/11-03-26 campaign plan and the documents-loop work on this branch
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.retire_stale_test_proofs.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.retire_stale_test_proofs.v1` |
| source_ref | `plan.simple.retire_stale_test_proofs.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Is plasticos_admin_dashboard already installed on the fixture clone? — V4 still runs make test-module m=plasticos_admin_dashboard, which upgrades that module on the clone. A failed load stops publication. It does not change the test or the database choice. | `accept_bounded` |
| `open_blocker` | stop_reason | PLAN_DOCUMENT is the planning artifact. V1 through V6 stay pending until Build. Do not claim the cleanup is done. | planning convergence `partial` |

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
  plan_id: "plan.simple.retire_stale_test_proofs.v1"
  name: "Retire stale test proofs"
  overview: "Delete the superseded CRM4 constraint proof, the four-repo Gate driver, the Cypher alignment scanner, the replica tests in tests/test_gap_fixes.py, and the vacuous phantom-enum printer. Keep the runtime tests that already lock material identity, CRM4 profile reuse, Gate contracts, intake partner sync, web-lead auth, and the absence of local Neo4j matching. Replace only the two claims that would otherwise have no owner by calling matching_engine_is_enabled, matching_engine_should_skip_cron, matching_engine_require_enabled_for_ui, and plasticos.rep.performance.init() on the Docker test fixture. Do not add a source-text contract. Product architecture is already settled: the material identity is the partial unique index, Gate converge stays the three contract tests, and local Neo4j matching stays retired. GAR does not select a new architecture. The L9 architecture profile is not the product law for this Odoo suite, and the integrated cognitive runtime is not activated. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. Those records are unrelated GMP work and stay out of this change."
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
  commit_sha: "2803c087e373d0ca6b871a35d44b14210b683e91"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Delete the superseded CRM4 constraint proof, the four-repo Gate driver, the Cypher alignment scanner, the replica tests in tests/test_gap_fixes.py, and the vacuous phantom-enum printer. Keep the runtime tests that already lock material identity, CRM4 profile reuse, Gate contracts, intake partner sync, web-lead auth, and the absence of local Neo4j matching. Replace only the two claims that would otherwise have no owner by calling matching_engine_is_enabled, matching_engine_should_skip_cron, matching_engine_require_enabled_for_ui, and plasticos.rep.performance.init() on the Docker test fixture. Do not add a source-text contract. Product architecture is already settled: the material identity is the partial unique index, Gate converge stays the three contract tests, and local Neo4j matching stays retired. GAR does not select a new architecture. The L9 architecture profile is not the product law for this Odoo suite, and the integrated cognitive runtime is not activated. MEMORY_PREFETCH namespace=ib-odoo-19 snapshot_digest=f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts=0. Those records are unrelated GMP work and stay out of this change."
  success_properties:
    - id: "SP-01"
      property: "The three CRM4 proof files and tests/e2e/four_repo are absent, and tests/test_suite_structure.py does not name run_odoo_driver.py. Proved by V5."
      evidence_type: "quality_gate"
      proof: ["V1", "V2", "V5"]
      blocking: true
    - id: "SP-02"
      property: "tests/test_cypher_schema_alignment.py and tests/test_gap_fixes.py are absent, and tests/README.md plus .coderabbit.yaml do not name the Cypher test. Proved by V5."
      evidence_type: "quality_gate"
      proof: ["V5"]
      blocking: true
    - id: "SP-03"
      property: "TestPhantomAuditReport is absent and pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py passes. Proved by V2."
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-04"
      property: "Unset, blank, and set GATE_URL drive the three matching-engine helpers under make test-module m=plasticos_base. Proved by V3."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-05"
      property: "plasticos.rep.performance.init() leaves relkind v, the six columns, and a successful search under make test-module m=plasticos_admin_dashboard. Proved by V4."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
    - id: "SP-06"
      property: "ruff check and ruff format pass on the touched Python files. Proved by V1."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-07"
      property: "The hook catalog .pre-commit-config.yaml names the ruff and ruff-format hooks that cover the touched Python files. Proved by V6."
      evidence_type: "quality_gate"
      proof: ["V6"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.retire_stale_test_proofs.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/crm4_constraint_compat.sh", "tests/crm4_constraint_compat_negative.sh", "tests/crm4_selected_constraint.sql", "tests/e2e/four_repo/", "tests/test_suite_structure.py", "tests/test_cypher_schema_alignment.py", "tests/test_gap_fixes.py", "tests/test_phantom_enum_values.py", "tests/README.md", ".coderabbit.yaml", "plasticos_base/tests/__init__.py", "plasticos_base/tests/test_matching_engine_gate_url.py", "plasticos_admin_dashboard/tests/__init__.py", "plasticos_admin_dashboard/tests/test_rep_performance_view.py"]
    write_deny: ["plasticos_material_profile/models/material_profile.py", "plasticos_gate/", "pipeline_v2.py", "tests/runtime_gates/", "tests/integration/test_gate_external_authority_e2e.py", "filetree.md", "docs/reports/repo-index/", "docs/campaigns/", ".cursor-commands/", "plasticos_base/__init__.py", "plasticos_admin_dashboard/__init__.py", "plasticos_base/__manifest__.py", "plasticos_admin_dashboard/__manifest__.py"]
  commands:
    allow: ["ruff check and ruff format --check on the touched Python files", "pytest tests/test_suite_structure.py tests/test_phantom_enum_values.py", "make test-module m=plasticos_base", "make test-module m=plasticos_admin_dashboard", "scoped rg for the deleted names", "test -f .pre-commit-config.yaml && rg ruff hooks", "ruff check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py && ruff format --check plasticos_base/tests/test_matching_engine_gate_url.py plasticos_base/tests/__init__.py plasticos_admin_dashboard/tests/test_rep_performance_view.py plasticos_admin_dashboard/tests/__init__.py tests/test_suite_structure.py tests/test_phantom_enum_values.py", "rg -n --glob '!.cursor-commands/**' --glob '!filetree.md' --glob '!docs/reports/repo-index/**' --glob '!docs/campaigns/**' 'crm4_constraint_compat|crm4_selected_constraint|four_repo|run_odoo_driver|test_gap_fixes|test_cypher_schema_alignment|test_source_contracts' .", "test -f .pre-commit-config.yaml && rg -n 'id: ruff|id: ruff-format' .pre-commit-config.yaml"]
  network:
    mode: "none"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "destructive_filesystem_mutation"
    idempotency: "unsafe_blind_repeat"
    retry: "manual_only"
  - todo_id: "T2"
    side_effects: "destructive_filesystem_mutation"
    idempotency: "unsafe_blind_repeat"
    retry: "manual_only"
  - todo_id: "T3"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T4"
    side_effects: "destructive_filesystem_mutation"
    idempotency: "unsafe_blind_repeat"
    retry: "manual_only"
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
rollback_contract_ref: "rollback.plan.simple.retire_stale_test_proofs.v1"
dependency_topology_ref: "dag.plan.simple.retire_stale_test_proofs.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6"]
stress_and_disconfirm:
  disconfirming_cases: ["If matching_engine_is_enabled reads an ICP string again, does the GATE_URL runtime test fail?", "If init() leaves a table, or omits one of the six columns, does the relkind and information_schema test fail?", "If the CRM4 shell is executed while the files are being deleted, can its failure trap remove the SQL receipt before git records the deletion?", "If tests/test_source_contracts.py is added instead of the Odoo tests, can a broken view still pass?"]
  assumption_failure_conditions: ["plasticos_material_profile/tests/test_nullable_form_uniqueness.py and plasticos_crm_bridge/tests/test_crm4_profile_reuse.py still lock the current identity and reuse behavior", "tests/conftest.py collect-ignores a module that imports odoo, so pure pytest does not prove the new Odoo tests", "The CRM4 shell is not executed"]
out_of_scope: ["Rewriting the CRM4 shell against UniqueIndex", "Repairing tests/e2e/four_repo or adding assertions to the GATE_URL-skipped live Gate test", "A tests/test_source_contracts.py source-text scan", "A second Odoo suite for intake partner sync or web-lead auth", "tests/runtime_gates/", "Module version bumps and make update", "filetree.md, docs/reports/repo-index/, docs/campaigns/, and .cursor-commands/", "plasticos_material_profile, plasticos_gate, and pipeline_v2.py", "The untracked docs/campaigns/11-03-26 campaign plan and the documents-loop work on this branch"]
convergence_contract_ref: "conv.plan.simple.retire_stale_test_proofs.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Delete the three CRM4 constraint proof files together. Do not execute tests/crm4_constraint_compat.sh. A failed run deletes tests/crm4_selected_constraint.sql."
    status: "pending"
  - id: "T2"
    content: "Delete tests/e2e/four_repo/run_odoo_driver.py and tests/e2e/four_repo/README.md, and remove the directory."
    status: "pending"
  - id: "T3"
    content: "In the same change as T2, remove run_odoo_driver.py from NON_TEST_FILES and delete the four-repo comment in tests/test_suite_structure.py."
    status: "pending"
  - id: "T4"
    content: "Delete tests/test_cypher_schema_alignment.py. Remove its row and pytest example from tests/README.md. Remove it from the pure-Python include list in .coderabbit.yaml. Do not turn the drift skip into a failure."
    status: "pending"
  - id: "T5"
    content: "Delete tests/test_gap_fixes.py. Do not replace it with a source-text scan. Intake sync and web-lead auth already have runtime tests."
    status: "pending"
  - id: "T6"
    content: "Add plasticos_base/tests/test_matching_engine_gate_url.py and import it from plasticos_base/tests/__init__.py. Do not import tests from plasticos_base/__init__.py. Use PlasticosTestCase and post_install,-at_install. Save and restore GATE_URL. Unset and whitespace-only values make matching_engine_is_enabled false, matching_engine_should_skip_cron true, and matching_engine_require_enabled_for_ui raise UserError. A non-empty URL reverses those three results. Do not assert that _param_truthy is absent."
    status: "pending"
  - id: "T7"
    content: "Add plasticos_admin_dashboard/tests/__init__.py and test_rep_performance_view.py. Leave plasticos_admin_dashboard/__init__.py as from . import models. TransactionCase, post_install,-at_install. Call plasticos.rep.performance.init(), then assert pg_class.relkind v for plasticos_rep_performance, information_schema columns rep_name, deals_closed, revenue_closed, gm_pct, commission, and period_sort, and search limit 1. Parameterize the relation name. Do not paste CREATE VIEW into the test."
    status: "pending"
  - id: "T8"
    content: "Remove class TestPhantomAuditReport from tests/test_phantom_enum_values.py. Leave the rest of the phantom-enum scanner."
    status: "pending"
  - id: "T9"
    content: "Run V1 through V6. Search only the live tree. Exclude filetree.md, docs/reports/repo-index/, docs/campaigns/, and .cursor-commands/. Do not edit those paths to clear a hit."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-05T16:00:56Z`
- conversation_id: `8b7210e1-30e4-4554-9ad1-8bc7a28aeea7`
- generation_id: `d90901b0-5437-4c9e-8ce6-a16e5d2dccb1`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/8b7210e1-30e4-4554-9ad1-8bc7a28aeea7/8b7210e1-30e4-4554-9ad1-8bc7a28aeea7.jsonl`
- todos at build time:
- `T1`: completed
- `T2`: completed
- `T3`: completed
- `T4`: completed
- `T5`: completed
- `T6`: completed
- `T7`: completed
- `T8`: completed
- `T9`: completed
