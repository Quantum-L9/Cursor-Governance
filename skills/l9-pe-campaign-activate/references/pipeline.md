<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: pipeline
tags: [campaign, pe, compile, bootstrap, l4]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-15
/L9_META -->

# PE activation pipeline

Purpose: run the in-repo Program Execution path after the file set exists.
Do not invent a second compiler or a second controller.

Operator front door — the only path:

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` is the tunnel. Do not call pec, the intent compiler, or
L4 as a substitute. Order inside the runner:

1. `compile_brief.py` (memo) or activate YAML passthrough
2. isolate worktrees from `origin/main`
3. `compile_activation_files.py` → `CAMPAIGN_SOURCE` + receipt
4. `compile_campaign_source.py` (allowlist from the emit worktree)
5. `collect_evidence.py` EVID-001 → `accept_blueprint.py`
6. `pec bootstrap` **without** `--admission-draft`
7. clean target checkout at `$HOME/.l9/program-worktrees/<id>` + `pec reconcile`
8. `pec draft-contract` + `register-contract` + `claim` TASK-001
9. host PR → merge-if-green

`program-execution.intent.v1` and `pe-<hash>` workspaces are refused.
`--admission-draft` is not a live path. Host-only merge is not program close.

## 0. Isolate

```bash
git fetch origin main
git worktree add -b campaign/<id> \
  "$HOME/.l9/program-worktrees/<id>" origin/main
```

If the seed must land in this governance clone, use
`feat/<id>` or `campaign/<id>` off `origin/main`. Never `git switch` on a
dirty shared checkout.

## 1. Emit files

```bash
python3 skills/l9-pe-campaign-activate/scripts/compile_activation_files.py \
  --intent <intent.yaml> --repo-root "$(pwd)"
```

Confirm the printed path list equals the allowed set.

## 2. Compile Blueprint

```bash
python3 environment/program-execution/scripts/compile_campaign_source.py \
  --source environment/program-execution/campaigns/<id>/CAMPAIGN_SOURCE.yaml \
  --target "$HOME/.l9/blueprints/<id>"
```

Fail closed if `<id>` is missing from `COMPILE_ALLOWLIST.yaml`.

## 3. Template validate

```bash
python3 environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py \
  "$HOME/.l9/blueprints/<id>" --mode template
```

Must PASS. Instantiated mode stays FAIL while `definition_status=draft`.
Do not flip accepted to force a pass.

## 4. pec bootstrap

```bash
python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py \
  bootstrap --workspace "$HOME/.l9/programs/<id>" \
  --blueprint "$HOME/.l9/blueprints/<id>"
```

`make campaign` collects EVID-001 and accepts the blueprint **before**
bootstrap. Live bootstrap must succeed without `--admission-draft`. If it
does not, the runner exits 2. Do not retry with `--admission-draft`.
A leftover `$HOME/.l9/programs/<id>` from a stopped run is quarantined
under `programs/stale/` so the next launch starts empty.

After arm, `LAUNCH.json` names the only legal pec workspace and TASK-001
must be `LEASED`. Execute that claimed task on
`$HOME/.l9/program-worktrees/<id>`. Do not attach to a `pe-<intent-hash>`
workspace. Autonomy packets are not a second scheduler. Do not load the
operator memo as the program.

`make campaign` must mark the campaign **active** on invoke: host
`CAMPAIGN_STATUS.yaml` `lifecycle: in_progress`, execution-policy row
`lifecycle: in_progress`, pec `runtime_status: active`, and
`$HOME/.l9/programs/<id>/runtime/LAUNCH.json`.
`CAMPAIGN_SOURCE.yaml` `metadata.status` stays `operator_intake`. Leaving
those surfaces at `planned` / `operator_intake` after invoke is a defect —
agents will treat the campaign as idle. `pec next` returning `ready: []`
because `admission_draft` or `source_contract_incomplete` is a runner bug.

`PHASE0_USER_CONFIG.yaml` `operator_ack.acknowledged_at` is a real human
acknowledgment from Igor Beylin. `make campaign` fills the name and leaves
`acknowledged_at: null`. Agents must stop and ask; do not forge the
timestamp. `program_deploying` stays false until that ack.

## 5. Execute the claimed task

Read `$HOME/.l9/programs/<id>/runtime/TASK-001.md` only (15 minutes).
Execute **only** `claimed_task` on `target_worktree`. Do not open the
operator memo. Do not start L4, the intent compiler, or a second pec
workspace. If blocked, stop and report.

## 6. Publish

```bash
PR_BASE=origin/campaign/<id> PR_REMEDIATE=0 make pr
```

If the integration branch does not exist yet, create
`campaign/<id>` from `origin/main` first, then stack the feature PR onto it.

Title must be `[{campaign_id}] {metadata.title}` via
`environment/program-execution/scripts/campaign_pr_copy.py`.

## 7. Remediate then merge

Load `l9-pr-remediation` Converge on that PR only. When green and mergeable,
follow [merge-authority.md](merge-authority.md).

## 8. Close

```bash
python3 environment/program-execution/campaigns/scripts/close_campaign.py close \
  --id <id> --verdict CONVERGED \
  --evidence pull_request=<url> --evidence merge_sha=<sha>
```

Leaving `CAMPAIGN_STATUS.yaml` at `planned` / `in_progress` after merge is a defect.
