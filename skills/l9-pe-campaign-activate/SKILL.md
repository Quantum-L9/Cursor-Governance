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
  version: 1.0.0
  updated: 2026-08-15
---

# PE Campaign Activate

## Purpose

Compile **only** the files that activate a Program Execution campaign, then run
that campaign through `environment/program-execution` with maximum autonomy:
L4 local execution, campaign-branch PR, `l9-pr-remediation` Converge, then
**authorized merge** of that PR once remediation is complete.

Invoking this skill **is** merge authorization for the single campaign PR this
run opens. It is not merge authorization for any other PR.

## Core Contract

| Item | Value |
|---|---|
| Emit set | exactly the files in [references/file-set.md](references/file-set.md) |
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

1. Collect `campaign_id`, `title`, `objective`, owner, target, and tasks
   ([references/source-contract.md](references/source-contract.md)).
2. Open an exclusive worktree from `origin/main`. Do not mutate a dirty shared clone.
3. Emit the file set:

   ```bash
   python3 skills/l9-pe-campaign-activate/scripts/compile_activation_files.py \
     --intent <intent.yaml> --repo-root "$(pwd)"
   ```

4. Run the PE pipeline in [references/pipeline.md](references/pipeline.md):
   allowlist compile → template validate → pec bootstrap (draft-honest) →
   L4 execute ready tasks → kernels → `authorize-release`.
5. Publish: `PR_BASE=origin/campaign/<id> make pr`.
6. Converge that PR with `l9-pr-remediation` until required checks are green
   and the PR is mergeable.
7. Authorize and merge **that PR only**
   ([references/merge-authority.md](references/merge-authority.md)):

   ```bash
   python3 skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py \
     --repo <owner/repo> --pr <n> \
     --reason "l9-pe-campaign-activate remediation complete"
   gh pr merge <n> --squash --delete-branch
   ```

8. Close the live ledger: `pec close` and
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
- Mix this campaign onto another feature branch or the primary dirty clone
- Force-push, admin-merge, hard-reset, or merge a different PR
- Set `program.definition_status: accepted` without evidence
- Weaken tests, skip hooks, or rewrite `CAMPAIGN_SOURCE.yaml` after the receipt is bound
- Treat an L4 release receipt as merge authority — this skill's merge step is separate

## Resource Map

- [references/file-set.md](references/file-set.md) — allowed vs forbidden files
- [references/source-contract.md](references/source-contract.md) — intent + seed fields
- [references/pipeline.md](references/pipeline.md) — PE compile / bootstrap / execute / PR
- [references/merge-authority.md](references/merge-authority.md) — post-remediation merge
- [scripts/compile_activation_files.py](scripts/compile_activation_files.py)
- [scripts/authorize_campaign_merge.py](scripts/authorize_campaign_merge.py)
- [scripts/test_compile_activation_files.py](scripts/test_compile_activation_files.py)

## Validation

Before claiming the campaign is activated:

- [ ] `compile_activation_files.py` exit 0; printed paths match the allowed set
- [ ] no forbidden extras under `campaigns/<id>/`
- [ ] `compile_campaign_source.py` succeeds against `$HOME/.l9/blueprints/<id>`
- [ ] `validate_blueprint --mode template` PASS
- [ ] campaign id present in allowlist, execution policy, surface profile, and status ledger
- [ ] campaign PR is green + mergeable, then merged
- [ ] `CAMPAIGN_STATUS.yaml` closed (`complete`) after merge

## Failure Handling

- Missing `campaign_id` / objective / at least one task → STOP; ask
- Schema or PE compile fail → fix the seed; do not hand-edit the Blueprint
- Template validate fail → fix source; do not weaken the validator
- pec bootstrap refuses draft → expected; continue L4 on `campaign/<id>`
- Remediation max cycles → report remaining blockers; do not merge
- Merge gate deny → re-run `authorize_campaign_merge.py` for this repo/PR only
- Dirty shared clone → create a worktree; do not `git switch`
