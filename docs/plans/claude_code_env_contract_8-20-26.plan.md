---
name: Claude Code environment contract repair (cloud/desktop → one session contract)
overview: "Execute the campaign brief at WIP/PE Claude Code Environment.md: repair the Claude Code bootstrap in Quantum-L9/Cursor-Governance so Web/Mobile/CLI/Desktop sessions share one governance contract — cloud setup scripts own only machine-level provisioning, mutable per-session work moves to the committed SessionStart path, the zero-static-secret capability contract becomes the single enforced contr..."
todos:
  - id: p1-register-campaign
    content: "Register campaign claude-code-env-contract-v1 in CAMPAIGN_EXECUTION_POLICY.yaml (additive entry: integration_branch campaign/claude-code-env-contract-v1, lane claude_env)"
    status: pending
    phase: execute
    depends_on: []
  - id: w1-setup-provisioning-only
    content: "web/setup.sh: delete consumer workspace toolchain install (step 5) and pre-commit warm (step 6); keep gh install, governance clone/validate, adapter install; note the move in comments"
    status: pending
    phase: execute
    depends_on: [p1-register-campaign]
  - id: w1-sessionstart-cloud-refresh
    content: "hooks/session_start_claude_governance.sh: add CLAUDE_CODE_REMOTE=true branch — fetch origin/main, reset ephemeral governance clone, record exact revision; local branch never resets, reports revision/drift"
    status: pending
    phase: execute
    depends_on: [w1-setup-provisioning-only]
  - id: w1-sessionstart-deps-helper
    content: "Create hooks/session_deps_cloud.sh: idempotent fingerprint-cached consumer workspace toolchain install (uv.lock/pip/npm) + pre-commit warm, invoked from SessionStart only when CLAUDE_CODE_REMOTE=true"
    status: pending
    phase: execute
    depends_on: [w1-sessionstart-cloud-refresh]
  - id: w1-committed-wiring-required
    content: "web/README.md: replace 'Not strictly required for Mobile/Web' with REQUIRED committed .claude/settings.json + .claude/hooks wiring for governed repos; update setup-field table and step 4 text"
    status: pending
    phase: execute
    depends_on: [w1-setup-provisioning-only]
  - id: w2-env-no-gh-token
    content: "web/environment.env.example: remove the GH_TOKEN=proxy-injected assignment; keep prohibition comments (leave UNSET; Anthropic platform proxy injects)"
    status: pending
    phase: execute
    depends_on: [p1-register-campaign]
  - id: w2-bootstrap-no-gh-export
    content: "web/setup.bootstrap.sh: stop exporting GH_TOKEN=proxy-injected (both process and durable cloud-session.env); keep stripping/unsetting real credentials"
    status: pending
    phase: execute
    depends_on: [w2-env-no-gh-token]
  - id: w2-mcp-brokered-memory
    content: "mcp.template.json: graphiti-memory -> url ${L9_CAPABILITY_BROKER_URL}/mcp, headers X-Capability-Id: graphiti.query + Authorization: ${CLAUDE_SESSION_JWT}; remove Bearer ${GRAPHITI_MCP_TOKEN}; update _comment"
    status: pending
    phase: execute
    depends_on: [w2-bootstrap-no-gh-export]
  - id: w2-validator-cross-file-contract
    content: "validate_claude_env.py: replace bearer enforcement with the cross-file zero-static-secret contract test (env.example <=> web/README <=> setup.bootstrap <=> setup.sh <=> mcp.template <=> bootstrap_agent_environment.sh <=> validator); ban GRAPHITI_MCP_TOKEN raw requirements and GH_TOKEN assignments; keep l9-shared-memory ban and URL env-ref checks"
    status: pending
    phase: execute
    depends_on: [w2-mcp-brokered-memory]
  - id: w2-front-door-tests
    content: "tests/test_graphiti_front_door.py: update to the brokered contract (no bearer in template; broker /mcp front door; DEGRADED posture wording)"
    status: pending
    phase: execute
    depends_on: [w2-validator-cross-file-contract]
  - id: w3-broker-mcp-facade
    content: "ops/secrets/capability_broker.py: extend /mcp to a real MCP facade — initialize (server info + capabilities), tools/list (search_memory, phase_lock, write_governed), tools/call mapping to graphiti.query / graphiti.write_governed capabilities; keep /capability; honest error envelopes when no platform identity"
    status: pending
    phase: execute
    depends_on: [w2-mcp-brokered-memory]
  - id: w3-broker-tests
    content: "Add broker facade tests (initialize/tools-list/tools-call JSON-RPC envelopes, capability mapping, no-identity rejection); run existing ops/secrets tests"
    status: pending
    phase: execute
    depends_on: [w3-broker-mcp-facade]
  - id: w3-honest-degraded-docs
    content: "Document honest memory posture: adapter README + web/README + SESSION_START_SPEC state memory=DEGRADED in ordinary Anthropic cloud until brokered identity exists (target: authenticated remote MCP through L9 broker)"
    status: pending
    phase: execute
    depends_on: [w3-broker-mcp-facade]
  - id: w4-installer-health-accumulator
    content: "install.sh: capture shared-bootstrap exit code; classify each step BLOCKED/DEGRADED/READY; use $GOV_PY for settings + skills reconciliation; final exit reflects BLOCKED (no unconditional 'adapter ready'); write ~/.l9/claude/bootstrap-state.json (schema l9.claude-bootstrap.v1)"
    status: pending
    phase: execute
    depends_on: [w2-validator-cross-file-contract]
  - id: w4-validator-installer-checks
    content: "validate_claude_env.py: add checks — install.sh runs Python steps on $GOV_PY, writes the l9.claude-bootstrap.v1 receipt, and never prints unconditional ready on failure"
    status: pending
    phase: execute
    depends_on: [w4-installer-health-accumulator]
  - id: w5-skill-plugin-ownership
    content: "Adapter README: skills are fed by reconcile_claude_l9_skills.py via install.sh (canonical); setup_claude_code_plugins.sh installs OPTIONAL marketplace plugins (local/Desktop augmentation, project-scoped where declared); plugins not required for Web/Mobile parity; keep make claude-plugins as explicit local enhancement"
    status: pending
    phase: execute
    depends_on: [w4-installer-health-accumulator]
  - id: w6-sessionstart-readiness-projection
    content: "session_start_claude_governance.sh: remove autonomy-surface-parity exception; read ~/.l9/claude/bootstrap-state.json; emit compact 'L9 Claude environment' status (surface, execution, governance rev + fresh/stale, bootstrap, project wiring, capability broker, memory, skills, rules); still exit 0 always (fail-open)"
    status: pending
    phase: execute
    depends_on: [w4-installer-health-accumulator, w1-sessionstart-deps-helper]
  - id: w6-make-claude-env-doctor
    content: "Makefile: claude-env -> $(MAKE) claude-install-check + $(PYTHON) validate_claude_env.py (canonical doctor). ROOT FILE additive_only: commit must carry ALLOW-ROOT-DELETION marker; CODEOWNERS approval at PR review"
    status: pending
    phase: execute
    depends_on: [w4-installer-health-accumulator]
  - id: v1-validation-gates
    content: "Run full validation: make claude-env (new doctor), make claude-skills-test, pytest adapter tests, make pr-check; negative test (plant token -> validator FAIL -> remove)"
    status: pending
    phase: execute
    depends_on: [w6-make-claude-env-doctor]
  - id: l4-publish
    content: "L4: l4_local.py begin/record-kernels/authorize-release -> PR_REMEDIATE=0 make pr with PR_BASE=origin/campaign/claude-code-env-contract-v1; end green + merge-ready; no merge"
    status: pending
    phase: execute
    depends_on: [v1-validation-gates]
