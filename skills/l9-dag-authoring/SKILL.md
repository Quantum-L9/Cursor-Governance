---
name: l9-dag-authoring
description: Author, update, validate, register, discover, and optionally bind thin command triggers to L9 workflow graphs, keeping SessionDAG guidance graphs and executable LangGraph runtimes as distinct first-class kinds. Use when creating or changing an L9 graph, repairing SessionDAG registration/discovery, validating a LangGraph runtime shape, or making a command a thin graph trigger. Do not use for domain workflow semantics, Skill wiring, Skill compilation, GMP execution, or generic component audits.
paths: "workflows/**, **/*dag*.py, **/*dag*.yaml"
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: dag_lifecycle_owner
  tags: [l9, dag, workflow, authoring, registry, langgraph, command-binding]
  owner: igor_beylin
  status: active
  version: 2.3.0
  updated: 2026-08-29
  absorbs: [l9-update-command]
---

# DAG Authoring — graph lifecycle owner

## Core contract

`BIND → CLASSIFY GRAPH KIND → RECONSTRUCT → DESIGN/RECONCILE → VALIDATE → BIND RUNTIME/DISCOVERY → OPTIONAL COMMAND BIND → OPTIONAL CONVERT → VERIFY → RECEIPT`

Own the **graph lifecycle mechanism** only. `workflows/` owns graph implementation
and execution. The most-specific domain Skill continues to own workflow semantics.

`CONVERT` is a disposition gate, not a rewrite of every `SessionDAG`. Classify
kind first. Continue only on `SESSION_GUIDANCE`. Look up
[`policies/session-deprecation.yaml`](policies/session-deprecation.yaml). Emit a
`StateGraph` only for `CONVERT_TO_LANGGRAPH`. Twin and absorb rows write a
receipt and stop. Never delete the source `SessionDAG` in the same step.

## Graph kinds

Classify before authoring, validating, registering, or binding. The two kinds are
distinct contracts, not two generations of one thing.

| | `SESSION_GUIDANCE` | `LANGGRAPH_RUNTIME` |
|---|---|---|
| Type | `SessionDAG` | `StateGraph` |
| Contract | `workflows/session/interface.py` | `langgraph.graph` |
| Registry | `register_session_dag()` | none |
| Lookup | `get_session_dag()` | domain runtime entrypoint |
| Discovery | `workflows/dags/__init__.py` | module import |
| Executable | no — guides an agent through a workflow | yes |
| Cycles | allowed by contract | per LangGraph semantics |

`UNKNOWN` is the third state: insufficient or conflicting evidence. It blocks
mutation until resolved.

`scripts/classify_graph_kind.py` classifies from the AST. A construction call
outranks an import, so a SessionDAG module that *documents* LangGraph validation
in a node `action` string stays `SESSION_GUIDANCE` — the mention is a string
literal, not a construction.

## Authority order

1. Explicit user scope and the domain Skill that owns workflow semantics.
2. Current executable repository truth under `workflows/`.
3. [`policies/graph-kinds.yaml`](policies/graph-kinds.yaml) for graph-kind resolution.
4. For `SESSION_GUIDANCE`: `workflows/session/interface.py`, `workflows/session/registry.py`, then `workflows/dags/__init__.py`.
5. For `LANGGRAPH_RUNTIME`: current LangGraph runtime surfaces, with `langgraph.graph.StateGraph` as the canonical graph contract when present.
6. The existing canonical graph implementation when updating.
7. This Skill's references and policies.
8. `UNKNOWN` when a material ownership or runtime fact cannot be verified.

## Invariants

- A graph does not justify a separate Skill. Skills represent capabilities; graphs
  represent workflow structures and runtimes.
- Never call `SessionDAG` fake merely because it is not executable LangGraph. It is
  a distinct guidance contract that deliberately permits revision loops.
- Never claim `SessionDAG` and `StateGraph` are equivalent runtime types.
- Keep domain semantics with the domain owner. Do not become a generic workflow
  god-skill.
- Author canonical graphs under `workflows/dags/` unless current repository ground
  truth proves another canonical location — a `LANGGRAPH_RUNTIME` may legitimately
  live elsewhere under `workflows/`. Never create a parallel workflow root.
- Register only `SESSION_GUIDANCE` graphs through `register_session_dag()`. Never
  invent `ACTIVE_DAGS`, dict-only registries, or a parallel registration layer.
- Never register a `LANGGRAPH_RUNTIME` graph in the SessionDAG registry unless a
  future explicit repository contract defines an adapter.
- `CONVERT` refuses `UNKNOWN` kind, a `LANGGRAPH_RUNTIME` source, an unknown
  catalog id, and `allow_session_retire: true`. Missing `proof_path` on a twin
  or absorb row is `BLOCKED`, not convert.
- An emitted runtime must not call `register_session_dag()`.
- A prose `action` string fails closed. Only an existing repo script path may
  become a node callable.
- Validate before registration. Never claim registration or reachability without a
  successful probe.
- Require unique node IDs, resolvable edge endpoints, a resolvable entry node, and
  explicit branch outcomes where gates exist.
- Duplicate graph IDs fail closed unless the task is an explicit update or
  migration by that same owner.
- Discovery through `workflows/dags/__init__.py` is a proof obligation separate
  from constructing the graph object.
- Command binding is optional and trigger-only. A command must never duplicate
  workflow instructions.
- Do not own Skill discovery or autonomy wiring. Hand that to
  `l9-wire-skill-into-repo` only when Skill wiring is requested.
