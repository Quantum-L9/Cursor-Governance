---
name: Close false attestation on PRs 776 777 778 and 786
overview: "Repair the confirmed false attestations on the existing PR heads and make 786 mergeable against current main. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=5c9536867c13e1df842b9458a8a4d3f3f88da0fd675f08635d95aa6519b78aa9 conflicts=0 policy_version=memory-phase-lock/v2. GAR run gar-pr-attestation-closure-2026-10-27 selected repair-in-place: exact hunk compare in the existing diff c..."
todos:
  - id: T1
    content: "On agent/claude-code/pr-audit-pipeline, stop assemble_audit.py from writing SURVIVED, validation_result PASS, or audit_passes pass_type VERIFICATION from a lane READY declaration or a probe DONE prose string. Require a separate run-directory final-verification artifact bound to the frozen head and covering claim, obligation, and probe ids before CONVERGED. Update test_audit_pipeline.py so the malformed-payload prose string cannot project that trio. Land the commit on the existing 777 branch."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "On the same 777 branch, make collect_snapshot.py select review threads with skills/l9-pr-remediation/scripts/protocol.py rest_only and the GraphQL reviewThreads path used by ingest_signals.py. Use ccr/review_threads only on the REST-only surface. If the selected transport fails, try the other once, then exit non-zero. Record classic branch protection: HTTP 404 with body Branch not protected means ABSENT; HTTP 200 is merged into required checks and approvals; every other result is UNKNOWN and cannot set complete readiness. Update semantic-lane.md so rulesets alone are not described as full merge readiness."
    status: pending
    phase: execute
    depends_on: [T1]
  - id: T3
    content: "Rebase agent/claude-code/pr-audit-correctness onto the new 777 tip. Keep the verify- lane head binding, previous_path overlap, and stand-alone bot lane pooling. Confirm the T1 and T2 closures are present on the new 778 head. Publish 778 with PR_BASE set to agent/claude-code/pr-audit-pipeline. Do not squash 778 onto main."
    status: pending
    phase: execute
    depends_on: [T1, T2]
  - id: T4
    content: "On agent/claude/gar-coding-delegation-exclusivity, replace patch-id equality in diff_truth with an exact compare of hunk text against git diff --no-color --no-ext-diff of frozen_target_revision and the delivered revision. The only permitted normalization is dropping the index oid header line. Indentation-only added lines and shifted hunk headers return VIOLATED. Extend the in-file regression next to the VALUE = 3 case. Publish on that existing branch against main."
    status: pending
    phase: execute
    depends_on: []
  - id: T5
    content: "On agent/cursor/retire-stale-ci-skills, rebase onto current origin/main. Ignore a clean git merge-tree result that comes from merge.l9-generated keep-ours. Regenerate rules/RULES-MANIFEST.json, rules/RULES-MANIFEST.md, rules/RULES-MANIFEST.yaml, environment/generated/llm-rules/MANIFEST.json, both skill-registry.json copies, and filetree.md from the post-rebase tree. Confirm GitHub mergeable is MERGEABLE. Do not import 778 registry digest 54912808."
    status: pending
    phase: execute
    depends_on: []
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Close false attestation on PRs 776 777 778 and 786

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.
> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
> **Execute:** Press **Build**. Stack on the unique open-PR tip if any open PR exists. After todos: `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do not run `make campaign`.
> **Suggested filename:** `close-false-attestation-on-prs-776-777-778-and-786_7749337c.plan.md`

## Objective (from PLAN_DOCUMENT)

Repair the confirmed false attestations on the existing PR heads and make 786 mergeable against current main. MEMORY_PREFETCH namespace=cursor-governance snapshot_digest=5c9536867c13e1df842b9458a8a4d3f3f88da0fd675f08635d95aa6519b78aa9 conflicts=0 policy_version=memory-phase-lock/v2. GAR run gar-pr-attestation-closure-2026-10-27 selected repair-in-place: exact hunk compare in the existing diff check, no synthesized SURVIVED or VERIFICATION pass, classic protection ABSENT only on the documented not-protected response otherwise UNKNOWN, and the existing review-thread transport selector. 778 keeps its verifier, rename overlap, and bot-lane split. 786 regenerates generated files after a rebase. Do not open a fifth sibling branch.

### Success properties (seed — complete evidence_type/proof in template sections)

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | A submitted patch whose added line has four extra spaces, and a patch whose hunk header line numbers differ, both fail diff_is_the_delivered_change on head 573fd886 or its descendant | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-02 | The pipeline fixture string fed malformed payloads; rejected does not produce merge_readiness READY together with a SURVIVED readiness probe or convergence_status CONVERGED | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-03 | collect_snapshot records classic protection ABSENT only for HTTP 404 body Branch not protected, merges a HTTP 200 protection document into the gate, and withholds complete readiness when the classic source is UNKNOWN | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-04 | On a local CLI host, collect_snapshot reads review threads through GraphQL reviewThreads; the ccr route is used only when rest_only is true; neither transport available exits non-zero | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-05 | 778 head still descends from 777, still binds merge-blocking finding verification to the frozen head, and still counts previous_path in overlap | quality_gate | observe .pre-commit-config.yaml catalog | true |
| SP-06 | 786 new head is GitHub mergeable MERGEABLE against main, and both skill registries are regenerated from that tree rather than copied from 778 | quality_gate | observe .pre-commit-config.yaml catalog | true |

## Scope (from PLAN_DOCUMENT)

**In:** PR 776 branch agent/claude/gar-coding-delegation-exclusivity at 573fd886e49ee7646ae71421b206b39425486e04, PR 777 branch agent/claude-code/pr-audit-pipeline at f175f971511f030790d758d30eae2cc28a1fc7ed, PR 778 branch agent/claude-code/pr-audit-correctness at d8e92836991849a266408bbacd62d638bd6c9ff2, rebased onto the repaired 777 tip, PR 786 branch agent/cursor/retire-stale-ci-skills at e264a1b42cf10c031994cc92100459ce8758b4ca, rebased onto origin/main, skills/l9-global-architect/scripts/verify_coding_delegation.py, skills/l9-pr-audit/scripts/assemble_audit.py, skills/l9-pr-audit/scripts/collect_snapshot.py, skills/l9-pr-audit/schemas/lane-findings.schema.json, skills/l9-pr-audit/references/semantic-lane.md, tests/skills/l9_pr_audit/test_audit_pipeline.py, Generated registries, rules manifests, llm-rules manifest, and filetree.md on the 786 tree only, via their owning generators

**Out:**
- A new branch from origin/main
- Squash of 778 onto main
- Unwinding 778 verifier, previous_path overlap, or stand-alone bot lane pooling
- Copying either branch skill-registry.json wholesale when 778 and 786 later share one tree
- Root additive_only files
- Merging any of these PRs
- The dirty checkout claude/gar-skill-bootstrap-hook-mm2oj9
- Dependabot PRs 764 765 766 771 and PR 791

## Critical path (seed)

T1 → T2 → T3

## Stress (seed from PLAN_DOCUMENT)

- Blast radius: Honest audits that were projecting READY from prose probes become UNKNOWN or NOT_READY until a real head-bound verification artifact exists. 778's stack parent changes. 786's generated manifests follow the post-rebase tree, so a bad generator run republishes stale digests.
- Rollback: Revert the scoped commits on each existing PR branch. Do not force-push. If the 778 rebase is wrong, reset that branch only to d8e92836991849a266408bbacd62d638bd6c9ff2 with an explicit user request, otherwise stop and leave the pre-rebase ref intact.

## Convergence (seed)

- status: partial
- next_skill: Build then stacked make pr
- stop_reason: Plan is ready to Build. Execution evidence FV-001 FV-002 and FV-003 is still pending. U2 is resolved by regeneration, not by a hand merge.
- execute_via: cursor-build

---

## Template body (complete every required section before status=executable)

# PLAN: Close false attestation on PRs 776 777 778 and 786

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

### Board binding for this plan

The open board has sibling chains, including 776, 777 with child 778, 786, and 791. `PR_STACK=auto` cannot resolve one tip and fails closed. Execute each todo on its existing branch. Publish with `PR_STACK` empty and `PR_BASE` set to that PR's current base. 778 stays based on `agent/claude-code/pr-audit-pipeline`. Do not call `agent_worktree_start.sh` for these repairs. The branches already exist. This planning checkout is `claude/gar-skill-bootstrap-hook-mm2oj9` at `61bd04b46abdacea150670f1c7ef87071f03464c` and is dirty, including `skills/l9-pr-audit/schemas/audit-output.schema.json`. Use `ops/scripts/worktree_add_wired.sh` for the existing branch when this checkout is not that branch. Do not copy this checkout's dirty files into those worktrees.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.governance.pr-attestation-closure.v1` |
| name | Close false attestation on PRs 776 777 778 and 786 |
| overview | Repair false diff, readiness, and transport attestations on the existing PR heads, and make 786 mergeable by regenerating projections after a rebase onto main. |
| schema_version | `1.0.0` |
| status | `draft` |
| is_project | false |
| owner | igor_beylin |
| created_at | 2026-10-27 |
| updated_at | 2026-10-27 |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | `docs/plans/pr-attestation-closure.plan.json` |
| plan_class | `remediation_plan` |
| redesign_allowed | false |
| follow_on_schema_evolution_separate | true |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign. GAR run `gar-pr-attestation-closure-2026-10-27` selected repair-in-place of the existing checks. First-order intervention is stop false attestation, not a new audit product. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | 2026-10-27T21:06:00-04:00 |
| repository | Quantum-L9/Cursor-Governance |
| workspace | /Users/ib-mac/Cursor-Governance |
| ssot_clone | /Users/ib-mac/Cursor-Governance |
| branch | claude/gar-skill-bootstrap-hook-mm2oj9 |
| commit_sha | 61bd04b46abdacea150670f1c7ef87071f03464c |
| dirty | true |
| artifact_hashes | audited heads 573fd886e49ee7646ae71421b206b39425486e04, f175f971511f030790d758d30eae2cc28a1fc7ed, d8e92836991849a266408bbacd62d638bd6c9ff2, e264a1b42cf10c031994cc92100459ce8758b4ca; origin/main b0ac77ad75710974f0e8b1a7a9ff732fe2fd3868 |
| allowed_local_dirt | none of this checkout's dirt is in the execution trees |
| overlap_policy | stop_if_dirty_overlaps_may_modify |
| verification_rule | reverify_at_execution_start |
| on_drift | stop_and_replan |

