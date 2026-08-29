from workflows.session.interface import SessionDAG, SessionNode

OK_DAG = SessionDAG(
    id="fixture-convert-ok",
    name="Ok",
    version="1",
    description="script action may emit",
    nodes=[
        SessionNode(
            id="RUN",
            name="Run",
            description="script",
            action="skills/l9-dag-authoring/scripts/validate_request.py",
            metadata={"ir_kind": "deterministic"},
        ),
    ],
    edges=[],
    entry_node="RUN",
)
