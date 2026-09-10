"""V2 on-disk sqlite compatibility for the bound l9-graphite-memory runtime.

GitHub ``v2.3.1`` ``SQLiteRecordStore.initialize()`` issues
``CREATE INDEX idx_outbox_lease ON outbox_events(status, lease_expires_at)``
before the ``ALTER TABLE`` that adds ``lease_expires_at``. A V2.2 / schema-4
ledger (the live Cursor store) therefore fails every CLI and MCP boot with
``sqlite3.OperationalError: no such column: lease_expires_at``.

This module adds the V2.3 columns first. It does not import the memory
package, does not grant namespaces, and does not open a second store. Callers
are the control-plane client and the Cursor MCP installer so both adapters
see one upgraded ledger.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path("~/.local/share/l9-memory")
DEFAULT_DB_NAME = "memory.sqlite3"

#: Columns 2.3.1 ``initialize()`` indexes before it can ALTER them onto a
#: pre-2.3 ``outbox_events`` table.
OUTBOX_LEASE_COLUMNS: tuple[str, ...] = ("lease_id", "lease_owner", "lease_expires_at")

_DEBUG_LOG = Path(__file__).resolve().parents[2] / ".cursor" / "debug-01ef49.log"


def resolve_sqlite_path(env: Mapping[str, str] | None = None) -> Path:
    """The sqlite ledger path the bound runtime will open (env + package default)."""

    environ = env if env is not None else os.environ
    explicit = str(environ.get("L9_MEMORY_DATABASE_PATH") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    data_dir = Path(str(environ.get("L9_MEMORY_DATA_DIR") or DEFAULT_DATA_DIR)).expanduser()
    return data_dir / DEFAULT_DB_NAME


def _debug(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        _DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "sessionId": "01ef49",
            "id": f"log_{int(time.time())}_{hypothesis_id}",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "runId": "v2-align",
            "hypothesisId": hypothesis_id,
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        # Best-effort debug NDJSON; a log-write failure must not fail store preflight.
        pass
    # #endregion


def prepare_v2_sqlite_store(
    path: Path | None = None, *, env: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Make a V2.2 schema-4 ledger openable by V2.3+ ``initialize()``.

    Absent path → ``absent`` (a first-run 2.3.1 process creates the file).
    Existing file → add any missing lease / references columns, then ``ready``
    or ``migrated``. Never deletes rows.
    """

    target = path if path is not None else resolve_sqlite_path(env)
    receipt: dict[str, Any] = {"path": str(target), "altered": [], "status": "absent"}
    if not target.is_file():
        _debug("H1", "store_compat.py:prepare", "sqlite ledger absent", receipt)
        return receipt
    connection = sqlite3.connect(str(target))
    altered: list[str] = []
    try:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "outbox_events" in tables:
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(outbox_events)")
            }
            for column in OUTBOX_LEASE_COLUMNS:
                if column not in columns:
                    connection.execute(f"ALTER TABLE outbox_events ADD COLUMN {column} TEXT")
                    altered.append(f"outbox_events.{column}")
        if "memory_records" in tables:
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(memory_records)")
            }
            if "references_json" not in columns:
                connection.execute(
                    "ALTER TABLE memory_records ADD COLUMN references_json "
                    "TEXT NOT NULL DEFAULT '[]'"
                )
                altered.append("memory_records.references_json")
        connection.commit()
    except sqlite3.Error as exc:
        receipt["status"] = "error"
        receipt["error"] = str(exc)
        _debug("H1", "store_compat.py:prepare", "sqlite preflight failed", receipt)
        return receipt
    finally:
        connection.close()
    receipt["altered"] = altered
    receipt["status"] = "migrated" if altered else "ready"
    _debug("H1", "store_compat.py:prepare", "sqlite V2 preflight", receipt)
    return receipt


__all__ = [
    "DEFAULT_DATA_DIR",
    "DEFAULT_DB_NAME",
    "OUTBOX_LEASE_COLUMNS",
    "prepare_v2_sqlite_store",
    "resolve_sqlite_path",
]
