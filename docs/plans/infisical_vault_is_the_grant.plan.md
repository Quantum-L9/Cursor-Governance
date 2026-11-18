---
name: The Infisical vault is the grant
overview: "A name present in Infisical project cursor-governance prod / is authorized for Cursor and Claude to bind when the task needs that system. The committed allow-list matches the vault. Agents see the name catalog at session start and are not asked to wait for a reminder. Values are never printed, exported, or written into mcp.json."
todos:
  - id: T1
    content: "Make the live prod / listing the allow-list. Mirror those names into root_env_keys, union a viewSecretValue=false list into allowed_names so a new vault name is authorized before the next commit, and add CLAUDE_INFISICAL_CLIENT_SECRET to REFUSED_NAMES beside the other machine-identity secrets. Drop L9_MEMORY_HOOK_CLIENT_ID and L9_MEMORY_HOOK_CLIENT_SECRET from the committed mirror because they are not in the vault; the live list authorizes them on the day they appear. Register AUTH0_CLIENT_NAME, GITHUB_CLASSIC_PAT, L9_MEMORY_NEO4J_URI, L9_MEMORY_NEO4J_USER, L9_MEMORY_NEO4J_PASSWORD, L9_STATE_MONGO_URI, MONGODB_ATLAS_CLIENT_ID, MONGODB_ATLAS_CLIENT_SECRET, and VANILLASOFT_API."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Remove the operator-only bind refusal and the hosted IAM forbid. Empty operator_only_keys. operator_only_iam.py --check passes when the forbid privilege is absent, and --apply deletes it. AUTH0_CLIENT_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET bind on Cursor and Claude. Values stay in-process."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Publish the authorized name catalog from that one list at SessionStart. The runtime report names every non-refused vault key and states that a listed name is authorized to bind when the task needs that system. Do not fetch values and do not add ninety individual binds. Append the same rule to skills/l9-secrets/SKILL.md and an AGENTS.md fragment. GITHUB_TOKEN remains the default GitHub credential; GITHUB_CLASSIC_PAT is bindable when the task needs that credential. Do not rewrite the make-pr sentence that says SONAR_TOKEN and SEMGREP_APP_TOKEN are not required."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Spawn MCP servers whose env name is a vault name through a child-env bind. Cover PERPLEXITY_API_KEY, NOTION_API_KEY, N8N_API_KEY, N8N_API_URL, SEMGREP_APP_TOKEN, and GITHUB_TOKEN mapped onto GITHUB_PERSONAL_ACCESS_TOKEN. The wrapper binds into the child environment only. master.mcp.json and the rendered Cursor config keep placeholders and never receive values. Leave FIRECRAWL_API_KEY and TAVILY_MCP_URL unwired."
    status: pending
    phase: execute
    depends_on: [T1]
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: The Infisical vault is the grant

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `the_infisical_vault_is_the_grant_5c5744b5.plan.md`
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
| plan_id | `plan.simple.the_infisical_vault_is_the_grant.v1` |
| name | The Infisical vault is the grant |
| overview | A name present in Infisical project cursor-governance prod / is authorized for Cursor and Claude to bind when the task needs that system. The committed allow-list matches the vault. Agents see the name catalog at session start and are not asked to wait for a reminder. Values are never printed, exported, or written into mcp.json. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-17T22:56:15+00:00 |
| updated_at | 2026-11-17T22:56:15+00:00 |
| depth | `deep` |
| estimate | 1 Build |

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
| captured_at | `2026-11-17T22:56:15+00:00` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| branch | `feat/pr-review-permission` |
| commit_sha | `f925f796dcece4c651b0c2673177bf280ecda151` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

A name present in Infisical project cursor-governance prod / is authorized for Cursor and Claude to bind when the task needs that system. The committed allow-list matches the vault. Agents see the name catalog at session start and are not asked to wait for a reminder. Values are never printed, exported, or written into mcp.json.

### Scope in

