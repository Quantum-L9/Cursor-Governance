from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from collections.abc import Mapping
from typing import Any

from autonomy.runtime.store import RuntimeStore, canonical_dump
from autonomy.runtime.timeutil import utc_now_text

GENESIS_HASH = "0" * 64


class ReceiptChain:
    def __init__(
        self,
        store: RuntimeStore,
        signing_key: str | None = None,
    ) -> None:
        self.store = store
        self.signing_key = (
            signing_key if signing_key is not None else os.environ.get("L9_AUTONOMY_RECEIPT_KEY")
        )

    def append(
        self,
        *,
        campaign_id: str,
        graph_id: str,
        event_type: str,
        actor: str,
        event: Mapping[str, Any],
        action_id: str | None = None,
        lease_id: str | None = None,
        artifact_id: str | None = None,
    ) -> dict[str, Any]:
        created_at = utc_now_text()
        with self.store.transaction() as connection:
            previous = connection.execute(
                """
                SELECT receipt_hash
                FROM receipts
                WHERE campaign_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (campaign_id,),
            ).fetchone()
            previous_hash = previous["receipt_hash"] if previous is not None else GENESIS_HASH
            receipt_id = f"rcpt-{uuid.uuid4().hex}"
            body = {
                "receipt_id": receipt_id,
                "campaign_id": campaign_id,
                "graph_id": graph_id,
                "event_type": event_type,
                "actor": actor,
                "action_id": action_id,
                "lease_id": lease_id,
                "artifact_id": artifact_id,
                "event": dict(event),
                "previous_receipt_hash": previous_hash,
                "created_at": created_at,
            }
            receipt_hash = hashlib.sha256(canonical_dump(body).encode("utf-8")).hexdigest()
            signature = self._sign(receipt_hash)
            connection.execute(
                """
                INSERT INTO receipts (
                    receipt_id,
                    campaign_id,
                    graph_id,
                    event_type,
                    actor,
                    action_id,
                    lease_id,
                    artifact_id,
                    event_json,
                    previous_receipt_hash,
                    receipt_hash,
                    signature,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    campaign_id,
                    graph_id,
                    event_type,
                    actor,
                    action_id,
                    lease_id,
                    artifact_id,
                    canonical_dump(event),
                    previous_hash,
                    receipt_hash,
                    signature,
                    created_at,
                ),
            )
        return {
            **body,
            "receipt_hash": receipt_hash,
            "signature": signature,
        }

    def verify(self, campaign_id: str) -> list[str]:
        errors: list[str] = []
        with self.store.connect() as connection:
            rows = list(
                connection.execute(
                    """
                    SELECT *
                    FROM receipts
                    WHERE campaign_id = ?
                    ORDER BY sequence
                    """,
                    (campaign_id,),
                )
            )
        previous_hash = GENESIS_HASH
        for row in rows:
            event = json.loads(row["event_json"])
            body = {
                "receipt_id": row["receipt_id"],
                "campaign_id": row["campaign_id"],
                "graph_id": row["graph_id"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "action_id": row["action_id"],
                "lease_id": row["lease_id"],
                "artifact_id": row["artifact_id"],
                "event": event,
                "previous_receipt_hash": row["previous_receipt_hash"],
                "created_at": row["created_at"],
            }
            calculated = hashlib.sha256(canonical_dump(body).encode("utf-8")).hexdigest()
            if row["previous_receipt_hash"] != previous_hash:
                errors.append(f"{row['receipt_id']}: previous hash mismatch")
            if row["receipt_hash"] != calculated:
                errors.append(f"{row['receipt_id']}: receipt hash mismatch")
            if self.signing_key:
                expected_signature = self._sign(row["receipt_hash"])
                if not hmac.compare_digest(
                    row["signature"] or "",
                    expected_signature or "",
                ):
                    errors.append(f"{row['receipt_id']}: signature mismatch")
            previous_hash = row["receipt_hash"]
        return errors

    def _sign(self, receipt_hash: str) -> str | None:
        if not self.signing_key:
            return None
        return hmac.new(
            self.signing_key.encode("utf-8"),
            receipt_hash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
