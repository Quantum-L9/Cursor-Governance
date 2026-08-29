---
name: Infisical GHA OIDC on existing secrets plane
overview: "Land the WIP OIDC intent as a GitHub Actions workload-identity binding on the existing Infisical client and capability broker, without a new Claude bootstrap path, without Infisical/secrets-action, and without injecting raw secrets into the live Claude install or SessionStart surfaces."
todos:
  - id: w0-worktree-branch
    content: "Open an isolated worktree and branch from fetched origin/main named campaign/infisical-gha-oidc-v1. Do not mutate the dirty primary clone."
    status: pending
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: w1-register-campaign
    content: "Add campaign infisical-gha-oidc-v1 to CAMPAIGN_EXECUTION_POLICY.yaml (additive row, lane secrets, integration_branch campaign/infisical-gha-oidc-v1). Do not edit the claude-code-env-contract-v1 row."
    status: pending
    phase: execute
    depends_on: [w0-worktree-branch]
    evidence_property_refs: [SP-01]
  - id: w2-inventory-identity
    content: "Extend infisical-cursor-governance.yaml with a gha_oidc identity block. Update infisical-protocol.md and ops/secrets/README.md. Do not add ops/secrets/INFISICAL_OIDC_SETUP.md."
    status: pending
    phase: execute
    depends_on: [w1-register-campaign]
    evidence_property_refs: [SP-03]
  - id: w3-shared-oidc-login
    content: "Add one Infisical OIDC login helper next to port_aws_to_infisical.login. Broker and hydrate call it. Model surfaces still cannot export values."
    status: pending
    phase: execute
    depends_on: [w2-inventory-identity]
    evidence_property_refs: [SP-02]
  - id: w4-oidc-login-tests
    content: "Add mocked tests for OIDC login helper, hydrate trusted-operator OIDC config, model-surface refusal, and broker still refusing INFISICAL_CLIENT_SECRET."
    status: pending
    phase: execute
    depends_on: [w3-shared-oidc-login]
    evidence_property_refs: [SP-02]
  - id: w5-claude-bootstrap-comments
    content: "Comment-only on install.sh, bootstrap_agent_environment.sh, and setup_claude_code_plugins.sh: they are not Infisical OIDC consumers and must not export ANTHROPIC_API_KEY. No behavior change."
    status: pending
    phase: execute
    depends_on: [w3-shared-oidc-login]
    evidence_property_refs: [SP-04]
  - id: w6-operator-create-identity
    content: "Create the Infisical machine identity; bind subject after U1/U2 probe; write identity_id into inventory; set GitHub Actions variable INFISICAL_IDENTITY_ID via gh api."
    status: pending
    phase: execute
    depends_on: [w2-inventory-identity, w4-oidc-login-tests]
    evidence_property_refs: [SP-03]
  - id: w7-prove-and-pr-check
    content: "Run pytest ops/secrets/test_aws_secrets.py, make capability-contract-validate, make capability-broker-preflight, and make pr-check. Prove no claude-code-bootstrap.yml and no Infisical/secrets-action."
    status: pending
    phase: validate
    depends_on: [w4-oidc-login-tests, w5-claude-bootstrap-comments, w6-operator-create-identity]
    evidence_property_refs: [SP-05]
isProject: false
kernel_pass:
  bound_path: infisical_gha_oidc_conformance_8-20-26.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T17:20:00Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Stamp kernel_pass so the next editor is not the first to fail G_PLAN_KERNEL_PASS"
      - "Keep this plan's existing todos and body; do not reopen landed work from this stamp"
      - "Do not mix #374 end-of-file-fixer exclude into this corpus pass"
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-29T17:20:30Z
    body_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    deltas:
      - "Align with issue #377 and the #376 G_PRECOMMIT_CONFIG plus kernel_pass precedent"
      - "Leave docs/plans/_TEMPLATE.plan.md exempt via PLAN_SKIP_PREFIXES"
      - "Do not edit .pre-commit-config.yaml in this cluster"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T17:21:00Z
    body_sha256: "54b692175fff95ace0f4ba6b482b1475d686ed651b5cd6f79c387b976bb181e7"
    deltas:
      - "G_PLAN_ETC and G_PLAN_EITHER_OR stay clean after this stamp"
      - "Canonical body_sha256 is the post-stamp file hash with sha fields zeroed"
      - "Do not mark status executable while the checker still fails"
---

# PLAN: Infisical GHA OIDC on existing secrets plane

> **PLAN_DOCUMENT:** `docs/plans/infisical_gha_oidc_conformance_8-20-26.plan.json` (`validate_plan_document.py` PASS)
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Status:** `draft` (implementation_ready after U1/U2 probe + isolated worktree)

