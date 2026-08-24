# L9 slash commands

This folder holds live slash triggers (`commands/*.md`).

- Human index: `commands/commands-index.md`
- Machine registry: `commands/COMMANDS_MANIFEST.yaml` (generated)
- Recognition rule: `rules/02-slash-commands.mdc`

Use **`/docs`** (skill `l9-update-agent-docs`) to update agent-facing docs. This README is not a `/readme` protocol. The README DAG remains under `workflows/dags/readme_pipeline_dag.py` and is not a slash.

Retired command files live in `commands/_archived/`.
