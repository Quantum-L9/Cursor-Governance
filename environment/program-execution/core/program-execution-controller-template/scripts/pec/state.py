from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .common import verification_mechanisms_from_card

TASK_STATES = {
    "WAITING",
    "BLOCKED",
    "ELIGIBLE",
    "LEASED",
    "PREPARED",
    "CONTRACTED",
    "EXECUTING",
    "SUBMITTED",
    "VERIFYING",
    "PASSED_LOCAL",
    "FAILED",
    "STALE",
    "CANCELLED",
    "COMPLETED",
}
ALLOWED_TRANSITIONS = {
    # WAITING: definition complete, runtime prerequisites not yet resolved into
    # a claim (ADR-0023). Not a failure state. BLOCKED stays in the enum for
    # legacy persisted runtimes and genuine-blocker representation, but it is
    # no longer the initialization state for a complete task.
    "WAITING": {"ELIGIBLE", "STALE", "CANCELLED"},
    "BLOCKED": {"ELIGIBLE", "CANCELLED", "STALE"},
    "ELIGIBLE": {"WAITING", "BLOCKED", "LEASED", "COMPLETED", "CANCELLED", "STALE"},
    "LEASED": {"PREPARED", "STALE", "FAILED", "CANCELLED"},
    "PREPARED": {"CONTRACTED", "STALE", "FAILED", "CANCELLED"},
    "CONTRACTED": {"EXECUTING", "SUBMITTED", "STALE", "FAILED", "CANCELLED"},
    "EXECUTING": {"SUBMITTED", "STALE", "FAILED", "CANCELLED"},
    "SUBMITTED": {"VERIFYING", "STALE", "FAILED"},
    "VERIFYING": {"PASSED_LOCAL", "FAILED", "STALE"},
    "PASSED_LOCAL": {"COMPLETED", "STALE", "CANCELLED"},
    "FAILED": {"ELIGIBLE", "EXECUTING", "SUBMITTED", "STALE", "CANCELLED"},
    "STALE": {"ELIGIBLE", "CANCELLED"},
    "CANCELLED": set(),
    "COMPLETED": set(),
}


class StateDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS repositories (
              repository_id TEXT PRIMARY KEY,
              target_id TEXT NOT NULL,
              local_path TEXT,
              current_branch TEXT,
              head_sha TEXT,
              dirty INTEGER NOT NULL DEFAULT 0,
              remote_url TEXT,
              reconciled_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              wave_id TEXT NOT NULL,
              workstream_id TEXT NOT NULL,
              target_id TEXT NOT NULL,
              repository_id TEXT,
              execution_kind TEXT NOT NULL,
              objective TEXT NOT NULL,
              dependencies TEXT NOT NULL,
              required_decisions TEXT NOT NULL,
              blocking_unknowns TEXT NOT NULL,
              required_evidence TEXT NOT NULL,
              completion_gates TEXT NOT NULL,
              authorization_ceiling TEXT NOT NULL,
              required_acceptance TEXT NOT NULL,
              verification_mechanisms TEXT NOT NULL,
              required_validation_commands TEXT NOT NULL,
              risk_tier TEXT NOT NULL,
              definition_status TEXT NOT NULL,
              runtime_state TEXT NOT NULL,
              scope_status TEXT NOT NULL,
              source_contract_path TEXT,
              source_contract_digest TEXT,
              rendered_contract_path TEXT,
              rendered_contract_digest TEXT,
              base_sha TEXT,
              branch TEXT,
              worktree TEXT,
              lease_id TEXT,
              attempts INTEGER NOT NULL DEFAULT 0,
              last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS gates (
              id TEXT PRIMARY KEY,
              definition TEXT NOT NULL,
              result TEXT NOT NULL,
              blocking INTEGER NOT NULL,
              evidence_ids TEXT NOT NULL,
              evaluation_receipt TEXT
            );
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              evidence_ids TEXT NOT NULL,
              source TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS unknowns (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              blocks TEXT NOT NULL,
              evidence_ids TEXT NOT NULL,
              source TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS waivers (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leases (
              lease_id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              repository_id TEXT NOT NULL,
              holder TEXT NOT NULL,
              base_sha TEXT NOT NULL,
              branch TEXT NOT NULL,
              worktree TEXT,
              contract_digest TEXT,
              issued_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              active INTEGER NOT NULL
            );
            DROP INDEX IF EXISTS active_repo_lease;
            CREATE UNIQUE INDEX IF NOT EXISTS active_task_lease
              ON leases(task_id) WHERE active = 1;
            CREATE TABLE IF NOT EXISTS attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id TEXT NOT NULL,
              attempt_number INTEGER NOT NULL,
              receipt_path TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(task_id, attempt_number)
            );
            CREATE TABLE IF NOT EXISTS approvals (
              approval_id TEXT PRIMARY KEY,
              payload TEXT NOT NULL
            );
            """
        )
        task_columns = {str(row["name"]) for row in self.conn.execute("PRAGMA table_info(tasks)")}
        if "verification_mechanisms" not in task_columns:
            self.conn.execute(
                "ALTER TABLE tasks ADD COLUMN verification_mechanisms TEXT NOT NULL DEFAULT '[]'"
            )
            self._backfill_verification_mechanisms()
        self.conn.commit()

    def _backfill_verification_mechanisms(self) -> None:
        """Populate the new column for rows frozen before it existed.

        The default `'[]'` is a schema placeholder, not an answer. Both contract
        schemas require `verification_mechanisms` with `minItems: 1`, so a task
        left at the default renders a contract that fails validation and the
        Controller reports `contract: FAIL` at verify -- for every task, on a
        runtime that was healthy before the upgrade. Without this, the migration
        would make an in-flight campaign unfinishable rather than merely
        uninformed.

        The answer is already frozen beside this database. The program lock
        carries each task's authored card under `source`, and
        `normalize_blueprint()` derives the mechanisms from exactly that card's
        `validation` list, so reading it here reproduces the value the next
        relock would write -- without consulting the Blueprint, which may no
        longer be on this disk.

        Deliberately silent when there is nothing to read: a database with no
        lock beside it is a fresh or test runtime with no legacy rows to
        repair. A task whose card declares no validation stays `'[]'`, which is
        the honest answer for it; acceptance now refuses to seal such a task
        when it is mutating, so it cannot recur going forward.
        """
        lock_path = self.path.parent / "program-lock.json"
        if not lock_path.is_file():
            return
        try:
            locked = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(locked, dict):
            return
        known = {str(row["id"]) for row in self.conn.execute("SELECT id FROM tasks")}
        for task in locked.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            task_id = str(task.get("id") or "")
            if task_id not in known:
                continue
            mechanisms = verification_mechanisms_from_card(task.get("source"))
            if not mechanisms:
                continue
            self.conn.execute(
                "UPDATE tasks SET verification_mechanisms=? WHERE id=?",
                (json.dumps(mechanisms, sort_keys=True), task_id),
            )

    def close(self) -> None:
        self.conn.close()

    def set_meta(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",  # noqa: E501
            (key, json.dumps(value, sort_keys=True)),
        )
        self.conn.commit()

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row["value"])

    def upsert_repository(self, repository_id: str, target_id: str, **fields: Any) -> None:
        existing = self.repository(repository_id) or {
            "repository_id": repository_id,
            "target_id": target_id,
        }
        existing.update(fields)
        self.conn.execute(
            """
            INSERT INTO repositories(
                repository_id, target_id, local_path, current_branch,
                head_sha, dirty, remote_url, reconciled_at
            )
            VALUES(
                :repository_id, :target_id, :local_path, :current_branch,
                :head_sha, :dirty, :remote_url, :reconciled_at
            )
            ON CONFLICT(repository_id) DO UPDATE SET
                target_id=excluded.target_id,
                local_path=excluded.local_path,
                current_branch=excluded.current_branch,
                head_sha=excluded.head_sha,
                dirty=excluded.dirty,
                remote_url=excluded.remote_url,
                reconciled_at=excluded.reconciled_at
            """,
            {
                "repository_id": repository_id,
                "target_id": target_id,
                "local_path": existing.get("local_path"),
                "current_branch": existing.get("current_branch"),
                "head_sha": existing.get("head_sha"),
                "dirty": int(bool(existing.get("dirty"))),
                "remote_url": existing.get("remote_url"),
                "reconciled_at": existing.get("reconciled_at"),
            },
        )
        self.conn.commit()

    def repository(self, repository_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM repositories WHERE repository_id=?", (repository_id,)
        ).fetchone()
        return None if row is None else dict(row)

    def repositories(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute("SELECT * FROM repositories ORDER BY repository_id")
        ]

    @staticmethod
    def _json_fields() -> set[str]:
        return {
            "dependencies",
            "required_decisions",
            "blocking_unknowns",
            "required_evidence",
            "completion_gates",
            "authorization_ceiling",
            "required_acceptance",
            "verification_mechanisms",
            "required_validation_commands",
        }

    def upsert_task(self, task: dict[str, Any]) -> None:
        current = self.task(task["id"])
        payload = {
            "id": task["id"],
            "title": task["title"],
            "wave_id": task["wave_id"],
            "workstream_id": task["workstream_id"],
            "target_id": task["target_id"],
            "repository_id": task.get("repository_id"),
            "execution_kind": task["execution_kind"],
            "objective": task["objective"],
            "dependencies": json.dumps(task.get("dependencies") or []),
            "required_decisions": json.dumps(task.get("required_decisions") or []),
            "blocking_unknowns": json.dumps(task.get("blocking_unknowns") or []),
            "required_evidence": json.dumps(task.get("required_evidence") or []),
            "completion_gates": json.dumps(task.get("completion_gates") or []),
            "authorization_ceiling": json.dumps(
                task.get("authorization_ceiling") or {}, sort_keys=True
            ),
            "required_acceptance": json.dumps(task.get("required_acceptance") or []),
            "verification_mechanisms": json.dumps(
                task.get("verification_mechanisms") or [], sort_keys=True
            ),
            "required_validation_commands": json.dumps(
                task.get("required_validation_commands") or []
            ),
            "risk_tier": task["risk_tier"],
            "definition_status": task["definition_status"],
            "runtime_state": current["runtime_state"] if current else "WAITING",
            "scope_status": current["scope_status"]
            if current
            else ("not_required" if task["execution_kind"] == "program_control" else "intent_only"),
            "source_contract_path": current["source_contract_path"] if current else None,
            "source_contract_digest": current["source_contract_digest"] if current else None,
            "rendered_contract_path": current["rendered_contract_path"] if current else None,
            "rendered_contract_digest": current["rendered_contract_digest"] if current else None,
            "base_sha": current["base_sha"] if current else None,
            "branch": current["branch"] if current else None,
            "worktree": current["worktree"] if current else None,
            "lease_id": current["lease_id"] if current else None,
            "attempts": current["attempts"] if current else 0,
            "last_error": current["last_error"] if current else None,
        }
        columns = ",".join(payload)
        placeholders = ",".join(f":{key}" for key in payload)
        updates = ",".join(
            f"{key}=excluded.{key}"
            for key in payload
            if key
            not in {
                "id",
                "runtime_state",
                "scope_status",
                "source_contract_path",
                "source_contract_digest",
                "rendered_contract_path",
                "rendered_contract_digest",
                "base_sha",
                "branch",
                "worktree",
                "lease_id",
                "attempts",
                "last_error",
            }
        )
        # Identifiers come from the hardcoded payload keys above; values are
        # bound parameters.
        self.conn.execute(
            f"INSERT INTO tasks({columns}) VALUES({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",  # noqa: E501  # nosec B608
            payload,
        )
        self.conn.commit()

    def _task_row(self, row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        for key in self._json_fields():
            value[key] = json.loads(value[key])
        return value

    def task(self, task_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return None if row is None else self._task_row(row)

    def tasks(self) -> list[dict[str, Any]]:
        return [self._task_row(row) for row in self.conn.execute("SELECT * FROM tasks ORDER BY id")]

    def transition_task(
        self, task_id: str, new_state: str, *, last_error: str | None = None
    ) -> None:
        if new_state not in TASK_STATES:
            raise ValueError(f"invalid task state: {new_state}")
        task = self.task(task_id)
        if task is None:
            raise ValueError(f"unknown task: {task_id}")
        current = task["runtime_state"]
        if new_state != current and new_state not in ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"invalid task transition: {current} -> {new_state}")
        self.conn.execute(
            "UPDATE tasks SET runtime_state=?, last_error=? WHERE id=?",
            (new_state, last_error, task_id),
        )
        self.conn.commit()

    def update_task(self, task_id: str, **fields: Any) -> None:
        allowed = {
            "scope_status",
            "source_contract_path",
            "source_contract_digest",
            "rendered_contract_path",
            "rendered_contract_digest",
            "base_sha",
            "branch",
            "worktree",
            "lease_id",
            "attempts",
            "last_error",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unsupported task fields: {sorted(unknown)}")
        if not fields:
            return
        sets = ",".join(f"{name}=?" for name in fields)
        # Column names are validated against the `allowed` set above; values
        # are bound parameters.
        self.conn.execute(
            f"UPDATE tasks SET {sets} WHERE id=?",  # nosec B608
            [*fields.values(), task_id],
        )
        self.conn.commit()

    def upsert_gate(self, gate: dict[str, Any]) -> None:
        existing = self.gate(gate["id"])
        self.conn.execute(
            """
            INSERT INTO gates(
                id, definition, result, blocking, evidence_ids, evaluation_receipt
            ) VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                definition=excluded.definition,
                blocking=excluded.blocking
            """,
            (
                gate["id"],
                json.dumps(gate, sort_keys=True),
                existing["result"] if existing else "UNKNOWN",
                int(bool(gate.get("blocking", True))),
                json.dumps(existing["evidence_ids"] if existing else []),
                existing.get("evaluation_receipt") if existing else None,
            ),
        )
        self.conn.commit()

    def gate(self, gate_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM gates WHERE id=?", (gate_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["definition"] = json.loads(item["definition"])
        item["evidence_ids"] = json.loads(item["evidence_ids"])
        return item

    def gates(self) -> list[dict[str, Any]]:
        return [
            self.gate(row["id"]) for row in self.conn.execute("SELECT id FROM gates ORDER BY id")
        ]  # type: ignore[list-item]

    def set_gate(self, gate_id: str, result: str, evidence_ids: list[str], receipt: str) -> None:
        self.conn.execute(
            "UPDATE gates SET result=?, evidence_ids=?, evaluation_receipt=? WHERE id=?",
            (result, json.dumps(evidence_ids), receipt, gate_id),
        )
        self.conn.commit()

    def upsert_decision(self, item: dict[str, Any]) -> None:
        existing = self.decision(item["id"])
        status = existing["status"] if existing else item.get("status", "pending")
        evidence_ids = existing["evidence_ids"] if existing else item.get("evidence_ids", [])
        self.conn.execute(
            "INSERT INTO decisions(id,status,evidence_ids,source) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET source=excluded.source",  # noqa: E501
            (item["id"], status, json.dumps(evidence_ids), json.dumps(item, sort_keys=True)),
        )
        self.conn.commit()

    def decision(self, decision_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["evidence_ids"] = json.loads(item["evidence_ids"])
        item["source"] = json.loads(item["source"])
        return item

    def decisions(self) -> list[dict[str, Any]]:
        return [
            self.decision(row["id"])
            for row in self.conn.execute("SELECT id FROM decisions ORDER BY id")
        ]  # type: ignore[list-item]

    def set_decision(self, decision_id: str, status: str, evidence_ids: list[str]) -> None:
        if status not in {"pending", "accepted", "rejected", "superseded"}:
            raise ValueError(f"invalid decision status: {status}")
        self.conn.execute(
            "UPDATE decisions SET status=?, evidence_ids=? WHERE id=?",
            (status, json.dumps(evidence_ids), decision_id),
        )
        self.conn.commit()

    def upsert_unknown(self, item: dict[str, Any]) -> None:
        existing = self.unknown(item["id"])
        status = existing["status"] if existing else item.get("status", "open")
        evidence_ids = (
            existing["evidence_ids"] if existing else item.get("resolution_evidence_ids", [])
        )
        self.conn.execute(
            "INSERT INTO unknowns(id,status,blocks,evidence_ids,source) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET blocks=excluded.blocks,source=excluded.source",  # noqa: E501
            (
                item["id"],
                status,
                json.dumps(item.get("blocks") or []),
                json.dumps(evidence_ids),
                json.dumps(item, sort_keys=True),
            ),
        )
        self.conn.commit()

    def unknown(self, unknown_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM unknowns WHERE id=?", (unknown_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["blocks"] = json.loads(item["blocks"])
        item["evidence_ids"] = json.loads(item["evidence_ids"])
        item["source"] = json.loads(item["source"])
        return item

    def unknowns(self) -> list[dict[str, Any]]:
        return [
            self.unknown(row["id"])
            for row in self.conn.execute("SELECT id FROM unknowns ORDER BY id")
        ]  # type: ignore[list-item]

    def set_unknown(self, unknown_id: str, status: str, evidence_ids: list[str]) -> None:
        if status not in {"open", "resolved", "accepted_risk", "superseded"}:
            raise ValueError(f"invalid unknown status: {status}")
        self.conn.execute(
            "UPDATE unknowns SET status=?, evidence_ids=? WHERE id=?",
            (status, json.dumps(evidence_ids), unknown_id),
        )
        self.conn.commit()

    def upsert_waiver(self, item: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO waivers(id,payload) VALUES(?,?)",
            (item["id"], json.dumps(item, sort_keys=True)),
        )
        self.conn.commit()

    def waiver(self, waiver_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT payload FROM waivers WHERE id=?", (waiver_id,)).fetchone()
        return None if row is None else json.loads(row["payload"])

    def waivers(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["payload"])
            for row in self.conn.execute("SELECT payload FROM waivers ORDER BY id")
        ]

    def upsert_evidence(self, item: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO evidence(id,payload) VALUES(?,?)",
            (item["id"], json.dumps(item, sort_keys=True)),
        )
        self.conn.commit()

    def evidence(self, evidence_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload FROM evidence WHERE id=?", (evidence_id,)
        ).fetchone()
        return None if row is None else json.loads(row["payload"])

    def evidence_items(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["payload"])
            for row in self.conn.execute("SELECT payload FROM evidence ORDER BY id")
        ]

    def create_lease(self, lease: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO leases(lease_id,task_id,repository_id,holder,base_sha,branch,worktree,contract_digest,issued_at,expires_at,active) VALUES(?,?,?,?,?,?,?,?,?,?,1)",  # noqa: E501
            (
                lease["lease_id"],
                lease["task_id"],
                lease["repository_id"],
                lease["holder"],
                lease["base_sha"],
                lease["branch"],
                lease.get("worktree"),
                lease.get("contract_digest"),
                lease["issued_at"],
                lease["expires_at"],
            ),
        )
        self.conn.commit()

    def update_lease(self, lease_id: str, **fields: Any) -> None:
        allowed = {"worktree", "contract_digest", "active"}
        if set(fields) - allowed:
            raise ValueError("unsupported lease update")
        sets = ",".join(f"{name}=?" for name in fields)
        # Column names are validated against the `allowed` set above; values
        # are bound parameters.
        self.conn.execute(
            f"UPDATE leases SET {sets} WHERE lease_id=?",  # nosec B608
            [*fields.values(), lease_id],
        )
        self.conn.commit()

    def active_lease_for_task(self, task_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM leases WHERE task_id=? AND active=1", (task_id,)
        ).fetchone()
        return None if row is None else dict(row)

    def active_leases(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute("SELECT * FROM leases WHERE active=1 ORDER BY issued_at")
        ]

    def release_lease(self, lease_id: str) -> None:
        self.conn.execute("UPDATE leases SET active=0 WHERE lease_id=?", (lease_id,))
        self.conn.commit()

    def next_attempt_number(self, task_id: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(attempt_number),0)+1 AS n FROM attempts WHERE task_id=?",
            (task_id,),
        ).fetchone()
        return int(row["n"])

    def create_attempt(
        self, task_id: str, attempt_number: int, receipt_path: str, created_at: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO attempts(task_id,attempt_number,receipt_path,status,created_at) VALUES(?,?,?,?,?)",  # noqa: E501
            (task_id, attempt_number, receipt_path, "RECORDED", created_at),
        )
        self.conn.commit()

    def latest_attempt(self, task_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM attempts WHERE task_id=? ORDER BY attempt_number DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return None if row is None else dict(row)

    def add_approval(self, approval: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO approvals(approval_id,payload) VALUES(?,?)",
            (approval["approval_id"], json.dumps(approval, sort_keys=True)),
        )
        self.conn.commit()

    def approvals(self) -> list[dict[str, Any]]:
        return [
            json.loads(row["payload"])
            for row in self.conn.execute("SELECT payload FROM approvals ORDER BY approval_id")
        ]
