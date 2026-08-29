---
name: Program Execution Authority and Recovery Remediation
overview: Repair the seven confirmed non-memory Program Execution findings at their
  existing canonical owners so the supported campaign path becomes a single fail-closed
  execution tunnel from accepted source to verified local completion. Preserve the
  folder-only audit boundary, all memory exclusions, PEC single ownership of Program
  truth, local-commit-only publication law, provider thinness, and current compiler/verification
  behavior that already works. Do not redesign Program Execution or add a second state
  machine, router, registry, validator, completion owner, or recovery authority.
todos:
- id: todo-00-execution-preflight
  content: At execution start, re-resolve origin/main, require HEAD == locked baseline,
    inspect working-tree overlap only for the exact write_allow files, and stop/replan
    on material drift or overlapping dirt. Do not mutate source in this step.
  status: pending
  phase: preflight
  depends_on: []
- id: todo-01-recovery-seal
  content: 'Seal the PEC recovery side door: add fresh-workspace to the campaign-tunnel
    mutation set; make workspace reset refuse active leases and active/ambiguous execution
    states; remove lease release and STALE->ELIGIBLE transitions from cleanup; require
    canonical fail/recover to preserve attempt evidence and establish a safe non-active
    state before destructive residue cleanup. Extend tunnel and recovery tests to
    prove no duplicate dispatch path.'
  status: pending
  phase: execute
  depends_on:
  - todo-00-execution-preflight
- id: todo-02-resume-source-lock
  content: Move execute-resume eligibility behind current-source reconciliation. Persist/compare
    source digest, program-shape digest, and per-task definition digests; unchanged
    resumes, task-local absorbable drift relocks before claim, wider drift quarantines/rebuilds,
    and an unprovable comparison fails closed. Add tests for dependency, validation,
    writable scope, authority, execution-kind, and task-set edits after partial completion.
  status: pending
  phase: execute
  depends_on:
  - todo-00-execution-preflight
- id: todo-03-completion-projection
  content: Collapse repository campaign close into a projection of PEC truth. close_campaign.py
    must consume and validate a canonical PEC terminal close/handoff receipt, bind
    campaign_id and Program Lock digest/current runtime, re-check required terminal
    predicates read-only, project the result idempotently into CAMPAIGN_STATUS/CLOSEOUT,
    and archive only after successful projection. Remove free-form evidence as independent
    close authority and align policy/docs/tests.
  status: pending
  phase: execute
  depends_on:
  - todo-00-execution-preflight
- id: todo-04-gate-derived-truth
  content: 'Make PEC gate evaluation a derivation, not an assertion. Preserve one
    evaluator inside the Controller: load the frozen gate definition, bind its digest,
    require the declared evidence IDs and current evidence, execute or mechanically
    verify the declared method/predicate, derive PASS/FAIL/BLOCKED/UNKNOWN, and keep
    waiver handling explicit. The CLI may name the gate and actor but must not choose
    PASS. Add negative tests for wrong evidence/method, stale evidence, changed definition,
    unmet pass condition, and invalid waiver.'
  status: pending
  phase: execute
  depends_on:
  - todo-00-execution-preflight
- id: todo-05-failover-parity
  content: Bind the existing EXECUTION_FAILOVER_POLICY to the live Peer provider lifecycle
    without adding a second router/state machine. Classify canonical provider failures,
    retry only declared transient classes up to the declared ceiling with a new dispatch
    ID, preserve logical task/attempt lineage, and refuse mutating failover when prior
    terminality or rollback is not proven. Keep non-retryable classes terminal. Add
    focused provider lifecycle tests and runner integration proof.
  status: pending
  phase: execute
  depends_on:
  - todo-00-execution-preflight
  - todo-02-resume-source-lock
- id: todo-06-supported-path-e2e
  content: Add one hermetic non-memory end-to-end test that invokes the actual supported
    campaign front door with a deterministic local provider and proves compile/blueprint/admission/claim/worktree/mutation/attempt/Controller
    validation+verification/integration/completion/dependency advance/canonical close.
    Add negative variants for fresh-workspace bypass, live-source drift, forged ledger
    close, gate assertion, provider failure, no-op worker, duplicate result/completion,
    dependency block, and conflicting mutations.
  status: pending
  phase: execute
  depends_on:
  - todo-01-recovery-seal
  - todo-02-resume-source-lock
  - todo-03-completion-projection
  - todo-04-gate-derived-truth
  - todo-05-failover-parity
