# SessionDAG Contract

Use `workflows.session.interface.SessionDAG`, `SessionNode`, and `SessionEdge` as the canonical L9 authoring types when that interface exists.

A canonical DAG module must:

1. Define one clearly named canonical `SessionDAG` object for the workflow.
2. Use unique node ids.
3. Use only edge endpoints that resolve to declared node ids.
4. Provide a valid entry node according to the live interface contract.
5. Validate successfully before registration.
6. Register through `workflows.session.registry.register_session_dag()`.
7. Become discoverable through `workflows/dags/__init__.py` when registry discovery depends on module import.

Do not create an `ACTIVE_DAGS` table, plain-dict registry, or second registration framework.

When the target runtime is LangGraph rather than SessionDAG, do not silently coerce it. Preserve the domain runtime and use SessionDAG only if the repository explicitly requires a registry/discovery projection. Runtime taxonomy is not owned by this Skill.