## Execute via @environment/program-execution + autonomy (required)

**Authority order (fail-closed — see `environment/agents/PEER_EXECUTION.md`):**

```text
this .plan.md  (intent / envelope / DAG / success properties)
        │ project
        ▼
@environment/program-execution   HOW work executes (authoritative)
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
        │
        ▼
Peer Execution Core -> thin provider
  (Cursor: cursor-foreground | cursor-background)
```

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`autonomous_merge: false`. Publish later only via `PR_REMEDIATE=0 make pr` after L4 release. Do not free-form mutate from this markdown.

### Campaign authorization packet (fill at execute)

```yaml
packet_id: autonomy-2026-08-20-infisical-oidc
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: docs/plans/infisical_gha_oidc_conformance_8-20-26.plan.md
plan_id: plan.secrets.infisical-gha-oidc.v1
declared_branches: [campaign/infisical-gha-oidc-v1]
forbidden_inside_packet:
  - create_claude-code-bootstrap_workflow
  - add_Infisical_secrets-action
  - inject_ANTHROPIC_API_KEY_into_model_surface
  - create_github_environment_production
  - merge_outside_l4_plan_build_stack
  - force_push
```

### Phase-0 action table ↔ PE Task Cards

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| w0-worktree-branch | TASK-001 | W0 | [] | true | `repo:HEAD` | `preflight` | `pes.w0.worktree` | `work` | `cursor-foreground` |
| w1-register-campaign | TASK-002 | W1 | [w0-worktree-branch] | true | `path:CAMPAIGN_EXECUTION_POLICY.yaml` | `campaign` | `pes.w1.campaign` | `work` | routed |
| w2-inventory-identity | TASK-003 | W1 | [w1-register-campaign] | true | `path:ops/secrets/*` | `inventory` | `pes.w1.inventory` | `work` | routed |
| w3-shared-oidc-login | TASK-004 | W1 | [w2-inventory-identity] | true | `path:ops/secrets/*.py` | `client` | `pes.w1.oidc-login` | `work` | routed |
| w4-oidc-login-tests | TASK-005 | W1 | [w3-shared-oidc-login] | true | `path:ops/secrets/test_aws_secrets.py` | `tests` | `pes.w1.tests` | `work` | routed |
| w5-claude-bootstrap-comments | TASK-006 | W1 | [w3-shared-oidc-login] | true | `path:install.sh+bootstrap+plugins` | `comments` | `pes.w1.comments` | `work` | routed |
| w6-operator-create-identity | TASK-007 | W2 | [w2-inventory-identity, w4-oidc-login-tests] | true | `path:infisical-cursor-governance.yaml` | `identity` | `pes.w2.identity` | `work` | `cursor-foreground` |
| w7-prove-and-pr-check | TASK-008 | W2 | [w4-oidc-login-tests, w5-claude-bootstrap-comments, w6-operator-create-identity] | false | `evidence:plan.secrets.infisical-gha-oidc.v1` | `validate` | `pes.w2.prove` | `work` | `ci-*` |

