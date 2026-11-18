---
name: Claude Code bootstrap friction fixes (EIE C1 governance handoff)
overview: "Remove the five Claude Code bootstrap frictions recorded in the EIE PR #259 governance handoff: worktree setup writing into consumer AGENTS.md/CLAUDE.md, the L4 gate refusing WS='$PWD' and make -n pr, session-deps overlaying requirements files onto venvs it does not own, the PR composer leaving human sections unfilled with no input for them, and conformance receipts pinned to an old .github rev..."
todos:
  - id: T1
    content: "Regenerate the coding-agent-execution projection bundle at .github@3dcdeaa with the compiler at its protected-main HEAD e07a143, then replay-check and verify"
    status: completed
    phase: execute
    depends_on: []
  - id: T2
    content: "Run ensure_workspace_wired.sh links-only from worktree_add_wired.sh so worktree creation never reaches install_ide_profile/agentdocs; add a regression test on a fixture consumer repo with tracked AGENTS.md and CLAUDE.md"
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Exempt GNU make dry-run/question flags (-n, --just-print, --dry-run, --recon, -q, --question, short groups containing n or q) from make pr publication classification using the same scan as make_goals; add a test that the pr dependency chain has no + or $(MAKE) recipe lines"
    status: pending
    phase: execute
    depends_on: []
  - id: T4
    content: "Resolve WS=$PWD / ${PWD} / $(pwd) / `pwd` (whole dequoted value only) to the shell cwd (preceding literal cd, else hook payload cwd) in effective_root and extract_named_roots; skip make -C as a named root whenever WS= is present; deny make pr with an unresolvable WS= with a message naming the literal-path fix"
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "session_deps_cloud.sh writes .venv/.l9-pip-owner when it creates a venv; an existing .venv with neither that marker nor .l9-pip-applied is reported owner-managed with no install and no stamp"
    status: pending
    phase: execute
    depends_on: []
  - id: T6
    content: "Add --intent-file (l9.pr_intent.v1: title, problem, reviewer_focus, head) to compose_pr_body.py for title, Problem and Reviewer focus; open_pr_after_gate.sh passes .l9/pr/pr-intent.json when present and on an already-open PR PATCHes title only when intent.title exists; document in rule 48 and regenerate projections"
    status: pending
    phase: execute
    depends_on: []
kernel_pass:
  bound_path: docs/plans/bootstrap_friction_fixes_5c1e9a07.plan.md
  improve:
    ran_at: "2026-10-31T01:10:00+00:00"
    deltas:
      - "filled every template parameter slot (metadata, baseline, preflight probes, envelope, side effects, architecture impact, rollback, DAG, evidence matrix, convergence) from verified session evidence"
      - "replaced the generic SP proof 'observe .pre-commit-config.yaml catalog' with per-property red-green test commands and receipt checks"
      - "recorded the measured finding that the old bundle was already CURRENT at .github main, so T1 changes pins only"
  recursive_alignment:
    ran_at: "2026-10-31T01:12:00+00:00"
    deltas:
      - "aligned frontmatter T1 status to completed with E-06 passed in the evidence matrix and PLAN_DOCUMENT V2 passed"
      - "aligned envelope write_deny with gmp_handoff.must_not_modify plus the SSOT clone and consumer repos"
  validate_repair:
    ran_at: "2026-10-31T01:14:00+00:00"
    deltas:
      - "repaired PLAN_DOCUMENT schema violations (convergence.execute_via removed; T1 operation Regenerate -> Replace) and re-validated PASS"
      - "moved plan artifacts out of the SSOT clone (reached through the .cursor/plans symlink) into the worktree docs/plans"
      - "verified no unfilled <parameter> slot remains outside template guidance lines; section receipt regenerated and PASS"
      - "reworded the blast-radius line that tripped G_PLAN_EITHER_OR (PLAN_DOCUMENT and projection kept in sync)"
    body_sha256: "f3e6e7f6cd88418d0ef8cb73d914fc1ef4016207ec1c8a864e51c55ff97de9ed"
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Claude Code bootstrap friction fixes (EIE C1 governance handoff)

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `claude-code-bootstrap-friction-fixes-eie-c1-governance-handoff_dd845e19.plan.md`

## Objective (from PLAN_DOCUMENT)