Reverify the four PR head SHAs before the first edit. If a head moved, stop.

## Objective

### Mission

Close F776-01, F777-01, F777-02, and F777-03 on the branches that contain them, keep 778's repairs, and make 786 mergeable against current main by regeneration rather than keep-ours.

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Indentation-only and hunk-header substitutions fail `diff_is_the_delivered_change` | runtime_behavior | in-file regression next to the VALUE = 3 case | true |
| SP-02 | Prose DONE probe does not yield READY plus SURVIVED plus CONVERGED | runtime_behavior | `tests/skills/l9_pr_audit/test_audit_pipeline.py` | true |
| SP-03 | Classic protection ABSENT only for body `Branch not protected`; otherwise UNKNOWN withholds complete readiness | structural | collector unit test | true |
| SP-04 | Local CLI uses GraphQL `reviewThreads`; `ccr/review_threads` only when `rest_only()` is true; neither transport exits non-zero | runtime_behavior | collector transport test | true |
| SP-05 | 778 still descends from 777 and still has head-bound finding verification plus `previous_path` overlap | repository_state | `git merge-base --is-ancestor` and diff grep | true |
| SP-06 | 786 `mergeable` is MERGEABLE and registries match the post-rebase tree | network_observation | `gh pr view 786` plus registry digest equals `git hash-object` of `skills/l9-pr-audit/SKILL.md` on that head | true |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.governance.pr-attestation-closure.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.governance.pr-attestation-closure.v1` |
| source_ref | `plan.governance.pr-attestation-closure.v1` |
| phase_id | `preflight` |
| blocking | true |
| immutable_baseline_ref | Immutable baseline |
| baseline_verified | false until execution start |
| drift_detected | false at planning time |

### Probes (min 1; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P-01 | head binding | `gh pr view 776 777 778 786 --json headRefOid` | SHAs still equal the audited heads, or stop and replan | true |
| P-02 | clean execution tree | checkout or wired worktree of the named branch | tree does not contain this planning checkout's dirty `audit-output.schema.json` | true |
| P-03 | hook catalog | read `.pre-commit-config.yaml` | catalog is the governed hook list for every commit | true |
| P-04 | sibling board | `gh pr list --state open` | more than one chain is open, so `PR_STACK=auto` is not used | true |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** the `gmp_handoff.may_modify` paths, only inside the worktree of the todo's owning branch
- **write_deny:** root additive_only files; `skills/l9-pr-remediation/scripts/protocol.py`; this planning checkout
- **delete_allow:** none

### Commands

- **allow:** scoped commits on the owning branch; `l4_local.py authorize-release`; `PR_STACK=` empty `PR_BASE=<existing base> PR_REMEDIATE=0 make pr`; `git rebase` of 778 onto the new 777 tip and of 786 onto `origin/main`; owning generators for registries, rules manifests, and `filetree.md`; pytest of the named tests
- **deny:** Do not run `make campaign`. Also denied: force-push, hard-reset, `gh pr merge`, `agent_worktree_start.sh` for a new task branch, and `git merge-tree` as the 786 cleanliness proof while `merge.l9-generated` is registered.

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | GitHub via `gh` for PR read and for `make pr` publish |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | true |

### Autonomous merge

`autonomous_merge:` `false`
**Merge for this plan** is out of scope. Publication updates the existing PRs and stops.

## Side effects and idempotency

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | filesystem_mutation | safe_to_repeat | retry_once | revert the 777 commit | false |
| T2 | filesystem_mutation | safe_to_repeat | retry_once | revert the 777 commit | false |
| T3 | external_state_mutation | unsafe_blind_repeat | manual_only | stop and keep `d8e92836` if the rebase drops 778-only repairs | false |
| T4 | filesystem_mutation | safe_to_repeat | retry_once | revert the 776 commit | false |
| T5 | external_state_mutation | unsafe_blind_repeat | manual_only | do not push a keep-ours tree; revert the 786 rebase commit | false |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | l9-pr-audit assembler | assurance | falsification ledger and audit_passes | synthesizing SURVIVED or VERIFICATION from READY |
| T2 | l9-pr-audit collector | assurance | review-replies transport table and branch-protection API | a second thread client; rulesets-only READY |
| T3 | 777 to 778 stack | assurance | parent-before-child ancestry | squash onto main |
| T4 | GAR coding delegation | assurance | `diff_is_the_delivered_change` | `git patch-id` as the equality proof |
| T5 | generated projections | ops | `.gitattributes` `merge=l9-generated` plus post-merge regeneration | hand-merge of manifest digests; copying 778's registry |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.governance.pr-attestation-closure.v1` |
| source_execution_ref | `plan.governance.pr-attestation-closure.v1` |
| supported | true |
| automatic_allowed | false |
| approval_required | true for any reset of 778 or 786 |
| trigger_conditions | checkpoint C1, C2, or C3 fails |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` | scoped revert on the owning branch |
| data | `none` | no data store |
| external_state | `manual_recovery` | a pushed bad head is reverted with a new commit, not a force-push |
| local_state | `git_restore_scoped_paths` | unpushed rebase stops before publish |

### Irreversible operations

- None inside this envelope. Force-push and squash of 778 are forbidden.

### Rollback verification

- Owning branch `git log` still contains the pre-change head, or a revert commit names it.
- 778 `git merge-base --is-ancestor` of the 777 tip still holds after a successful rebase.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | high |
| uncertainty | medium |
| blast_radius | high |
| architectural_boundaries_crossed | GAR delegation verifier, pr-audit assembler and collector, generated skill and rules projections |
| external_systems_touched | GitHub pull request mergeability |
| migration_required | false |
| unknown_dependency_count | 1 |

## Regeneration extinguishment *(optional — retirement/deprecation)*

| id | source | required_change | validation |
|----|--------|-----------------|------------|
| R-786 | post-rebase 786 tree | regenerate rules manifests, llm-rules manifest, both skill registries, and filetree.md | registries omit the three archived skill names; filetree.md header stays a non-authority projection and no longer lists those three as live |

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` / `execution_DAG_ref`

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.governance.pr-attestation-closure.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | owner | layer | depends_on | outputs |
|----|-------|-------|------------|---------|
| T1 | 777 branch | assurance | [] | assembler refuses prose SURVIVED |
| T2 | 777 branch | assurance | [T1] | collector transport and classic-protection status |
| T3 | 778 branch | assurance | [T1, T2] | child contains parent closures and keeps its own repairs |
| T4 | 776 branch | assurance | [] | exact hunk compare |
| T5 | 786 branch | ops | [] | mergeable head and regenerated projections |

