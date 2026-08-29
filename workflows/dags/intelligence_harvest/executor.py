from __future__ import annotations

from workflows.dags.intelligence_harvest.graph import build_intelligence_harvest_graph


def compile_graph():
    return build_intelligence_harvest_graph().compile()