- Do not claim commands, imports, registration, compilation, tests, or runtime
  behavior that were not actually checked.

## Operation routing

Classify the request as exactly one primary operation:

- `CREATE` — create a new canonical graph for semantics already owned by a domain capability.
- `UPDATE` — modify an existing canonical graph without forking ownership.
- `VALIDATE` — prove graph structure and importability without changing semantics.
- `REGISTER` — repair canonical registration/discovery for an existing graph.
- `COMMAND_BIND` — create or reduce a command to a thin trigger for an existing graph.
- `CONVERT` — classify a `SESSION_GUIDANCE` graph against the deprecation catalog
  and apply exactly one disposition: `DELETE_TWIN`, `ABSORB_INTO_SKILL`, or
  `CONVERT_TO_LANGGRAPH`.

`REGISTER` applies directly to `SESSION_GUIDANCE`. For `LANGGRAPH_RUNTIME`,
interpret binding as proving the canonical module and runtime entrypoint resolve
to the same graph — never as SessionDAG registration.

`CONVERT` requires `dag_id` or `dag_path`. It does not absorb GMP, harvest, docs,
or maintenance semantics. Domain owners stay with the catalog `domain_owner`.

If the request is actually "design the domain workflow", route to the domain owner
first. This Skill then encodes the resulting workflow as a graph.

## Runtime procedure

1. Validate the request with `scripts/validate_request.py`.
2. Resolve repository surfaces with `scripts/inspect_repo_surfaces.py`; executable repo truth outranks stale docs.
3. Resolve graph kind from explicit authority or `scripts/classify_graph_kind.py`.
4. For `SESSION_GUIDANCE`, load [`references/session-dag-contract.md`](references/session-dag-contract.md), reconcile the `SessionDAG`, and run `scripts/validate_session_dag_source.py`.
5. For `LANGGRAPH_RUNTIME`, load [`references/langgraph-runtime-contract.md`](references/langgraph-runtime-contract.md) and run `scripts/validate_langgraph_source.py` (package directory → `validate_package`) before any runtime claim. PASS requires `persistence_class=durable`.
6. For `SESSION_GUIDANCE`, bind discovery through `workflows/dags/__init__.py` and probe `get_session_dag()` with `scripts/probe_registration.py`.
7. For `LANGGRAPH_RUNTIME`, prove the canonical builder and executor entrypoint resolve to the same graph and that the executor compiles with a durable checkpointer and `thread_id`. Do not create SessionDAG registration as a side effect.
8. Only when requested or already owned, create or reduce a command trigger and validate it with `scripts/validate_command_trigger.py`.
9. For `CONVERT`, load [`references/session-to-langgraph-contract.md`](references/session-to-langgraph-contract.md), run `scripts/classify_conversion_disposition.py`, and emit a `StateGraph` with `scripts/convert_session_to_langgraph.py` only when disposition is `CONVERT_TO_LANGGRAPH`. Then `validate_package` on the emit directory must PASS with `persistence_class=durable`.
10. Emit a receipt with `scripts/render_receipt.py`. CONVERT receipts carry `disposition`, `target_skill`, `emitted_runtime`, and `surviving_runtime`. LANGGRAPH_RUNTIME receipts may carry optional `persistence_class`.

## Command binding rules

A bound command is trigger-only:

- references the canonical graph id and its `workflows/dags/*.py` path;
- carries no stale `.cursor-commands/workflows/dags` path;
- carries no detailed phase logic and does not restate workflow phases;
- stays short — roughly 80 lines is the ceiling.

A command-binding failure does not invalidate an otherwise valid graph unless the
command was the required deliverable.

## Consolidation rule

This Skill absorbs the former `l9-update-command` capability for **thin
command-to-graph binding** (`COMMAND_BIND`, reachable as `/dag-authoring
--bind-command`). That pack is archived under `skills/_archived/l9-update-command/`.
It does not absorb the domain behavior of GMP, skill compilation, maintenance,
verification, harvesting, or any other workflow that merely happens to use a graph.

## Resources

- [`contracts/dag-authoring-request.schema.json`](contracts/dag-authoring-request.schema.json)
- [`contracts/dag-authoring-receipt.schema.json`](contracts/dag-authoring-receipt.schema.json)
- [`policies/dag-lifecycle.yaml`](policies/dag-lifecycle.yaml)
- [`policies/graph-kinds.yaml`](policies/graph-kinds.yaml)
- [`policies/ownership-boundary.yaml`](policies/ownership-boundary.yaml)
- [`policies/command-binding.yaml`](policies/command-binding.yaml)
- [`policies/session-deprecation.yaml`](policies/session-deprecation.yaml)
- [`references/session-dag-contract.md`](references/session-dag-contract.md)
- [`references/langgraph-runtime-contract.md`](references/langgraph-runtime-contract.md)
- [`references/session-to-langgraph-contract.md`](references/session-to-langgraph-contract.md)
- [`references/dag-lifecycle-contract.md`](references/dag-lifecycle-contract.md)
- [`references/command-binding-contract.md`](references/command-binding-contract.md)

## Failure behavior

Fail closed when graph kind is unresolved, structural validation fails, required
SessionDAG registration or discovery fails, a LangGraph runtime cannot prove a
canonical executable graph, CONVERT sees a non-session source or unknown catalog
id, or CONVERT is asked to retire SessionDAG this wave. Report the smallest
repair seam. Do not widen into domain semantics, Skill wiring, or unrelated
repository surgery.

Terminal state is `PASS`, `PARTIAL`, `BLOCKED`, or `FAIL`.
