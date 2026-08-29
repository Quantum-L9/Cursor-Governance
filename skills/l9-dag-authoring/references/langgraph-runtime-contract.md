# LangGraph Runtime Contract

Use this contract only when graph kind resolves to `LANGGRAPH_RUNTIME`.

## Canonical shape

A LangGraph runtime is executable code built with `langgraph.graph.StateGraph` (or a repository-proven equivalent) and normally separates graph construction from state, routing, and node behavior when complexity warrants it.

Required proof obligations:

1. Source imports or resolves `StateGraph` from the repository's installed LangGraph surface.
2. A graph builder or canonical graph object is identifiable.
3. Every referenced node is bound.
4. Conditional routing targets resolve.
5. `graph.py` builds only and never calls `compile()`. Existence of `StateGraph.compile()` is not durability.
6. The executor is the only compile site: `compile(checkpointer=...)`.
7. Persistence class is `durable` only when `compile(checkpointer=...)` resolves to `open_checkpointer` or `SqliteSaver`. `MemorySaver` / `InMemorySaver` is `ephemeral_checkpointer` (FAIL). Missing saver, `checkpointer=None`, or an unproven name is `missing_durable_checkpointer` (FAIL). VALIDATE and CONVERT PASS only when `persistence_class=durable` is observed.
8. Durable means a file or database saver (`SqliteSaver` or equivalent) after `setup()`. Checkpoint path is workspace `.l9/langgraph/<dag_id>.sqlite` (already covered by `.l9/` in `.gitignore`).
9. Every invoke / resume / `get_state` takes `configurable.thread_id`. The caller supplies it, or the executor generates it once and returns it. Missing thread_id is `missing_thread_id` (FAIL). Resume after a checkpoint is `update_state` (when applying values) then `invoke(None, config)` — never replay saved values as a fresh START input.
10. Any public executor/runner entrypoint points to the same canonical graph.
11. No `SessionDAG` registry entry is created merely because the artifact is a graph.
12. Nodes are documented as re-enterable. Authoring does not implement domain idempotency.

Typed remaining_action codes: `missing_durable_checkpointer`, `ephemeral_checkpointer`, `missing_thread_id`, `builder_compiles_graph`, `compile_not_in_executor`.

`workflows/dags/gmp/` is the current exemplar of a modular LangGraph runtime: graph, state, routing, nodes, and executor remain domain-owned. The shared checkpointer helper is `workflows/dags/_runtime/durable_checkpointer.py`.

## Persistence planes

Three planes stay distinct:

- LangGraph checkpointer — thread resume for one graph run
- Program Execution typed state — campaign authority
- Graphiti — episodic memory

Do not add a LangGraph Store. Do not treat the checkpointer as memory SSOT or PE authority.

## Boundary

`l9-dag-authoring` owns graph mechanics, lifecycle validation, and LANGGRAPH_RUNTIME persistence mechanics. The domain owner owns node semantics, state semantics, side effects, permissions, interrupt placement, and terminal meaning.
