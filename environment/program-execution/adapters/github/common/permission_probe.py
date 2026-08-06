from __future__ import annotations

from typing import Any


def repository_permissions(transport, repository: str) -> dict[str, Any]:
    value = transport.api(f"repos/{repository}")
    permissions = value.get("permissions") if isinstance(value, dict) else None
    if not isinstance(permissions, dict):
        return {
            "status": "BLOCKED",
            "reason": "repository permissions were not returned",
            "permissions": {},
        }
    return {
        "status": "PASS",
        "reason": None,
        "permissions": {
            key: bool(permissions.get(key))
            for key in ("admin", "maintain", "push", "triage", "pull")
        },
    }
