from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from peer_execution.bindings import resolve_peer_binding
from peer_execution.digests import digest_object
from peer_execution.models import CapabilityReceipt

READINESS_SCHEMA = "l9.executable-peer-readiness.v3"


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def _registry_entry(subsystem_root: Path, provider_ref: str) -> dict[str, Any] | None:
    registry = _load_yaml(subsystem_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    return next(
        (item for item in registry.get("adapters") or [] if item.get("adapter_id") == provider_ref),
        None,
    )


def _profile_exists(subsystem_root: Path, profile_ref: str) -> bool:
    registry = _load_yaml(subsystem_root / "registry/EXECUTION_PROFILE_REGISTRY.yaml")
    return isinstance((registry.get("profiles") or {}).get(profile_ref), dict)


def _autonomy_facts(subsystem_root: Path, repo_root: Path, autonomy_provider_ref: str) -> dict[str, Any]:
    provider_path = subsystem_root / "integrations/autonomy-control-plane/PROVIDER.yaml"
    compat_path = subsystem_root / "COMPATIBILITY.yaml"
    provider = _load_yaml(provider_path) if provider_path.is_file() else {}
    compat = _load_yaml(compat_path) if compat_path.is_file() else {}
    canonical_path = provider.get("canonical_path")
    compat_path_value = ((compat.get("providers") or {}).get("root_autonomy") or {}).get("path")
    gateway = bool(canonical_path) and (repo_root / str(canonical_path)).is_dir()
    provider_ok = (
        provider.get("owns_program_state") is False
        and provider.get("provider_id") == autonomy_provider_ref
    )
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
    provider_ref: str,
    execution_profile_ref: str,
    *,
    provider_probe: Mapping[str, Any] | None = None,
    now: dt.datetime | None = None,
    ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Build one canonical binding-level readiness receipt.

    The full peer/surface/provider/profile tuple is resolved against
    PEER_RUNTIME_BINDINGS before any provider or autonomy checks proceed.
    """
    subsystem_root = Path(subsystem_root).resolve()
    repo_root = Path(repo_root).resolve()
    if ttl_seconds <= 0:
        raise ValueError("readiness ttl_seconds must be positive")
    observed = (now or dt.datetime.now(dt.UTC)).replace(microsecond=0)

    try:
        binding = resolve_peer_binding(
            repo_root,
            agent_id,
            surface,
            provider_ref,
            execution_profile_ref,
        )
        binding_ok = True
        binding_error = None
    except (OSError, ValueError, TypeError) as exc:
        binding = None
        binding_ok = False
        binding_error = str(exc)

    entry = _registry_entry(subsystem_root, provider_ref)
    descriptor: dict[str, Any] = {}
    descriptor_digest: str | None = None
    if entry is not None:
        descriptor_path = subsystem_root / str(entry["descriptor"])
        if descriptor_path.is_file():
            descriptor = _load_yaml(descriptor_path)
            descriptor_digest = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()

    autonomy = _autonomy_facts(
        subsystem_root,
        repo_root,
        binding.autonomy_provider_ref if binding is not None else "<invalid-binding>",
    )
    provider_identity = descriptor.get("identity") or {}
    provider_conformance_ok = (
        bool(descriptor)
        and descriptor.get("contract_family") == "program-execution-system.v2"
        and provider_identity.get("binding") == "peer_runtime_binding"
        and "agent_ref" not in provider_identity
    )
    profile_ok = _profile_exists(subsystem_root, execution_profile_ref)
    routable = (
        entry is not None
        and entry.get("status") not in {"dormant", "non_routable"}
        and entry.get("adapter_kind") in {"worker_host", "verifier"}
    )

    probe_value = dict(provider_probe or {})
    probe_status = str(probe_value.get("status") or "UNKNOWN")
    probe_integrity_ok = False
    if probe_value.get("receipt_digest") is not None:
        try:
            receipt = CapabilityReceipt.from_dict(probe_value)
        except (KeyError, TypeError, ValueError):
            pass
        else:
            probe_integrity_ok = receipt.adapter_id == provider_ref
            if probe_status == "PASS":
                probe_integrity_ok = probe_integrity_ok and receipt.is_fresh(observed)
    elif probe_status != "PASS":
        probe_integrity_ok = True
    if probe_status == "PASS" and not probe_integrity_ok:
        probe_status = "FAIL"

    checks = {
        "canonical_binding": "PASS" if binding_ok else "FAIL",
        "provider_conformance": "PASS" if provider_conformance_ok else "FAIL",
        "execution_profile": "PASS" if profile_ok else "FAIL",
        "provider_routable": "PASS" if routable else "FAIL",
        "provider_probe": "PASS" if probe_status == "PASS" else probe_status,
        "provider_probe_integrity": "PASS" if probe_integrity_ok else "FAIL",
        "autonomy_provider": "PASS" if autonomy["provider_ok"] else "FAIL",
        "autonomy_conformance": "PASS" if autonomy["conformance_ok"] else "FAIL",
        "execution_gateway": "PASS" if autonomy["gateway_enforced"] else "FAIL",
    }
    blocked_reason = next((name for name, value in checks.items() if value != "PASS"), None)
    status = "READY" if blocked_reason is None else "BLOCKED"
    expires = observed + dt.timedelta(seconds=ttl_seconds)
    body: dict[str, Any] = {
        "schema": READINESS_SCHEMA,
        "agent_id": agent_id,
        "surface": surface,
        "provider_ref": provider_ref,
        "execution_profile_ref": execution_profile_ref,
        "binding": {
            "status": "PASS" if binding_ok else "FAIL",
            "error": binding_error,
            "autonomy_provider_ref": (
                binding.autonomy_provider_ref if binding is not None else None
            ),
        },
        "program_execution": {
            "status": (
                "PASS"
                if binding_ok
                and provider_conformance_ok
                and profile_ok
                and routable
                and probe_status == "PASS"
                and probe_integrity_ok
                else "FAIL"
            ),
            "contract_family": descriptor.get("contract_family"),
            "descriptor_digest": descriptor_digest,
            "provider_probe": {
                "status": probe_status,
                "blocked_reason": probe_value.get("blocked_reason"),
                "capabilities": list(probe_value.get("capabilities") or []),
                "receipt_digest": probe_value.get("receipt_digest"),
            },
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
