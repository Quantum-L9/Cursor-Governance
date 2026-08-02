from __future__ import annotations

import fnmatch
import uuid
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from autonomy.errors import PolicyViolation
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
        except (KeyError, LookupError, ValueError, RuntimeError, PolicyViolation) as exc:
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
                    message=(f"Lease belongs to {lease.agent_id!r}, not {agent_id!r}"),
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
                    message=(f"Capability {capability!r} is globally forbidden"),
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
                    message=(f"Role {lease.role!r} does not grant {capability!r}"),
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
                    message=(f"Agent did not acknowledge capability {capability!r}"),
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
            forbidden_operations = set(campaign["scope"]["forbidden_operations"])
            if operation in forbidden_operations:
                return self._record(
                    lease=lease,
                    capability=capability,
                    resource=resource,
                    decision=AuthorizationDecision(
                        allowed=False,
                        code="CAMPAIGN_OPERATION_FORBIDDEN",
                        message=(f"Operation {operation!r} is forbidden by the campaign"),
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
                        message=(f"Operation {operation!r} is not granted by the campaign"),
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
                message=(f"Capability {capability!r} requires a path resource"),
                lease_id=lease_id,
                capability=capability,
                resource=resource,
            )
        try:
            normalized = normalize_path(resource)
        except ValueError as exc:
            return AuthorizationDecision(
                allowed=False,
                code="INVALID_PATH",
                message=str(exc),
                lease_id=lease_id,
                capability=capability,
                resource=resource,
            )
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
                message=(f"Path {normalized!r} is outside campaign scope"),
                lease_id=lease_id,
                capability=capability,
                resource=normalized,
            )
        action_paths = action.get("metadata", {}).get(
            "allowed_paths",
            [],
        )
        if action_paths and not any(path_matches(pattern, normalized) for pattern in action_paths):
            return AuthorizationDecision(
                allowed=False,
                code="PATH_OUTSIDE_ACTION_SCOPE",
                message=(f"Path {normalized!r} is outside action scope"),
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
            event_type=("tool_authorized" if decision.allowed else "tool_denied"),
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
        # Persist denials for unknown/invalid leases so audits see the attempt.
        # Campaign/action are empty because the lease cannot be resolved safely.
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
                    "",
                    "",
                    lease_id,
                    agent_id,
                    capability,
                    resource,
                    int(decision.allowed),
                    decision.code,
                    decision.message,
                    canonical_dump(dict(metadata or {})),
                    now,
                ),
            )


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