**Stop / do not execute when:** U1/U2 unprobed before w6; dirty primary clone used for mutation; attempt to add `claude-code-bootstrap.yml`.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.secrets.infisical-gha-oidc.v1` |
| name | Infisical GHA OIDC on existing secrets plane |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | governance-control-plane |
| created_at | `2026-08-20` |
| updated_at | `2026-08-20` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `ops/secrets/README.md` + `environment/agents/adapters/ADAPTER_CONTRACT.md` capability carrier + `capability_broker.py` `workload_identity` |
| plan_class | `integration_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | OIDC is a trusted-operator / CI workload identity. Claude bootstrap stays `make claude-install` → `install.sh` → `bootstrap_agent_environment.sh` → `bootstrap_agent_env.sh --check`. Do not invent a GHA Claude session path. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-20T21:41:36Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/Users/ib-mac/Cursor-Governance` |
| ssot_clone | `$HOME/.cursor-governance` |
| branch | `main` at capture; execute on `campaign/infisical-gha-oidc-v1` |
| commit_sha | `b406feeb4734f7029c36d718a68b004cacd6a68a` |
| dirty | `true` (unrelated WIP on primary clone) |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |
| allowed_local_dirt | none on the campaign worktree |

## Objective

### Mission

The WIP pack’s useful concept is: GitHub Actions mints an OIDC JWT; Infisical validates `iss`/`aud`/`sub`; a dedicated machine identity receives a short-lived token. That concept already has an owner: `capability_broker.py` `oidc-workload-identity` → `POST /api/v1/auth/oidc-auth/login` with `identityId` + `jwt`. The live Infisical read client is `hydrate_infisical.py` / `port_aws_to_infisical.login` (Universal Auth today).

The pack’s attached consumer is the conflict. Claude bootstrap as it exists does **not** pull `ANTHROPIC_API_KEY`. `install.sh` calls shared bootstrap; bootstrap runs `bootstrap_agent_env.sh --check` and **warns** if raw secrets are present. `setup_claude_code_plugins.sh` needs a local `claude` binary and writes `$HOME/.claude/`. Putting those on `ubuntu-latest` behind Infisical/secrets-action creates a parallel secrets client and a parallel bootstrap.

Right implementation: extend the existing secrets plane; leave Claude bootstrap ingress unchanged except comments that make the refusal explicit.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Isolated campaign branch from `origin/main`; primary dirty clone not mutated | `repository_state` | worktree `git rev-parse --abbrev-ref HEAD` == `campaign/infisical-gha-oidc-v1` | true |
| SP-02 | One Infisical OIDC login helper; broker + hydrate call it; no `Infisical/secrets-action` | `structural` | helper symbol imported; `rg Infisical/secrets-action .github ops/secrets` empty | true |
| SP-03 | GHA OIDC identity lives in `infisical-cursor-governance.yaml` + protocol; no `INFISICAL_OIDC_SETUP.md` SSOT | `filesystem` | yaml has `gha_oidc`; `ops/secrets/INFISICAL_OIDC_SETUP.md` absent | true |
| SP-04 | Claude bootstrap still hydrates no raw secrets and still does not call Infisical OIDC | `structural` | `rg oidc-auth\\|ANTHROPIC_API_KEY` on install.sh / bootstrap / plugins is comments only | true |
| SP-05 | `make pr-check` PASS; no `claude-code-bootstrap.yml` | `quality_gate` | `make pr-check` PASS; file absent under `.github/workflows` | true |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.secrets.infisical-gha-oidc.v1` |
| blocking | `true` |
| baseline_verified | capture SHA `b406feeb4734f7029c36d718a68b004cacd6a68a` |

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` on campaign worktree | equals locked SHA at execute start or stop_and_replan | true |
| CP-02 | `secrets_plane_import` | locked venv import `yaml`, `pydantic` | `make gov-python` equivalent | true |
| CP-03 | `gh_api` | `gh api user` / repo vars | PAT from `openclaw-igorbot/github#token` works for variable write | true |
| CP-04 | `infisical_org_probe` | operator list identities (U2) | know whether a GHA OIDC identity already exists | true for w6 only |

## Execution envelope

### Filesystem

- **write_allow:** `ops/secrets/infisical-cursor-governance.yaml`, `ops/secrets/README.md`, `ops/secrets/port_aws_to_infisical.py`, `ops/secrets/capability_broker.py`, `ops/secrets/hydrate_infisical.py`, `ops/secrets/test_aws_secrets.py`, `skills/l9-aws-secrets/references/infisical-protocol.md`, `environment/agents/adapters/claude-code/install.sh`, `ops/scripts/bootstrap_agent_environment.sh`, `ops/scripts/setup_claude_code_plugins.sh`, `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`
- **write_deny:** `.github/workflows/**`, `CANONICAL_LAW.md`, `AGENTS.md`, `ops/hooks/session_start_bootstrap.sh`, `environment/agents/adapters/claude-code/mcp.template.json`, `environment/agents/adapters/claude-code/web/**`, `environment/agents/adapters/claude-code/validate_claude_env.py`, `ops/secrets/deploy/broker-kubernetes.yaml`

### Commands

