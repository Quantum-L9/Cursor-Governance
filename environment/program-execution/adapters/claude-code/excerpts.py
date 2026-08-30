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
        re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
        _REDACTED,
    ),
    (
        re.compile(
            r"(?i)\b([A-Za-z0-9_]*"
            r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|CREDENTIAL)"
            r"[A-Za-z0-9_]*)[\"']?\s*[:=]\s*[\"']?[^\s\"',;&]+"
        ),
        r"\1=" + _REDACTED,
    ),
)


_ALLOWLIST_LINE = re.compile(
    r"(?i)("
    r"^(error|warning|fatal|fail)[:\s]"
    r"|permission denied"
    r"|max(?:imum)? (?:number of )?turns"
    r"|exit[_ ]?code"
    r"|unauthorized|forbidden|not allowed"
    r"|timed? ?out"
    r")"
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


def allowlisted_excerpt(text: str | None, *, limit: int = _EXCERPT_LIMIT) -> str | None:
    """Keep only shape-validated diagnostic lines, then redact secrets.

    Arbitrary CLI/JSON dumps are dropped. Digests stay on the caller.
    """
    if not isinstance(text, str) or not text:
        return None
    kept = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[:1] in "{[":
            continue
        if _ALLOWLIST_LINE.search(line):
            kept.append(line)
    if not kept:
        return None
    return redacted_excerpt("\n".join(kept), limit=limit)