Remove the five Claude Code bootstrap frictions recorded in the EIE PR #259 governance handoff: worktree setup writing into consumer AGENTS.md/CLAUDE.md, the L4 gate refusing WS="$PWD" and make -n pr, session-deps overlaying requirements files onto venvs it does not own, the PR composer leaving human sections unfilled with no input for them, and conformance receipts pinned to an old .github revision.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | worktree_add_wired.sh on a consumer repo with tracked AGENTS.md/CLAUDE.md leaves git status --porcelain empty in the new worktree (new test red on 774acf2, green after) | quality_gate | see Success properties proof column | true |
| SP-02 | local_execution_gate does not classify make -n/--dry-run/--just-print/--recon/-q/--question pr as publication; MAKEFLAGS=n stays classified (tests red then green) | quality_gate | see Success properties proof column | true |
| SP-03 | make -C <dir> pr WS="$PWD" resolves the receipt workspace to the hook cwd (or a preceding literal cd); any other unresolvable WS= on make pr is denied with a message naming the fix (tests red then green); test_make_ws_does_not_expand_env stays green | quality_gate | see Success properties proof column | true |
| SP-04 | session_deps_cloud.sh never installs into an existing .venv it did not create (no owner marker and no prior .l9-pip-applied); it reports that repo owner-managed without a stamp (test red then green) | quality_gate | see Success properties proof column | true |
| SP-05 | compose_pr_body.py accepts an agent-authored .l9/pr/pr-intent.json bound to HEAD that supplies title, Problem and Reviewer focus; a stale head is ignored with WARN; open_pr_after_gate.sh passes it and, on an already-open PR, replaces only the composer's own unresolved markers and PATCHes the title only when intent.title is present (tests red then green) | quality_gate | see Success properties proof column | true |
| SP-06 | generated/governance/coding_agent_execution is pinned to .github@3dcdeaae355b6de08562993f705084d7a3714bfd; produce_projection_bundle.py --check exits 0; coding_projection_status.py --expect-main 3dcdeaa reports CURRENT; verify_canonical_binding.py exits 0 BOUND | quality_gate | see Success properties proof column | true |
| SP-07 | all touched test modules pass and make pr gate passes | quality_gate | see Success properties proof column | true |

## Scope (from PLAN_DOCUMENT)

**In:** ops/scripts/worktree_add_wired.sh, ops/autonomy/local_execution_gate.py, ops/autonomy/command_parse.py, environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh, ops/scripts/compose_pr_body.py, ops/scripts/open_pr_after_gate.sh, generated/governance/coding_agent_execution/, rules/48-make-pr-remediation.mdc and its generated projections, tests for each of the above

**Out:**
- agentdocs.sh behaviour on sessionStart and make ide-profile (intended consumer formatter block stays)
- workspace_roots.py discovery semantics (shared with memory hydration)
- removal of already-installed stale packages from existing venvs
- a fail-closed PR_REQUIRE_INTENT switch
- architecture_intelligence and other projection bundles
- scheduled regeneration workflow for the coding-agent bundle (needs GH_TOKEN for the private compiler)
- consumer repository edits (EIE)

## Critical path (seed)

T3 → T4

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: the L4 gate runs on every Claude and Cursor shell command; a wrong classification can block all publication, and the opposite error lets a real publish through without a receipt
- Rollback: revert the single PR; each todo is an independent commit so any one can be reverted alone

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: plan validated; T1 executed during investigation, T2-T6 pending Build
- execute_via: cursor-build

---

## Template body (completed)

