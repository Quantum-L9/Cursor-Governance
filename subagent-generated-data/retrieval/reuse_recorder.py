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
_STATE_STORE_PATH = _PACKAGE_ROOT / "orchestration" / "state_store.py"

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
                raise ValueError(f"{name} must be a non-empty string")

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
    injection_method: str = "agent_contract_context"

    def __post_init__(self) -> None:
        for name in (
            "record_id",
            "context_pack_id",
            "query",
            "injection_method",
        ):
            value = getattr(self, name)
            if not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

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
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"Unsupported reuse outcome: {self.outcome}")
        if not isinstance(self.evidence, Mapping):
            raise ValueError("evidence must be an object")
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
            "remote_dispatched": (self.remote_dispatched),
            "remote_status": self.remote_status,
            "remote_response": (
                dict(self.remote_response) if self.remote_response is not None else None
            ),
            "invalidation_candidate": (
                dict(self.invalidation_candidate)
                if self.invalidation_candidate is not None
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
            raise ValueError("Reuse command is required")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(str(item) for item in command)
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = ("L9_SGD_GRAPHITI_REUSE_COMMAND"),
        timeout_seconds: int = 30,
    ) -> CommandReuseTransport:
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise ReuseTransportError(f"{variable} is not configured")
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
                self.command,
                input=canonical_json(event),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise ReuseTransportError(
                f"Reuse command timed out after {self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise ReuseTransportError(f"Reuse command could not start: {exc}") from exc

        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise ReuseTransportError(
                f"Reuse command failed with exit {completed.returncode}: {stderr}"
            )

        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ReuseProtocolError("Reuse command stdout was not valid JSON") from exc

        if not isinstance(response, Mapping):
            raise ReuseProtocolError("Reuse response must be a JSON object")

        status = str(response.get("status", ""))
        if status not in {
            "recorded",
            "accepted",
            "duplicate",
            "already_exists",
        }:
            raise ReuseProtocolError(f"Unsupported reuse status: {status!r}")

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
    ) -> ReuseRecorder:
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
                "injection_method": (pending.injection_method),
                "context_pack_id": (pending.context_pack_id),
            },
            "outcome": finalization.outcome,
            "evidence": dict(finalization.evidence),
            "correction_required": (finalization.correction_required),
            "validity_confirmed": (finalization.validity_confirmed),
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
            remote_response = self.transport.record(event)
            remote_status = str(remote_response.get("status", ""))
            remote_dispatched = True

        invalidation_candidate = (
            build_invalidation_candidate(event)
            if finalization.outcome in NEGATIVE_INVALIDATION_CANDIDATE_OUTCOMES
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
            invalidation_candidate=(invalidation_candidate),
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
                "injection_method": (pending.injection_method),
                "context_pack_id": (pending.context_pack_id),
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
        row, created = self.state_store.record_reuse_event(
            event_id=event_id,
            record_id=pending.record_id,
            campaign_id=(pending.consumer.campaign_id),
            action_id=(pending.consumer.action_id),
            agent_id=(pending.consumer.agent_id),
            context_pack_id=(pending.context_pack_id),
            stage=stage.value,
            outcome=outcome,
            payload=payload,
        )

        if not created:
            stored_payload = row.get("payload_json")
            if stored_payload is not None:
                try:
                    parsed = json.loads(str(stored_payload))
                except json.JSONDecodeError as exc:
                    raise ReuseProtocolError("Stored reuse payload is invalid JSON") from exc

                if canonical_json(parsed) != (canonical_json(payload)):
                    raise ReuseCollisionError(f"Reuse event ID collision: {event_id}")

        return row, created


def build_invalidation_candidate(
    reuse_event: Mapping[str, Any],
) -> dict[str, Any]:
    """Create an advisory candidate; never mutate memory directly."""

    event_id = str(reuse_event["event_id"])
    return {
        "schema_version": "1.0.0",
        "kind": "SourceInvalidationCandidate",
        "candidate_id": (f"invalidation-candidate-{event_id}"),
        "event_type": "failed_reuse_reported",
        "record_ids": [str(reuse_event["record_id"])],
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
    digest = hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()
    return f"reuse-{digest[:32]}"


def load_state_store_module() -> ModuleType:
    if not _STATE_STORE_PATH.is_file():
        raise ReuseRecorderError(f"State store not found: {_STATE_STORE_PATH}")

    module_name = "_l9_sgd_orchestration_state_store"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        _STATE_STORE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ReuseRecorderError("Could not create state-store import spec")

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
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid occurred_at timestamp: {value}") from exc

    if parsed.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")


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
        description=("Record a finalized governed memory-reuse outcome.")
    )
    parser.add_argument(
        "--database",
        required=True,
    )
    parser.add_argument(
        "--event",
        help=("Finalization JSON file. Defaults to stdin."),
    )
    parser.add_argument(
        "--command",
        nargs="+",
        help=(
            "Explicit Graphiti reuse command. When omitted, L9_SGD_GRAPHITI_REUSE_COMMAND is used."
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
        payload = json.loads(Path(args.event).read_text(encoding="utf-8"))
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise SystemExit("Reuse finalization must be a JSON object")

    consumer_payload = payload.get(
        "consumer",
        {},
    )
    use_payload = payload.get("use", {})
    if not isinstance(
        consumer_payload,
        Mapping,
    ) or not isinstance(use_payload, Mapping):
        raise SystemExit("consumer and use must be objects")

    pending = PendingReuse(
        record_id=str(payload["record_id"]),
        consumer=ReuseIdentity(
            repository=str(consumer_payload["repository"]),
            campaign_id=str(consumer_payload["campaign_id"]),
            action_id=str(consumer_payload["action_id"]),
            agent_id=str(consumer_payload["agent_id"]),
            role=str(consumer_payload["role"]),
        ),
        context_pack_id=str(use_payload["context_pack_id"]),
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
        evidence=dict(payload.get("evidence", {})),
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
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )
        ),
        metadata=dict(payload.get("metadata", {})),
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
        transport = CommandReuseTransport.from_environment(timeout_seconds=(args.timeout_seconds))

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
