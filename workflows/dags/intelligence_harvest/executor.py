from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from workflows.dags._runtime.durable_checkpointer import open_checkpointer
from workflows.dags.intelligence_harvest.graph import build_intelligence_harvest_graph

DAG_ID = "intelligence_harvest"


def compile_graph(workspace: Path | None = None):
    root = Path(workspace) if workspace else Path.cwd()
    checkpointer = open_checkpointer(DAG_ID, workspace=root)
    return build_intelligence_harvest_graph().compile(checkpointer=checkpointer)


class HarvestExecutor:
    def __init__(self, workspace: Path | None = None):
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.checkpointer = open_checkpointer(DAG_ID, workspace=self.workspace)
        self.compiled = build_intelligence_harvest_graph().compile(checkpointer=self.checkpointer)

    def run(
        self,
        initial: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        if thread_id is None:
            thread_id = f"{DAG_ID}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        config = {"configurable": {"thread_id": thread_id}}
        state = self.compiled.invoke(initial or {}, config)
        return {"thread_id": thread_id, "state": state}

    def resume(self, thread_id: str, updates: dict[str, Any] | None = None) -> dict[str, Any]:
        config = {"configurable": {"thread_id": thread_id}}
        if updates:
            self.compiled.update_state(config, updates)
        state = self.compiled.invoke(None, config)
        return {"thread_id": thread_id, "state": state}

    def get_state(self, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.compiled.get_state(config)
        return snapshot.values if snapshot else None