isProject: false
---

# PLAN: Claude Code environment contract repair (cloud/desktop → one session contract)

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `claude-code-environment-contract-repair-cloud-desktop-one-session-contract_d831c66d.plan.md`

## Objective (from PLAN_DOCUMENT)

Execute the campaign brief at WIP/PE Claude Code Environment.md: repair the Claude Code bootstrap in Quantum-L9/Cursor-Governance so Web/Mobile/CLI/Desktop sessions share one governance contract — cloud setup scripts own only machine-level provisioning, mutable per-session work moves to the committed SessionStart path, the zero-static-secret capability contract becomes the single enforced contract (validator included), Graphiti memory reports an honest DEGRADED state in ordinary Anthropic cloud until a brokered identity exists, install.sh becomes a canonical health-classifying installer with a machine-readable receipt, L9 skill activation is separated from optional marketplace plugins, and SessionStart projects one cross-surface readiness status. PE machinery is explicitly parked (no Program Execution changes).

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Cross-file zero-static-secret contract holds and is enforced by validate_claude_env.py; a planted raw-token requirement anywhere in the contract chain FAILs the validator (negative test). | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | mcp.template.json contains no GRAPHITI_MCP_TOKEN reference; graphiti-memory is routed through the broker /mcp front door with a platform-issued identity (CLAUDE_SESSION_JWT), never a static bearer. | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | install.sh classifies every step BLOCKED/DEGRADED/READY, exits nonzero when the shared bootstrap fails, uses $GOV_PY for all Python steps, and writes ~/.l9/claude/bootstrap-state.json (schema l9.claude-bootstrap.v1). | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | web/setup.sh owns only machine-level cloud provisioning (gh, governance clone, locked venv, durable non-secret env); consumer workspace toolchain install moved to an idempotent fingerprint-cached SessionStart helper. | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | SessionStart hook branches on CLAUDE_CODE_REMOTE=true (refresh ephemeral governance clone, record exact revision) vs local (never reset; report revision/drift), drops the autonomy-surface-parity exception, and emits a compact L9 Claude environment status block from the bootstrap receipt. | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | web/README.md and the adapter README state .claude/settings.json + hooks are REQUIRED committed wiring for governed repos, and marketplace plugins (hookify/pr-review-toolkit/desktop-commander/context7) are optional local/Desktop augmentation, not the L9 skill mechanism. | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | make claude-env becomes the canonical doctor: claude-install-check + validate_claude_env.py. | quality_gate | observe during PE verify / make pr-check | true |
| SP-08 | Broker /mcp speaks the MCP handshake (initialize, tools/list, tools/call) mapping to graphiti.query / graphiti.write_governed capabilities, with unit tests; ordinary Anthropic cloud without brokered identity reports memory=DEGRADED honestly. | quality_gate | observe during PE verify / make pr-check | true |
| SP-09 | make pr-check PASSes, adapter test suites PASS, and the campaign PR is published green + merge-ready via PR_REMEDIATE=0 make pr (no merge from this path). | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** environment/agents/adapters/claude-code/ (install.sh, mcp.template.json, settings.template.json if needed, hooks/, web/, memory/, tests/, validate_claude_env.py, README.md), ops/secrets/ (capability_broker.py /mcp facade, capability_client.py posture, capabilities.yaml comments only), ops/scripts/ (bootstrap_agent_environment.sh read-only verification, reconcile_claude_settings.py, reconcile_claude_l9_skills.py, setup_claude_code_plugins.sh doc/comment alignment only), .claude/ (repo settings.json — no change expected; verified committed wiring), Makefile (claude-env target change; ALLOW-ROOT-DELETION marker required), environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml (register campaign claude-code-env-contract-v1, additive), WIP/8-17-25/claude-code-env-contract/ (plan + execution record artifacts)

