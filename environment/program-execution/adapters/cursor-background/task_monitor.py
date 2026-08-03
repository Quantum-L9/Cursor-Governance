from __future__ import annotations


def normalize_status(value: str) -> str:
    mapping = {
        "queued": "RUNNING",
        "running": "RUNNING",
        "completed": "PASS",
        "failed": "FAIL",
        "cancelled": "CANCELLED",
    }
    return mapping.get(value.lower(), "BLOCKED")
