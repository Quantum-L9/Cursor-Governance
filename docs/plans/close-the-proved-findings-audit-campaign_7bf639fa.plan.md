---
name: Close the proved-findings audit campaign
overview: "Finish fix/audit-proved-findings by reusing the field registry and the pinned defusedxml parser, hoisting the constant document-rule search, and proving the result on the pinned test fixture. A write of different values per record stays, because one write cannot carry those values."
todos:
  - id: T1
    content: "Make the field and query scanners describe and enforce one rule: inherit fields are visible to depends and onchange, unresolved views stay silent, and a loop write is a finding only when the values are identical"
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Parse repository XML with the pinned defusedxml parser, delete the nosec markers on those calls, and copy the two cron lock files onto the branch"
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Search plasticos.document.rule once before the missing-document transaction loop, keeping the current domain"
    status: pending
    phase: execute
    depends_on: []
  - id: T4
    content: "Rescan, run the scanner and cron tests, and run fixture tests for every module whose Python behavior changed"
    status: pending
    phase: execute
    depends_on: [T1, T2, T3]
  - id: T5
    content: "Upgrade the already bumped modules only when Docker mounts this worktree"
    status: pending
    phase: execute
    depends_on: [T4]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Close the proved-findings audit campaign

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

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `close-the-proved-findings-audit-campaign_7bf639fa.plan.md`

## Objective (from PLAN_DOCUMENT)

Finish fix/audit-proved-findings by reusing the field registry and the pinned defusedxml parser, hoisting the constant document-rule search, and proving the result on the pinned test fixture. A write of different values per record stays, because one write cannot carry those values.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | scripts/audit/odoo_audit.py describes the same rule it enforces: an unresolved view emits nothing, and depends and onchange checks use the same inherit registry as constraints | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | A write inside a loop is a finding only when every item would receive the same values; a write of different values per item is not a finding, and plasticos_enrichment/models/enrichment_run.py is not rewritten to hide those writes | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | cron_check_missing_docs searches plasticos.document.rule once, before the transaction loop, with the same domain | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | Every repository XML parse named in this plan imports defusedxml.ElementTree and the nosec marker on that parse is gone | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | tests/test_cron_xml_lock.py and tests/cron_contract.py are on fix/audit-proved-findings, and the lock test imports defusedxml.ElementTree | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | run_baseline_gate.sh reports no new CRITICAL or HIGH finding and the three proved types stay absent from both baseline files | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-07 | The pinned Docker test fixture runs the tests of every plasticos module whose Python behavior changed, and make update of those modules runs only when that worktree is the tree Docker mounts | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** Worktree /Users/ib-mac/IB-Odoo_19 (LOCAL)/wt-audit-truth on branch fix/audit-proved-findings, scripts/audit/odoo_audit.py docstring, depends check, and onchange check, scripts/audit/performance_audit.py identical-values write rule and its unit tests, plasticos_documents/models/transaction_docs.py cron_check_missing_docs rule search, Stdlib XML parses in tools/cron_invariant_check.py, tests/test_xpath_anchor_topology.py, tests/test_odoo19_compat.py, ci/check_xpath_stability.py, ci/check_state_guard_bypass.py, ci/check_automation_field_refs.py, Copy of the two untracked cron files from the main checkout onto this branch, Fixture tests and a mount-checked module upgrade of the modules already bumped on this branch

**Out:**
- 27 unbounded searches and 19 unjustified sudo calls; they are a later campaign
- CRM roadmap README failure and VanillaSoft phantom enums on the other branch
- pipeline_v2.py and enrichment feature wiring
- A batch write helper or a nested function whose only job is to hide enrichment profile writes
- New baseline allowlist rows
- A new test-database template or a second Docker Compose project
- Any other dirty file in the main checkout
- ci and tools parsers beyond the six named XML entry points

## Critical path (seed)

