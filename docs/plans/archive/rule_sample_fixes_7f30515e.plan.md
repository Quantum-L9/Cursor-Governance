---
name: Correct three Odoo rule samples
overview: "Replace the false security-group sample, the reversed ampersand sample, and the advisory-lock sample so each matches its source of truth. Publish that change with make pr-nosmoke from a clean worktree stacked on pull request 378, whose head is test/retire-stale-proofs. The worktree contains only those three rule files on top of that head. Do not rewrite the surfaces owned by the agent-rule real..."
todos:
  - id: T1
    content: "Replace the fictional plasticos_privilege tree, the manager/user/readonly minimum, the slash-separator sentence, and the CSV sample with the eight xmlids in plasticos_security_base/security/security_groups.xml. The CSV example uses base.group_user and base.group_system, matching plasticos_material_profile/security/ir.model.access.csv. A role-scoped row uses plasticos_security_base plus one of those xmlids. Keep the CSV preflight."
    status: pending
    phase: execute
    depends_on: [T4]
  - id: T2
    content: "Replace the reversed ampersand pair. The wrong sample is a string attribute with a raw spaced ampersand. The correct sample is the same attribute with the amp entity. scripts/check_odoo_patterns.sh flags that raw form. Leave the rest of the file unchanged."
    status: pending
    phase: execute
    depends_on: [T4]
  - id: T3
    content: "Replace only the advisory-lock code fence. cr.execute returns None. The fence must follow plasticos_offer/models/offer.py cron_expire_offers: pg_try_advisory_lock via hashtext, fetchone, return when unlocked, and pg_advisory_unlock on the same key inside finally. tools/cron_invariant_check.py CRON205 and CRON206 require that pair. Do not rewrite noupdate or cron active rules."
    status: pending
    phase: execute
    depends_on: [T4]
  - id: T4
    content: "Fetch origin/test/retire-stale-proofs and create a sibling worktree with bash .cursor-commands/ops/scripts/worktree_add_wired.sh -b docs/odoo-rule-samples. Do not use the dirty checkout fix/material-profile-count-batch. Do not copy any other dirty or untracked file into the worktree. git status --porcelain in the worktree is empty before the three edits."
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "From the clean worktree, after T1 T2 and T3, commit only the three rule files. git status --porcelain must be empty. Then run make pr-nosmoke reason='agent rule samples only; no addon or installer input changed' base=test/retire-stale-proofs. Do not run bare make pr. Do not force-add rule 37. Do not edit any file that pull request 378 already changes."
    status: pending
    phase: execute
    depends_on: [T1, T2, T3]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Correct three Odoo rule samples

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `correct_three_odoo_rule_samples_73e69f2b.plan.md`
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
| plan_id | `plan.simple.correct_three_odoo_rule_samples.v1` |
| name | Correct three Odoo rule samples |
| overview | Replace the false security-group sample, the reversed ampersand sample, and the advisory-lock sample so each matches its source of truth. Publish that change with make pr-nosmoke from a clean worktree stacked on pull request 378, whose head is test/retire-stale-proofs. The worktree contains only those three rule files on top of that head. Do not rewrite the surfaces owned by the agent-rule realignment plan. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T16:55:01+00:00 |
| updated_at | 2026-11-05T16:55:01+00:00 |
| depth | `standard` |
| estimate | one stacked no-smoke pull request |

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
| captured_at | `2026-11-05T16:55:01+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `docs/brs-documents-logistics-ownership` |
| commit_sha | `7edbcce1967af5cca89a2d2f4f00b891a109ce34` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Replace the false security-group sample, the reversed ampersand sample, and the advisory-lock sample so each matches its source of truth. Publish that change with make pr-nosmoke from a clean worktree stacked on pull request 378, whose head is test/retire-stale-proofs. The worktree contains only those three rule files on top of that head. Do not rewrite the surfaces owned by the agent-rule realignment plan.

### Scope in

- .cursor/rules/71-plasticos-security-model.mdc group hierarchy, three-tier minimum, slash-separator sentence, and CSV sample
- .cursor/rules/84-ci-odoo19-patterns.mdc unescaped-ampersand example only
- .cursor/rules/75-plasticos-xml-data-rules.mdc advisory-lock code fence only
- a clean worktree branched from origin/test/retire-stale-proofs, the head of pull request 378, containing one commit of the three rule files
- publication with make pr-nosmoke reason="agent rule samples only; no addon or installer input changed" base=test/retire-stale-proofs

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1: .cursor/rules/71-plasticos-security-model.mdc names group_sales_rep, group_logistics, group_logistics_ops, group_accounting, group_accounting_ops, group_qc_manager, group_operations_manager, and group_system_admin, and it does not name plasticos_privilege_manager, plasticos_privilege_user, plasticos_privilege_readonly, or readonly=R. | `quality_gate` | V1: `python3 -c "from pathlib import Path; t=Path('.cursor/rules/71-plasticos-security-model.mdc').read_text(); need=['group_sales_rep','group_logistics','group_logistics_ops','group_accounting','group_accounting_ops','group_qc_manager','group_operations_manager','group_system_admin']; bad=['plasticos_privilege_manager','plasticos_privilege_user','plasticos_privilege_readonly','readonly=R']; assert all(n in t for n in need) and not any(b in t for b in bad)"` → eight live xmlids present and the fictional tiers absent | `true` |
| SP-02 | V2: .cursor/rules/84-ci-odoo19-patterns.mdc shows a wrong string attribute containing a raw spaced ampersand and a correct string attribute containing the amp entity. | `quality_gate` | V2: `python3 -c "from pathlib import Path; t=Path('.cursor/rules/84-ci-odoo19-patterns.mdc').read_text(); assert 'A & B' in t and 'A &amp; B' in t"` → wrong sample has a raw spaced ampersand and correct sample has the amp entity | `true` |
| SP-03 | V3: .cursor/rules/75-plasticos-xml-data-rules.mdc lock fence calls fetchone and pg_advisory_unlock inside finally on the same hashtext key, and it does not contain if not self.env.cr.execute. | `quality_gate` | V3: `python3 -c "from pathlib import Path; t=Path('.cursor/rules/75-plasticos-xml-data-rules.mdc').read_text(); assert 'fetchone' in t and 'pg_advisory_unlock' in t and 'finally' in t and 'if not self.env.cr.execute' not in t"` → lock fence acquires, reads the boolean, and unlocks in finally | `true` |
| SP-04 | V4: the stacked pull request base is test/retire-stale-proofs, its diff against that head names only the three rule files, and publication was make pr-nosmoke from a clean worktree. | `quality_gate` | V4: `git status --porcelain && git diff --name-only origin/test/retire-stale-proofs...HEAD && gh pr view --json baseRefName,files` → porcelain is empty, the diff names only the three rule files, and baseRefName is test/retire-stale-proofs | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.correct_three_odoo_rule_samples.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.correct_three_odoo_rule_samples.v1` |
| source_ref | `plan.simple.correct_three_odoo_rule_samples.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.correct_three_odoo_rule_samples.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `MEMORY_PREFETCH .l9/memory/plan-prefetch.json namespace ib-odoo-19 snapshot_digest f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2 conflicts 0` | prefetch state HIT and conflicts_state CLEAN | `true` |
| P1 | pre-validation (status `passed`) | `GAR 0.8.4 STANDALONE. Architecture already settled: the three samples stay in their current rule files. Intervention class is Replace. L9 architecture profile is NotApplicable because the target is PlasticOS rule markdown, not an L9 runtime.` | no new owner and no new rule file | `true` |
| P2 | pre-validation (status `passed`) | `python3 skills/l9-plan/scripts/route_plan.py --risk medium --evidence sufficient --json` | depth standard and omit_gates empty | `true` |
| P3 | pre-validation (status `passed`) | `gh pr view 378 --json baseRefName,headRefName,files; hook catalog is .pre-commit-config.yaml` | pull request 378 is open, base Staging, head test/retire-stale-proofs, and its files do not include the three rule paths | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `.cursor/rules/71-plasticos-security-model.mdc`, `.cursor/rules/75-plasticos-xml-data-rules.mdc`, `.cursor/rules/84-ci-odoo19-patterns.mdc`
- **write_deny:** `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `V1`, `V2`, `V3`, `V4`, `V5`, `python3 -c "from pathlib import Path; t=Path('.cursor/rules/71-plasticos-security-model.mdc').read_text(); need=['group_sales_rep','group_logistics','group_logistics_ops','group_accounting','group_accounting_ops','group_qc_manager','group_operations_manager','group_system_admin']; bad=['plasticos_privilege_manager','plasticos_privilege_user','plasticos_privilege_readonly','readonly=R']; assert all(n in t for n in need) and not any(b in t for b in bad)"`, `python3 -c "from pathlib import Path; t=Path('.cursor/rules/84-ci-odoo19-patterns.mdc').read_text(); assert 'A & B' in t and 'A &amp; B' in t"`, `python3 -c "from pathlib import Path; t=Path('.cursor/rules/75-plasticos-xml-data-rules.mdc').read_text(); assert 'fetchone' in t and 'pg_advisory_unlock' in t and 'finally' in t and 'if not self.env.cr.execute' not in t"`, `git status --porcelain && git diff --name-only origin/test/retire-stale-proofs...HEAD && gh pr view --json baseRefName,files`, `.pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `github.com` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- clean worktree from origin/test/retire-stale-proofs
- make pr-nosmoke base=test/retire-stale-proofs
- do not publish from fix/material-profile-count-batch
- do not edit pull request 378 files
- do not admit a Program Lock

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .cursor/rules/71-plasticos-security-model.mdc` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .cursor/rules/84-ci-odoo19-patterns.mdc` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .cursor/rules/75-plasticos-xml-data-rules.mdc` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .cursor-commands/ops/scripts/worktree_add_wired.sh` | `false` |
| T5 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- .cursor/rules/71-plasticos-security-model.mdc .cursor/rules/75-plasticos-xml-data-rules.mdc .cursor/rules/84-ci-odoo19-patterns.mdc` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `.cursor/rules` | `policy` | `clean worktree from origin/test/retire-stale-proofs`, `make pr-nosmoke base=test/retire-stale-proofs`, `do not publish from fix/material-profile-count-batch`, `do not edit pull request 378 files`, `do not admit a Program Lock` | `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md` |
| T2 | `.cursor/rules` | `policy` | `clean worktree from origin/test/retire-stale-proofs`, `make pr-nosmoke base=test/retire-stale-proofs`, `do not publish from fix/material-profile-count-batch`, `do not edit pull request 378 files`, `do not admit a Program Lock` | `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md` |
| T3 | `.cursor/rules` | `policy` | `clean worktree from origin/test/retire-stale-proofs`, `make pr-nosmoke base=test/retire-stale-proofs`, `do not publish from fix/material-profile-count-batch`, `do not edit pull request 378 files`, `do not admit a Program Lock` | `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md` |
| T4 | `.cursor-commands/ops/scripts` | `ops` | `clean worktree from origin/test/retire-stale-proofs`, `make pr-nosmoke base=test/retire-stale-proofs`, `do not publish from fix/material-profile-count-batch`, `do not edit pull request 378 files`, `do not admit a Program Lock` | `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md` |
| T5 | `.cursor/rules` | `ops` | `clean worktree from origin/test/retire-stale-proofs`, `make pr-nosmoke base=test/retire-stale-proofs`, `do not publish from fix/material-profile-count-batch`, `do not edit pull request 378 files`, `do not admit a Program Lock` | `.cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md`, `.cursor/rules/00-plasticos-master-context.mdc`, `AGENTS.md`, `CLAUDE.md`, `INVARIANTS.md` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.correct_three_odoo_rule_samples.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.correct_three_odoo_rule_samples.v1` |
| source_execution_ref | `plan.simple.correct_three_odoo_rule_samples.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 V2 and V3 textual checks pass) → do not commit a sample that still names a missing group, reverses the ampersand, or locks without a finally unlock; C2 fails (V4 shows a clean tree, base test/retire-stale-proofs, and only the three rule files) → stop before bare make pr, and stop if the worktree is dirty or the parent files overlap |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Close the stacked pull request without merging it. The parent branch test/retire-stale-proofs stays as pull request 378 left it. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `V1`
- re-run `V2`
- re-run `V3`
- re-run `V4`
- re-run `V5`
- re-run `python3 -c "from pathlib import Path; t=Path('.cursor/rules/71-plasticos-security-model.mdc').read_text(); need=['group_sales_rep','group_logistics','group_logistics_ops','group_accounting','group_accounting_ops','group_qc_manager','group_operations_manager','group_system_admin']; bad=['plasticos_privilege_manager','plasticos_privilege_user','plasticos_privilege_readonly','readonly=R']; assert all(n in t for n in need) and not any(b in t for b in bad)"`
- re-run `python3 -c "from pathlib import Path; t=Path('.cursor/rules/84-ci-odoo19-patterns.mdc').read_text(); assert 'A & B' in t and 'A &amp; B' in t"`
- re-run `python3 -c "from pathlib import Path; t=Path('.cursor/rules/75-plasticos-xml-data-rules.mdc').read_text(); assert 'fetchone' in t and 'pg_advisory_unlock' in t and 'finally' in t and 'if not self.env.cr.execute' not in t"`
- re-run `git status --porcelain && git diff --name-only origin/test/retire-stale-proofs...HEAD && gh pr view --json baseRefName,files`
- re-run `.pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 5 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — Agents that trust rule 71 will write ACL rows for xmlids that do not exist. Agents that trust the lock sample will return from every cron. Publishing from the dirty checkout would mix this commit into another pull request. Editing a file pull request 378 already changes would conflict with that parent. |
| architectural_boundaries_crossed | none |
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
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.correct_three_odoo_rule_samples.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.correct_three_odoo_rule_samples.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Replace the fictional plasticos_privilege tree, the manager/user/readonly minimum, the slash-separator sentence, and the CSV sample with the eight xmlids in plasticos_security_base/security/security_groups.xml. The CSV example uses base.group_user and base.group_system, matching plasticos_material_profile/security/ir.model.access.csv. A role-scoped row uses plasticos_security_base plus one of those xmlids. Keep the CSV preflight. | Cursor Build agent | `medium` | S | `[T4]` | `.cursor/rules/71-plasticos-security-model.mdc` |
| T2 | Replace the reversed ampersand pair. The wrong sample is a string attribute with a raw spaced ampersand. The correct sample is the same attribute with the amp entity. scripts/check_odoo_patterns.sh flags that raw form. Leave the rest of the file unchanged. | Cursor Build agent | `low` | S | `[T4]` | `.cursor/rules/84-ci-odoo19-patterns.mdc` |
| T3 | Replace only the advisory-lock code fence. cr.execute returns None. The fence must follow plasticos_offer/models/offer.py cron_expire_offers: pg_try_advisory_lock via hashtext, fetchone, return when unlocked, and pg_advisory_unlock on the same key inside finally. tools/cron_invariant_check.py CRON205 and CRON206 require that pair. Do not rewrite noupdate or cron active rules. | Cursor Build agent | `medium` | S | `[T4]` | `.cursor/rules/75-plasticos-xml-data-rules.mdc` |
| T4 | Fetch origin/test/retire-stale-proofs and create a sibling worktree with bash .cursor-commands/ops/scripts/worktree_add_wired.sh -b docs/odoo-rule-samples. Do not use the dirty checkout fix/material-profile-count-batch. Do not copy any other dirty or untracked file into the worktree. git status --porcelain in the worktree is empty before the three edits. | Cursor Build agent | `medium` | S | `[]` | `.cursor-commands/ops/scripts/worktree_add_wired.sh` |
| T5 | From the clean worktree, after T1 T2 and T3, commit only the three rule files. git status --porcelain must be empty. Then run make pr-nosmoke reason="agent rule samples only; no addon or installer input changed" base=test/retire-stale-proofs. Do not run bare make pr. Do not force-add rule 37. Do not edit any file that pull request 378 already changes. | Cursor Build agent | `medium` | S | `[T1, T2, T3]` | `.cursor/rules/71-plasticos-security-model.mdc`, `.cursor/rules/75-plasticos-xml-data-rules.mdc`, `.cursor/rules/84-ci-odoo19-patterns.mdc` |

**Critical path:** T4 → T1 → T3 → T5

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | The three samples match security_groups.xml, check_odoo_patterns.sh, and cron_expire_offers | T5 |
| M2 | A no-smoke pull request is stacked on test/retire-stale-proofs and its diff is only the three rule files | review of the stacked pull request |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 V2 and V3 textual checks pass | do not commit a sample that still names a missing group, reverses the ampersand, or locks without a finally unlock |
| C2 | M2 | V4 shows a clean tree, base test/retire-stale-proofs, and only the three rule files | stop before bare make pr, and stop if the worktree is dirty or the parent files overlap |

### Leverage

- **Ranked todos:** `T1`, `T3`, `T2`, `T4`, `T5`
- **Shared causes:** false sample
- **Deletions / consolidations:** Delete the fictional privilege tree instead of mapping it onto the real groups; Do not add a second security or cron rule

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | The realignment plan owns the contradicted lines in this append-only file. |
| CLAUDE.md | `n_a` | — | The realignment plan owns the design-principle edits. |
| INVARIANTS.md | `n_a` | — | No invariant body changes in this sample correction. |
| ARCHITECTURE.md | `n_a` | — | Out of scope. The realignment plan leaves this root file for a later pass. |
| .cursor/rules/00-plasticos-master-context.mdc | `n_a` | — | Its manager/user/readonly router line stays until the realignment plan rewrites rule 00. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -c "from pathlib import Path; t=Path('.cursor/rules/71-plasticos-security-model.mdc').read_text(); need=['group_sales_rep','group_logistics','group_logistics_ops','group_accounting','group_accounting_ops','group_qc_manager','group_operations_manager','group_system_admin']; bad=['plasticos_privilege_manager','plasticos_privilege_user','plasticos_privilege_readonly','readonly=R']; assert all(n in t for n in need) and not any(b in t for b in bad)"` | eight live xmlids present and the fictional tiers absent | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `python3 -c "from pathlib import Path; t=Path('.cursor/rules/84-ci-odoo19-patterns.mdc').read_text(); assert 'A & B' in t and 'A &amp; B' in t"` | wrong sample has a raw spaced ampersand and correct sample has the amp entity | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `python3 -c "from pathlib import Path; t=Path('.cursor/rules/75-plasticos-xml-data-rules.mdc').read_text(); assert 'fetchone' in t and 'pg_advisory_unlock' in t and 'finally' in t and 'if not self.env.cr.execute' not in t"` | lock fence acquires, reads the boolean, and unlocks in finally | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `git status --porcelain && git diff --name-only origin/test/retire-stale-proofs...HEAD && gh pr view --json baseRefName,files` | porcelain is empty, the diff names only the three rule files, and baseRefName is test/retire-stale-proofs | `not_run` |
| E-V5 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | hooks that match the three mdc paths pass, or no hook selects those paths | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does renaming the three tiers onto real groups still teach a readonly tier that security_groups.xml does not define?
- Does fetchone alone still fail CRON206 because the unlock is missing?
- Does the ampersand correction still show an escaped ampersand in the sample marked wrong?
- Does publishing from the dirty checkout, or branching anywhere except origin/test/retire-stale-proofs, put these rule edits on pull request 378's own diff or on another open pull request?

