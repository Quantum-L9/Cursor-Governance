---
name: docs
version: "1.0.0"
description: "Update agent-facing docs via l9-update-agent-docs; module READMEs via readme-pipeline-v1"
auto_chain: ynp
---

# /docs — Agent docs

Delegates to skill **`l9-update-agent-docs`**.

Root pointer stack stays in the skill. Module / subsystem README generation is
the same pipeline the skill invokes: `readme-pipeline-v1` in
`workflows/dags/readme_pipeline_dag.py` → `scripts/generate_subsystem_readmes.py`
+ `config/subsystems/readme_config.yaml`.

`/readme` is an alias of this command.

## EXECUTION

1. Read and follow skill `l9-update-agent-docs`.
2. Stay inside that skill's envelope. Do not overwrite root additive-only files unless the skill authorizes it.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Generating the repo-root `README.md`
- Recreating `/readme` as a live command file
- Editing `CANONICAL_LAW.md`
