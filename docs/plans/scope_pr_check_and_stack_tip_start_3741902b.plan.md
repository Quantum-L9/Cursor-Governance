---
name: Scope make pr-check pytest and start agents on the stack tip
overview: "Cut make pr wall-clock by scoping local pytest to changed Python and by creating agent worktrees from the unambiguous open-PR stack tip when PR_STACK=auto."
todos:
  - id: T1
    content: "Add a fail-closed stack-tip resolver: unique open-PR chain tip, else origin/main if none, else exit 2 on sibling chains. Same rule for start and publish. Do not require file overlap."
    status: pending
    phase: execute
    depends_on: []
  - id: T3
    content: "Scope make pr-check pytest: never pass repo-root '.' for local profile. Select changed tests plus inferred test_<stem>.py. Non-dot suites only when owned_paths intersect. No inferred test fails closed to that tests/ directory, not the catalog."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Default agent_worktree_start.sh base to the resolver tip when PR_STACK is auto. Empty PR_STACK keeps origin/main. Implied L9_TASK_BASE_AUTHORIZED for that auto tip only."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T4
    content: "Prove both selectors with unit tests (tip vs main vs siblings; autonomy-only change excludes PE and generated-data; non-dot owned_path still runs that suite)."
    status: pending
    phase: validate
    depends_on: [T1, T3]
  - id: T6
    content: "After ruff-format dirties only the files it formatted, restage those paths in the same gate pass or write the receipt after format. Do not git add -A."
    status: pending
    phase: execute
    depends_on: [T3]
  - id: T5
    content: "Align AGENTS.md, surface_profile.yaml, and rules/53 so agents start on the tip instead of inventing a main branch and restacking at make pr."
    status: pending
    phase: converge
    depends_on: [T2, T4]
isProject: false
kernel_pass:
  bound_path: scope_pr_check_and_stack_tip_start_3741902b.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-21T05:57:52Z
    body_sha256: "06c15db5d6df721d6c1d59188b0390ac355422d6ef96c282671f1cd7ffbd6598"
    deltas:
      - applied Improve.md to this plan artifact
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-21T06:00:52Z
    body_sha256: "06c15db5d6df721d6c1d59188b0390ac355422d6ef96c282671f1cd7ffbd6598"
    deltas:
      - applied Validate & Repair.md and stamped kernel_pass
---
# PLAN: Scope make pr-check pytest and start agents on the stack tip

> **Projected from** validated PLAN_DOCUMENT `pr_check_scope_and_stack_tip_start.json` (validate_plan_document.py PASS).
> **plan_id:** plan.governance.scope-pr-check-stack-tip.v1
> **schema_version:** canonical.schema.plan_document.v1 / l9-plan 1.0.0
> **status:** executable (baseline bound, envelope set, selectors specified)
> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate). Do not free-form mutate from this markdown alone.

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
  (Cursor: cursor-foreground)
```

Live execution is one command. Do not hand-run pec, L4, or inner compile scripts from this plan.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<activate.yaml projected from this plan>
```

`autonomous_merge: false`. Publish via `PR_REMEDIATE=0 make pr` after L4 authorize-release. Merge only through `/l9-pr-remediation` + `stack_safe_merge.py`.

### Campaign authorization packet (fill at execute)

```yaml
packet_id: autonomy-2026-08-21-pr-check-stack-tip
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
authority_profile: program_controller_bound
autonomous_merge: false
plan_ref: /Users/ib-mac/.cursor/plans/scope_pr_check_and_stack_tip_start_3741902b.plan.md
plan_id: plan.governance.scope-pr-check-stack-tip.v1
program_execution:
  root: environment/program-execution
  provider_ref: cursor-foreground
```

## Metadata

| Field | Value |
|-------|--------|
| plan_id | plan.governance.scope-pr-check-stack-tip.v1 |
| schema_version | 1.0.0 |
| status | executable |
| depth | deep |
| target_repo | Quantum-L9/Cursor-Governance |
| workspace | `$HOME/.cursor-governance` (SSOT) or a worktree on `feat/stack-safe-merge` / #242 tip |

## Architect framing

Two delays share one publish path. `make pr-check` already scopes ruff and security to changed files. Pytest ignores that list and runs `python-contract.json` (repo-root `'.'` plus PE and generated-data). Agents still fork `origin/main`; `PR_STACK=auto` only restacks after the gate, and only when overlap blockers exist. #242 published against main for that reason. The other agent in the 12:36 screenshot then paid a second catalog to stack two commits onto #242.

Fix the selectors in code. Do not tell agents to remember a shorter pytest command.

## Immutable baseline

| Ref | Full SHA |
|-----|----------|
| origin/main | `a588f8b23212b176861dc5abf9f1172536943c77` |
| PR #242 tip (`feat/stack-safe-merge`) | `dcb84112c4714705bbc60291223daa3e64b70ee3` |
| Local SSOT main (unpushed, do not land this plan on it) | `2b5f1cda6b0bd4231b0769b693dcc77088b0c878` |

