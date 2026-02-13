name: readme
version: "1.0.0"
description: "Generate and validate subsystem READMEs via DAG-enforced pipeline"
auto_chain: ynp
dag: readme-pipeline-v1
dag_file: workflows/session/dags/readme_pipeline_dag.py

# /readme — README Generation Pipeline

**DAG-ENFORCED.** Execute the `readme-pipeline-v1` DAG.

## Usage

```
/readme                    # Full pipeline
/readme --tier core        # Only core tier
/readme --subsystem memory # Single subsystem
```

## Execution

Load and execute the DAG:

```python
from workflows.session.dags import README_PIPELINE_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `workflows/session/dags/readme_pipeline_dag.py`
- **Config**: `config/subsystems/readme_config.yaml`
- **Generator**: `scripts/generate_subsystem_readmes.py`
