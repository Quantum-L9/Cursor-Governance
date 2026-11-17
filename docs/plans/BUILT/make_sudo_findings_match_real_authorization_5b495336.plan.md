---
name: Make sudo findings match real authorization
overview: Make a green UNJUSTIFIED_SUDO result mean every remaining .sudo() has a
  same-line reason that matches the check above it, delete elevations that add no
  privilege, and let the existing HIGH audit gate reject the next bare call.
todos:
- id: T1
  content: 'Lock the scanner contract in tests/test_unjustified_sudo_scanner.py. A
    preceding-line comment stays a finding. A same-line comment that does not start
    with # sudo: or # cron-sudo-justification: stays a finding. An empty marker and
    a debt-marker reason stay findings. Do not change _is_sudo_justification or _sudo_call_lines.'
  status: completed
- id: T2
  content: Delete elevations that add no privilege. At linda_request.py:796 remove
    .sudo() and the comment above it that names a caller who is already superuser;
    _check_evidence_writer still refuses a non-superuser. At facility_profile.py:290
    remove .sudo() and its comment; internal users can already read mail.scheduled.message.
    At crm_tag_adoption.py lines 47, 51, and 52 remove .sudo() on the installer creates;
    the XML function and the pre-migrate already run as superuser. Do not remove the
    reads at lines 24 and 33.
  status: completed
- id: T3
  content: Replace reasons that do not match the code. In _currently_eligible the
    checksum sudo must say it reads the checksum of the attachment already linked
    to this document. It must not say a command check ran; compliance_service.py and
    the scale-ticket scan call that method with no verifier check. On document.py:426,
    document.py:448, transaction_docs.py:71, and transaction_docs.py:98 the reason
    must say the write sets compliance flags for a document the caller can already
    write, and that the group_user full-access row still admits every internal user.
    Do not edit the ACL CSV.
  status: completed
- id: T4
  content: Put the existing true reason on the .sudo() line with the required prefix.
    Cover mail_mail_inherit.py lines 33, 34, 66, 89, and 191; linda_response.py lines
    207, 209, and 216; linda_request.py lines 328, 593, 708, and 833; invoice_reminder.py
    line 39; account_move_inherit.py line 38; commission_payout.py line 132; crm_tag_adoption.py
    lines 24 and 33; document.py lines 540, 621, 660, 754, 764, and 793; document_native.py
    line 540. Keep the ir.model.data read elevations. A verifier or override check
    may be named only on a line that runs after that check.
  status: completed
- id: T5
  content: Resolve U1 before editing facility_profile.py:307. Read the core mail.message
    access rule. If base.group_user can already read the row and write res_id, delete
    that sudo and its comment. If not, keep the sudo and set the same-line reason
    to the profile merge moving that profile's own chatter, which the sync caller
    cannot write. Do not add a group and do not edit line 322. The only production
    caller is orchestrator.py link_verified_location.
  status: completed
- id: T6
  content: Regenerate extended_audit_report.json and require zero UNJUSTIFIED_SUDO.
    Only then change that finding's severity in business_logic_audit.py from MODERATE
    to HIGH, and assert the bare-call fixture reports HIGH. Do not change the marker
    regex. Do not add a baseline entry. Do not add a CI job. The existing HIGH diff
    is the gate.
  status: completed
- id: T7
  content: 'Bump the patch version in __manifest__.py once for each module whose Python
    changed: plasticos_logistics, plasticos_crm_bridge, plasticos_documents, plasticos_documents_native,
    plasticos_transaction, plasticos_commission, and plasticos_automation. Run ruff
    format on each manifest. Do not bump a module whose files were not edited.'
  status: completed