T1 → T3 → T2 → T4 → T5

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: A wrong inherit-field check can hide a real missing field or fail the baseline gate. A wrong Docker mount can upgrade the wrong tree. A rejected XML parse stops the cron and CI parsers that read repository XML.
- Rollback: The branch is uncommitted. Restore the worktree with git checkout -- on the touched paths and remove the two copied cron files if they were the only additions. Do not reset the dirty main checkout.

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: Architecture is selected and the plan is validated. Implementation starts when Build is pressed. U1 is probed before the upgrade and does not block the code edits.
- execute_via: cursor-build

---

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.plasticos.audit-closeout.v1` |
| name | Close the proved-findings audit campaign |
| overview | Finish the uncommitted `fix/audit-proved-findings` worktree by reusing the field registry and pinned `defusedxml`, hoisting one constant search, and proving the result on the pinned fixture |
| schema_version | `1.0.0` |
| status | `current` |
| is_project | false |
| owner | igor_beylin |
| created_at | 2026-10-28 |
| updated_at | 2026-10-28 |

## Architect framing

GAR selected `USE_EXISTING` before this document was emitted. The field registry `_fields_on_model` already exists. `defusedxml==0.7.1` is already pinned. The document-rule search already exists and does not use the loop item. The enrichment profile write already applies different values per profile.

First-order compression stops at three edits. One registry reuse covers depends and onchange. One parser covers the named XML entry points. One hoist covers the missing-document cron. A fourth system that batches distinct writes is invalid: one `write` applies one values dict. Those writes stay in `plasticos_enrichment/models/enrichment_run.py`, and that file is not modified.

L9 architecture profile was loaded and is not a live inventory. Integration mode is `STANDALONE`. Reasoning materiality is `MATERIAL`. Second-order before: inherit-aware checks can surface a real missing field, and that finding is fixed in code rather than allowlisted; `defusedxml` fails closed on entity expansion; the Docker mount is probed before any upgrade. Predicted leverage: the nosec markers, the per-transaction rule search, and the stale unresolved-view sentences become unnecessary. Signal recipients are the baseline gate and the operator who upgrades. No Gate route is selected.

MEMORY_PREFETCH snapshot `84285faaaf0ae34c9b231c0df0fb2c0098797dc2f04b98b31dc5e64450f3ee44`, conflicts 0. Those records are other campaigns and are not absorbed.

| Field | Value |
|-------|-------|
| planning_ssot | `l9-plan-simple` cursor-build projection of PLAN_DOCUMENT |
| plan_class | `remediation_plan` |
| redesign_allowed | false |
| follow_on_schema_evolution_separate | true |
| framing_notes | Intervention class USE_EXISTING. Distinct per-record writes are residual work, not a new design. |

## Immutable baseline

| Field | Value |
|-------|-------|
| bound_tree | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/wt-audit-truth` |
| branch | `fix/audit-proved-findings` |
| base | `Staging` `04bd0594` |
| dirty | uncommitted scanner, product, and baseline edits; `plasticos_material_profile/models/coded_master.py` untracked |
| excluded_tree | dirty main checkout, except a read of `tests/test_cron_xml_lock.py` and `tests/cron_contract.py` |
| excluded_tree_2 | CRM worktree `wt-pr-079a13df` |
| hook_catalog | `.pre-commit-config.yaml` |
| test_fixture | `config/test_env_fixture.conf` database `odoo_test_tpl_ee_c9e8a81f52f23680` |
| on_drift | stop and replan |

## Objective

### Mission

