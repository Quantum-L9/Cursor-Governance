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
_STATE_STORE_PATH = _PACKAGE_ROOT / "orchestration" / "state_store.py"

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


class RepositoryStateError(RepositoryEventBridgeError):
    """The repository state is unsuitable for deterministic diffing."""


class InvalidationCollisionError(RepositoryEventBridgeError):
    """An immutable event ID was reused with different content."""


class InvalidationTransportError(RepositoryEventBridgeError):
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
        normalized = normalize_repository_path(self.path)
        object.__setattr__(
            self,
            "path",
            normalized,
        )

        if self.previous_path is not None:
            object.__setattr__(
                self,
                "previous_path",
                normalize_repository_path(self.previous_path),
            )

        if self.change_kind is ChangeKind.RENAMED and self.previous_path is None:
            raise ValueError("Renamed paths require previous_path")

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
            raise ValueError("repository must be non-empty")
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"Unsupported invalidation event type: {self.event_type}")

        metadata = {} if self.metadata is None else dict(self.metadata)
        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

        if (
            self.event_type == "repository_path_changed"
            and not self.changed_paths
            and not self.selectors
        ):
            raise ValueError("repository_path_changed requires changed paths or selectors")

        normalized_selectors = tuple(normalize_selector(selector) for selector in self.selectors)
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
                "condition_type": ("relevant_path_changed"),
                "selector": item.path,
                "change_kind": (item.change_kind.value),
                "previous_path": (item.previous_path),
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
            "selectors": [dict(selector) for selector in self.effective_selectors()],
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
            "remote_dispatched": (self.remote_dispatched),
            "remote_status": self.remote_status,
            "response": (dict(self.response) if self.response is not None else None),
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
            raise ValueError("Invalidation command is required")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(str(item) for item in command)
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None

    @classmethod
    def from_environment(
        cls,
        *,
        variable: str = ("L9_SGD_GRAPHITI_INVALIDATE_COMMAND"),
        timeout_seconds: int = 30,
    ) -> CommandInvalidationTransport:
        raw = os.environ.get(variable, "").strip()
        if not raw:
            raise InvalidationTransportError(f"{variable} is not configured")
        return cls(
            shlex.split(raw),
            timeout_seconds=timeout_seconds,
        )

    def invalidate(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        try:
            # Operator-configured argv (env/CLI), not untrusted request body.
            completed = subprocess.run(  # nosemgrep: subprocess-injection
                self.command,
                input=canonical_json(request),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self.environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise InvalidationTransportError(
                f"Invalidation command timed out after {self.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise InvalidationTransportError(
                f"Invalidation command could not start: {exc}"
            ) from exc

        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise InvalidationTransportError(
                f"Invalidation command failed with exit {completed.returncode}: {stderr}"
            )

        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise InvalidationTransportError(
                "Invalidation command stdout was not valid JSON"
            ) from exc

        if not isinstance(response, Mapping):
            raise InvalidationTransportError("Invalidation response must be a JSON object")

        if response.get("deleted") is True:
            raise InvalidationTransportError(
                "Invalidation boundary violation: destination reported deletion"
            )

        if response.get("replacement_created") is True:
            raise InvalidationTransportError(
                "Invalidation boundary violation: destination created a replacement"
            )

        status = str(response.get("status", ""))
        if status not in {
            "accepted",
            "invalidated",
            "partially_invalidated",
            "duplicate",
            "no_matches",
            "quarantined",
            "archived",
        }:
            raise InvalidationTransportError(f"Unsupported invalidation status: {status!r}")

        return dict(response)


class RepositoryEventBridge:
    """Produce and dispatch structured invalidation requests."""

    def __init__(
        self,
        state_store: Any,
        *,
        transport: (InvalidationTransport | None) = None,
    ) -> None:
        self.state_store = state_store
        self.transport = transport

    @classmethod
    def from_database(
        cls,
        database_path: str | Path,
        *,
        transport: (InvalidationTransport | None) = None,
    ) -> RepositoryEventBridge:
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
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RepositoryStateError(completed.stderr.strip() or "git diff failed")

        changed_paths = tuple(parse_name_status(completed.stdout))

        if not changed_paths:
            raise RepositoryStateError("Git diff contains no changed paths")

        return RepositoryChangeEvent(
            repository=repository_name,
            event_type=("repository_path_changed"),
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

        row, created = self.state_store.record_invalidation_event(
            event_id=event_id,
            repository=event.repository,
            from_sha=event.from_sha,
            to_sha=event.to_sha,
            event_type=event.event_type,
            status=("DRY_RUN" if dry_run else "PENDING"),
            payload=request,
        )

        if not created:
            stored_payload = row.get("payload_json")
            if stored_payload is not None:
                try:
                    parsed = json.loads(str(stored_payload))
                except json.JSONDecodeError as exc:
                    raise RepositoryEventBridgeError(
                        "Stored invalidation payload is invalid JSON"
                    ) from exc

                if canonical_json(parsed) != (canonical_json(request)):
                    raise InvalidationCollisionError(f"Invalidation event ID collision: {event_id}")

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

        response = self.transport.invalidate(request)
        return InvalidationDispatchResult(
            event_id=event_id,
            dry_run=False,
            local_created=created,
            local_duplicate=not created,
            remote_dispatched=True,
            remote_status=str(response.get("status", "")),
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
                raise RepositoryStateError(f"Invalid rename record: {raw_line!r}")
            changes.append(
                ChangedPath(
                    path=fields[2],
                    previous_path=fields[1],
                    change_kind=(ChangeKind.RENAMED),
                )
            )
            continue

        if len(fields) != 2:
            raise RepositoryStateError(f"Invalid name-status record: {raw_line!r}")

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
    selector_value = str(selector.get("selector", "")).strip()

    if not condition_type:
        raise ValueError("Invalidation selector requires condition_type")
    if not selector_value:
        raise ValueError("Invalidation selector requires selector")

    normalized: dict[str, Any] = {
        "condition_type": condition_type,
        "selector": (
            normalize_repository_path(selector_value)
            if condition_type == "relevant_path_changed"
            else selector_value
        ),
    }

    if selector.get("change_kind") is not None:
        normalized["change_kind"] = str(selector["change_kind"])

    if selector.get("previous_path") is not None:
        normalized["previous_path"] = normalize_repository_path(str(selector["previous_path"]))
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
        raise ValueError("changed_paths must be an array")

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
        raise ValueError("selectors must be an array")

    changed_paths = tuple(
        ChangedPath(
            path=str(item["path"]),
            change_kind=ChangeKind(str(item["change_kind"])),
            previous_path=(
                str(item["previous_path"]) if item.get("previous_path") is not None else None
            ),
        )
        for item in changed_paths_raw
        if isinstance(item, Mapping)
    )

    selectors = tuple(dict(item) for item in selectors_raw if isinstance(item, Mapping))

    return RepositoryChangeEvent(
        event_id=(str(payload["event_id"]) if payload.get("event_id") else None),
        repository=str(payload["repository"]),
        event_type=str(
            payload.get(
                "event_type",
                "repository_path_changed",
            )
        ),
        from_sha=optional_string(payload.get("from_sha")),
        to_sha=optional_string(payload.get("to_sha")),
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
    selectors: Sequence[Mapping[str, Any]],
) -> str:
    seed = {
        "repository": repository,
        "event_type": event_type,
        "from_sha": from_sha,
        "to_sha": to_sha,
        "changed_paths": [item.to_dict() for item in changed_paths],
        "selectors": [dict(item) for item in selectors],
    }
    digest = hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()
    return f"invalidation-{digest[:32]}"


def normalize_repository_path(
    value: str,
) -> str:
    text = value.replace("\\", "/").strip()
    if not text:
        raise ValueError("Repository path cannot be empty")
    path = PurePosixPath(text)
    if path.is_absolute():
        raise ValueError("Repository path must be relative")
    if ".." in path.parts:
        raise ValueError("Repository path traversal is forbidden")

    parts = tuple(part for part in path.parts if part not in {"", "."})
    if not parts:
        raise ValueError("Repository path cannot resolve to root")
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
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != "true":
        raise RepositoryStateError(f"Not a Git repository: {root}")


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
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(completed.stderr.strip() or "git status failed")
    if completed.stdout.strip():
        raise RepositoryStateError("Repository has uncommitted changes")


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
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(f"Unknown commit: {revision}")


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
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise RepositoryStateError(f"Could not resolve commit: {revision}")
    return completed.stdout.strip()


def load_state_store_module() -> ModuleType:
    if not _STATE_STORE_PATH.is_file():
        raise RepositoryEventBridgeError(f"State store not found: {_STATE_STORE_PATH}")

    module_name = "_l9_sgd_orchestration_state_store"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        _STATE_STORE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RepositoryEventBridgeError("Could not create state-store import spec")

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
        major = int(schema_version.split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid schema version: {schema_version!r}") from exc

    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(f"Unsupported invalidation schema major: {major}")


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
        description=("Create and dispatch a structured source-invalidation request.")
    )
    parser.add_argument(
        "--database",
        required=True,
    )
    parser.add_argument(
        "--event",
        help=("Explicit event JSON file. Defaults to Git diff mode."),
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
        transport = CommandInvalidationTransport(
            args.command,
            timeout_seconds=(args.timeout_seconds),
        )
    else:
        transport = CommandInvalidationTransport.from_environment(
            timeout_seconds=(args.timeout_seconds)
        )

    bridge = RepositoryEventBridge.from_database(
        args.database,
        transport=transport,
    )

    if args.event:
        payload = json.loads(Path(args.event).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise SystemExit("Event root must be a JSON object")
        event = event_from_mapping(payload)
    else:
        if not (args.repository_name and args.from_sha and args.to_sha):
            parser.error("--repository-name, --from-sha and --to-sha are required in Git diff mode")

        event = bridge.from_git_diff(
            repository_root=(args.repository_root),
            repository_name=(args.repository_name),
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
