from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _reader_type():
    from adapters.common.imports import load_module

    module = load_module(
        Path(__file__).with_name("registry_reader.py"),
        "pes_agent_registry_reader",
    )
    return module.AgentRegistryReader


def agent_ref_for(subsystem_root: str | Path, adapter_id: str) -> str | None:
    """Resolve a Program adapter's identity.agent_ref foreign key.

    Reads the execution adapter registry to find the adapter's descriptor, then
    returns descriptor.identity.agent_ref. Returns None when the adapter does
    not bind to the agent registry (controller_contract / external_receipt), so
    the caller falls back to controller-contract identity.
    """
    root = Path(subsystem_root).resolve()
    registry = yaml.safe_load(
        (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
    )
    entry = next(
        (item for item in registry.get("adapters") or [] if item.get("adapter_id") == adapter_id),
        None,
    )
    if entry is None:
        return None
    descriptor = yaml.safe_load((root / str(entry["descriptor"])).read_text(encoding="utf-8"))
    identity = descriptor.get("identity") or {}
    if identity.get("binding") != "agent_registry":
        return None
    return identity.get("agent_ref")


def bind_identity(reader: object, adapter_id: str, agent_ref: str | None = None) -> dict[str, Any]:
    """Bind a Program adapter to its agent identity via the agent_ref foreign key.

    The hardcoded adapter->agent map is gone: callers pass the descriptor's
    identity.agent_ref (resolve it with agent_ref_for). When agent_ref is None
    the adapter is not agent-registry bound and controller-contract identity is
    returned, preserving the ChatGPT manual-handoff / CI / GitHub behavior.
    """
    if not hasattr(reader, "active"):
        raise TypeError("reader must provide active(agent_id)")
    if agent_ref is None:
        return {"binding": "controller_contract", "agent_id": None}
    value = reader.active(agent_ref)
    if value is None:
        raise ValueError(f"active agent identity not found: {agent_ref}")
    return {
        "binding": "agent_registry",
        "agent_id": value["agent_id"],
        "principal_id": value["principal_id"],
        "source": value["source"],
    }