- Sync root_env_keys to the live prod / names and accept a live listing as authorization even when the committed list is stale
- Remove the operator-only bind refusal and the hosted IAM forbid on AUTH0_CLIENT_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET
- Publish the authorized name catalog from one viewSecretValue=false list at SessionStart
- Append the grant rule to skills/l9-secrets/SKILL.md and AGENTS.md
- Spawn vault-named MCP servers through a child-env bind so N8N_API_KEY, NOTION_API_KEY, PERPLEXITY_API_KEY, SEMGREP_APP_TOKEN, and GITHUB_TOKEN are usable without a second copy of the value

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 passes: capability_bind allows every name in the vault-list fixture, including AUTH0_CLIENT_SECRET, GITHUB_CLASSIC_PAT, L9_MEMORY_NEO4J_URI, and VANILLASOFT_API, and refuses CLAUDE_INFISICAL_CLIENT_SECRET | `quality_gate` | V1: `.venv/bin/python -m pytest tests/ops/secrets/test_capability_bind.py -q` → PASS, including a vault-list name absent from the yaml and a refusal of CLAUDE_INFISICAL_CLIENT_SECRET | `true` |
| SP-02 | V2 passes: operator_only_iam --check exits 0 with an empty operator_only_keys list and no hosted forbid privilege required | `quality_gate` | V2: `.venv/bin/python ops/secrets/operator_only_iam.py --check` → exit 0 when operator_only_keys is empty and the forbid privilege is not required | `true` |
| SP-03 | V3 passes: the session report lists PERPLEXITY_API_KEY as an authorized name and the report text contains no secret value | `quality_gate` | V3: `.venv/bin/python ops/scripts/session_start_runtime_report.py` → report lists PERPLEXITY_API_KEY as authorized and contains no secret value | `true` |
| SP-04 | V4 passes: the changed-file catalog in .pre-commit-config.yaml exits 0 | `quality_gate` | V4: `bash ops/scripts/run_pr_precommit.sh .pre-commit-config.yaml` → .pre-commit-config.yaml changed-file catalog exits 0 | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.the_infisical_vault_is_the_grant.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.the_infisical_vault_is_the_grant.v1` |
| source_ref | `plan.simple.the_infisical_vault_is_the_grant.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.the_infisical_vault_is_the_grant.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `ops/hooks/plan_memory_prefetch.py --workspace Cursor-Governance --task vault presence authorizes bind` | namespace=cursor-governance snapshot_digest=9a45f66406e67cfb8d46e5ed6fbf708b52632d5dba590f90335bccf6314e1243 checked_record_count=363 conflicts=0 policy_version=memory-phase-lock/v2 | `true` |
| P1 | pre-validation (status `passed`) | `bind workspace /Users/ib-mac/Cursor-Governance branch feat/pr-review-permission HEAD f925f796` | planning binds this checkout; implementation starts on a new branch from origin/main and does not edit this dirty tree | `true` |
| P2 | pre-validation (status `passed`) | `list Infisical prod / with viewSecretValue=false and compare to root_env_keys` | 93 names at / and 2 path-local aliases; this working tree allow-list has 84; nine vault names are outside it | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/secrets/capability_bind.py`, `ops/secrets/infisical-cursor-governance.yaml`, `ops/secrets/operator_only_iam.py`, `ops/secrets/session_start_secrets.py`, `ops/secrets/vault_mcp_bridge.py`, `ops/secrets/vault-mcp-bridges.json`, `ops/scripts/session_start_runtime_report.py`, `ops/memory/mcp_instantiation.py`, `environment/mcp/master.mcp.json`, `skills/l9-secrets/SKILL.md`, `AGENTS.md`, `tests/ops/secrets/test_capability_bind.py`, `ops/secrets/test_session_start_secrets.py`
- **write_deny:** `CANONICAL_LAW.md`, `INVARIANTS.md`, `ops/autonomy/pr_board.py`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `.venv/bin/python -m pytest tests/ops/secrets/test_capability_bind.py -q`, `.venv/bin/python ops/secrets/operator_only_iam.py --check`, `.venv/bin/python ops/scripts/session_start_runtime_report.py`, `bash ops/scripts/run_pr_precommit.sh`, `bash ops/scripts/run_pr_precommit.sh .pre-commit-config.yaml`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `app.infisical.com` |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- Values never go to stdout, stderr, mcp.json, receipts, or chat
- GITHUB_TOKEN remains the default GitHub credential
- make pr does not require SONAR_TOKEN or SEMGREP_APP_TOKEN
- Machine-identity client secrets are used by the plane and are not re-issued
- A name absent from the vault is not a grant

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/secrets/capability_bind.py ops/secrets/infisical-cursor-governance.yaml tests/ops/secrets/test_capability_bind.py` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/secrets/capability_bind.py ops/secrets/operator_only_iam.py ops/secrets/infisical-cursor-governance.yaml ops/secrets/test_session_start_secrets.py` | `false` |
| T3 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/secrets/session_start_secrets.py ops/scripts/session_start_runtime_report.py skills/l9-secrets/SKILL.md AGENTS.md` | `false` |
| T4 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- ops/secrets/vault_mcp_bridge.py ops/secrets/vault-mcp-bridges.json environment/mcp/master.mcp.json ops/memory/mcp_instantiation.py` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `repository root` | `policy` | `Values never go to stdout, stderr, mcp.json, receipts, or chat`, `GITHUB_TOKEN remains the default GitHub credential`, `make pr does not require SONAR_TOKEN or SEMGREP_APP_TOKEN`, `Machine-identity client secrets are used by the plane and are not re-issued`, `A name absent from the vault is not a grant` | `CANONICAL_LAW.md`, `INVARIANTS.md`, `ops/autonomy/pr_board.py` |
| T2 | `ops/secrets` | `policy` | `Values never go to stdout, stderr, mcp.json, receipts, or chat`, `GITHUB_TOKEN remains the default GitHub credential`, `make pr does not require SONAR_TOKEN or SEMGREP_APP_TOKEN`, `Machine-identity client secrets are used by the plane and are not re-issued`, `A name absent from the vault is not a grant` | `CANONICAL_LAW.md`, `INVARIANTS.md`, `ops/autonomy/pr_board.py` |
| T3 | `repository root` | `docs` | `Values never go to stdout, stderr, mcp.json, receipts, or chat`, `GITHUB_TOKEN remains the default GitHub credential`, `make pr does not require SONAR_TOKEN or SEMGREP_APP_TOKEN`, `Machine-identity client secrets are used by the plane and are not re-issued`, `A name absent from the vault is not a grant` | `CANONICAL_LAW.md`, `INVARIANTS.md`, `ops/autonomy/pr_board.py` |
| T4 | `repository root` | `runtime` | `Values never go to stdout, stderr, mcp.json, receipts, or chat`, `GITHUB_TOKEN remains the default GitHub credential`, `make pr does not require SONAR_TOKEN or SEMGREP_APP_TOKEN`, `Machine-identity client secrets are used by the plane and are not re-issued`, `A name absent from the vault is not a grant` | `CANONICAL_LAW.md`, `INVARIANTS.md`, `ops/autonomy/pr_board.py` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.the_infisical_vault_is_the_grant.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.the_infisical_vault_is_the_grant.v1` |
| source_execution_ref | `plan.simple.the_infisical_vault_is_the_grant.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 pytest shows a fixture vault name absent from the yaml is allowed and CLAUDE_INFISICAL_CLIENT_SECRET is refused) → stop before the IAM privilege is removed; C2 fails (V2 operator_only_iam --check exits 0 and a hosted-identity probe of AUTH0_CLIENT_ID is no longer required to fail) → leave the forbid privilege in place and report the identity that could not delete it; C3 fails (V3 session report lists PERPLEXITY_API_KEY and V4 pre-commit catalog passes) → do not render secret values into mcp.json to force a pass |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Revert the branch. Restore operator_only_keys and run operator_only_iam.py --apply to put the forbid privilege back. No vault value is rotated by this change. The machine-identity secrets were never issued. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `.venv/bin/python -m pytest tests/ops/secrets/test_capability_bind.py -q`
- re-run `.venv/bin/python ops/secrets/operator_only_iam.py --check`
- re-run `.venv/bin/python ops/scripts/session_start_runtime_report.py`
- re-run `bash ops/scripts/run_pr_precommit.sh`
- re-run `bash ops/scripts/run_pr_precommit.sh .pre-commit-config.yaml`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` — highest todo risk across 4 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `high` — Cursor and Claude can bind every non-refused prod / secret, including the Auth0 Memory admin client and GITHUB_CLASSIC_PAT. A bug in the MCP child environment can expose one bound value to that child process. The session report can leak a value only if the list call requests values. |
| architectural_boundaries_crossed | `secrets bind gate`, `hosted Infisical IAM`, `SessionStart report`, `MCP spawn` |
| external_systems_touched | `Infisical project cursor-governance` |
| migration_required | `true` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.the_infisical_vault_is_the_grant.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.the_infisical_vault_is_the_grant.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Make the live prod / listing the allow-list. Mirror those names into root_env_keys, union a viewSecretValue=false list into allowed_names so a new vault name is authorized before the next commit, and add CLAUDE_INFISICAL_CLIENT_SECRET to REFUSED_NAMES beside the other machine-identity secrets. Drop L9_MEMORY_HOOK_CLIENT_ID and L9_MEMORY_HOOK_CLIENT_SECRET from the committed mirror because they are not in the vault; the live list authorizes them on the day they appear. Register AUTH0_CLIENT_NAME, GITHUB_CLASSIC_PAT, L9_MEMORY_NEO4J_URI, L9_MEMORY_NEO4J_USER, L9_MEMORY_NEO4J_PASSWORD, L9_STATE_MONGO_URI, MONGODB_ATLAS_CLIENT_ID, MONGODB_ATLAS_CLIENT_SECRET, and VANILLASOFT_API. | Cursor Build agent | `high` | M | `[]` | `ops/secrets/capability_bind.py`, `ops/secrets/infisical-cursor-governance.yaml`, `tests/ops/secrets/test_capability_bind.py` |
| T2 | Remove the operator-only bind refusal and the hosted IAM forbid. Empty operator_only_keys. operator_only_iam.py --check passes when the forbid privilege is absent, and --apply deletes it. AUTH0_CLIENT_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET bind on Cursor and Claude. Values stay in-process. | Cursor Build agent | `high` | M | `[T1]` | `ops/secrets/capability_bind.py`, `ops/secrets/operator_only_iam.py`, `ops/secrets/infisical-cursor-governance.yaml`, `ops/secrets/test_session_start_secrets.py` |
| T3 | Publish the authorized name catalog from that one list at SessionStart. The runtime report names every non-refused vault key and states that a listed name is authorized to bind when the task needs that system. Do not fetch values and do not add ninety individual binds. Append the same rule to skills/l9-secrets/SKILL.md and an AGENTS.md fragment. GITHUB_TOKEN remains the default GitHub credential; GITHUB_CLASSIC_PAT is bindable when the task needs that credential. Do not rewrite the make-pr sentence that says SONAR_TOKEN and SEMGREP_APP_TOKEN are not required. | Cursor Build agent | `medium` | M | `[T1]` | `ops/secrets/session_start_secrets.py`, `ops/scripts/session_start_runtime_report.py`, `skills/l9-secrets/SKILL.md`, `AGENTS.md` |
| T4 | Spawn MCP servers whose env name is a vault name through a child-env bind. Cover PERPLEXITY_API_KEY, NOTION_API_KEY, N8N_API_KEY, N8N_API_URL, SEMGREP_APP_TOKEN, and GITHUB_TOKEN mapped onto GITHUB_PERSONAL_ACCESS_TOKEN. The wrapper binds into the child environment only. master.mcp.json and the rendered Cursor config keep placeholders and never receive values. Leave FIRECRAWL_API_KEY and TAVILY_MCP_URL unwired. | Cursor Build agent | `medium` | M | `[T1]` | `ops/secrets/vault_mcp_bridge.py`, `ops/secrets/vault-mcp-bridges.json`, `environment/mcp/master.mcp.json`, `ops/memory/mcp_instantiation.py` |