### Assumption failure conditions

- The realignment plan already corrected these three samples
- Rule 37 is already a commit on this branch
- cr.execute returns the lock boolean

### Blast radius notes

- Agents that trust rule 71 will write ACL rows for xmlids that do not exist. Agents that trust the lock sample will return from every cron. Publishing from the dirty checkout would mix this commit into another pull request. Editing a file pull request 378 already changes would conflict with that parent.

### Rollback constraints

- Close the stacked pull request without merging it. The parent branch test/retire-stale-proofs stays as pull request 378 left it.

### Risks

| risk | mitigation |
|------|------------|
| The cursor-build boilerplate names bare make pr, which runs install-smoke and does not set the stacked base. | T5 is the publication command: make pr-nosmoke with base=test/retire-stale-proofs from the clean worktree. Do not publish from fix/material-profile-count-batch. |
| The realignment plan tells a later edit to delete the advisory-lock snippet. | This plan owns the code fence only. That later edit must not restore if not self.env.cr.execute. |
| Rule 00 still tells agents to add manager, user, and readonly rows. | Leave rule 00 to the realignment plan. Rule 71 states that those tiers are not groups. |

## Out of scope

- agent_rule_realignment_07c524c1.plan.md and every rewrite it already owns
- rule 00, rule 10, rule 30, rule 35, rule 40, rule 80, rule 81, rule 82, rule 86, rule 95, rule 98
- AGENTS.md, CLAUDE.md, INVARIANTS.md, ARCHITECTURE.md, .claude/rules
- noupdate doctrine and cron active defaults in rule 75
- the category_id pointer at the missing 83-ci-odoo19-patterns file
- force-adding gitignored rule 37
- the dirty checkout fix/material-profile-count-batch. Bare make pr is refused because it runs install-smoke. Campaign admission and a Program Lock stay refused.
- any file in pull request 378: tests, plasticos_admin_dashboard, plasticos_base/tests, and .coderabbit.yaml
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.correct_three_odoo_rule_samples.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.correct_three_odoo_rule_samples.v1` |
| source_ref | `plan.simple.correct_three_odoo_rule_samples.v1` |
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

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Will origin/test/retire-stale-proofs move again before the worktree is cut, or start touching one of the three rule files? — Branch from the fetched parent tip at execution time. Stop if that tip's diff against Staging includes any of the three rule files. | `accept_bounded` |
| `open_blocker` | stop_reason | Planning gates passed. V1 through V5 stay pending until Build edits the three rule files in the clean worktree and publishes with make pr-nosmoke stacked on pull request 378. | planning convergence `partial` |

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
  plan_id: "plan.simple.correct_three_odoo_rule_samples.v1"
  name: "Correct three Odoo rule samples"
  overview: "Replace the false security-group sample, the reversed ampersand sample, and the advisory-lock sample so each matches its source of truth. Publish that change with make pr-nosmoke from a clean worktree stacked on pull request 378, whose head is test/retire-stale-proofs. The worktree contains only those three rule files on top of that head. Do not rewrite the surfaces owned by the agent-rule realignment plan."
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
  commit_sha: "7edbcce1967af5cca89a2d2f4f00b891a109ce34"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Replace the false security-group sample, the reversed ampersand sample, and the advisory-lock sample so each matches its source of truth. Publish that change with make pr-nosmoke from a clean worktree stacked on pull request 378, whose head is test/retire-stale-proofs. The worktree contains only those three rule files on top of that head. Do not rewrite the surfaces owned by the agent-rule realignment plan."
  success_properties:
    - id: "SP-01"
      property: "V1: .cursor/rules/71-plasticos-security-model.mdc names group_sales_rep, group_logistics, group_logistics_ops, group_accounting, group_accounting_ops, group_qc_manager, group_operations_manager, and group_system_admin, and it does not name plasticos_privilege_manager, plasticos_privilege_user, plasticos_privilege_readonly, or readonly=R."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2: .cursor/rules/84-ci-odoo19-patterns.mdc shows a wrong string attribute containing a raw spaced ampersand and a correct string attribute containing the amp entity."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3: .cursor/rules/75-plasticos-xml-data-rules.mdc lock fence calls fetchone and pg_advisory_unlock inside finally on the same hashtext key, and it does not contain if not self.env.cr.execute."
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4: the stacked pull request base is test/retire-stale-proofs, its diff against that head names only the three rule files, and publication was make pr-nosmoke from a clean worktree."
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.correct_three_odoo_rule_samples.v1"
execution_envelope:
  filesystem:
    write_allow: [".cursor/rules/71-plasticos-security-model.mdc", ".cursor/rules/75-plasticos-xml-data-rules.mdc", ".cursor/rules/84-ci-odoo19-patterns.mdc"]
    write_deny: [".cursor-commands/docs/plans/agent_rule_realignment_07c524c1.plan.md", ".cursor/rules/00-plasticos-master-context.mdc", "AGENTS.md", "CLAUDE.md", "INVARIANTS.md"]
  commands:
    allow: ["V1", "V2", "V3", "V4", "V5", "python3 -c \"from pathlib import Path; t=Path('.cursor/rules/71-plasticos-security-model.mdc').read_text(); need=['group_sales_rep','group_logistics','group_logistics_ops','group_accounting','group_accounting_ops','group_qc_manager','group_operations_manager','group_system_admin']; bad=['plasticos_privilege_manager','plasticos_privilege_user','plasticos_privilege_readonly','readonly=R']; assert all(n in t for n in need) and not any(b in t for b in bad)\"", "python3 -c \"from pathlib import Path; t=Path('.cursor/rules/84-ci-odoo19-patterns.mdc').read_text(); assert 'A & B' in t and 'A &amp; B' in t\"", "python3 -c \"from pathlib import Path; t=Path('.cursor/rules/75-plasticos-xml-data-rules.mdc').read_text(); assert 'fetchone' in t and 'pg_advisory_unlock' in t and 'finally' in t and 'if not self.env.cr.execute' not in t\"", "git status --porcelain && git diff --name-only origin/test/retire-stale-proofs...HEAD && gh pr view --json baseRefName,files", ".pre-commit-config.yaml"]
  network:
    mode: "bounded_external_write"
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
rollback_contract_ref: "rollback.plan.simple.correct_three_odoo_rule_samples.v1"
dependency_topology_ref: "dag.plan.simple.correct_three_odoo_rule_samples.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5"]
stress_and_disconfirm:
  disconfirming_cases: ["Does renaming the three tiers onto real groups still teach a readonly tier that security_groups.xml does not define?", "Does fetchone alone still fail CRON206 because the unlock is missing?", "Does the ampersand correction still show an escaped ampersand in the sample marked wrong?", "Does publishing from the dirty checkout, or branching anywhere except origin/test/retire-stale-proofs, put these rule edits on pull request 378's own diff or on another open pull request?"]
  assumption_failure_conditions: ["The realignment plan already corrected these three samples", "Rule 37 is already a commit on this branch", "cr.execute returns the lock boolean"]
out_of_scope: ["agent_rule_realignment_07c524c1.plan.md and every rewrite it already owns", "rule 00, rule 10, rule 30, rule 35, rule 40, rule 80, rule 81, rule 82, rule 86, rule 95, rule 98", "AGENTS.md, CLAUDE.md, INVARIANTS.md, ARCHITECTURE.md, .claude/rules", "noupdate doctrine and cron active defaults in rule 75", "the category_id pointer at the missing 83-ci-odoo19-patterns file", "force-adding gitignored rule 37", "the dirty checkout fix/material-profile-count-batch. Bare make pr is refused because it runs install-smoke. Campaign admission and a Program Lock stay refused.", "any file in pull request 378: tests, plasticos_admin_dashboard, plasticos_base/tests, and .coderabbit.yaml"]
convergence_contract_ref: "conv.plan.simple.correct_three_odoo_rule_samples.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Replace the fictional plasticos_privilege tree, the manager/user/readonly minimum, the slash-separator sentence, and the CSV sample with the eight xmlids in plasticos_security_base/security/security_groups.xml. The CSV example uses base.group_user and base.group_system, matching plasticos_material_profile/security/ir.model.access.csv. A role-scoped row uses plasticos_security_base plus one of those xmlids. Keep the CSV preflight."
    status: "pending"
  - id: "T2"
    content: "Replace the reversed ampersand pair. The wrong sample is a string attribute with a raw spaced ampersand. The correct sample is the same attribute with the amp entity. scripts/check_odoo_patterns.sh flags that raw form. Leave the rest of the file unchanged."
    status: "pending"
  - id: "T3"
    content: "Replace only the advisory-lock code fence. cr.execute returns None. The fence must follow plasticos_offer/models/offer.py cron_expire_offers: pg_try_advisory_lock via hashtext, fetchone, return when unlocked, and pg_advisory_unlock on the same key inside finally. tools/cron_invariant_check.py CRON205 and CRON206 require that pair. Do not rewrite noupdate or cron active rules."
    status: "pending"
  - id: "T4"
    content: "Fetch origin/test/retire-stale-proofs and create a sibling worktree with bash .cursor-commands/ops/scripts/worktree_add_wired.sh -b docs/odoo-rule-samples. Do not use the dirty checkout fix/material-profile-count-batch. Do not copy any other dirty or untracked file into the worktree. git status --porcelain in the worktree is empty before the three edits."
    status: "pending"
  - id: "T5"
    content: "From the clean worktree, after T1 T2 and T3, commit only the three rule files. git status --porcelain must be empty. Then run make pr-nosmoke reason=\"agent rule samples only; no addon or installer input changed\" base=test/retire-stale-proofs. Do not run bare make pr. Do not force-add rule 37. Do not edit any file that pull request 378 already changes."
    status: "pending"
```
