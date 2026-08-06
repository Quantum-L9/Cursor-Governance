#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
if [[ ! -f "$ROOT/autonomy/models.py" ]]; then
  echo "ERROR: Wave 1 is not installed under $ROOT/autonomy" >&2
  exit 1
fi
mkdir -p \
  "$ROOT/autonomy/runtime" \
  "$ROOT/autonomy/schemas" \
  "$ROOT/autonomy/policies" \
  "$ROOT/autonomy/tests" \
  "$ROOT/.l9/autonomy"

cat > "$ROOT/autonomy/runtime/__init__.py" <<'PY'
"""
Wave 2 enforcement runtime.
This package provides:
- persistent campaign and action state
- capability-scoped leases
- resource claim arbitration
- lease heartbeats and revocation
- role and campaign tool authorization
- typed artifact validation
- critical-path scheduling
- tamper-evident receipt chaining
"""
__version__ = "1.0.0"
PY

cat > "$ROOT/autonomy/runtime/artifacts.py" <<'PY'
from __future__ import annotations

import json
from typing import Any, Mapping

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
                "LEASE_AGENT_MISMATCH: artifact producer does not "
                "match lease subject"
            )
        action_row = self.store.get_action(
            lease.campaign_id,
            lease.action_id,
        )
        if action_row["status"] not in {"LEASED", "RUNNING"}:
            raise PolicyViolation(
                "ACTION_NOT_RUNNING: cannot submit an artifact for "
                f"status {action_row['status']!r}"
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
            raise ContractError(
                "Artifact envelope is missing fields: " + ", ".join(missing)
            )
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
                f"Artifact kind must be {expected_kind!r}, "
                f"got {artifact['kind']!r}"
            )
        if (
            completion.get("require_base_sha_match", True)
            and artifact["base_sha"] != expected_base_sha
        ):
            raise ContractError(
                "Artifact base SHA does not match the lease base SHA"
            )
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
                "Artifact payload is missing required fields: "
                + ", ".join(sorted(missing))
            )
        if completion.get("require_empty_blockers", False):
            blockers = payload.get(
                "unresolved_blockers",
                payload.get("blockers", []),
            )
            if blockers:
                raise ContractError(
                    "Artifact cannot complete this action while blockers "
                    "remain"
                )

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
                raise ContractError(
                    f"Dependency {dependency_id!r} is not complete"
                )
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
                        f"Dependency artifact "
                        f"{dependency_artifact!r} is stale or invalid"
                    )
PY

cat > "$ROOT/autonomy/runtime/capability_gateway.py" <<'PY'
from __future__ import annotations

import fnmatch
import uuid
from pathlib import PurePosixPath
from typing import Any, Mapping

from autonomy.runtime.leases import LeaseManager
from autonomy.runtime.receipts import ReceiptChain
from autonomy.runtime.store import RuntimeStore, canonical_dump
from autonomy.runtime.timeutil import utc_now_text
from autonomy.runtime.types import AuthorizationDecision


