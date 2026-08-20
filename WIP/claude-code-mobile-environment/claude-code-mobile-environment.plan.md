---
name: Claude Code Mobile Environment — unified readiness master plan
overview: "Consolidate three concurrent efforts on the same concern into one master plan: this session's forensic audit of the cloud/mobile surface from the Python governance repo, the sibling plan at WIP/claude-code-mobile-environment written from the TypeScript node fleet, and the unmerged code on branch claude/startup-audit-review-bmj21b. Restore full non-memory readiness for Claude Code Mobile, make t..."
todos:
  - id: w0-01-integrate-inflight-workspace-resolution
    content: "Replay branch claude/startup-audit-review-bmj21b onto current main as ONE resolve_workspace in web/setup.sh. Keep main's refuse-rather-than-guess posture, and adopt the branch's three genuine improvements: probe CLAUDE_PROJECT_DIR with git rev-parse --show-toplevel rather than testing for a .git directory so worktrees and subdirectories resolve, exclude the governance clone from candidate repos, and cd into the resolved workspace so later cwd-derived steps inherit it"
    status: pending
    phase: execute
    depends_on: []
  - id: w0-02-preserve-locked-interpreter
    content: "Preserve main's locked governance interpreter in every hook command while integrating the branch's settings.template.json changes. The branch predates that hardening and calls bare system python3, which would silently un-pin every hook"
    status: pending
    phase: execute
    depends_on: [w0-01-integrate-inflight-workspace-resolution]
  - id: w0-03-split-memory-lifecycle-out
    content: "Separate the branch's SessionEnd and Graphiti session-close work, including its check_session_lifecycle_parity validator, onto its own branch owned by the memory plane. It is coupled into the same commits as the workspace fix, so the integration must split it rather than carry it, and this plan must not land it"
    status: pending
    phase: execute
    depends_on: [w0-01-integrate-inflight-workspace-resolution]
  - id: w0-04-resolve-validator-conflict
    content: "Resolve the three-way conflict on validate_claude_env.py that PV-04 detected, coordinating the branch's additions with this plan's own validator amendment so the file is edited once rather than twice"
    status: pending
    phase: execute
    depends_on: [w0-03-split-memory-lifecycle-out]
  - id: w1-01-baseline-regression-guard
    content: "Add regression tests that pin the integrated behaviour: install.sh refuses a non-git workspace, resolve_workspace prefers the checkout over its parent, a multi-repo parent produces a named refusal rather than a silent parent wire, and exactly one resolve_workspace definition exists"
    status: pending
    phase: execute
    depends_on: [w0-01-integrate-inflight-workspace-resolution]
  - id: w1-02-vendor-only-fast-path
    content: "Add a --vendor-only flag to install.sh that runs the settings, skills, rules and MCP reconcilers while skipping the shared agent bootstrap, so a session-time reconcile costs the measured 0.16s rather than a full toolchain pass"
    status: pending
    phase: execute
    depends_on: [w1-01-baseline-regression-guard]
  - id: w1-03-sessionstart-reconcile
    content: "Wire a bounded adapter reconcile into the cloud branch of the SessionStart hook: run install.sh --check against the resolved project dir and, on drift, run install.sh --vendor-only, then re-read the receipt before projecting status. This is the plan's spine — it converts a permanent mis-wire into one that self-heals without an environment rebuild"
    status: pending
    phase: execute
    depends_on: [w1-02-vendor-only-fast-path, w0-02-preserve-locked-interpreter]
  - id: w1-04-receipt-truthfulness
    content: "Make the bootstrap receipt self-describing: record the real surface execution mode instead of the hardcoded local literal, stamp a reconciled_at timestamp, and add a workspace_verified boolean the SessionStart projection can trust"
    status: pending
    phase: execute
    depends_on: [w1-02-vendor-only-fast-path]
  - id: w1-05-multi-repo-workspace-contract
    content: "Define and implement the multi-repo rooting contract raised by the sibling plan's U2: when a session is rooted at a parent holding several sibling repositories, wire each candidate repository rather than refusing wholesale, or refuse with a named list and a one-command remedy. Today main refuses and the node fleet gets nothing wired"
    status: pending
    phase: execute
    depends_on: [w1-03-sessionstart-reconcile]
  - id: w2-01-skill-registry-ssot-decision
    content: "Record the SSOT decision for the four account-registry-only skills — l9-ci-gap-auditor, l9-ci-repair, l9-github-ci and l9-pr-analysis — which exist in the Anthropic account registry with no counterpart under skills/. Either commit them into the repository with registry coverage, or document the account registry as their owner and stop treating skills/ as complete. Any sync change is additive only: extend the list, never remove an entry, and capture the synced manifest before and after so a reconciliation cannot silently shrink another surface's skill availability"
    status: pending
    phase: execute
    depends_on: [w1-03-sessionstart-reconcile]
  - id: w2-02-claude-slash-commands
    content: "Reconcile the governance commands library into the project Claude commands directory during vendor wiring, so the 54 command files resolve as native slash commands on this surface"
    status: pending
    phase: execute
    depends_on: [w1-03-sessionstart-reconcile]
  - id: w3-01-surface-aware-wiring-check
    content: "Teach check_governance_wiring.sh the surface it runs on, so Cursor IDE host checks classify as not-applicable on claude-code instead of emitting a red FAIL that masks real signal"
    status: pending
    phase: execute
    depends_on: [w1-01-baseline-regression-guard]
  - id: w3-02-shellcheck-toolchain
    content: "Add shellcheck to the canonical checker toolchain acquisition beside gitleaks, with the same pinned-version and report-on-absence discipline"
    status: pending
    phase: execute
    depends_on: [w1-01-baseline-regression-guard]
  - id: w3-03-gh-sentinel-contract
    content: "Reverse the predecessor campaign's GH_TOKEN removal narrowly, preserving its security intent. The probe proved the value is not a credential — any non-empty string works because the proxy substitutes the real one — so restore the sentinel, change the prohibited-value branch from unset to replace-with-sentinel, and narrow the validator ban to credential-shaped values while allowing the exact literal"
    status: pending
    phase: execute
    depends_on: [w0-04-resolve-validator-conflict]
  - id: w3-04-durable-env-reaches-shells
    content: "Make the durable cloud session env effective for non-interactive tool shells by exporting BASH_ENV, or retire the mechanism and rely on the account variables field; the profile-sourcing path never applies to the agent Bash tool"
    status: pending
    phase: execute
    depends_on: [w3-03-gh-sentinel-contract]
  - id: w3-05-rest-merge-path
    content: "Replace the GraphQL-dependent gh pr merge step in the PR remediation path with the REST or platform GitHub MCP merge call, and align merge_gate.py and the adapter deny-list so the sanctioned merge route stays singular"
    status: pending
    phase: execute
    depends_on: [w1-03-sessionstart-reconcile]
  - id: w3-06-context7-degraded-posture
    content: "Give rule 22 a defined behaviour when no Context7 transport is reachable: record the honest degraded posture with an explicit removal trigger, require the official-docs fetch fallback the rule already names, and require the blocker to be stated in the response rather than leaving a mandatory gate silently unsatisfiable"
    status: pending
    phase: execute
    depends_on: [w1-03-sessionstart-reconcile]
  - id: w3-07-narrow-pretool-stack-gate
    content: "Fix the pretool stack-proof gate on two counts. Scope: its documented purpose is program-execution planning, but its filename and body patterns fire on any edit or write that merely mentions a dependency manifest, a container file, an install verb or a credential-shaped word, so it denies ordinary prose and plan documents. Narrow it to campaign seed files. Degraded path: its only two satisfaction routes are a live documentation-service call and a campaign activation receipt, both unreachable when the capability broker is down, which makes it unsatisfiable rather than fail-soft on this surface. Accept the rule-22 official-docs fallback as proof, recorded as a receipt the gate can read"
    status: pending
    phase: execute
    depends_on: [w3-06-context7-degraded-posture]
  - id: w3-08-unpushed-commit-hook-surface-aware
    content: "Make the stop-hook unpushed-commit check surface-aware. It asks for a direct push after every local commit, but on this surface the L4 gate denies remote until a release receipt exists and the Makefile publish path is the only sanctioned route, so the instruction is unactionable and fires repeatedly. Have it read the release-gate state and name the sanctioned next step instead of a bare push"
    status: pending
    phase: execute
    depends_on: []
  - id: w4-01-link-local-packages-script
    content: "Write ops/scripts/link_local_l9_packages.sh in this repository: for each scoped dependency declared by a caller repo, locate the sibling source checkout and install it from that local source so a model-controlled session gains validation capability without a PAT. Read the mapping from a declared ops/scripts/l9_package_sources.yaml rather than rediscovering it by find each session. Four invariants are binding, two of them established against the vendor's official documentation rather than assumed. First, pass --no-save explicitly: the package manager saves to dependencies by default, so a folder specifier would otherwise write a local-path entry into the caller's manifest and break the byte-identical guarantee below. Second, build the sibling and provision its own runtime dependencies before linking: a folder outside the project root is only symlinked and its dependencies are NOT installed, so an unbuilt sibling yields a link that fails at import time. Third, write only into the ignored dependency directory and leave the caller's manifest and lockfile byte-identical to main. Fourth, print each resolved local version against the declared range and warn on mismatch, so a drifted local source cannot masquerade as CI truth."
    status: pending
    phase: execute
    depends_on: [w1-05-multi-repo-workspace-contract]
  - id: w4-02-node-repo-session-contract
    content: "Adopt the governed session contract in SEO-Bot, Website-Bot and LLM-Router: commit a .claude/settings.json that registers the SessionStart hook, and rewrite the hook's no-token branch to call the governance link script instead of advising a PAT remediation that surface_trust guarantees will fail. Preserve the soft-fail contract — every step guarded, always exit 0 — and cap the link step with a timeout so a slow resolve cannot stall session start. Delete the AWS-resolution advice from both the hook and ensure-npm-auth.sh rather than maintaining a path policy will always deny"
    status: pending
    phase: execute
    depends_on: [w4-01-link-local-packages-script]
  - id: w4-03-node-gate-hygiene
    content: "Clear the node-fleet gate defects the sibling plan found: point the aggregate verify script at a non-interactive runner and include the real typecheck gate, correct the AGENTS.md sections that contradict the CI workflow on lockfile handling, and decide whether the linter debt on main is cleared or recorded so the pre-PR gate can go green. Two guardrails are binding: never silence rules wholesale to force green — if the findings are real, land them as their own commit with no behavioural edits and prove typecheck and tests green on both sides of it — and never mask a real failure to make a command terminate"
    status: pending
    phase: execute
    depends_on: [w4-02-node-repo-session-contract]
  - id: w5-01-broker-url-operator
    content: "Append the capability broker URL to the account Environment variables field as a single line. Do not re-paste the example wholesale until the sentinel work lands, because the live field still carries the GH_TOKEN sentinel while the example no longer does"
    status: pending
    phase: execute
    depends_on: [w3-03-gh-sentinel-contract]
  - id: w5-02-broker-deployment
    content: "Deploy the L9 capability broker behind the hostname the manifest already declares and bind its Infisical workload identity. The facade code is complete and the predecessor campaign deferred deployment deliberately, so this is deployment and identity binding with no application code to write"
    status: pending
    phase: execute
    depends_on: [w5-01-broker-url-operator]