- id: T8
  content: Run V1, V2, V3, and V4. V2 passes on a zero UNJUSTIFIED_SUDO count even
    if the process exits 1 for the baselined enrichment N_PLUS_ONE_QUERY. Do not start
    T6's severity edit until that count is zero.
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Make sudo findings match real authorization

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `make_sudo_findings_match_real_authorization_5b495336.plan.md`
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
| plan_id | `plan.simple.make_sudo_findings_match_real_authorization.v1` |
| name | Make sudo findings match real authorization |
| overview | Make a green UNJUSTIFIED_SUDO result mean every remaining .sudo() has a same-line reason that matches the check above it, delete elevations that add no privilege, and let the existing HIGH audit gate reject the next bare call. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-06T16:10:09+00:00 |
| updated_at | 2026-11-06T16:10:09+00:00 |
| depth | `deep` |
| estimate | one implementation pass |

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
| captured_at | `2026-11-06T16:10:09+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `fix/enrichment-batch-profile-create` |
| commit_sha | `e822dbda7fa1833a9b5fca3b7f66e41e055a701a` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Make a green UNJUSTIFIED_SUDO result mean every remaining .sudo() has a same-line reason that matches the check above it, delete elevations that add no privilege, and let the existing HIGH audit gate reject the next bare call.

### Scope in

- Lock the same-line marker in tests/test_unjustified_sudo_scanner.py
- Delete sudo that adds no privilege at linda_request.py:796, facility_profile.py:290, and the crm_tag_adoption creates
- Rewrite false or too-wide reasons and move true reasons onto the .sudo() line
- Probe mail.message ACL before deciding facility_profile.py:307
- Raise UNJUSTIFIED_SUDO from MODERATE to HIGH only after the count is zero
- Bump each touched module version once

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 tests/test_unjustified_sudo_scanner.py still flags a preceding-line comment and a prefix-less same-line comment as UNJUSTIFIED_SUDO, and a bare .sudo() finding has severity HIGH | `quality_gate` | V1: `python3 -m pytest tests/test_unjustified_sudo_scanner.py` → PASS, including the preceding-comment rejection and severity HIGH on a bare call; V2: `python3 scripts/audit/run_all_audits.py .` → extended_audit_report.json contains zero UNJUSTIFIED_SUDO | `true` |
| SP-02 | V2 scripts/audit/run_all_audits.py writes extended_audit_report.json with zero UNJUSTIFIED_SUDO. Exit 1 is still allowed while the baselined N_PLUS_ONE_QUERY on enrichment_run.py remains | `quality_gate` | V2: `python3 scripts/audit/run_all_audits.py .` → extended_audit_report.json contains zero UNJUSTIFIED_SUDO | `true` |
| SP-03 | V3 .pre-commit-config.yaml passes on the changed Python | `quality_gate` | V3: `.pre-commit-config.yaml` → pre-commit passes on the changed Python files | `true` |
| SP-04 | V4 make test-module passes once for each bumped module | `quality_gate` | V4: `make test-module m=plasticos_logistics` → the same target passes for plasticos_logistics, plasticos_crm_bridge, plasticos_documents, plasticos_documents_native, plasticos_transaction, plasticos_commission, and plasticos_automation | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.make_sudo_findings_match_real_authorization.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.make_sudo_findings_match_real_authorization.v1` |
| source_ref | `plan.simple.make_sudo_findings_match_real_authorization.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.make_sudo_findings_match_real_authorization.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `git rev-parse --abbrev-ref HEAD and git status --porcelain at /Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` | branch fix/enrichment-batch-profile-create at 62cb3cfc and a clean porcelain | `true` |
| P1 | pre-validation (status `passed`) | `python3 ops/hooks/plan_memory_prefetch.py --workspace . --task sudo authorization` | MEMORY_PREFETCH namespace ib-odoo-19 snapshot f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts 0 | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk high --evidence partial --json` | depth deep and omit_gates empty | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `tests/test_unjustified_sudo_scanner.py`, `scripts/audit/business_logic_audit.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_logistics/models/linda_response.py`, `plasticos_logistics/models/mail_mail_inherit.py`, `plasticos_logistics/__manifest__.py`, `plasticos_crm_bridge/models/facility_profile.py`, `plasticos_crm_bridge/models/crm_tag_adoption.py`, `plasticos_crm_bridge/__manifest__.py`, `plasticos_documents/models/document.py`, `plasticos_documents/models/transaction_docs.py`, `plasticos_documents/__manifest__.py`, `plasticos_documents_native/models/document_native.py`, `plasticos_documents_native/__manifest__.py`, `plasticos_transaction/models/account_move_inherit.py`, `plasticos_transaction/__manifest__.py`, `plasticos_commission/models/commission_payout.py`, `plasticos_commission/__manifest__.py`, `plasticos_automation/models/invoice_reminder.py`, `plasticos_automation/__manifest__.py`
- **write_deny:** `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322`
- **delete_allow:** `plasticos_logistics/models/linda_request.py`, `plasticos_crm_bridge/models/facility_profile.py`, `plasticos_crm_bridge/models/crm_tag_adoption.py`

