from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from adapters.common.imports import load_module
from peer_execution.bindings import resolve_peer_binding

CONTEXT_SCHEMA = "l9.executable-peer-context.v2"


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def build_context(
    subsystem_root: str | Path,
    repo_root: str | Path,
    agent_id: str,
    surface: str,
    adapter_id: str | None = None,
    execution_profile_ref: str | None = None,
) -> dict[str, Any]:
    """Render normalized executable-peer context from one canonical binding."""
    subsystem_root = Path(subsystem_root).resolve()
    repo_root = Path(repo_root).resolve()
    binding = resolve_peer_binding(
        repo_root,
        agent_id,
        surface,
        adapter_id,
        execution_profile_ref,
    )

    agents = _load_yaml(repo_root / "environment/agents/agent_registry.yaml").get("agents") or {}
    agent = agents.get(agent_id) or {}
    registry = _load_yaml(subsystem_root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    entry = next(
        (
            item
            for item in registry.get("adapters") or []
            if item.get("adapter_id") == binding.provider_ref
        ),
        None,
    )
    descriptor: dict[str, Any] = {}
    if entry is not None:
        descriptor = _load_yaml(subsystem_root / str(entry["descriptor"]))

    provider = _load_yaml(subsystem_root / "integrations/autonomy-control-plane/PROVIDER.yaml")
    readiness_module = load_module(
        subsystem_root / "integrations/bootstrap/peer_readiness.py",
        "pes_peer_context_readiness",
    )
    readiness = readiness_module.build_readiness(
        subsystem_root,
        repo_root,
        binding.agent_ref,
        binding.surface,
        binding.provider_ref,
        binding.execution_profile_ref,
    )

    return {
        "schema": CONTEXT_SCHEMA,
        "agent": {
            "agent_id": binding.agent_ref,
            "role": agent.get("role"),
            "surface": binding.surface,
        },
        "program_execution": {
            "adapter_id": binding.provider_ref,
            "execution_profile_ref": binding.execution_profile_ref,
            "contract_family": descriptor.get("contract_family"),
        },
        "autonomy": {
            "provider_id": binding.autonomy_provider_ref,
            "canonical": (
                provider.get("provider_id") == binding.autonomy_provider_ref
                and provider.get("owns_program_state") is False
            ),
        },
        "readiness": {
            "status": readiness["status"],
            "receipt_digest": readiness["receipt_digest"],
        },
    }
