from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from autonomy.errors import ContractError, PolicyViolation
from autonomy.io import sha256_json
from autonomy.runtime.leases import LeaseManager
from autonomy.runtime.receipts import ReceiptChain
from autonomy.runtime.store import RuntimeStore, canonical_dump
from autonomy.runtime.timeutil import utc_now_text


class ArtifactValidator:
    def __init__(
        self,
        store: RuntimeStore,
        leases: LeaseManager,
        receipts: ReceiptChain,
    ) -> None:
        self.store = store
        self.leases = leases
        self.receipts = receipts

    def submit(
        self,
        *,
        lease_id: str,
        agent_id: str,
        artifact: Mapping[str, Any],
    ) -> str:
        lease = self.leases.get(lease_id)
        self.leases.assert_active(lease)
        if lease.agent_id != agent_id:
            raise PolicyViolation(
                "LEASE_AGENT_MISMATCH: artifact producer does not match lease subject"
            )
        action_row = self.store.get_action(
            lease.campaign_id,
            lease.action_id,
        )
        if action_row["status"] not in {"LEASED", "RUNNING"}:
            raise PolicyViolation(
                f"ACTION_NOT_RUNNING: cannot submit an artifact for status {action_row['status']!r}"
            )
        action = json.loads(action_row["action_json"])
        completion = action["completion"]
        self._validate_envelope(
            artifact=artifact,
            lease_id=lease_id,
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            action_id=lease.action_id,
            agent_id=agent_id,
        )
        self._validate_completion(
            artifact=artifact,
            completion=completion,
            expected_base_sha=lease.base_sha,
        )
        self._validate_dependencies_current(
            campaign_id=lease.campaign_id,
            action=action,
            artifact=artifact,
        )
        artifact_id = str(artifact.get("artifact_id"))
        payload = artifact["payload"]
        payload_hash = sha256_json(payload)
        now = utc_now_text()
        target_sha = artifact.get("target_sha")
        with self.store.transaction() as connection:
            duplicate = connection.execute(
                """
                SELECT artifact_id
                FROM artifacts
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()
            if duplicate is not None:
                raise ContractError(f"Duplicate artifact ID: {artifact_id}")
            connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id,
                    campaign_id,
                    graph_id,
                    action_id,
                    lease_id,
                    kind,
                    base_sha,
                    target_sha,
                    status,
                    payload_json,
                    payload_hash,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VALID', ?, ?, ?)
                """,
                (
                    artifact_id,
                    lease.campaign_id,
                    lease.graph_id,
                    lease.action_id,
                    lease_id,
                    artifact["kind"],
                    artifact["base_sha"],
                    target_sha,
                    canonical_dump(payload),
                    payload_hash,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE actions
                SET
                    status = 'COMPLETED',
                    result_artifact_id = ?,
                    active_lease_id = NULL,
                    failure_reason = NULL,
                    updated_at = ?
                WHERE
                    campaign_id = ?
                    AND action_id = ?
                    AND active_lease_id = ?
                """,
                (
                    artifact_id,
                    now,
                    lease.campaign_id,
                    lease.action_id,
                    lease_id,
                ),
            )
        self.leases.release(
            lease_id=lease_id,
            actor=agent_id,
            reason="VALID_ARTIFACT_ACCEPTED",
        )
        self.receipts.append(
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            event_type="artifact_accepted",
            actor=agent_id,
            action_id=lease.action_id,
            lease_id=lease_id,
            artifact_id=artifact_id,
            event={
                "kind": artifact["kind"],
                "base_sha": artifact["base_sha"],
                "target_sha": target_sha,
                "payload_hash": payload_hash,
            },
        )
        return artifact_id

    def invalidate(
        self,
        *,
        artifact_id: str,
        reason: str,
        actor: str,
    ) -> None:
        with self.store.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM artifacts
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown artifact: {artifact_id}")
            if row["status"] == "INVALID":
                return
            connection.execute(
                """
                UPDATE artifacts
                SET
                    status = 'INVALID',
                    invalidated_at = ?,
                    invalidation_reason = ?
                WHERE artifact_id = ?
                """,
                (utc_now_text(), reason, artifact_id),
            )
            connection.execute(
                """
                UPDATE actions
                SET
                    status = 'INVALIDATED',
                    failure_reason = ?,
                    updated_at = ?
                WHERE
                    campaign_id = ?
                    AND action_id = ?
                    AND result_artifact_id = ?
                """,
                (
                    reason,
                    utc_now_text(),
                    row["campaign_id"],
                    row["action_id"],
                    artifact_id,
                ),
            )
            campaign_id = row["campaign_id"]
            graph_id = row["graph_id"]
            action_id = row["action_id"]
            lease_id = row["lease_id"]
        self.receipts.append(
            campaign_id=campaign_id,
            graph_id=graph_id,
            event_type="artifact_invalidated",
            actor=actor,
            action_id=action_id,
            lease_id=lease_id,
            artifact_id=artifact_id,
            event={"reason": reason},
        )

    def _validate_envelope(
        self,
        *,
        artifact: Mapping[str, Any],
        lease_id: str,
        campaign_id: str,
        graph_id: str,
        action_id: str,
        agent_id: str,
    ) -> None:
        required = {
            "artifact_id",
            "kind",
            "campaign_id",
            "graph_id",
            "action_id",
            "lease_id",
            "producer_agent_id",
            "base_sha",
            "input_artifacts",
            "payload",
        }
        missing = sorted(required - set(artifact))
        if missing:
            raise ContractError("Artifact envelope is missing fields: " + ", ".join(missing))
        expected = {
            "campaign_id": campaign_id,
            "graph_id": graph_id,
            "action_id": action_id,
            "lease_id": lease_id,
            "producer_agent_id": agent_id,
        }
        for field_name, expected_value in expected.items():
            if artifact.get(field_name) != expected_value:
                raise ContractError(
                    f"Artifact {field_name!r} mismatch: "
                    f"expected {expected_value!r}, "
                    f"got {artifact.get(field_name)!r}"
                )
        if not isinstance(artifact["payload"], Mapping):
            raise ContractError("Artifact payload must be an object")
        if not isinstance(artifact["input_artifacts"], list):
            raise ContractError("Artifact input_artifacts must be a list")
        if not str(artifact["artifact_id"]).strip():
            raise ContractError("Artifact artifact_id must be non-empty")

    def _validate_completion(
        self,
        *,
        artifact: Mapping[str, Any],
        completion: Mapping[str, Any],
        expected_base_sha: str,
    ) -> None:
        expected_kind = completion["artifact_kind"]
        if artifact["kind"] != expected_kind:
            raise ContractError(
                f"Artifact kind must be {expected_kind!r}, got {artifact['kind']!r}"
            )
        if (
            completion.get("require_base_sha_match", True)
            and artifact["base_sha"] != expected_base_sha
        ):
            raise ContractError("Artifact base SHA does not match the lease base SHA")
        payload = artifact["payload"]
        missing = [
            field_name
            for field_name in completion.get(
                "required_fields",
                [],
            )
            if field_name not in payload
        ]
        if missing:
            raise ContractError(
                "Artifact payload is missing required fields: " + ", ".join(sorted(missing))
            )
        if completion.get("require_empty_blockers", False):
            blockers = payload.get(
                "unresolved_blockers",
                payload.get("blockers", []),
            )
            if blockers:
                raise ContractError("Artifact cannot complete this action while blockers remain")

    def _validate_dependencies_current(
        self,
        *,
        campaign_id: str,
        action: Mapping[str, Any],
        artifact: Mapping[str, Any],
    ) -> None:
        declared_inputs = set(artifact["input_artifacts"])
        for dependency_id in action.get("depends_on", []):
            dependency = self.store.get_action(
                campaign_id,
                dependency_id,
            )
            if dependency["status"] != "COMPLETED":
                raise ContractError(f"Dependency {dependency_id!r} is not complete")
            dependency_artifact = dependency["result_artifact_id"]
            if dependency_artifact:
                if dependency_artifact not in declared_inputs:
                    raise ContractError(
                        f"Artifact does not declare required input "
                        f"{dependency_artifact!r} from dependency "
                        f"{dependency_id!r}"
                    )
                with self.store.connect() as connection:
                    artifact_row = connection.execute(
                        """
                        SELECT status
                        FROM artifacts
                        WHERE artifact_id = ?
                        """,
                        (dependency_artifact,),
                    ).fetchone()
                if artifact_row is None or artifact_row["status"] != "VALID":
                    raise ContractError(
                        f"Dependency artifact {dependency_artifact!r} is stale or invalid"
                    )
