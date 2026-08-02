"""Typed, bounded context retrieval through the existing Graphiti surface.

This module owns the Cursor-Governance-side retrieval request and response
contract. It does not implement memory search, ranking, admission, storage, or
hydration. Those remain owned by l9-graphiti-memory.

The default production boundary is an explicitly configured command consuming
one JSON object from stdin and returning one JSON object on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

SUPPORTED_SCHEMA_MAJOR = 1

_ALLOWED_VISIBILITY = {
    "campaign_local",
    "repository_local",
    "project_group",
    "constellation_internal",
    "restricted",
}

_ACTIVE_STATES = {
    "active",
    "accepted",
    "promoted",
    "valid",
}


class ContextRetrievalError(RuntimeError):
    """Base failure for generated-data context retrieval."""


class RetrievalUnavailableError(ContextRetrievalError):
    """The configured retrieval surface could not be reached."""


class RetrievalProtocolError(ContextRetrievalError):
    """The retrieval surface returned an invalid response."""


class RetrievalSchemaError(ContextRetrievalError):
    """The retrieval response uses an unsupported schema version."""


class ContextScope(StrEnum):
    REPOSITORY = "repository"
    CONSTELLATION = "constellation"


@dataclass(frozen=True)
class ContextBudget:
    """Hard context-selection limits supplied to the memory data plane."""

    max_items: int = 12
    max_characters: int = 12_000

    def __post_init__(self) -> None:
        if self.max_items < 1:
            raise ValueError("max_items must be positive")
        if self.max_characters < 1:
            raise ValueError("max_characters must be positive")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_items": self.max_items,
            "max_characters": self.max_characters,
        }


@dataclass(frozen=True)
class ContextQuery:
    """Governed request for memory search and bounded hydration."""

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
    budget: ContextBudget = field(default_factory=ContextBudget)
    scope: ContextScope = ContextScope.REPOSITORY
    minimum_confidence: float = 0.70
    include_contested: bool = False
    include_raw_evidence: bool = False
    query_text: str | None = None
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        for name in (
            "repository",
            "repository_class",
            "campaign_id",
            "action_id",
            "agent_id",
            "role",
            "task_type",
            "base_sha",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if self.visibility_ceiling not in _ALLOWED_VISIBILITY:
            raise ValueError(f"Unsupported visibility ceiling: {self.visibility_ceiling}")

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be within [0.0, 1.0]")

        normalized_paths = tuple(normalize_repository_path(path) for path in self.paths)
        object.__setattr__(self, "paths", normalized_paths)

        if self.scope is ContextScope.REPOSITORY and not self.repository:
            raise ValueError("repository scope requires an explicit repository")

        validate_schema_major(self.schema_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": "GeneratedDataContextQuery",
            "scope": self.scope.value,
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
            "query": self.query_text or self.default_query_text(),
        }

    def default_query_text(self) -> str:
        path_text = ", ".join(self.paths) if self.paths else "repository"
        return f"Reusable knowledge for {self.task_type} by role {self.role} affecting {path_text}"


@dataclass(frozen=True)
class ContextCandidate:
    """One memory item returned by the canonical memory data plane."""

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
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> ContextCandidate:
        record_id = string_field(
            value,
            "record_id",
            fallback="id",
        )
        text = string_field(
            value,
            "text",
            fallback="statement",
        )

        state = str(value.get("state", "unknown")).lower()
        invalidated = bool(
            value.get("invalidated", False)
            or state
            in {
                "archived",
                "deleted",
                "deletion_pending",
                "invalidated",
                "superseded",
            }
        )

        return cls(
            record_id=record_id,
            text=text,
            score=float(value.get("score", 0.0)),
            confidence=float(value.get("confidence", 0.0)),
            state=state,
            authority_class=str(value.get("authority_class", "advisory")),
            visibility=str(
                value.get(
                    "visibility",
                    "repository_local",
                )
            ),
            repository=str(value.get("repository", "")),
            source_sha=optional_string(
                value.get(
                    "source_sha",
                    value.get("base_sha"),
                )
            ),
            paths=tuple(
                normalize_repository_path(str(item)) for item in sequence_field(value, "paths")
            ),
            task_types=tuple(
                str(item)
                for item in sequence_field(
                    value,
                    "task_types",
                )
            ),
            roles=tuple(str(item) for item in sequence_field(value, "roles")),
            epistemic_status=str(
                value.get(
                    "epistemic_status",
                    "observed",
                )
            ),
            invalidated=invalidated,
            successful_reuse_count=int(
                value.get(
                    "successful_reuse_count",
                    0,
                )
            ),
            failed_reuse_count=int(
                value.get(
                    "failed_reuse_count",
                    0,
                )
            ),
            metadata=dict(
                value.get("metadata", {})
                if isinstance(
                    value.get("metadata", {}),
                    Mapping,
                )
                else {}
            ),
        )

    @property
    def ordinarily_eligible(self) -> bool:
        return not self.invalidated and self.state in _ACTIVE_STATES

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
            "successful_reuse_count": (self.successful_reuse_count),
            "failed_reuse_count": (self.failed_reuse_count),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ContextQueryResult:
    """Typed retrieval response with availability separated from emptiness."""

    available: bool
    candidates: tuple[ContextCandidate, ...]
    source: str
    schema_version: str
    request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return self.available and not self.candidates

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "empty": self.empty,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "source": self.source,
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "metadata": dict(self.raw_metadata),
        }


class ContextClient(Protocol):
    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        """Execute one governed context query."""


class CommandContextClient:
    """Invoke the existing memory command with JSON over stdin/stdout."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: int = 30,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError("Context retrieval command is required")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")

        self.command = tuple(str(item) for item in command)
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = ("L9_SGD_GRAPHITI_SEARCH_COMMAND"),
        timeout_seconds: int = 30,
    ) -> CommandContextClient:
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise RetrievalUnavailableError(f"{variable} is not configured")
        return cls(
            shlex.split(raw),
            timeout_seconds=timeout_seconds,
        )

    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        try:
            completed = subprocess.run(
                list(self.command),
                input=canonical_json(query.to_dict()),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise RetrievalUnavailableError(
                f"Context retrieval timed out after {self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise RetrievalUnavailableError(f"Context command could not start: {exc}") from exc

        stderr = completed.stderr.strip()

        if completed.returncode != 0:
            return ContextQueryResult(
                available=False,
                candidates=(),
                source="command",
                schema_version="unknown",
                error_code=exit_code_name(completed.returncode),
                error_message=(stderr or f"command exited {completed.returncode}"),
                raw_metadata={
                    "exit_code": completed.returncode,
                },
            )

        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RetrievalProtocolError("Context command stdout was not valid JSON") from exc

        if not isinstance(payload, Mapping):
            raise RetrievalProtocolError("Context command response must be a JSON object")

        return parse_query_result(
            payload,
            source="command",
        )


class StaticContextClient:
    """Deterministic boundary for tests and explicit local simulation."""

    def __init__(
        self,
        candidates: Sequence[ContextCandidate],
        *,
        source: str = "static",
    ) -> None:
        self.candidates = tuple(candidates)
        self.source = source

    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        del query
        return ContextQueryResult(
            available=True,
            candidates=self.candidates,
            source=self.source,
            schema_version="1.0.0",
        )


def parse_query_result(
    payload: Mapping[str, Any],
    *,
    source: str,
) -> ContextQueryResult:
    schema_version = str(payload.get("schema_version", "1.0.0"))
    validate_schema_major(schema_version)

    available = bool(payload.get("available", True))

    raw_candidates = payload.get(
        "candidates",
        payload.get(
            "records",
            payload.get("results", []),
        ),
    )
    if raw_candidates is None:
        raw_candidates = []
    if not isinstance(raw_candidates, list):
        raise RetrievalProtocolError("Context candidates must be a JSON array")

    candidates = tuple(
        ContextCandidate.from_mapping(item) for item in raw_candidates if isinstance(item, Mapping)
    )

    return ContextQueryResult(
        available=available,
        candidates=candidates,
        source=str(payload.get("source", source)),
        schema_version=schema_version,
        request_id=optional_string(payload.get("request_id")),
        error_code=optional_string(payload.get("error_code")),
        error_message=optional_string(
            payload.get(
                "error_message",
                payload.get("error"),
            )
        ),
        raw_metadata={
            key: value
            for key, value in payload.items()
            if key
            not in {
                "available",
                "candidates",
                "records",
                "results",
                "source",
                "schema_version",
                "request_id",
                "error_code",
                "error_message",
                "error",
            }
        },
    )


def query_from_mapping(
    payload: Mapping[str, Any],
) -> ContextQuery:
    return ContextQuery(
        repository=string_field(
            payload,
            "repository",
        ),
        repository_class=string_field(
            payload,
            "repository_class",
        ),
        campaign_id=string_field(
            payload,
            "campaign_id",
        ),
        action_id=string_field(
            payload,
            "action_id",
        ),
        agent_id=string_field(
            payload,
            "agent_id",
        ),
        role=string_field(payload, "role"),
        task_type=string_field(
            payload,
            "task_type",
        ),
        paths=tuple(
            str(item)
            for item in sequence_field(
                payload,
                "paths",
            )
        ),
        base_sha=string_field(
            payload,
            "base_sha",
        ),
        visibility_ceiling=str(
            payload.get(
                "visibility_ceiling",
                "repository_local",
            )
        ),
        budget=ContextBudget(
            max_items=int(payload.get("max_items", 12)),
            max_characters=int(
                payload.get(
                    "max_characters",
                    12_000,
                )
            ),
        ),
        scope=ContextScope(
            str(
                payload.get(
                    "scope",
                    ContextScope.REPOSITORY.value,
                )
            )
        ),
        minimum_confidence=float(
            payload.get(
                "minimum_confidence",
                0.70,
            )
        ),
        include_contested=bool(
            payload.get(
                "include_contested",
                False,
            )
        ),
        include_raw_evidence=bool(
            payload.get(
                "include_raw_evidence",
                False,
            )
        ),
        query_text=optional_string(payload.get("query")),
        schema_version=str(
            payload.get(
                "schema_version",
                "1.0.0",
            )
        ),
    )


def normalize_repository_path(value: str) -> str:
    path = value.replace("\\", "/").strip()
    if not path:
        raise ValueError("Repository path cannot be empty")
    if path.startswith("/"):
        raise ValueError("Repository path must be relative")

    parts = tuple(part for part in path.split("/") if part not in {"", "."})
    if ".." in parts:
        raise ValueError("Repository path traversal is forbidden")
    return "/".join(parts)


def validate_schema_major(
    schema_version: str,
) -> None:
    try:
        major = int(schema_version.split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise RetrievalSchemaError(f"Invalid schema version: {schema_version!r}") from exc

    if major != SUPPORTED_SCHEMA_MAJOR:
        raise RetrievalSchemaError(f"Unsupported context schema major: {major}")


def string_field(
    value: Mapping[str, Any],
    field_name: str,
    *,
    fallback: str | None = None,
) -> str:
    raw = value.get(field_name)
    if raw is None and fallback:
        raw = value.get(fallback)
    if not isinstance(raw, str) or not raw.strip():
        raise RetrievalProtocolError(f"{field_name} must be a non-empty string")
    return raw.strip()


def sequence_field(
    value: Mapping[str, Any],
    field_name: str,
) -> Sequence[Any]:
    raw = value.get(field_name, [])
    if isinstance(raw, (str, bytes)):
        raise RetrievalProtocolError(f"{field_name} must be an array")
    if not isinstance(raw, Sequence):
        raise RetrievalProtocolError(f"{field_name} must be an array")
    return raw


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def canonical_json(
    value: Mapping[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def exit_code_name(code: int) -> str:
    return {
        2: "invalid_input",
        3: "authorization_denied",
        4: "schema_incompatible",
        5: "service_unavailable",
        6: "conflict",
        7: "policy_rejected",
        8: "internal_invariant",
    }.get(code, "command_failed")


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=("Query l9-graphiti-memory through the configured governed command surface.")
    )
    parser.add_argument(
        "--query",
        help="JSON query file. Defaults to stdin.",
    )
    parser.add_argument(
        "--command",
        nargs="+",
        help=("Explicit retrieval command. Otherwise L9_SGD_GRAPHITI_SEARCH_COMMAND is used."),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
    )
    args = parser.parse_args(argv)

    if args.query:
        payload = json.loads(Path(args.query).read_text(encoding="utf-8"))
    else:
        payload = json.load(os.sys.stdin)

    if not isinstance(payload, Mapping):
        raise SystemExit("Context query must be a JSON object")

    query = query_from_mapping(payload)
    client = (
        CommandContextClient(
            args.command,
            timeout_seconds=args.timeout_seconds,
        )
        if args.command
        else CommandContextClient.from_environment(timeout_seconds=args.timeout_seconds)
    )
    result = client.query(query)

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.available else 5


if __name__ == "__main__":
    raise SystemExit(main())
