"""SQLite-backed durable state for the generated-data pipeline.

Owns the job state machine, per-stage snapshots, delivery attempts and receipts,
reuse events, context selections, invalidation events, and the dead-letter queue.
All identifiers are content-derived so re-processing is idempotent, and every
state change is an explicit, optimistic-concurrency transition.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class PipelineState(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    HARVESTED = "HARVESTED"
    CLASSIFIED = "CLASSIFIED"
    ROUTED = "ROUTED"
    PROMOTION_DECIDED = "PROMOTION_DECIDED"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    DESTINATION_SUBMITTED = "DESTINATION_SUBMITTED"
    DESTINATION_DEFERRED = "DESTINATION_DEFERRED"
    DESTINATION_ACCEPTED = "DESTINATION_ACCEPTED"
    DESTINATION_REJECTED = "DESTINATION_REJECTED"
    RETRY_WAIT = "RETRY_WAIT"
    DEAD_LETTERED = "DEAD_LETTERED"
    LEARNING_CLOSED = "LEARNING_CLOSED"
    REJECTED = "REJECTED"


class StateStoreError(RuntimeError):
    """Base state-store failure."""


class JobNotFoundError(StateStoreError):
    """Raised when a referenced job does not exist."""


class StateTransitionError(StateStoreError):
    """Raised when an optimistic state transition does not match."""


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def deterministic_id(prefix: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:32]}"


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    campaign_id: str
    graph_id: str | None
    packet_id: str
    state: PipelineState
    version: int
    replay_generation: int
    created_at: str
    updated_at: str
    next_attempt_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "campaign_id": self.campaign_id,
            "graph_id": self.graph_id,
            "packet_id": self.packet_id,
            "state": self.state.value,
            "version": self.version,
            "replay_generation": self.replay_generation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_attempt_at": self.next_attempt_at,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class DeliveryAttempt:
    attempt_id: str
    job_id: str
    unit_id: str
    route: str
    attempt_number: int
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "job_id": self.job_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "attempt_number": self.attempt_number,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class JobEvent:
    seq: int
    job_id: str
    event_type: str
    from_state: str | None
    to_state: str | None
    actor: str
    payload: Mapping[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "job_id": self.job_id,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CampaignStatus:
    campaign_id: str
    state: str
    job_counts: Mapping[str, int]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "state": self.state,
            "job_counts": dict(self.job_counts),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class DeadLetter:
    dead_letter_id: str
    job_id: str
    unit_id: str | None
    route: str | None
    failure_class: str
    reason: str
    status: str
    payload: Mapping[str, Any]
    created_at: str
    resolution_type: str | None = None
    resolution_reason: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dead_letter_id": self.dead_letter_id,
            "job_id": self.job_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "failure_class": self.failure_class,
            "reason": self.reason,
            "status": self.status,
            "payload": dict(self.payload),
            "created_at": self.created_at,
            "resolution_type": self.resolution_type,
            "resolution_reason": self.resolution_reason,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }


_EARLIER_STATES = (
    PipelineState.RECEIVED,
    PipelineState.VALIDATED,
    PipelineState.HARVESTED,
    PipelineState.CLASSIFIED,
    PipelineState.ROUTED,
    PipelineState.PROMOTION_DECIDED,
    PipelineState.DELIVERY_PENDING,
)


class PipelineStateStore:
    """Durable, content-addressed pipeline state."""

    def __init__(self, database_path: str | Path) -> None:
        self._db_path = Path(database_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self._db_path))
        connection.row_factory = sqlite3.Row
        try:
            # sqlite3.Connection is itself a context manager that commits on
            # success and rolls back on any exception — no broad except needed.
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(_SCHEMA)

    # ---- job lifecycle ---------------------------------------------------
    def create_job(
        self,
        *,
        job_id: str,
        campaign_id: str,
        graph_id: str | None,
        packet_id: str,
        packet: Mapping[str, Any],
        state: PipelineState = PipelineState.RECEIVED,
    ) -> ProcessingJob:
        now = utc_now_text()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM processing_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if existing is not None:
                # Reprocessing a deterministic job id must not reset state or
                # orphan prior events/snapshots — return the existing job as-is.
                return _row_to_job(existing)
            connection.execute(
                """
                INSERT INTO processing_jobs (
                    job_id, campaign_id, graph_id, packet_id, state, version,
                    replay_generation, created_at, updated_at, next_attempt_at,
                    error_code, error_message
                ) VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, NULL, NULL, NULL)
                """,
                (job_id, campaign_id, graph_id, packet_id, state.value, now, now),
            )
            connection.execute(
                "INSERT INTO packets (job_id, packet_json) VALUES (?, ?)",
                (job_id, _dumps(packet)),
            )
            connection.execute(
                """
                INSERT INTO campaigns (campaign_id, state, updated_at)
                VALUES (?, 'active', ?)
                ON CONFLICT(campaign_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (campaign_id, now),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_created",
                from_state=None,
                to_state=state.value,
                actor="processor",
                payload={"packet_id": packet_id},
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> ProcessingJob:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM processing_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(f"No such job: {job_id}")
        return _row_to_job(row)

    def transition(
        self,
        *,
        job_id: str,
        expected_state: PipelineState,
        target_state: PipelineState,
        actor: str,
        payload: Mapping[str, Any],
        allow_replay: bool = False,
    ) -> ProcessingJob:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM processing_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise JobNotFoundError(f"No such job: {job_id}")
            current = PipelineState(row["state"])
            replay_generation = int(row["replay_generation"])
            if current is not expected_state and not allow_replay:
                raise StateTransitionError(
                    f"{job_id}: expected {expected_state.value}, found {current.value}"
                )
            if allow_replay and target_state in _EARLIER_STATES:
                replay_generation += 1
            current_version = int(row["version"])
            now = utc_now_text()
            cursor = connection.execute(
                """
                UPDATE processing_jobs
                SET state = ?, version = version + 1, replay_generation = ?,
                    updated_at = ?
                WHERE job_id = ? AND version = ?
                """,
                (target_state.value, replay_generation, now, job_id, current_version),
            )
            if cursor.rowcount != 1:
                # Optimistic-concurrency guard: another writer changed the row
                # between the SELECT and this UPDATE.
                raise StateTransitionError(
                    f"{job_id}: concurrent modification at version {current_version}"
                )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="transition",
                from_state=current.value,
                to_state=target_state.value,
                actor=actor,
                payload=payload,
            )
            updated = connection.execute(
                "SELECT * FROM processing_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return _row_to_job(updated)

    def schedule_retry(
        self,
        *,
        job_id: str,
        expected_state: PipelineState,
        actor: str,
        next_attempt_at: str,
        error_code: str,
        error_message: str,
        payload: Mapping[str, Any],
    ) -> ProcessingJob:
        job = self.transition(
            job_id=job_id,
            expected_state=expected_state,
            target_state=PipelineState.RETRY_WAIT,
            actor=actor,
            payload={**dict(payload), "error_code": error_code},
        )
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE processing_jobs
                SET next_attempt_at = ?, error_code = ?, error_message = ?
                WHERE job_id = ?
                """,
                (next_attempt_at, error_code, error_message, job_id),
            )
        return self.get_job(job.job_id)

    def dead_letter(
        self,
        *,
        job_id: str,
        expected_state: PipelineState,
        actor: str,
        failure_class: str,
        reason: str,
        payload: Mapping[str, Any],
        unit_id: str | None = None,
        route: str | None = None,
    ) -> ProcessingJob:
        job = self.transition(
            job_id=job_id,
            expected_state=expected_state,
            target_state=PipelineState.DEAD_LETTERED,
            actor=actor,
            payload={"failure_class": failure_class, "reason": reason},
        )
        dead_letter_id = deterministic_id(
            "deadletter",
            {"job_id": job_id, "unit_id": unit_id, "route": route, "reason": reason},
        )
        now = utc_now_text()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO dead_letters (
                    dead_letter_id, job_id, unit_id, route, failure_class, reason,
                    status, payload_json, created_at, resolution_type,
                    resolution_reason, resolved_by, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, NULL, NULL, NULL, NULL)
                """,
                (
                    dead_letter_id,
                    job_id,
                    unit_id,
                    route,
                    failure_class,
                    reason,
                    _dumps(payload),
                    now,
                ),
            )
            connection.execute(
                "UPDATE processing_jobs SET error_code = ?, error_message = ? WHERE job_id = ?",
                (failure_class, reason, job_id),
            )
        return self.get_job(job.job_id)

    # ---- stage snapshots & packet ---------------------------------------
    def add_stage_snapshot(
        self,
        *,
        job_id: str,
        stage: str,
        payload: Mapping[str, Any],
    ) -> str:
        snapshot_id = deterministic_id(
            "snapshot",
            {"job_id": job_id, "stage": stage, "payload": payload},
        )
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO stage_snapshots (
                    snapshot_id, job_id, stage, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (snapshot_id, job_id, stage, _dumps(payload), utc_now_text()),
            )
        return snapshot_id

    def list_stage_snapshots(
        self,
        *,
        job_id: str,
        stage: str,
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT snapshot_id, stage, payload_json, created_at
                FROM stage_snapshots
                WHERE job_id = ? AND stage = ?
                ORDER BY created_at, snapshot_id
                """,
                (job_id, stage),
            ).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "stage": row["stage"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def load_packet(self, job_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT packet_json FROM packets WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(f"No packet stored for job: {job_id}")
        return json.loads(row["packet_json"])

    # ---- delivery attempts & receipts -----------------------------------
    def record_delivery_attempt(
        self,
        *,
        job_id: str,
        unit_id: str,
        route: str,
        attempt_number: int,
        idempotency_key: str,
    ) -> DeliveryAttempt:
        attempt_id = deterministic_id(
            "attempt",
            {"job_id": job_id, "unit_id": unit_id, "route": route, "attempt": attempt_number},
        )
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO delivery_attempts (
                    attempt_id, job_id, unit_id, route, attempt_number,
                    idempotency_key, status, response_code, error_class,
                    error_message, response_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'STARTED', NULL, NULL, NULL, NULL, ?, NULL)
                """,
                (
                    attempt_id,
                    job_id,
                    unit_id,
                    route,
                    attempt_number,
                    idempotency_key,
                    utc_now_text(),
                ),
            )
        return DeliveryAttempt(
            attempt_id=attempt_id,
            job_id=job_id,
            unit_id=unit_id,
            route=route,
            attempt_number=attempt_number,
            idempotency_key=idempotency_key,
        )

    def complete_delivery_attempt(
        self,
        *,
        attempt_id: str,
        status: str,
        response_code: str | None = None,
        response_payload: Mapping[str, Any] | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE delivery_attempts
                SET status = ?, response_code = ?, error_class = ?,
                    error_message = ?, response_json = ?, completed_at = ?
                WHERE attempt_id = ?
                """,
                (
                    status,
                    response_code,
                    error_class,
                    error_message,
                    _dumps(response_payload) if response_payload is not None else None,
                    utc_now_text(),
                    attempt_id,
                ),
            )

    def record_delivery_receipt(
        self,
        *,
        job_id: str,
        unit_id: str,
        route: str,
        destination_status: str,
        destination_reference: str | None,
        payload: Mapping[str, Any],
    ) -> None:
        receipt_id = deterministic_id(
            "delivery-receipt",
            {
                "job_id": job_id,
                "unit_id": unit_id,
                "route": route,
                "reference": destination_reference,
                "status": destination_status,
            },
        )
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO delivery_receipts (
                    receipt_id, job_id, unit_id, route, destination_status,
                    destination_reference, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    job_id,
                    unit_id,
                    route,
                    destination_status,
                    destination_reference,
                    _dumps(payload),
                    utc_now_text(),
                ),
            )

    # ---- reuse / context / invalidation ---------------------------------
    def record_reuse_event(
        self,
        *,
        event_id: str,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        stage: str,
        outcome: str | None,
        payload: Mapping[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO reuse_events (
                    event_id, record_id, campaign_id, action_id, agent_id,
                    context_pack_id, stage, outcome, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    record_id,
                    campaign_id,
                    action_id,
                    agent_id,
                    context_pack_id,
                    stage,
                    outcome,
                    _dumps(payload),
                    utc_now_text(),
                ),
            )
            created = cursor.rowcount == 1
            row = connection.execute(
                "SELECT * FROM reuse_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return (dict(row) if row is not None else {"event_id": event_id}), created

    def record_context_selection(
        self,
        *,
        selection_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        record_ids: tuple[str, ...],
        payload: Mapping[str, Any],
        status: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO context_selections (
                    selection_id, campaign_id, action_id, agent_id,
                    context_pack_id, record_ids_json, payload_json, status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    selection_id,
                    campaign_id,
                    action_id,
                    agent_id,
                    context_pack_id,
                    _dumps(list(record_ids)),
                    _dumps(payload),
                    status,
                    utc_now_text(),
                ),
            )

    def record_invalidation_event(
        self,
        *,
        event_id: str,
        repository: str,
        from_sha: str | None,
        to_sha: str | None,
        event_type: str,
        status: str,
        payload: Mapping[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO invalidation_events (
                    event_id, repository, from_sha, to_sha, event_type, status,
                    payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    repository,
                    from_sha,
                    to_sha,
                    event_type,
                    status,
                    _dumps(payload),
                    utc_now_text(),
                ),
            )
            created = cursor.rowcount == 1
            row = connection.execute(
                "SELECT * FROM invalidation_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return (dict(row) if row is not None else {"event_id": event_id}), created

    # ---- dead letters ----------------------------------------------------
    def list_dead_letters(self) -> list[DeadLetter]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM dead_letters ORDER BY created_at, dead_letter_id"
            ).fetchall()
        return [_row_to_dead_letter(row) for row in rows]

    def resolve_dead_letter(
        self,
        *,
        dead_letter_id: str,
        resolution_type: str,
        resolution_reason: str,
        actor: str,
    ) -> DeadLetter:
        now = utc_now_text()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE dead_letters
                SET status = 'RESOLVED', resolution_type = ?, resolution_reason = ?,
                    resolved_by = ?, resolved_at = ?
                WHERE dead_letter_id = ?
                """,
                (resolution_type, resolution_reason, actor, now, dead_letter_id),
            )
            if cursor.rowcount == 0:
                raise StateStoreError(f"No such dead letter: {dead_letter_id}")
            row = connection.execute(
                "SELECT * FROM dead_letters WHERE dead_letter_id = ?",
                (dead_letter_id,),
            ).fetchone()
        return _row_to_dead_letter(row)

    # ---- status / reporting ---------------------------------------------
    def pipeline_status(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT state, COUNT(*) AS count FROM processing_jobs GROUP BY state"
            ).fetchall()
            total = connection.execute("SELECT COUNT(*) AS n FROM processing_jobs").fetchone()["n"]
        return {
            "total_jobs": int(total),
            "by_state": {row["state"]: int(row["count"]) for row in rows},
        }

    def campaign_status(self, campaign_id: str) -> CampaignStatus:
        with self.connect() as connection:
            counts = connection.execute(
                """
                SELECT state, COUNT(*) AS count
                FROM processing_jobs
                WHERE campaign_id = ?
                GROUP BY state
                """,
                (campaign_id,),
            ).fetchall()
            row = connection.execute(
                "SELECT state, updated_at FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
        job_counts = {item["state"]: int(item["count"]) for item in counts}
        return CampaignStatus(
            campaign_id=campaign_id,
            state=row["state"] if row is not None else "unknown",
            job_counts=job_counts,
            updated_at=row["updated_at"] if row is not None else utc_now_text(),
        )

    def recalculate_campaign_state(self, campaign_id: str) -> None:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT state FROM processing_jobs WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchall()
            states = {row["state"] for row in rows}
            terminal = {
                PipelineState.DESTINATION_DEFERRED.value,
                PipelineState.DESTINATION_ACCEPTED.value,
                PipelineState.DESTINATION_REJECTED.value,
                PipelineState.LEARNING_CLOSED.value,
                PipelineState.REJECTED.value,
            }
            if PipelineState.DEAD_LETTERED.value in states:
                state = "attention"
            elif states and states <= terminal:
                state = "completed"
            else:
                # DESTINATION_SUBMITTED remains active until an authoritative
                # downstream acceptance, deferral, or rejection receipt exists.
                state = "active"
            connection.execute(
                """
                INSERT INTO campaigns (campaign_id, state, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(campaign_id) DO UPDATE SET
                    state = excluded.state, updated_at = excluded.updated_at
                """,
                (campaign_id, state, utc_now_text()),
            )

    def list_events(self, job_id: str) -> list[JobEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY seq",
                (job_id,),
            ).fetchall()
        return [
            JobEvent(
                seq=int(row["seq"]),
                job_id=row["job_id"],
                event_type=row["event_type"],
                from_state=row["from_state"],
                to_state=row["to_state"],
                actor=row["actor"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # ---- internals -------------------------------------------------------
    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        actor: str,
        payload: Mapping[str, Any],
    ) -> None:
        seq_row = connection.execute(
            "SELECT COALESCE(MAX(seq), 0) AS n FROM job_events WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        seq = int(seq_row["n"]) + 1
        connection.execute(
            """
            INSERT INTO job_events (
                job_id, seq, event_type, from_state, to_state, actor,
                payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                seq,
                event_type,
                from_state,
                to_state,
                actor,
                _dumps(payload),
                utc_now_text(),
            ),
        )


def _dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _row_to_job(row: sqlite3.Row) -> ProcessingJob:
    return ProcessingJob(
        job_id=row["job_id"],
        campaign_id=row["campaign_id"],
        graph_id=row["graph_id"],
        packet_id=row["packet_id"],
        state=PipelineState(row["state"]),
        version=int(row["version"]),
        replay_generation=int(row["replay_generation"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_attempt_at=row["next_attempt_at"],
        error_code=row["error_code"],
        error_message=row["error_message"],
    )


def _row_to_dead_letter(row: sqlite3.Row) -> DeadLetter:
    return DeadLetter(
        dead_letter_id=row["dead_letter_id"],
        job_id=row["job_id"],
        unit_id=row["unit_id"],
        route=row["route"],
        failure_class=row["failure_class"],
        reason=row["reason"],
        status=row["status"],
        payload=json.loads(row["payload_json"]),
        created_at=row["created_at"],
        resolution_type=row["resolution_type"],
        resolution_reason=row["resolution_reason"],
        resolved_by=row["resolved_by"],
        resolved_at=row["resolved_at"],
    )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    graph_id TEXT,
    packet_id TEXT NOT NULL,
    state TEXT NOT NULL,
    version INTEGER NOT NULL,
    replay_generation INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    next_attempt_at TEXT,
    error_code TEXT,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS packets (
    job_id TEXT PRIMARY KEY,
    packet_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stage_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_events (
    job_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (job_id, seq)
);
CREATE TABLE IF NOT EXISTS delivery_attempts (
    attempt_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    route TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    response_code TEXT,
    error_class TEXT,
    error_message TEXT,
    response_json TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS delivery_receipts (
    receipt_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    route TEXT NOT NULL,
    destination_status TEXT NOT NULL,
    destination_reference TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_receipts (
    job_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    stage TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    event_identity TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    receipt_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (job_id, seq),
    UNIQUE (job_id, event_identity)
);
CREATE TABLE IF NOT EXISTS reuse_events (
    event_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    context_pack_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    outcome TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS context_selections (
    selection_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    context_pack_id TEXT NOT NULL,
    record_ids_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invalidation_events (
    event_id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    from_sha TEXT,
    to_sha TEXT,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dead_letters (
    dead_letter_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    unit_id TEXT,
    route TEXT,
    failure_class TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolution_type TEXT,
    resolution_reason TEXT,
    resolved_by TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