**Critical path:** T1 → T2 → T3 → T4

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | A vault name binds without a committed allow-list edit, and the identity client secret does not | T2 and T3 |
| M2 | Cursor and Claude can bind every non-refused prod / name, and the session names those grants | MCP child-env spawn |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | T1 | V1 pytest shows a fixture vault name absent from the yaml is allowed and CLAUDE_INFISICAL_CLIENT_SECRET is refused | stop before the IAM privilege is removed |
| C2 | T2 | V2 operator_only_iam --check exits 0 and a hosted-identity probe of AUTH0_CLIENT_ID is no longer required to fail | leave the forbid privilege in place and report the identity that could not delete it |
| C3 | T4 | V3 session report lists PERPLEXITY_API_KEY and V4 pre-commit catalog passes | do not render secret values into mcp.json to force a pass |

### Leverage

- **Ranked todos:** `T1`, `T2`, `T3`, `T4`
- **Shared causes:** allow-list narrower than the vault; agents are not shown the grant
- **Deletions / consolidations:** Delete the operator-only bind refusal and the hosted forbid privilege instead of adding AUTH0 to a reminder list; One list call replaces ninety SessionStart binds; Do not keep a second copy of vault values in mcp.json

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `update` | `T3` | Append one fragment: vault presence authorizes bind. Do not rewrite the existing make-pr token sentence. |
| CANONICAL_LAW.md | `n_a` | — | GITHUB_TOKEN remains the default GitHub credential. This plan does not edit the constitution. |
| skills/l9-secrets/SKILL.md | `update` | `T3` | The grant is vault presence. The skill must say so, including the identity-secret refusal. |
| INVARIANTS.md | `n_a` | — | The make-pr row that says the scanner tokens are not required stays true. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `.venv/bin/python -m pytest tests/ops/secrets/test_capability_bind.py -q` | PASS, including a vault-list name absent from the yaml and a refusal of CLAUDE_INFISICAL_CLIENT_SECRET | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `.venv/bin/python ops/secrets/operator_only_iam.py --check` | exit 0 when operator_only_keys is empty and the forbid privilege is not required | `not_run` |
| E-V3 | SP-03 | `quality_gate_evidence` | command | `.venv/bin/python ops/scripts/session_start_runtime_report.py` | report lists PERPLEXITY_API_KEY as authorized and contains no secret value | `not_run` |
| E-V4 | SP-04 | `quality_gate_evidence` | command | `bash ops/scripts/run_pr_precommit.sh .pre-commit-config.yaml` | .pre-commit-config.yaml changed-file catalog exits 0 | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does unioning the live list let a name through before anyone reviews it?
- Does opening AUTH0_CLIENT_SECRET to Claude hand the Memory tenant admin client to a hosted session?
- Does the session catalog print a value if the list call is made with viewSecretValue=true?
- Does the MCP wrapper write the bound value back into mcp.json?