**Out:**
- Program Execution machinery changes (intent: park PE completely)
- canonical.template.executable_plan.v1.plan.md / PE schema evolution
- Graphiti server-side (C1/Caddy) or docker-compose changes
- pyproject.toml, requirements.txt, .pre-commit-config.yaml, AGENTS.md, CANONICAL_LAW.md
- Web/Mobile network-policy.md allowlist changes beyond what the README already requires
- Building a production cloud broker deployment (k8s/deploy) — code only
- Merging the PR (merge requires /l9-pr-remediation invocation)

## Critical path (seed)

p1-register-campaign → w2-env-no-gh-token → w2-bootstrap-no-gh-export → w2-mcp-brokered-memory → w2-validator-cross-file-contract → w4-installer-health-accumulator → w6-sessionstart-readiness-projection → w6-make-claude-env-doctor → v1-validation-gates → l4-publish

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Cross-surface: every Claude surface (Web/Mobile/CLI/Desktop/Dispatch) consumes install.sh, mcp.template.json, SessionStart hook and setup scripts; validator feeds make pr-check; broker /mcp is trusted-side ops/secrets. High blast radius, all changes reversible via git revert, no PE/Graphiti-server/Infra changes.
- Rollback: Each wave is a separately-committed unit; revert per-commit restores prior behavior. mcp.template.json + validator flip land as one atomic commit so the gate never enforces a contract the template violates. SessionStart stays fail-open (exit 0) so a broken projection can never block a session. ~/.l9/claude/bootstrap-state.json is a non-repo artifact (last-write-wins).

