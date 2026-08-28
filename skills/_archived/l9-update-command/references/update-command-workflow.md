<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [commands, dag, update]
status: active
/L9_META -->

# Update Command Workflow

## Usage

```
/update-command readme
/update-command wire
/update-command --all
```

## Execution

```python
# Load DAG — follow each node action in sequence
# DAG: .cursor-commands/workflows/dags/slash_command_update_dag.py
```

## Key files

- DAG: `.cursor-commands/workflows/dags/slash_command_update_dag.py`
- Commands: `.cursor-commands/commands/*.md`
- Registry: `.cursor/rules/02-slash-commands.mdc` (if present)

## Principle

Slash command = trigger only. Workflow = DAG.