isProject: false
---

# PLAN: Claude Code Mobile Environment — unified readiness master plan

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).
> **Suggested filename:** `claude-code-mobile-environment-unified-readiness-master-plan_9763e657.plan.md`

## Objective (from PLAN_DOCUMENT)

Consolidate three concurrent efforts on the same concern into one master plan: this session's forensic audit of the cloud/mobile surface from the Python governance repo, the sibling plan at WIP/claude-code-mobile-environment written from the TypeScript node fleet, and the unmerged code on branch claude/startup-audit-review-bmj21b. Restore full non-memory readiness for Claude Code Mobile, make the wiring self-healing, land the in-flight code without its three merge regressions, and give the TypeScript consumer repos the same governed session contract. Memory is fenced out of scope throughout.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | SC-01: branch claude/startup-audit-review-bmj21b is integrated onto current main with exactly ONE resolve_workspace definition in web/setup.sh, verified by grep -c returning 1 | quality_gate | observe during PE verify / make pr-check | true |
| SP-02 | SC-02: the integrated settings.template.json still invokes hooks through the locked governance interpreter, never bare system python3, verified by grep for .venv/bin/python3 in every hook command | quality_gate | observe during PE verify / make pr-check | true |
| SP-03 | SC-03: a fresh session's receipt records workspace equal to the project dir, with no workspace-mismatch WARN in the SessionStart projection | quality_gate | observe during PE verify / make pr-check | true |
| SP-04 | SC-04: Skill tool invocation of l9-aws-secrets and l9-plan returns the skill contract instead of Unknown skill, in the session after the reconcile | quality_gate | observe during PE verify / make pr-check | true |
| SP-05 | SC-05: find $CLAUDE_PROJECT_DIR/.claude/skills -maxdepth 2 -name SKILL.md returns 51 | quality_gate | observe during PE verify / make pr-check | true |
| SP-06 | SC-06: a session rooted at a multi-repo parent either wires the correct repo or reports a named refusal, and never silently wires the parent | quality_gate | observe during PE verify / make pr-check | true |
| SP-07 | SC-07: the four account-only skills have a recorded SSOT decision and, if repo-owned, exist under skills/ with registry coverage | quality_gate | observe during PE verify / make pr-check | true |
| SP-08 | SC-08: bash ops/scripts/check_governance_wiring.sh exits 0 on a claude-code surface without requiring Cursor IDE artifacts | quality_gate | observe during PE verify / make pr-check | true |
| SP-09 | SC-09: command -v shellcheck resolves after the shared bootstrap runs | quality_gate | observe during PE verify / make pr-check | true |
| SP-10 | SC-10: gh api succeeds from both a login shell and a non-interactive tool shell | quality_gate | observe during PE verify / make pr-check | true |
| SP-11 | SC-11: a model-controlled session in a TypeScript node repo runs that repo's blocking gates with no PAT and no hand-written stubs | quality_gate | observe during PE verify / make pr-check | true |
| SP-12 | SC-12: npm run verify:all completes non-interactively rather than hanging in watch mode | quality_gate | observe during PE verify / make pr-check | true |
| SP-13 | SC-13: make pr-check exits 0 on a clean checkout in every participating repo | quality_gate | observe during PE verify / make pr-check | true |
| SP-14 | SC-14: make pr-check PASSes on the changed files in this repository | quality_gate | observe during PE verify / make pr-check | true |
| SP-15 | SC-15: capability plane reports ENABLED for sonar.read_issues and semgrep.appsec_scan (gated on the broker milestone and excluded from the pr-check gate) | quality_gate | observe during PE verify / make pr-check | true |