## Convergence (seed)

- status: partial
- next_skill: l9-pr-remediation (post-publish; merge only on user invocation)
- stop_reason: plan ready for execution; unknowns resolved by probes during their waves
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: Claude Code environment contract repair (cloud/desktop → one session contract)

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_YYYY-MM-DD.plan.md` before execute.
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

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
  MAY the leased agent act?  (packet, lanes, PR poll) — owns_program_state: false
        │
        ▼
Peer Execution Core -> thin provider
  (Cursor: cursor-foreground | cursor-background;
   Claude: claude-code-direct)
```

Program leases are authoritative. Autonomy leases are subordinate and **must not outlive** the Program lease (`COMPATIBILITY.yaml` / autonomy-control-plane bridge). Never invent a second scheduler; never widen Blueprint ceilings via the campaign packet.

### Pipeline steps

Live execution is one command. Do not hand-run pec, L4, or inner compile
scripts from this template.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` projects the plan into Blueprint artifacts under
`$HOME/.l9/programs/<id>/`, admits the lock, executes every task, stacks
PRs, and closes into `campaigns/COMPLETED/<id>/`. Never mutate sealed
`environment/program-execution/core/` templates in place.

| Plan section | Runner-owned Blueprint / Controller artifact |
|--------------|-------------------------------------|
| metadata / objective | `PROGRAM.yaml` / program identity |
| immutable_baseline | `CURRENT_STATE_DELTA` + reconcile exact SHA |
| execution_envelope + architecture_impact | Task Card `authorization_ceiling` + Source/Rendered Contract paths |
| execution_DAG / todos | `DEPENDENCY_GRAPH.yaml` + `TASK_CARDS.yaml` + `EXECUTION_WAVES.yaml` |
| capability_preflight | Controller reconcile + gate probes before claim |
| property_evidence_matrix | Task Card `validation` / evidence catalog refs |
| rollback | Task Card `rollback` + recovery receipts |
| convergence | `CONVERGENCE_GATES.yaml` + Handoff Receipt (owner accepts verdict) |

If the runner exits nonzero, stop and report. Do not continue with
`pec.py bootstrap`, `claim`, `record-attempt`, or a second scheduler.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Work class | Prefer |
|------------|--------|
| interactive local repair (this Cursor plan default) | `cursor-foreground` → `claude-code-direct` |
| repository implementation | `claude-code-direct` → `cursor-background` → `cursor-foreground` |
| verification | `ci-github-actions` / `ci-generic-shell` |
| remote PR/merge actions | `github-remote-actions` only with exact approval |

### Campaign authorization packet (fill at execute — subordinate to Program Lock)

```yaml
packet_id: autonomy-<YYYY-MM-DD>-<n>
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence            # or program_deploy_max_autonomy when PES Phase-0 selects it
authority_profile: program_controller_bound
autonomous_merge: false            # COMPATIBILITY forbidden; L4 plan/PE stack merge after green+mergeable
plan_ref: <this .plan.md path>
plan_id: plan.<domain>.<slug>.v1
schema_ref: canonical.schema.plan_document.v1
program_execution:
  root: environment/program-execution
  program_id: pes-<slug>
  program_lock_digest: <sha256 from Controller>
  blueprint_ref: $HOME/.l9/programs/<program_id>/blueprint
  runtime_ref: $HOME/.l9/programs/<program_id>/runtime
  provider_ref: cursor-foreground  # or routed thin provider
  execution_profile_ref: worker-default
  autonomy_provider_id: root-autonomy-control-plane
declared_prs: []
declared_branches: [<feature-branch>]
allowed_inside_packet:
  - execute_rendered_contract_only
  - execute_plan_todos_inside_envelope
  - remediate_until_green
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch   # only after L4 release_authorized
  - inspect_ci_and_comments
