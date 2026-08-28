---
name: Cut l9-ci-core v2 tags and close remaining issues
status: superseded
built: true
overview: "SUPERSEDED 2026-08-28. Consumer and pack workflows SHA-pinned install-consumer-ci; do not cut v2 to unblock CI. Issues 112/98/24 remain open as residual docs, not a live Set-up-job 404."
todos:
  - id: todo-01-baseline-preflight
    content: "Re-lock origin/main full SHA and confirm v2 plus v2.0.0 are still absent before any tag push"
    status: cancelled
    phase: preflight
    depends_on: []
    evidence_property_refs: [SP-01]
  - id: todo-02-human-cut-release
    content: "Human with tag push rights runs bash docs/release/tag-and-release.sh from an l9-ci-core clone at the locked origin/main SHA"
    status: cancelled
    phase: execute
    depends_on: [todo-01-baseline-preflight]
    side_effect_ref: SE-todo-02
    evidence_property_refs: [SP-01, SP-02]
  - id: todo-03-prove-tags
    content: "Prove v2 and v2.0.0 resolve install-consumer-ci and record release-validation status"
    status: cancelled
    phase: validate
    depends_on: [todo-02-human-cut-release]
    evidence_property_refs: [SP-02, SP-03, SP-05]
  - id: todo-04-close-remaining
    content: "Close issues 112, 98, and 24 with tag SHA evidence; close PR 114 without merge as superseded"
    status: cancelled
    phase: converge
    depends_on: [todo-03-prove-tags]
    evidence_property_refs: [SP-04]
  - id: todo-05-breadcrumb
    content: "Write Graphiti PICKUP for the v2 release cluster after closeout"
    status: cancelled
    phase: converge
    depends_on: [todo-04-close-remaining]
    evidence_property_refs: [SP-04]
isProject: false
kind: pe
execute_via: pe-campaign
kernel_pass:
  bound_path: l9_ci_core_v2_release_8-23-26.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-28T18:45:00Z
    body_sha256: "af9ace95efa80fe99b3d9a3e445cec7c932ec5e78bb5ed14dcae541d3cb36be5"
    deltas:
      - "Marked superseded after 2026-08-28 evidence: main moved off 7148fc73, PR 114 merged, pack and Core workflows SHA-pin install-consumer-ci"
      - "Cancelled all execute todos; tag cut is no longer the consumer unblock"
      - "Recorded residual open issues 112/98/24 and still-absent v2 tags as docs/contract leftover"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-28T18:46:00Z
    body_sha256: "af9ace95efa80fe99b3d9a3e445cec7c932ec5e78bb5ed14dcae541d3cb36be5"
    deltas:
      - "Replaced executable tag-cut instructions with stop_and_replan / do-not-Build guidance"
      - "Aligned success properties and envelope with SHA-pin reality; PR 114 already merged"
      - "Stamped kernel_pass after Improve then Validate and Repair"
---

# SUPERSEDED — do not Build or campaign this packet

Re-verified **2026-08-28**. The 2026-08-23 mission (cut `v2` / `v2.0.0` at `7148fc73` to stop consumer Set-up-job 404s; do not merge PR 114) is **stale**.

Live installer refs moved to a full SHA. Tags were never cut. Open issues 112 / 98 / 24 are leftover paperwork, not a current CI unblock.

Do **not** run `make campaign` on this file. Do **not** cut tags at the old locked SHA.

## Freshness evidence (2026-08-28)