**Critical path:** T1 → T2 → T3

**Forbidden edges:** T4 or T5 depending on T3; 778 published against main; any todo committing on `claude/gar-skill-bootstrap-hook-mm2oj9`

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-01 | SP-01 | runtime_behavior_evidence | in-file regression | `python3 skills/l9-global-architect/scripts/verify_coding_delegation.py` | indent and hunk-header cases are VIOLATED | not_run |
| E-02 | SP-02 | runtime_behavior_evidence | pytest | `python3 -m pytest tests/skills/l9_pr_audit/test_audit_pipeline.py -q` | prose DONE is not READY with SURVIVED and not CONVERGED | not_run |
| E-03 | SP-03 | structural_evidence | pytest | same file as E-02 | ABSENT only for the not-protected body | not_run |
| E-04 | SP-04 | runtime_behavior_evidence | pytest | same file as E-02 | GraphQL on local, ccr only when rest_only, fail closed otherwise | not_run |
| E-05 | SP-05 | repository_state_evidence | git | `git merge-base --is-ancestor <new-777> <new-778>` | ancestor relationship holds and verify- plus previous_path remain | not_run |
| E-06 | SP-06 | network_observation | gh | `gh pr view 786 --json mergeable,mergeStateStatus` | MERGEABLE, and registry digest matches that head's SKILL.md | not_run |