## Scope (from PLAN_DOCUMENT)

**In:** Integration of branch claude/startup-audit-review-bmj21b onto current main, environment/agents/adapters/claude-code/ adapter tree: install.sh, hooks, settings template, web setup scripts, validator, ops/scripts/bootstrap_agent_environment.sh and check_governance_wiring.sh, Governance skill and slash-command delivery to the project .claude tree, SSOT decision for the four account-registry-only skills, ops/scripts/link_local_l9_packages.sh as the shared cross-repo local-link entrypoint, Coordination of the TypeScript node-fleet items owned by SEO-Bot, Website-Bot and LLM-Router, Operator-side account Environment variables field, L9 capability broker deployment

**Out:**
- Memory plane in every form: Graphiti hydrate and PICKUP, memory_gate.py, memory_prefetch.py, memory_writeback.py, graphiti_bridge.py, the memory-enforcement contract and schema, and rules 03/87/97/98
- The SessionEnd and Graphiti session-close half of branch claude/startup-audit-review-bmj21b, including its check_session_lifecycle_parity validator, which belongs to the memory owner
- The validate_claude_env.py memory-enforcement schema failure recorded as finding I14
- Protected core per rule 90: docker-compose.yml, Dockerfile, .env, infra/, deploy/, kubernetes/, helm/
- Weakening surface_trust, resolve_secret or the authed_npm PAT policy in any way
- Publishing or re-versioning any @quantum-l9 package
- Product code in any node repo, including build-intelligence
- CI workflow definitions and branch protection
- Cursor IDE host wiring under the home cursor directory
- Any weakening of tests, scanners or gate thresholds to obtain a green result