# PLAN: Claude Code bootstrap friction fixes (EIE C1 governance handoff)

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every `<parameter>` is an instance slot. Backtick tokens are the closed vocabulary for that field. Replace each parameter before status becomes `executable`. Leave no sample instance in a delivered plan.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **Rename to:** `<snake_case_name>_<8hex>.plan.md` before execute.
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
| plan_id | `plan.governance.bootstrap-friction-fixes.v1` |
| name | Claude Code bootstrap friction fixes (EIE C1 governance handoff) |
| overview | Five governance-side repairs from the EIE PR #259 governance handoff |
| schema_version | `1.0.0` |
| status | `executable` |
| is_project | false |
| owner | `claude-code` (agent/claude-code/bootstrap-friction-fixes) |
| created_at | `2026-10-31` |
| updated_at | `2026-10-31` |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `docs/plans/bootstrap_friction_fixes_5c1e9a07.json` (PLAN_DOCUMENT, validate_plan_document.py PASS) |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` — architecture settled: every fix lands inside the existing owner (worktree wiring, L4 gate, session-deps helper, PR composer, projection producer) |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; PR board empty so base is origin/main; no redesign |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-10-31` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | `/root/.l9/gov-worktrees/claude-code__bootstrap-friction-fixes` |
| ssot_clone | `/root/.cursor-governance` (untouched) |
| branch | `agent/claude-code/bootstrap-friction-fixes` |
| commit_sha | `774acf2c178284f90472be1a7fedd81a73a4ef34` |
| dirty | `false` at start; T1 regenerated files and plan artifacts are the only dirt |
| artifact_hashes | bundle.lock.json pinned `.github@7252e3b`, compiler `b9b4892` at baseline |
| allowed_local_dirt | `docs/plans/bootstrap_friction_fixes_5c1e9a07.*`, `generated/governance/coding_agent_execution/**` |
| overlap_policy | `explicitly_allow_listed_paths` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Remove five recorded bootstrap frictions so a Claude Code session can create a consumer worktree, dry-run and publish `make pr` with `WS="$PWD"`, resume without its venv being overlaid, open a PR with author prose, and claim projection conformance against current `.github`.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | worktree setup leaves a consumer's tracked AGENTS.md/CLAUDE.md untouched | `quality_gate` | `pytest tests/ops/scripts/test_worktree_add_wired_clean.py` red on 774acf2, green on branch | true |
| SP-02 | make dry-run/question flags are not publication | `quality_gate` | `pytest tests/ops/autonomy/test_publish_path_gate.py` new cases red then green | true |
| SP-03 | `WS="$PWD"` resolves to the shell cwd; other unresolvable WS= on make pr denies with a fix message | `quality_gate` | `pytest tests/ops/autonomy/test_effective_root.py tests/ops/autonomy/test_command_parse.py` new cases red then green; no-expand tests green | true |
| SP-04 | session-deps never installs into an unowned existing venv | `quality_gate` | `pytest tests/environment/adapters/test_session_deps_cloud.py` new case red then green | true |
| SP-05 | composer takes title, Problem, Reviewer focus from a HEAD-bound intent file | `quality_gate` | `pytest ops/scripts/tests/test_compose_pr_body.py tests/ops/scripts/test_pr_lifecycle.py` new cases red then green | true |
| SP-06 | coding-agent bundle pinned to `.github@3dcdeaa` and CURRENT | `proof_receipt` | producer `--check` exit 0; `coding_projection_status.py --expect-main 3dcdeaa` CURRENT; `verify_canonical_binding.py` BOUND | true |
| SP-07 | publication gate passes | `quality_gate` | `PR_REMEDIATE=0 make pr` PASS with PR URL | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.governance.bootstrap-friction-fixes.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.governance.bootstrap-friction-fixes.v1` |
| source_ref | `plan.governance.bootstrap-friction-fixes.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `774acf2c178284f90472be1a7fedd81a73a4ef34` |
| baseline_verified | `true` |
| drift_detected | `false` |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| PR-1 | isolated worktree | `agent_worktree_start.sh --agent-id claude-code --task-id bootstrap-friction-fixes` | RESULT: PASS | true |
| PR-2 | governance venv | `.venv/bin/python -c 'import yaml, pytest'` | exit 0 | true |
| PR-3 | `.github` read | `git clone https://github.com/Quantum-L9/.github` into scratchpad at 3dcdeaa | HEAD 3dcdeaa | true |
| PR-4 | private compiler | `add_repo Quantum-L9/l9-semantic-compiler-engine` + clone at e07a143 + pip install | `l9-semantic-compiler` on PATH | true |
| PR-5 | open PR board | `gh api repos/Quantum-L9/Cursor-Governance/pulls?state=open` | empty | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** paths in `gmp_handoff.may_modify` of the PLAN_DOCUMENT, plus `docs/plans/bootstrap_friction_fixes_5c1e9a07.*`
- **write_deny:** `AGENTS.md`, `CANONICAL_LAW.md`, `Makefile`, `ops/scripts/adapters/agentdocs.sh`, `ops/scripts/lib/workspace_roots.py`, `/root/.cursor-governance/**`, consumer repositories
- **delete_allow:** none

### Commands

- **allow:** pytest, ruff, the projection producer and verifiers, `git add -- <paths>`, `git commit`, `l4_local.py begin|authorize-release`, `PR_REMEDIATE=0 make pr`
- **deny:** raw `git push`, `gh pr create`, `make push`, merge of any kind, force-push, `git add -A`

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | github.com (Quantum-L9/.github read, compiler read, Cursor-Governance via make pr) |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false`. This plan never merges; the PR waits for human review.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_to_repeat` | `bounded_retry` | revert the bundle files | false |
| T2 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |
| T3 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |
| T4 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |
| T5 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |
| T6 | `filesystem_mutation` | `safe_to_repeat` | `none` | revert commit | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | projection bundle | `assurance` | ADR-021 / docs/PROJECTION_PUBLICATION.md | hand-editing generated receipts |
| T2 | worktree wiring | `ops` | rules/49 shared worktree isolation | changing agentdocs.sh |
| T3 | L4 publish gate | `policy` | rules/88 L4 local autonomy | weakening receipt checks |
| T4 | L4 publish gate | `policy` | rules/88, rules/54 | expanding non-PWD variables |
| T5 | session deps | `runtime` | session_deps_cloud.sh header contract | changing workspace_roots.py |
| T6 | publication | `ops` | rules/48 make pr | new publish path, fail-closed switch |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.governance.bootstrap-friction-fixes.v1` |
| source_execution_ref | `plan.governance.bootstrap-friction-fixes.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | any L4 gate regression observed after merge; any consumer reporting a missing venv |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | one commit per todo |
| data | `none` | no data |
| external_state | `none` | PR only |
| local_state | `git_restore_scoped_paths` | worktree only |

