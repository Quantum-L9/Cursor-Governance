from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class AgentRegistryReader:
    def __init__(self, repository_root: str | Path) -> None:
        self.path = Path(repository_root).resolve() / "environment/agents/agent_registry.yaml"

    def load(self) -> dict[str, Any]:
        value = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("agents"), dict):
            raise ValueError("agent registry is malformed")
        return value

    def active(self, agent_id: str) -> dict[str, Any] | None:
        agents = self.load()["agents"]
        value = agents.get(agent_id)
        if not isinstance(value, dict) or value.get("status") != "active":
            return None
        return dict(value)