### Assumption failure conditions

- A committed allow-list that matches today's 93 names stays true after the next vault write
- Removing the IAM forbid is optional because the repo refusal was the real boundary
- FIRECRAWL_API_KEY becomes usable because the MCP template mentions it

### Blast radius notes

- Cursor and Claude can bind every non-refused prod / secret, including the Auth0 Memory admin client and GITHUB_CLASSIC_PAT. A bug in the MCP child environment can expose one bound value to that child process. The session report can leak a value only if the list call requests values.

### Rollback constraints

- Revert the branch. Restore operator_only_keys and run operator_only_iam.py --apply to put the forbid privilege back. No vault value is rotated by this change. The machine-identity secrets were never issued.

### Risks

| risk | mitigation |
|------|------------|
| Claude can bind the Auth0 client that administers the Memory tenant | Bind stays in-process. The session catalog prints names only. Rollback restores the forbid privilege with operator_only_iam.py --apply. |
| The live-list union authorizes a newly created vault name with no review commit | That is the operator rule. The committed mirror is still updated in the same change so review sees today's names, and REFUSED_NAMES still blocks the identity secrets. |
| The hook carrier expects L9_MEMORY_HOOK_CLIENT_ID and L9_MEMORY_HOOK_CLIENT_SECRET, which are not in the vault | Drop them from the committed mirror and leave the carrier calling bind. It stays unbound until those names exist in the vault, at which point the live list authorizes them. |

