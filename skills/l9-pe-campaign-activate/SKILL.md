---
name: l9-pe-campaign-activate
description: invoke make campaign INTENT= as the only live PE campaign front door. use when the user asks to activate a campaign, run a pe campaign, compile campaign source, emit campaign seeds, or take a brief through COMPLETED. do not call pec, the intent compiler, or inner compile/accept scripts as a substitute.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, program-execution, campaign, compiler, activate, merge]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-08-16
---

# PE Campaign Activate

## Purpose

Run the one PE campaign tunnel. The only live invocation is
`make campaign INTENT=`. The runner emits the allowed file set, admits the
blueprint, executes every task, opens stacked PRs, remediates those PRs, and
closes into `campaigns/COMPLETED/<id>/`.

Invoking this skill **is** merge authorization for the single campaign PR this
run opens. It is not merge authorization for any other PR.

Invoking **`/l9-pr-remediation`** separately authorizes ordinary merge of all
open PRs in the target repo after they are green and mergeable. Receipt writer
SSOT: `ops/autonomy/authorize_merge.py`. Wrapper:
[scripts/authorize_campaign_merge.py](scripts/authorize_campaign_merge.py).

## Core Contract

| Item | Value |
|---|---|
| Emit set | exactly the files in [references/file-set.md](references/file-set.md) |
| Stack proof | runner-owned `$HOME/.l9/primed/<id>/stack-proof.json` before emit/blueprint |
| Brief IR | [scripts/compile_brief.py](scripts/compile_brief.py) — memo `.md` → activate seed |
| Compiler | [scripts/compile_activation_files.py](scripts/compile_activation_files.py) |
| Pipeline | [references/pipeline.md](references/pipeline.md) |
| Merge | [references/merge-authority.md](references/merge-authority.md) |
| Isolation | new worktree from `origin/main`; never the dirty primary clone |
| Publish | runner pushes `campaign/<id>` before execute; task PRs stack on that remote base |
| Remediate | `l9-pr-remediation` Converge, max 5 cycles, then merge that PR |
| Forbidden extras | README, handoff, `INTENT.yaml`, `CONTRACT_SOURCE.md`, `PROGRAM_SOURCE.md`, alignment overlays |

## Authority Order

1. Explicit user campaign id / objective / this skill invocation
2. `environment/program-execution` schemas + `compile_campaign_source.py`
3. `CAMPAIGN_EXECUTION_POLICY.yaml` + `ops/autonomy/surface_profile.yaml`
4. This skill + references
5. `l9-pr-remediation` for the opened PR only
6. `Unknown` — fail closed; do not invent campaign ids, targets, or extra files

## Compact Workflow

1. One command. No other front door.

   ```bash
   make -C "$HOME/.cursor-governance" campaign INTENT=/path/to/brief.md
   ```

   Stay inside that process. Do not call pec, `compile_campaign_source.py`,
   `compile_activation_files.py`, `accept_blueprint.py`, or
   `program-execution intent` as a follow-up. If the runner exits nonzero,
   stop and report its output.
2. Live SSOT after arm is `$HOME/.l9/programs/<id>/runtime/LAUNCH.json` plus
   the 15-minute task cards and `STACK.json`. The runner stacks each task PR
   on the previous task branch. Never `PR_BASE=main`. Do not open the
   operator memo.
3. If a STACK.json PR is red, remediate that recorded PR only. Do not start
   a parallel pec workspace or a new campaign id.
4. Close is a runner stage. Do not run `pec close` or `close_campaign.py`
   yourself unless the runner already failed and you are reporting that fail.

## MUST

- Emit only the allowed file set. Delete any extra file you created by mistake.
- Keep `CAMPAIGN_SOURCE.yaml` schema-valid and PE-compiler-admissible.
- Land work on `campaign/<campaign_id>`. Stack each task PR on the previous
  task branch from `STACK.json`. Never open a campaign PR against `main`.
- Use `make pr` (not raw `gh pr create`).
- Merge only after remediation is complete on the observed head SHA.
- Write the one-shot merge authorization file before `gh pr merge` so
  `ops/autonomy/merge_gate.py` allows that one PR.

## MUST NOT

- Emit README, handoff receipts, `INTENT.yaml`, contract/program prose, or alignment YAML
- Run `program-execution intent` or bootstrap a `pe-<hash>` workspace
- Mix this campaign onto another feature branch or the primary dirty clone
- Use `pec --admission-draft` as a live campaign path
- Force-push, admin-merge, hard-reset, or merge a different PR
- Set `program.definition_status: accepted` without evidence
- Weaken tests, skip hooks, or rewrite `CAMPAIGN_SOURCE.yaml` after the receipt is bound
- Treat an L4 release receipt as merge authority — this skill's merge step is separate

## Resource Map

- [references/file-set.md](references/file-set.md) — allowed vs forbidden files
- [references/source-contract.md](references/source-contract.md) — intent + seed fields
- [references/pipeline.md](references/pipeline.md) — PE compile / bootstrap / execute / PR
- [references/merge-authority.md](references/merge-authority.md) — post-remediation merge
- [scripts/compile_brief.py](scripts/compile_brief.py)
- [scripts/compile_activation_files.py](scripts/compile_activation_files.py)
- [scripts/authorize_campaign_merge.py](scripts/authorize_campaign_merge.py)
- [scripts/test_compile_brief.py](scripts/test_compile_brief.py)
- [scripts/test_compile_activation_files.py](scripts/test_compile_activation_files.py)

## Validation

Before claiming the campaign finished:

- [ ] The only command you ran to drive the campaign was `make campaign INTENT=`
- [ ] Runner exit 0 and `stages_completed` includes `close`
- [ ] Host `campaigns/<id>/` is gone; `campaigns/COMPLETED/<id>/` exists
- [ ] pec `runtime_status` is `completed` and `admission_draft` is false
- [ ] `PHASE0_USER_CONFIG.yaml` `operator_ack.acknowledged_at` is still null
      unless Igor acknowledged it
- [ ] Every PR on `STACK.json` is the PR the runner opened (never against main)

## Failure Handling

- Memo with no numbered Release / program-ordering items → STOP; do not invent tasks
- Missing activate-YAML `campaign_id` / objective / tasks → STOP; ask
- Runner FAIL on compile/validate/bootstrap → fix the seed or report; do not
  hand-edit the Blueprint; do not retry with `--admission-draft`; do not
  continue in L4 or pec outside the runner
- Remediation max cycles on a STACK.json PR → report remaining blockers
- Dirty shared clone → the runner isolates a worktree; do not `git switch`
