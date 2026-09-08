"""PII redaction for transcript excerpts before they leave the session.

Moved out of the retired provider episode contract at realignment stage C11.
The patterns are deliberately conservative: an over-redacted excerpt costs
recall, an under-redacted one costs a person their privacy.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("memory.redaction")

_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)"),
        "[PHONE_REDACTED]",
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b"),
        "[SSN_REDACTED]",
    ),
    (
        "secret",
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        "[SECRET_REDACTED]",
    ),
]


def redact_pii(text: str, enabled: bool = True) -> str:
    if not enabled or not text:
        return text
    cleaned = text
    for pii_type, pattern, replacement in _PII_PATTERNS:
        matches = pattern.findall(cleaned)
        if matches:
            log.info("PII redacted: %d %s pattern(s)", len(matches), pii_type)
            cleaned = pattern.sub(replacement, cleaned)
    return cleaned


__all__ = ["redact_pii"]
