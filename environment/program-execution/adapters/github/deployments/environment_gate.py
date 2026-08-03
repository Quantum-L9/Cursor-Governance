from __future__ import annotations

from typing import Any


def read_environment(transport, repository: str, environment: str) -> dict[str, Any]:
    return transport.api(f"repos/{repository}/environments/{environment}")
