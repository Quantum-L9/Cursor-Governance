---
name: Remediator max-velocity
overview: Make `/l9-pr-remediation` honor maximum_velocity and mechanically enforce one census → one commit → one CI run per PR. This run’s slowness was not `make pr`; it was a 10-lane cap, a watch loop that did not re-poll an UNKNOWN merge_state to a decision, catch-up-instead-of-fix, and prose-only one-and-done. UNKNOWN stays fail-closed (board=WAIT); polling resolves it, never conversion.
todos:
  - id: pe-lock-baseline
    content: "W0: isolated worktree from origin/main; prefetch; Program Lock; stop if HEAD drifts. No product edits."
    status: completed
  - id: lift-skill-cap
    content: "W1a: pr_fleet.skill_caps pass-through + validate_max_velocity ratchet + skill/test needles. Parallel with W1b."
    status: in_progress
  - id: board-unknown-behind
    content: "W1b: pr_board.decide fail-closed: UNKNOWN merge_state + green required = WAIT (watch loop re-polls); failing required before BEHIND = FIX naming the check; keep UNKNOWN-waits test, add red-CI+BEHIND test. Parallel with W1a."
    status: in_progress
  - id: ingest-complete-one-commit
    content: "W1c: ingest auto-Sonar; validate_plan --findings required; Gate E git log; cycle-2 reject; activation cases. After W1a+W1b."
    status: pending
  - id: remediator-verify-isolation
    content: "W1d: L9_REMEDIATOR skips PR_STACK=auto; ban merge-main as CI fix; assign --record before launch. After W1c."
    status: pending
  - id: pack-prove
    content: "W2: self_test + validators + targeted pytest. Then L4 authorize-release and PR_STACK=auto PR_REMEDIATE=0 make pr. No merge from this plan."
    status: pending
isProject: false
kernel_pass:
  bound_path: remediator_max-velocity_ca77e43f.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-09-14T16:49:07Z
    deltas:
      - ff_shelf corpus pass
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-09-14T16:49:08Z
    deltas:
      - ff_shelf corpus pass
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-09-14T22:33:32Z
    body_sha256: "8cad3acfe85a8c2066184737b172f8db0ec4115d2062bb7361d7f2d4b9facc75"
    deltas:
      - ff_shelf corpus pass
      - F-01: pr_board UNKNOWN merge_state is fail-closed (WAIT + re-poll); MERGE conversion removed from every line
---

# Remediator one-commit max-velocity

## How this plan is executed

This is a **PE+autonomy landing**, not a remediator run and not a chat-mutate. The remediator *runtime* stays no-campaign. **This change** is a skill-pack + autonomy-brain landing on a **new branch from `origin/main`**.

```text
this plan
  -> isolated worktree off fetched origin/main
  -> @environment/program-execution  (Blueprint -> Program Lock -> Controller)
  -> subordinate @autonomy / l9-bounded-autonomy under that lease
  -> adapter cursor-foreground
  -> scoped commits on the declared branch
  -> L4 authorize-release
  -> PR_STACK=auto PR_REMEDIATE=0 make pr
  -> stop (do not merge; do not invoke /l9-pr-remediation on leftover PRs)
```

**Live PE command (do not hand-run pec / inner compile scripts):**

```bash
bash "$HOME/.cursor-governance/ops/scripts/agent_worktree_start.sh" \
  --agent-id remediator-max-velocity \
  --task-id rem-mv
make -C "$HOME/.cursor-governance" campaign \
  INTENT="$PWD/docs/plans/remediator_max-velocity_ca77e43f.plan.md"
```

If the user presses **Build**, follow the same envelope, file lists, DAG, and verify/publish verbs. Do not invent a third path.

**Branch:** `feat/remediator-max-velocity-one-commit` from the worktree authorized base. Never mix onto `chore/wip-corpus-*` or the dirty primary clone.

**Publish:**

```bash
"$PWD/.venv/bin/python" ops/autonomy/l4_local.py begin --contract-id remediator-max-velocity
"$PWD/.venv/bin/python" ops/autonomy/l4_local.py authorize-release
PR_STACK=auto PR_REMEDIATE=0 make pr
```

**Stop / do not execute when:** shared dirty clone; Program Lock drift; capability preflight blocked; a forbidden path is required; Build would edit `.github/workflows/**` or `stack_safe_merge.py`.

## Must do