forbidden_inside_packet:
  - widen_blueprint_or_task_card_ceiling
  - mutate_without_program_lease
  - outlive_program_lease
  - merge_outside_l4_plan_build_stack
  - force_push
  - admin_merge
  - expand_scope
  - commit_secrets
  - weaken_tests_for_green
  - direct_graphiti_task_claim
created_by: "/autonomy+program-execution"
```

### Phase-0 action table ↔ PE Task Cards

Derive from frontmatter todos + `execution_DAG`. Each row is both an autonomy action and a PE Task Card projection.

| id | pe_task_id | wave | depends_on | mutation | lock_keys | isolation_key | autonomy_action_id | kind | adapter_hint |
|----|------------|------|------------|----------|-----------|---------------|--------------------|------|--------------|
| todo-01-baseline-preflight | TASK-001 | W0 | [] | false | `repo:HEAD` | `preflight` | `pes.w0.task001` | `work` | `cursor-foreground` |
| todo-02-mutate | TASK-002 | W1 | [todo-01-baseline-preflight] | true | `path:<write_allow…>` | `mutate` | `pes.w1.task002` | `work` | routed |
| todo-03-prove | TASK-003 | W1 | [todo-02-mutate] | false | `evidence:<plan_id>` | `validate` | `pes.w1.task003` | `work` | `ci-*` / foreground |
| todo-04-converge | TASK-004 | W2 | [todo-03-prove] | true | `pr:<n>` / `branch:<name>` | `converge` | `pes.w2.task004` | `work` | `github-*` + poll |
| poll-pr-N | — | W2 | [todo-04-converge] | true | `pr:<n>` | `pr:<n>` | `pes.w2.poll.pr<n>` | `poll` | background |

**Spawn rules:** PE `claim`/`render` first for mutation rows; then @autonomy Protocol A (ready `work` Tasks in one message) / B (`poll` + `run_in_background: true`) / C (join) / D (PICKUP). Autonomy must not bypass wave order or Program Lock drift checks (`program_lock_stale_or_invalid` → stop).

**Stop / do not execute when:** plan status ≠ `executable`; PE Blueprint not accepted / Controller not bootstrapped; Program Lock drift; capability preflight blocked; DAG cyclic; envelope or Task Card ceiling incomplete; blocking unknowns remain; autonomy revoke / lease expired.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.<domain>.<slug>.v1` |
| name | *(same as frontmatter `name`)* |
| overview | *(same as frontmatter `overview`)* |
| schema_version | `1.0.0` |
| status | `draft` \| `preflight_blocked` \| `executable` \| `in_progress` \| `validation_failed` \| `converged` \| `superseded` |
| is_project | `false` *(frontmatter `isProject`)* |
| owner | |
| created_at | `YYYY-MM-DD` |
| updated_at | |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | path or ADR that owns architecture for this change |
| plan_class | `bounded_execution_contract` \| `migration_plan` \| `retirement_plan` \| `remediation_plan` \| `deployment_plan` \| `refactor_plan` \| `integration_plan` \| `recovery_plan` \| `custom` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via @environment/program-execution + subordinate @autonomy; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | ISO datetime |
| repository | `org/repo` |
| workspace | absolute or `$(pwd)` convention |
| ssot_clone | if applicable |
| branch | feature branch name |
| commit_sha | **full 40-char SHA** (PLAN-SCHEMA-001) |
| dirty | `true` \| `false` |
| artifact_hashes | `{ "path": "sha256:…" }` |
| allowed_local_dirt | optional path list |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` \| `require_clean_tree` \| `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

One paragraph: residual defect or feature; system bound; non-negotiable preserved contracts.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline still matches locked SHA at start | `repository_state` | `git rev-parse HEAD` == locked SHA | true |
| SP-02 | Declared behavior/structure holds after mutation | `runtime_behavior` \| `structural` \| `filesystem` | exact command + expected marker (not exit-0 alone) | true |
| SP-03 | Quality gate / PR gate PASS on changed files | `quality_gate` | e.g. `make pr-check` → PASS | true |

`evidence_type` ∈ `filesystem` \| `runtime_behavior` \| `structural` \| `quality_gate` \| `repository_state` \| `network_observation` \| `proof_receipt` \| `human_confirmation`

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → fill path or inline id below.

