"""Cursor-owned session contracts: the ContinuationCapsuleV2.

Cursor owns this schema because it describes Cursor session continuation.
Memory owns admission, canonical storage, record identity, temporal state,
authorization, supersession, receipts, and projection. The capsule crosses
the boundary as a governed candidate (``session_continuation`` class,
``namespace_local`` visibility, lossless ``structured_payload``) and comes
back as record metadata that :meth:`ContinuationCapsuleV2.from_payload`
re-validates.

Continuation data is *evidence*. Current filesystem and git state win: a
capsule whose ``repository_state_digest`` no longer matches the checkout is
stale, and :meth:`ContinuationCapsuleV2.is_stale_for` says so.

INV-03 note: no provider name, URL, or tool appears here on purpose.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

CONTINUATION_SCHEMA = "cursor.continuation/v2"
PRODUCER = "Cursor-Governance"
CANDIDATE_SCHEMA_VERSION = "1.1.0"
CANDIDATE_KIND = "MemoryCandidate"
CANDIDATE_CLASS = "session_continuation"

_REQUIRED = (
    "schema",
    "session_id",
    "repository_identity",
    "task_signature",
    "objective",
    "next_action",
    "repository_state_digest",
    "producer",
    "producer_version",
    "created_at",
)


class ContinuationContractError(ValueError):
    """The payload is not a valid ContinuationCapsuleV2."""


def canonical_json(payload: Any) -> str:
    """Deterministic serialization used for digests and candidate bodies."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def task_signature_for(objective: str, repository_identity: str) -> str:
    """Stable task identity from the objective and repository, never the session."""

    return sha256_text(f"{repository_identity}\n{objective.strip()}")[:32]


@dataclass(frozen=True)
class ContinuationCapsuleV2:
    session_id: str
    repository_identity: str
    objective: str
    next_action: str
    repository_state_digest: str
    producer_version: str
    task_signature: str = ""
    active_files: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    unfinished_work: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    producer: str = PRODUCER
    schema: str = CONTINUATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CONTINUATION_SCHEMA:
            raise ContinuationContractError(f"unsupported continuation schema: {self.schema!r}")
        for name in ("session_id", "repository_identity", "objective", "next_action"):
            if not str(getattr(self, name)).strip():
                raise ContinuationContractError(f"{name} must be non-empty")
        if not self.task_signature:
            object.__setattr__(
                self,
                "task_signature",
                task_signature_for(self.objective, self.repository_identity),
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("active_files", "blockers", "decisions", "unfinished_work"):
            payload[key] = list(payload[key])
        return payload

    def canonical(self) -> str:
        return canonical_json(self.to_payload())

    def digest(self) -> str:
        return sha256_text(self.canonical())

    @classmethod
    def from_payload(cls, payload: Any) -> ContinuationCapsuleV2:
        if not isinstance(payload, dict):
            raise ContinuationContractError("continuation payload must be an object")
        missing = [key for key in _REQUIRED if key not in payload]
        if missing:
            raise ContinuationContractError(f"continuation payload missing: {', '.join(missing)}")
        if payload.get("schema") != CONTINUATION_SCHEMA:
            raise ContinuationContractError(
                f"unsupported continuation schema: {payload.get('schema')!r}"
            )

        def _strings(key: str) -> tuple[str, ...]:
            value = payload.get(key) or ()
            if not isinstance(value, (list, tuple)):
                raise ContinuationContractError(f"{key} must be a list")
            return tuple(str(item) for item in value)

        return cls(
            session_id=str(payload["session_id"]),
            repository_identity=str(payload["repository_identity"]),
            objective=str(payload["objective"]),
            next_action=str(payload["next_action"]),
            repository_state_digest=str(payload["repository_state_digest"]),
            producer_version=str(payload["producer_version"]),
            task_signature=str(payload["task_signature"]),
            active_files=_strings("active_files"),
            blockers=_strings("blockers"),
            decisions=_strings("decisions"),
            unfinished_work=_strings("unfinished_work"),
            created_at=str(payload["created_at"]),
            producer=str(payload["producer"]),
            schema=str(payload["schema"]),
        )

    # ------------------------------------------------------------------
    # Repository-state precedence
    # ------------------------------------------------------------------
    def is_stale_for(self, current_repository_state_digest: str) -> bool:
        """True when the checkout has moved on since this capsule was written."""

        return self.repository_state_digest != current_repository_state_digest

    # ------------------------------------------------------------------
    # Boundary crossing
    # ------------------------------------------------------------------
    def candidate_id(self) -> str:
        """Stable operation identity: producer, repo, session, kind, payload digest."""

        return (
            f"cursor-continuation:{self.repository_identity}:{self.session_id}:{self.digest()[:16]}"
        )

    def to_governed_candidate(
        self,
        *,
        namespace: str,
        source_sha: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """The memory-owned governed-candidate envelope carrying this capsule.

        ``namespace`` is a *request*: MemoryService authorizes the principal
        against it (INV-07). ``source_sha`` binds freshness to the checkout.
        """

        if not namespace.strip():
            raise ContinuationContractError("namespace request must be non-empty")
        if not source_sha.strip():
            raise ContinuationContractError("source_sha must be non-empty")
        return {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "kind": CANDIDATE_KIND,
            "candidate_id": self.candidate_id(),
            "source": {
                "repository": self.repository_identity,
                "sha": source_sha,
                "visibility": "namespace_local",
                "namespace": namespace,
            },
            "knowledge": {
                "primary_class": CANDIDATE_CLASS,
                "statement": f"{self.objective} | next: {self.next_action}",
                "confidence": 1.0,
                "invalidation_conditions": [
                    {
                        "condition_type": "repository_state_changed",
                        "selector": self.repository_state_digest,
                    }
                ],
                "payload_schema": CONTINUATION_SCHEMA,
                "structured_payload": self.to_payload(),
            },
            "governance": {
                "authority_class": "advisory",
                "route": "memory",
                "promotion_decision": "promote",
                "may_override_repository_state": False,
                "may_override_canonical_authority": False,
            },
            "provenance": {"producer": self.producer, "source_agent_id": agent_id},
        }


def continuation_from_record_metadata(metadata: dict[str, Any]) -> ContinuationCapsuleV2 | None:
    """Recover a capsule from a canonical record's metadata, or ``None``.

    Returns ``None`` when the record is not a continuation record; raises
    :class:`ContinuationContractError` when it claims to be one but is malformed.
    """

    if metadata.get("payload_schema") != CONTINUATION_SCHEMA:
        return None
    return ContinuationCapsuleV2.from_payload(metadata.get("structured_payload"))


__all__ = [
    "CANDIDATE_CLASS",
    "CONTINUATION_SCHEMA",
    "PRODUCER",
    "ContinuationCapsuleV2",
    "ContinuationContractError",
    "canonical_json",
    "continuation_from_record_metadata",
    "sha256_text",
    "task_signature_for",
]