## Critical path (seed)

w0-01-integrate-inflight-workspace-resolution → w1-01-baseline-regression-guard → w1-02-vendor-only-fast-path → w1-03-sessionstart-reconcile → w1-05-multi-repo-workspace-contract → w4-01-link-local-packages-script

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: This plan now spans four repositories and the shared adapter installer that every Claude surface reaches — CLI, Desktop, Web and Mobile — plus the shared agent bootstrap that Codex, Gemini, Manus and the generic adapter also call. A defect in the workspace resolver or the SessionStart reconcile degrades or blocks session startup on all of them, and the resolver is now the merge point of two independent implementations, which raises the chance of a subtle regression above either one alone. The SessionStart contract is fail-open, so the dominant failure mode is a slower or noisier startup, but a hook exceeding its timeout loses the entire governance context blob including the autonomy profile. The node-fleet items touch three repositories not attached to this session and cannot be validated here. The GH_TOKEN work touches credential-adjacent code where a mistake either breaks gh outright or dilutes the prohibition on real tokens. Memory paths are fenced out and, for the in-flight branch, actively split away.
- Rollback: Each workstream lands as its own branch and PR so W0 through W5 revert independently; the master plan is a coordination artifact, not a single commit. W0 is the riskiest and is reverted by dropping the integration branch entirely, which returns main to its current resolver with no loss, since the branch remains intact upstream. The SessionStart reconcile ships behind an environment kill switch so a bad reconcile is disabled without a code change or redeploy, and the hook's fail-open contract means a disabled reconcile returns the session to today's behaviour. The vendor-only flag adds a new code path and changes no existing default, so reverting it is a deletion. The GH_TOKEN and durable-env changes revert by restoring the prior unset list, returning to the currently observed working state. Node-fleet changes are per-repository commits reverted in their own repositories. Broker deployment rolls back by removing the account variable, returning the capability plane to its present honest degraded posture.

## Convergence (seed)

- status: partial
- next_skill: l9-plan-audit
- stop_reason: Three concurrent efforts are consolidated into one master plan with six workstreams and one dependency order. Milestones M0 through M3 are executable against verified ground truth in this repository. M4 depends on three repositories not attached to this session and carries explicit blockers. M5 stays blocked on U-01. The most urgent open item is U-02: whether the in-flight branch is still actively worked decides whether W0 is a replay this plan performs or a rebase handed to its author, and getting that wrong either duplicates the work a third time or destroys another agent's tree.
- execute_via: @environment/program-execution → @autonomy

---

## Template body (complete every required section before status=executable)

# PLAN: Claude Code Mobile Environment — unified readiness master plan

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

