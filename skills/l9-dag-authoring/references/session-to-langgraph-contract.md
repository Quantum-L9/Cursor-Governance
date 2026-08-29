# SessionDAG to LangGraph CONVERT contract

Use this contract only when the request operation is `CONVERT`.

## Law

1. Classify graph kind first with `scripts/classify_graph_kind.py`. Continue only when the source is `SESSION_GUIDANCE`.
2. Look up `dag_id` in `policies/session-deprecation.yaml`. Unknown id is `BLOCKED`.
3. Emit a `StateGraph` only when disposition is `CONVERT_TO_LANGGRAPH`.
4. `DELETE_TWIN` and `ABSORB_INTO_SKILL` produce a receipt and no new graph.
5. Never call `register_session_dag` from an emitted runtime.
6. Never delete the source SessionDAG in the same CONVERT step.
7. `allow_session_retire` is false for this wave. A true value is refused.

## Mapping

- `SessionNode.id` → `add_node` name
- `action` that is an existing repo script path → node function invokes that script
- `action` that is prose → fail closed
- `SessionEdge` with no condition → `add_edge`
- `SessionEdge.condition` → `add_conditional_edges`
- `entry_node` → `START`
- terminal nodes → `END`

When `proof_path` is a skill IR (`meta/skill-ir.json`), the IR `workflow.nodes` ids are the builder authority.

## Proof

`scripts/validate_langgraph_source.py` structural `validate` must PASS on the emitted `graph.py`, and `validate_package` must PASS on the emit directory with `persistence_class=durable`. The SessionDAG adapter stays registered until a later retirement plan.
