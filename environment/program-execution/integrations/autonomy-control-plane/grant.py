"""Grant PE task mutation through the root autonomy control plane.

Program Execution remains the controller. This module binds one rendered
Program contract to one subordinate root-autonomy campaign, completes the
synthesis action that represents the already-rendered contract, then issues
and acknowledges an executor lease that authorizes local write and commit.
Push, pull request, and merge stay forbidden.

The executor lease is bound to two things the campaign alone cannot supply:

* a *conformant adapter session*, registered from the canonical `PeerBinding`
  plus the current `autonomy/policies/adapter-requirements.json` policy, so the
  live `AdapterOrchestrator` can authorize each individual effect against it;
* the *live Program parent*, read read-only from canonical PEC state, so the
  subordinate lease carries the parent's identity and can never outlive it.

The acknowledgment path stays exactly as narrow as it was.
`_executor_authority(contract)` intersects the task's `requested_actions`, and
that intersection — not the executor role's full capability set — is what the
lease accepts. `AdapterOrchestrator.request_agent()` is deliberately *not* used
for this lease: it derives its acknowledgment set from the role policy, and
`acknowledge_agent()` requires that exact role set, which would hand a
`local_write`-only task `git.commit_local` (DG-001).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_PE_ROOT = _HERE.parents[1]
_GOV_ROOT = _PE_ROOT.parents[1]
for _path in (_HERE, _PE_ROOT, _GOV_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from bridge import AutonomyControlPlaneBridge  # noqa: E402
from contract_mapper import (  # noqa: E402
    ContractActionError,
    map_program_contract,
    require_coherent_actions,
)
from peer_execution.bindings import (  # noqa: E402
    PeerBinding,
    load_peer_bindings,
    resolve_peer_binding,
)
from program_authority import (  # noqa: E402
    AUTHORIZATION_PHASE_EFFECT,
    AUTHORIZATION_PHASE_GRANT_PROBE,
    ProgramAuthorityError,
    ProgramAuthorityVerifier,
    ProgramParent,
)

from autonomy.adapters.orchestrator import AdapterOrchestrator  # noqa: E402
from autonomy.adapters.protocol import ADAPTER_PROTOCOL_VERSION  # noqa: E402
from autonomy.compiler.graph_compiler import compile_graph  # noqa: E402
from autonomy.models import CampaignAuthorization, DeploymentManifest  # noqa: E402
from autonomy.policy_loader import load_policy  # noqa: E402
from autonomy.runtime.engine import AutonomyRuntime  # noqa: E402

AUTONOMY_AUTHORITY_SCHEMA = "l9.program-execution.autonomy-authority.v1"

SYNTHESIS_CAPABILITIES = [
    "repository.read",
    "artifact.read_recon_report",
    "artifact.write_execution_brief",
    "graphiti.read",
]
# What an executor holds regardless of what it may change. None of these
# mutate the repository, so none of them depend on a mutating action.
EXECUTOR_BASE_CAPABILITIES = [
    "repository.read",
    "test.run",
    "git.diff",
    "artifact.write_execution_result",
]
WRITE_CAPABILITIES = ["repository.write_scoped"]
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

# `AUTHORIZATION_PHASE_GRANT_PROBE` / `AUTHORIZATION_PHASE_EFFECT` are imported
# from `program_authority`, which owns the phase vocabulary, and re-exported
# here because this module is the query surface campaign reconciliation reads.


def _executor_authority(contract: Mapping[str, Any]) -> tuple[list[str], tuple[str, ...]]:
    """Capabilities to acknowledge and authorize, from the requested actions.

    Each capability traces to the single action that justifies it:
    `repository.write_scoped` to `local_write`, `git.commit_local` to `commit`.
    Neither is inferred from the other, and neither is inferred from a
    "mutation" boolean. So local_write without commit never receives
    `git.commit_local`, and commit without local_write is refused outright
    rather than quietly handed the write capability it did not request.

    This is the authority owner, so it re-derives the invariant itself instead
    of trusting the caller to have already enforced it.
    """
    requested = require_coherent_actions(contract)
    capabilities = list(EXECUTOR_BASE_CAPABILITIES)
    authorize: tuple[str, ...] = ()
    if "local_write" in requested:
        capabilities = capabilities + WRITE_CAPABILITIES
        authorize = authorize + WRITE_AUTHORIZATIONS
    if "commit" in requested:
        capabilities = capabilities + COMMIT_CAPABILITIES
        authorize = authorize + COMMIT_AUTHORIZATIONS
    return capabilities, authorize


class AutonomyGrantError(RuntimeError):
    """Root autonomy refused to grant the requested local authority."""


def resolve_identity(
    repository_root: str | Path,
    *,
    agent_ref: str | None,
    surface: str | None,
    provider_ref: str | None,
    execution_profile_ref: str | None,
    adapter_id: str | None,
) -> PeerBinding:
    """The full canonical peer identity for this grant, or fail closed.

    A caller that already knows its live identity passes it. A caller that only
    knows a provider id (the historical surface-only argument) is resolved
    through the same topology SSOT, and only when that lookup is unique — the
    bridge never guesses which peer a provider belongs to.
    """
    root = Path(repository_root).resolve()
    if agent_ref and surface:
        return resolve_peer_binding(root, agent_ref, surface, provider_ref, execution_profile_ref)
    probe = (provider_ref or adapter_id or "").strip()
    if not probe:
        raise AutonomyGrantError(
            "AUTONOMY_IDENTITY_UNRESOLVED: peer agent_ref/surface or a provider_ref is required"
        )
    document = load_peer_bindings(root)
    candidates: list[tuple[str, str, str]] = []
    for peer_key, peer in (document.get("peers") or {}).items():
        if not isinstance(peer, Mapping):
            continue
        for binding in (peer.get("execution") or {}).get("bindings") or []:
            if not isinstance(binding, Mapping):
                continue
            if str(binding.get("provider_ref")) != probe:
                continue
            candidates.append(
                (
                    str(peer.get("agent_ref") or peer_key),
                    str(binding.get("surface")),
                    str(binding.get("execution_profile_ref")),
                )
            )
    if len(candidates) != 1:
        raise AutonomyGrantError(
            "AUTONOMY_IDENTITY_UNRESOLVED: provider "
            f"{probe!r} does not resolve to exactly one canonical peer binding "
            f"(candidates={sorted(candidates)})"
        )
    resolved_agent, resolved_surface, resolved_profile = candidates[0]
    return resolve_peer_binding(root, resolved_agent, resolved_surface, probe, resolved_profile)


def _mandatory_policy_value(requirements: Mapping[str, Any], field_name: str) -> Any:
    mandatory = requirements.get("mandatory") or {}
    if not isinstance(mandatory, Mapping) or field_name not in mandatory:
        raise AutonomyGrantError(
            "ADAPTER_POLICY_INCOMPLETE: adapter-requirements does not declare "
            f"mandatory {field_name!r}"
        )
    return mandatory[field_name]


def _surface_supports_background(repository_root: Path, agent_ref: str) -> bool:
    """Background-agent capability as the topology SSOT declares it."""
    peer = (load_peer_bindings(repository_root).get("peers") or {}).get(agent_ref)
    if not isinstance(peer, Mapping):
        return False
    subagents = peer.get("subagents")
    return bool(isinstance(subagents, Mapping) and subagents.get("enabled") is True)


def adapter_config_payload(
    repository_root: str | Path,
    binding: PeerBinding,
    *,
    database_path: str | Path,
    requirements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Current-policy adapter configuration for one canonical peer binding.

    Every mandatory field comes from the live policy file rather than a literal
    here, so a policy tightening is picked up without editing this bridge. The
    two optional surface capabilities are declared from the topology SSOT, never
    asserted optimistically.
    """
    root = Path(repository_root).resolve()
    policy = dict(requirements if requirements is not None else load_policy("adapter-requirements"))
    payload: dict[str, Any] = {
        "adapter_id": binding.provider_ref,
        "adapter_type": binding.agent_ref,
        "peer_ref": binding.agent_ref,
        "surface": binding.surface,
        "provider_ref": binding.provider_ref,
        "execution_profile_ref": binding.execution_profile_ref,
        "protocol_version": str(policy.get("protocol_version") or ADAPTER_PROTOCOL_VERSION),
        "supports_background_agents": _surface_supports_background(root, binding.agent_ref),
        "supports_independent_review": False,
        "metadata": {
            "database_path": str(database_path),
            "autonomy_provider_ref": binding.autonomy_provider_ref,
            "program_bound": True,
        },
    }
    for field_name in (
        "tool_mediation_mode",
        "direct_tool_access",
        "autonomous_merge",
        "supports_agent_identity",
        "supports_lease_propagation",
        "supports_heartbeat",
        "supports_typed_artifacts",
        "supports_human_gate",
    ):
        payload[field_name] = _mandatory_policy_value(policy, field_name)
    return payload


