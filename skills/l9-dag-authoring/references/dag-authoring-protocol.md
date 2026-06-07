<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-dag-authoring
layer: reference
role: dag_authoring_protocol
tags: [l9, dag, workflow, authoring]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
dag: dag-authoring-v1
dag_file: .cursor-commands/workflows/dags/dag_authoring_dag.py
--- /SKILL_META ---
-->

# /dag-authoring — Create DAGs Properly

**DAG-ENFORCED.** Execute the `dag-authoring-v1` DAG.

## Usage

```
/dag-authoring                    # Start new DAG
/dag-authoring --update existing  # Update existing DAG
```

## Execution

Load and execute the DAG:

```python
from .cursor_commands.workflows.dags import DAG_AUTHORING_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Chain

- **before_chain:** rules
- **auto_chain:** ynp

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/dag_authoring_dag.py`
- **Interface**: `.cursor-commands/workflows/session/interface.py`
- **Registry**: `.cursor-commands/workflows/session/registry.py`
- **Commands**: `.cursor-commands/commands/*.md`
