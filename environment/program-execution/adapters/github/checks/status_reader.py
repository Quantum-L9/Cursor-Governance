from __future__ import annotations

from typing import Any


def read_combined_status(transport, repository: str, sha: str) -> dict[str, Any]:
    return transport.api(f"repos/{repository}/commits/{sha}/status")
