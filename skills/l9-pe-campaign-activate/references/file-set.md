<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: file_set
tags: [campaign, files, allowlist, pe]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-15
/L9_META -->

# Allowed activation file set

Purpose: the exact files this skill may create or patch. Nothing else.

## Campaign directory (`environment/program-execution/campaigns/<id>/`)

| File | Role |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Immutable seed (`l9.program-execution.campaign-source.v2`) |
| `source-integrity-receipt.json` | sha256 binding of that seed (`source-integrity-receipt.v1`) |

Do not create any other file in this directory.

## Host registrations (patch existing files; do not invent new host files)

| File | Patch |
|---|---|
| `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml` | append campaign row (`integration_branch`, `pr_base`, `execute_order`) |
| `ops/autonomy/surface_profile.yaml` | append `campaign_execution.campaigns.<id>` |
| `environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml` | append `lifecycle: planned`; `make campaign` immediately promotes to `in_progress` |

## Runtime (not in git)

| Path | Role |
|---|---|
| `$HOME/.l9/blueprints/<id>` | compiled Blueprint |
| `$HOME/.l9/programs/<id>` | Controller workspace |
| `$HOME/.l9/program-worktrees/<id>` | exclusive worktree |
| `$HOME/.l9/primed/<id>/stack-proof.json` | runner-owned stack-doc receipt (not a campaign emit file) |
| `campaign/<id>` | integration branch |

## Forbidden (never emit)

- `README.md`
- `handoff/**`
- `INTENT.yaml`
- `CONTRACT_SOURCE.md`
- `PROGRAM_SOURCE.md`
- `AUTH-001-SUPERSESSION.yaml`
- `PE_COMPILER_MODULE_ALIGNMENT.yaml`
- `CAMPAIGN_EXECUTION_BINDING.yaml`
- `CURRENT_STATE.yaml`
- `VALIDATION_EVIDENCE.md`
- `deliverables/**`
- `history/**`
- `AGENT_FEED.md`

`INTENT.yaml` is a compiler front-door input, not a campaign seed. If the user
supplied prose, fold it into `CAMPAIGN_SOURCE.yaml` `operator_directive` /
`program.objective`. Do not drop a second source file.