- New branch from fetched `origin/main` (or unique stack tip). Rule 46. Pathspecs only.
- Caps = execution profile (`max_parallel>=480`, `max_mutation_lanes>=128`). Safety is `claim_scopes_conflict` + `waves()`, not 10.
- One-and-done is mechanical: complete ingest before first edit; Gate E reads `git log`; cycle 2 rejected for plan-time finding ids.
- `pr_board.decide` is fail-closed on merge_state: green required + `UNKNOWN` → `wait` ("GitHub has not finished computing mergeability"); the watch loop re-polls until the fact resolves — polling, not conversion. Failing required checks **before** BEHIND → FIX naming the check.
- Verify is exactly `L9_REMEDIATOR=1 PR_STACK= PR_BASE=origin/main make precommit-repo`.
- `L9_REMEDIATOR=1` skips `pr_stack_apply_publish_base`.
- After `plan --board`, first status line is `merge_order` + `merge_now` + wave sizes.
- AGENTS.md append-only. Regen via `sync_generated_artifacts.py --force`.
- `autonomous_merge: false`. Do not merge this landing PR. Do not remediator-merge 571/576/580.

## Must not do

- Keep `SKILL_SUBAGENT_CAP = 10`. Invent a second scheduler. Edit `stack_safe_merge.py`, `execution_profile.py`, `resolve_pr_stack.sh`, Makefile, workflows, `CANONICAL_LAW.md`.
- Teach `git merge origin/main` as a CI fix. Convert an `UNKNOWN` merge_state into `merge` under any check evidence — UNKNOWN resolves only by re-poll. Flip or weaken `test_unknown_merge_state_waits`; weaken tests to keep first-wave=10.
- Remediator-push leftover PRs. `--admin`, force-push, `--no-verify`. Implement on `rem-pr-*` worktrees.

## Files to touch

### W1a — cap lift

- [ops/autonomy/pr_fleet.py](ops/autonomy/pr_fleet.py): delete `SKILL_SUBAGENT_CAP = 10`; `skill_caps()` pass-through; `_objective` verify gets `PR_STACK=`; watch until `board=merge`; `assign --record` fail-closed if `.l9/pr/assignments/` missing
- [ops/scripts/validate_max_velocity.py](ops/scripts/validate_max_velocity.py): fail if remediator clamps below profile floors
- [tests/ops/autonomy/test_pr_fleet.py](tests/ops/autonomy/test_pr_fleet.py): 12 independent PRs → 12 remediations
- [skills/l9-pr-remediation/SKILL.md](skills/l9-pr-remediation/SKILL.md) bump past 5.4.0; delete `skill_subagent_cap: 10`; delete poll-until-CLEAN
- [skills/l9-pr-remediation/references/fleet-waves.md](skills/l9-pr-remediation/references/fleet-waves.md), [run-contract.md](skills/l9-pr-remediation/references/run-contract.md), [self_test.py](skills/l9-pr-remediation/scripts/self_test.py), [expertise_model.yaml](skills/l9-pr-remediation/expertise_model.yaml), [skill_intelligence_report.yaml](skills/l9-pr-remediation/skill_intelligence_report.yaml)
- [AGENTS.md](AGENTS.md) append-only fragment

### W1b — board

- [ops/autonomy/pr_board.py](ops/autonomy/pr_board.py) `decide()`: failing required before BEHIND → FIX naming the check; UNKNOWN merge_state + green required → WAIT with reason "GitHub has not finished computing mergeability" (fail-closed; the watch loop re-polls)
- [tests/ops/autonomy/test_pr_board.py](tests/ops/autonomy/test_pr_board.py): keep `test_unknown_merge_state_waits` (UNKNOWN → wait is the contract); add red-CI+BEHIND → FIX naming the check; keep `test_no_evidence_at_all_waits`

### W1c — census + one commit

- [ingest_signals.py](skills/l9-pr-remediation/scripts/ingest_signals.py): auto Sonar when `sonar-project.properties` exists
- [validate_plan.py](skills/l9-pr-remediation/scripts/validate_plan.py) + [protocol.py](skills/l9-pr-remediation/scripts/protocol.py): `--findings` required; cycle-2 reject plan-time ids; Gate E `git log`
- [gate_receipt.py](skills/l9-pr-remediation/scripts/gate_receipt.py), [remediation-plan.md](skills/l9-pr-remediation/references/remediation-plan.md), [signal-ingestion.md](skills/l9-pr-remediation/references/signal-ingestion.md), [activation_cases.json](skills/l9-pr-remediation/scripts/activation_cases.json), [test_protocol.py](tests/skills/l9_pr_remediation/test_protocol.py)

### W1d — remediator verify

- [ops/scripts/run_pr_precommit.sh](ops/scripts/run_pr_precommit.sh): skip stack-tip when `L9_REMEDIATOR=1`
- [generated-heal.md](skills/l9-pr-remediation/references/generated-heal.md), [fix-engine.md](skills/l9-pr-remediation/references/fix-engine.md), [merge-advise.md](skills/l9-pr-remediation/references/merge-advise.md)

