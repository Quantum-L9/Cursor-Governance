---
name: docs
version: "1.0.0"
description: "Update agent-facing docs via l9-update-agent-docs (not the README DAG)"
auto_chain: ynp
---

# /docs — Agent docs

Delegates to skill **`l9-update-agent-docs`**.

This is **not** the README DAG. Subsystem README generation stays under `workflows/dags/readme_pipeline_dag.py` and is invoked from there, not as a slash.

`/readme` is an alias of this command.

## EXECUTION

1. Read and follow skill `l9-update-agent-docs`.
2. Stay inside that skill's envelope. Do not overwrite root additive-only files unless the skill authorizes it.
3. Auto-chain `/ynp`.

## FORBIDDEN

- Treating this slash as the README DAG
- Recreating `/readme` as a live command file
- Editing `CANONICAL_LAW.md`
