from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

import yaml
from adapters.common.digests import digest_object
from adapters.common.imports import load_module

READINESS_SCHEMA = "l9.executable-peer-readiness.v1"


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def _agent_ref_for(subsystem_root: Path, adapter_id: str) -> str | None:
    binding = load_module(
        subsystem_root / "integrations/agent-identity/identity_binding.py",
        "pes_peer_readiness_identity_binding",
    )
    return binding.agent_ref_for(subsystem_root, adapter_id)


def _registry_entry(subsystem_root: Path, adapter_id: str) -> dict[str, Any] | None:
    registry = _load_yaml(subsystem_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    return next(
        (item for item in registry.get("adapters") or [] if item.get("adapter_id") == adapter_id),
        None,
    )


def _autonomy_facts(subsystem_root: Path, repo_root: Path) -> dict[str, Any]:
    provider_path = subsystem_root / "integrations/autonomy-control-plane/PROVIDER.yaml"
    compat_path = subsystem_root / "COMPATIBILITY.yaml"
    provider = _load_yaml(provider_path) if provider_path.is_file() else {}
    compat = _load_yaml(compat_path) if compat_path.is_file() else {}
    canonical_path = provider.get("canonical_path")
    compat_path_value = ((compat.get("providers") or {}).get("root_autonomy") or {}).get("path")
    gateway = bool(canonical_path) and (repo_root / str(canonical_path)).is_dir()
    provider_ok = provider.get("owns_program_state") is False and bool(provider.get("provider_id"))
    conformance_ok = bool(canonical_path) and canonical_path == compat_path_value
    return {
        "provider_id": provider.get("provider_id"),
        "protocol_version": provider.get("protocol_version"),
        "canonical_path": canonical_path,
        "gateway_enforced": gateway,
        "provider_ok": provider_ok,
        "conformance_ok": conformance_ok,
    }


def build_readiness(
    subsystem_root: str | Path,
    repo_root: str | Path,
    agent_id: str,
    surface: str,
    adapter_id: str,
    *,
    now: dt.datetime | None = None,
    ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Build a deterministic executable-peer readiness receipt for one binding.

    All checks are structural (registry + descriptor + provider) so the receipt
    is reproducible and CI-testable; a live host probe can tighten adapter_probe
    later. Readiness is per (agent_id, surface, adapter_id) binding.
    """
    subsystem_root = Path(subsystem_root).resolve()
    repo_root = Path(repo_root).resolve()

    agents = _load_yaml(repo_root / "environment/agents/agent_registry.yaml").get("agents") or {}
    agent = agents.get(agent_id) or {}
    principal_id = agent.get("principal_id")

    entry = _registry_entry(subsystem_root, adapter_id)
    descriptor: dict[str, Any] = {}
    descriptor_digest: str | None = None
    if entry is not None:
        descriptor_path = subsystem_root / str(entry["descriptor"])
        if descriptor_path.is_file():
            descriptor = _load_yaml(descriptor_path)
            descriptor_digest = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()

    resolved_ref = _agent_ref_for(subsystem_root, adapter_id)
    autonomy = _autonomy_facts(subsystem_root, repo_root)

    identity_ok = resolved_ref == agent_id and bool(principal_id)
    adapter_conformance_ok = bool(descriptor) and descriptor.get("contract_family") == (
        "program-execution-system.v2"
    )
    routable = (
        entry is not None
        and entry.get("status") not in {"dormant", "non_routable"}
        and entry.get("adapter_kind") == "worker_host"
    )

    checks = {
        "identity_binding": "PASS" if identity_ok else "FAIL",
        "adapter_conformance": "PASS" if adapter_conformance_ok else "FAIL",
        "adapter_probe": "PASS" if routable else "FAIL",
        "autonomy_provider": "PASS" if autonomy["provider_ok"] else "FAIL",
        "autonomy_conformance": "PASS" if autonomy["conformance_ok"] else "FAIL",
        "execution_gateway": "PASS" if autonomy["gateway_enforced"] else "FAIL",
    }
    blocked_reason = next((name for name, value in checks.items() if value != "PASS"), None)
    status = "READY" if blocked_reason is None else "BLOCKED"

    observed = (now or dt.datetime.now(dt.UTC)).replace(microsecond=0)
    expires = observed + dt.timedelta(seconds=ttl_seconds)

    body: dict[str, Any] = {
        "schema": READINESS_SCHEMA,
        "agent_id": agent_id,
        "surface": surface,
        "adapter_id": adapter_id,
        "identity": {
            "status": "PASS" if identity_ok else "FAIL",
            "principal_id": principal_id,
        },
        "program_execution": {
            "status": "PASS" if adapter_conformance_ok else "FAIL",
            "contract_family": descriptor.get("contract_family"),
            "descriptor_digest": descriptor_digest,
        },
        "autonomy": {
            "status": "PASS" if autonomy["provider_ok"] else "FAIL",
            "provider_id": autonomy["provider_id"],
            "protocol_version": autonomy["protocol_version"],
            "canonical_path": autonomy["canonical_path"],
            "gateway_enforced": autonomy["gateway_enforced"],
        },
        "checks": checks,
        "observed_at": observed.isoformat(),
        "expires_at": expires.isoformat(),
        "status": status,
        "blocked_reason": blocked_reason,
    }
    body["receipt_digest"] = digest_object(body)
    return body
