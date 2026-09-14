---
name: Per-repository bootstrap correctness for multi-repo Claude cloud containers
overview: "Remove the recurring friction observed while executing the l9cr-context-compiler-pr-pack-v2 contract against Quantum-L9/l9-cognitive-runtime: make the Cursor-Governance cloud bootstrap resolve every repository in a multi-repo container instead of only the container root, and make readiness receipts bind to the governance revision they were produced against."
todos:
  - id: T1
    content: "Extract the per-repository workspace-root resolver into a shared library. memory_prefetch._hydration_roots() is the only correct multi-repo detector in the bootstrap (children of the workspace with a .git entry, sorted, capped at 6). Promote it verbatim to a shared module and make memory_prefetch import it, so one definition of 'which repositories is this session working in' exists."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Reconcile per-repository .claude mirrors. The claude-code-project projection adapter targets /home/user/.claude, so per-repo .claude/skills and .claude/commands mirrors created by earlier single-repo sessions sit outside every reconciler's target set and keep symlinks to skills the SSOT has removed. Iterate workspace_roots and apply the existing stale-removal path (reconcile_claude_l9_skills.remove_managed) to each repository mirror; report removals per repository in the projection receipt."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Make session_deps_cloud.sh provision each detected repository. Today --workspace receives /home/user, which holds no manifest, so the fingerprint degenerates to tool versions, toolchain_present() can never return true, and the install pass is a no-op that still reports 'toolchain ready'. Loop workspace_roots, fingerprint and stamp per repository, and aggregate a per-repo banner line."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Make the deps stamp assert applied state, not attempted state. Add a post-install proof per repository: uv sync --locked --check (or an equivalent lock-vs-environment probe) plus an import smoke of the repo's own package, and refuse to write the stamp or emit 'toolchain ready' unless the proof passes. This is the detector that would have caught RC-1 on the day it started."
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "Bind bootstrap receipt freshness to the governance revision. claude_bootstrap_receipt.py carries governance_revision through but expires on wall-clock TTL only, so a DEGRADED verdict produced against a superseded governance revision is reported as current. Return UNKNOWN with reason 'revision superseded' when the recorded revision differs from live governance HEAD."
    status: pending
    phase: execute
    depends_on: []
  - id: T6
    content: "Re-run the installer when the receipt is UNKNOWN or DEGRADED instead of reprinting it. SessionStart prints the receipt's own remediation string but never executes it, so a degraded verdict is inherited indefinitely. Invoke the adapter installer bounded and fail-open, then re-read the receipt so the banner reports post-repair state."
    status: pending
    phase: execute
    depends_on: [T5]
  - id: T7
    content: "Publish an observed GitHub transport truth-table for this surface and correct the stale prior-art record. gh is installed at /usr/bin/gh and gh api succeeds through the agent proxy, while gh auth status reports the GH_TOKEN sentinel invalid and still exits 0. Record which transports are proven working, mark rule 62's PAT-resolution path inapplicable on a model-controlled surface, and supersede P307 CR-105/CR-124 ('no gh CLI exists'), which the current container falsifies."
    status: pending
    phase: execute
    depends_on: []
  - id: T8
    content: "Seed agent-authority docs in l9-cognitive-runtime. It is the only in-scope repository with no CLAUDE.md, AGENTS.md, INVARIANTS.md or ARCHITECTURE.md, which is why the PR pack has to ship INVARIANTS.md for verbatim copy as step 3 of its own execution order. Add the authority pointer and invariants index so repo law is loadable without a pack."
    status: pending
    phase: execute
    depends_on: []
  - id: T9
    content: "Replace the standing publish breakglass with a scoped expiring receipt. L9_PUBLISH_PATH_OVERRIDE is exported into every session carrying the literal text 'one-time breakglass authorized by user', so a one-time authorization has become permanent configuration. Move it to a receipt with an issued-at and a TTL that the execution gate reads."
    status: pending
    phase: execute
    depends_on: []