class CapabilityGateway:
    def __init__(
        self,
        store: RuntimeStore,
        leases: LeaseManager,
        receipts: ReceiptChain,
        role_policy: Mapping[str, Any],
        operation_aliases: Mapping[str, Any],
    ) -> None:
        self.store = store
        self.leases = leases
        self.receipts = receipts
        self.role_policy = role_policy
        self.operation_aliases = operation_aliases

    def authorize(
        self,
        *,
        lease_id: str,
        agent_id: str,
        capability: str,
        resource: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuthorizationDecision:
        try:
            lease = self.leases.get(lease_id)
            self.leases.assert_active(lease)
        except Exception as exc:
            decision = AuthorizationDecision(
                allowed=False,
                code="LEASE_INVALID",
                message=str(exc),
                lease_id=lease_id,
                capability=capability,
                resource=resource,
            )
            self._record_unknown_lease_decision(
                lease_id=lease_id,
                agent_id=agent_id,
                capability=capability,
                resource=resource,
                decision=decision,
                metadata=metadata,
            )
            return decision
        if lease.agent_id != agent_id:
            return self._record(
                lease=lease,
                capability=capability,
                resource=resource,
                decision=AuthorizationDecision(
                    allowed=False,
                    code="LEASE_AGENT_MISMATCH",
                    message=(
                        f"Lease belongs to {lease.agent_id!r}, "
                        f"not {agent_id!r}"
                    ),
                    lease_id=lease_id,
                    capability=capability,
                    resource=resource,
                ),
                metadata=metadata,
            )
        if not bool(lease.metadata.get("acknowledged")):
            return self._record(
                lease=lease,
                capability=capability,
                resource=resource,
                decision=AuthorizationDecision(
                    allowed=False,
                    code="LEASE_NOT_ACKNOWLEDGED",
                    message="Agent must acknowledge the lease first",
                    lease_id=lease_id,
                    capability=capability,
                    resource=resource,
                ),
                metadata=metadata,
            )
        global_forbidden = set(
            self.role_policy.get(
                "globally_forbidden_capabilities",
                [],
            )
        )
        if capability in global_forbidden:
            return self._record(
                lease=lease,
                capability=capability,
                resource=resource,
                decision=AuthorizationDecision(
                    allowed=False,
                    code="GLOBALLY_FORBIDDEN_CAPABILITY",
                    message=(
                        f"Capability {capability!r} is globally forbidden"
                    ),
                    lease_id=lease_id,
                    capability=capability,
                    resource=resource,
                ),
                metadata=metadata,
            )
        role_config = self.role_policy.get("roles", {}).get(
            lease.role,
            {},
        )
        role_capabilities = set(role_config.get("capabilities", []))
        if capability not in role_capabilities:
            return self._record(
                lease=lease,
                capability=capability,
                resource=resource,
                decision=AuthorizationDecision(
                    allowed=False,
                    code="ROLE_CAPABILITY_DENIED",
                    message=(
                        f"Role {lease.role!r} does not grant "
                        f"{capability!r}"
                    ),
                    lease_id=lease_id,
                    capability=capability,
                    resource=resource,
                ),
                metadata=metadata,
            )
        accepted = set(lease.metadata.get("accepted_capabilities", []))
        if capability not in accepted:
            return self._record(
                lease=lease,
                capability=capability,
                resource=resource,
                decision=AuthorizationDecision(
                    allowed=False,
                    code="CAPABILITY_NOT_ACCEPTED",
                    message=(
                        f"Agent did not acknowledge capability "
                        f"{capability!r}"
                    ),
                    lease_id=lease_id,
                    capability=capability,
                    resource=resource,
                ),
                metadata=metadata,
            )
        campaign = self.store.decode_campaign(lease.campaign_id)
        action = self.store.decode_action(
            lease.campaign_id,
            lease.action_id,
        )
        operation = self.operation_aliases.get(
            "capability_to_operation",
            {},
        ).get(capability)
        if operation:
            allowed_operations = set(campaign["scope"]["allowed_operations"])
            forbidden_operations = set(
                campaign["scope"]["forbidden_operations"]
            )
            if operation in forbidden_operations:
                return self._record(
                    lease=lease,
                    capability=capability,
                    resource=resource,
                    decision=AuthorizationDecision(
                        allowed=False,
                        code="CAMPAIGN_OPERATION_FORBIDDEN",
                        message=(
                            f"Operation {operation!r} is forbidden "
                            "by the campaign"
                        ),
                        lease_id=lease_id,
                        capability=capability,
                        resource=resource,
                    ),
                    metadata=metadata,
                )
            if operation not in allowed_operations:
                return self._record(
                    lease=lease,
                    capability=capability,
                    resource=resource,
                    decision=AuthorizationDecision(
                        allowed=False,
                        code="CAMPAIGN_OPERATION_NOT_ALLOWED",
                        message=(
                            f"Operation {operation!r} is not granted "
                            "by the campaign"
                        ),
                        lease_id=lease_id,
                        capability=capability,
                        resource=resource,
                    ),
                    metadata=metadata,
                )
        if self._is_path_capability(capability):
            path_decision = self._authorize_path(
                campaign=campaign,
                action=action,
                resource=resource,
                capability=capability,
                lease_id=lease_id,
            )
            if not path_decision.allowed:
                return self._record(
                    lease=lease,
                    capability=capability,
                    resource=resource,
                    decision=path_decision,
                    metadata=metadata,
                )
        decision = AuthorizationDecision(
            allowed=True,
            code="ALLOWED",
            message="Capability authorized",
            lease_id=lease_id,
            capability=capability,
            resource=resource,
        )
        return self._record(
            lease=lease,
            capability=capability,
            resource=resource,
            decision=decision,
            metadata=metadata,
        )

    def require(
        self,
        **kwargs,
    ) -> AuthorizationDecision:
        decision = self.authorize(**kwargs)
        decision.require_allowed()
        return decision

    def _authorize_path(
        self,
        *,
        campaign: Mapping[str, Any],
        action: Mapping[str, Any],
        resource: str | None,
        capability: str,
        lease_id: str,
    ) -> AuthorizationDecision:
        if not resource:
            return AuthorizationDecision(
                allowed=False,
                code="RESOURCE_REQUIRED",
                message=(
                    f"Capability {capability!r} requires a path resource"
                ),
                lease_id=lease_id,
                capability=capability,
                resource=resource,
            )
        normalized = normalize_path(resource)
        forbidden = campaign["scope"]["forbidden_paths"]
        allowed = campaign["scope"]["allowed_paths"]
        if any(path_matches(pattern, normalized) for pattern in forbidden):
            return AuthorizationDecision(
                allowed=False,
                code="FORBIDDEN_PATH",
                message=f"Path {normalized!r} is forbidden",
                lease_id=lease_id,
                capability=capability,
                resource=normalized,
            )
        if not any(path_matches(pattern, normalized) for pattern in allowed):
            return AuthorizationDecision(
                allowed=False,
                code="PATH_OUTSIDE_CAMPAIGN_SCOPE",
                message=(
                    f"Path {normalized!r} is outside campaign scope"
                ),
                lease_id=lease_id,
                capability=capability,
                resource=normalized,
            )
        action_paths = action.get("metadata", {}).get(
            "allowed_paths",
            [],
        )
        if action_paths and not any(
            path_matches(pattern, normalized) for pattern in action_paths
        ):
            return AuthorizationDecision(
                allowed=False,
                code="PATH_OUTSIDE_ACTION_SCOPE",
                message=(
                    f"Path {normalized!r} is outside action scope"
                ),
                lease_id=lease_id,
                capability=capability,
                resource=normalized,
            )
        return AuthorizationDecision(
            allowed=True,
            code="PATH_ALLOWED",
            message="Path is within campaign and action scope",
            lease_id=lease_id,
            capability=capability,
            resource=normalized,
        )

    def _is_path_capability(self, capability: str) -> bool:
        prefixes = (
            "repository.",
            "file.",
            "git.diff",
        )
        return capability.startswith(prefixes)

    def _record(
        self,
        *,
        lease,
        capability: str,
        resource: str | None,
        decision: AuthorizationDecision,
        metadata: Mapping[str, Any] | None,
    ) -> AuthorizationDecision:
        decision_id = f"decision-{uuid.uuid4().hex}"
        now = utc_now_text()
        with self.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tool_decisions (
                    decision_id,
                    campaign_id,
                    action_id,
                    lease_id,
                    agent_id,
                    capability,
                    resource,
                    allowed,
                    code,
                    message,
                    metadata_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    lease.campaign_id,
                    lease.action_id,
                    lease.lease_id,
                    lease.agent_id,
                    capability,
                    resource,
                    int(decision.allowed),
                    decision.code,
                    decision.message,
                    canonical_dump(dict(metadata or {})),
                    now,
                ),
            )
        self.receipts.append(
            campaign_id=lease.campaign_id,
            graph_id=lease.graph_id,
            event_type=(
                "tool_authorized" if decision.allowed else "tool_denied"
            ),
            actor=lease.agent_id,
            action_id=lease.action_id,
            lease_id=lease.lease_id,
            event={
                "decision_id": decision_id,
                "capability": capability,
                "resource": resource,
                "allowed": decision.allowed,
                "code": decision.code,
            },
        )
        return decision

    def _record_unknown_lease_decision(
        self,
        *,
        lease_id: str,
        agent_id: str,
        capability: str,
        resource: str | None,
        decision: AuthorizationDecision,
        metadata: Mapping[str, Any] | None,
    ) -> None:
        # Unknown or invalid leases cannot be associated safely with a
        # campaign receipt chain. The caller still receives a hard denial.
        return None


