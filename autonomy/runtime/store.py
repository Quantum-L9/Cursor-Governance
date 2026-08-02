from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from autonomy.runtime.timeutil import utc_now_text


class RuntimeStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    base_sha TEXT NOT NULL,
                    campaign_json TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS actions (
                    campaign_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mutation INTEGER NOT NULL,
                    resource_class TEXT NOT NULL,
                    priority_weight REAL NOT NULL,
                    critical_depth INTEGER NOT NULL,
                    action_json TEXT NOT NULL,
                    assigned_agent_id TEXT,
                    active_lease_id TEXT,
                    result_artifact_id TEXT,
                    failure_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (campaign_id, action_id),
                    FOREIGN KEY (campaign_id)
                        REFERENCES campaigns(campaign_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS leases (
                    lease_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    graph_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    base_sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_heartbeat_at TEXT NOT NULL,
                    revoked_reason TEXT,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY (campaign_id, action_id)
                        REFERENCES actions(campaign_id, action_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_leases_campaign_status
                    ON leases(campaign_id, status);
                CREATE INDEX IF NOT EXISTS idx_leases_action_status
                    ON leases(campaign_id, action_id, status);
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    lease_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    resource_key TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    exclusive INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    released_at TEXT,
                    FOREIGN KEY (lease_id)
                        REFERENCES leases(lease_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_claims_resource_status
                    ON claims(campaign_id, resource_key, status);
                CREATE TABLE IF NOT EXISTS heartbeats (
                    heartbeat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lease_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_json TEXT NOT NULL,
                    observed_base_sha TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (lease_id)
                        REFERENCES leases(lease_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    graph_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    base_sha TEXT NOT NULL,
                    target_sha TEXT,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    invalidated_at TEXT,
                    invalidation_reason TEXT,
                    FOREIGN KEY (lease_id)
                        REFERENCES leases(lease_id)
                        ON DELETE RESTRICT
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_action_status
                    ON artifacts(campaign_id, action_id, status);
                CREATE TABLE IF NOT EXISTS receipts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT NOT NULL UNIQUE,
                    campaign_id TEXT NOT NULL,
                    graph_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action_id TEXT,
                    lease_id TEXT,
                    artifact_id TEXT,
                    event_json TEXT NOT NULL,
                    previous_receipt_hash TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,
                    signature TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_receipts_campaign_sequence
                    ON receipts(campaign_id, sequence);
                CREATE TABLE IF NOT EXISTS tool_decisions (
                    decision_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    resource TEXT,
                    allowed INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tool_decisions_campaign
                    ON tool_decisions(campaign_id, created_at);
                """
            )

    def register_campaign(
        self,
        campaign: Mapping[str, Any],
        graph: Mapping[str, Any],
    ) -> None:
        campaign_id = str(campaign["campaign_id"])
        graph_id = str(graph["graph_id"])
        base_sha = str(campaign["base_state"]["commit_sha"])
        now = utc_now_text()
        with self.transaction() as connection:
            existing = connection.execute(
                """
                SELECT campaign_json, graph_json
                FROM campaigns
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
            campaign_json = canonical_dump(campaign)
            graph_json = canonical_dump(graph)
            if existing is not None:
                if (
                    existing["campaign_json"] != campaign_json
                    or existing["graph_json"] != graph_json
                ):
                    raise ValueError(
                        f"Campaign {campaign_id!r} is already registered with different contracts"
                    )
                return
            connection.execute(
                """
                INSERT INTO campaigns (
                    campaign_id,
                    graph_id,
                    state,
                    base_sha,
                    campaign_json,
                    graph_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    graph_id,
                    "LOCKED",
                    base_sha,
                    campaign_json,
                    graph_json,
                    now,
                    now,
                ),
            )
            critical_depth = graph.get("critical_depth", {})
            for action in graph["actions"]:
                connection.execute(
                    """
                    INSERT INTO actions (
                        campaign_id,
                        action_id,
                        role,
                        kind,
                        status,
                        mutation,
                        resource_class,
                        priority_weight,
                        critical_depth,
                        action_json,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        campaign_id,
                        action["id"],
                        action["role"],
                        action["kind"],
                        "PENDING",
                        int(bool(action["mutation"])),
                        action["resource_class"],
                        float(action.get("priority_weight", 1.0)),
                        int(critical_depth.get(action["id"], 1)),
                        canonical_dump(action),
                        now,
                        now,
                    ),
                )

    def get_campaign(self, campaign_id: str) -> sqlite3.Row:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM campaigns
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown campaign: {campaign_id}")
        return row

    def get_action(
        self,
        campaign_id: str,
        action_id: str,
    ) -> sqlite3.Row:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM actions
                WHERE campaign_id = ? AND action_id = ?
                """,
                (campaign_id, action_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown action {action_id!r} in campaign {campaign_id!r}")
        return row

    def list_actions(
        self,
        campaign_id: str,
    ) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT *
                    FROM actions
                    WHERE campaign_id = ?
                    ORDER BY action_id
                    """,
                    (campaign_id,),
                )
            )

    def set_campaign_state(
        self,
        campaign_id: str,
        state: str,
    ) -> None:
        with self.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE campaigns
                SET state = ?, updated_at = ?
                WHERE campaign_id = ?
                """,
                (state, utc_now_text(), campaign_id),
            ).rowcount
            if updated != 1:
                raise KeyError(f"Unknown campaign: {campaign_id}")

    def set_action_status(
        self,
        campaign_id: str,
        action_id: str,
        status: str,
        *,
        agent_id: str | None = None,
        lease_id: str | None = None,
        artifact_id: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        with self.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE actions
                SET
                    status = ?,
                    assigned_agent_id = COALESCE(?, assigned_agent_id),
                    active_lease_id = ?,
                    result_artifact_id = COALESCE(
                        ?,
                        result_artifact_id
                    ),
                    failure_reason = ?,
                    updated_at = ?
                WHERE campaign_id = ? AND action_id = ?
                """,
                (
                    status,
                    agent_id,
                    lease_id,
                    artifact_id,
                    failure_reason,
                    utc_now_text(),
                    campaign_id,
                    action_id,
                ),
            ).rowcount
            if updated != 1:
                raise KeyError(f"Unknown action {action_id!r} in campaign {campaign_id!r}")

    def decode_campaign(self, campaign_id: str) -> dict[str, Any]:
        row = self.get_campaign(campaign_id)
        return json.loads(row["campaign_json"])

    def decode_graph(self, campaign_id: str) -> dict[str, Any]:
        row = self.get_campaign(campaign_id)
        return json.loads(row["graph_json"])

    def decode_action(
        self,
        campaign_id: str,
        action_id: str,
    ) -> dict[str, Any]:
        row = self.get_action(campaign_id, action_id)
        return json.loads(row["action_json"])


def canonical_dump(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
