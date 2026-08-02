from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.contract_renderer import render_agent_contract
from autonomy.adapters.protocol import AdapterConfig
from autonomy.errors import PolicyViolation
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.runtime.store import canonical_dump
from autonomy.runtime.timeutil import utc_now_text


class AdapterOrchestrator:
    def __init__(
        self,
        runtime: AutonomyRuntime,
        repository_root: str | Path = ".",
    ) -> None:
        self.runtime = runtime
        self.repository_root = Path(repository_root).resolve()
        self.requirements = self._load_requirements()
        self.conformance = AdapterConformance(
            self.requirements,
            self.repository_root,
        )
        self._initialize_extension_tables()

    def register(
        self,
        config_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        config = AdapterConfig.from_dict(config_payload)
        report = self.conformance.run(config)
        session_id = f"adapter-session-{uuid.uuid4().hex}"
        now = utc_now_text()
        with self.runtime.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO adapter_sessions (
                    session_id,
                    adapter_id,
                    adapter_type,
                    protocol_version,
                    status,
                    config_json,
                    conformance_json,
                    created_at,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    config.adapter_id,
                    config.adapter_type.value,
                    config.protocol_version,
                    report.status.value,
                    canonical_dump(dict(config_payload)),
                    canonical_dump(report.to_dict()),
                    now,
                    now,
                ),
            )
        return {
            "session_id": session_id,
            "conformance": report.to_dict(),
        }

    def require_conformant_session(self, session_id: str):
        with self.runtime.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM adapter_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise PolicyViolation(f"ADAPTER_SESSION_UNKNOWN: {session_id}")
        if row["status"] != "PASS":
            raise PolicyViolation(
                "ADAPTER_CONFORMANCE_FAILED: campaign execution is blocked for this adapter session"
            )
        with self.runtime.store.transaction() as connection:
            connection.execute(
                """
                UPDATE adapter_sessions
                SET last_seen_at = ?
                WHERE session_id = ?
                """,
                (utc_now_text(), session_id),
            )
        return row

    def request_agent(
        self,
        *,
        session_id: str,
        campaign_id: str,
        agent_id: str,
        action_id: str | None = None,
        requested_role: str | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        session = self.require_conformant_session(session_id)
        ready = self.runtime.scheduler.next_actions(campaign_id)
        selected = None
        if action_id:
            selected = next(
                (item for item in ready if item.action_id == action_id),
                None,
            )
            if selected is None:
                raise PolicyViolation(f"ACTION_NOT_RUNNABLE: {action_id!r}")
        else:
            for candidate in ready:
                if requested_role is None or candidate.role == requested_role:
                    selected = candidate
                    break
            if selected is None:
                raise PolicyViolation(
                    f"NO_RUNNABLE_ACTION: no ready action matches requested role {requested_role!r}"
                )
        action = self.runtime.store.decode_action(
            campaign_id,
            selected.action_id,
        )
        campaign = self.runtime.store.decode_campaign(campaign_id)
        campaign_row = self.runtime.store.get_campaign(campaign_id)
        lease = self.runtime.leases.issue(
            campaign_id=campaign_id,
            action_id=selected.action_id,
            agent_id=agent_id,
            ttl_seconds=ttl_seconds,
            metadata={
                "adapter_session_id": session_id,
                "adapter_id": session["adapter_id"],
                "adapter_type": session["adapter_type"],
            },
        )
        role_config = self.runtime.role_policy["roles"][action["role"]]
        capabilities = sorted(set(role_config.get("capabilities", [])))
        dependency_artifacts = self._dependency_artifacts(
            campaign_id=campaign_id,
            action=action,
        )
        lease_payload = {
            "lease_id": lease.lease_id,
            "agent_id": lease.agent_id,
            "capability_id": lease.capability_id,
            "base_sha": lease.base_sha,
            "expires_at": lease.expires_at,
        }
        contract = render_agent_contract(
            campaign=campaign,
            graph_id=campaign_row["graph_id"],
            action=action,
            lease=lease_payload,
            capabilities=capabilities,
            globally_forbidden=self.runtime.role_policy.get(
                "globally_forbidden_capabilities",
                [],
            ),
            dependency_artifacts=dependency_artifacts,
        )
        self.runtime.receipts.append(
            campaign_id=campaign_id,
            graph_id=campaign_row["graph_id"],
            event_type="agent_deployed",
            actor=session["adapter_id"],
            action_id=selected.action_id,
            lease_id=lease.lease_id,
            event={
                "session_id": session_id,
                "agent_id": agent_id,
                "role": action["role"],
                "adapter_type": session["adapter_type"],
            },
        )
        return {
            "deployment": {
                "session_id": session_id,
                "adapter_id": session["adapter_id"],
                "adapter_type": session["adapter_type"],
                "agent_id": agent_id,
                "action_id": selected.action_id,
            },
            "lease": lease_payload,
            "required_acknowledgment": {
                "capabilities": capabilities,
            },
            "agent_contract": contract,
        }

    def acknowledge_agent(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        accepted_capabilities: list[str],
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        expected_session = lease.metadata.get("adapter_session_id")
        if expected_session != session_id:
            raise PolicyViolation(
                "ADAPTER_SESSION_MISMATCH: lease was issued through a different adapter session"
            )
        role_capabilities = set(
            self.runtime.role_policy["roles"][lease.role].get("capabilities", [])
        )
        accepted = set(accepted_capabilities)
        if accepted != role_capabilities:
            missing = sorted(role_capabilities - accepted)
            extra = sorted(accepted - role_capabilities)
            raise PolicyViolation(
                "CAPABILITY_ACK_MISMATCH: agent must acknowledge the "
                f"exact role capability set; missing={missing}, extra={extra}"
            )
        self.runtime.leases.acknowledge(
            lease_id=lease_id,
            agent_id=agent_id,
            accepted_capabilities=sorted(accepted),
        )
        return {
            "acknowledged": True,
            "lease_id": lease_id,
            "agent_id": agent_id,
            "capabilities": sorted(accepted),
        }

    def authorize_tool(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        capability: str,
        resource: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        decision = self.runtime.gateway.authorize(
            lease_id=lease_id,
            agent_id=agent_id,
            capability=capability,
            resource=resource,
            metadata={
                "adapter_session_id": session_id,
                **dict(metadata or {}),
            },
        )
        return {
            "allowed": decision.allowed,
            "code": decision.code,
            "message": decision.message,
            "lease_id": decision.lease_id,
            "capability": decision.capability,
            "resource": decision.resource,
        }

    def heartbeat(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        base_sha: str,
        status: str,
        progress: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        self.runtime.leases.heartbeat(
            lease_id=lease_id,
            agent_id=agent_id,
            observed_base_sha=base_sha,
            status=status,
            progress=progress,
        )
        return {
            "accepted": True,
            "lease_id": lease_id,
            "status": status,
        }

    def submit_artifact(
        self,
        *,
        session_id: str,
        lease_id: str,
        agent_id: str,
        artifact: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.require_conformant_session(session_id)
        lease = self.runtime.leases.get(lease_id)
        if lease.metadata.get("adapter_session_id") != session_id:
            raise PolicyViolation("ADAPTER_SESSION_MISMATCH")
        artifact_id = self.runtime.artifacts.submit(
            lease_id=lease_id,
            agent_id=agent_id,
            artifact=artifact,
        )
        self.runtime.scheduler.refresh_readiness(lease.campaign_id)
        return {
            "accepted": True,
            "artifact_id": artifact_id,
            "campaign_status": self.runtime.status(lease.campaign_id),
        }

    def status(
        self,
        *,
        session_id: str,
        campaign_id: str,
    ) -> dict[str, Any]:
        session = self.require_conformant_session(session_id)
        status = self.runtime.status(campaign_id)
        status["adapter"] = {
            "session_id": session_id,
            "adapter_id": session["adapter_id"],
            "adapter_type": session["adapter_type"],
            "conformance": session["status"],
        }
        errors = self.runtime.verify_receipts(campaign_id)
        status["receipt_chain"] = {
            "valid": not errors,
            "errors": errors,
        }
        return status

    def _dependency_artifacts(
        self,
        *,
        campaign_id: str,
        action: Mapping[str, Any],
    ) -> list[str]:
        result: list[str] = []
        for dependency_id in action.get("depends_on", []):
            row = self.runtime.store.get_action(campaign_id, dependency_id)
            artifact_id = row["result_artifact_id"]
            if artifact_id:
                result.append(artifact_id)
        return sorted(result)

    def _load_requirements(self) -> dict[str, Any]:
        path = self.repository_root / "autonomy/policies/adapter-requirements.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _initialize_extension_tables(self) -> None:
        with self.runtime.store.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS adapter_sessions (
                    session_id TEXT PRIMARY KEY,
                    adapter_id TEXT NOT NULL,
                    adapter_type TEXT NOT NULL,
                    protocol_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    conformance_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS
                    idx_adapter_sessions_adapter
                    ON adapter_sessions(adapter_id, created_at);
                """
            )
