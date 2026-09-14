<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: file_set
tags: [campaign, files, campaign-source-v2, pe]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-13
/L9_META -->

# Emitted campaign file set

The direct campaign source template is authored outside a campaign directory. The
runner owns isolated-worktree placement, generated receipts, and host
registrations. Do not hand-create campaign output files or patch obsolete
preregistration surfaces.

## Campaign directory (`environment/program-execution/campaigns/<id>/`)

| File | Role | Owner |
|---|---|---|
| `CAMPAIGN_SOURCE.yaml` | Immutable emitted `l9.program-execution.campaign-source.v2` source. | Campaign runner |
| `source-integrity-receipt.json` | SHA-256 binding for that emitted source. | Campaign runner |

Do not create any other file in this directory through this skill.

## Host registrations

The runner registers a valid campaign by patching only these host surfaces:

| File | Runner action |
|---|---|
| `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml` | Add the campaign's execution-policy entry. |
| `ops/autonomy/surface_profile.yaml` | Add `campaign_execution.campaigns.<id>`. |
| `environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml` | Create or update lifecycle tracking; active execution is runner-owned. |

There is no compile allowlist. A complete source is admitted by exact
`campaign-source.v2` schema and semantic preflight, never list membership. Do
not recreate a preregistration surface.

## Runtime (not in Git)

| Path | Role |
|---|---|
| `$L9_ROOT/blueprints/<id>` | Compiler-generated native Blueprint. |
| `$L9_ROOT/programs/<id>` | Controller workspace and mutable runtime state. |
| `$L9_ROOT/gov-worktrees/<id>` | Host isolate on `feat/<id>` for campaign emission. |
| `$L9_ROOT/program-worktrees/<id>` | Target reconciliation and `campaign/<id>` worktree. |
| `$L9_ROOT/primed/<id>/stack-proof.json` | Runner-owned stack-documentation receipt. |

## Forbidden output

Never emit these as companion campaign files:

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

A three-file historical campaign pack is not a live input. The only direct
operator-authored input is a complete `CAMPAIGN_SOURCE.yaml`; its receipt,
Blueprint, and PEC state are generated artifacts.

## Retired input evidence

`environment/program-execution/archive/campaign-input-v1/` is an immutable
evidence boundary, not a campaign directory. It retains legacy v1 inputs with
an `ARCHIVE_RECORD.yaml` containing provenance and hashes. The front door must
reject their declared schemas; a new campaign requires a newly authored v2
source.