def normalize_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute():
        raise ValueError("Resource paths must be repository-relative")
    parts = path.parts
    if ".." in parts:
        raise ValueError("Resource paths cannot contain '..'")
    normalized = str(path)
    if normalized in {"", "."}:
        raise ValueError("Resource path cannot be empty")
    return normalized


def path_matches(pattern: str, path: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/")
    return fnmatch.fnmatchcase(path, normalized_pattern)
PY

cat > "$ROOT/autonomy/runtime/claims.py" <<'PY'
from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

from autonomy.errors import PolicyViolation
from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text


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
                existing_mode = claim["mode"]
                existing_exclusive = bool(claim["exclusive"])
                conflict = (
                    requested_exclusive
                    or existing_exclusive
                    or requested_mode == "write"
                    or existing_mode == "write"
                )
                if conflict:
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
PY

cat > "$ROOT/autonomy/runtime/cli.py" <<'PY'
from __future__ import annotations

import argparse
import json
from typing import Any

from autonomy.io import load_json
from autonomy.runtime.engine import AutonomyRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="L9 Wave-2 autonomy runtime."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--database",
        help="Runtime SQLite database path.",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("--campaign", required=True)
    bootstrap.add_argument("--deployment", required=True)
    bootstrap.add_argument("--graph", required=True)
    status = commands.add_parser("status")
    status.add_argument("--campaign-id", required=True)
    ready = commands.add_parser("ready")
    ready.add_argument("--campaign-id", required=True)
    ready.add_argument("--limit", type=int)
    lease = commands.add_parser("lease")
    lease.add_argument("--campaign-id", required=True)
    lease.add_argument("--action-id", required=True)
    lease.add_argument("--agent-id", required=True)
    lease.add_argument("--ttl-seconds", type=int)
    acknowledge = commands.add_parser("ack")
    acknowledge.add_argument("--lease-id", required=True)
    acknowledge.add_argument("--agent-id", required=True)
    acknowledge.add_argument(
        "--capability",
        action="append",
        default=[],
    )
    heartbeat = commands.add_parser("heartbeat")
    heartbeat.add_argument("--lease-id", required=True)
    heartbeat.add_argument("--agent-id", required=True)
    heartbeat.add_argument("--base-sha", required=True)
    heartbeat.add_argument(
        "--status",
        default="running",
    )
    heartbeat.add_argument(
        "--progress-json",
        default="{}",
    )
    authorize = commands.add_parser("authorize")
    authorize.add_argument("--lease-id", required=True)
    authorize.add_argument("--agent-id", required=True)
    authorize.add_argument("--capability", required=True)
    authorize.add_argument("--resource")
    submit = commands.add_parser("submit")
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--artifact", required=True)
    commands.add_parser("sweep")
    verify = commands.add_parser("verify-receipts")
    verify.add_argument("--campaign-id", required=True)
    suspend = commands.add_parser("suspend")
    suspend.add_argument("--campaign-id", required=True)
    suspend.add_argument("--reason", required=True)
    suspend.add_argument("--actor", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    if args.command == "bootstrap":
        runtime.bootstrap(
            campaign_payload=load_json(args.campaign),
            deployment_payload=load_json(args.deployment),
            graph_payload=load_json(args.graph),
        )
        print("campaign bootstrapped")
        return 0
    if args.command == "status":
        print_json(runtime.status(args.campaign_id))
        return 0
    if args.command == "ready":
        actions = runtime.scheduler.next_actions(
            args.campaign_id,
            limit=args.limit,
        )
        print_json(
            [
                {
                    "action_id": action.action_id,
                    "role": action.role,
                    "resource_class": action.resource_class,
                    "score": action.score,
                    "mutation": action.mutation,
                }
                for action in actions
            ]
        )
        return 0
    if args.command == "lease":
        lease = runtime.leases.issue(
            campaign_id=args.campaign_id,
            action_id=args.action_id,
            agent_id=args.agent_id,
            ttl_seconds=args.ttl_seconds,
        )
        print_json(
            {
                "lease_id": lease.lease_id,
                "campaign_id": lease.campaign_id,
                "graph_id": lease.graph_id,
                "action_id": lease.action_id,
                "agent_id": lease.agent_id,
                "role": lease.role,
                "capability_id": lease.capability_id,
                "base_sha": lease.base_sha,
                "issued_at": lease.issued_at,
                "expires_at": lease.expires_at,
            }
        )
        return 0
    if args.command == "ack":
        runtime.leases.acknowledge(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            accepted_capabilities=args.capability,
        )
        print("lease acknowledged")
        return 0
    if args.command == "heartbeat":
        progress = json.loads(args.progress_json)
        runtime.leases.heartbeat(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            observed_base_sha=args.base_sha,
            status=args.status,
            progress=progress,
        )
        print("heartbeat accepted")
        return 0
    if args.command == "authorize":
        decision = runtime.gateway.authorize(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            capability=args.capability,
            resource=args.resource,
        )
        print_json(
            {
                "allowed": decision.allowed,
                "code": decision.code,
                "message": decision.message,
                "lease_id": decision.lease_id,
                "capability": decision.capability,
                "resource": decision.resource,
            }
        )
        return 0 if decision.allowed else 1
    if args.command == "submit":
        artifact_id = runtime.artifacts.submit(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            artifact=load_json(args.artifact),
        )
        print_json({"artifact_id": artifact_id})
        return 0
    if args.command == "sweep":
        print_json(runtime.leases.sweep())
        return 0
    if args.command == "verify-receipts":
        errors = runtime.verify_receipts(args.campaign_id)
        print_json({"valid": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.command == "suspend":
        runtime.suspend(
            campaign_id=args.campaign_id,
            reason=args.reason,
            actor=args.actor,
        )
        print("campaign suspended")
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$ROOT/autonomy/runtime/engine.py" <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from autonomy.io import load_json
from autonomy.models import (
    CampaignAuthorization,
    DeploymentManifest,
)
from autonomy.runtime.artifacts import ArtifactValidator
from autonomy.runtime.capability_gateway import CapabilityGateway
from autonomy.runtime.claims import ClaimRegistry
from autonomy.runtime.leases import LeaseManager
from autonomy.runtime.receipts import ReceiptChain
from autonomy.runtime.scheduler import Scheduler
from autonomy.runtime.store import RuntimeStore
from autonomy.validation.graph_linter import GraphLinter


class AutonomyRuntime:
    def __init__(
        self,
        *,
        database_path: str | Path,
        role_policy: Mapping[str, Any],
        pipeline_policy: Mapping[str, Any],
        resource_policy: Mapping[str, Any],
        operation_aliases: Mapping[str, Any],
        signing_key: str | None = None,
        default_lease_ttl_seconds: int = 900,
        stale_after_seconds: int = 90,
        revoke_after_seconds: int = 180,
    ) -> None:
        self.store = RuntimeStore(database_path)
        self.receipts = ReceiptChain(
            self.store,
            signing_key=signing_key,
        )
        self.claims = ClaimRegistry(self.store)
        self.leases = LeaseManager(
            self.store,
            self.claims,
            self.receipts,
            default_ttl_seconds=default_lease_ttl_seconds,
            stale_after_seconds=stale_after_seconds,
            revoke_after_seconds=revoke_after_seconds,
        )
        self.gateway = CapabilityGateway(
            self.store,
            self.leases,
            self.receipts,
            role_policy,
            operation_aliases,
        )
        self.artifacts = ArtifactValidator(
            self.store,
            self.leases,
            self.receipts,
        )
        self.scheduler = Scheduler(
            self.store,
            resource_policy,
        )
        self.role_policy = role_policy
        self.pipeline_policy = pipeline_policy

    @classmethod
    def from_repository(
        cls,
        *,
        repository_root: str | Path = ".",
        database_path: str | Path | None = None,
        signing_key: str | None = None,
    ) -> "AutonomyRuntime":
        root = Path(repository_root)
        return cls(
            database_path=(
                database_path or root / ".l9/autonomy/runtime.sqlite3"
            ),
            role_policy=load_json(
                root / "autonomy/policies/role-capabilities.json"
            ),
            pipeline_policy=load_json(
                root / "autonomy/policies/pipeline-invariants.json"
            ),
            resource_policy=load_json(
                root / "autonomy/policies/resource-classes.json"
            ),
            operation_aliases=load_json(
                root / "autonomy/policies/operation-aliases.json"
            ),
            signing_key=signing_key,
        )

    def bootstrap(
        self,
        *,
        campaign_payload: Mapping[str, Any],
        deployment_payload: Mapping[str, Any],
        graph_payload: Mapping[str, Any],
    ) -> None:
        campaign = CampaignAuthorization.from_dict(campaign_payload)
        deployment = DeploymentManifest.from_dict(deployment_payload)
        if graph_payload["campaign_id"] != campaign.campaign_id:
            raise ValueError(
                "Compiled graph campaign ID does not match campaign"
            )
        if deployment.graph_id not in {
            "AUTO",
            graph_payload["graph_id"],
        }:
            raise ValueError(
                "Deployment graph ID does not match compiled graph"
            )
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        linter.assert_valid(graph_payload)
        self.store.register_campaign(
            campaign_payload,
            graph_payload,
        )
        self.receipts.append(
            campaign_id=campaign.campaign_id,
            graph_id=graph_payload["graph_id"],
            event_type="campaign_bootstrapped",
            actor="runtime",
            event={
                "base_sha": campaign.base_state["commit_sha"],
                "deployment_id": deployment.deployment_id,
                "graph_hash": graph_payload.get("graph_hash"),
            },
        )
        self.scheduler.refresh_readiness(campaign.campaign_id)

    def status(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.store.get_campaign(campaign_id)
        actions = self.store.list_actions(campaign_id)
        return {
            "campaign_id": campaign_id,
            "graph_id": campaign["graph_id"],
            "state": campaign["state"],
            "base_sha": campaign["base_sha"],
            "actions": [
                {
                    "action_id": row["action_id"],
                    "role": row["role"],
                    "status": row["status"],
                    "resource_class": row["resource_class"],
                    "agent_id": row["assigned_agent_id"],
                    "lease_id": row["active_lease_id"],
                    "artifact_id": row["result_artifact_id"],
                    "failure_reason": row["failure_reason"],
                }
                for row in actions
            ],
            "ready": [
                {
                    "action_id": item.action_id,
                    "role": item.role,
                    "resource_class": item.resource_class,
                    "score": item.score,
                    "mutation": item.mutation,
                }
                for item in self.scheduler.next_actions(campaign_id)
            ],
        }

    def suspend(
        self,
        *,
        campaign_id: str,
        reason: str,
        actor: str,
    ) -> None:
        campaign = self.store.get_campaign(campaign_id)
        with self.store.connect() as connection:
            active_leases = list(
                connection.execute(
                    """
                    SELECT lease_id
                    FROM leases
                    WHERE
                        campaign_id = ?
                        AND status = 'ACTIVE'
                    """,
                    (campaign_id,),
                )
            )
        for row in active_leases:
            self.leases.revoke(
                lease_id=row["lease_id"],
                reason=f"CAMPAIGN_SUSPENDED: {reason}",
                actor=actor,
            )
        self.store.set_campaign_state(
            campaign_id,
            "SUSPENDED",
        )
        self.receipts.append(
            campaign_id=campaign_id,
            graph_id=campaign["graph_id"],
            event_type="campaign_suspended",
            actor=actor,
            event={"reason": reason},
        )

    def verify_receipts(
        self,
        campaign_id: str,
    ) -> list[str]:
        return self.receipts.verify(campaign_id)
PY

cat > "$ROOT/autonomy/runtime/leases.py" <<'PY'
from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any, Mapping

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
            raise ValueError(
                "revoke_after_seconds must be >= stale_after_seconds"
            )
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
                "CAMPAIGN_NOT_EXECUTABLE: campaign state is "
                f"{campaign['state']!r}"
            )
        if action_row["status"] != "READY":
            raise PolicyViolation(
                f"ACTION_NOT_READY: {action_id!r} status is "
                f"{action_row['status']!r}"
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
                "LEASE_AGENT_MISMATCH: acknowledgment agent does not "
                "match lease subject"
            )
        if lease.status is not LeaseStatus.ACTIVE:
            raise PolicyViolation(
                f"LEASE_NOT_ACTIVE: status={lease.status.value}"
            )
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
            event={
                "accepted_capabilities": sorted(set(accepted_capabilities))
            },
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
                "LEASE_AGENT_MISMATCH: heartbeat agent does not match "
                "lease subject"
            )
        self.assert_active(lease)
        if observed_base_sha != lease.base_sha:
            self.revoke(
                lease_id=lease_id,
                reason=(
                    "BASE_SHA_DRIFT: expected "
                    f"{lease.base_sha}, observed {observed_base_sha}"
                ),
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
                    reason=(
                        "HEARTBEAT_TIMEOUT: no heartbeat for "
                        f"{int(heartbeat_age)} seconds"
                    ),
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
            raise PolicyViolation(
                f"LEASE_NOT_ACTIVE: status={lease.status.value}"
            )
        now = utc_now()
        if now >= parse_timestamp(lease.expires_at):
            self.revoke(
                lease_id=lease.lease_id,
                reason="LEASE_EXPIRED",
                actor="lease-manager",
                terminal_status="EXPIRED",
            )
            raise PolicyViolation("LEASE_EXPIRED")
PY

cat > "$ROOT/autonomy/runtime/receipts.py" <<'PY'
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Any, Mapping

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
            signing_key
            if signing_key is not None
            else os.environ.get("L9_AUTONOMY_RECEIPT_KEY")
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
            previous_hash = (
                previous["receipt_hash"] if previous is not None else GENESIS_HASH
            )
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
            receipt_hash = hashlib.sha256(
                canonical_dump(body).encode("utf-8")
            ).hexdigest()
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
            calculated = hashlib.sha256(
                canonical_dump(body).encode("utf-8")
            ).hexdigest()
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
PY

cat > "$ROOT/autonomy/runtime/scheduler.py" <<'PY'
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping

from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text
from autonomy.runtime.types import ScheduledAction

TERMINAL_SUCCESS = {"COMPLETED", "SKIPPED"}
ACTIVE_STATUSES = {"LEASED", "RUNNING"}


class Scheduler:
    def __init__(
        self,
        store: RuntimeStore,
        resource_policy: Mapping[str, Any],
    ) -> None:
        self.store = store
        self.resource_policy = resource_policy

    def refresh_readiness(self, campaign_id: str) -> list[str]:
        campaign = self.store.get_campaign(campaign_id)
        graph = json.loads(campaign["graph_json"])
        action_rows = {
            row["action_id"]: row for row in self.store.list_actions(campaign_id)
        }
        became_ready: list[str] = []
        now = utc_now_text()
        with self.store.transaction() as connection:
            for action in graph["actions"]:
                row = action_rows[action["id"]]
                if row["status"] not in {
                    "PENDING",
                    "BLOCKED",
                    "INVALIDATED",
                }:
                    continue
                dependencies = action.get("depends_on", [])
                dependencies_complete = all(
                    action_rows[dependency]["status"] in TERMINAL_SUCCESS
                    for dependency in dependencies
                )
                if not dependencies_complete:
                    continue
                if not self._condition_satisfied(
                    action=action,
                    action_rows=action_rows,
                ):
                    continue
                connection.execute(
                    """
                    UPDATE actions
                    SET
                        status = 'READY',
                        failure_reason = NULL,
                        updated_at = ?
                    WHERE campaign_id = ? AND action_id = ?
                    """,
                    (now, campaign_id, action["id"]),
                )
                became_ready.append(action["id"])
        return became_ready

    def next_actions(
        self,
        campaign_id: str,
        *,
        limit: int | None = None,
    ) -> list[ScheduledAction]:
        self.refresh_readiness(campaign_id)
        action_rows = self.store.list_actions(campaign_id)
        active_by_resource = Counter(
            row["resource_class"]
            for row in action_rows
            if row["status"] in ACTIVE_STATUSES
        )
        resource_classes = self.resource_policy.get(
            "classes",
            {},
        )
        candidates: list[ScheduledAction] = []
        for row in action_rows:
            if row["status"] != "READY":
                continue
            resource_class = row["resource_class"]
            config = resource_classes.get(resource_class)
            if not isinstance(config, Mapping):
                continue
            capacity = int(config.get("capacity", 0))
            if active_by_resource[resource_class] >= capacity:
                continue
            action = json.loads(row["action_json"])
            if action["kind"] == "human_gate":
                continue
            score = float(row["priority_weight"]) * float(row["critical_depth"])
            if action.get("mutation"):
                score *= 1.15
            candidates.append(
                ScheduledAction(
                    action_id=row["action_id"],
                    role=row["role"],
                    resource_class=resource_class,
                    score=score,
                    mutation=bool(row["mutation"]),
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.score,
                item.action_id,
            )
        )
        if limit is not None:
            return candidates[:limit]
        return candidates

    def _condition_satisfied(
        self,
        *,
        action: Mapping[str, Any],
        action_rows: Mapping[str, Any],
    ) -> bool:
        conditional_on = action.get("conditional_on")
        if not conditional_on:
            return True
        condition_row = action_rows.get(conditional_on)
        return (
            condition_row is not None
            and condition_row["status"] in TERMINAL_SUCCESS
        )
PY

cat > "$ROOT/autonomy/runtime/store.py" <<'PY'
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

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
                        f"Campaign {campaign_id!r} is already registered "
                        "with different contracts"
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
            raise KeyError(
                f"Unknown action {action_id!r} in campaign {campaign_id!r}"
            )
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
                raise KeyError(
                    f"Unknown action {action_id!r} "
                    f"in campaign {campaign_id!r}"
                )

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
PY

cat > "$ROOT/autonomy/runtime/timeutil.py" <<'PY'
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    normalized = value
    if value.endswith("Z"):
        normalized = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def add_seconds(value: datetime, seconds: int) -> datetime:
    return value + timedelta(seconds=seconds)


def timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
PY

cat > "$ROOT/autonomy/runtime/types.py" <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
    SKIPPED = "SKIPPED"


class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class CampaignRuntimeState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    LOCKED = "LOCKED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Lease:
    lease_id: str
    campaign_id: str
    graph_id: str
    action_id: str
    agent_id: str
    role: str
    status: LeaseStatus
    issued_at: str
    expires_at: str
    last_heartbeat_at: str
    capability_id: str
    base_sha: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    code: str
    message: str
    lease_id: str | None = None
    capability: str | None = None
    resource: str | None = None

    def require_allowed(self) -> None:
        if not self.allowed:
            from autonomy.errors import PolicyViolation

            raise PolicyViolation(f"{self.code}: {self.message}")


@dataclass(frozen=True)
class ScheduledAction:
    action_id: str
    role: str
    resource_class: str
    score: float
    mutation: bool
PY

cat > "$ROOT/autonomy/policies/operation-aliases.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "capability_to_operation": {
    "campaign.inspect": "read",
    "graph.inspect": "read",
    "scheduler.request": "read",
    "status.inspect": "read",
    "repository.read": "read",
    "repository.search": "search",
    "repository.write_scoped": "edit_scoped",
    "graphiti.read": "read",
    "artifact.write_recon_report": "edit_scoped",
    "artifact.read_recon_report": "read",
    "artifact.write_execution_brief": "edit_scoped",
    "test.run": "run_tests",
    "git.diff": "read",
    "git.commit_local": "commit_local",
    "artifact.write_execution_result": "edit_scoped",
    "diff.inspect": "read",
    "runtime.probe": "read",
    "evidence.inspect": "read",
    "artifact.write_verification_report": "edit_scoped",
    "test.inspect": "inspect_ci",
    "receipt.inspect": "read",
    "artifact.write_review_verdict": "edit_scoped",
    "pr.inspect": "inspect_review",
    "ci.inspect": "inspect_ci",
    "review.inspect": "inspect_review",
    "artifact.write_poll_report": "edit_scoped",
    "artifact.write_remediation_brief": "edit_scoped",
    "git.push_non_force_declared_branch": "push_non_force_declared_branch",
    "artifact.write_remediation_result": "edit_scoped",
    "artifact.read": "read",
    "artifact.write_context_pack": "edit_scoped",
    "git.inspect": "read",
    "artifact.invalidate": "edit_scoped",
    "campaign.suspend": "read",
    "artifact.write_sentinel_report": "edit_scoped",
    "receipt.append": "read",
    "artifact.write_evidence_receipt": "edit_scoped",
    "git.force_push": "force_push",
    "pr.merge": "merge",
    "pr.admin_merge": "admin_merge",
    "secret.read": "modify_secrets",
    "secret.write": "modify_secrets",
    "test.weaken_for_green": "weaken_tests_for_green"
  }
}
JSON

cat > "$ROOT/autonomy/schemas/agent-lease.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/agent-lease.schema.json",
  "title": "L9 Agent Lease",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "lease_id",
    "campaign_id",
    "graph_id",
    "action_id",
    "agent_id",
    "role",
    "capability_id",
    "base_sha",
    "status",
    "issued_at",
    "expires_at",
    "last_heartbeat_at"
  ],
  "properties": {
    "lease_id": {
      "type": "string",
      "minLength": 1
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "graph_id": {
      "type": "string",
      "minLength": 1
    },
    "action_id": {
      "type": "string",
      "minLength": 1
    },
    "agent_id": {
      "type": "string",
      "minLength": 1
    },
    "role": {
      "type": "string",
      "minLength": 1
    },
    "capability_id": {
      "type": "string",
      "minLength": 1
    },
    "base_sha": {
      "type": "string",
      "minLength": 1
    },
    "status": {
      "type": "string",
      "enum": [
        "ACTIVE",
        "RELEASED",
        "REVOKED",
        "EXPIRED"
      ]
    },
    "issued_at": {
      "type": "string",
      "format": "date-time"
    },
    "expires_at": {
      "type": "string",
      "format": "date-time"
    },
    "last_heartbeat_at": {
      "type": "string",
      "format": "date-time"
    },
    "revoked_reason": {
      "type": [
        "string",
        "null"
      ]
    },
    "metadata": {
      "type": "object"
    },
    "accepted_capabilities": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true
    }
  }
}
JSON