def register_adapter_session(
    orchestrator: AdapterOrchestrator,
    config_payload: Mapping[str, Any],
) -> str:
    """Register a conformant live adapter session or fail closed."""
    registration = orchestrator.register(dict(config_payload))
    report = registration.get("conformance") or {}
    if report.get("status") != "PASS":
        failures = [
            f"{check.get('check_id')}: {check.get('message')}"
            for check in report.get("checks") or []
            if check.get("blocking") and not check.get("passed")
        ]
        raise AutonomyGrantError(
            "ADAPTER_CONFORMANCE_FAILED: root autonomy refused a non-conformant "
            f"adapter session; failures={failures}"
        )
    return str(registration["session_id"])


def authority_digest(authority: Mapping[str, Any]) -> str:
    """Stable correlation digest over the authority sidecar's own fields."""
    payload = {key: value for key, value in authority.items() if key != "authority_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def grant_task_mutation(
    repository_root: str | Path,
    workspace: str | Path,
    contract: Mapping[str, Any],
    *,
    attempt_number: int = 1,
    adapter_id: str = "cursor-foreground",
    agent_ref: str | None = None,
    surface: str | None = None,
    provider_ref: str | None = None,
    execution_profile_ref: str | None = None,
) -> dict[str, Any]:
    # Refuse an incoherent action set before the runtime is touched at all --
    # before bootstrap, before graph compile, before any lease is issued or
    # acknowledged. Nothing downstream should have to undo a bad grant.
    try:
        require_coherent_actions(contract)
    except ContractActionError as exc:
        raise AutonomyGrantError(str(exc)) from exc
    root = Path(repository_root).resolve()
    pec = Path(workspace).resolve()
    bridge = AutonomyControlPlaneBridge(root)
    probe = bridge.probe()
    if probe.get("status") != "PASS":
        missing = ", ".join(probe.get("missing") or [])
        raise AutonomyGrantError(f"root autonomy control plane is BLOCKED; missing={missing}")
    try:
        binding = resolve_identity(
            root,
            agent_ref=agent_ref,
            surface=surface,
            provider_ref=provider_ref,
            execution_profile_ref=execution_profile_ref,
            adapter_id=adapter_id,
        )
    except (OSError, ValueError) as exc:
        raise AutonomyGrantError(f"AUTONOMY_IDENTITY_UNRESOLVED: {exc}") from exc
    # The canonical Program parent is read read-only before any root authority
    # exists: a subordinate lease is only ever issued beneath a live parent.
    verifier = ProgramAuthorityVerifier(pec)
    try:
        parent = verifier.require_live_parent(contract)
    except ProgramAuthorityError as exc:
        raise AutonomyGrantError(str(exc)) from exc
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
    orchestrator = AdapterOrchestrator(runtime, repository_root=root)
    session_id = register_adapter_session(
        orchestrator,
        adapter_config_payload(root, binding, database_path=database),
    )
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
    task_id = str(contract.get("task_id") or contract.get("id") or "task")
    try:
        ttl_seconds = verifier.subordinate_ttl_seconds(
            parent,
            default_ttl_seconds=runtime.leases.default_ttl_seconds,
        )
    except ProgramAuthorityError as exc:
        raise AutonomyGrantError(str(exc)) from exc
    lease = _issue_or_reuse(
        runtime,
        campaign_id=campaign.campaign_id,
        action_id=work_action,
        agent_id=work_agent,
        capabilities=work_capabilities,
        ttl_seconds=ttl_seconds,
        metadata=_lease_metadata(
            session_id=session_id,
            binding=binding,
            parent=parent,
            workspace=pec,
            task_id=task_id,
            attempt_number=attempt_number,
        ),
    )
    # A reused lease keeps the adapter session it was issued under: authorizing
    # against a session the lease was not bound to is exactly the mismatch
    # `authorize_tool` exists to refuse.
    effective_session = str(lease.get("adapter_session_id") or session_id)
    authorized: list[str] = []
    for capability in authorize:
        decision = orchestrator.authorize_tool(
            session_id=effective_session,
            lease_id=lease["lease_id"],
            agent_id=work_agent,
            capability=capability,
            resource=_resource_for_capability(contract, capability),
            metadata={
                "program_task_id": task_id,
                "program_lease_id": parent.lease_id,
                "authorization_phase": AUTHORIZATION_PHASE_GRANT_PROBE,
            },
        )
        if not decision.get("allowed"):
            raise AutonomyGrantError(
                f"{decision.get('code')}: {decision.get('message')} capability={capability}"
            )
        authorized.append(capability)
    # Receipts are task/attempt-scoped: one mutable workspace-global
    # autonomy-grant.json pair would let two concurrent PE tasks overwrite
    # each other's authority evidence.
    packet_path = grant_receipt_path(pec, task_id, attempt_number, kind="packet")
    grant_path = grant_receipt_path(pec, task_id, attempt_number, kind="grant")
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(campaign_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    authority = {
        "schema": AUTONOMY_AUTHORITY_SCHEMA,
        "owns_program_state": False,
        "task_id": task_id,
        "attempt_number": int(attempt_number),
        "adapter_session_id": effective_session,
        "campaign_id": campaign.campaign_id,
        "graph_id": graph_payload["graph_id"],
        "action_id": work_action,
        "agent_id": work_agent,
        "lease_id": lease["lease_id"],
        "capability_id": lease["capability_id"],
        "expires_at": lease.get("expires_at"),
        "base_sha": str(campaign.base_state["commit_sha"]),
        "capabilities": sorted(set(work_capabilities)),
        "authorized": list(authorized),
        "repository_root": str(root),
        "runtime_database": str(database),
        "workspace": str(pec),
        "peer_binding": binding.to_dict(),
        "program_parent": parent.to_dict(),
    }
    authority["authority_digest"] = authority_digest(authority)
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
        "adapter_session_id": effective_session,
        "expires_at": lease.get("expires_at"),
        "base_sha": str(campaign.base_state["commit_sha"]),
        "mutation": bool(mapped["mutation"]),
        "authorized": authorized,
        "forbidden": list(campaign.scope.get("forbidden_operations") or []),
        "packet": str(packet_path),
        "runtime_database": str(database),
        "program_lease_id": contract.get("lease_id"),
        "program_parent": parent.to_dict(),
        "peer_binding": binding.to_dict(),
        "autonomy_authority": authority,
    }
    grant_path.write_text(json.dumps(grant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return grant


def _lease_metadata(
    *,
    session_id: str,
    binding: PeerBinding,
    parent: ProgramParent,
    workspace: Path,
    task_id: str,
    attempt_number: int,
) -> dict[str, Any]:
    """Identity the live orchestrator and the Program parent both check."""
    return {
        "adapter_session_id": session_id,
        "adapter_id": binding.provider_ref,
        "adapter_type": binding.agent_ref,
        "peer_ref": binding.agent_ref,
        "surface": binding.surface,
        "execution_profile_ref": binding.execution_profile_ref,
        "owns_program_state": False,
        "program_workspace": str(workspace),
        "program_task_id": task_id,
        "program_attempt_number": int(attempt_number),
        "program_lease_id": parent.lease_id,
        "program_base_sha": parent.base_sha,
        "program_branch": parent.branch,
        "program_worktree": parent.worktree,
        "program_contract_digest": parent.contract_digest,
        "program_parent_expires_at": parent.expires_at,
        "program_parent_bound": parent.bound,
    }


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
    ttl_seconds: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = runtime.store.get_action(campaign_id, action_id)
    status = str(row["status"])
    if status in {"LEASED", "RUNNING"} and row["active_lease_id"]:
        lease = runtime.leases.get(str(row["active_lease_id"]))
        return {
            "lease_id": lease.lease_id,
            "capability_id": lease.capability_id,
            "agent_id": lease.agent_id,
            "expires_at": lease.expires_at,
            "adapter_session_id": lease.metadata.get("adapter_session_id"),
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
        ttl_seconds=ttl_seconds,
        metadata=dict(metadata or {}),
    )
    # Acknowledge the action-specific intersection, never the role-wide set:
    # the accepted capability list is what the gateway checks per effect.
    runtime.leases.acknowledge(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        accepted_capabilities=list(capabilities),
    )
    return {
        "lease_id": lease.lease_id,
        "capability_id": lease.capability_id,
        "agent_id": lease.agent_id,
        "expires_at": lease.expires_at,
        "adapter_session_id": dict(metadata or {}).get("adapter_session_id"),
    }


# ---------------------------------------------------------------------------
# Subordinate lifecycle
#
# A grant that is only ever issued is half a lifecycle. These helpers close it:
# what the root gateway actually authorized (decision coverage), the terminal
# ExecutionResult that releases the lease and its claims on success, and the
# invalidation path for when the Controller — the only Program-state authority —
# later rejects the attempt the root evidence supported.
# ---------------------------------------------------------------------------


def _runtime_for(grant: Mapping[str, Any]) -> AutonomyRuntime:
    database = Path(str(grant.get("runtime_database") or ""))
    if not database.is_file():
        raise AutonomyGrantError("grant carries no live runtime binding")
    root = str(grant.get("repository_root") or _GOV_ROOT)
    return AutonomyRuntime.from_repository(repository_root=root, database_path=database)


def _decision_phase(row: Mapping[str, Any]) -> str | None:
    """The `authorization_phase` a decision was recorded under, if any.

    Decisions written before the phase annotation existed carry no phase. They
    are reported as `None` rather than defaulted to either phase: guessing
    `effect` would resurrect exactly the coverage hole this distinction closes,
    and guessing `grant_probe` would misattribute a real mediated write.
    """
    raw = row.get("metadata_json")
    if not raw:
        return None
    try:
        metadata = json.loads(str(raw))
    except (TypeError, ValueError):
        return None
    if not isinstance(metadata, Mapping):
        return None
    phase = metadata.get("authorization_phase")
    return str(phase) if isinstance(phase, str) and phase.strip() else None


def lease_decisions(
    grant: Mapping[str, Any],
    *,
    capability: str | None = None,
    allowed_only: bool = True,
    phase: str | None = None,
) -> list[dict[str, Any]]:
    """Every gateway decision recorded under this grant's subordinate lease.

    `phase` narrows the result to one `authorization_phase` (see the constants
    above). The filter is applied in Python rather than SQL because the phase
    lives inside the decision's `metadata_json` blob, which is the gateway's
    own column and is not this bridge's to reshape.
    """
    lease_id = str(grant.get("lease_id") or "")
    if not lease_id:
        return []
    runtime = _runtime_for(grant)
    query = (
        "SELECT capability, resource, allowed, code, created_at, metadata_json "
        "FROM tool_decisions WHERE lease_id = ?"
    )
    parameters: list[Any] = [lease_id]
    if capability is not None:
        query += " AND capability = ?"
        parameters.append(capability)
    if allowed_only:
        query += " AND allowed = 1"
    with runtime.store.connect() as connection:
        rows = [dict(row) for row in connection.execute(query, tuple(parameters))]
    for row in rows:
        row["authorization_phase"] = _decision_phase(row)
    if phase is None:
        return rows
    return [row for row in rows if row["authorization_phase"] == phase]


def authorized_resources(
    grant: Mapping[str, Any],
    *,
    capability: str = "repository.write_scoped",
    phase: str | None = None,
) -> set[str]:
    """Resources this lease was actually allowed to write, as decided.

    Unfiltered by default, because "what did this lease ever hold?" is a
    different question from "what authorized this write?". Coverage asks the
    second one and passes `phase`.
    """
    return {
        str(row["resource"])
        for row in lease_decisions(grant, capability=capability, phase=phase)
        if row.get("resource")
    }


def unmediated_changed_paths(
    grant: Mapping[str, Any],
    changed_paths: Iterable[str],
    *,
    capability: str = "repository.write_scoped",
    phase: str = AUTHORIZATION_PHASE_EFFECT,
) -> list[str]:
    """Changed paths with no pre-effect root authorization under this lease.

    This is the coverage question the whole bridge exists to answer: an effect
    that reached the filesystem without a `tool_authorized` decision was not
    mediated, whatever the provider reports about it.

    Only an `effect`-phase decision answers it. The probe this module takes
    while issuing the grant is a real allowed decision on the task's first
    writable path, so before the phase distinction existed a provider could
    write that path directly, with no hook in the loop at all, and coverage
    would still report full mediation.
    """
    if not phase:
        # `phase=None` on this function would mean "count any decision", which
        # is precisely the hole below. Coverage names a phase or it fails.
        raise AutonomyGrantError(
            "COVERAGE_PHASE_REQUIRED: mediation coverage must name an authorization phase"
        )
    authorized = authorized_resources(grant, capability=capability, phase=phase)
    missing: list[str] = []
    for path in changed_paths:
        normalized = str(path).replace("\\", "/").strip()
        if not normalized:
            continue
        if normalized not in authorized:
            missing.append(normalized)
    return sorted(set(missing))


def _dependency_artifacts(runtime: AutonomyRuntime, grant: Mapping[str, Any]) -> list[str]:
    campaign_id = str(grant.get("campaign_id") or "")
    action_id = str(grant.get("action_id") or "")
    row = runtime.store.get_action(campaign_id, action_id)
    action = json.loads(row["action_json"])
    inputs: list[str] = []
    for dependency_id in action.get("depends_on", []):
        dependency = runtime.store.get_action(campaign_id, dependency_id)
        artifact_id = dependency["result_artifact_id"]
        if artifact_id:
            inputs.append(str(artifact_id))
    return sorted(inputs)


def submit_task_result(
    grant: Mapping[str, Any],
    *,
    changed_files: Iterable[str],
    candidate_sha: str | None,
    contract_digest: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Terminalize the subordinate lease with a typed root ExecutionResult.

    Root autonomy does not decide whether the Program task succeeded — the
    Controller verifies that independently. This records what the subordinate
    executor actually produced so its lease and resource claims are released
    instead of staying live after the work is done.
    """
    runtime = _runtime_for(grant)
    lease_id = str(grant["lease_id"])
    agent_id = str(grant["agent_id"])
    lease = runtime.leases.get(lease_id)
    if lease.status.value != "ACTIVE":
        return {
            "submitted": False,
            "reason": f"subordinate lease is already {lease.status.value}",
            "lease_id": lease_id,
        }
    artifact_id = f"artifact-{uuid.uuid4().hex}"
    runtime.artifacts.submit(
        lease_id=lease_id,
        agent_id=agent_id,
        artifact={
            "artifact_id": artifact_id,
            "kind": "ExecutionResult",
            "campaign_id": str(grant["campaign_id"]),
            "graph_id": str(grant["graph_id"]),
            "action_id": str(grant["action_id"]),
            "lease_id": lease_id,
            "producer_agent_id": agent_id,
            "base_sha": str(grant["base_sha"]),
            "input_artifacts": _dependency_artifacts(runtime, grant),
            "payload": {
                "candidate_sha": candidate_sha,
                "changed_files": sorted({str(item) for item in changed_files}),
                "contract_digest": contract_digest,
                "owns_program_state": False,
                "evidence": dict(evidence or {}),
            },
        },
    )
    terminal = runtime.leases.get(lease_id)
    return {
        "submitted": True,
        "artifact_id": artifact_id,
        "lease_id": lease_id,
        "lease_status": terminal.status.value,
    }


def invalidate_task_support(
    grant: Mapping[str, Any],
    *,
    artifact_id: str,
    reason: str,
    actor: str = "program-controller",
) -> dict[str, Any]:
    """Withdraw root support after the Controller rejected the attempt.

    The Controller owns the verdict. What root autonomy owns is its own
    evidence, and evidence for an attempt that did not verify must not stand.
    """
    runtime = _runtime_for(grant)
    try:
        runtime.artifacts.invalidate(artifact_id=artifact_id, reason=reason, actor=actor)
    except KeyError:
        return {"invalidated": False, "reason": "unknown artifact", "artifact_id": artifact_id}
    return {"invalidated": True, "artifact_id": artifact_id, "reason": reason}


def release_task_grant(
    grant: Mapping[str, Any],
    *,
    reason: str = "ACTION_COMPLETED",
    actor: str = "program-controller",
) -> dict[str, Any]:
    """Release a still-active subordinate lease and its resource claims."""
    lease_id = str(grant.get("lease_id") or "")
    if not lease_id:
        return {"released": False, "reason": "grant carries no lease"}
    runtime = _runtime_for(grant)
    runtime.leases.release(lease_id=lease_id, actor=actor, reason=reason)
    return {"released": True, "lease_id": lease_id, "reason": reason}
