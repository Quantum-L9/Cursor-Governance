---
name: dag-authoring
version: "2.3.0"
description: "Create, update, validate, register, command-bind, or convert an L9 workflow graph"
before_chain: rules
auto_chain: ynp
dag: dag-authoring-v1
dag_file: workflows/dags/dag_authoring_dag.py
---

# /dag-authoring — DAG lifecycle

Delegates to skill **`l9-dag-authoring`** (graph lifecycle owner).

`workflows/` hosts two first-class graph kinds — `SESSION_GUIDANCE`
(`SessionDAG`, registry-backed) and `LANGGRAPH_RUNTIME` (`StateGraph`,
executable, never registry-backed). Kind is classified before authoring.

## Usage

```
/dag-authoring                       # CREATE a new canonical DAG
/dag-authoring --update <dag-id>     # UPDATE an existing DAG
/dag-authoring --validate <dag-id>   # VALIDATE structure only
/dag-authoring --register <dag-id>   # Repair registration / discovery
/dag-authoring --bind-command <cmd>  # Reduce a command to a thin DAG trigger
/dag-authoring --convert <dag-id>    # Disposition-gate a SessionDAG
```

`--bind-command` is the former `/update-command`. That slash and its skill are
retired; thin command-to-DAG binding is owned here.

## EXECUTION

1. Read and follow skill `l9-dag-authoring`.
2. Classify the graph kind, then exactly one operation: CREATE, UPDATE,
   VALIDATE, REGISTER, COMMAND_BIND, CONVERT. CONVERT continues only on
   SESSION_GUIDANCE and emits a StateGraph only for CONVERT_TO_LANGGRAPH.
3. Validate before any registration claim; probe before any discovery claim.
4. Auto-chain `/ynp`.

## FORBIDDEN

- Claiming registration or reachability without a successful probe
- Inventing a registry beside `register_session_dag()`
- Registering a `LANGGRAPH_RUNTIME` graph in the SessionDAG registry
- Calling a `SessionDAG` fake because it is not executable LangGraph
- Absorbing domain workflow semantics (GMP, compiler, maintenance, verification)
- Pasting a DAG body or workflow phases into this file
- Emitting a StateGraph for a twin or absorb row
- Deleting a SessionDAG in the same CONVERT step
