---
name: harvest
version: "3.2.0"
description: "Extract code from documents using sed — NEVER write/type code manually"
before_chain: rules
auto_chain: use-harvest
dag: harvest-deploy-v1
dag_file: .cursor-commands/workflows/dags/harvest_deploy_dag.py
---

# /harvest — Code Extraction via sed

**DAG-ENFORCED.** Execute the `harvest-deploy-v1` DAG.

## Absolute Rule

**sed ONLY.** Never use `Write`, `StrReplace`, or manually type code from documents. Use `grep -n` for boundaries, `sed -n` for extraction. Violation = governance breach.

## Usage

```
/harvest path/to/document.md              # Harvest from single doc
/harvest doc1.md doc2.md                  # Harvest from multiple docs
```

## Execution

Load and execute the DAG:

```python
from .cursor_commands.workflows.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/harvest_deploy_dag.py`
- **CLI**: `python3 .cursor-commands/workflows/harvest_executor.py path/to/doc.md` (standalone alternative)
- **Next step**: `/use-harvest` after extraction completes
