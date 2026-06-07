---
name: l9-dag-authoring
description: create or update l9 workflow dags the proper way via dag-authoring-v1. use when authoring new dags, updating existing dags, wiring commands to dag nodes, or registering dag executors.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, dag, workflow, authoring, governance]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
disable-model-invocation: true
---

# DAG Authoring

## Purpose

Create or update L9 workflow DAGs through the enforced `dag-authoring-v1` pipeline — ensuring nodes, actions, registries, and command wiring follow governance conventions.

## Core Contract

`LOAD DAG → EXECUTE NODES IN ORDER → REGISTER → VALIDATE`

1. **Load** `dag-authoring-v1` DAG from canonical path.
2. **Execute** each node's `action` field exactly — no improvisation.
3. **Register** new DAGs in session registry and command index.
4. **Validate** DAG imports, node graph, and command linkage before handoff.

## Authority Order

1. `.cursor-commands/workflows/dags/dag_authoring_dag.py` — enforced DAG
2. `.cursor-commands/workflows/session/interface.py` — DAG interface contract
3. `.cursor-commands/workflows/session/registry.py` — registry of active DAGs
4. [`references/dag-authoring-protocol.md`](references/dag-authoring-protocol.md) — usage and execution details
5. `.cursor-commands/commands/*.md` — command definitions linked to DAGs

## Compact Workflow

```
/dag-authoring                    # Start new DAG
/dag-authoring --update existing  # Update existing DAG
```

1. Load and execute `DAG_AUTHORING_DAG` node sequence.
2. Follow each node's `action` field exactly.
3. Wire command markdown and registry entries.
4. Chain to `/ynp` for next action after completion.

See [`references/dag-authoring-protocol.md`](references/dag-authoring-protocol.md).

## Resource Map

- [`references/dag-authoring-protocol.md`](references/dag-authoring-protocol.md) — usage, execution, key files
- `.cursor-commands/workflows/dags/dag_authoring_dag.py` — authoring DAG
- `.cursor-commands/workflows/session/interface.py` — session interface
- `.cursor-commands/workflows/session/registry.py` — DAG registry
- `.cursor-commands/commands/*.md` — command definitions

## Validation

- DAG file imports without error.
- All nodes have non-empty `action` fields.
- Registry entry exists for new DAG ID.
- Linked command markdown references correct `dag` and `dag_file`.

## Failure Handling

| Symptom | Action |
|---------|--------|
| DAG import error | Fix syntax/imports before proceeding; do not skip nodes |
| Missing registry entry | Add to `registry.py` before claiming complete |
| Node action ambiguous | Halt; ask one focused question or read interface spec |
| Command not wired | Link command markdown before handoff |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: read `interface.py` or run DAG node 1 only).
