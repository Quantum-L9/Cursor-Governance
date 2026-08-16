---
name: l9-pe-campaign-activate
description: compile only the files required to activate a program execution campaign, run the pe compile/bootstrap/execute pipeline with maximum autonomy, remediate the campaign pr, and merge after remediation is complete. use when the user asks to activate a campaign, compile campaign source, emit campaign seeds, or run a pe campaign through compile, bootstrap, pr, remediate, and merge.
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

Compile **only** the files that activate a Program Execution campaign, then run
that campaign through `environment/program-execution` with maximum autonomy:
L4 local execution, campaign-branch PR, `l9-pr-remediation` Converge, then
**authorized merge** of that PR once remediation is complete.

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
| Brief IR | [scripts/compile_brief.py](scripts/compile_brief.py) — memo `.md` → activate seed |
| Compiler | [scripts/compile_activation_files.py](scripts/compile_activation_files.py) |
| Pipeline | [references/pipeline.md](references/pipeline.md) |
| Merge | [references/merge-authority.md](references/merge-authority.md) |
| Isolation | new worktree from `origin/main`; never the dirty primary clone |
| Publish | `PR_BASE=origin/campaign/<id> make pr` (Makefile checkers) |
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

   That runner assigns the id, emits the file set, collects EVID-001, accepts
   the blueprint, bootstraps pec **without** `--admission-draft`, reconciles
   a clean target checkout, drafts and claims TASK-001, then opens/merges
   the host PR when green. A leftover pec workspace is quarantined.
2. Read **only** `$HOME/.l9/programs/<id>/runtime/TASK-001.md` (15 minutes).
   Do not open the operator memo. Do not attach to `pe-<hash>`. If blocked,
   stop and report.
3. Converge the campaign PR with `l9-pr-remediation` until required checks are
   green and the PR is mergeable.
4. Authorize and merge **that PR only**
   ([references/merge-authority.md](references/merge-authority.md)).
5. Close the live ledger: `pec close` and
   `python3 environment/program-execution/campaigns/scripts/close_campaign.py close`.

## MUST

- Emit only the allowed file set. Delete any extra file you created by mistake.
- Keep `CAMPAIGN_SOURCE.yaml` schema-valid and PE-compiler-admissible.
- Land work on `campaign/<campaign_id>`. Never open this campaign's PR against `main`.
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

Before claiming the campaign is activated:

- [ ] `compile_activation_files.py` exit 0; printed paths match the allowed set
- [ ] no forbidden extras under `campaigns/<id>/`
- [ ] `compile_campaign_source.py` succeeds against `$HOME/.l9/blueprints/<id>`
- [ ] `validate_blueprint --mode template` PASS
- [ ] campaign id present in allowlist, execution policy, surface profile, and status ledger
- [ ] `make campaign` left host `lifecycle: in_progress` and pec `runtime_status: active`
- [ ] pec `admission_draft` is false and TASK-001 `runtime_state` is `LEASED`
- [ ] `PHASE0_USER_CONFIG.yaml` `operator_ack.acknowledged_at` is still null unless Igor acknowledged it
- [ ] campaign PR is green + mergeable, then merged
- [ ] `CAMPAIGN_STATUS.yaml` closed (`complete`) after merge

## Failure Handling

- Memo with no numbered Release / program-ordering items → STOP; do not invent tasks
- Missing activate-YAML `campaign_id` / objective / tasks → STOP; ask
- Schema or PE compile fail → fix the seed; do not hand-edit the Blueprint
- Template validate fail → fix source; do not weaken the validator
- pec bootstrap refuses draft → expected; continue L4 on `campaign/<id>`
- Remediation max cycles → report remaining blockers; do not merge
- Merge gate deny → re-run `authorize_campaign_merge.py` for this repo/PR only
- Dirty shared clone → create a worktree; do not `git switch`
