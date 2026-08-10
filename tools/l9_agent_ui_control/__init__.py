"""L9 Agent UI Control — local-first Mac control plane for Cursor."""

__all__ = [
    "AgentConfig",
    "AutomationExecutor",
    "EventType",
    "MacAgentClient",
    "TaskExecutor",
]


def __getattr__(name: str):
    # Lazy exports — avoid importing executor (optional heavy deps) at package import.
    if name == "AutomationExecutor":
        from .executor import AutomationExecutor

        return AutomationExecutor
    if name in ("AgentConfig", "EventType", "MacAgentClient", "TaskExecutor"):
        from . import websocket_client as wc

        return getattr(wc, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
