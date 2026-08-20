from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from autonomy.errors import PolicyViolation
from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text


def claims_collide(
    *,
    mode: str,
    exclusive: bool,
    other_mode: str,
    other_exclusive: bool,
) -> bool:
    """Whether two claims on the *same* resource key may not be held at once.

    Single source of truth for claim compatibility. The registry enforces it
    transactionally, the scheduler pre-filters admission with it, and the graph
    linter uses it to tell a real ordering constraint from a serialization-only
    dependency edge — all three must agree or the scheduler would offer work the
    registry then rejects.
    """

    return exclusive or other_exclusive or "write" in {mode, other_mode}


class ClaimRegistry:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def assert_available(
        self,
        connection,
        *,
        campaign_id: str,
        claims: Sequence[Mapping[str, Any]],
    ) -> None:
        for requested in claims:
            resource_key = str(requested["key"])
            requested_mode = str(requested["mode"])
            requested_exclusive = bool(
                requested.get(
                    "exclusive",
                    requested_mode == "write",
                )
            )
            existing = list(
                connection.execute(
                    """
                    SELECT *
                    FROM claims
                    WHERE
                        campaign_id = ?
                        AND resource_key = ?
                        AND status = 'ACTIVE'
                    """,
                    (campaign_id, resource_key),
                )
            )
            for claim in existing:
                if claims_collide(
                    mode=requested_mode,
                    exclusive=requested_exclusive,
                    other_mode=str(claim["mode"]),
                    other_exclusive=bool(claim["exclusive"]),
                ):
                    raise PolicyViolation(
                        "CLAIM_CONFLICT: resource "
                        f"{resource_key!r} is already claimed by "
                        f"action {claim['action_id']!r} "
                        f"under lease {claim['lease_id']!r}"
                    )

    def create_claims(
        self,
        connection,
        *,
        lease_id: str,
        campaign_id: str,
        action_id: str,
        claims: Sequence[Mapping[str, Any]],
    ) -> list[str]:
        self.assert_available(
            connection,
            campaign_id=campaign_id,
            claims=claims,
        )
        created: list[str] = []
        now = utc_now_text()
        for requested in claims:
            claim_id = f"claim-{uuid.uuid4().hex}"
            mode = str(requested["mode"])
            exclusive = bool(requested.get("exclusive", mode == "write"))
            connection.execute(
                """
                INSERT INTO claims (
                    claim_id,
                    lease_id,
                    campaign_id,
                    action_id,
                    resource_key,
                    mode,
                    exclusive,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (
                    claim_id,
                    lease_id,
                    campaign_id,
                    action_id,
                    requested["key"],
                    mode,
                    int(exclusive),
                    now,
                ),
            )
            created.append(claim_id)
        return created

    def release_for_lease(
        self,
        connection,
        lease_id: str,
    ) -> int:
        return connection.execute(
            """
            UPDATE claims
            SET status = 'RELEASED', released_at = ?
            WHERE lease_id = ? AND status = 'ACTIVE'
            """,
            (utc_now_text(), lease_id),
        ).rowcount
