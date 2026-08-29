"""Workspace-scoped durable LangGraph checkpointer.

Owned by l9-dag-authoring persistence mechanics. Does not import GMP or harvest.

`SqliteSaver.from_conn_string` is a context manager that closes the connection
on exit. Executors need a live connection, so this helper opens sqlite3 itself.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def checkpoint_path(dag_id: str, *, workspace: Path) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in dag_id)
    return Path(workspace) / ".l9" / "langgraph" / f"{safe}.sqlite"


def open_checkpointer(dag_id: str, *, workspace: Path) -> SqliteSaver:
    path = checkpoint_path(dag_id, workspace=workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    saver = SqliteSaver(conn)
    setup = getattr(saver, "setup", None)
    if callable(setup):
        setup()
    return saver