kernel_pass:
  bound_path: .cursor/plans/l9-runtime-velocity_7c4a1e93.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T02:20:00Z
    body_sha256: "e23094e04a91cfde59f8aa763711d306a1f452f48ccbff5fd70538b16b6c7e20"
    deltas:
      - "bound Metadata, Architect framing and Immutable baseline to the observed container state (4 repositories, locked governance and runtime SHAs, reproduced deps fingerprint)"
      - "replaced the generic Success properties scaffold with SP-01..SP-08, each carrying a measured baseline and a falsifiable proof command"
      - "bound Capability preflight probes CP-01..CP-07 so the failing baseline and the residue must be reproduced before mutation"
      - "narrowed the Execution envelope to explicit write_allow/write_deny/delete_allow paths and named the denied command forms"
      - "bound Side effects, Architecture impact, Rollback strategies and Execution DAG to T1..T9 with forbidden edges"
      - "bound the Property evidence matrix to SP-01..SP-08 with exact commands and expected positives"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T02:24:00Z
    body_sha256: "e23094e04a91cfde59f8aa763711d306a1f452f48ccbff5fd70538b16b6c7e20"
    deltas:
      - "repaired a section-swallowing edit: an over-broad Success properties replacement had removed Capability preflight, Execution envelope and Side effects; re-rendered from the validated PLAN_DOCUMENT and re-applied with bounded replacements"
      - "verified the heading set is byte-identical to a fresh render, proving no template section was lost"
isProject: false
kind: pe
execute_via: pe-campaign
---

# PLAN: Per-repository bootstrap correctness for multi-repo Claude cloud containers

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `per-repository-bootstrap-correctness-for-multi-repo-claude-cloud-containers_d1b58860.plan.md`

## Objective (from PLAN_DOCUMENT)

