"""V2.2 schema-4 ledgers must become openable by V2.3 initialize()."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ops.memory.store_compat import (
    OUTBOX_LEASE_COLUMNS,
    prepare_v2_sqlite_store,
    resolve_sqlite_path,
)


def _schema4(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    connection.execute(
        """
        CREATE TABLE outbox_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            namespace TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            next_attempt_at TEXT NOT NULL,
            last_error TEXT,
            created_at TEXT NOT NULL,
            delivered_at TEXT,
            event_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE memory_records (
            record_id TEXT PRIMARY KEY,
            content TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def test_resolve_honors_explicit_database_path(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("L9_MEMORY_DATABASE_PATH", str(target))
    assert resolve_sqlite_path() == target


def test_absent_ledger_is_reported_not_created(tmp_path: Path) -> None:
    target = tmp_path / "missing.sqlite3"
    receipt = prepare_v2_sqlite_store(target)
    assert receipt["status"] == "absent"
    assert receipt["altered"] == []
    assert not target.exists()


def test_schema4_outbox_gains_lease_columns_so_v23_index_can_land(tmp_path: Path) -> None:
    target = tmp_path / "memory.sqlite3"
    _schema4(target)
    receipt = prepare_v2_sqlite_store(target)
    assert receipt["status"] == "migrated"
    assert receipt["altered"] == [
        "outbox_events.lease_id",
        "outbox_events.lease_owner",
        "outbox_events.lease_expires_at",
        "memory_records.references_json",
    ]
    connection = sqlite3.connect(str(target))
    try:
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outbox_lease ON outbox_events(status, lease_expires_at)"
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(outbox_events)")}
    finally:
        connection.close()
    assert set(OUTBOX_LEASE_COLUMNS) <= columns
    again = prepare_v2_sqlite_store(target)
    assert again["status"] == "ready"
    assert again["altered"] == []
