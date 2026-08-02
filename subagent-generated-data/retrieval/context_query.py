from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class ContextRetrievalError(RuntimeError):
    """Raised when context retrieval is unavailable or invalid."""


@dataclass(frozen=True)
class ContextBudget:
    max_items: int = 12
    max_characters: int = 12_000

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.max_characters <= 0:
            raise ValueError("max_characters must be positive")


@dataclass(frozen=True)
class ContextQuery:
    repository: str
    repository_class: str
    campaign_id: str
    action_id: str
    agent_id: str
    role: str
    task_type: str
    paths: tuple[str, ...]
    base_sha: str
    visibility_ceiling: str
    budget: ContextBudget
    minimum_confidence: float = 0.70
    include_contested: bool = False
    include_raw_evidence: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be within [0, 1]")
        if not self.repository.strip():
            raise ValueError("repository is required")
        if not self.role.strip():
            raise ValueError("role is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "repository": self.repository,
            "repository_class": self.repository_class,
            "campaign_id": self.campaign_id,
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "task_type": self.task_type,
            "paths": list(self.paths),
            "base_sha": self.base_sha,
            "visibility_ceiling": self.visibility_ceiling,
            "max_items": self.budget.max_items,
            "max_characters": self.budget.max_characters,
            "minimum_confidence": self.minimum_confidence,
            "include_contested": self.include_contested,
            "include_raw_evidence": self.include_raw_evidence,
        }


@dataclass(frozen=True)
class ContextCandidate:
    record_id: str
    text: str
    score: float
    confidence: float
    state: str
    authority_class: str
    visibility: str
    repository: str
    source_sha: str | None
    paths: tuple[str, ...]
    task_types: tuple[str, ...]
    roles: tuple[str, ...]
    epistemic_status: str
    invalidated: bool
    successful_reuse_count: int = 0
    failed_reuse_count: int = 0
    metadata: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> ContextCandidate:
        return cls(
            record_id=str(value["record_id"]),
            text=str(value.get("text", value.get("statement", ""))),
            score=float(value.get("score", 0)),
            confidence=float(value.get("confidence", 0)),
            state=str(value.get("state", "unknown")),
            authority_class=str(value.get("authority_class", "advisory")),
            visibility=str(value.get("visibility", "repository_local")),
            repository=str(value.get("repository", "")),
            source_sha=(str(value["source_sha"]) if value.get("source_sha") is not None else None),
            paths=tuple(str(item) for item in value.get("paths", [])),
            task_types=tuple(str(item) for item in value.get("task_types", [])),
            roles=tuple(str(item) for item in value.get("roles", [])),
            epistemic_status=str(value.get("epistemic_status", "observed")),
            invalidated=bool(value.get("invalidated", False)),
            successful_reuse_count=int(value.get("successful_reuse_count", 0)),
            failed_reuse_count=int(value.get("failed_reuse_count", 0)),
            metadata=dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "text": self.text,
            "score": self.score,
            "confidence": self.confidence,
            "state": self.state,
            "authority_class": self.authority_class,
            "visibility": self.visibility,
            "repository": self.repository,
            "source_sha": self.source_sha,
            "paths": list(self.paths),
            "task_types": list(self.task_types),
            "roles": list(self.roles),
            "epistemic_status": self.epistemic_status,
            "invalidated": self.invalidated,
            "successful_reuse_count": self.successful_reuse_count,
            "failed_reuse_count": self.failed_reuse_count,
            "metadata": dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class ContextQueryResult:
    available: bool
    candidates: tuple[ContextCandidate, ...]
    source: str
    schema_version: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "candidates": [item.to_dict() for item in self.candidates],
            "source": self.source,
            "schema_version": self.schema_version,
            "error": self.error,
        }


class ContextClient(Protocol):
    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        """Retrieve memory candidates using an existing memory surface."""


class CommandContextClient:
    """
    Delegate retrieval to an existing command.
    Configure with ``L9_SGD_GRAPHITI_SEARCH_COMMAND`` or pass a command
    explicitly. JSON query is sent on stdin.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: int = 30,
    ) -> None:
        if not command:
            raise ValueError("Retrieval command is required")
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(
        cls,
    ) -> CommandContextClient:
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "",
        ).strip()
        if not raw:
            raise ContextRetrievalError("L9_SGD_GRAPHITI_SEARCH_COMMAND is not configured")
        return cls(shlex.split(raw))

    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                query.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
            ),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            return ContextQueryResult(
                available=False,
                candidates=(),
                source="command",
                schema_version="unknown",
                error=completed.stderr.strip() or f"exit {completed.returncode}",
            )
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ContextRetrievalError("Retrieval command returned invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ContextRetrievalError("Retrieval result must be an object")
        schema_version = str(payload.get("schema_version", "1.0.0"))
        major = schema_version.split(".", 1)[0]
        if major != "1":
            raise ContextRetrievalError(f"Unsupported retrieval schema: {schema_version}")
        raw_candidates = payload.get(
            "candidates",
            payload.get("results", []),
        )
        if not isinstance(raw_candidates, list):
            raise ContextRetrievalError("Retrieval candidates must be a list")
        return ContextQueryResult(
            available=True,
            candidates=tuple(
                ContextCandidate.from_mapping(item)
                for item in raw_candidates
                if isinstance(item, Mapping)
            ),
            source=str(payload.get("source", "command")),
            schema_version=schema_version,
            error=None,
        )


class StaticContextClient:
    """Deterministic client used by tests and golden mock mode."""

    def __init__(
        self,
        candidates: Sequence[ContextCandidate],
    ) -> None:
        self.candidates = tuple(candidates)

    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        return ContextQueryResult(
            available=True,
            candidates=self.candidates,
            source="static",
            schema_version="1.0.0",
        )


def query_from_mapping(
    payload: Mapping[str, Any],
) -> ContextQuery:
    return ContextQuery(
        repository=str(payload["repository"]),
        repository_class=str(payload["repository_class"]),
        campaign_id=str(payload["campaign_id"]),
        action_id=str(payload["action_id"]),
        agent_id=str(payload["agent_id"]),
        role=str(payload["role"]),
        task_type=str(payload["task_type"]),
        paths=tuple(str(item) for item in payload.get("paths", [])),
        base_sha=str(payload["base_sha"]),
        visibility_ceiling=str(
            payload.get(
                "visibility_ceiling",
                "repository_local",
            )
        ),
        budget=ContextBudget(
            max_items=int(payload.get("max_items", 12)),
            max_characters=int(payload.get("max_characters", 12_000)),
        ),
        minimum_confidence=float(payload.get("minimum_confidence", 0.70)),
        include_contested=bool(payload.get("include_contested", False)),
        include_raw_evidence=bool(payload.get("include_raw_evidence", False)),
    )


def main() -> int:
    raise SystemExit(
        "context_query CLI disabled (Sonar S8707); use CommandContextClient/ContextQuery APIs"
    )


if __name__ == "__main__":
    raise SystemExit(main())