Hook catalog for every commit: `.pre-commit-config.yaml`.

## Stress and disconfirm

### Disconfirming cases

- Dropping only the `index` oid line still lets an indentation change or a hunk-header change compare equal.
- A final-verification JSON names the frozen head while no command ran.
- HTTP 404 without body `Branch not protected` is stored as ABSENT.
- The 778 rebase drops `verify-` head binding or `previous_path`.
- `git merge-tree --write-tree` exit 0 is treated as 786 clean while `merge.l9-generated` kept ours.

### Assumption failure conditions

- An audited head moves before execution (PLAN-SCHEMA-013). Stop and replan.
- An authorized owner re-scopes READY to mean rulesets only. Stop T2's readiness half and record the re-scope.
- This dirty planning checkout is used as the implementation tree.

### Blast radius notes

- Audits that projected READY from prose probes become UNKNOWN or NOT_READY until a head-bound verification artifact exists.
- 786 generated manifests follow the post-rebase tree. A bad generator run republishes stale digests.

### Rollback constraints

- Revert with a new commit on the owning branch.
- Do not force-push.
- A wrong 778 rebase stops before publish and leaves `d8e92836991849a266408bbacd62d638bd6c9ff2` reachable.

## Out of scope

- A new branch from origin/main
- Squash of 778 onto main
- Unwinding 778's verifier, `previous_path` overlap, or stand-alone bot lane pooling
- Copying either skill registry wholesale when 778 and 786 later share one tree
- Root additive_only files
- Merging these PRs
- Dependabot PRs 764, 765, 766, 771, and PR 791
- Architecture redesign
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners or gates to obtain PASS

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

