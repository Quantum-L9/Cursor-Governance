<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: source_contract
tags: [campaign, intent, schema, campaign-source-v2, pe]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-13
/L9_META -->

# Campaign input and source contract

Use `make campaign INTENT=<path>` as the only live Program Execution campaign
front door. It classifies the input before choosing a compiler. Do not override
the classifier or invoke PEC and inner compiler scripts as a substitute.

## Accepted input forms

| Input | Use when | Route |
|---|---|---|
| Complete `campaign-source.v2` YAML | Campaign semantics are already fully specified. Start from the canonical template. | `campaign_source → blueprint → PEC` |
| Architecture intent | The source is rich architecture prose. | `architecture → campaign_source → blueprint → PEC` |
| Activate YAML | The user intentionally supplied the compact seed shape. | `activate → campaign_source → blueprint → PEC` |
| Plan | The user supplied a supported plan representation. | `plan → activate → campaign_source → blueprint → PEC` |
| Brief | The user supplied a free-form memo with numbered work items. | `brief → activate → campaign_source → blueprint → PEC` |

The direct template source of truth is
`environment/program-execution/templates/campaign-source-v2/CAMPAIGN_SOURCE.yaml`.
Read [canonical-template.md](canonical-template.md) before authoring a direct
source. Direct input preserves complete source semantics; the runner serializes it
into the isolated campaign worktree before compilation.

Architecture prose must not be rebuilt through brief → activate merely because it
lacks frontmatter. A classifier-selected free-form brief fails closed when it has
no numbered work items; do not invent tasks.

## Complete direct campaign source

The direct source must declare:

- `schema: l9.program-execution.campaign-source.v2` and `schema_version: 2.0.0`
- matching `metadata.campaign_id` and `program.id`, plus title, owner, and draft
  definition state
- a target with an accepted adapter, repository identity, and current binding facts
- authorities, evidence requirements, workstreams, waves, top-level dependency
  edges, tasks, gates, risks, and prohibited paths
- every task's ready/blocked/cancelled/superseded definition status, objective,
  actions, acceptance statement, target/workstream/wave bindings, authority
  basis, negative cases, rollback, risk, and completion gates
- explicit writable paths and an admissible terminal validation for each mutable
  `repo_local` task
- remote-action ceilings restricted to `false`

Keep `metadata.status: operator_intake` and `program.definition_status: draft`
until the controller has collected and bound required evidence. Do not leave
placeholder markers, task-local dependency fields, or unverified example facts.

## Activate YAML alternative

Use compact activate YAML only when the input is intentionally a seed rather than
a complete direct source:

```yaml
campaign_id: kebab-case-id
title: Human title
objective: One paragraph
owner: Quantum AI Partners
target:
  repository_id: Quantum-L9/Cursor-Governance
  source_of_truth: environment/program-execution
  adapter: git
tasks:
  - title: Lock current state
    objective: ...
    paths: []
```

`scripts/compile_activation_files.py` fills the required campaign-source defaults.
Do not add invented seed sections. The compiler will write the emitted source and
integrity receipt in the isolated worktree.

## Preflight and receipt

```bash
make campaign-check-input INTENT=path/to/input
```

The direct route emits `source-integrity-receipt.json` after source placement.
Do not hand-edit the emitted `CAMPAIGN_SOURCE.yaml` after its receipt exists;
change the original authoring source and re-run the front door. Campaign IDs are
not admitted through `COMPILE_ALLOWLIST.yaml`; that file is historical only.
