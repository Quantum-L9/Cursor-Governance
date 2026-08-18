# Activate a PE campaign

You author one file: `INTENT.yaml`.
The compiler writes the rest. Do not invent extras.

## 1. Fill INTENT.yaml

Required: `campaign_id`, `title`, `objective`, `tasks` (≥1).
`campaign_id` must match `^[a-z0-9][a-z0-9-]{2,62}$`.

Optional: `owner`, `problem_statement`, `target_state`, `target`, per-task `id` / `paths` / `actions`.

## 2. Compile (from the governance repo root)

```bash
python3 skills/l9-pe-campaign-activate/scripts/compile_activation_files.py \
  --intent "WIP/8-15-26/Campaign Activation Files/TEMPLATE/INTENT.yaml" \
  --repo-root "$(pwd)"
```

Writes exactly:

- `environment/program-execution/campaigns/<id>/CAMPAIGN_SOURCE.yaml`
- `environment/program-execution/campaigns/<id>/source-integrity-receipt.json`

Patches existing hosts (does not create new host files):

- `environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml`
- `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`
- `ops/autonomy/surface_profile.yaml`
- `environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml`

## 3. Run PE

```bash
python3 environment/program-execution/scripts/compile_campaign_source.py \
  --source environment/program-execution/campaigns/<id>/CAMPAIGN_SOURCE.yaml \
  --target "$HOME/.l9/blueprints/<id>"

python3 environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py \
  "$HOME/.l9/blueprints/<id>" --mode template

python3 environment/program-execution/core/program-execution-controller-template/scripts/pec.py \
  bootstrap --workspace "$HOME/.l9/programs/<id>" \
  --blueprint "$HOME/.l9/blueprints/<id>"
```

Then L4 on `campaign/<id>` (local commits only). After kernels + `authorize-release`:

```bash
PR_BASE=origin/campaign/<id> PR_REMEDIATE=0 make pr
```

## Never put in campaigns/<id>/

`INTENT.yaml`, `README.md`, `AGENT_FEED.md`, `CONTRACT_SOURCE.md`,
`PROGRAM_SOURCE.md`, alignment YAML, `handoff/`, `deliverables/`.

After the receipt is written, do not hand-edit `CAMPAIGN_SOURCE.yaml`. Re-run the compiler.
