---
name: IdeaOS 12 Reconciliation
overview: "Merge three competing lifecycle visions (realization depth from PR #4, execution assurance from PR #6, source resolution from PR #7) into unified IdeaOS 12.0, fix implementation gaps discovered in the audit, and consolidate 6 open PRs into one reconciliation PR."
todos:
  - id: T-01
    content: "Merge PR #3 (doctrine) to main - already green and unblocked"
    status: pending
  - id: T-02
    content: Create reconciliation branch feat/ideaos-12-unified from main
    status: pending
  - id: T-03
    content: "Define unified IDEA_LIFECYCLE.yaml v12.0.0 with all features: source_resolution, realization_modes on decide, execution_assurance, learning_gate as utility"
    status: pending
  - id: T-04
    content: Add execution_assurance step to engine.py route() ladder after has_authorizing_decision_packet
    status: pending
  - id: T-05
    content: "Update assurance.py to validate realization depth: block BUILD_TO_SCALE if architectural assurance not SATISFIED"
    status: pending
  - id: T-06
    content: "Cherry-pick PR #4 realization depth changes onto reconciliation branch"
    status: pending
  - id: T-07
    content: "Cherry-pick PR #7 source resolution and learning gate modules"
    status: pending
  - id: T-08
    content: Merge unified _OPERATIONS registry in runtime.py with all modes (HIGH RISK)
    status: pending
  - id: T-09
    content: "Cherry-pick PR #8 EIE provider and Gate SDK integration"
    status: pending
  - id: T-10
    content: Run uv lock to update lockfile with Gate_SDK dependency
    status: pending
  - id: T-11
    content: "Cherry-pick PR #5 corpus files onto reconciliation branch"
    status: pending
  - id: T-12
    content: "Fix SonarCloud S1244 in corpus validators: replace == 0.0 with math.isclose"
    status: pending
  - id: T-13
    content: Fix Ruff E306/E701 issues and docstring formatting
    status: pending
  - id: T-14
    content: Update README.md to reflect IdeaOS 12.0 unified lifecycle
    status: pending
  - id: T-15
    content: Update VERSION to 12.0.0 and sync pyproject.toml/version.py
    status: pending
  - id: T-16
    content: Run make verify and fix any remaining failures
    status: pending
  - id: T-17
    content: "Open reconciliation PR targeting main, close PRs #4-#8 as superseded"
    status: pending
isProject: false
kernel_pass:
  bound_path: ideaos_12_reconciliation_5a8034b7.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-09-13T15:31:10Z
    deltas:
      - ff_shelf corpus pass
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-09-13T15:31:11Z
    deltas:
      - ff_shelf corpus pass
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-09-13T15:31:12Z
    body_sha256: "9f54336a7229016dfa8f3b75c720ff107e569f1d2d723653987c971588cb8899"
    deltas:
      - ff_shelf corpus pass
---

# PLAN: IdeaOS 12.0 Architecture Reconciliation

> **Schema:** `canonical.schema.plan_document.v1`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.

---

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`.
- The finish reply **must** display the opened PR URL as proof.

---

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.ideaos.reconciliation-12.v1` |
| name | IdeaOS 12.0 Reconciliation |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | `false` |
| owner | agent |
| created_at | `2026-09-13` |

---

## Architect Framing

| Field | Value |
|-------|-------|
| planning_ssot | `Quantum-L9/IdeaOS/.l9/architecture.yaml` |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; no redesign - reconcile existing features only |

---