- id: todo-07-compatibility-thinning
  content: After supported-path proof is green, extract only the live provider binding/probe/execute
    helpers from run_peer_task_pipeline.py into peer_execution/task_pipeline.py. Update
    run_campaign to consume that neutral module. Leave run_peer_task_pipeline.py as
    a minimal explicit non-routable refusal shim with no active orchestration logic,
    and add import/CLI tests that prevent resurrection of a second front door.
  status: pending
  phase: execute
  depends_on:
  - todo-05-failover-parity
  - todo-06-supported-path-e2e
- id: todo-08-final-proof
  content: Run targeted Program Execution regression suites followed by make pr-check.
    Verify only expected in-scope files changed, manifests/generated integrity are
    updated through their existing supported mechanism if required, every seven finding
    property is proven, no memory-related content changed, no publication/merge occurs,
    and the final diff contains no parallel state/receipt/router authority.
  status: pending
  phase: validate
  depends_on:
  - todo-01-recovery-seal
  - todo-02-resume-source-lock
  - todo-03-completion-projection
  - todo-04-gate-derived-truth
  - todo-05-failover-parity
  - todo-06-supported-path-e2e
  - todo-07-compatibility-thinning
isProject: false
kind: pe
execute_via: pe-campaign
kernel_pass:
  bound_path: program_execution_authority_recovery_remediation_d681ee05.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: '2026-08-28T14:37:20+00:00'
    body_sha256: '4f29033f9990e93c7c2cff5b2180bed6d297b53cfe98acde93ad02aaf0936d8e'
    deltas:
    - Compressed seven findings into six canonical-owner root causes; removed symptom-per-finding
      patching.
    - Moved P0 recovery seal ahead of all other mutation work and made safe retry
      evidence a blocking property.
    - Kept folder-only and memory exclusions as hard execution-envelope denies.
    - Rebound execution baseline to current main without changing remediation root causes.
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: '2026-08-28T14:37:21+00:00'
    body_sha256: '4f29033f9990e93c7c2cff5b2180bed6d297b53cfe98acde93ad02aaf0936d8e'
    deltas:
    - 'Added self-hosting bootstrap rule: use compiled Claude Code contracts for PE
      repair rather than relying on the defective PE side doors.'
    - Added exact negative regression properties for P0/P1 authority and false-completion
      paths.
    - Removed any plan work not traceable to PE-001 through PE-007 or required final
      proof.
    - Rebound execution baseline to current main after SHA drift and re-adjudicated all seven findings.
    - Loaded compiler v2.7.0; target-native validation, compound preflights, committed_and_validated seams, and single terminal make pr all validate.
---

# PLAN: Program Execution Authority and Recovery Remediation

> **First-class SSOT:** current `canonical.template.executable_plan.v1.plan.md` at locked baseline.
> **Status:** executable planning authority; implementation has not run. Claude Code contracts v2.7 are the bounded bootstrap executor projection.
> **Self-host rule:** this plan repairs Program Execution itself. Use the validated Claude Code contract chain in this package as the bootstrap executor. Do not exercise the defective reset/ledger-close side doors. After repairs, the supported PE front-door E2E must prove the canonical path.

## Execute via @environment/program-execution + autonomy (required)

Canonical steady-state execution remains `.plan.md -> @environment/program-execution -> Program Lock/Controller -> subordinate @autonomy -> Peer Execution Core`. This remediation is a self-host repair, so the packaged Claude Code contracts are the bounded bootstrap executor projection. They may not widen this plan. Program Execution work itself stops at local commits; the terminal compiler wrapper may invoke `make pr` once after the final validated commit.

### Pipeline steps

