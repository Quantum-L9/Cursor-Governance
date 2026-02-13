name: update-command
version: "1.0.0"
description: "Update slash commands to be minimal triggers"
auto_chain: ynp
dag: slash-command-update-v1
dag_file: workflows/session/dags/slash_command_update_dag.py

# /update-command — Minimize Slash Commands

**DAG-ENFORCED.** Execute the `slash-command-update-v1` DAG.

## Usage

```
/update-command readme     # Reduce /readme command
/update-command wire       # Reduce /wire command
/update-command --all      # Audit all DAG-trigger commands
```

## Execution

Load and execute the DAG:

```python
from workflows.session.dags import SLASH_COMMAND_UPDATE_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `workflows/session/dags/slash_command_update_dag.py`
- **Commands**: `.cursor-commands/commands/*.md`
- **Registry**: `.cursor/rules/02-slash-commands.mdc`
