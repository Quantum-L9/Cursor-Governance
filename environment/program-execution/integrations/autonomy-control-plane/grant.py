"""Grant PE task mutation through the root autonomy control plane.

Program Execution remains the controller. This module binds one rendered
Program contract to one subordinate root-autonomy campaign, completes the
synthesis action that represents the already-rendered contract, then issues
and acknowledges an executor lease that authorizes local write and commit.
Push, pull request, and merge stay forbidden.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_PE_ROOT = _HERE.parents[1]
_GOV_ROOT = _PE_ROOT.parents[1]
for _path in (_HERE, _PE_ROOT, _GOV_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from bridge import AutonomyControlPlaneBridge  # noqa: E402
from contract_mapper import map_program_contract  # noqa: E402

from autonomy.compiler.graph_compiler import compile_graph  # noqa: E402
from autonomy.models import CampaignAuthorization, DeploymentManifest  # noqa: E402
from autonomy.runtime.engine import AutonomyRuntime  # noqa: E402

SYNTHESIS_CAPABILITIES = [
    "repository.read",
    "artifact.read_recon_report",
    "artifact.write_execution_brief",
    "graphiti.read",
]
EXECUTOR_WRITE_CAPABILITIES = [
    "repository.read",
    "repository.write_scoped",
    "test.run",
    "git.diff",
    "artifact.write_execution_result",
]
COMMIT_CAPABILITIES = ["git.commit_local"]
RECON_CAPABILITIES = [
    "repository.read",
    "repository.search",
    "graphiti.read",
    "artifact.write_recon_report",
]
WRITE_AUTHORIZATIONS = ("repository.write_scoped",)
COMMIT_AUTHORIZATIONS = ("git.commit_local",)
INSPECT_AUTHORIZATIONS = ("repository.read",)


def _executor_authority(contract: Mapping[str, Any]) -> tuple[list[str], tuple[str, ...]]:
    """Capabilities to acknowledge and authorize, from the requested actions.

    Defense in depth against an upstream contract that should never exist: a
    contract requesting local_write without commit never receives
    `git.commit_local`, so the capability is absent from the lease as well as
    from the campaign's allowed operations. commit is never inferred from
    local_write, and neither is inferred from a "mutation" boolean.
    """
    requested = {str(item) for item in (contract.get("requested_actions") or [])}
    capabilities = list(EXECUTOR_WRITE_CAPABILITIES)
    authorize = WRITE_AUTHORIZATIONS
    if "commit" in requested:
        capabilities = capabilities + COMMIT_CAPABILITIES
        authorize = authorize + COMMIT_AUTHORIZATIONS
    return capabilities, authorize


class AutonomyGrantError(RuntimeError):
    """Root autonomy refused to grant the requested local authority."""


def grant_task_mutation(
    repository_root: str | Path,
    workspace: str | Path,
    contract: Mapping[str, Any],
    *,
    attempt_number: int = 1,
    adapter_id: str = "cursor-foreground",
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    pec = Path(workspace).resolve()
    bridge = AutonomyControlPlaneBridge(root)
    probe = bridge.probe()
    if probe.get("status") != "PASS":
        missing = ", ".join(probe.get("missing") or [])
        raise AutonomyGrantError(f"root autonomy control plane is BLOCKED; missing={missing}")
    mapped = map_program_contract(
        contract,
        adapter_id=adapter_id,
        attempt_number=attempt_number,
    )
    campaign_payload = mapped["campaign"]
    deployment_payload = mapped["deployment"]
    campaign = CampaignAuthorization.from_dict(campaign_payload)
    deployment = DeploymentManifest.from_dict(deployment_payload)
    compiled = compile_graph(campaign, deployment, mapped["graph"])
    graph_payload = compiled.to_dict()
    database = pec / ".l9" / "autonomy" / "runtime.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=database,
    )
    runtime.bootstrap(
        campaign_payload=campaign_payload,
        deployment_payload=deployment_payload,
        graph_payload=graph_payload,
    )
    runtime.scheduler.refresh_readiness(campaign.campaign_id)
    ids = mapped["ids"]
    if mapped["mutation"]:
        _complete_if_ready(
            runtime,
            campaign_id=campaign.campaign_id,
            graph_id=graph_payload["graph_id"],
            action_id=ids["synthesis_id"],
            agent_id=f"{ids['agent_id']}-synthesis",
            role_capabilities=SYNTHESIS_CAPABILITIES,
            artifact_kind="ExecutionBrief",
            payload={
                "objective": campaign.objective,
                "base_sha": campaign.base_state["commit_sha"],
                "contract_digest": str(
                    contract.get("contract_digest") or contract.get("source_contract_digest") or ""
                ),
            },
            base_sha=str(campaign.base_state["commit_sha"]),
        )
        runtime.scheduler.refresh_readiness(campaign.campaign_id)
        work_action = ids["action_id"]
        work_agent = ids["agent_id"]
        work_capabilities, authorize = _executor_authority(contract)
    else:
        work_action = ids["action_id"]
        work_agent = ids["agent_id"]
        work_capabilities = RECON_CAPABILITIES
        authorize = INSPECT_AUTHORIZATIONS
    lease = _issue_or_reuse(
        runtime,
        campaign_id=campaign.campaign_id,
        action_id=work_action,
        agent_id=work_agent,
        capabilities=work_capabilities,
    )
    authorized: list[str] = []
    for capability in authorize:
        decision = runtime.gateway.authorize(
            lease_id=lease["lease_id"],
            agent_id=work_agent,
            capability=capability,
            resource=_resource_for_capability(contract, capability),
        )
        if not decision.allowed:
            raise AutonomyGrantError(f"{decision.code}: {decision.message} capability={capability}")
        authorized.append(capability)
    # Receipts are task/attempt-scoped: one mutable workspace-global
    # autonomy-grant.json pair would let two concurrent PE tasks overwrite
    # each other's authority evidence.
    task_id = str(contract.get("task_id") or contract.get("id") or "task")
    packet_path = grant_receipt_path(pec, task_id, attempt_number, kind="packet")
    grant_path = grant_receipt_path(pec, task_id, attempt_number, kind="grant")
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(campaign_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    grant = {
        "schema": "l9.program-execution.autonomy-grant.v2",
        "provider": "root-autonomy-control-plane",
        "owns_program_state": False,
        "task_id": task_id,
        "attempt_number": int(attempt_number),
        "campaign_id": campaign.campaign_id,
        "graph_id": graph_payload["graph_id"],
        "action_id": work_action,
        "agent_id": work_agent,
        "lease_id": lease["lease_id"],
        "capability_id": lease["capability_id"],
        "base_sha": str(campaign.base_state["commit_sha"]),
        "mutation": bool(mapped["mutation"]),
        "authorized": authorized,
        "forbidden": list(campaign.scope.get("forbidden_operations") or []),
        "packet": str(packet_path),
        "runtime_database": str(database),
        "program_lease_id": contract.get("lease_id"),
    }
    grant_path.write_text(json.dumps(grant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return grant


def grant_receipt_path(
    workspace: str | Path,
    task_id: str,
    attempt_number: int,
    *,
    kind: str = "grant",
) -> Path:
    """Task/attempt-scoped receipt location; never a workspace-global file."""
    if kind not in {"grant", "packet"}:
        msg = f"unknown grant receipt kind: {kind}"
        raise ValueError(msg)
    safe_task = _slugify_receipt(task_id)
    return (
        Path(workspace).resolve()
        / "runtime"
        / "autonomy-grants"
        / f"{safe_task}.attempt-{int(attempt_number):03d}.{kind}.json"
    )


def _slugify_receipt(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return cleaned or "task"


def revoke_task_grant(
    grant: Mapping[str, Any],
    *,
    reason: str,
    actor: str = "program-controller",
) -> dict[str, Any]:
    """Revoke a previously issued root-Autonomy lease for a failed task.

    Revocation releases every resource claim the lease held; a failed child
    must never retain live mutation authority. Idempotent: a lease that is
    already terminal stays terminal.
    """
    database = Path(str(grant.get("runtime_database") or ""))
    lease_id = str(grant.get("lease_id") or "")
    if not lease_id or not database.is_file():
        return {
            "revoked": False,
            "reason": "grant carries no live runtime binding",
            "lease_id": lease_id or None,
        }
    runtime = AutonomyRuntime.from_repository(
        repository_root=Path.cwd(),
        database_path=database,
    )
    runtime.leases.revoke(lease_id=lease_id, reason=reason, actor=actor)
    return {"revoked": True, "lease_id": lease_id, "reason": reason}


def _first_writable(contract: Mapping[str, Any]) -> str | None:
    for path in contract.get("writable_paths") or []:
        if str(path).strip():
            return str(path)
    return None


def _resource_for_capability(contract: Mapping[str, Any], capability: str) -> str | None:
    if not capability.startswith(("repository.", "file.", "git.diff")):
        return None
    return _first_writable(contract) or "README.md"


def _action_status(runtime: AutonomyRuntime, campaign_id: str, action_id: str) -> str:
    return str(runtime.store.get_action(campaign_id, action_id)["status"])


def _complete_if_ready(
    runtime: AutonomyRuntime,
    *,
    campaign_id: str,
    graph_id: str,
    action_id: str,
    agent_id: str,
    role_capabilities: list[str],
    artifact_kind: str,
    payload: Mapping[str, Any],
    base_sha: str,
) -> None:
    status = _action_status(runtime, campaign_id, action_id)
    if status == "COMPLETED":
        return
    lease = runtime.leases.issue(
        campaign_id=campaign_id,
        action_id=action_id,
        agent_id=agent_id,
    )
    runtime.leases.acknowledge(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        accepted_capabilities=list(role_capabilities),
    )
    runtime.artifacts.submit(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        artifact={
            "artifact_id": f"artifact-{uuid.uuid4().hex}",
            "kind": artifact_kind,
            "campaign_id": campaign_id,
            "graph_id": graph_id,
            "action_id": action_id,
            "lease_id": lease.lease_id,
            "producer_agent_id": agent_id,
            "base_sha": base_sha,
            "input_artifacts": [],
            "payload": dict(payload),
        },
    )


def _issue_or_reuse(
    runtime: AutonomyRuntime,
    *,
    campaign_id: str,
    action_id: str,
    agent_id: str,
    capabilities: list[str],
) -> dict[str, Any]:
    row = runtime.store.get_action(campaign_id, action_id)
    status = str(row["status"])
    if status in {"LEASED", "RUNNING"} and row["active_lease_id"]:
        lease = runtime.leases.get(str(row["active_lease_id"]))
        return {
            "lease_id": lease.lease_id,
            "capability_id": lease.capability_id,
            "agent_id": lease.agent_id,
        }
    if status != "READY":
        runtime.scheduler.refresh_readiness(campaign_id)
        status = _action_status(runtime, campaign_id, action_id)
    if status != "READY":
        raise AutonomyGrantError(
            f"executor action {action_id!r} is {status}; synthesis must complete first"
        )
    lease = runtime.leases.issue(
        campaign_id=campaign_id,
        action_id=action_id,
        agent_id=agent_id,
    )
    runtime.leases.acknowledge(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        accepted_capabilities=list(capabilities),
    )
    return {
        "lease_id": lease.lease_id,
        "capability_id": lease.capability_id,
        "agent_id": lease.agent_id,
    }