cat > "$ROOT/autonomy/schemas/artifact-envelope.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/artifact-envelope.schema.json",
  "title": "L9 Artifact Envelope",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "kind",
    "campaign_id",
    "graph_id",
    "action_id",
    "lease_id",
    "base_sha",
    "payload",
    "producer_agent_id"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "artifact_id": {
      "type": "string",
      "minLength": 1
    },
    "kind": {
      "type": "string",
      "minLength": 1
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "graph_id": {
      "type": "string",
      "minLength": 1
    },
    "action_id": {
      "type": "string",
      "minLength": 1
    },
    "lease_id": {
      "type": "string",
      "minLength": 1
    },
    "base_sha": {
      "type": "string",
      "minLength": 1
    },
    "target_sha": {
      "type": [
        "string",
        "null"
      ]
    },
    "payload": {
      "type": "object"
    },
    "producer_agent_id": {
      "type": "string",
      "minLength": 1
    },
    "produced_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
JSON

cat > "$ROOT/autonomy/schemas/orchestration-receipt.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quantum-l9.dev/schemas/orchestration-receipt.schema.json",
  "title": "L9 Orchestration Receipt",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "receipt_id",
    "campaign_id",
    "graph_id",
    "event_type",
    "actor",
    "event",
    "previous_receipt_hash",
    "receipt_hash",
    "created_at"
  ],
  "properties": {
    "receipt_id": {
      "type": "string",
      "minLength": 1
    },
    "campaign_id": {
      "type": "string",
      "minLength": 1
    },
    "graph_id": {
      "type": "string",
      "minLength": 1
    },
    "event_type": {
      "type": "string",
      "minLength": 1
    },
    "actor": {
      "type": "string",
      "minLength": 1
    },
    "action_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "lease_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "artifact_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "event": {
      "type": "object"
    },
    "previous_receipt_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$"
    },
    "receipt_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$"
    },
    "signature": {
      "type": [
        "string",
        "null"
      ]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
JSON

cat > "$ROOT/autonomy/tests/test_wave2.py" <<'PY'
from __future__ import annotations

import copy
import tempfile
import unittest
import uuid
from pathlib import Path

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import ContractError, PolicyViolation
from autonomy.io import load_json
from autonomy.models import (
    CampaignAuthorization,
    DeploymentManifest,
)
from autonomy.runtime.engine import AutonomyRuntime

ROOT = Path(__file__).resolve().parents[2]


class Wave2RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        self.campaign_payload = load_json(
            ROOT / "autonomy/examples/w7-campaign.json"
        )
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(
            ROOT / "autonomy/examples/w7-deployment.json"
        )
        self.actions_payload = load_json(
            ROOT / "autonomy/examples/w7-actions.json"
        )
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(
            campaign,
            deployment,
            self.actions_payload,
        )
        self.graph_payload = compiled.to_dict()
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="test-signing-key",
        )
        self.runtime.bootstrap(
            campaign_payload=self.campaign_payload,
            deployment_payload=self.deployment_payload,
            graph_payload=self.graph_payload,
        )
        self.campaign_id = self.campaign_payload["campaign_id"]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initial_actions_become_ready(self) -> None:
        ready = self.runtime.scheduler.next_actions(self.campaign_id)
        ids = {item.action_id for item in ready}
        self.assertIn("campaign-coordinator", ids)
        self.assertNotIn("execute-m0", ids)

    def test_lease_requires_ready_action(self) -> None:
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.issue(
                campaign_id=self.campaign_id,
                action_id="execute-m0",
                agent_id="executor-1",
            )

    def test_role_capability_is_enforced(self) -> None:
        self.runtime.scheduler.refresh_readiness(self.campaign_id)
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=[
                "campaign.inspect",
                "repository.write_scoped",
            ],
        )
        denied = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="repository.write_scoped",
            resource="autonomy/README.md",
        )
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.code, "ROLE_CAPABILITY_DENIED")
        allowed = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="campaign.inspect",
        )
        self.assertTrue(allowed.allowed)

    def test_unacknowledged_lease_cannot_use_tools(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        decision = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="campaign.inspect",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "LEASE_NOT_ACKNOWLEDGED")

    def test_base_sha_drift_revokes_lease(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["campaign.inspect"],
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.heartbeat(
                lease_id=lease.lease_id,
                agent_id="coordinator-1",
                observed_base_sha="different-sha",
                status="running",
            )
        revoked = self.runtime.leases.get(lease.lease_id)
        self.assertEqual(revoked.status.value, "REVOKED")

    def test_claim_conflict_blocks_second_writer(self) -> None:
        # Force two independent writer actions ready for this isolated
        # arbitration test.
        with self.runtime.store.transaction() as connection:
            execute = self.runtime.store.decode_action(
                self.campaign_id,
                "execute-m0",
            )
            duplicate = copy.deepcopy(execute)
            duplicate["id"] = "execute-m0-duplicate"
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
                )
                SELECT
                    campaign_id,
                    ?,
                    role,
                    kind,
                    'READY',
                    mutation,
                    resource_class,
                    priority_weight,
                    critical_depth,
                    ?,
                    created_at,
                    updated_at
                FROM actions
                WHERE campaign_id = ? AND action_id = 'execute-m0'
                """,
                (
                    duplicate["id"],
                    __import__("json").dumps(
                        duplicate,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    self.campaign_id,
                ),
            )
            connection.execute(
                """
                UPDATE actions
                SET status = 'READY'
                WHERE
                    campaign_id = ?
                    AND action_id = 'execute-m0'
                """,
                (self.campaign_id,),
            )
        first = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="execute-m0",
            agent_id="executor-1",
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.issue(
                campaign_id=self.campaign_id,
                action_id="execute-m0-duplicate",
                agent_id="executor-2",
            )
        self.runtime.leases.revoke(
            lease_id=first.lease_id,
            reason="test cleanup",
            actor="test",
        )

    def test_valid_artifact_completes_action(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        accepted = [
            "campaign.inspect",
            "graph.inspect",
            "scheduler.request",
            "status.inspect",
        ]
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=accepted,
        )
        artifact_id = f"artifact-{uuid.uuid4().hex}"
        submitted = self.runtime.artifacts.submit(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            artifact={
                "artifact_id": artifact_id,
                "kind": "CampaignStatus",
                "campaign_id": self.campaign_id,
                "graph_id": self.graph_payload["graph_id"],
                "action_id": "campaign-coordinator",
                "lease_id": lease.lease_id,
                "producer_agent_id": "coordinator-1",
                "base_sha": "abc1234",
                "input_artifacts": [],
                "payload": {
                    "campaign_id": self.campaign_id,
                    "state": "EXECUTING",
                },
            },
        )
        self.assertEqual(submitted, artifact_id)
        action = self.runtime.store.get_action(
            self.campaign_id,
            "campaign-coordinator",
        )
        self.assertEqual(action["status"], "COMPLETED")

    def test_missing_artifact_field_is_rejected(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["campaign.inspect"],
        )
        with self.assertRaises(ContractError):
            self.runtime.artifacts.submit(
                lease_id=lease.lease_id,
                agent_id="coordinator-1",
                artifact={
                    "artifact_id": f"artifact-{uuid.uuid4().hex}",
                    "kind": "CampaignStatus",
                    "campaign_id": self.campaign_id,
                    "graph_id": self.graph_payload["graph_id"],
                    "action_id": "campaign-coordinator",
                    "lease_id": lease.lease_id,
                    "producer_agent_id": "coordinator-1",
                    "base_sha": "abc1234",
                    "input_artifacts": [],
                    "payload": {"campaign_id": self.campaign_id},
                },
            )

    def test_receipt_chain_verifies(self) -> None:
        errors = self.runtime.verify_receipts(self.campaign_id)
        self.assertEqual(errors, [])

    def test_forbidden_global_capability_is_denied(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["pr.merge"],
        )
        decision = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="pr.merge",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "GLOBALLY_FORBIDDEN_CAPABILITY")


if __name__ == "__main__":
    unittest.main()
PY

cat > "$ROOT/autonomy/README.md" <<'MD'
# L9 Enforceable Autonomy Control Plane

Wave 1 converts autonomy orchestration from IDE convention into validated,
machine-readable contracts.

## Properties enforced

- Campaigns require resolved base SHAs.
- Autonomous merge, admin merge, and force push are forbidden.
- Executors require synthesis inputs.
- Mutation roles require exclusive write claims.
- Read-only roles cannot request write claims.
- Reviewers must be independent from executors.
- Reviews must consume verifier outputs.
- Every action declares a typed completion artifact.
- Role cardinality is validated before execution.
- Action graphs must be acyclic and dependency-complete.

## Compile the W7 graph

Replace the example base SHA first:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("autonomy/examples/w7-campaign.json")
data = json.loads(path.read_text())
data["base_state"]["commit_sha"] = "YOUR_RESOLVED_BASE_SHA"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
```

Compile:

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

Validate:

```bash
python -m autonomy.validation.graph_linter \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --deployment autonomy/examples/w7-deployment.json
```

Run tests:

```bash
python -m unittest discover -s autonomy/tests -v
```

## Wave boundaries

Wave 1 only compiles and validates authority and topology.

It intentionally does not yet grant leases or mediate tools. Runtime mutation
must remain disabled until Wave 2 is installed and its capability gateway is
active.

---

# Wave 2 — Enforcement Runtime

Wave 2 installs the runtime that enforces the Wave 1 graph.

## Runtime properties

- SQLite-backed durable campaign state.
- Exactly one active lease per action.
- Resource claims are checked transactionally.
- Write claims are exclusive.
- Agent identity is bound to each lease.
- Leases must be acknowledged before tools are authorized.
- Role capabilities are enforced at the tool gateway.
- Campaign operation and path scope are enforced.
- Global merge, force-push, secret, and test-weakening capabilities are denied.
- Heartbeat base-SHA drift revokes the lease.
- Typed artifacts are checked against action completion predicates.
- Dependency artifacts must remain valid.
- Accepted artifacts complete actions and release claims.
- Runtime decisions are appended to a hash-linked receipt chain.
- Optional HMAC receipt signatures use `L9_AUTONOMY_RECEIPT_KEY`.

## Compile the graph

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

## Bootstrap the runtime

```bash
python -m autonomy.runtime.cli \
  --root . \
  bootstrap \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --graph .l9/autonomy/w7-compiled-graph.json
```

## Inspect ready work

```bash
python -m autonomy.runtime.cli \
  --root . \
  ready \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Issue a lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  lease \
  --campaign-id autonomy-w7-mothball-2026-08-02 \
  --action-id campaign-coordinator \
  --agent-id cursor-agent-001
```

## Acknowledge the lease

```bash
python -m autonomy.runtime.cli \
  --root . \
  ack \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect \
  --capability graph.inspect \
  --capability scheduler.request \
  --capability status.inspect
```

## Authorize a tool call

```bash
python -m autonomy.runtime.cli \
  --root . \
  authorize \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --capability campaign.inspect
```

A denied authorization exits non-zero.

## Heartbeat

```bash
python -m autonomy.runtime.cli \
  --root . \
  heartbeat \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --base-sha YOUR_RESOLVED_BASE_SHA \
  --status running \
  --progress-json '{"completed_units":3,"total_units":8}'
```

## Submit a typed artifact

```bash
python -m autonomy.runtime.cli \
  --root . \
  submit \
  --lease-id LEASE_ID \
  --agent-id cursor-agent-001 \
  --artifact path/to/artifact.json
```

The artifact envelope must match:

```json
{
  "artifact_id": "artifact-unique-id",
  "kind": "CampaignStatus",
  "campaign_id": "autonomy-w7-mothball-2026-08-02",
  "graph_id": "compiled-graph-id",
  "action_id": "campaign-coordinator",
  "lease_id": "lease-id",
  "producer_agent_id": "cursor-agent-001",
  "base_sha": "resolved-base-sha",
  "input_artifacts": [],
  "payload": {
    "campaign_id": "autonomy-w7-mothball-2026-08-02",
    "state": "EXECUTING"
  }
}
```

## Sweep stale leases

```bash
python -m autonomy.runtime.cli \
  --root . \
  sweep
```

## Verify receipt integrity

```bash
python -m autonomy.runtime.cli \
  --root . \
  verify-receipts \
  --campaign-id autonomy-w7-mothball-2026-08-02
```

## Runtime database

The default database is:

```text
.l9/autonomy/runtime.sqlite3
```

Do not commit it. `.l9/` is already gitignored.

## Security boundary

Wave 2 mediates capability decisions in the runtime. The IDE must still be
wired so every relevant tool invocation calls the gateway before execution.
Wave 3 supplies the Cursor and Claude Code adapters, conformance checks,
deployment handshake, pipeline simulator, and negative/chaos validation.
MD

echo "Wave 2 installed under: $ROOT/autonomy/runtime"
echo
echo "Next steps:"
echo "  1. Compile the Wave 1 graph (resolved base SHA required)."
echo "  2. Bootstrap: python -m autonomy.runtime.cli --root . bootstrap ..."
echo "  3. Do not enable IDE mutation until Wave 3 adapters pass conformance."

