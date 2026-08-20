---
name: Campaign brief IR
overview: Build the factory glue only — make campaign INTENT=brief.md assigns an id, compiles an activate seed, and runs the existing pipeline. PE- Memory.md is a document-class example, not a campaign to launch. Ping when the host PR is merged.
todos:
  - id: compile-brief
    content: "Add compile_brief.py: memo-class extract + filename campaign_id; YAML passthrough"
    status: completed
  - id: brief-tests
    content: Trimmed fixture matching PE- Memory.md patterns only — do not launch that campaign
    status: completed
  - id: run-campaign-resolve
    content: make campaign INTENT=.md assigns id and compiles brief; keep intent.v1 refusal
    status: completed
  - id: docs-make
    content: Update Makefile help, source-contract.md, pipeline.md, SKILL.md
    status: completed
  - id: host-pr-merge
    content: PR feat/make-campaign on Cursor-Governance; remediate; merge; ping operator
    status: completed
isProject: false
---

# Campaign brief IR (memo upload, not a heading schema)

## Decision

Keep `CAMPAIGN_SOURCE.yaml` + `source-integrity-receipt.json` as the only PE-admissible seed. Do **not** teach `compile_campaign_source.py` or `compile_activation_files.py` to parse markdown.

This is the **factory**, not a campaign launch. Do not compile or activate PE-Memory (or any other live program) as part of this work. [`.cursor-commands/WIP/PE- Memory.md`](/Users/macm2/l9-ci-core/.cursor-commands/WIP/PE-%20Memory.md) is only the document class the extractor must accept.

Operator path after merge:

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=/path/to/brief.md
```

No campaign id, no canonical YAML. The compiler assigns the id. Existing activate YAML still works. `program-execution.intent.v1` stays refused.

```mermaid
flowchart LR
  memo["PE-Memory.md class memo"]
  seed["Activate seed IR"]
  source["CAMPAIGN_SOURCE + receipt"]
  bp["Blueprint + pec"]
  memo -->|"compile_brief.py assigns id"| seed
  seed -->|"compile_activation_files.py"| source
  source -->|"compile_campaign_source.py"| bp
```

Existing activate YAML remains a passthrough. `program-execution.intent.v1` stays refused.

## Why not the heading-contract plan

That contract would reject this file (no H1, no `campaign_id:`, no `## Tasks`). Rewriting the memo into headings is the friction this step exists to remove.

Still not an LLM extract: stdlib, deterministic, fail-closed if no work items can be found.

## How this memo maps to the activate seed

Verified in the file:

- Work program is `Build-ready convergence program` with seven numbered releases (`1. Release A — …` through `7. Release G — …`).
- A second list `Program ordering` has 12 numbered items. Use **releases first**; only fall back to program-ordering if no Release blocks exist.
- Objective is the paragraph after `It is:` under `Final architectural judgment` (collapse agent memory onto `l9-graphiti-memory`…).
- Title from filename stem: `PE- Memory.md` → `PE Memory`.
- `campaign_id` assigned from filename slug: `pe-memory`. If that id is already on the host allowlist / status ledger as non-complete, assign `pe-memory-v2` (then v3…). Never ask the operator.
- `problem_statement` = full memo text (so design is not discarded).
- `target.repository_id` = first `owner/repo` found, else `Quantum-L9/Cursor-Governance`. This memo names Cursor-Governance and l9-graphiti-memory; v1 stays **one** intended host (activate compiler is single-target). Optional `TARGET=` override. Multi-repo campaigns are out of scope.
- `owner` = Igor Beylin unless an `owner:` line exists.

Fail closed (exit 2) if the memo has no numbered Release blocks and no numbered program-ordering / task list. Do not invent tasks from architecture prose.

## Implementation (Cursor-Governance `feat/make-campaign`)

- New [`skills/l9-pe-campaign-activate/scripts/compile_brief.py`](/Users/macm2/.l9/gov-worktrees/make-campaign/skills/l9-pe-campaign-activate/scripts/compile_brief.py): `brief_to_seed(text, *, filename, existing_ids) -> dict`; write `$HOME/.l9/primed/<id>.activate.yaml`; never write `INTENT.yaml` under `campaigns/<id>/`.
- Tests use a trimmed fixture that preserves this memo’s patterns (Release A–G headings, Program ordering list, Final architectural judgment / `It is:`). Assert 7 tasks, id `pe-memory`, objective contains the collapse-to-l9-graphiti-memory sentence.
- [`run_campaign.py`](/Users/macm2/.l9/gov-worktrees/make-campaign/environment/program-execution/scripts/run_campaign.py): if `INTENT` is not an activate mapping, run `compile_brief` then the existing pipeline. Pass host allowlist/status ids into id assignment.
- Makefile: `INTENT=` may be a memo `.md` or activate YAML. No `CAMPAIGN_ID=` required.
- Docs: source-contract, pipeline, SKILL — memo upload is the operator path; heading YAML is optional power-user.

Do not change `compile_campaign_source.py`, receipt schema, or Phase 0 `operator_ack` forging rules. Host/pec status still flip to active on invoke.

## Acceptance

- Factory tests pass on a PE-Memory-**class** fixture (not a live campaign).
- Assigned id is a valid kebab slug; collision gets `-v2`.
- Seven Release tasks, not twelve program-ordering items, not invented architecture bullets.
- Empty / architecture-only memo fails closed.
- Activate YAML and `intent.v1` behavior unchanged.
- Host PR on `feat/make-campaign` is green and merged. Ping the operator with the merge URL. Do not start a campaign from the example memo.

## Reversibility

Additive. Rollback is delete `compile_brief.py` and revert the `INTENT=` resolver.

## Reconsider if

The operator later needs one campaign to mutate two repos as first-class targets — that is a separate activate-compiler change, not this IR.
