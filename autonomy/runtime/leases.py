from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Mapping
from datetime import timedelta
from typing import Any

from autonomy.errors import PolicyViolation
from autonomy.runtime.claims import ClaimRegistry
from autonomy.runtime.receipts import ReceiptChain
from autonomy.runtime.store import RuntimeStore, canonical_dump
from autonomy.runtime.timeutil import (
    parse_timestamp,
    timestamp_text,
    utc_now,
    utc_now_text,
)
from autonomy.runtime.types import Lease, LeaseStatus

# Roles whose whole purpose is to judge another agent's work. Their lease
# subject must not be a producer of anything they depend on or were declared
# independent from; the graph linter proves the declaration, this proves the
# binding at issue time.
INDEPENDENT_ROLES = frozenset({"verifier", "reviewer", "verifier_reviewer"})


def producer_agent_ids(
    connection: Any,
    *,
    campaign_id: str,
    action_ids: Iterable[str],
) -> list[str]:
    """Agents that produced (or hold/held the lease on) the given actions.

    An action's producers are the lease subjects of its VALID artifacts plus
    the agent currently assigned to it. The assignment is included because an
    action may be completed without an artifact row (status set directly) and
    the agent that held its lease still authored that state.
    """
    producers: dict[str, None] = {}
    for action_id in action_ids:
        rows = connection.execute(
            """
            SELECT l.agent_id AS agent_id
            FROM artifacts AS a
            JOIN leases AS l ON l.lease_id = a.lease_id
            WHERE a.campaign_id = ? AND a.action_id = ? AND a.status = 'VALID'
            """,
            (campaign_id, action_id),
        ).fetchall()
        for row in rows:
            if row["agent_id"]:
                producers.setdefault(str(row["agent_id"]), None)
        assigned = connection.execute(
            """
            SELECT assigned_agent_id
            FROM actions
            WHERE campaign_id = ? AND action_id = ?
            """,
            (campaign_id, action_id),
        ).fetchone()
        if assigned is not None and assigned["assigned_agent_id"]:
            producers.setdefault(str(assigned["assigned_agent_id"]), None)
    return list(producers)


def independence_sources(action: Mapping[str, Any]) -> list[str]:
    """Actions this one must be independent from: the explicit declaration
    first (it names the subject under review), then every dependency."""
    sources: dict[str, None] = {}
    for key in ("independent_from", "depends_on"):
        for action_id in action.get(key, []) or []:
            sources.setdefault(str(action_id), None)
    return list(sources)


def requires_independence(action: Mapping[str, Any]) -> bool:
    return str(action.get("role")) in INDEPENDENT_ROLES or str(action.get("kind")) == "validation"