1. Create `claude/program-execution-authority-remediation-v1` from exact `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`; stop and replan on any material baseline drift.
2. Execute contracts PR-001 through PR-006 in order. Each fresh Claude session runs its generated `preflight.sh` before mutation.
3. Contracts 1-5 produce exactly one validated local commit each and never publish. Direct `git push`, direct `gh pr create`, merge, deployment, and repo-settings mutation remain denied.
4. Contract 6 proves the supported front door, compatibility thinning, and final quality gate, then creates its one validated local commit.
5. Only after contract 6 is green, run the compiler-authorized terminal `make pr` exactly once. Merge remains outside this chain.

### Adapter routing

Use the executor selected by the Claude contract compiler for implementation. Do not create a new Program Execution provider registry or routing layer. The live steady-state provider lifecycle remains Peer Execution controlled.

### Campaign authorization packet

`autonomous_merge: false`; allowed scope is exactly the filesystem envelope below; forbidden capabilities include direct git push, direct gh PR creation, merge, force-push, admin merge, deployment, secret access, scope expansion, and all excluded memory work. The sole remote-delivery exception is terminal `make pr` in contract 6.

### Phase-0 action table ↔ PE Task Cards

| id | wave | depends_on | mutation | isolation | findings |
|---|---|---|---|---|---|
| todo-00-execution-preflight | W0 | none | false | baseline_drift_prevention | cross-cutting |
| todo-01-recovery-seal | W1 | todo-00-execution-preflight | true | RC-001 | PE-001 |
| todo-02-resume-source-lock | W1 | todo-00-execution-preflight | true | RC-002 | PE-002 |
| todo-03-completion-projection | W1 | todo-00-execution-preflight | true | RC-003 | PE-003 |
| todo-04-gate-derived-truth | W1 | todo-00-execution-preflight | true | RC-004 | PE-004 |
| todo-05-failover-parity | W1 | todo-00-execution-preflight, todo-02-resume-source-lock | true | RC-005 | PE-005 |
| todo-06-supported-path-e2e | W2 | todo-01-recovery-seal, todo-02-resume-source-lock, todo-03-completion-projection, todo-04-gate-derived-truth, todo-05-failover-parity | true | RC-006 | PE-006 |
| todo-07-compatibility-thinning | W2 | todo-05-failover-parity, todo-06-supported-path-e2e | true | RC-006 | PE-007 |
| todo-08-final-proof | W2 | todo-01-recovery-seal, todo-02-resume-source-lock, todo-03-completion-projection, todo-04-gate-derived-truth, todo-05-failover-parity, todo-06-supported-path-e2e, todo-07-compatibility-thinning | false | cross-cutting-proof | cross-cutting |

## Metadata

| Field | Value |
|---|---|
| plan_id | `plan.program-execution.authority-recovery-remediation.v1` |
| schema_version | `1.0.0` |
| status | `executable` |
| plan_class | `remediation_plan` |
| owner | `l9_global_architect_remediation_planner` |
| created_at | `2026-08-27` |

## Architect framing

