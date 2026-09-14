from __future__ import annotations

from typing import Any


def bind_identity(reader: object, agent_ref: str | None = None) -> dict[str, Any]:
    """Bind execution to peer identity supplied by PEER_RUNTIME_BINDINGS.

    Provider descriptors are identity-neutral. The caller must pass the peer's
    canonical agent_ref from the topology SSOT. None is reserved for
    controller-contract or external-receipt integrations.
    """
    if not hasattr(reader, "active"):
        raise TypeError("reader must provide active(agent_id)")
    if agent_ref is None:
        return {"binding": "controller_contract", "agent_id": None}
    value = reader.active(agent_ref)
    if value is None:
        raise ValueError(f"active agent identity not found: {agent_ref}")
    return {
        "binding": "peer_runtime_binding",
        "agent_id": value["agent_id"],
        "principal_id": value["principal_id"],
        "source": value["source"],
    }
