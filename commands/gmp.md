---
name: gmp
version: "9.0.0"
description: "TRIGGER ONLY — enforced phased GMP execution via the LangGraph GMP package"
before_chain: rules
auto_chain: ynp
dag: gmp-execution-v1
dag_file: workflows/dags/gmp/graph.py
---

# /gmp — Governance Managed Process

**TRIGGER ONLY.** All logic lives in the graph.

Semantics (when GMP is required, scope lock, evidence, terminal states) are owned
by skill **`l9-gmp-protocol`**. Runtime is owned by `workflows/dags/gmp/`.

## INVOCATION

```bash
python3 -m workflows.dags.gmp.executor "task description" --tier RUNTIME
```

`workflows/dags/gmp_langgraph_executor.py` is a backwards-compatibility shim over
the same package.

## WHAT THE GRAPH ENFORCES

`start → memory_read → scope_lock → [user gate] → baseline → implement → validate
→ [user gate] → memory_write → finalize → end`

- Memory read and memory write are mandatory nodes, not advisory steps.
- Two explicit user gates: scope confirmation and validation confirmation.
- A failed validation routes back into `implement`; a declined gate routes to `aborted`.
- State is `GMPState` with MemorySaver checkpointing, so a run is resumable.

## TIERS

`KERNEL` (core execution, safety) · `RUNTIME` (services, tools, agents) ·
`INFRA` (deployment, containers) · `UX` (frontend, docs, scripts)

## OUTPUT

Terminal progress per node, plus a GMP report at `reports/GMP-Report-*.md`.

## FORBIDDEN

- **Committing or pushing from this graph.** It owns neither. Publication is
  `PR_REMEDIATE=0 make pr` (`l9 pr`), separately authorized. Any older contract
  describing a GMP `COMMIT_GATE` is superseded.
- Skipping a node or a user gate.
- Pasting phase logic into this file.
