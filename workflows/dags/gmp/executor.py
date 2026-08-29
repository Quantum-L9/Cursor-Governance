"""
GMP Executor — Executor class and CLI for GMP workflow
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from workflows.dags._runtime.durable_checkpointer import open_checkpointer
from workflows.dags.gmp.graph import build_gmp_graph
from workflows.dags.gmp.state import GMPState

logger = structlog.get_logger(__name__)

DAG_ID = "gmp"


class GMPLangGraphExecutor:
    """
    Executor for GMP workflow using LangGraph.

    This provides a clean interface for running the GMP DAG
    with proper state management and durable checkpointing.
    """

    def __init__(self, workspace: Path | None = None):
        """Initialize the executor."""
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.graph = build_gmp_graph()
        self.checkpointer = open_checkpointer(DAG_ID, workspace=self.workspace)
        self.compiled = self.graph.compile(checkpointer=self.checkpointer)

    def run(
        self,
        task: str,
        tier: str = "RUNTIME",
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the GMP workflow. Returns thread_id plus state."""
        if thread_id is None:
            thread_id = f"gmp-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        initial_state = GMPState(task=task, tier=tier)
        config = {"configurable": {"thread_id": thread_id}}
        result = self.compiled.invoke(initial_state, config)

        return {"thread_id": thread_id, "state": result}

    def resume(
        self,
        thread_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume execution with user input."""
        config = {"configurable": {"thread_id": thread_id}}
        if updates:
            self.compiled.update_state(config, updates)
        result = self.compiled.invoke(None, config)
        return {"thread_id": thread_id, "state": result}

    def get_state(self, thread_id: str) -> GMPState | dict[str, Any] | None:
        """Get current state for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = self.compiled.get_state(config)
            return state.values if state else None
        except Exception:
            return None

    def get_mermaid(self) -> str:
        """Get Mermaid diagram of the graph."""
        return self.compiled.get_graph().draw_mermaid()


def compile_graph(workspace: Path | None = None):
    root = Path(workspace) if workspace else Path.cwd()
    checkpointer = open_checkpointer(DAG_ID, workspace=root)
    return build_gmp_graph().compile(checkpointer=checkpointer)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GMP LangGraph Executor")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--tier", default="RUNTIME", help="KERNEL|RUNTIME|INFRA|UX")
    parser.add_argument("--resume", help="Thread ID to resume")
    parser.add_argument("--status", help="Get status for thread ID")
    parser.add_argument("--mermaid", action="store_true", help="Print Mermaid diagram")
    parser.add_argument("--workspace", help="Workspace root for checkpoints")

    args = parser.parse_args()

    executor = GMPLangGraphExecutor(workspace=args.workspace)

    if args.mermaid:
        logger.info("output", value=executor.get_mermaid())
        return

    if args.status:
        state = executor.get_state(args.status)
        if state:
            phase = state.get("phase") if isinstance(state, dict) else getattr(state, "phase", None)
            task = state.get("task") if isinstance(state, dict) else getattr(state, "task", None)
            messages = (
                state.get("messages", [])
                if isinstance(state, dict)
                else getattr(state, "messages", [])
            )
            logger.info("phase", phase=phase)
            logger.info("task", task=task)
            for msg in messages[-10:]:
                logger.info("output", value=msg)
        else:
            logger.info("no state found for thread: {args.status}")
        return

    if not args.task and not args.resume:
        parser.print_help()
        return

    if args.resume:
        payload = executor.resume(args.resume, {})
    else:
        payload = executor.run(args.task, args.tier)

    thread_id = payload.get("thread_id")
    state = payload.get("state", payload)
    messages = (
        state.get("messages", []) if isinstance(state, dict) else getattr(state, "messages", [])
    )
    for msg in messages:
        logger.info("output", value=msg)

    phase = (
        state.get("phase", "unknown")
        if isinstance(state, dict)
        else getattr(state, "phase", "unknown")
    )
    gmp_id = state.get("gmp_id", "") if isinstance(state, dict) else getattr(state, "gmp_id", "")
    logger.info("gmp id", gmp_id=gmp_id)
    logger.info("phase", phase=phase)
    logger.info("thread id", thread_id=thread_id)
    logger.info("use --resume <thread_id> to continue")


if __name__ == "__main__":
    main()