### W2

- Generated companions only via `sync_generated_artifacts.py --force`

## Files not to touch

- `ops/autonomy/stack_safe_merge.py`, `merge_gate.py`, `first_publication_gate.py`, `execution_profile.py`, `claude-execution-profiles.json`
- `ops/scripts/lib/resolve_pr_stack.sh`, `ops/scripts/resolve_stack_tip.py`
- `Makefile`, `ops/autonomy/surface_profile.yaml`, `CANONICAL_LAW.md`, `.github/workflows/**`
- `environment/program-execution/core/**`, `pyproject.toml`, `requirements.txt`, `conftest.py`, `.pre-commit-config.yaml`
- `skills/l9-repo-birth/**`, leftover remediator worktrees/PRs, `WIP/**`, `TODO.md`, historical AGENTS.md paragraphs

## Commands allowed vs denied

**Allowed:** isolated worktree; scoped commit; gov venv python; pack self_test / validate_skill_pack / validate_exemplary_skill; targeted pytest listed above; sync_generated_artifacts --force; l4 begin/authorize-release; `PR_STACK=auto PR_REMEDIATE=0 make pr` once after prove; `make campaign INTENT=<this plan>`.

**Denied:** mid-todo `make pr` / `make pr-check`; remediator push/merge of 571/576/580; `gh pr merge`; `--admin`; force-push; `git merge origin/main` on leftover branches; `--no-verify`; `uv pip install` past lock.

## Execution DAG

```mermaid
flowchart TD
  w0["W0 pe-lock-baseline"]
  w1a["W1a lift-skill-cap"]
  w1b["W1b board-unknown-behind"]
  w1c["W1c ingest-complete-one-commit"]
  w1d["W1d remediator-verify-isolation"]
  w2["W2 pack-prove + make pr"]
  w0 --> w1a
  w0 --> w1b
  w1a --> w1c
  w1b --> w1c
  w1c --> w1d
  w1d --> w2
```

- W0: no product mutation.
- W1a and W1b: parallel Tasks. W1b does not edit SKILL.md. W1a removes cap-10 needles; W1c writes remaining Law 15 / ingest / verify sentences.
- W2: verify + ceremony publish. `autonomous_merge: false`.

## Capability preflight (W0)

Isolated clean worktree; HEAD is authorized base; gov venv imports yaml; MEMORY_PREFETCH cited; `.pre-commit-config.yaml` named not rewritten.

## Why (kept short)

User corrections: one-line CI loops; no parallelism; merge order invisible; sitting on green 570 through UNKNOWN without re-polling it to a decision; catch-up on 576 instead of fixing the test.

Code owners: `SKILL_SUBAGENT_CAP=10`; Gate E self-attested; ingest scanners opt-in; `decide()` orders BEHIND before failing checks (UNKNOWN→wait itself is correct and stays); remediator verify inherits `PR_STACK=auto`; generated-heal teaches `git merge origin/main`.

Previous speed plan already removed `make pr` from remediator publish. Do not redo that.

## Success properties

- SP-01: `skill_caps()` parallel ≥ 480 and mutation ≥ 128. Twelve independent PRs launch twelve remediations.
- SP-02: green required + `UNKNOWN` merge_state → `board=wait` ("GitHub has not finished computing mergeability") and the watch loop re-polls to a decision; `merge` needs a computed mergeable state. Red required + `BEHIND` → FIX naming the check, not catch-up.
- SP-03: ingest without `--sonar` still emits Sonar ids when `sonar-project.properties` exists. Converge `validate_plan` without `--findings` is FAIL.
- SP-04: Gate E FAIL on two remediator commits whose finding ids ⊆ plan-time ingest.
- SP-05: `L9_REMEDIATOR=1 make precommit-repo` does not call `pr_stack_apply_publish_base`.
- SP-06: W2 commands Passed. Landing PR URL printed.

## Envelope

- fs write: Files to touch only
- fs deny: Files not to touch
- `autonomous_merge: false`

## Rollback

Revert the feature branch.

## After this PR merges — not this Build

Re-invoke `/l9-pr-remediation` for leftover open PRs.

## Campaign packet stub

```yaml
packet_id: autonomy-2026-09-14-remediator-max-velocity
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
autonomous_merge: false
plan_ref: docs/plans/remediator_max-velocity_ca77e43f.plan.md
declared_branches: [feat/remediator-max-velocity-one-commit]
forbidden_inside_packet:
  - merge_outside_l4_plan_build_stack
  - force_push
  - admin_merge
  - expand_scope
  - remediate_leftover_open_prs
```