Close the proved-findings campaign on the existing branch. The scanners report a missing inherited field, a per-item lookup, and a write of identical values. They stay silent for an unresolved view, a page cursor, a savepoint command, and a write whose values differ per record.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| S1 | Depends and onchange use the inherit registry, and the module docstring matches that rule | structural | `tests/test_odoo_audit_field_attribution.py` | yes |
| S2 | An identical-values loop write is a finding and a differing-values loop write is not | structural | `tests/test_audit_n_plus_one.py` | yes |
| S3 | The missing-document cron searches rules once | structural | the search call sits before `for tx in transactions` | yes |
| S4 | Named XML parses import `defusedxml.ElementTree` and carry no nosec marker | filesystem | `rg` over the six named files | yes |
| S5 | The cron lock files are on this branch and the lock test passes | quality_gate | `pytest tests/test_cron_xml_lock.py` | yes |
| S6 | The baseline gate stays green with none of the three proved types | quality_gate | `bash scripts/audit/run_baseline_gate.sh` | yes |
| S7 | Changed-module Odoo tests pass on the pinned fixture | runtime_behavior | `make test-module` per changed module | yes |
| S8 | Live upgrade runs only when Docker mounts this worktree | runtime_behavior | mount probe recorded before `make update` | yes |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.plasticos.audit-closeout.v1` |
| source_ref | `plan.plasticos.audit-closeout.v1` |
| phase_id | `preflight` |
| blocking | true |
| immutable_baseline_ref | worktree `fix/audit-proved-findings` |
| baseline_verified | true |
| drift_detected | false |
| memory_prefetch | `84285faaaf0ae34c9b231c0df0fb2c0098797dc2f04b98b31dc5e64450f3ee44` conflicts 0 |
| depth | deep |

Probes already passed: the worktree is the bound tree, the two cron files exist only as untracked files in the main checkout, and `route_plan.py` returned depth `deep` with no omitted gates.

## Execution envelope

Work only inside `wt-audit-truth` on `fix/audit-proved-findings`.

T1. In `scripts/audit/odoo_audit.py`, point depends and onchange checks at `_fields_on_model`. Replace the module sentences that still call `UNRESOLVED_VIEW_CONTEXT` and `UNRESOLVED_VIEW_MODEL` gated findings. In `scripts/audit/performance_audit.py`, emit `N_PLUS_ONE_QUERY` for a `write` only when the values dict is the same for every loop item. Add the two fixtures. Do not edit `plasticos_enrichment/models/enrichment_run.py`.

T3. Replace `import xml.etree.ElementTree` with `import defusedxml.ElementTree as ET` in `tools/cron_invariant_check.py`, `tests/test_xpath_anchor_topology.py`, `tests/test_odoo19_compat.py`, `ci/check_xpath_stability.py`, `ci/check_state_guard_bypass.py`, and `ci/check_automation_field_refs.py`. Delete the `nosec` comment on each of those parses. Copy only `tests/test_cron_xml_lock.py` and `tests/cron_contract.py` from the main checkout. The lock test already imports `defusedxml`.

T2. In `plasticos_documents/models/transaction_docs.py` `cron_check_missing_docs`, run the `plasticos.document.rule` search once before `for tx in transactions`. Keep the domain `[("res_model", "=", "plasticos.transaction"), ("active", "=", True)]` and `order="id ASC"`. Do not bump `plasticos_documents` again: `19.0.2.1.3` is already the uncommitted version and has not been upgraded.

T4. From the worktree, run the pytest files in final validation V1, then `bash scripts/audit/run_baseline_gate.sh`. Then `make test-module` for `plasticos_material_profile`, `plasticos_facility_profile`, `plasticos_transaction`, `plasticos_claims`, `plasticos_automation`, `plasticos_offer`, `plasticos_crm_bridge`, `plasticos_intake`, `plasticos_documents`, `plasticos_logistics`, and `plasticos_enrichment`. The clone source is only `config/test_env_fixture.conf`. Do not set `TEST_ENV_ALLOW_NEW_TEMPLATE`. Do not set `TEST_ENV_PARITY=community`.

T5. Read the running Compose project's mount for `/mnt/extra-addons`. If it is this worktree, run `make update m=plasticos_material_profile,plasticos_facility_profile,plasticos_transaction,plasticos_claims,plasticos_automation,plasticos_offer,plasticos_crm_bridge,plasticos_intake,plasticos_documents,plasticos_logistics,plasticos_enrichment`. If it is another tree, do not upgrade that database and do not start a second Compose project. The fixture result remains the runtime proof.

## Side effects and idempotency

| id | side effect | idempotent | reversal |
|----|-------------|------------|----------|
| E1 | Scanner and test edits on the branch | yes, until commit | `git checkout --` those paths in the worktree |
| E2 | Two cron files copied onto the branch | yes | delete the copies if they were not previously on the branch |
| E3 | `defusedxml` rejects an entity payload | yes | repair the XML; do not restore the stdlib parser |
| E4 | Fixture clone upgraded with `-u` of the changed modules | yes, per clone | the clone is disposable; the template is not rebuilt |
| E5 | Live `make update` when the mount matches | yes, per module version | do not downgrade; fix forward on a new patch only after this version has been applied |

Copying the cron files does not stage any other file from the main checkout. Enrichment profile writes are unchanged.

## Architecture impact

No new model, module, or parser dependency. `plasticos.coded.master` is already the uniqueness owner on this branch and is not redesigned. Depends and onchange join the constraint check on the existing registry. XML entry points join the parser `tests/test_phantom_enum_values.py` already uses. The proof rule gains one case: identical `write` values are one write; different values are the record's own command.

## Rollback

The branch is uncommitted. Restore touched tracked paths in the worktree with `git checkout --` and remove the two copied cron files if this plan added them. Do not reset, clean, or switch the dirty main checkout. Do not drop the test-fixture database. If a live upgrade already ran, leave that database on the applied version and fix forward.

## Complexity and uncertainty

Depth is `deep`. The code edits are local. The high-risk steps are the fixture test run and the mount check, because a wrong database or a wrong tree would hide the result. U1 stays open until T5 probes the mount. It does not block T1, T2, or T3.

## Execution DAG

```text
T1 scanners ──┐
T3 defusedxml ┼──> T4 fixture and baseline gate ──> T5 mount-checked upgrade
T2 hoist ─────┘
```

T1, T2, and T3 have no dependencies on each other. T4 waits for all three. T5 waits for T4.

## Property evidence matrix

| property | todo | proof |
|----------|------|-------|
| S1 | T1 | field attribution tests |
| S2 | T1 | n-plus-one tests, both write cases |
| S3 | T2 | search sits before the transaction loop |
| S4 | T3 | no stdlib ElementTree import and no nosec on those parses |
| S5 | T3 | cron lock pytest on the worktree |
| S6 | T4 | `run_baseline_gate.sh` |
| S7 | T4 | `make test-module` per changed module |
| S8 | T5 | recorded mount path before any `make update` |

## Stress and disconfirm

Disconfirming questions:

- A new depends or onchange finding is fixed in the model or the registry. A baseline row is not added.
- Repository XML that `defusedxml` rejects is repaired or accepted as fail-closed. The stdlib import is not restored.
- The enrichment merge cannot become one write without dropping per-profile values, so that file stays untouched.
- `make update` does not run when Compose mounts a tree other than `wt-audit-truth`.

Assumptions that must stay false: a `nosec` comment closes an XML parse; a nested function closes an N+1 write; the uncommitted version bumps are bumped again before their first upgrade; other dirty main-checkout files join this branch.

Blast radius: a wrong field check hides or invents a gated finding, a wrong mount upgrades the wrong tree, and a rejected XML file stops the parser that reads it.

## Out of scope

- The 27 unbounded searches and 19 unjustified `sudo()` calls.
- The CRM roadmap README failure and the VanillaSoft phantom-enum failure.
- `pipeline_v2.py` and enrichment feature wiring.
- A helper whose only purpose is to hide the enrichment profile writes.
- A new test-database template, a second Compose project, and `make update-all`.
- Any main-checkout file other than the two cron files being copied.

## Convergence

| Field | Value |
|-------|-------|
| status | `partial` |
| remaining_unknown | U1, the Docker mount, probed at T5 |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| stop_reason | The plan is validated. Code edits wait for Build. U1 does not block those edits. |

`validate_plan_document.py` PASSed `.l9/plans/close_audit_campaign.plan.json` before this projection was written.