## Out of scope

- Creating FIRECRAWL_API_KEY or TAVILY_MCP_URL; those names are not in the vault and are not a grant
- hydrate --export, printing values, or writing values into mcp.json, receipts, or chat
- Deleting AWS Secrets Manager objects
- Rewriting CANONICAL_LAW.md; GITHUB_TOKEN stays the default GitHub credential
- Making make pr require SONAR_TOKEN or SEMGREP_APP_TOKEN
- Implementing this change on the dirty feat/pr-review-permission checkout
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.the_infisical_vault_is_the_grant.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.the_infisical_vault_is_the_grant.v1` |
| source_ref | `plan.simple.the_infisical_vault_is_the_grant.v1` |
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
| `unknown` | U1 | Can this surface's machine identity delete the hosted forbid privilege, or can only a project admin? — If --apply cannot delete it, Claude bind of the Auth0 names still fails at Infisical after the repo refusal is gone. | `accept_bounded` |
| `open_blocker` | stop_reason | Plan is ready for Cursor Build. Implementation has not run. U1 is bounded: if the IAM delete fails, report it and do not claim Claude can read the Auth0 names. | planning convergence `partial` |

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
  plan_id: "plan.simple.the_infisical_vault_is_the_grant.v1"
  name: "The Infisical vault is the grant"
  overview: "A name present in Infisical project cursor-governance prod / is authorized for Cursor and Claude to bind when the task needs that system. The committed allow-list matches the vault. Agents see the name catalog at session start and are not asked to wait for a reminder. Values are never printed, exported, or written into mcp.json."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "Quantum-L9/Cursor-Governance"
  commit_sha: "f925f796dcece4c651b0c2673177bf280ecda151"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "A name present in Infisical project cursor-governance prod / is authorized for Cursor and Claude to bind when the task needs that system. The committed allow-list matches the vault. Agents see the name catalog at session start and are not asked to wait for a reminder. Values are never printed, exported, or written into mcp.json."
  success_properties:
    - id: "SP-01"
      property: "V1 passes: capability_bind allows every name in the vault-list fixture, including AUTH0_CLIENT_SECRET, GITHUB_CLASSIC_PAT, L9_MEMORY_NEO4J_URI, and VANILLASOFT_API, and refuses CLAUDE_INFISICAL_CLIENT_SECRET"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 passes: operator_only_iam --check exits 0 with an empty operator_only_keys list and no hosted forbid privilege required"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-03"
      property: "V3 passes: the session report lists PERPLEXITY_API_KEY as an authorized name and the report text contains no secret value"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-04"
      property: "V4 passes: the changed-file catalog in .pre-commit-config.yaml exits 0"
      evidence_type: "quality_gate"
      proof: ["V4"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.the_infisical_vault_is_the_grant.v1"
execution_envelope:
  filesystem:
    write_allow: ["ops/secrets/capability_bind.py", "ops/secrets/infisical-cursor-governance.yaml", "ops/secrets/operator_only_iam.py", "ops/secrets/session_start_secrets.py", "ops/secrets/vault_mcp_bridge.py", "ops/secrets/vault-mcp-bridges.json", "ops/scripts/session_start_runtime_report.py", "ops/memory/mcp_instantiation.py", "environment/mcp/master.mcp.json", "skills/l9-secrets/SKILL.md", "AGENTS.md", "tests/ops/secrets/test_capability_bind.py", "ops/secrets/test_session_start_secrets.py"]
    write_deny: ["CANONICAL_LAW.md", "INVARIANTS.md", "ops/autonomy/pr_board.py"]
  commands:
    allow: [".venv/bin/python -m pytest tests/ops/secrets/test_capability_bind.py -q", ".venv/bin/python ops/secrets/operator_only_iam.py --check", ".venv/bin/python ops/scripts/session_start_runtime_report.py", "bash ops/scripts/run_pr_precommit.sh", "bash ops/scripts/run_pr_precommit.sh .pre-commit-config.yaml"]
  network:
    mode: "bounded_external_write"
  secrets:
    access: "read_only_named"
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
rollback_contract_ref: "rollback.plan.simple.the_infisical_vault_is_the_grant.v1"
dependency_topology_ref: "dag.plan.simple.the_infisical_vault_is_the_grant.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4"]
stress_and_disconfirm:
  disconfirming_cases: ["Does unioning the live list let a name through before anyone reviews it?", "Does opening AUTH0_CLIENT_SECRET to Claude hand the Memory tenant admin client to a hosted session?", "Does the session catalog print a value if the list call is made with viewSecretValue=true?", "Does the MCP wrapper write the bound value back into mcp.json?"]
  assumption_failure_conditions: ["A committed allow-list that matches today's 93 names stays true after the next vault write", "Removing the IAM forbid is optional because the repo refusal was the real boundary", "FIRECRAWL_API_KEY becomes usable because the MCP template mentions it"]
out_of_scope: ["Creating FIRECRAWL_API_KEY or TAVILY_MCP_URL; those names are not in the vault and are not a grant", "hydrate --export, printing values, or writing values into mcp.json, receipts, or chat", "Deleting AWS Secrets Manager objects", "Rewriting CANONICAL_LAW.md; GITHUB_TOKEN stays the default GitHub credential", "Making make pr require SONAR_TOKEN or SEMGREP_APP_TOKEN", "Implementing this change on the dirty feat/pr-review-permission checkout"]
convergence_contract_ref: "conv.plan.simple.the_infisical_vault_is_the_grant.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Make the live prod / listing the allow-list. Mirror those names into root_env_keys, union a viewSecretValue=false list into allowed_names so a new vault name is authorized before the next commit, and add CLAUDE_INFISICAL_CLIENT_SECRET to REFUSED_NAMES beside the other machine-identity secrets. Drop L9_MEMORY_HOOK_CLIENT_ID and L9_MEMORY_HOOK_CLIENT_SECRET from the committed mirror because they are not in the vault; the live list authorizes them on the day they appear. Register AUTH0_CLIENT_NAME, GITHUB_CLASSIC_PAT, L9_MEMORY_NEO4J_URI, L9_MEMORY_NEO4J_USER, L9_MEMORY_NEO4J_PASSWORD, L9_STATE_MONGO_URI, MONGODB_ATLAS_CLIENT_ID, MONGODB_ATLAS_CLIENT_SECRET, and VANILLASOFT_API."
    status: "pending"
  - id: "T2"
    content: "Remove the operator-only bind refusal and the hosted IAM forbid. Empty operator_only_keys. operator_only_iam.py --check passes when the forbid privilege is absent, and --apply deletes it. AUTH0_CLIENT_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET bind on Cursor and Claude. Values stay in-process."
    status: "pending"
  - id: "T3"
    content: "Publish the authorized name catalog from that one list at SessionStart. The runtime report names every non-refused vault key and states that a listed name is authorized to bind when the task needs that system. Do not fetch values and do not add ninety individual binds. Append the same rule to skills/l9-secrets/SKILL.md and an AGENTS.md fragment. GITHUB_TOKEN remains the default GitHub credential; GITHUB_CLASSIC_PAT is bindable when the task needs that credential. Do not rewrite the make-pr sentence that says SONAR_TOKEN and SEMGREP_APP_TOKEN are not required."
    status: "pending"
  - id: "T4"
    content: "Spawn MCP servers whose env name is a vault name through a child-env bind. Cover PERPLEXITY_API_KEY, NOTION_API_KEY, N8N_API_KEY, N8N_API_URL, SEMGREP_APP_TOKEN, and GITHUB_TOKEN mapped onto GITHUB_PERSONAL_ACCESS_TOKEN. The wrapper binds into the child environment only. master.mcp.json and the rendered Cursor config keep placeholders and never receive values. Leave FIRECRAWL_API_KEY and TAVILY_MCP_URL unwired."
    status: "pending"
```