| Claim in the original plan | Observed now |
|---|---|
| `origin/main` = `7148fc73dcbf41367f5c5401432dc997b1f4f869` | **Drift.** `main` = `450f6ec753435365c6e4212cc898ee9ba560bb7d` (2026-08-28T16:17:39Z, PR #120) |
| Do not merge PR 114 | **Already merged** 2026-08-24T11:44:14Z as `6ea607807ebf34e41c0494ff035ba4d13bbb01d2` |
| Cut `v2` + `v2.0.0` to unblock `@v2` consumers | Tags still **absent**. Core `pr-pipeline.yml`, python preset/starter/template, and `.github` `l9-ci-pack/workflows/l9-lint-test.yml` call `install-consumer-ci@7148fc73dcbf41367f5c5401432dc997b1f4f869` |
| `gh search code install-consumer-ci@v2 --filename '*.yml'` | **Empty** under Quantum-L9 (docs/tests/READMEs still name `@v2`) |
| Issues 112 / 98 / 24 still the live defect | Still **OPEN**. #57 stays closed. #112 comment 2026-08-27 still describes the old `@v2` 404 |

Original on_drift rule was `stop_and_replan`. That rule fired.

## Residual (not this campaign)

- Tags `v2` / `v2.0.0` and Release `v2.0.0` still do not exist.
- Core tests/docs (`tests/workflows/test_python_mypy_contract.py` `INSTALLER = "install-consumer-ci@v2"`, `presets/python/README.md`, `.github` pack README, `sync-v2-starters.sh` comments) still describe the floating-major contract.
- Closing 112 / 98 / 24 as superseded by the SHA-pin, or later cutting `v2` for docs-only, needs a **new** plan. This file is not that plan.

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
```

**This packet is not executable.** Status is `superseded`. If a runner is pointed at this file, stop and report stale baseline. Do not admit a Program Lock. Do not cut tags. Do not merge or revert PR 114 from this plan.

### Pipeline steps

```bash
# Do not run. Historical only:
# make -C "$HOME/.cursor-governance" campaign INTENT=docs/plans/l9_ci_core_v2_release_8-23-26.plan.md
```

### Campaign authorization packet

```yaml
packet_id: autonomy-2026-08-28-l9-ci-core-v2-superseded
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
autonomous_merge: false
plan_ref: docs/plans/l9_ci_core_v2_release_8-23-26.plan.md
plan_id: plan.l9-ci-core.v2-release.v1
status: superseded
forbidden_inside_packet:
  - execute_this_plan
  - cut_v2_at_7148fc73
  - revert_or_reopen_pr_114_from_this_packet
```

### Phase-0 action table

All Task Cards cancelled. No wave is admitted.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.l9-ci-core.v2-release.v1` |
| schema_version | `1.0.0` |
| status | `superseded` |
| created_at | `2026-08-23` |
| updated_at | `2026-08-28` |
| owner | Quantum-L9/l9-ci-core maintainers |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | Live `Quantum-L9/l9-ci-core` `main` @ `450f6ec753435365c6e4212cc898ee9ba560bb7d` |
| plan_class | `deployment_plan` (retired) |
| redesign_allowed | `false` |
| framing_notes | Org moved installer callers to SHA pin. Floating `@v2` is docs residue. |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-08-28T18:40:00Z` (re-verify; original capture 2026-08-24 is stale) |
| repository | `Quantum-L9/l9-ci-core` |
| branch | `main` |
| commit_sha | `450f6ec753435365c6e4212cc898ee9ba560bb7d` |
| original_lock | `7148fc73dcbf41367f5c5401432dc997b1f4f869` (installer pin SHA; not current HEAD) |
| dirty | unknown on local clones |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` — already triggered |

Tags still: `v0.1.0`, `v1`, `v1.0.0`. Absent: `v2`, `v2.0.0`.

## Objective

### Mission (original, no longer live)

Cut `v2.0.0` + `v2` so `install-consumer-ci@v2` resolves. That was the 2026-08-23 defect.

### Mission (now)

Do not execute. Treat this plan as a closed record. Residual issue-close or a real `v2` publish is a separate contract.

### Success properties (historical; not in force)

| id | property | evidence_type | proof | blocking | 2026-08-28 |
|----|----------|---------------|-------|----------|------------|
| SP-01 | Locked SHA; tags absent until cut | `repository_state` | `gh api` tags + `commits/main` | was true | **Failed as written** — HEAD moved; tags still absent |
| SP-02 | Tags exist at locked SHA | `network_observation` | `git/ref/tags/v2` | was true | **not met** — 404 |
| SP-03 | GitHub Release `v2.0.0` | `quality_gate` | `gh release view` | was true | **not met** |
| SP-04 | Close 112/98/24; close 114 unmerged | `network_observation` | `gh issue/pr view` | was true | **Failed as written** — 114 merged; issues still open |
| SP-05 | Seeded `@v2` consumer Set up job | `runtime_behavior` | consumer Actions | was true | **Bypassed** — live yml callers use SHA `7148fc73` |

## Capability preflight

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.l9-ci-core.v2-release.v1` |
| baseline_verified | no — original lock drifted |
| drift_detected | **yes** |

CP-01 fail-closed on SHA drift. No further capability is required for a superseded plan.

## Execution envelope

Mutations from this plan are **forbidden**.

- **write_allow:** none
- **write_deny:** all product trees, all tag refs, PR 114 history
- **commands deny:** `tag-and-release.sh` invoked because of this file; `make campaign` on this INTENT
- **autonomous_merge:** `false`

## Side effects and idempotency

No mutating todo remains admitted. Historical SE-todo-02 (tag push) must not be replayed from this packet.

## Architecture impact

None from this file. The live architecture change already landed: SHA-pin via PR 114, later Core HEAD `450f6ec`.

## Rollback

Not applicable to a superseded no-op. Do not delete consumer SHA pins to restore `@v2`.

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `low` |
| uncertainty | `low` for "is this packet stale" (confirmed). Medium for whether to still publish `v2` later. |
| blast_radius | `high` if someone still force-cuts tags at the old SHA |
| unknown_dependency_count | `0` for this packet |

## Execution DAG

Cancelled. Critical path is empty.

## Property evidence matrix

| evidence_id | SP | status 2026-08-28 |
|-------------|----|-------------------|
| EV-SP-01 | SP-01 | `failed` vs original lock; current HEAD recorded |
| EV-SP-02 | SP-02 | `failed` — no `v2` ref |
| EV-SP-03 | SP-03 | `failed` — no release |
| EV-SP-04 | SP-04 | `failed` as written (114 merged; issues open) |
| EV-SP-05 | SP-05 | `bypassed` — yml callers SHA-pinned |

## Stress and disconfirm

- Did every consumer move, or only the pack + Core copies? `gh search code install-consumer-ci@v2 --filename '*.yml' --owner Quantum-L9` returned no hits. Residual `@v2` is markdown/tests/scripts.
- Would cutting `v2` at current `main` (`450f6ec`) still be useful? Only as a docs/test contract, not as a CI unblock. Separate plan if a maintainer wants that.
- Could `#112` still be true for an un-reseeding old branch? Yes, any leftover workflow still on `@v2` 404s. That is not this campaign.

## Out of scope

- New `v2` tag campaign
- Closing 112 / 98 / 24
- Reverting PR 114
- Fleet SHA-pin of analysis/SDK actions
- `.github` seeder clobber

## Convergence

| Field | Value |
|-------|-------|
| current_state | `superseded` |
| implementation_ready | `false` |
| next_convergence_gate | none on this file |
| minimum_safe_next_action | Do not Build. Optional new plan only if a human wants tags or issue closeout. |
| execute_via | `@environment/program-execution` is the standing pipeline; this INTENT must not be admitted |

```yaml
execute_via:
  pipeline: environment/program-execution
  mention_program: "@environment/program-execution"
  slash: /autonomy
  skill: l9-bounded-autonomy
  admit_this_intent: false
  authority_order:
    - plan_document
    - program_lock_and_controller
    - autonomy_packet_subordinate
```
