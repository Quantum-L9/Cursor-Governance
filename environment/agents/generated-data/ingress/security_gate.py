from __future__ import annotations

import re
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
]


def preflight(packet: dict[str, Any]) -> dict[str, Any]:
    """Run BEFORE durable ordinary persistence. Never echo secrets."""
    blob = str(packet)
    findings = []
    for pat in _SECRET_PATTERNS:
        if pat.search(blob):
            findings.append(pat.pattern[:32])
    size = len(blob.encode())
    if size > 2_000_000:
        return {
            "safe": False,
            "classification": "TOO_LARGE",
            "finding_types": ["size"],
            "size": size,
        }
    if findings:
        return {
            "safe": False,
            "classification": "SENSITIVE",
            "finding_types": ["secret_pattern"],
            "size": size,
        }
    return {"safe": True, "classification": "CLEAN", "finding_types": [], "size": size}
