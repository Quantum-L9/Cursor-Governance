"""Hash-chained processing receipts with tamper-evident verification.

Each receipt links to the previous one for its job via a SHA-256 chain, so a
job's processing history cannot be silently rewritten. ``append_receipt`` is
idempotent on ``(job_id, event_identity)`` and ``verify_job_chain`` recomputes
the chain to detect any break or mutation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from state_store import PipelineStateStore, utc_now_text

GENESIS_HASH = "GENESIS"


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _receipt_hash(
    *,
    prev_hash: str,
    job_id: str,
    seq: int,
    stage: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
    event_identity: str,
) -> str:
    return hashlib.sha256(
        _canonical(
            {
                "prev_hash": prev_hash,
                "job_id": job_id,
                "seq": seq,
                "stage": stage,
                "event_type": event_type,
                "actor": actor,
                "payload": payload,
                "event_identity": event_identity,
            }
        )
    ).hexdigest()


class ProcessingReceiptChain:
    """Append-only, per-job hash chain of processing receipts."""

    def __init__(self, store: PipelineStateStore) -> None:
        self.store = store

    def append_receipt(
        self,
        *,
        job_id: str,
        stage: str,
        event_type: str,
        actor: str,
        payload: Mapping[str, Any],
        event_identity: str,
    ) -> dict[str, Any]:
        with self.store.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM processing_receipts WHERE job_id = ? AND event_identity = ?",
                (job_id, event_identity),
            ).fetchone()
            if existing is not None:
                return _row_to_receipt(existing)
            tail = connection.execute(
                """
                SELECT seq, receipt_hash FROM processing_receipts
                WHERE job_id = ? ORDER BY seq DESC LIMIT 1
                """,
                (job_id,),
            ).fetchone()
            seq = (int(tail["seq"]) + 1) if tail is not None else 1
            prev_hash = tail["receipt_hash"] if tail is not None else GENESIS_HASH
            receipt_hash = _receipt_hash(
                prev_hash=prev_hash,
                job_id=job_id,
                seq=seq,
                stage=stage,
                event_type=event_type,
                actor=actor,
                payload=payload,
                event_identity=event_identity,
            )
            connection.execute(
                """
                INSERT INTO processing_receipts (
                    job_id, seq, stage, event_type, actor, payload_json,
                    event_identity, prev_hash, receipt_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    seq,
                    stage,
                    event_type,
                    actor,
                    json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
                    event_identity,
                    prev_hash,
                    receipt_hash,
                    utc_now_text(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM processing_receipts WHERE job_id = ? AND seq = ?",
                (job_id, seq),
            ).fetchone()
        return _row_to_receipt(row)

    def list_receipts(self, job_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM processing_receipts WHERE job_id = ? ORDER BY seq",
                (job_id,),
            ).fetchall()
        return [_row_to_receipt(row) for row in rows]

    def verify_job_chain(self, job_id: str) -> list[str]:
        errors: list[str] = []
        prev_hash = GENESIS_HASH
        expected_seq = 1
        for receipt in self.list_receipts(job_id):
            if receipt["seq"] != expected_seq:
                errors.append(f"{job_id}: seq gap at {receipt['seq']} (expected {expected_seq})")
            if receipt["prev_hash"] != prev_hash:
                errors.append(f"{job_id}: broken link at seq {receipt['seq']}")
            recomputed = _receipt_hash(
                prev_hash=receipt["prev_hash"],
                job_id=job_id,
                seq=receipt["seq"],
                stage=receipt["stage"],
                event_type=receipt["event_type"],
                actor=receipt["actor"],
                payload=receipt["payload"],
                event_identity=receipt["event_identity"],
            )
            if recomputed != receipt["receipt_hash"]:
                errors.append(f"{job_id}: hash mismatch at seq {receipt['seq']}")
            prev_hash = receipt["receipt_hash"]
            expected_seq = receipt["seq"] + 1
        return errors


def _row_to_receipt(row: Any) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "seq": int(row["seq"]),
        "stage": row["stage"],
        "event_type": row["event_type"],
        "actor": row["actor"],
        "payload": json.loads(row["payload_json"]),
        "event_identity": row["event_identity"],
        "prev_hash": row["prev_hash"],
        "receipt_hash": row["receipt_hash"],
        "created_at": row["created_at"],
    }