## Immutable Baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-09-12T20:00:00Z` |
| repository | `Quantum-L9/IdeaOS` |
| workspace | `/tmp/IdeaOS-reconcile` |
| branch | `feat/ideaos-12-unified` |
| commit_sha | `80a84c759f22...` (main after PR #3 merge) |
| dirty | `false` |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

---

## Objective

### Mission

Reconcile three competing lifecycle visions in IdeaOS (realization depth, execution assurance, source resolution) into a single unified 12.0 architecture. Fix the missing `execution_assurance` route ladder step, merge conflicting `_OPERATIONS` registries, and consolidate 6 open PRs into one reconciliation PR. Preserve all existing schema contracts (IdeaExecutionPacket, ExpansionGateReceipt, decision node I/O).

### Success Properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Single lifecycle contract at v12.0.0 | `filesystem` | `grep -q 'version: 12.0.0' pipeline/IDEA_LIFECYCLE.yaml` | true |
| SP-02 | Route ladder includes execution_assurance | `structural` | `grep -q 'has_execution_assurance' src/ideaos/engine.py` | true |
| SP-03 | Runtime has 8+ operations registered | `runtime_behavior` | `python -c 'from ideaos.runtime import runtime_capabilities; assert len(runtime_capabilities()["operations"]) >= 8'` | true |
| SP-04 | All tests pass | `quality_gate` | `make verify` exits 0 | true |
| SP-05 | Pre-commit hooks pass | `quality_gate` | `pre-commit run --all-files --config .pre-commit-config.yaml` | true |
| SP-06 | Reconciliation PR opened | `network_observation` | PR URL displayed | true |

---

## Capability Preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.ideaos.reconciliation-12.v1` |
| blocking | `true` |

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| CP-01 | `gh_cli_available` | `gh --version` | version string returned | true |
| CP-02 | `repo_cloneable` | `gh repo clone Quantum-L9/IdeaOS /tmp/IdeaOS-reconcile` | exit 0 | true |
| CP-03 | `pr_3_mergeable` | `gh pr view 3 --repo Quantum-L9/IdeaOS --json mergeable` | `mergeable: true` | true |
| CP-04 | `uv_available` | `uv --version` | version string returned | true |

---

## Execution Envelope

### Filesystem

**write_allow:**
- `pipeline/IDEA_LIFECYCLE.yaml`
- `src/ideaos/**`
- `tests/**`
- `Ideas/**`
- `README.md`, `CHANGELOG.md`, `VERSION`
- `pyproject.toml`, `uv.lock`, `src/ideaos/version.py`
- `Dockerfile`, `.l9/sdk-compatibility.yaml`

**write_deny:**
- `.github/workflows/**`
- `AGENTS.md`
- `.l9/architecture.yaml`
- Any secrets or credentials

### Commands

**allow:** `gh pr create`, `gh pr close`, `git cherry-pick`, `git commit`, `git push`, `uv lock`, `uv sync`, `make verify`, `make lint`, `make test`, `pre-commit run`

**deny:** force-push, secret exfiltration, CI workflow modifications

### Network

| Field | Value |
|-------|-------|
| mode | `bounded_external_write` |
| allowed_services | `github.com` (PR operations only) |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

---

## Side Effects and Idempotency

| todo_id | side_effects | idempotency | retry | irreversible |
|---------|--------------|-------------|-------|--------------|
| T-01 | `network_write` | `non_idempotent` | `manual_only` | true |
| T-02 | `filesystem_mutation` | `safe_to_repeat` | `retry_once` | false |
| T-03 to T-05 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | false |
| T-06 to T-07 | `filesystem_mutation` | `unsafe_blind_repeat` | `manual_only` | false |
| T-08 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | false |
| T-09 to T-15 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | false |
| T-16 | `filesystem_read` | `safe_to_repeat` | `retry_once` | false |
| T-17 | `network_write` | `safe_with_dedupe` | `manual_only` | false |

---

## Architecture Impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T-03 | ideaos/pipeline | `policy` | `pipeline/IDEA_LIFECYCLE.yaml` | redesign stage order; remove existing stages |
| T-04 | ideaos/engine | `runtime` | `src/ideaos/engine.py` | change existing ladder steps |
| T-05 | ideaos/assurance | `assurance` | `src/ideaos/assurance.py` | weaken existing validations |
| T-08 | ideaos/runtime | `runtime` | `src/ideaos/runtime.py` | remove existing operations |

---

## Rollback

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.ideaos.reconciliation-12.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `true` |
| trigger_conditions | baseline drift; blocking property fail; envelope breach; cherry-pick conflict |

### Strategies

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | Revert reconciliation PR if merged |
| data | `none` | No data migrations |
| external_state | `corrective_append_only_record` | Close reconciliation PR, reopen #4-#8 |
| local_state | `git_restore_scoped_paths` | restore from origin/main on clone |

### Irreversible Operations

- T-01: Merging PR #3 cannot be undone without revert commit

---

## Complexity and Uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` |
| blast_radius | `medium` |
| architectural_boundaries_crossed | `1` (IdeaOS only) |
| external_systems_touched | `1` (GitHub) |
| migration_required | `false` |
| unknown_dependency_count | `0` |

---

## Execution DAG

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.ideaos.reconciliation-12.v1` |
| graph_type | `directed_acyclic_graph` |

### Critical Path

`T-01 -> T-02 -> T-03 -> T-04 -> T-08 -> T-16 -> T-17`

### Nodes / Edges

| id | layer | depends_on | outputs |
|----|-------|------------|---------|
| T-01 | control_plane | [] | PR #3 merged |
| T-02 | control_plane | [T-01] | branch created |
| T-03 | policy | [T-02] | unified lifecycle |
| T-04 | runtime | [T-03] | route ladder fixed |
| T-05 | assurance | [T-03, T-04] | depth validation wired |
| T-06 | runtime | [T-02] | realization depth code |
| T-07 | runtime | [T-02] | source resolution code |
| T-08 | runtime | [T-06, T-07] | unified _OPERATIONS |
| T-09 | runtime | [T-08] | Gate SDK integrated |
| T-10 | runtime | [T-09] | lockfile updated |
| T-11 | docs | [T-06] | corpus files |
| T-12 | assurance | [T-11] | S1244 fixed |
| T-13 | assurance | [T-08] | lint fixed |
| T-14 | docs | [T-03] | README updated |
| T-15 | docs | [T-14] | version bumped |
| T-16 | assurance | [T-10, T-12, T-13, T-15] | all tests pass |
| T-17 | control_plane | [T-16] | PR opened |

---

## Property Evidence Matrix

| evidence_id | claim_id | evidence_kind | command | expected_positive | status |
|-------------|----------|---------------|---------|-------------------|--------|
| EV-SP-01 | SP-01 | `filesystem_evidence` | `grep version 12.0.0` | exit 0 | `not_run` |
| EV-SP-02 | SP-02 | `structural_evidence` | `grep has_execution_assurance` | exit 0 | `not_run` |
| EV-SP-03 | SP-03 | `runtime_behavior_evidence` | python runtime check | assertion passes | `not_run` |
| EV-SP-04 | SP-04 | `quality_gate_evidence` | `make verify` | exit 0 | `not_run` |
| EV-SP-05 | SP-05 | `quality_gate_evidence` | `pre-commit run` | exit 0 | `not_run` |
| EV-SP-06 | SP-06 | `network_observation_evidence` | `gh pr create` | PR URL returned | `not_run` |

---

## Stress and Disconfirm

### Disconfirming Cases

- If cherry-pick of PR #4 conflicts with unified lifecycle (T-03) -> resolve conflicts manually using T-03 as source of truth
- If cherry-pick of PR #7 conflicts with PR #4 changes -> runtime.py will need manual merge (T-08)
- If Gate_SDK has transitive dependency conflicts -> uv lock may fail (T-10)

### Assumption Failure Conditions

- PR #3 not actually mergeable (blocked by review or CI)
- `realization_modes` and `execution_assurance` semantically incompatible
- Learning gate requires running BEFORE expansion_gate (would need lifecycle redesign)

### Blast Radius Notes

- IdeaOS runtime directly affected
- Downstream consumers: `l9-idea-execute`, `l9-idea-foundry` may need updates after 12.0
- No impact on Cursor-Governance

---

## Out of Scope

- New feature development beyond reconciliation
- Architecture redesign of lifecycle stages
- Modifications to `.github/workflows/**`
- Changes to `AGENTS.md` or `.l9/architecture.yaml`
- Downstream skill updates (`l9-idea-execute`, `l9-idea-foundry`)
- Weakening tests or gates to obtain PASS

---

## Follow-on Milestone

| priority | change | why |
|----------|--------|-----|
| P1 | Update `l9-idea-execute` skill for 12.0 lifecycle | Downstream consumer |
| P2 | Update `l9-idea-foundry` for new stages | Downstream consumer |
| P3 | Add integration tests for full 12.0 pipeline | Coverage |

---

## Convergence

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.ideaos.reconciliation-12.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

**executable_when:**
- baseline locked + reverified (PR #3 merged, branch created)
- blocking capability probes pass (gh, uv available)
- DAG acyclic (verified above)
- envelope + side-effect matrix complete (verified above)
- no blocking unknowns

**complete_when:**
- all blocking SP-* evidence `passed`
- rollback contract unused or verified
- out_of_scope respected

**blocking_conditions:**
- `preflight_blocked` (PR #3 not mergeable)
- envelope breach
- baseline drift
- failed blocking property

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `draft` -> `executable` -> `executing` -> `converged` |
| minimum_safe_next_action | Press **Build**, execute todos, then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display PR URL |
| execute_via | Cursor Build |
| broader_work_requires_separate_contract | `true` |