### Irreversible operations

- none (PLAN-SCHEMA-010)

### Rollback verification

- after revert, `pytest tests/ops/autonomy -q` green on the reverted tree

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` |
| uncertainty | `low` |
| blast_radius | `high` |
| architectural_boundaries_crossed | none |
| external_systems_touched | GitHub (read .github, read compiler, PR via make pr) |
| migration_required | false |
| unknown_dependency_count | 0 |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated: nothing is retired, migrated or replaced.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated: the only external write is the PR opened by `make pr`, which carries its own gates.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated: no retirement.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.governance.bootstrap-friction-fixes.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T1 | claude-code | `assurance` | `[]` | regenerated bundle |
| T2 | claude-code | `ops` | `[]` | links-only worktree wiring + test |
| T3 | claude-code | `policy` | `[]` | dry-run exemption + tests |
| T4 | claude-code | `policy` | `[T3]` | PWD resolution + tests |
| T5 | claude-code | `runtime` | `[]` | owner marker + test |
| T6 | claude-code | `ops` | `[]` | intent file + tests + rule 48 |

**Critical path:** T3 → T4

**Forbidden edges:** none of T1, T2, T5, T6 may depend on gate changes

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-01 | SP-01 | `quality_gate_evidence` | red-green | `pytest tests/ops/scripts/test_worktree_add_wired_clean.py` | pass on branch, fail on base | `not_run` |
| E-02 | SP-02 | `quality_gate_evidence` | red-green | `pytest tests/ops/autonomy/test_publish_path_gate.py` | pass | `not_run` |
| E-03 | SP-03 | `quality_gate_evidence` | red-green | `pytest tests/ops/autonomy/test_effective_root.py tests/ops/autonomy/test_command_parse.py` | pass | `not_run` |
| E-04 | SP-04 | `quality_gate_evidence` | red-green | `pytest tests/environment/adapters/test_session_deps_cloud.py` | pass | `not_run` |
| E-05 | SP-05 | `quality_gate_evidence` | red-green | `pytest ops/scripts/tests/test_compose_pr_body.py tests/ops/scripts/test_pr_lifecycle.py` | pass | `not_run` |
| E-06 | SP-06 | `structural_evidence` | replay + verify | producer `--check`; status `--expect-main`; `verify_canonical_binding.py` | exit 0, CURRENT, BOUND | `passed` |
| E-07 | SP-07 | `quality_gate_evidence` | gate | `PR_REMEDIATE=0 make pr` | PASS + PR URL | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- `make -n pr` would push if the pr chain had a `+` or `$(MAKE)` recipe line; a test pins their absence
- `$PWD` from the payload cwd could differ from the shell cwd after a `cd`; a preceding literal `cd` wins
- the bundle was BOUND/CURRENT before regeneration; regeneration changes pins only, projections byte-identical

### Assumption failure conditions

- the hook payload carries no `cwd`: PWD forms then stay unresolved and make pr denies with the fix message (PLAN-SCHEMA-013)
- a venv built by an older helper lacks `.l9-pip-owner`: adopted when `.l9-pip-applied` exists

### Blast radius notes

- the L4 gate runs for every shell command on Claude and Cursor; T3/T4 run the full `tests/ops/autonomy` suite

### Rollback constraints

- none beyond revert; no state outside git

## Out of scope

- agentdocs on sessionStart and `make ide-profile`
- `workspace_roots.py` discovery semantics
- removing stale packages from existing venvs
- a fail-closed `PR_REQUIRE_INTENT` switch
- other projection bundles; a scheduled regeneration workflow
- consumer repository edits
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
| P2 | scheduled regeneration + STALE in `--fail-on` for the coding-agent bundle | nothing re-cuts it when `.github` moves; needs GH_TOKEN for the private compiler |
| P3 | `PR_REQUIRE_INTENT=1` fail-closed switch | needs owner decision on default |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.governance.bootstrap-friction-fixes.v1` |
| source_ref | `plan.governance.bootstrap-friction-fixes.v1` |
| current_state | `execution_ready` |
| implementation_ready | `true` |

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

- **required_evidence_refs:** E-01 through E-07
- **observed_evidence_refs:** E-06
- **missing_evidence:** E-01, E-02, E-03, E-04, E-05, E-07 (Build)

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U-0 | none open | n/a |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | Build T2–T6, then E-07 |
| minimum_safe_next_action | Build on this worktree (PR board empty), then `PR_REMEDIATE=0 make pr` and display the PR URL |
| execute_via | Cursor Build; display PR URL |
| broader_work_requires_separate_contract | `true` |