Stop and replan if origin/main moves or #242 is merged/retargeted before execute.

**Start execute from the #242 tip**, not a new `origin/main` fork. That matches the contract this plan writes. KERNEL_PACK_NEW_BRANCH_DEFAULT_V1 yields to the user-named stack-tip rule.

## Objective

Cut `make pr` wall-clock without weakening CI or merge safety.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Unique open-PR chain + default `PR_STACK=auto` → worktree `base_sha` is the fetched tip, not origin/main | repository_state | resolver unit test + start script probe | true |
| SP-02 | Two sibling PRs targeting main → start exits 2 and names both heads | quality_gate | `test_resolve_stack_tip.py` | true |
| SP-03 | `PR_STACK=` → start remains origin/main | repository_state | unit / script probe | true |
| SP-04 | Changed files only `merge_gate.py` + `test_merge_gate.py` → local pytest argv excludes PE and generated-data and includes those paths | quality_gate | `test_select_pr_pytest_paths.py` | true |
| SP-05 | `make test` / `make pr-full` / CI still collect repo-root `'.'` | quality_gate | argv fixture for ci/pr-full profile | true |
| SP-06 | `make pr-check` PASS on the implementation worktree | quality_gate | gate receipt | true |

## Capability preflight

- `gh` required for live tip resolve; offline: fail-closed (U1).
- Locked `.venv` via `ensure_gov_python.sh` (`pwd -P` after #242).
- Public verbs: `make pr-check`, `PR_REMEDIATE=0 make pr`.

## Execution envelope

| Plane | Allowed |
|-------|---------|
| fs | Paths in gmp_handoff.may_modify under Cursor-Governance |
| commands | pytest on selector tests; `make pr-check`; `PR_REMEDIATE=0 make pr` after L4 |
| network | `gh pr list` for the resolver; GitHub publish via `make pr` only |
| secrets | existing openclaw PAT via sanctioned `gh`; no new secrets |
| autonomous_merge | false |

## Side effects and idempotency

| Todo | Side effect | Idempotent |
|------|-------------|------------|
| T1 | New resolver module | Re-run safe; no remote |
| T2 | New worktrees fork tip SHA | Same inputs → same base |
| T3 | Local gate runs fewer tests | CI unchanged |
| T6 | May stage ruff-format paths the gate itself wrote | Explicit pathspecs only |
| T5 | Doc text | Re-run safe |

## Architecture impact

- `PR_STACK=auto` moves from publish-time overlap exception to **start-time default ancestry**.
- Local pytest profile is no longer “any `.py` → catalog”.
- `owned_paths: ['.']` stays valid for CI. Local pr-check must not treat `.` as “run everything”.

## Rollback

Revert the feature-branch commits. Restore `run_pr_gate.sh` pytest to `run_pytest_suites.sh` with only the secrets ignore. Restore `agent_worktree_start.sh` `origin/main` default. Do not touch `stack_safe_merge.py` or merge-gate parent-squash denial.

## Complexity and uncertainty

Deep: quality-gate polarity + main-bound contract. U1 bounded to fail-closed when `gh` cannot list PRs (same polarity as merge_gate stack probe).

## Execution DAG

```text
T1 (resolver) ─┬─► T2 (start) ─► T5 (docs)
               └─► T4 (tests) ─┘
T3 (pytest select) ─┬─► T4
                    └─► T6 (format same-gate)
```

| Phase-0 / PE card | Todo | Wave |
|-------------------|------|------|
| W0 baseline | P0–P2 already passed | 0 |
| W1 selectors | T1, T3 | 1 |
| W2 wire + prove | T2, T4, T6 | 2 |
| W3 align docs + pr-check | T5, V2 | 3 |

## Property evidence matrix

See Success properties SP-01..SP-06. Each maps to T4 fixtures plus V2 `make pr-check`.

## Stress and disconfirm

- Intersecting changed files with `owned_paths='.'` still dumps the catalog — **T3 forbids passing `.` on the local profile**.
- Picking newest-by-createdAt among siblings can orphan the other child — **T1 exits 2**.
- Shared helper with no `test_<stem>.py` ships untested — **fail-closed to that `tests/` directory or block**.
- Implied auth on any `--base` waives main-bound — **only the resolver-selected tip**.

Blast radius: under-scoped pytest; wrong-parent squash orphan; fail-open main fork when `gh` is down.

## Out of scope

- Weakening scanners or CI coverage
- Merge-method / squash-parent logic (already locked)
- Rebase of published history; merge of #240/#241/#242
- CEG engine/chassis
- Workflow YAML
- Push to `main`

## Convergence

- status: partial (implementation not run)
- remaining_unknown_ids: U1 (bounded fail-closed)
- next_skill: l9-ynp → then `@environment/program-execution` + `/autonomy`
- execute_via: PE Controller then subordinate autonomy
- stop_reason: Plan validated; do not mutate until the user starts the PE campaign

PLAN_DOCUMENT: `/Users/ib-mac/.cursor/plans/pr_check_scope_and_stack_tip_start.json`