| Field | Value |
|---|---|
| planning_ssot | validated PLAN_DOCUMENT JSON in this package |
| plan_class | `remediation_plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Repair existing canonical owners; no second state machine/router/validator/completion owner. |

## Immutable baseline

| Field | Value |
|---|---|
| captured_at | `2026-08-27T19:05:08Z` |
| repository | `Quantum-L9/Cursor-Governance` |
| workspace | executor checkout, re-resolved at execution |
| branch | `claude/program-execution-authority-remediation-v1` created from current `main` baseline |
| commit_sha | `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d` |
| dirty | `UNKNOWN_NOT_LOCAL_WORKSPACE`; must be rechecked before mutation |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Repair the seven confirmed non-memory Program Execution findings at their existing canonical owners so the supported campaign path becomes a single fail-closed execution tunnel from accepted source to verified local completion. Preserve the folder-only audit boundary, all memory exclusions, PEC single ownership of Program truth, local-commit-only publication law, provider thinness, and current compiler/verification behavior that already works. Do not redesign Program Execution or add a second state machine, router, registry, validator, completion owner, or recovery authority.

### Success properties

| id | property | evidence_type | proof | blocking |
|---|---|---|---|---|
| SP-01 | Execution start re-verifies Cursor-Governance main at the locked 40-character SHA and stops/replans on drift. | `repository_state` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-02 | Direct pec fresh-workspace without the campaign tunnel is rejected before state or filesystem mutation. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-03 | No workspace reset can release an active execution lease or transition an active/ambiguous attempt directly back to ELIGIBLE. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-04 | Every resumed execute path reconciles current source identity and task/program shape against the active Program Lock before dispatch. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-05 | Repository campaign lifecycle complete/archive can be produced only from a current canonical PEC terminal receipt whose campaign and Program Lock identities match. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-06 | A gate cannot PASS from caller assertion: PEC derives the result from the frozen definition, required evidence, current revision/freshness, waiver law, and executable method/predicate semantics. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-07 | Provider retry/failover obeys EXECUTION_FAILOVER_POLICY: bounded retryable classes only, new dispatch identity, and no mutating failover after uncertain/partial mutation without proven rollback. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-08 | A hermetic test traverses the supported campaign front door through real local mutation, Controller verification, integration, task completion, dependency advance, and canonical campaign close, including the P0/P1 negative cases. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-09 | run_peer_task_pipeline.py no longer contains active provider lifecycle ownership; its public compatibility behavior remains an explicit refusal and run_campaign consumes the neutral Peer lifecycle module. | `runtime_behavior` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |
| SP-10 | All changed Program Execution tests and make pr-check pass without weakening validation, widening authority, touching excluded content, or publishing/merging. | `quality_gate` | mapped negative/positive tests plus observed Controller/runner state; exit-0 alone insufficient | true |

## Capability preflight

`preflight_id: preflight.plan.program-execution.authority-recovery-remediation.v1`

### Probes

| id | capability | command_or_action | pass_criteria | blocking |
|---|---|---|---|---|
| CP-01 | baseline | `git rev-parse HEAD` | equals `5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d` | true |
| CP-02 | clean overlap | `git status --porcelain` filtered to write_allow | no unowned overlapping dirt | true |
| CP-03 | local validation | Python/pytest/git/make availability | required local commands resolve | true |

## Execution envelope

### Filesystem

**write_allow**
- `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`
- `environment/program-execution/campaigns/README.md`
- `environment/program-execution/campaigns/scripts/close_campaign.py`
- `environment/program-execution/campaigns/scripts/test_close_campaign.py`
- `environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py`
- `environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py`
- `environment/program-execution/core/program-execution-controller-template/scripts/pec/workspace_reset.py`
- `environment/program-execution/core/program-execution-controller-template/scripts/tests/test_gate_evaluation.py`
- `environment/program-execution/core/program-execution-controller-template/scripts/tests/test_workspace_reset_safety.py`
- `environment/program-execution/peer_execution/task_pipeline.py`
- `environment/program-execution/peer_execution/tests/test_failover_policy.py`
- `environment/program-execution/registry/EXECUTION_FAILOVER_POLICY.yaml`
- `environment/program-execution/scripts/run_campaign.py`
- `environment/program-execution/scripts/run_peer_task_pipeline.py`
- `environment/program-execution/scripts/tests/test_campaign_tunnel_airtight.py`
- `environment/program-execution/scripts/tests/test_run_campaign.py`
- `environment/program-execution/tests/hardening/test_supported_campaign_front_door_e2e.py`

**write_deny**
- ALL paths outside environment/program-execution/**
- Any memory-related directory, module, class, function, contract, schema, test, fixture, example, documentation, integration, receipt, or generated surface even if nested under environment/program-execution/**
- root autonomy/ implementation and ops/autonomy implementation
- repository-wide CI, unrelated skills/agents, external repositories
- secrets, credentials, caches, build outputs, generated runtime state

### Commands

- allow: repository reads; targeted pytest; Python validation; git status/diff/restore/add/commit with scoped pathspecs; `make pr-check`.
- deny: push, `make pr`, PR create/edit/merge, force-push, hard-reset, admin merge, deployment, package installs unrelated to existing test execution, secret reads/exfiltration.

### Network

| Field | Value |
|---|---|
| mode | `read_only` for baseline verification only; implementation effects must remain local |
| allowed_services | GitHub read-only only when needed to reverify baseline |

### Secrets

| Field | Value |
|---|---|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`false`. Push/PR/merge are outside this remediation execution chain.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---|---|---|---|---|---|
| todo-00-execution-preflight | filesystem_read | safe_to_repeat | retry_once | none | false |
| todo-01-recovery-seal | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-02-resume-source-lock | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-03-completion-projection | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-04-gate-derived-truth | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-05-failover-parity | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-06-supported-path-e2e | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-07-compatibility-thinning | filesystem_mutation | unsafe_blind_repeat | manual_only | revert scoped local commit / git_restore_scoped_paths | false |
| todo-08-final-proof | filesystem_read | safe_to_repeat | retry_once | none | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---|---|---|---|---|
| todo-01-recovery-seal | Program Execution | runtime/control_plane/assurance | `RC-001` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-02-resume-source-lock | Program Execution | runtime/control_plane/assurance | `RC-002` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-03-completion-projection | Program Execution | runtime/control_plane/assurance | `RC-003` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-04-gate-derived-truth | Program Execution | runtime/control_plane/assurance | `RC-004` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-05-failover-parity | Program Execution | runtime/control_plane/assurance | `RC-005` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-06-supported-path-e2e | Program Execution | runtime/control_plane/assurance | `RC-006` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |
| todo-07-compatibility-thinning | Program Execution | runtime/control_plane/assurance | `RC-006` mapped to current canonical owner | duplicate authority; outside-root edits; excluded memory work; publication effects |

## Rollback

`rollback_id: rollback.plan.program-execution.authority-recovery-remediation.v1`; automatic rollback forbidden.

### Strategies

| domain | mode | notes |
|---|---|---|
| code | `revert_commit` or `git_restore_scoped_paths` | only current root-cause batch; preserve prior green batches |
| data | `none` | no production data mutation |
| external_state | `none` | no external writes authorized |
| local_state | `git_restore_scoped_paths` | preserve test/recovery evidence before restore |

### Irreversible operations

- none authorized.

### Rollback verification

- Re-run the root-cause negative test and the baseline/diff-hygiene checks after restore.

## Complexity and uncertainty

| Field | Value |
|---|---|
| complexity | `high` |
| uncertainty | `low` |
| blast_radius | `high` |
| architectural_boundaries_crossed | `4` (runner, PEC, campaign ledger projection, Peer lifecycle) |
| external_systems_touched | `0` by mutation |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Execution DAG

`topology_id: dag.plan.program-execution.authority-recovery-remediation.v1` · directed acyclic graph

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|---|---|---|---|---|
| todo-00-execution-preflight | current canonical owner | runtime/assurance | none | baseline_drift_prevention implementation/evidence |
| todo-01-recovery-seal | current canonical owner | runtime/assurance | todo-00-execution-preflight | RC-001 implementation/evidence |
| todo-02-resume-source-lock | current canonical owner | runtime/assurance | todo-00-execution-preflight | RC-002 implementation/evidence |
| todo-03-completion-projection | current canonical owner | runtime/assurance | todo-00-execution-preflight | RC-003 implementation/evidence |
| todo-04-gate-derived-truth | current canonical owner | runtime/assurance | todo-00-execution-preflight | RC-004 implementation/evidence |
| todo-05-failover-parity | current canonical owner | runtime/assurance | todo-00-execution-preflight, todo-02-resume-source-lock | RC-005 implementation/evidence |
| todo-06-supported-path-e2e | current canonical owner | runtime/assurance | todo-01-recovery-seal, todo-02-resume-source-lock, todo-03-completion-projection, todo-04-gate-derived-truth, todo-05-failover-parity | RC-006 implementation/evidence |
| todo-07-compatibility-thinning | current canonical owner | runtime/assurance | todo-05-failover-parity, todo-06-supported-path-e2e | RC-006 implementation/evidence |
| todo-08-final-proof | current canonical owner | runtime/assurance | todo-01-recovery-seal, todo-02-resume-source-lock, todo-03-completion-projection, todo-04-gate-derived-truth, todo-05-failover-parity, todo-06-supported-path-e2e, todo-07-compatibility-thinning | cross-cutting-proof implementation/evidence |

**Critical path:** todo-00-execution-preflight -> todo-01-recovery-seal -> todo-02-resume-source-lock -> todo-05-failover-parity -> todo-06-supported-path-e2e -> todo-07-compatibility-thinning -> todo-08-final-proof

**Forbidden edges:** proof before behavior; compatibility cleanup before supported-path proof; any edge to excluded memory or outside-root mutation.

## Property evidence matrix

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|---|---|---|---|---|---|---|
| EV-SP-01 | SP-01 | property_evidence | independent behavior/structure observation | `git rev-parse HEAD` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-02 | SP-02 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-03 | SP-03 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-04 | SP-04 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-05 | SP-05 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-06 | SP-06 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-07 | SP-07 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-08 | SP-08 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-09 | SP-09 | property_evidence | independent behavior/structure observation | `mapped targeted pytest/structural assertion` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |
| EV-SP-10 | SP-10 | property_evidence | independent behavior/structure observation | `make pr-check` | property discriminator satisfied; corresponding negative case fails before repair and passes after | not_run |

## Stress and disconfirm

### Disconfirming cases

- Can fresh-workspace still cause any active or terminality-unknown provider attempt to lose its lease/worktree and later be redispatched?
- Can an edited campaign source reach provider dispatch on a resumable runtime before current source/Program Lock reconciliation?
- Can CAMPAIGN_STATUS or COMPLETED advance without a valid current PEC terminal receipt?
- Can a caller still choose a gate PASS while the frozen gate definition would not derive PASS?
- Can provider retry/failover occur after partial mutation or uncertain terminality without proven rollback?
- Could every unit test pass while the real run_campaign front door remains broken or bypassable?
- Does extracting provider helpers accidentally create another public execution path or duplicate lifecycle owner?

### Assumption failure conditions

- Current main changes materially before execution starts
- Canonical ownership moves outside environment/program-execution/ before implementation
- Required correction is found to depend on excluded memory behavior
- Existing Program Execution quality gate is unavailable in the execution workspace

### Blast radius notes

- High: incorrect recovery/resume/completion repairs can duplicate consequential execution or manufacture terminal truth; incorrect gate/failover changes can silently weaken verification or retry safety.

### Rollback constraints

- Each implementation batch is a scoped local commit. On a blocking property failure, revert only that batch commit or git-restore its exact write_allow paths; preserve prior green batches and all recovery evidence. No force-push or hard reset.

## Out of scope

- All memory-related Program Execution content and all memory dependencies
- All repository paths outside environment/program-execution/** except read-only execution preflight of repository instructions/baseline metadata
- root autonomy/ implementation and ops/autonomy implementation
- Unrelated agents, skills, repository-wide CI, external repositories, publication/merge/deployment redesign
- Any feature work not required to close PE-001 through PE-007

## Convergence

`convergence_id: conv.plan.program-execution.authority-recovery-remediation.v1`

### Gates

- executable_when: locked baseline reverified, exact envelope accepted, no overlapping dirt, compiler contract preflight passes.
- complete_when: SP-01 through SP-10 all have discriminating passing evidence, targeted suites and make pr-check pass, and diff stays inside scope.
- blocking_conditions: baseline drift, memory/outside-root scope request, active reset path still possible, false close path remains, gate caller can assert PASS, unsafe failover, supported-front-door E2E failure.
- compiler_status: v2.7.0 target compatibility PASS; 6/6 contracts + chain + 11/11 target regression suite PASS.

### Evidence

- required_evidence_refs: EV-SP-01 through EV-SP-10.
- observed_evidence_refs: populated by implementation contracts.
- missing_evidence: all implementation evidence until contracts run.

### Blockers / unknowns

- No target-architecture or compiler unknown blocks execution. Current main drift was re-adjudicated; all seven findings remain. v2.7 emits explicit target-native validation, safe compound preflights, committed_and_validated seams, and one terminal make pr wrapper.

### Next

- minimum_safe_next_action: execute the first validated Claude Code contract from this package against the locked baseline.
- execute_via bootstrap: validated Claude Code v2.7 contract chain on the declared branch; contracts 1-5 local-only, contract 6 terminal make pr. Steady-state after remediation remains `@environment/program-execution -> Program Lock/Controller -> @autonomy -> Peer adapter`.
- broader_work_requires_separate_contract: true