| Field | Value |
|-------|-------|
| preflight_id | `preflight.<plan_id>` |
| source_ref | this plan_id |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | baseline section / receipt path |
| baseline_verified | |
| drift_detected | |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `branch_and_HEAD_resolution` | `git rev-parse HEAD` | equals locked commit_sha | true |
| CP-02 | `command_available` | tool X present | version / path | true |
| CP-03 | `filesystem_write` | may_modify paths writable | write probe or ACL | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `path/or/glob/...`
- **write_deny:** `protected/...`, secrets, unrelated trees
- **delete_allow:** *(optional)*

### Commands

- **allow:** listed validation / mutate commands
- **deny:** force-push, hard-reset, secret exfil, out-of-scope installs

### Network

| Field | Value |
|-------|-------|
| mode | `none` \| `read_only` \| `named_services_only` \| `existing_tunnel_only` \| `bounded_external_write` |
| allowed_services | *(if named_services_only / bounded)* |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` \| `read_only_named` \| `runtime_injected_only` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005).

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| todo-01-baseline-preflight | `filesystem_read` | `safe_to_repeat` | `none` | null | false |
| todo-02-mutate | `filesystem_mutation` | `safe_with_dedupe` \| `unsafe_blind_repeat` \| `non_idempotent` | `manual_only` \| `retry_once` \| `bounded_retry` | restore scoped paths / revert | false |
| todo-03-prove | `filesystem_read` | `safe_to_repeat` | `retry_once` | null | false |
| todo-04-converge | `network_write` \| `none` | `safe_with_dedupe` | `manual_only` | close/abandon PR | false |

`side_effects` ∈ `none` \| `filesystem_read` \| `filesystem_mutation` \| `destructive_filesystem_mutation` \| `network_read` \| `network_write` \| `database_read` \| `database_write` \| `external_state_mutation` \| `human_approval`

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| todo-02-mutate | e.g. memory / ops / adapters | `control_plane` \| `data_plane` \| `chassis` \| `ops` \| `runtime` \| `policy` \| `assurance` \| `memory` \| `graph` \| `docs` \| `external_system` | ADR / schema / skill that owns it | redesign X; touch Y; invent Z |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.<plan_id>` |
| source_execution_ref | this plan_id |
| supported | `true` \| `false` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` \| `revert_commit` \| `none` | scoped to write_allow |
| data | `none` \| `restore_snapshot` \| `compensating_transaction` \| `manual_recovery` | |
| external_state | `none` \| `corrective_append_only_record` \| `manual_recovery` | never claim false reversibility |
| local_state | `none` \| `git_restore_scoped_paths` \| `manual_recovery` | |

### Irreversible operations

- *(enumerate; PLAN-SCHEMA-010)* none | …

### Rollback verification

- command / proof that rollback restored invariants

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` \| `medium` \| `high` \| `critical` |
| uncertainty | `low` \| `medium` \| `high` \| `critical` |
| blast_radius | `low` \| `medium` \| `high` \| `critical` |
| architectural_boundaries_crossed | `0` |
| external_systems_touched | `0` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

| Field | Value |
|-------|-------|
| receipt_path | |
| categories | `delete` \| `migrate_then_delete` \| `keep` \| `replace` \| `skip` |
| checksum_required | `true` |
| destructive_gate_required_for | `migrate_then_delete` |

## Gated write pipeline *(optional — irreversible or external writes)*

