---
name: dag-authoring
version: "1.1.0"
description: "Create or update DAGs the PROPER way"
before_chain: rules
auto_chain: ynp
dag: dag-authoring-v1
dag_file: .cursor-commands/workflows/dags/dag_authoring_dag.py
---

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

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/dag_authoring_dag.py`
- **Interface**: `.cursor-commands/workflows/session/interface.py`
- **Registry**: `.cursor-commands/workflows/session/registry.py`
- **Commands**: `.cursor-commands/commands/*.md`
