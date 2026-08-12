These files are bound to the current merged `GraphitiMemoryAdapter` candidate shape and the existing `PipelineStateStore` methods for context selections, reuse events, and invalidation events.

Create and run this installer in **`Quantum-L9/Cursor-Governance`**:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
BASE="$ROOT/subagent-generated-data"
RETRIEVAL="$BASE/retrieval"
INVALIDATION="$BASE/invalidation"
ORCHESTRATION="$BASE/orchestration"

cd "$ROOT"

if [[ ! -f "CANONICAL_LAW.md" ]] \
  || [[ ! -f "$BASE/adapters/graphiti_memory.py" ]] \
  || [[ ! -f "$ORCHESTRATION/state_store.py" ]]; then
  echo "ERROR: Run only from Quantum-L9/Cursor-Governance." >&2
  exit 1
fi

ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
if [[ -n "$ORIGIN" ]] \
  && [[ "$ORIGIN" != *"Quantum-L9/Cursor-Governance"* ]]; then
  echo "ERROR: Wrong repository origin: $ORIGIN" >&2
  exit 1
fi

mkdir -p "$RETRIEVAL" "$INVALIDATION"

cat > "$RETRIEVAL/context_query.py" <<'PY'
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
            raise ValueError(
                f"Unsupported visibility ceiling: {self.visibility_ceiling}"
            )

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be within [0.0, 1.0]"
            )

        normalized_paths = tuple(
            normalize_repository_path(path)
            for path in self.paths
        )
        object.__setattr__(self, "paths", normalized_paths)

        if self.scope is ContextScope.REPOSITORY and not self.repository:
            raise ValueError(
                "repository scope requires an explicit repository"
            )

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
        return (
            f"Reusable knowledge for {self.task_type} by role "
            f"{self.role} affecting {path_text}"
        )


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
    ) -> "ContextCandidate":
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
            or state in {
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
            authority_class=str(
                value.get("authority_class", "advisory")
            ),
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
                normalize_repository_path(str(item))
                for item in sequence_field(value, "paths")
            ),
            task_types=tuple(
                str(item)
                for item in sequence_field(
                    value,
                    "task_types",
                )
            ),
            roles=tuple(
                str(item)
                for item in sequence_field(value, "roles")
            ),
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
        return (
            not self.invalidated
            and self.state in _ACTIVE_STATES
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
            "successful_reuse_count": (
                self.successful_reuse_count
            ),
            "failed_reuse_count": (
                self.failed_reuse_count
            ),
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
    raw_metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @property
    def empty(self) -> bool:
        return self.available and not self.candidates

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "empty": self.empty,
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
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
            raise ValueError(
                "Context retrieval command is required"
            )
        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be positive"
            )

        self.command = tuple(str(item) for item in command)
        self.timeout_seconds = timeout_seconds
        self.environment = (
            dict(environment)
            if environment is not None
            else None
        )

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = (
            "L9_SGD_GRAPHITI_SEARCH_COMMAND"
        ),
        timeout_seconds: int = 30,
    ) -> "CommandContextClient":
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise RetrievalUnavailableError(
                f"{variable} is not configured"
            )
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise RetrievalUnavailableError(
                f"Context retrieval timed out after "
                f"{self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise RetrievalUnavailableError(
                f"Context command could not start: {exc}"
            ) from exc

        stderr = completed.stderr.strip()

        if completed.returncode != 0:
            return ContextQueryResult(
                available=False,
                candidates=(),
                source="command",
                schema_version="unknown",
                error_code=exit_code_name(
                    completed.returncode
                ),
                error_message=(
                    stderr
                    or f"command exited "
                    f"{completed.returncode}"
                ),
                raw_metadata={
                    "exit_code": completed.returncode,
                },
            )

        try:
            payload = json.loads(
                completed.stdout or "{}"
            )
        except json.JSONDecodeError as exc:
            raise RetrievalProtocolError(
                "Context command stdout was not valid JSON"
            ) from exc

        if not isinstance(payload, Mapping):
            raise RetrievalProtocolError(
                "Context command response must be a JSON object"
            )

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
    schema_version = str(
        payload.get("schema_version", "1.0.0")
    )
    validate_schema_major(schema_version)

    available = bool(
        payload.get("available", True)
    )

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
        raise RetrievalProtocolError(
            "Context candidates must be a JSON array"
        )

    candidates = tuple(
        ContextCandidate.from_mapping(item)
        for item in raw_candidates
        if isinstance(item, Mapping)
    )

    return ContextQueryResult(
        available=available,
        candidates=candidates,
        source=str(
            payload.get("source", source)
        ),
        schema_version=schema_version,
        request_id=optional_string(
            payload.get("request_id")
        ),
        error_code=optional_string(
            payload.get("error_code")
        ),
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
            max_items=int(
                payload.get("max_items", 12)
            ),
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
        query_text=optional_string(
            payload.get("query")
        ),
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
        raise ValueError(
            "Repository path cannot be empty"
        )
    if path.startswith("/"):
        raise ValueError(
            "Repository path must be relative"
        )

    parts = tuple(
        part
        for part in path.split("/")
        if part not in {"", "."}
    )
    if ".." in parts:
        raise ValueError(
            "Repository path traversal is forbidden"
        )
    return "/".join(parts)


def validate_schema_major(
    schema_version: str,
) -> None:
    try:
        major = int(
            schema_version.split(".", 1)[0]
        )
    except (TypeError, ValueError) as exc:
        raise RetrievalSchemaError(
            f"Invalid schema version: {schema_version!r}"
        ) from exc

    if major != SUPPORTED_SCHEMA_MAJOR:
        raise RetrievalSchemaError(
            f"Unsupported context schema major: {major}"
        )


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
        raise RetrievalProtocolError(
            f"{field_name} must be a non-empty string"
        )
    return raw.strip()


def sequence_field(
    value: Mapping[str, Any],
    field_name: str,
) -> Sequence[Any]:
    raw = value.get(field_name, [])
    if isinstance(raw, (str, bytes)):
        raise RetrievalProtocolError(
            f"{field_name} must be an array"
        )
    if not isinstance(raw, Sequence):
        raise RetrievalProtocolError(
            f"{field_name} must be an array"
        )
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
        description=(
            "Query l9-graphiti-memory through the "
            "configured governed command surface."
        )
    )
    parser.add_argument(
        "--query",
        help="JSON query file. Defaults to stdin.",
    )
    parser.add_argument(
        "--command",
        nargs="+",
        help=(
            "Explicit retrieval command. Otherwise "
            "L9_SGD_GRAPHITI_SEARCH_COMMAND is used."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
    )
    args = parser.parse_args(argv)

    if args.query:
        payload = json.loads(
            Path(args.query).read_text(
                encoding="utf-8"
            )
        )
    else:
        payload = json.load(os.sys.stdin)

    if not isinstance(payload, Mapping):
        raise SystemExit(
            "Context query must be a JSON object"
        )

    query = query_from_mapping(payload)
    client = (
        CommandContextClient(
            args.command,
            timeout_seconds=args.timeout_seconds,
        )
        if args.command
        else CommandContextClient.from_environment(
            timeout_seconds=args.timeout_seconds
        )
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
PY

cat > "$RETRIEVAL/reuse_recorder.py" <<'PY'
"""Governed memory-reuse lifecycle and remote recording bridge.

Search results are not reuse. A memory becomes a reuse candidate when selected,
is considered consumed when injected into an agent contract, and becomes proven
reuse only when a task, verifier, or reviewer finalizes an outcome.

Cursor-Governance records local lifecycle evidence in PipelineStateStore and
dispatches only finalized outcomes to l9-graphiti-memory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_STATE_STORE_PATH = (
    _PACKAGE_ROOT
    / "orchestration"
    / "state_store.py"
)

SUPPORTED_SCHEMA_MAJOR = 1

SUCCESSFUL_OUTCOMES = {
    "accelerated_execution",
    "prevented_error",
    "improved_validation",
    "improved_context",
    "reduced_discovery",
    "improved_scope_control",
    "improved_contract",
}

VALID_OUTCOMES = SUCCESSFUL_OUTCOMES | {
    "no_observable_value",
    "caused_confusion",
    "stale",
    "incorrect",
}

NEGATIVE_INVALIDATION_CANDIDATE_OUTCOMES = {
    "stale",
    "incorrect",
}


class ReuseRecorderError(RuntimeError):
    """Base memory-reuse recording failure."""


class ReuseProtocolError(ReuseRecorderError):
    """The local or remote reuse protocol was invalid."""


class ReuseCollisionError(ReuseRecorderError):
    """An immutable reuse event ID was reused with different content."""


class ReuseTransportError(ReuseRecorderError):
    """The memory reuse destination could not be called safely."""


class ReuseStage(StrEnum):
    SELECTED = "selected"
    INJECTED = "injected"
    FINALIZED = "finalized"


@dataclass(frozen=True)
class ReuseIdentity:
    repository: str
    campaign_id: str
    action_id: str
    agent_id: str
    role: str

    def __post_init__(self) -> None:
        for name in (
            "repository",
            "campaign_id",
            "action_id",
            "agent_id",
            "role",
        ):
            value = getattr(self, name)
            if not value.strip():
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

    def to_dict(self) -> dict[str, str]:
        return {
            "repository": self.repository,
            "campaign_id": self.campaign_id,
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "role": self.role,
        }


@dataclass(frozen=True)
class PendingReuse:
    record_id: str
    consumer: ReuseIdentity
    context_pack_id: str
    query: str
    injection_method: str = (
        "agent_contract_context"
    )

    def __post_init__(self) -> None:
        for name in (
            "record_id",
            "context_pack_id",
            "query",
            "injection_method",
        ):
            value = getattr(self, name)
            if not value.strip():
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

    def identity_seed(
        self,
        stage: ReuseStage,
    ) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "consumer": self.consumer.to_dict(),
            "context_pack_id": self.context_pack_id,
            "query": self.query,
            "injection_method": self.injection_method,
            "stage": stage.value,
        }


@dataclass(frozen=True)
class ReuseFinalization:
    outcome: str
    evidence: Mapping[str, Any]
    correction_required: bool
    validity_confirmed: bool
    occurred_at: str = field(
        default_factory=lambda: (
            datetime.now(UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Unsupported reuse outcome: "
                f"{self.outcome}"
            )
        if not isinstance(self.evidence, Mapping):
            raise ValueError(
                "evidence must be an object"
            )
        validate_utc_timestamp(self.occurred_at)


@dataclass(frozen=True)
class ReuseDispatchResult:
    event_id: str
    stage: ReuseStage
    local_created: bool
    local_duplicate: bool
    remote_dispatched: bool
    remote_status: str | None
    remote_response: Mapping[str, Any] | None
    invalidation_candidate: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "stage": self.stage.value,
            "local_created": self.local_created,
            "local_duplicate": self.local_duplicate,
            "remote_dispatched": (
                self.remote_dispatched
            ),
            "remote_status": self.remote_status,
            "remote_response": (
                dict(self.remote_response)
                if self.remote_response is not None
                else None
            ),
            "invalidation_candidate": (
                dict(self.invalidation_candidate)
                if self.invalidation_candidate
                is not None
                else None
            ),
        }


class ReuseTransport(Protocol):
    def record(
        self,
        event: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Record one finalized reuse event."""


class CommandReuseTransport:
    """Invoke the existing Graphiti reuse command over stdin/stdout."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: int = 30,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError(
                "Reuse command is required"
            )
        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be positive"
            )
        self.command = tuple(
            str(item) for item in command
        )
        self.timeout_seconds = timeout_seconds
        self.environment = (
            dict(environment)
            if environment is not None
            else None
        )

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = (
            "L9_SGD_GRAPHITI_REUSE_COMMAND"
        ),
        timeout_seconds: int = 30,
    ) -> "CommandReuseTransport":
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise ReuseTransportError(
                f"{variable} is not configured"
            )
        return cls(
            shlex.split(raw),
            timeout_seconds=timeout_seconds,
        )

    def record(
        self,
        event: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        try:
            completed = subprocess.run(
                list(self.command),
                input=canonical_json(event),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise ReuseTransportError(
                f"Reuse command timed out after "
                f"{self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise ReuseTransportError(
                f"Reuse command could not start: {exc}"
            ) from exc

        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise ReuseTransportError(
                f"Reuse command failed with exit "
                f"{completed.returncode}: {stderr}"
            )

        try:
            response = json.loads(
                completed.stdout or "{}"
            )
        except json.JSONDecodeError as exc:
            raise ReuseProtocolError(
                "Reuse command stdout was not valid JSON"
            ) from exc

        if not isinstance(response, Mapping):
            raise ReuseProtocolError(
                "Reuse response must be a JSON object"
            )

        status = str(
            response.get("status", "")
        )
        if status not in {
            "recorded",
            "accepted",
            "duplicate",
            "already_exists",
        }:
            raise ReuseProtocolError(
                f"Unsupported reuse status: "
                f"{status!r}"
            )

        return dict(response)


class ReuseRecorder:
    """Record local reuse lifecycle and dispatch finalized outcomes."""

    def __init__(
        self,
        state_store: Any,
        *,
        transport: ReuseTransport | None = None,
    ) -> None:
        self.state_store = state_store
        self.transport = transport

    @classmethod
    def from_database(
        cls,
        database_path: str | Path,
        *,
        transport: ReuseTransport | None = None,
    ) -> "ReuseRecorder":
        module = load_state_store_module()
        store_type = getattr(
            module,
            "PipelineStateStore",
        )
        return cls(
            store_type(database_path),
            transport=transport,
        )

    def record_selection(
        self,
        pending: PendingReuse,
        *,
        evidence: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record_local_stage(
            pending,
            stage=ReuseStage.SELECTED,
            payload={
                "selection_evidence": dict(evidence),
                "proven_reuse": False,
            },
        )

    def record_injection(
        self,
        pending: PendingReuse,
        *,
        evidence: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record_local_stage(
            pending,
            stage=ReuseStage.INJECTED,
            payload={
                "injection_evidence": dict(evidence),
                "proven_reuse": False,
            },
        )

    def finalize_outcome(
        self,
        pending: PendingReuse,
        finalization: ReuseFinalization,
    ) -> ReuseDispatchResult:
        event_id = deterministic_event_id(
            pending,
            stage=ReuseStage.FINALIZED,
            outcome=finalization.outcome,
        )

        event = {
            "schema_version": "1.0.0",
            "kind": "MemoryReuseEvent",
            "event_id": event_id,
            "record_id": pending.record_id,
            "consumer": pending.consumer.to_dict(),
            "use": {
                "query": pending.query,
                "injection_method": (
                    pending.injection_method
                ),
                "context_pack_id": (
                    pending.context_pack_id
                ),
            },
            "outcome": finalization.outcome,
            "evidence": dict(
                finalization.evidence
            ),
            "correction_required": (
                finalization.correction_required
            ),
            "validity_confirmed": (
                finalization.validity_confirmed
            ),
            "occurred_at": finalization.occurred_at,
            "metadata": {
                "producer": "Cursor-Governance",
                "proven_reuse": True,
                **dict(finalization.metadata),
            },
        }

        row, created = self._record_local(
            event_id=event_id,
            pending=pending,
            stage=ReuseStage.FINALIZED,
            outcome=finalization.outcome,
            payload=event,
        )

        remote_response: Mapping[str, Any] | None = None
        remote_status: str | None = None
        remote_dispatched = False

        if self.transport is not None:
            remote_response = self.transport.record(
                event
            )
            remote_status = str(
                remote_response.get("status", "")
            )
            remote_dispatched = True

        invalidation_candidate = (
            build_invalidation_candidate(
                event
            )
            if finalization.outcome
            in NEGATIVE_INVALIDATION_CANDIDATE_OUTCOMES
            else None
        )

        return ReuseDispatchResult(
            event_id=event_id,
            stage=ReuseStage.FINALIZED,
            local_created=created,
            local_duplicate=not created,
            remote_dispatched=remote_dispatched,
            remote_status=remote_status,
            remote_response=remote_response,
            invalidation_candidate=(
                invalidation_candidate
            ),
        )

    def _record_local_stage(
        self,
        pending: PendingReuse,
        *,
        stage: ReuseStage,
        payload: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        event_id = deterministic_event_id(
            pending,
            stage=stage,
            outcome=None,
        )
        body = {
            "schema_version": "1.0.0",
            "kind": "MemoryReuseLifecycleEvent",
            "event_id": event_id,
            "record_id": pending.record_id,
            "consumer": pending.consumer.to_dict(),
            "use": {
                "query": pending.query,
                "injection_method": (
                    pending.injection_method
                ),
                "context_pack_id": (
                    pending.context_pack_id
                ),
            },
            "stage": stage.value,
            **dict(payload),
        }

        _, created = self._record_local(
            event_id=event_id,
            pending=pending,
            stage=stage,
            outcome=None,
            payload=body,
        )

        return ReuseDispatchResult(
            event_id=event_id,
            stage=stage,
            local_created=created,
            local_duplicate=not created,
            remote_dispatched=False,
            remote_status=None,
            remote_response=None,
            invalidation_candidate=None,
        )

    def _record_local(
        self,
        *,
        event_id: str,
        pending: PendingReuse,
        stage: ReuseStage,
        outcome: str | None,
        payload: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], bool]:
        row, created = (
            self.state_store.record_reuse_event(
                event_id=event_id,
                record_id=pending.record_id,
                campaign_id=(
                    pending.consumer.campaign_id
                ),
                action_id=(
                    pending.consumer.action_id
                ),
                agent_id=(
                    pending.consumer.agent_id
                ),
                context_pack_id=(
                    pending.context_pack_id
                ),
                stage=stage.value,
                outcome=outcome,
                payload=payload,
            )
        )

        if not created:
            stored_payload = row.get(
                "payload_json"
            )
            if stored_payload is not None:
                try:
                    parsed = json.loads(
                        str(stored_payload)
                    )
                except json.JSONDecodeError as exc:
                    raise ReuseProtocolError(
                        "Stored reuse payload is invalid JSON"
                    ) from exc

                if canonical_json(parsed) != (
                    canonical_json(payload)
                ):
                    raise ReuseCollisionError(
                        f"Reuse event ID collision: "
                        f"{event_id}"
                    )

        return row, created


def build_invalidation_candidate(
    reuse_event: Mapping[str, Any],
) -> dict[str, Any]:
    """Create an advisory candidate; never mutate memory directly."""

    event_id = str(reuse_event["event_id"])
    return {
        "schema_version": "1.0.0",
        "kind": "SourceInvalidationCandidate",
        "candidate_id": (
            f"invalidation-candidate-{event_id}"
        ),
        "event_type": "failed_reuse_reported",
        "record_ids": [
            str(reuse_event["record_id"])
        ],
        "reason": str(reuse_event["outcome"]),
        "source_reuse_event_id": event_id,
        "requires_policy_approval": True,
        "may_delete_memory": False,
        "may_mutate_memory_directly": False,
    }


def deterministic_event_id(
    pending: PendingReuse,
    *,
    stage: ReuseStage,
    outcome: str | None,
) -> str:
    seed = {
        **pending.identity_seed(stage),
        "outcome": outcome,
    }
    digest = hashlib.sha256(
        canonical_json(seed).encode("utf-8")
    ).hexdigest()
    return f"reuse-{digest[:32]}"


def load_state_store_module() -> ModuleType:
    if not _STATE_STORE_PATH.is_file():
        raise ReuseRecorderError(
            f"State store not found: "
            f"{_STATE_STORE_PATH}"
        )

    module_name = (
        "_l9_sgd_orchestration_state_store"
    )
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        _STATE_STORE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ReuseRecorderError(
            "Could not create state-store import spec"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def validate_utc_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid occurred_at timestamp: {value}"
        ) from exc

    if parsed.tzinfo is None:
        raise ValueError(
            "occurred_at must be timezone-aware"
        )


def canonical_json(
    value: Mapping[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record a finalized governed memory-reuse "
            "outcome."
        )
    )
    parser.add_argument(
        "--database",
        required=True,
    )
    parser.add_argument(
        "--event",
        help=(
            "Finalization JSON file. Defaults to stdin."
        ),
    )
    parser.add_argument(
        "--command",
        nargs="+",
        help=(
            "Explicit Graphiti reuse command. When omitted, "
            "L9_SGD_GRAPHITI_REUSE_COMMAND is used."
        ),
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
    )
    args = parser.parse_args(argv)

    if args.event:
        payload = json.loads(
            Path(args.event).read_text(
                encoding="utf-8"
            )
        )
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise SystemExit(
            "Reuse finalization must be a JSON object"
        )

    consumer_payload = payload.get(
        "consumer",
        {},
    )
    use_payload = payload.get("use", {})
    if not isinstance(
        consumer_payload,
        Mapping,
    ) or not isinstance(use_payload, Mapping):
        raise SystemExit(
            "consumer and use must be objects"
        )

    pending = PendingReuse(
        record_id=str(payload["record_id"]),
        consumer=ReuseIdentity(
            repository=str(
                consumer_payload["repository"]
            ),
            campaign_id=str(
                consumer_payload["campaign_id"]
            ),
            action_id=str(
                consumer_payload["action_id"]
            ),
            agent_id=str(
                consumer_payload["agent_id"]
            ),
            role=str(consumer_payload["role"]),
        ),
        context_pack_id=str(
            use_payload["context_pack_id"]
        ),
        query=str(use_payload["query"]),
        injection_method=str(
            use_payload.get(
                "injection_method",
                "agent_contract_context",
            )
        ),
    )
    finalization = ReuseFinalization(
        outcome=str(payload["outcome"]),
        evidence=dict(
            payload.get("evidence", {})
        ),
        correction_required=bool(
            payload.get(
                "correction_required",
                False,
            )
        ),
        validity_confirmed=bool(
            payload.get(
                "validity_confirmed",
                True,
            )
        ),
        occurred_at=str(
            payload.get(
                "occurred_at",
                datetime.now(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
            )
        ),
        metadata=dict(
            payload.get("metadata", {})
        ),
    )

    transport: ReuseTransport | None
    if args.local_only:
        transport = None
    elif args.command:
        transport = CommandReuseTransport(
            args.command,
            timeout_seconds=args.timeout_seconds,
        )
    else:
        transport = (
            CommandReuseTransport.from_environment(
                timeout_seconds=(
                    args.timeout_seconds
                )
            )
        )

    recorder = ReuseRecorder.from_database(
        args.database,
        transport=transport,
    )
    result = recorder.finalize_outcome(
        pending,
        finalization,
    )

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$INVALIDATION/repository_event_bridge.py" <<'PY'
"""Structured repository-change to memory-invalidation bridge.

This module converts explicit Git or version-change evidence into the
SourceInvalidationRequest contract consumed by l9-graphiti-memory. It never
parses memory prose, deletes memory, creates replacement records, or performs
lifecycle mutation locally.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Protocol


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_STATE_STORE_PATH = (
    _PACKAGE_ROOT
    / "orchestration"
    / "state_store.py"
)

SUPPORTED_SCHEMA_MAJOR = 1

SUPPORTED_EVENT_TYPES = {
    "repository_path_changed",
    "repository_base_changed",
    "schema_version_changed",
    "contract_version_changed",
    "policy_version_changed",
    "architecture_owner_changed",
    "dependency_upgraded",
    "contradictory_evidence_accepted",
    "failed_reuse_reported",
    "expiration_reached",
}


class RepositoryEventBridgeError(RuntimeError):
    """Base repository invalidation bridge failure."""


class RepositoryStateError(
    RepositoryEventBridgeError
):
    """The repository state is unsuitable for deterministic diffing."""


class InvalidationCollisionError(
    RepositoryEventBridgeError
):
    """An immutable event ID was reused with different content."""


class InvalidationTransportError(
    RepositoryEventBridgeError
):
    """The invalidation destination failed or returned an invalid response."""


class ChangeKind(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    TYPE_CHANGED = "type_changed"


@dataclass(frozen=True)
class ChangedPath:
    path: str
    change_kind: ChangeKind
    previous_path: str | None = None

    def __post_init__(self) -> None:
        normalized = normalize_repository_path(
            self.path
        )
        object.__setattr__(
            self,
            "path",
            normalized,
        )

        if self.previous_path is not None:
            object.__setattr__(
                self,
                "previous_path",
                normalize_repository_path(
                    self.previous_path
                ),
            )

        if (
            self.change_kind is ChangeKind.RENAMED
            and self.previous_path is None
        ):
            raise ValueError(
                "Renamed paths require previous_path"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_kind": self.change_kind.value,
            "previous_path": self.previous_path,
        }


@dataclass(frozen=True)
class RepositoryChangeEvent:
    repository: str
    event_type: str
    from_sha: str | None
    to_sha: str | None
    changed_paths: tuple[ChangedPath, ...] = ()
    selectors: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = None  # type: ignore[assignment]
    event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.repository.strip():
            raise ValueError(
                "repository must be non-empty"
            )
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(
                f"Unsupported invalidation event type: "
                f"{self.event_type}"
            )

        metadata = (
            {}
            if self.metadata is None
            else dict(self.metadata)
        )
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

        if (
            self.event_type
            == "repository_path_changed"
            and not self.changed_paths
            and not self.selectors
        ):
            raise ValueError(
                "repository_path_changed requires "
                "changed paths or selectors"
            )

        normalized_selectors = tuple(
            normalize_selector(selector)
            for selector in self.selectors
        )
        object.__setattr__(
            self,
            "selectors",
            normalized_selectors,
        )

        if self.event_id is None:
            object.__setattr__(
                self,
                "event_id",
                deterministic_event_id(
                    repository=self.repository,
                    event_type=self.event_type,
                    from_sha=self.from_sha,
                    to_sha=self.to_sha,
                    changed_paths=self.changed_paths,
                    selectors=normalized_selectors,
                ),
            )

    def effective_selectors(
        self,
    ) -> tuple[Mapping[str, Any], ...]:
        path_selectors = tuple(
            {
                "condition_type": (
                    "relevant_path_changed"
                ),
                "selector": item.path,
                "change_kind": (
                    item.change_kind.value
                ),
                "previous_path": (
                    item.previous_path
                ),
            }
            for item in self.changed_paths
        )
        return path_selectors + self.selectors

    def to_request(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "kind": "SourceInvalidationRequest",
            "event_id": self.event_id,
            "repository": self.repository,
            "from_sha": self.from_sha,
            "to_sha": self.to_sha,
            "event_type": self.event_type,
            "selectors": [
                dict(selector)
                for selector
                in self.effective_selectors()
            ],
            "delete_memory": False,
            "create_replacement_record": False,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class InvalidationDispatchResult:
    event_id: str
    dry_run: bool
    local_created: bool
    local_duplicate: bool
    remote_dispatched: bool
    remote_status: str | None
    response: Mapping[str, Any] | None
    request: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "dry_run": self.dry_run,
            "local_created": self.local_created,
            "local_duplicate": self.local_duplicate,
            "remote_dispatched": (
                self.remote_dispatched
            ),
            "remote_status": self.remote_status,
            "response": (
                dict(self.response)
                if self.response is not None
                else None
            ),
            "request": dict(self.request),
        }


class InvalidationTransport(Protocol):
    def invalidate(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Submit one structured invalidation request."""


class CommandInvalidationTransport:
    """Invoke the existing Graphiti invalidation command."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: int = 30,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError(
                "Invalidation command is required"
            )
        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be positive"
            )
        self.command = tuple(
            str(item) for item in command
        )
        self.timeout_seconds = timeout_seconds
        self.environment = (
            dict(environment)
            if environment is not None
            else None
        )

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = (
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND"
        ),
        timeout_seconds: int = 30,
    ) -> "CommandInvalidationTransport":
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise InvalidationTransportError(
                f"{variable} is not configured"
            )
        return cls(
            shlex.split(raw),
            timeout_seconds=timeout_seconds,
        )

    def invalidate(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        try:
            completed = subprocess.run(
                list(self.command),
                input=canonical_json(request),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise InvalidationTransportError(
                f"Invalidation command timed out after "
                f"{self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise InvalidationTransportError(
                f"Invalidation command could not start: "
                f"{exc}"
            ) from exc

        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise InvalidationTransportError(
                f"Invalidation command failed with exit "
                f"{completed.returncode}: {stderr}"
            )

        try:
            response = json.loads(
                completed.stdout or "{}"
            )
        except json.JSONDecodeError as exc:
            raise InvalidationTransportError(
                "Invalidation command stdout was "
                "not valid JSON"
            ) from exc

        if not isinstance(response, Mapping):
            raise InvalidationTransportError(
                "Invalidation response must be "
                "a JSON object"
            )

        if response.get("deleted") is True:
            raise InvalidationTransportError(
                "Invalidation boundary violation: "
                "destination reported deletion"
            )

        if (
            response.get(
                "replacement_created"
            )
            is True
        ):
            raise InvalidationTransportError(
                "Invalidation boundary violation: "
                "destination created a replacement"
            )

        status = str(
            response.get("status", "")
        )
        if status not in {
            "accepted",
            "invalidated",
            "partially_invalidated",
            "duplicate",
            "no_matches",
            "quarantined",
            "archived",
        }:
            raise InvalidationTransportError(
                f"Unsupported invalidation status: "
                f"{status!r}"
            )

        return dict(response)


class RepositoryEventBridge:
    """Produce and dispatch structured invalidation requests."""

    def __init__(
        self,
        state_store: Any,
        *,
        transport: (
            InvalidationTransport | None
        ) = None,
    ) -> None:
        self.state_store = state_store
        self.transport = transport

    @classmethod
    def from_database(
        cls,
        database_path: str | Path,
        *,
        transport: (
            InvalidationTransport | None
        ) = None,
    ) -> "RepositoryEventBridge":
        module = load_state_store_module()
        store_type = getattr(
            module,
            "PipelineStateStore",
        )
        return cls(
            store_type(database_path),
            transport=transport,
        )

    def from_git_diff(
        self,
        *,
        repository_root: str | Path,
        repository_name: str,
        from_sha: str,
        to_sha: str,
        allow_dirty: bool = False,
    ) -> RepositoryChangeEvent:
        root = Path(repository_root).resolve()
        assert_git_repository(root)

        if not allow_dirty:
            ensure_clean_repository(root)

        validate_commit(root, from_sha)
        validate_commit(root, to_sha)

        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--name-status",
                "--find-renames",
                from_sha,
                to_sha,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RepositoryStateError(
                completed.stderr.strip()
                or "git diff failed"
            )

        changed_paths = tuple(
            parse_name_status(
                completed.stdout
            )
        )

        if not changed_paths:
            raise RepositoryStateError(
                "Git diff contains no changed paths"
            )

        return RepositoryChangeEvent(
            repository=repository_name,
            event_type=(
                "repository_path_changed"
            ),
            from_sha=resolve_commit(
                root,
                from_sha,
            ),
            to_sha=resolve_commit(
                root,
                to_sha,
            ),
            changed_paths=changed_paths,
            metadata={
                "producer": "Cursor-Governance",
                "repository_root": str(root),
            },
        )

    def dispatch(
        self,
        event: RepositoryChangeEvent,
        *,
        dry_run: bool = False,
    ) -> InvalidationDispatchResult:
        request = event.to_request()
        event_id = str(request["event_id"])

        row, created = (
            self.state_store.record_invalidation_event(
                event_id=event_id,
                repository=event.repository,
                from_sha=event.from_sha,
                to_sha=event.to_sha,
                event_type=event.event_type,
                status=(
                    "DRY_RUN"
                    if dry_run
                    else "PENDING"
                ),
                payload=request,
            )
        )

        if not created:
            stored_payload = row.get(
                "payload_json"
            )
            if stored_payload is not None:
                try:
                    parsed = json.loads(
                        str(stored_payload)
                    )
                except json.JSONDecodeError as exc:
                    raise RepositoryEventBridgeError(
                        "Stored invalidation payload "
                        "is invalid JSON"
                    ) from exc

                if canonical_json(parsed) != (
                    canonical_json(request)
                ):
                    raise InvalidationCollisionError(
                        f"Invalidation event ID "
                        f"collision: {event_id}"
                    )

        if dry_run or self.transport is None:
            return InvalidationDispatchResult(
                event_id=event_id,
                dry_run=dry_run,
                local_created=created,
                local_duplicate=not created,
                remote_dispatched=False,
                remote_status=None,
                response=None,
                request=request,
            )

        response = self.transport.invalidate(
            request
        )
        return InvalidationDispatchResult(
            event_id=event_id,
            dry_run=False,
            local_created=created,
            local_duplicate=not created,
            remote_dispatched=True,
            remote_status=str(
                response.get("status", "")
            ),
            response=response,
            request=request,
        )


def parse_name_status(
    output: str,
) -> list[ChangedPath]:
    changes: list[ChangedPath] = []

    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue

        fields = raw_line.split("\t")
        status = fields[0]

        if status.startswith("R"):
            if len(fields) != 3:
                raise RepositoryStateError(
                    f"Invalid rename record: "
                    f"{raw_line!r}"
                )
            changes.append(
                ChangedPath(
                    path=fields[2],
                    previous_path=fields[1],
                    change_kind=(
                        ChangeKind.RENAMED
                    ),
                )
            )
            continue

        if len(fields) != 2:
            raise RepositoryStateError(
                f"Invalid name-status record: "
                f"{raw_line!r}"
            )

        kind = {
            "A": ChangeKind.ADDED,
            "M": ChangeKind.MODIFIED,
            "D": ChangeKind.DELETED,
            "T": ChangeKind.TYPE_CHANGED,
        }.get(status[:1])

        if kind is None:
            continue

        changes.append(
            ChangedPath(
                path=fields[1],
                change_kind=kind,
            )
        )

    return changes


def normalize_selector(
    selector: Mapping[str, Any],
) -> dict[str, Any]:
    condition_type = str(
        selector.get(
            "condition_type",
            "",
        )
    ).strip()
    selector_value = str(
        selector.get("selector", "")
    ).strip()

    if not condition_type:
        raise ValueError(
            "Invalidation selector requires "
            "condition_type"
        )
    if not selector_value:
        raise ValueError(
            "Invalidation selector requires selector"
        )

    normalized: dict[str, Any] = {
        "condition_type": condition_type,
        "selector": (
            normalize_repository_path(
                selector_value
            )
            if condition_type
            == "relevant_path_changed"
            else selector_value
        ),
    }

    if selector.get("change_kind") is not None:
        normalized["change_kind"] = str(
            selector["change_kind"]
        )

    if selector.get("previous_path") is not None:
        normalized["previous_path"] = (
            normalize_repository_path(
                str(
                    selector[
                        "previous_path"
                    ]
                )
            )
        )
    else:
        normalized["previous_path"] = None

    return normalized


def event_from_mapping(
    payload: Mapping[str, Any],
) -> RepositoryChangeEvent:
    schema_version = str(
        payload.get(
            "schema_version",
            "1.0.0",
        )
    )
    validate_schema_major(schema_version)

    changed_paths_raw = payload.get(
        "changed_paths",
        [],
    )
    if not isinstance(
        changed_paths_raw,
        Sequence,
    ) or isinstance(
        changed_paths_raw,
        (str, bytes),
    ):
        raise ValueError(
            "changed_paths must be an array"
        )

    selectors_raw = payload.get(
        "selectors",
        [],
    )
    if not isinstance(
        selectors_raw,
        Sequence,
    ) or isinstance(
        selectors_raw,
        (str, bytes),
    ):
        raise ValueError(
            "selectors must be an array"
        )

    changed_paths = tuple(
        ChangedPath(
            path=str(item["path"]),
            change_kind=ChangeKind(
                str(item["change_kind"])
            ),
            previous_path=(
                str(item["previous_path"])
                if item.get(
                    "previous_path"
                )
                is not None
                else None
            ),
        )
        for item in changed_paths_raw
        if isinstance(item, Mapping)
    )

    selectors = tuple(
        dict(item)
        for item in selectors_raw
        if isinstance(item, Mapping)
    )

    return RepositoryChangeEvent(
        event_id=(
            str(payload["event_id"])
            if payload.get("event_id")
            else None
        ),
        repository=str(
            payload["repository"]
        ),
        event_type=str(
            payload.get(
                "event_type",
                "repository_path_changed",
            )
        ),
        from_sha=optional_string(
            payload.get("from_sha")
        ),
        to_sha=optional_string(
            payload.get("to_sha")
        ),
        changed_paths=changed_paths,
        selectors=selectors,
        metadata=dict(
            payload.get("metadata", {})
            if isinstance(
                payload.get(
                    "metadata",
                    {},
                ),
                Mapping,
            )
            else {}
        ),
    )


def deterministic_event_id(
    *,
    repository: str,
    event_type: str,
    from_sha: str | None,
    to_sha: str | None,
    changed_paths: Sequence[ChangedPath],
    selectors: Sequence[
        Mapping[str, Any]
    ],
) -> str:
    seed = {
        "repository": repository,
        "event_type": event_type,
        "from_sha": from_sha,
        "to_sha": to_sha,
        "changed_paths": [
            item.to_dict()
            for item in changed_paths
        ],
        "selectors": [
            dict(item)
            for item in selectors
        ],
    }
    digest = hashlib.sha256(
        canonical_json(seed).encode("utf-8")
    ).hexdigest()
    return f"invalidation-{digest[:32]}"


def normalize_repository_path(
    value: str,
) -> str:
    text = value.replace("\\", "/").strip()
    if not text:
        raise ValueError(
            "Repository path cannot be empty"
        )
    path = PurePosixPath(text)
    if path.is_absolute():
        raise ValueError(
            "Repository path must be relative"
        )
    if ".." in path.parts:
        raise ValueError(
            "Repository path traversal is forbidden"
        )

    parts = tuple(
        part
        for part in path.parts
        if part not in {"", "."}
    )
    if not parts:
        raise ValueError(
            "Repository path cannot resolve to root"
        )
    return "/".join(parts)


def assert_git_repository(
    root: Path,
) -> None:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--is-inside-work-tree",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )
    if (
        completed.returncode != 0
        or completed.stdout.strip()
        != "true"
    ):
        raise RepositoryStateError(
            f"Not a Git repository: {root}"
        )


def ensure_clean_repository(
    root: Path,
) -> None:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(
            completed.stderr.strip()
            or "git status failed"
        )
    if completed.stdout.strip():
        raise RepositoryStateError(
            "Repository has uncommitted changes"
        )


def validate_commit(
    root: Path,
    revision: str,
) -> None:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "cat-file",
            "-e",
            f"{revision}^{{commit}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(
            f"Unknown commit: {revision}"
        )


def resolve_commit(
    root: Path,
    revision: str,
) -> str:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            f"{revision}^{{commit}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(
            f"Could not resolve commit: "
            f"{revision}"
        )
    return completed.stdout.strip()


def load_state_store_module() -> ModuleType:
    if not _STATE_STORE_PATH.is_file():
        raise RepositoryEventBridgeError(
            f"State store not found: "
            f"{_STATE_STORE_PATH}"
        )

    module_name = (
        "_l9_sgd_orchestration_state_store"
    )
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        _STATE_STORE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RepositoryEventBridgeError(
            "Could not create state-store import spec"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def validate_schema_major(
    schema_version: str,
) -> None:
    try:
        major = int(
            schema_version.split(".", 1)[0]
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid schema version: "
            f"{schema_version!r}"
        ) from exc

    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(
            f"Unsupported invalidation schema "
            f"major: {major}"
        )


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


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create and dispatch a structured "
            "source-invalidation request."
        )
    )
    parser.add_argument(
        "--database",
        required=True,
    )
    parser.add_argument(
        "--event",
        help=(
            "Explicit event JSON file. Defaults to "
            "Git diff mode."
        ),
    )
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--repository-name",
    )
    parser.add_argument(
        "--from-sha",
    )
    parser.add_argument(
        "--to-sha",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
    )
    parser.add_argument(
        "--command",
        nargs="+",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
    )
    args = parser.parse_args(argv)

    transport: InvalidationTransport | None
    if args.dry_run or args.local_only:
        transport = None
    elif args.command:
        transport = (
            CommandInvalidationTransport(
                args.command,
                timeout_seconds=(
                    args.timeout_seconds
                ),
            )
        )
    else:
        transport = (
            CommandInvalidationTransport
            .from_environment(
                timeout_seconds=(
                    args.timeout_seconds
                )
            )
        )

    bridge = RepositoryEventBridge.from_database(
        args.database,
        transport=transport,
    )

    if args.event:
        payload = json.loads(
            Path(args.event).read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(payload, Mapping):
            raise SystemExit(
                "Event root must be a JSON object"
            )
        event = event_from_mapping(payload)
    else:
        if not (
            args.repository_name
            and args.from_sha
            and args.to_sha
        ):
            parser.error(
                "--repository-name, --from-sha and "
                "--to-sha are required in Git diff mode"
            )

        event = bridge.from_git_diff(
            repository_root=(
                args.repository_root
            ),
            repository_name=(
                args.repository_name
            ),
            from_sha=args.from_sha,
            to_sha=args.to_sha,
            allow_dirty=args.allow_dirty,
        )

    result = bridge.dispatch(
        event,
        dry_run=args.dry_run,
    )

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

python -m compileall \
  "$RETRIEVAL/context_query.py" \
  "$RETRIEVAL/reuse_recorder.py" \
  "$INVALIDATION/repository_event_bridge.py"

python - <<'PY'
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

files = (
    Path(
        "subagent-generated-data/retrieval/"
        "context_query.py"
    ),
    Path(
        "subagent-generated-data/retrieval/"
        "reuse_recorder.py"
    ),
    Path(
        "subagent-generated-data/invalidation/"
        "repository_event_bridge.py"
    ),
)

required_symbols = {
    files[0]: {
        "ContextBudget",
        "ContextQuery",
        "ContextCandidate",
        "ContextQueryResult",
        "CommandContextClient",
        "StaticContextClient",
    },
    files[1]: {
        "ReuseIdentity",
        "PendingReuse",
        "ReuseFinalization",
        "ReuseRecorder",
        "CommandReuseTransport",
    },
    files[2]: {
        "ChangedPath",
        "RepositoryChangeEvent",
        "RepositoryEventBridge",
        "CommandInvalidationTransport",
    },
}

for path in files:
    tree = ast.parse(
        path.read_text(encoding="utf-8")
    )
    symbols = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }
    missing = required_symbols[path] - symbols
    if missing:
        raise SystemExit(
            f"{path}: missing symbols: "
            f"{sorted(missing)}"
        )

print("STATIC CONTRACT VALIDATION PASSED")
print()
print("SHA-256")
for path in files:
    digest = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    print(f"{digest}  {path}")
PY

echo
echo "Installed exemplary producer modules:"
echo "  $RETRIEVAL/context_query.py"
echo "  $RETRIEVAL/reuse_recorder.py"
echo "  $INVALIDATION/repository_event_bridge.py"
```

The three modules deliberately terminate at existing command and state-store boundaries: context retrieval delegates search to the memory data plane, reuse dispatches only finalized outcomes, and repository invalidation emits structured non-deleting requests.
