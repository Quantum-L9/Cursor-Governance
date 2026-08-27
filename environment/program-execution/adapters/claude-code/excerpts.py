from __future__ import annotations

import re

_EXCERPT_LIMIT = 2000
_REDACTED = "<redacted>"
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 " + _REDACTED),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), _REDACTED),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), _REDACTED),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), _REDACTED),
    (
        re.compile(
            r"(?i)\b([A-Za-z0-9_]*"
            r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|CREDENTIAL)"
            r"[A-Za-z0-9_]*)[\"']?\s*[:=]\s*[\"']?[^\s\"',;&]+"
        ),
        r"\1=" + _REDACTED,
    ),
)


def redacted_excerpt(text: str | None, *, limit: int = _EXCERPT_LIMIT) -> str | None:
    if not isinstance(text, str) or not text:
        return None
    sanitized = text
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    sanitized = sanitized.strip()
    if not sanitized:
        return None
    return sanitized[-limit:]
