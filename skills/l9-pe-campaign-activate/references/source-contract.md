<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: source_contract
tags: [campaign, intent, schema, pe]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-15
/L9_META -->

# Intent and seed contract

Purpose: minimum inputs this skill accepts, and the seed fields it must emit
so `compile_campaign_source.py` can succeed.

## Operator input (memo or activate YAML)

Preferred: a free-form program memo (`.md`). `make campaign INTENT=brief.md`
assigns `campaign_id` from the filename slug (`PE- Memory.md` → `pe-memory`,
then `-v2` on collision). You do not write a campaign id or a PE schema.

The brief compiler (`scripts/compile_brief.py`) extracts:

- tasks from numbered `Release A — …` blocks, else a `Program ordering` list
- objective from `It is:` under Final architectural judgment (not an earlier `It is:`)
- `problem_statement` = the full memo
- target = github-shaped `owner/repo` (hyphen or `github.com/…`), else
  `Quantum-L9/Cursor-Governance` (`TARGET=` override). Slash-noise like
  `MCP/API` is not a repo.

It fails closed if there are no numbered work items. It does not invent tasks.
Generated seed lands in `$HOME/.l9/primed/<id>.activate.yaml`, never as
`INTENT.yaml` under `campaigns/<id>/`.

Optional power-user activate YAML (passthrough):

```yaml
campaign_id: kebab-case-id          # required only for this YAML form
title: Human title                  # required
objective: One paragraph            # required
owner: Igor Beylin                  # default Igor Beylin
target:
  repository_id: Quantum-L9/Cursor-Governance
  source_of_truth: environment/program-execution
  adapter: git
tasks:                              # required, ≥1
  - title: Lock current state
    objective: ...
    paths: []                       # optional include paths
```

`scripts/compile_activation_files.py` fills PE-required defaults
(`problem_statement`, `target_state`, `scope`, `authority_order`,
`operating_rules`, `terminal_verdicts`, authorities, workstreams, waves,
gates, task rollback/risk/acceptance). Do not invent extra seed sections.

## Seed fields the PE compiler requires

Schema required (`core/shared/schemas/campaign-source.schema.json`):

- `schema: l9.program-execution.campaign-source.v2`
- `schema_version: 2.0.0`
- `metadata.campaign_id`, `metadata.title`
- `program.id`, `program.name`, `program.definition_status`

Compiler-admissible (or compile raises):

- `program.owner`, `objective`, `problem_statement`, `target_state`, `scope`
- `program.authority_order`, `operating_rules`, `terminal_verdicts`
- `targets[]` with `id` + `adapter` in `{git, git_repo_adapter, controller}`
- `authorities[]` with `id`, `responsibility`, `owner`
- each task: `definition_status` in `{ready, blocked, cancelled, superseded}`
- each task: `title`, `objective`, `actions`, `acceptance[0].statement`,
  `workstream_id`, `wave_id`, `target_id`, `execution_kind`,
  `authority_basis_ids`, `negative_cases`, `rollback`, `risk`,
  `completion_gate_ids`
- decisions, if present, must include non-empty `options`

`metadata.status` stays `operator_intake`. `program.definition_status` stays
`draft` until evidence exists. The PE compiler itself rewrites compiled
`PROGRAM.yaml` to `draft`.

## Integrity receipt

```json
{
  "schema": "source-integrity-receipt.v1",
  "campaign_id": "<id>",
  "source_file": "CAMPAIGN_SOURCE.yaml",
  "digest_algorithm": "sha256",
  "digest": "<hex>",
  "bytes": 0,
  "pack_recorded_digest": "<hex>",
  "pack_recorded_bytes": 0,
  "digest_matches_pack": true,
  "producer": "l9-pe-campaign-activate"
}
```

After the receipt is written, do not hand-edit `CAMPAIGN_SOURCE.yaml`.
Re-run the compiler instead.
