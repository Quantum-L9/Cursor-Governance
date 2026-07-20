"""Graphiti episode contract and PII filter — adapted from graphiti 2/episode_contract.py."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

log = logging.getLogger("graphiti.contract")

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

MAX_BODY_CHARS = 32_000
MAX_NAME_CHARS = 200
MAX_DESCRIPTION_CHARS = 500
VALID_SOURCES = {"text", "json", "message"}
FORBIDDEN_GROUPS = {"main", "default", "", "test"}


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


class EpisodeContract(BaseModel):
    name: str = Field(..., min_length=3, max_length=MAX_NAME_CHARS)
    episode_body: str = Field(..., min_length=1, max_length=MAX_BODY_CHARS)
    source: Literal["text", "json", "message"]
    source_description: str = Field(..., max_length=MAX_DESCRIPTION_CHARS)
    reference_time: datetime
    group_id: str = Field(..., min_length=3, max_length=100)
    kind: str | None = Field(None, description="lesson|pickup|manifest|gmp|session")
    pii_redaction: bool = True

    @field_validator("reference_time")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @field_validator("reference_time")
    @classmethod
    def reject_future_dates(cls, value: datetime) -> datetime:
        now = datetime.now(UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if value > now + timedelta(hours=1):
            raise ValueError(f"reference_time {value.isoformat()} is in the future")
        return value

    @field_validator("group_id")
    @classmethod
    def validate_group_id(cls, value: str) -> str:
        if value in FORBIDDEN_GROUPS:
            raise ValueError(f"group_id '{value}' is forbidden in production")
        return value

    @model_validator(mode="after")
    def apply_pii_redaction(self) -> EpisodeContract:
        if self.pii_redaction:
            object.__setattr__(self, "episode_body", redact_pii(self.episode_body))
        return self

    def to_mcp_payload(self) -> dict:
        return {
            "name": self.name,
            "episode_body": self.episode_body,
            "source": self.source,
            "source_description": self.source_description,
            "reference_time": self.reference_time.isoformat(),
            "group_id": self.group_id,
        }