### Commands

- **allow:** `python3 -m pytest tests/test_unjustified_sudo_scanner.py`, `python3 scripts/audit/run_all_audits.py .`, `.pre-commit-config.yaml`, `make test-module m=plasticos_logistics`
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

- A preceding-line comment remains a finding
- A comment is not proof of authorization
- The ir.model.data read elevations stay
- No baseline entry is added for UNJUSTIFIED_SUDO
- No second CI job is added

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_unjustified_sudo_scanner.py` | `false` |
| T2 | `destructive_filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | `git restore -- plasticos_logistics/models/linda_request.py plasticos_crm_bridge/models/facility_profile.py plasticos_crm_bridge/models/crm_tag_adoption.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_documents/models/document.py plasticos_documents/models/transaction_docs.py` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_logistics/models/mail_mail_inherit.py plasticos_logistics/models/linda_response.py plasticos_logistics/models/linda_request.py plasticos_automation/models/invoice_reminder.py plasticos_transaction/models/account_move_inherit.py plasticos_commission/models/commission_payout.py plasticos_crm_bridge/models/crm_tag_adoption.py plasticos_documents/models/document.py plasticos_documents_native/models/document_native.py` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_crm_bridge/models/facility_profile.py` | `false` |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- scripts/audit/business_logic_audit.py tests/test_unjustified_sudo_scanner.py` | `false` |
| T7 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_logistics/__manifest__.py plasticos_crm_bridge/__manifest__.py plasticos_documents/__manifest__.py plasticos_documents_native/__manifest__.py plasticos_transaction/__manifest__.py plasticos_commission/__manifest__.py plasticos_automation/__manifest__.py` | `false` |
| T8 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/test_unjustified_sudo_scanner.py scripts/audit/run_all_audits.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `tests` | `assurance` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T2 | `repository root` | `runtime` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T3 | `plasticos_documents/models` | `runtime` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T4 | `repository root` | `runtime` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T5 | `plasticos_crm_bridge/models` | `runtime` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T6 | `repository root` | `assurance` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T7 | `repository root` | `runtime` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |
| T8 | `repository root` | `assurance` | `A preceding-line comment remains a finding`, `A comment is not proof of authorization`, `The ir.model.data read elevations stay`, `No baseline entry is added for UNJUSTIFIED_SUDO`, `No second CI job is added` | `plasticos_documents/security/ir.model.access.csv`, `plasticos_base/security/ir.model.access.csv`, `ci/baselines/extended_audit_baseline.json`, `plasticos_enrichment/models/enrichment_run.py`, `scripts/audit/performance_audit.py`, `plasticos_inference_engine/pipeline_v2.py`, `plasticos_crm_bridge/models/facility_profile.py line 322` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.make_sudo_findings_match_real_authorization.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.make_sudo_findings_match_real_authorization.v1` |
| source_execution_ref | `plan.simple.make_sudo_findings_match_real_authorization.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | C1 fails (V1 red tests fail before the scanner is loosened and pass with the scanner unchanged) → stop and revert any change to the marker regex; C2 fails (extended_audit_report.json has zero UNJUSTIFIED_SUDO before the severity change) → do not raise the severity and do not add baseline entries; C3 fails (a bare sudo fixture is HIGH and the regenerated report still has zero UNJUSTIFIED_SUDO) → revert the severity change |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the feature branch. No schema migration. Do not edit ci/baselines/extended_audit_baseline.json. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/test_unjustified_sudo_scanner.py`
- re-run `python3 scripts/audit/run_all_audits.py .`
- re-run `.pre-commit-config.yaml`
- re-run `make test-module m=plasticos_logistics`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 8 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `high` — Removing a necessary sudo raises AccessError on order confirm, mail send, document verification, or CRM sync. Raising severity too early turns the 34 rows into a red HIGH gate. |
| architectural_boundaries_crossed | `sudo comment contract to the existing HIGH audit gate`, `model elevation to ir.model.access without editing ACL rows` |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.make_sudo_findings_match_real_authorization.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.make_sudo_findings_match_real_authorization.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Lock the scanner contract in tests/test_unjustified_sudo_scanner.py. A preceding-line comment stays a finding. A same-line comment that does not start with # sudo: or # cron-sudo-justification: stays a finding. An empty marker and a debt-marker reason stay findings. Do not change _is_sudo_justification or _sudo_call_lines. | Cursor Build agent | `low` | S | `[]` | `tests/test_unjustified_sudo_scanner.py` |
| T2 | Delete elevations that add no privilege. At linda_request.py:796 remove .sudo() and the comment above it that names a caller who is already superuser; _check_evidence_writer still refuses a non-superuser. At facility_profile.py:290 remove .sudo() and its comment; internal users can already read mail.scheduled.message. At crm_tag_adoption.py lines 47, 51, and 52 remove .sudo() on the installer creates; the XML function and the pre-migrate already run as superuser. Do not remove the reads at lines 24 and 33. | Cursor Build agent | `high` | S | `[T1]` | `plasticos_logistics/models/linda_request.py`, `plasticos_crm_bridge/models/facility_profile.py`, `plasticos_crm_bridge/models/crm_tag_adoption.py` |
| T3 | Replace reasons that do not match the code. In _currently_eligible the checksum sudo must say it reads the checksum of the attachment already linked to this document. It must not say a command check ran; compliance_service.py and the scale-ticket scan call that method with no verifier check. On document.py:426, document.py:448, transaction_docs.py:71, and transaction_docs.py:98 the reason must say the write sets compliance flags for a document the caller can already write, and that the group_user full-access row still admits every internal user. Do not edit the ACL CSV. | Cursor Build agent | `medium` | S | `[T1]` | `plasticos_documents/models/document.py`, `plasticos_documents/models/transaction_docs.py` |
| T4 | Put the existing true reason on the .sudo() line with the required prefix. Cover mail_mail_inherit.py lines 33, 34, 66, 89, and 191; linda_response.py lines 207, 209, and 216; linda_request.py lines 328, 593, 708, and 833; invoice_reminder.py line 39; account_move_inherit.py line 38; commission_payout.py line 132; crm_tag_adoption.py lines 24 and 33; document.py lines 540, 621, 660, 754, 764, and 793; document_native.py line 540. Keep the ir.model.data read elevations. A verifier or override check may be named only on a line that runs after that check. | Cursor Build agent | `medium` | M | `[T1]` | `plasticos_logistics/models/mail_mail_inherit.py`, `plasticos_logistics/models/linda_response.py`, `plasticos_logistics/models/linda_request.py`, `plasticos_automation/models/invoice_reminder.py`, `plasticos_transaction/models/account_move_inherit.py`, `plasticos_commission/models/commission_payout.py`, `plasticos_crm_bridge/models/crm_tag_adoption.py`, `plasticos_documents/models/document.py`, `plasticos_documents_native/models/document_native.py` |
| T5 | Resolve U1 before editing facility_profile.py:307. Read the core mail.message access rule. If base.group_user can already read the row and write res_id, delete that sudo and its comment. If not, keep the sudo and set the same-line reason to the profile merge moving that profile's own chatter, which the sync caller cannot write. Do not add a group and do not edit line 322. The only production caller is orchestrator.py link_verified_location. | Cursor Build agent | `high` | S | `[T1]` | `plasticos_crm_bridge/models/facility_profile.py` |
| T6 | Regenerate extended_audit_report.json and require zero UNJUSTIFIED_SUDO. Only then change that finding's severity in business_logic_audit.py from MODERATE to HIGH, and assert the bare-call fixture reports HIGH. Do not change the marker regex. Do not add a baseline entry. Do not add a CI job. The existing HIGH diff is the gate. | Cursor Build agent | `medium` | S | `[T2, T3, T4, T5]` | `scripts/audit/business_logic_audit.py`, `tests/test_unjustified_sudo_scanner.py` |
| T7 | Bump the patch version in __manifest__.py once for each module whose Python changed: plasticos_logistics, plasticos_crm_bridge, plasticos_documents, plasticos_documents_native, plasticos_transaction, plasticos_commission, and plasticos_automation. Run ruff format on each manifest. Do not bump a module whose files were not edited. | Cursor Build agent | `low` | S | `[T2, T3, T4, T5]` | `plasticos_logistics/__manifest__.py`, `plasticos_crm_bridge/__manifest__.py`, `plasticos_documents/__manifest__.py`, `plasticos_documents_native/__manifest__.py`, `plasticos_transaction/__manifest__.py`, `plasticos_commission/__manifest__.py`, `plasticos_automation/__manifest__.py` |
| T8 | Run V1, V2, V3, and V4. V2 passes on a zero UNJUSTIFIED_SUDO count even if the process exits 1 for the baselined enrichment N_PLUS_ONE_QUERY. Do not start T6's severity edit until that count is zero. | Cursor Build agent | `medium` | M | `[T6, T7]` | `tests/test_unjustified_sudo_scanner.py`, `scripts/audit/run_all_audits.py` |

**Critical path:** T1 → T5 → T6 → T7 → T8

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The scanner still rejects a preceding comment and a prefix-less comment | call-site edits cannot loosen the marker |
| M2 | Every remaining elevation has a same-line reason that matches its check, and the no-privilege elevations are gone | a zero UNJUSTIFIED_SUDO count |
| M3 | The finding is HIGH and the report contains zero of them | the existing HIGH baseline diff rejects the next bare call |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 red tests fail before the scanner is loosened and pass with the scanner unchanged | stop and revert any change to the marker regex |
| C2 | M2 | extended_audit_report.json has zero UNJUSTIFIED_SUDO before the severity change | do not raise the severity and do not add baseline entries |
| C3 | M3 | a bare sudo fixture is HIGH and the regenerated report still has zero UNJUSTIFIED_SUDO | revert the severity change |

### Leverage

- **Ranked todos:** `T1`, `T5`, `T2`, `T3`, `T4`, `T6`, `T7`, `T8`
- **Shared causes:** comment shape treated as authorization
- **Deletions / consolidations:** Remove .sudo() at linda_request.py:796; Remove .sudo() at facility_profile.py:290; Remove .sudo() on the crm_tag_adoption installer creates

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The extended baseline stays the one reviewed N_PLUS_ONE_QUERY entry. This plan adds no baseline row and no new workflow. |
| ci/baselines/README.md | `n_a` | — | The extended audit remains gated at HIGH. Raising this finding to HIGH uses that gate. |
| .cursor/rules/71-plasticos-security-model.mdc | `n_a` | — | The same-line sudo justification law is already the rule. This plan enforces it. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/test_unjustified_sudo_scanner.py` | PASS, including the preceding-comment rejection and severity HIGH on a bare call | `not_run` |
| E-V2 | SP-01, SP-02 | `quality_gate_evidence` | command | `python3 scripts/audit/run_all_audits.py .` | extended_audit_report.json contains zero UNJUSTIFIED_SUDO | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | pre-commit passes on the changed Python files | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `make test-module m=plasticos_logistics` | the same target passes for plasticos_logistics, plasticos_crm_bridge, plasticos_documents, plasticos_documents_native, plasticos_transaction, plasticos_commission, and plasticos_automation | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Would accepting a preceding comment let the false command-check sentence in _currently_eligible pass?
- Does deleting the ir.model.data read sudo depend on keeping access_ir_model_data_import, which the security evidence says to remove?
- Does raising the severity before the count is zero force the 34 rows into the baseline?
- Does facility_profile.py:307 describe a group check that link_verified_location does not perform?