class LeaseManager:
    def __init__(
        self,
        store: RuntimeStore,
        claims: ClaimRegistry,
        receipts: ReceiptChain,
        *,
        default_ttl_seconds: int = 900,
        stale_after_seconds: int = 90,
        revoke_after_seconds: int = 180,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if revoke_after_seconds < stale_after_seconds:
            raise ValueError("revoke_after_seconds must be >= stale_after_seconds")
        self.store = store
        self.claims = claims
        self.receipts = receipts
        self.default_ttl_seconds = default_ttl_seconds
        self.stale_after_seconds = stale_after_seconds
        self.revoke_after_seconds = revoke_after_seconds

    def issue(
        self,
        *,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        ttl_seconds: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Lease:
        ttl = ttl_seconds or self.default_ttl_seconds
        if ttl <= 0:
            raise ValueError("Lease TTL must be positive")
        campaign = self.store.get_campaign(campaign_id)
        action_row = self.store.get_action(campaign_id, action_id)
        action = json.loads(action_row["action_json"])
        if campaign["state"] not in {
            "LOCKED",
            "EXECUTING",
            "VALIDATING",
            "INDEPENDENT_REVIEW",
        }:
            raise PolicyViolation(
                f"CAMPAIGN_NOT_EXECUTABLE: campaign state is {campaign['state']!r}"
            )
        if action_row["status"] != "READY":
            raise PolicyViolation(
                f"ACTION_NOT_READY: {action_id!r} status is {action_row['status']!r}"
            )
        role = str(action["role"])
        lease_id = f"lease-{uuid.uuid4().hex}"
        capability_id = f"cap-{campaign_id}-{action_id}-{uuid.uuid4().hex[:12]}"
        now = utc_now()
        issued_at = timestamp_text(now)
        expires_at = timestamp_text(now + timedelta(seconds=ttl))
        metadata_payload = dict(metadata or {})
        with self.store.transaction() as connection:
            duplicate = connection.execute(
                """
                SELECT lease_id
                FROM leases
                WHERE
                    campaign_id = ?
                    AND action_id = ?
                    AND status = 'ACTIVE'
                """,
                (campaign_id, action_id),
            ).fetchone()
            if duplicate is not None:
                raise PolicyViolation(
                    f"ACTION_ALREADY_LEASED: {action_id!r} already has "
                    f"active lease {duplicate['lease_id']!r}"
                )
            if requires_independence(action):
                producers = producer_agent_ids(
                    connection,
                    campaign_id=campaign_id,
                    action_ids=independence_sources(action),
                )
                if agent_id in producers:
                    raise PolicyViolation(
                        f"VERIFIER_NOT_INDEPENDENT: {agent_id!r} produced work that "
                        f"{action_id!r} must judge independently"
                    )
            # Insert the lease row before claims so the claims FK is satisfiable.
            self.claims.assert_available(
                connection,
                campaign_id=campaign_id,
                claims=action.get("claims", []),
            )
            connection.execute(
                """
                INSERT INTO leases (
                    lease_id,
                    campaign_id,
                    graph_id,
                    action_id,
                    agent_id,
                    role,
                    capability_id,
                    base_sha,
                    status,
                    issued_at,
                    expires_at,
                    last_heartbeat_at,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    campaign_id,
                    campaign["graph_id"],
                    action_id,
                    agent_id,
                    role,
                    capability_id,
                    campaign["base_sha"],
                    issued_at,
                    expires_at,
                    issued_at,
                    canonical_dump(metadata_payload),
                ),
            )
            self.claims.create_claims(
                connection,
                lease_id=lease_id,
                campaign_id=campaign_id,
                action_id=action_id,
                claims=action.get("claims", []),
            )
            connection.execute(
                """
                UPDATE actions
                SET
                    status = 'LEASED',
                    assigned_agent_id = ?,
                    active_lease_id = ?,
                    updated_at = ?
                WHERE campaign_id = ? AND action_id = ?
                """,
                (
                    agent_id,
                    lease_id,
                    issued_at,
                    campaign_id,
                    action_id,
                ),
            )
            if campaign["state"] == "LOCKED":
                connection.execute(
                    """
                    UPDATE campaigns
                    SET state = 'EXECUTING', updated_at = ?
                    WHERE campaign_id = ?
                    """,
                    (issued_at, campaign_id),
                )
        self.receipts.append(
            campaign_id=campaign_id,
            graph_id=campaign["graph_id"],
            event_type="lease_issued",
            actor="runtime",
            action_id=action_id,
            lease_id=lease_id,
            event={
                "agent_id": agent_id,
                "role": role,
                "capability_id": capability_id,
                "base_sha": campaign["base_sha"],
                "expires_at": expires_at,
                "claims": action.get("claims", []),
            },
        )
        return Lease(
            lease_id=lease_id,
            campaign_id=campaign_id,
            graph_id=campaign["graph_id"],
            action_id=action_id,
            agent_id=agent_id,
            role=role,
            status=LeaseStatus.ACTIVE,
            issued_at=issued_at,
            expires_at=expires_at,
            last_heartbeat_at=issued_at,
            capability_id=capability_id,
            base_sha=campaign["base_sha"],
            metadata=metadata_payload,
        )

    def acknowledge(
        self,
        *,
        lease_id: str,
        agent_id: str,
        accepted_capabilities: list[str],
    ) -> None:
        lease = self.get(lease_id)
        if lease.agent_id != agent_id:
            raise PolicyViolation(
                "LEASE_AGENT_MISMATCH: acknowledgment agent does not match lease subject"
            )
        if lease.status is not LeaseStatus.ACTIVE:
            raise PolicyViolation(f"LEASE_NOT_ACTIVE: status={lease.status.value}")
        metadata = dict(lease.metadata)
        metadata["acknowledged"] = True
        metadata["accepted_capabilities"] = sorted(set(accepted_capabilities))
        metadata["acknowledged_at"] = utc_now_text()
        with self.store.transaction() as connection:
            connection.execute(
                """
                UPDATE leases
                SET metadata_json = ?
                WHERE lease_id = ?
                """,
                (canonical_dump(metadata), lease_id),
            )
            connection.execute(
                """
                UPDATE actions
                SET status = 'RUNNING', updated_at = ?
                WHERE
                    campaign_id = ?
                    AND action_id = ?
                    AND active_lease_id = ?
                """,
                (
                    utc_now_text(),
                    lease.campaign_id,
                    lease.action_id,
                    lease_id,
                ),
            )
        self.receipts.append(
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            event_type="lease_acknowledged",
            actor=agent_id,
            action_id=lease.action_id,
            lease_id=lease_id,
            event={"accepted_capabilities": sorted(set(accepted_capabilities))},
        )

    def heartbeat(
        self,
        *,
        lease_id: str,
        agent_id: str,
        observed_base_sha: str,
        status: str,
        progress: Mapping[str, Any] | None = None,
    ) -> None:
        lease = self.get(lease_id)
        if lease.agent_id != agent_id:
            raise PolicyViolation(
                "LEASE_AGENT_MISMATCH: heartbeat agent does not match lease subject"
            )
        self.assert_active(lease)
        if observed_base_sha != lease.base_sha:
            self.revoke(
                lease_id=lease_id,
                reason=(f"BASE_SHA_DRIFT: expected {lease.base_sha}, observed {observed_base_sha}"),
                actor="heartbeat-monitor",
            )
            raise PolicyViolation(
                "BASE_SHA_DRIFT: lease revoked because observed base SHA "
                "does not match the authorized base"
            )
        now = utc_now_text()
        with self.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO heartbeats (
                    lease_id,
                    campaign_id,
                    action_id,
                    status,
                    progress_json,
                    observed_base_sha,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    lease.campaign_id,
                    lease.action_id,
                    status,
                    canonical_dump(dict(progress or {})),
                    observed_base_sha,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE leases
                SET last_heartbeat_at = ?
                WHERE lease_id = ? AND status = 'ACTIVE'
                """,
                (now, lease_id),
            )

    def sweep(self) -> dict[str, list[str]]:
        now = utc_now()
        expired: list[str] = []
        stale: list[str] = []
        with self.store.connect() as connection:
            rows = list(
                connection.execute(
                    """
                    SELECT *
                    FROM leases
                    WHERE status = 'ACTIVE'
                    """
                )
            )
        for row in rows:
            lease_id = row["lease_id"]
            expires_at = parse_timestamp(row["expires_at"])
            heartbeat_at = parse_timestamp(row["last_heartbeat_at"])
            heartbeat_age = (now - heartbeat_at).total_seconds()
            if now >= expires_at:
                self.revoke(
                    lease_id=lease_id,
                    reason="LEASE_EXPIRED",
                    actor="lease-sweeper",
                    terminal_status="EXPIRED",
                )
                expired.append(lease_id)
            elif heartbeat_age >= self.revoke_after_seconds:
                self.revoke(
                    lease_id=lease_id,
                    reason=(f"HEARTBEAT_TIMEOUT: no heartbeat for {int(heartbeat_age)} seconds"),
                    actor="lease-sweeper",
                )
                expired.append(lease_id)
            elif heartbeat_age >= self.stale_after_seconds:
                stale.append(lease_id)
        return {
            "revoked_or_expired": expired,
            "stale": stale,
        }

    def release(
        self,
        *,
        lease_id: str,
        actor: str,
        reason: str = "ACTION_COMPLETED",
    ) -> None:
        lease = self.get(lease_id)
        if lease.status is not LeaseStatus.ACTIVE:
            return
        with self.store.transaction() as connection:
            connection.execute(
                """
                UPDATE leases
                SET
                    status = 'RELEASED',
                    revoked_reason = ?
                WHERE lease_id = ? AND status = 'ACTIVE'
                """,
                (reason, lease_id),
            )
            self.claims.release_for_lease(connection, lease_id)
        self.receipts.append(
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            event_type="lease_released",
            actor=actor,
            action_id=lease.action_id,
            lease_id=lease_id,
            event={"reason": reason},
        )

    def revoke(
        self,
        *,
        lease_id: str,
        reason: str,
        actor: str,
        terminal_status: str = "REVOKED",
    ) -> None:
        lease = self.get(lease_id)
        if lease.status is not LeaseStatus.ACTIVE:
            return
        if terminal_status not in {"REVOKED", "EXPIRED"}:
            raise ValueError("terminal_status must be REVOKED or EXPIRED")
        with self.store.transaction() as connection:
            connection.execute(
                """
                UPDATE leases
                SET status = ?, revoked_reason = ?
                WHERE lease_id = ? AND status = 'ACTIVE'
                """,
                (terminal_status, reason, lease_id),
            )
            self.claims.release_for_lease(connection, lease_id)
            connection.execute(
                """
                UPDATE actions
                SET
                    status = 'BLOCKED',
                    active_lease_id = NULL,
                    failure_reason = ?,
                    updated_at = ?
                WHERE
                    campaign_id = ?
                    AND action_id = ?
                    AND active_lease_id = ?
                """,
                (
                    reason,
                    utc_now_text(),
                    lease.campaign_id,
                    lease.action_id,
                    lease_id,
                ),
            )
        self.receipts.append(
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            event_type="lease_revoked",
            actor=actor,
            action_id=lease.action_id,
            lease_id=lease_id,
            event={
                "reason": reason,
                "terminal_status": terminal_status,
            },
        )

    def get(self, lease_id: str) -> Lease:
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM leases
                WHERE lease_id = ?
                """,
                (lease_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown lease: {lease_id}")
        return Lease(
            lease_id=row["lease_id"],
            campaign_id=row["campaign_id"],
            graph_id=row["graph_id"],
            action_id=row["action_id"],
            agent_id=row["agent_id"],
            role=row["role"],
            status=LeaseStatus(row["status"]),
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            last_heartbeat_at=row["last_heartbeat_at"],
            capability_id=row["capability_id"],
            base_sha=row["base_sha"],
            metadata=json.loads(row["metadata_json"]),
        )

    def assert_active(self, lease: Lease) -> None:
        if lease.status is not LeaseStatus.ACTIVE:
            raise PolicyViolation(f"LEASE_NOT_ACTIVE: status={lease.status.value}")
        now = utc_now()
        if now >= parse_timestamp(lease.expires_at):
            self.revoke(
                lease_id=lease.lease_id,
                reason="LEASE_EXPIRED",
                actor="lease-manager",
                terminal_status="EXPIRED",
            )
            raise PolicyViolation("LEASE_EXPIRED")