- **allow:** locked pytest, `make capability-contract-validate`, `make capability-broker-preflight`, `make pr-check`, `gh api` for Actions variables, Infisical identity create (operator)
- **deny:** `Infisical/secrets-action`, raw `git push`, `gh pr create`, force-push, writing `.env`, exporting secret values to chat

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `app.infisical.com` (operator identity create), `api.github.com` (vars), no C1 |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` (inventory IDs only in git; values never committed) |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| w0-worktree-branch | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | remove unused worktree | false |
| w1-register-campaign | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert campaign row | false |
| w2-inventory-identity | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert yaml/docs | false |
| w3-shared-oidc-login | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert helper; restore broker inline login | false |
| w4-oidc-login-tests | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert tests | false |
| w5-claude-bootstrap-comments | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert comments | false |
| w6-operator-create-identity | `external_state_mutation` | `unsafe_blind_repeat` | `manual_only` | leave unused identity unused; unset GH var | false |
| w7-prove-and-pr-check | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| w2-inventory-identity | secrets inventory | `ops` | `infisical-cursor-governance.yaml` | second markdown SSOT |
| w3-shared-oidc-login | Infisical client | `ops` | `hydrate_infisical.py` + `capability_broker.py` | Infisical/secrets-action; new client module tree |
| w5-claude-bootstrap-comments | Claude adapter | `runtime` | `install.sh` + `ADAPTER_CONTRACT.md` | new bootstrap script; GHA plugin setup |
| w6-operator-create-identity | Infisical org + GitHub vars | `external_system` | `l9-aws-secrets` + CANONICAL_LAW §14 | GitHub Settings UI; Environment `production` |

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.secrets.infisical-gha-oidc.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | campaign branch only |
| data | `none` | no vault value migration |
| external_state | `manual_recovery` | unused Infisical identity left unused; GH var deleted via `gh api` |
| local_state | `git_restore_scoped_paths` | drop worktree if unused |

**Irreversible operations:** none required. Creating an Infisical identity is append-only org state; it is not a secret leak if unused.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `medium` |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `1` (CI identity ↔ secrets plane; Claude bootstrap comments only) |
| external_systems_touched | `2` (Infisical org, GitHub Actions variables) |
| migration_required | `false` |
| unknown_dependency_count | `2` (U1, U2) |

## Execution DAG

**Critical path:** `w0-worktree-branch` → `w1-register-campaign` → `w2-inventory-identity` → `w3-shared-oidc-login` → `w4-oidc-login-tests` → `w6-operator-create-identity` → `w7-prove-and-pr-check`

`w5-claude-bootstrap-comments` is parallel after `w3-shared-oidc-login`.

**Forbidden edges:** any todo that adds `.github/workflows/claude-code-bootstrap.yml`; any todo that edits `claude-code-env-contract` files.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | worktree branch | `git rev-parse --abbrev-ref HEAD` | `campaign/infisical-gha-oidc-v1` | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | helper + rg | pytest + `rg Infisical/secrets-action` | helper used; rg empty | `not_run` |
| EV-SP-03 | SP-03 | `filesystem` | inventory files | `rg gha_oidc ops/secrets/infisical-cursor-governance.yaml` | match; no INFISICAL_OIDC_SETUP.md | `not_run` |
| EV-SP-04 | SP-04 | `structural_evidence` | comment-only diff | `git diff` on three bootstrap files | comments only | `not_run` |
| EV-SP-05 | SP-05 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

- If a live GHA job already needs Infisical values, add **one step to that job** (request JWT → file → `hydrate --check`). Do not create a new workflow.
- If shared helper import cycles or exposes a value path to model surfaces, keep login on the broker and add only a thin wrapper imported one way.
- If AWS OIDC already uses a GitHub Environment (U1), match that subject. Do not invent `production` otherwise.
- If Claude CLI on this machine requires `ANTHROPIC_API_KEY` (U4), do not add it to the leak list in this plan. Env-contract campaign owns that list.
- If Infisical cannot add a second identity (U2), stop at inventory-plus-helper; do not reuse Cursor Universal Auth for GHA.

## Out of scope

- New workflow `claude-code-bootstrap.yml`
- `Infisical/secrets-action`
- Infisical folder `/claude-code` and `ANTHROPIC_API_KEY` injection
- GitHub Environment `production`
- Running `setup_claude_code_plugins.sh` or `install.sh` on GitHub-hosted runners
- `claude_code_env_contract_8-20-26.plan.md` (broker MCP facade, GH_TOKEN stripping, bootstrap-state.json)
- Replacing Cursor Universal Auth chicken-egg in AWS
- Changing `memory-distill.yml` AWS OIDC
- Applying `broker-kubernetes.yaml` on C1

## Follow-on milestone

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | When a trusted-operator GHA job needs Infisical, add JWT-file + `hydrate --check` to **that** workflow | First real consumer; still no new Claude bootstrap job |
| P2 | Optional `job_workflow_ref` tighten after that workflow exists | Least privilege without inventing Environments |

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.secrets.infisical-gha-oidc.v1` |
| current_state | `partial` |
| implementation_ready | `false` until U1/U2 probed and worktree exists |

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U1 | AWS_ROLE_TO_ASSUME trust (ref vs environment) | probe |
| unknown | U2 | Existing Infisical GHA OIDC identity? | probe |
| unknown | U3 | Any GHA job need Infisical values soon? | accept_bounded (no new workflow this plan) |
| unknown | U4 | Local Claude `ANTHROPIC_API_KEY` vs OAuth | accept_bounded (env-contract owns leak list) |

### Next

| Field | Value |
|-------|-------|
| next_skill | `l9-ynp` |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) |
| broader_work_requires_separate_contract | `true` |

Machine JSON: `docs/plans/infisical_gha_oidc_conformance_8-20-26.plan.json` (validator PASS).
