from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from autonomy.models import (
    CampaignAuthorization,
    DeploymentManifest,
)
from autonomy.policy_loader import load_policy
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
    ) -> AutonomyRuntime:
        root = Path(repository_root)
        return cls(
            database_path=(database_path or root / ".l9/autonomy/runtime.sqlite3"),
            role_policy=load_policy("role-capabilities"),
            pipeline_policy=load_policy("pipeline-invariants"),
            resource_policy=load_policy("resource-classes"),
            operation_aliases=load_policy("operation-aliases"),
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
            raise ValueError("Compiled graph campaign ID does not match campaign")
        if deployment.graph_id not in {
            "AUTO",
            graph_payload["graph_id"],
        }:
            raise ValueError("Deployment graph ID does not match compiled graph")
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
