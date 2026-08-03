from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.imports import load_module


def _reader_type():
    module = load_module(
        Path(__file__).with_name("registry_reader.py"),
        "pes_agent_registry_reader",
    )
    return module.AgentRegistryReader


def bind_identity(reader: object, adapter_id: str) -> dict[str, Any]:
    if not hasattr(reader, "active"):
        raise TypeError("reader must provide active(agent_id)")
    mapping = {
        "cursor-foreground": "cursor",
        "cursor-background": "cursor",
        "claude-code-direct": "claude-code",
        "claude-code-bounded-autonomy": "claude-code",
    }
    agent_id = mapping.get(adapter_id)
    if agent_id is None:
        return {"binding": "controller_contract", "agent_id": None}
    value = reader.active(agent_id)
    if value is None:
        raise ValueError(f"active agent identity not found: {agent_id}")
    return {
        "binding": "agent_registry",
        "agent_id": value["agent_id"],
        "principal_id": value["principal_id"],
        "source": value["source"],
    }
