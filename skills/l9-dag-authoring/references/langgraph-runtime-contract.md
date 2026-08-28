# LangGraph Runtime Contract

Use this contract only when graph kind resolves to `LANGGRAPH_RUNTIME`.

## Canonical shape

A LangGraph runtime is executable code built with `langgraph.graph.StateGraph` (or a repository-proven equivalent) and normally separates graph construction from state, routing, and node behavior when complexity warrants it.

Required proof obligations:

1. Source imports or resolves `StateGraph` from the repository's installed LangGraph surface.
2. A graph builder or canonical graph object is identifiable.
3. Every referenced node is bound.
4. Conditional routing targets resolve.
5. The graph compiles when the repository runtime is available.
6. Any public executor/runner entrypoint points to the same canonical graph.
7. No `SessionDAG` registry entry is created merely because the artifact is a graph.

`workflows/dags/gmp/` is the current exemplar of a modular LangGraph runtime: graph, state, routing, nodes, and executor remain domain-owned.

## Boundary

`l9-dag-authoring` owns graph mechanics and lifecycle validation. The domain owner owns node semantics, state semantics, side effects, permissions, and terminal meaning.