- **gates (ordered):** …
- **dedupe_before_non_idempotent_write:** `true`
- **bounded_write_count:**
- **receipt_required:** `true`

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| RG-01 | regenerator path / script | disable or retarget | prove artifact not recreated |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.<plan_id>` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| todo-01-baseline-preflight | agent | assurance | [] | baseline_receipt, preflight_receipt |
| todo-02-mutate | agent | *(layer)* | [todo-01-baseline-preflight] | mutated paths |
| todo-03-prove | agent | assurance | [todo-02-mutate] | validation_evidence refs |
| todo-04-converge | agent | control_plane | [todo-03-prove] | convergence receipt / PR |

**Critical path:** `todo-01-baseline-preflight` → `todo-02-mutate` → `todo-03-prove` → `todo-04-converge`

**Forbidden edges:** *(none, or list cycles / illegal orderings)*

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | locked SHA | `not_run` |
| EV-SP-02 | SP-02 | `property_evidence` \| `structural_evidence` \| `runtime_behavior_evidence` | … | … | marker / structure | `not_run` |
| EV-SP-03 | SP-03 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Assumption A false → …
- Probe/environment differs from baseline capture → …

### Assumption failure conditions

- Dirty tree overlaps `write_allow` under `stop_if_dirty_overlaps_may_modify`
- Blocking success property fails after mutation
- Unknown dependency discovered mid-flight (PLAN-SCHEMA-013)

### Blast radius notes

- …

### Rollback constraints

- No force-push / history rewrite
- External append-only systems → compensating record only

## Out of scope

- Adjacent features / refactors not listed in envelope
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution (see below)

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | `true` |

| priority | change | why |
|----------|--------|-----|
| P1 | … | … |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.<plan_id>` |
| source_ref | this plan_id |
| current_state | `draft` \| `preflight_blocked` \| `execution_ready` \| `executing` \| `validation_failed` \| `partial` \| `converged` |
| implementation_ready | `false` until preflight + DAG + envelope filled |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking SP-* evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** `EV-SP-01`, `EV-SP-02`, `EV-SP-03`
- **observed_evidence_refs:** *(fill during execution)*
- **missing_evidence:** *(fill)*

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| open_blocker | | | |
| unknown | U1 | | ask / measure / lock — do not infer away |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `execution_ready` → `executing` → `converged` |
| minimum_safe_next_action | When law holds and status=`executable`, attach [@environment/program-execution](environment/program-execution/) + [@autonomy](commands/autonomy.md); project→Lock→claim→render→autonomy lanes — do not free-form execute |
| execute_via | `@environment/program-execution` → Program Lock/Controller → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Copy out and fill when promoting to a validated plan_document artifact; keep in sync with sections above.

```yaml
schema_id: canonical.schema.plan_document.v1
schema_version: 1.0.0
metadata:
  plan_id: plan.domain.slug.v1
  name: Short plan title
  overview: "…"
  status: draft
  is_project: false
  created_at: YYYY-MM-DD
architect_framing:
  planning_ssot: …
  plan_class: bounded_execution_contract
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: org/repo
  commit_sha: REPLACE_WITH_FULL_SHA
  dirty: false
  artifact_hashes: {}
  overlap_policy: stop_if_dirty_overlaps_may_modify
  verification_rule: reverify_at_execution_start
  on_drift: stop_and_replan
objective:
  mission: …
  success_properties:
    - id: SP-01
      property: …
      evidence_type: repository_state
      proof: …
      blocking: true
capability_preflight_ref: preflight.plan.domain.slug.v1
execution_envelope:
  filesystem:
    write_allow: []
    write_deny: []
  commands:
    allow: []
    deny: []
  network:
    mode: none
  secrets:
    access: none
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency: []
architecture_impact: []
rollback_contract_ref: rollback.plan.domain.slug.v1
complexity_and_uncertainty:
  complexity: low
  uncertainty: low
  blast_radius: low
  architectural_boundaries_crossed: 0
  external_systems_touched: 0
  migration_required: false
  unknown_dependency_count: 0
dependency_topology_ref: dag.plan.domain.slug.v1
validation_evidence_refs: []
stress_and_disconfirm:
  disconfirming_cases: []
  assumption_failure_conditions: []
out_of_scope: []
convergence_contract_ref: conv.plan.domain.slug.v1
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  controller: environment/program-execution/core/program-execution-controller-template
  blueprint: environment/program-execution/core/program-execution-blueprint-template
  autonomy_provider: root-autonomy-control-plane
  autonomy_integration: environment/program-execution/integrations/autonomy-control-plane
  adapter_default: cursor-foreground
  command_ref: commands/autonomy.md
  slash: /autonomy
  skill: l9-bounded-autonomy
  mention_autonomy: "@autonomy"
  authority_order:
    - plan_document
    - program_lock_and_controller
    - autonomy_packet_subordinate
    - pe_adapter_worker
todos:
  - id: todo-01-baseline-preflight
    content: …
    status: pending
```