| Field | Value |
|-------|-------|
| separate_plan_required | true |

| priority | change | why |
|----------|--------|-----|
| 1 | After 778 and 786 are both in one tree, regenerate both skill registries from that combined corpus | 778 binds l9-pr-audit digest 54912808 and 786 binds 8e3eef71. Either file copied wholesale is wrong. |

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref`

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.governance.pr-attestation-closure.v1` |
| source_ref | `plan.governance.pr-attestation-closure.v1` |
| current_state | `partial` |
| implementation_ready | true for Build on the named branches; execution evidence is not yet run |

### Gates

- **executable_when:**
  - baseline reverified at execution start
  - blocking capability probes pass
  - DAG acyclic
  - envelope and side-effect matrix complete
  - U2 remains a regeneration probe, not a hand-merge
- **complete_when:**
  - E-01 through E-06 are `passed`
  - rollback contract unused or verified
  - out_of_scope respected
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-01 E-02 E-03 E-04 E-05 E-06
- **observed_evidence_refs:** planning recheck of the four heads on 2026-10-27
- **missing_evidence:** execution results of E-01 through E-06

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| unknown | U2 | Non-header conflict hunks inside the four 786 manifests | probe by regenerating, not by hand-merging |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | C1 after T1 |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build** on the owning branch named by the todo, with `PR_STACK` empty because sibling chains fail closed, then `PR_REMEDIATE=0 make pr` and display that PR URL — do not free-form execute |
| execute_via | Cursor Build; one existing PR branch per todo; display that PR URL |
| broader_work_requires_separate_contract | true for the combined 778 plus 786 registry regeneration |
