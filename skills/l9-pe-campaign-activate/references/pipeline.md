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

Default bootstrap refuses an unvalidated draft lock. That is expected for a
new seed. Use `--admission-draft` only to inspect. Continue L4 execution on
`campaign/<id>` either way. Do not claim Program Lock accepted.

## 5. L4 execute

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"
# execute ready tasks locally; local commits only; no mid-execution push
```

Then kernels, then release:

```bash
# kernels/Recursive Alignment.md then kernels/Validate & Repair.md
python3 ops/autonomy/l4_local.py record-kernels
python3 ops/autonomy/l4_local.py authorize-release
```

## 6. Publish

```bash
PR_BASE=origin/campaign/<id> make pr
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
