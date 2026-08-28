---
name: dag-authoring
version: "2.0.0"
description: "Create, update, validate, register, or command-bind an L9 DAG"
before_chain: rules
auto_chain: ynp
dag: dag-authoring-v1
dag_file: workflows/dags/dag_authoring_dag.py
---

# /dag-authoring — DAG lifecycle

Delegates to skill **`l9-dag-authoring`** (DAG lifecycle owner).

## Usage

```
/dag-authoring                       # CREATE a new canonical DAG
/dag-authoring --update <dag-id>     # UPDATE an existing DAG
/dag-authoring --validate <dag-id>   # VALIDATE structure only
/dag-authoring --register <dag-id>   # Repair registration / discovery
/dag-authoring --bind-command <cmd>  # Reduce a command to a thin DAG trigger
```

`--bind-command` is the former `/update-command`. That slash and its skill are
retired; thin command-to-DAG binding is owned here.

## EXECUTION

1. Read and follow skill `l9-dag-authoring`.
2. Classify exactly one operation: CREATE, UPDATE, VALIDATE, REGISTER, COMMAND_BIND.
3. Validate before any registration claim; probe before any discovery claim.
4. Auto-chain `/ynp`.

## FORBIDDEN

- Claiming registration or reachability without a successful probe
- Inventing a registry beside `register_session_dag()`
- Absorbing domain workflow semantics (GMP, compiler, maintenance, verification)
- Pasting a DAG body or workflow phases into this file