### Assumption failure conditions

- A same-line comment proves the caller was authorized
- The current documents ACL limits the compliance-flag sudo to a documents manager

### Blast radius notes

- Removing a necessary sudo raises AccessError on order confirm, mail send, document verification, or CRM sync. Raising severity too early turns the 34 rows into a red HIGH gate.

### Rollback constraints

- Revert the feature branch. No schema migration. Do not edit ci/baselines/extended_audit_baseline.json.

### Risks

| risk | mitigation |
|------|------------|
| A later non-superuser caller of _cancel_queued loses the removed sudo | _check_evidence_writer still raises AccessError unless env.su. The current callers are already superuser. |
| Prefix-only edits leave the compliance-flag actor as every internal user | The reason states that ACL fact. Deleting the group_user full-access rows is out of scope. |
| run_all_audits.py still exits 1 because of the baselined enrichment N_PLUS_ONE_QUERY | V2 judges the JSON type count, not the process exit code. |
| The only open pull request is #197, mack into Development, and it does not own these files | make pr targets Staging. Do not set the base to Development or Production. |

## Out of scope

- Accepting a preceding-line comment or any comment without the sudo or cron-sudo-justification prefix
- Removing the ir.model.data read elevations in account_move_inherit.py, commission_payout.py, and role_tag_binding
- Deleting access_ir_model_data_import or the plasticos_documents group_user full-access rows
- Adding a new security group or a has_group check that the sync does not already have
- Baselining the 34 rows or adding a second CI job
- The baselined N_PLUS_ONE_QUERY on plasticos_enrichment/models/enrichment_run.py
- UNBOUNDED_SEARCH findings
- facility_profile.py:322
- pipeline_v2.py
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.make_sudo_findings_match_real_authorization.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.make_sudo_findings_match_real_authorization.v1` |
| source_ref | `plan.simple.make_sudo_findings_match_real_authorization.v1` |
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
| `unknown` | U1 | Can base.group_user already read mail.message and write res_id, which would make the sudo at facility_profile.py:307 unnecessary? — If yes, delete that sudo and its comment. If no, keep it and write the same-line reason for the profile merge. Do not add a group. Do not edit line 322. | `probe` |
| `open_blocker` | stop_reason | Architecture is settled. U1 is a bounded probe inside T5, not a question for the user. Implementation has not run. | planning convergence `partial` |

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
  plan_id: "plan.simple.make_sudo_findings_match_real_authorization.v1"
  name: "Make sudo findings match real authorization"
  overview: "Make a green UNJUSTIFIED_SUDO result mean every remaining .sudo() has a same-line reason that matches the check above it, delete elevations that add no privilege, and let the existing HIGH audit gate reject the next bare call."
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
  commit_sha: "e822dbda7fa1833a9b5fca3b7f66e41e055a701a"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Make a green UNJUSTIFIED_SUDO result mean every remaining .sudo() has a same-line reason that matches the check above it, delete elevations that add no privilege, and let the existing HIGH audit gate reject the next bare call."
  success_properties:
    - id: "SP-01"
      property: "V1 tests/test_unjustified_sudo_scanner.py still flags a preceding-line comment and a prefix-less same-line comment as UNJUSTIFIED_SUDO, and a bare .sudo() finding has severity HIGH"
      evidence_type: "quality_gate"
      proof: ["V1", "V2"]
      blocking: true
    - id: "SP-02"
      property: "V2 scripts/audit/run_all_audits.py writes extended_audit_report.json with zero UNJUSTIFIED_SUDO. Exit 1 is still allowed while the baselined N_PLUS_ONE_QUERY on enrichment_run.py remains"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 .pre-commit-config.yaml passes on the changed Python"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 make test-module passes once for each bumped module"
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.make_sudo_findings_match_real_authorization.v1"
execution_envelope:
  filesystem:
    write_allow: ["tests/test_unjustified_sudo_scanner.py", "scripts/audit/business_logic_audit.py", "plasticos_logistics/models/linda_request.py", "plasticos_logistics/models/linda_response.py", "plasticos_logistics/models/mail_mail_inherit.py", "plasticos_logistics/__manifest__.py", "plasticos_crm_bridge/models/facility_profile.py", "plasticos_crm_bridge/models/crm_tag_adoption.py", "plasticos_crm_bridge/__manifest__.py", "plasticos_documents/models/document.py", "plasticos_documents/models/transaction_docs.py", "plasticos_documents/__manifest__.py", "plasticos_documents_native/models/document_native.py", "plasticos_documents_native/__manifest__.py", "plasticos_transaction/models/account_move_inherit.py", "plasticos_transaction/__manifest__.py", "plasticos_commission/models/commission_payout.py", "plasticos_commission/__manifest__.py", "plasticos_automation/models/invoice_reminder.py", "plasticos_automation/__manifest__.py"]
    write_deny: ["plasticos_documents/security/ir.model.access.csv", "plasticos_base/security/ir.model.access.csv", "ci/baselines/extended_audit_baseline.json", "plasticos_enrichment/models/enrichment_run.py", "scripts/audit/performance_audit.py", "plasticos_inference_engine/pipeline_v2.py", "plasticos_crm_bridge/models/facility_profile.py line 322"]
  commands:
    allow: ["python3 -m pytest tests/test_unjustified_sudo_scanner.py", "python3 scripts/audit/run_all_audits.py .", ".pre-commit-config.yaml", "make test-module m=plasticos_logistics"]
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
    side_effects: "destructive_filesystem_mutation"
    idempotency: "unsafe_blind_repeat"
    retry: "manual_only"
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
rollback_contract_ref: "rollback.plan.simple.make_sudo_findings_match_real_authorization.v1"
dependency_topology_ref: "dag.plan.simple.make_sudo_findings_match_real_authorization.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Would accepting a preceding comment let the false command-check sentence in _currently_eligible pass?", "Does deleting the ir.model.data read sudo depend on keeping access_ir_model_data_import, which the security evidence says to remove?", "Does raising the severity before the count is zero force the 34 rows into the baseline?", "Does facility_profile.py:307 describe a group check that link_verified_location does not perform?"]
  assumption_failure_conditions: ["A same-line comment proves the caller was authorized", "The current documents ACL limits the compliance-flag sudo to a documents manager"]
out_of_scope: ["Accepting a preceding-line comment or any comment without the sudo or cron-sudo-justification prefix", "Removing the ir.model.data read elevations in account_move_inherit.py, commission_payout.py, and role_tag_binding", "Deleting access_ir_model_data_import or the plasticos_documents group_user full-access rows", "Adding a new security group or a has_group check that the sync does not already have", "Baselining the 34 rows or adding a second CI job", "The baselined N_PLUS_ONE_QUERY on plasticos_enrichment/models/enrichment_run.py", "UNBOUNDED_SEARCH findings", "facility_profile.py:322", "pipeline_v2.py"]
convergence_contract_ref: "conv.plan.simple.make_sudo_findings_match_real_authorization.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Lock the scanner contract in tests/test_unjustified_sudo_scanner.py. A preceding-line comment stays a finding. A same-line comment that does not start with # sudo: or # cron-sudo-justification: stays a finding. An empty marker and a debt-marker reason stay findings. Do not change _is_sudo_justification or _sudo_call_lines."
    status: "pending"
  - id: "T2"
    content: "Delete elevations that add no privilege. At linda_request.py:796 remove .sudo() and the comment above it that names a caller who is already superuser; _check_evidence_writer still refuses a non-superuser. At facility_profile.py:290 remove .sudo() and its comment; internal users can already read mail.scheduled.message. At crm_tag_adoption.py lines 47, 51, and 52 remove .sudo() on the installer creates; the XML function and the pre-migrate already run as superuser. Do not remove the reads at lines 24 and 33."
    status: "pending"
  - id: "T3"
    content: "Replace reasons that do not match the code. In _currently_eligible the checksum sudo must say it reads the checksum of the attachment already linked to this document. It must not say a command check ran; compliance_service.py and the scale-ticket scan call that method with no verifier check. On document.py:426, document.py:448, transaction_docs.py:71, and transaction_docs.py:98 the reason must say the write sets compliance flags for a document the caller can already write, and that the group_user full-access row still admits every internal user. Do not edit the ACL CSV."
    status: "pending"
  - id: "T4"
    content: "Put the existing true reason on the .sudo() line with the required prefix. Cover mail_mail_inherit.py lines 33, 34, 66, 89, and 191; linda_response.py lines 207, 209, and 216; linda_request.py lines 328, 593, 708, and 833; invoice_reminder.py line 39; account_move_inherit.py line 38; commission_payout.py line 132; crm_tag_adoption.py lines 24 and 33; document.py lines 540, 621, 660, 754, 764, and 793; document_native.py line 540. Keep the ir.model.data read elevations. A verifier or override check may be named only on a line that runs after that check."
    status: "pending"
  - id: "T5"
    content: "Resolve U1 before editing facility_profile.py:307. Read the core mail.message access rule. If base.group_user can already read the row and write res_id, delete that sudo and its comment. If not, keep the sudo and set the same-line reason to the profile merge moving that profile's own chatter, which the sync caller cannot write. Do not add a group and do not edit line 322. The only production caller is orchestrator.py link_verified_location."
    status: "pending"
  - id: "T6"
    content: "Regenerate extended_audit_report.json and require zero UNJUSTIFIED_SUDO. Only then change that finding's severity in business_logic_audit.py from MODERATE to HIGH, and assert the bare-call fixture reports HIGH. Do not change the marker regex. Do not add a baseline entry. Do not add a CI job. The existing HIGH diff is the gate."
    status: "pending"
  - id: "T7"
    content: "Bump the patch version in __manifest__.py once for each module whose Python changed: plasticos_logistics, plasticos_crm_bridge, plasticos_documents, plasticos_documents_native, plasticos_transaction, plasticos_commission, and plasticos_automation. Run ruff format on each manifest. Do not bump a module whose files were not edited."
    status: "pending"
  - id: "T8"
    content: "Run V1, V2, V3, and V4. V2 passes on a zero UNJUSTIFIED_SUDO count even if the process exits 1 for the baselined enrichment N_PLUS_ONE_QUERY. Do not start T6's severity edit until that count is zero."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-06T16:39:15Z`
- conversation_id: `d508d136-a886-4e21-b606-b4f30dd37bc6`
- generation_id: `890cbb89-b5a5-4194-b3c5-b94e79fc1cc6`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/d508d136-a886-4e21-b606-b4f30dd37bc6/d508d136-a886-4e21-b606-b4f30dd37bc6.jsonl`
- todos at build time:
- `T1`: completed
- `T2`: completed
- `T3`: completed
- `T4`: completed
- `T5`: completed
- `T6`: completed
- `T7`: completed
- `T8`: completed