Remove the recurring friction observed while executing the l9cr-context-compiler-pr-pack-v2 contract against Quantum-L9/l9-cognitive-runtime: make the Cursor-Governance cloud bootstrap resolve every repository in a multi-repo container instead of only the container root, and make readiness receipts bind to the governance revision they were produced against.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | l9-cognitive-runtime pytest is 184 passed / 0 failed with no dangling bootstrap symlinks in the tree (baseline today: 2 failed, 182 passed) | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | find /home/user/*/.claude -xtype l returns zero entries after a SessionStart in a multi-repo container (baseline today: 16 across 4 repos) | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | uv sync --locked --extra dev --dry-run reports zero package deltas in every detected repository after SessionStart (baseline today: 3 deltas in l9-cognitive-runtime including a missing declared dependency) | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | the session-deps banner names each repository it provisioned and its per-repo outcome, and never reports 'toolchain ready' for a repository whose lock is unapplied | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | claude_bootstrap_receipt.py reports state UNKNOWN when receipt.governance_revision does not equal the live governance HEAD, and SessionStart re-runs the installer instead of reprinting a stale DEGRADED verdict | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | make claude-env exits 0 in a correctly bootstrapped multi-repo container (baseline today: exit 5 on every session) | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** Cursor-Governance ops/scripts/lib shared workspace-root resolver extracted from environment/agents/adapters/claude-code/hooks/memory_prefetch.py, environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh per-repository provisioning, ops/scripts/claude_projection.py and ops/scripts/reconcile_claude_l9_skills.py per-repository .claude mirror reconciliation, ops/scripts/claude_bootstrap_receipt.py revision-bound staleness, environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh installer re-run on stale receipt, conformance tests under tests/ for each of the above

**Out:**
- implementing the CompiledTaskContext IR or any part of l9cr-context-compiler-pr-pack-v2
- changing the make pr publish path, merge authority, or L4 release gating
- changing Graphiti transport, broker identity, or the secret boundary
- repairing the invalid GH_TOKEN sentinel or provisioning a PAT on this surface
- rewriting the prior P307 environment-experience pack records
- any edit inside l9-cognitive-runtime beyond adding absent agent-authority docs (R5)

## Critical path (seed)

T1 → T2 → T3 → T4

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: SessionStart runs on every session of every governed cloud workspace, so a defect in T3 or T6 degrades or stalls every future session rather than one repository. T2 unlinks files inside consumer repositories; scoped wrongly it could remove tracked content. T9 touches the publish-path gate and is the only high-risk item; it is deliberately last and off the critical path.
- Rollback: Each TODO is an independent commit on a branch from origin/main. Revert order is reverse-dependency (T4, T3, T2, T1). The bootstrap is fail-open by construction: reverting restores the current behavior, which is degraded but non-blocking. T2 removals are recoverable because the mirrors are untracked, gitignored, and regenerable by the projection; no tracked file is deleted. T9 reverts to reading the environment variable.

## Convergence (seed)

- status: partial
- next_skill: l9-ynp
- stop_reason: Analysis is evidence-complete and the plan is structurally validated, but four unknowns remain that are resolvable only by reading CI history and the projection writer's git history; none blocks starting T1, and each is bound to the TODO that must resolve it before its own implementation.
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: Per-repository bootstrap correctness for multi-repo Claude cloud containers

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Execute:** when status is `executable`, run through **[@environment/program-execution](environment/program-execution/)** with autonomy as the subordinate orchestration plane — **[@autonomy](commands/autonomy.md)** / `l9-bounded-autonomy` under a Program lease. Do **not** free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to PE Task Cards + Phase-0 autonomy actions. Body is the binding contract.
> **Rename to:** `snake_case_name_<8hex>.plan.md` before execute.
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
| plan_id | `plan.bootstrap.per-repository-workspace-roots.v1` |
| name | Per-repository bootstrap correctness for multi-repo Claude cloud containers |
| overview | Make the cloud bootstrap resolve every repository in a multi-repo container instead of only the container root, and bind readiness receipts to the governance revision. |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | `false` |
| owner | ib@scrapmanagement.com |
| created_at | `2026-08-29` |
| updated_at | `2026-08-29` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `AGENTS.md` §2 + `environment/agents/adapters/claude-code/hooks/SESSION_START_SPEC.md` |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Repairs implementations of existing invariants. No new governance invariant, no publish-path change, no memory-transport change. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | 2026-08-29T01:47:07Z |
| repository | `Quantum-L9/Cursor-Governance` (primary); `Quantum-L9/l9-cognitive-runtime` (T8 only) |
| workspace | `/home/user` — multi-repo container, 4 repositories detected |
| ssot_clone | `/root/.cursor-governance` == `/home/user/Cursor-Governance` |
| branch | `claude/l9-runtime-velocity-analysis-yig5fe` |
| commit_sha | `0fc6ee6f2aadfbee885bf5bb708ff91c38205ba1` (governance) · `cc671c4bfd075d5158b9d34d52f1934fe81ece62` (l9-cognitive-runtime) |
| dirty | `false` in l9-cognitive-runtime at capture; governance carries this plan only |
| artifact_hashes | deps fingerprint `9ff843f2c5497a1fd3d6b792a4899071d33d54f4ea709ef369cb0aaa1c3f8df1` — reproduced from tool versions alone, proving zero manifests were seen |
| allowed_local_dirt | `WIP/8-29-26/l9-runtime-velocity/`, `.cursor/plans/` |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

SessionStart in a Claude cloud container assumes `WORKSPACE` is one repository. This container holds four. Only `memory_prefetch._hydration_roots()` iterates repositories; the dependency helper and the project-scope projection adapter both act on the container root, where no manifest and no consumed `.claude` mirror exists. One root cause produces three simultaneous defects: sixteen dangling bootstrap symlinks across four repositories, two failing tests in the in-scope repository caused by those links, and repository virtual environments that never receive the lock refreshed in the same session — while the banner reports `toolchain ready`. A second, independent defect makes readiness time-bound rather than revision-bound, so a DEGRADED receipt written against a superseded governance revision is reported as current and `make claude-env` exits 5 every session.

Preserved contracts, non-negotiable: SessionStart stays fail-open and exits 0; no git commit hook is installed; publish stays `make pr` and merge authority stays the `/l9-pr-remediation` receipt; this surface holds no credential; memory never gates repository writes.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline matches the locked SHAs at execution start | `repository_state` | `git rev-parse HEAD` equals the locked SHAs | true |
| SP-02 | No dangling bootstrap symlink survives SessionStart in any repository | `filesystem` | `find /home/user/*/.claude -xtype l` prints nothing (baseline: 16) | true |
| SP-03 | The in-scope repository's suite is green | `runtime_behavior` | `pytest -q` reports `184 passed` and no `failed` (baseline: `2 failed, 182 passed`) | true |
| SP-04 | Every uv repository is synchronized with its own lock after SessionStart | `structural` | `uv sync --locked --extra dev --dry-run` prints no package line (baseline: 3 deltas incl. missing `structlog`) | true |
| SP-05 | The banner names each repository and never claims readiness for an unapplied lock | `proof_receipt` | one status line per detected repository; no stamp when the applied-state proof fails | true |
| SP-06 | A receipt naming a superseded governance revision reads UNKNOWN | `proof_receipt` | hand-stamp a prior SHA; `claude_bootstrap_receipt.py --read` reports UNKNOWN, reason `revision superseded` | true |
| SP-07 | Readiness is informative again | `quality_gate` | `make claude-env` exits 0 (baseline: exit 5 every session) | true |
| SP-08 | Governed quality gate passes on the changed set | `quality_gate` | `make pr-check` PASS | true |

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
| CP-01 | `branch_and_HEAD_resolution` | `git -C /home/user/Cursor-Governance rev-parse HEAD` | equals the locked governance SHA | true |
| CP-02 | `multi_repo_detection` | list children of `/home/user` carrying a `.git` entry | exactly the 4 in-scope repositories | true |
| CP-03 | `residue_reproduced` | `find /home/user/*/.claude -xtype l` | non-empty at start — the defect must exist before it can be cleared | true |
| CP-04 | `failing_baseline_reproduced` | `cd /home/user/l9-cognitive-runtime && .venv/bin/python -m pytest tests/test_gar_deployment_closure.py -q` | 2 failed — the acceptance signal exists | true |
| CP-05 | `lock_drift_reproduced` | `cd /home/user/l9-cognitive-runtime && uv sync --locked --extra dev --dry-run` | reports package deltas | true |
| CP-06 | `filesystem_write` | write probe under `ops/scripts/lib/` and the adapter hooks directory | both writable | true |
| CP-07 | `quality_gate_available` | `make -C /home/user/Cursor-Governance pr-check` resolves | target found | false |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `ops/scripts/lib/**`, `ops/scripts/claude_bootstrap_receipt.py`, `ops/scripts/claude_projection.py`, `ops/scripts/reconcile_claude_l9_skills.py`, `ops/scripts/reconcile_claude_commands.py`, `environment/agents/adapters/claude-code/hooks/**`, `rules/62-github-openclaw-authority.mdc`, `tests/**`, `/home/user/l9-cognitive-runtime/{CLAUDE.md,AGENTS.md}`
- **write_deny:** `environment/generated/llm-rules/**` (generated), `CANONICAL_LAW.md`, `ops/autonomy/merge_gate.py`, `ops/scripts/open_pr_after_gate.sh`, `ops/scripts/pr_overlap_check.py`, `ops/autonomy/verification_bypass_gate.py`, every other repository's tracked tree
- **delete_allow:** untracked, gitignored, projection-managed symlinks under `/home/user/*/.claude/{skills,commands}` — only when the entry is a symlink whose target lies under the governance SSOT **and** `git check-ignore` confirms it is ignored

### Commands

- **allow:** `git` read and scoped commit on the declared branch, `uv sync`, targeted `pytest <path>`, `pre-commit`, `make pr-check`, `make claude-env`, `find`, `bash` on the adapter hooks under test
- **deny:** force-push, hard-reset, `git revert` on shared history, broad `git add`, `pytest .` / bare `pytest` / `make test` / `make pr-full`, `pre-commit install`, `--no-verify` in any spelling, `make push`, MCP `create_pull_request` / `push_files`, installs outside the declared toolchain

### Network

| Field | Value |
|-------|-------|
| mode | `read_only` |
| allowed_services | pypi.org and github.com, for lock-pinned dependency and pre-commit hook fetches only; nothing is written before the sanctioned publish |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

This surface is `model-controlled` and holds no credential. T7 documents that boundary; it never provisions one.

### Autonomous merge

`autonomous_merge:` `false` always in packet + PE `COMPATIBILITY.yaml` (forbidden).
**Merge for this plan** only after PE verify/handoff path + [@autonomy](commands/autonomy.md) join on this L4 plan/PE stack, green+mergeable (see Execute section). Outside that stack → denied.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005).

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert commit | false |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `manual_only` | re-run the projection to recreate mirrors | false |
| T3 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert commit; stale stamps are inert | false |
| T4 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert commit | false |
| T5 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | revert commit | false |
| T6 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | revert commit; a per-session marker caps repair at one attempt | false |
| T7 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |
| T8 | `filesystem_mutation` | `safe_to_repeat` | `none` | delete the added files | false |
| T9 | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | revert commit; the gate falls back to reading the environment variable | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | bootstrap workspace resolution | `chassis` | `SESSION_START_SPEC.md` | a second root detector; changing the 6-root cap before U3 resolves |
| T2 | projection / adapters | `control_plane` | `claude_projection.py` receipt schema | removing any tracked path; touching generated rule projections |
| T3 | dependency provisioning | `ops` | `session_deps_cloud.sh` fail-open contract | making SessionStart blocking or non-zero |
| T4 | dependency provisioning | `assurance` | same | stamping an unproven install |
| T5 | readiness receipts | `assurance` | `l9.claude-bootstrap.v1` | widening the schema; adding a second state owner |
| T6 | startup sequence | `chassis` | `SESSION_START_SPEC.md` | unbounded repair loops; blocking the session |
| T7 | capability documentation | `policy` | `rules/62-github-openclaw-authority.mdc` | asserting a credential this surface cannot hold |
| T8 | repository law | `docs` | consumer root-file protection | overwriting a protected root file without its marker |
| T9 | publish authorization | `policy` | `ops/autonomy/local_execution_gate.py` | widening publish authority; touching merge authority |

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
| code | `revert_commit` | one commit per TODO; revert in reverse-dependency order T4, T3, T2, T1 |
| data | `none` | no datastore is written |
| external_state | `none` | the PR is the only external artifact, and it is created after all local work |
| local_state | `git_restore_scoped_paths` | the mirrors T2 removes are untracked, gitignored and regenerable by the projection |

### Irreversible operations

- none. Every mutation is a tracked commit or a regenerable machine-local artifact. T2 is the only removal and it removes only untracked, gitignored symlinks the projection recreates.

### Rollback verification

- `git revert <sha> && make claude-env` — readiness returns to its pre-change value.
- `bash environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh` re-runs cleanly and exits 0, proving the fail-open contract survived.
- `find /home/user/*/.claude -xtype l` after a revert returns the pre-change residue, proving the removal was regenerable rather than destructive.

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
| CP | agent | assurance | [] | baseline + preflight receipts (CP-01..CP-07) |
| T1 | agent | chassis | [CP] | `ops/scripts/lib/workspace_roots.py` + test |
| T2 | agent | control_plane | [T1] | per-repo mirror reconciliation + receipt fields |
| T3 | agent | ops | [T1] | per-repository deps provisioning + banner |
| T4 | agent | assurance | [T3] | applied-state proof gating the stamp |
| T5 | agent | assurance | [] | revision-bound receipt staleness |
| T6 | agent | chassis | [T5] | bounded installer re-run on stale receipt |
| T7 | agent | policy | [] | observed GitHub transport truth-table |
| T8 | agent | docs | [] | repository authority docs |
| T9 | agent | policy | [] | scoped expiring publish breakglass |
| V | agent | assurance | [T2,T4,T6,T7,T8,T9] | SP-01..SP-08 evidence |

**Critical path:** `CP` → `T1` → `T2` → `T3` → `T4` → `V`

**Forbidden edges:** T2 must not precede T1 (it would re-derive a second root detector). T6 must not precede T5 (repair without revision binding loops every session). T9 must not join the critical path — it touches the publish gate and lands last or not at all.

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |

|-------------|---------------|---------------|--------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `repository_state_evidence` | rev-parse compare | `git rev-parse HEAD` | locked SHA | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | dangling-link sweep | `find /home/user/*/.claude -xtype l` | empty output | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | full suite | `cd /home/user/l9-cognitive-runtime && .venv/bin/python -m pytest -q` | `184 passed` with no `failed` | `not_run` |
| EV-SP-04 | SP-04 | `structural_evidence` | lock-vs-environment | `uv sync --locked --extra dev --dry-run` per uv repo | no `+`/`-` package line | `not_run` |
| EV-SP-05 | SP-05 | `proof_receipt` | banner + stamp inspection | run the deps helper; read `~/.l9/claude/deps-*.log` | one line per repository; no stamp on failed proof | `not_run` |
| EV-SP-06 | SP-06 | `proof_receipt` | negative test | stamp a prior `governance_revision`, then `claude_bootstrap_receipt.py --read` | UNKNOWN, reason `revision superseded` | `not_run` |
| EV-SP-07 | SP-07 | `quality_gate_evidence` | readiness | `make claude-env` | exit 0 | `not_run` |
| EV-SP-08 | SP-08 | `quality_gate_evidence` | pr-check | `make pr-check` | PASS | `not_run` |

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

