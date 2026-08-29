from workflows.session.interface import SessionDAG, SessionNode
from workflows.session.registry import register_session_dag

PROSE_DAG = SessionDAG(
    id="prose-convert-fixture",
    name="Prose",
    version="1",
    description="prose action must fail closed",
    nodes=[
        SessionNode(
            id="START_NODE",
            name="Start",
            description="prose",
            action="walk the donor and invent a harvest.json",
        ),
    ],
    edges=[],
    entry_node="START_NODE",
)
register_session_dag(PROSE_DAG)
