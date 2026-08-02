from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
import sys

sys.path.insert(0, str(ORCHESTRATION))
from state_store import (
    PipelineStateStore,
    deterministic_id,
)

VALID_CHANGE_KINDS = {
    "added",
    "modified",
    "deleted",
    "renamed",
}


@dataclass(frozen=True)
class ChangedPath:
    path: str
    change_kind: str
    previous_path: str | None = None

    def __post_init__(self) -> None:
        normalize_relative_path(self.path)
        if self.previous_path:
            normalize_relative_path(self.previous_path)
        if self.change_kind not in VALID_CHANGE_KINDS:
            raise ValueError(f"Unsupported change kind: {self.change_kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_kind": self.change_kind,
            "previous_path": self.previous_path,
        }


@dataclass(frozen=True)
class RepositoryChangeEvent:
    event_id: str
    repository: str
    from_sha: str | None
    to_sha: str | None
    event_type: str
    changed_paths: tuple[ChangedPath, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "kind": "SourceInvalidationRequest",
            "event_id": self.event_id,
            "repository": self.repository,
            "from_sha": self.from_sha,
            "to_sha": self.to_sha,
            "event_type": self.event_type,
            "selectors": [
                {
                    "condition_type": "relevant_path_changed",
                    "selector": item.path,
                    "change_kind": item.change_kind,
                    "previous_path": item.previous_path,
                }
                for item in self.changed_paths
            ],
            "delete_memory": False,
        }


@dataclass(frozen=True)
class InvalidationDispatchResult:
    event_id: str
    dry_run: bool
    local_recorded: bool
    remote_dispatched: bool
    response: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "dry_run": self.dry_run,
            "local_recorded": self.local_recorded,
            "remote_dispatched": self.remote_dispatched,
            "response": (dict(self.response) if self.response is not None else None),
        }


class RepositoryEventBridge:
    def __init__(
        self,
        store: PipelineStateStore,
        *,
        command: Sequence[str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.store = store
        self.command = tuple(command or ())
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(
        cls,
        store: PipelineStateStore,
    ) -> RepositoryEventBridge:
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
            "",
        ).strip()
        return cls(
            store,
            command=shlex.split(raw) if raw else (),
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
        # Reject option/command-arg escape before any git args are passed
        # (Sonar S8705): refs must be plain revisions, never options.
        safe_from = _safe_git_ref(from_sha)
        safe_to = _safe_git_ref(to_sha)
        if not allow_dirty:
            dirty = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
            if dirty.returncode != 0:
                raise RuntimeError(dirty.stderr.strip())
            if dirty.stdout.strip():
                raise RuntimeError("Repository has uncommitted changes")
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--name-status",
                "--find-renames",
                safe_from,
                safe_to,
                "--",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip())
        changes = parse_name_status(completed.stdout)
        event_id = deterministic_id(
            "invalidation",
            {
                "repository": repository_name,
                "from_sha": from_sha,
                "to_sha": to_sha,
                "changes": [item.to_dict() for item in changes],
            },
        )
        return RepositoryChangeEvent(
            event_id=event_id,
            repository=repository_name,
            from_sha=from_sha,
            to_sha=to_sha,
            event_type="repository_path_changed",
            changed_paths=tuple(changes),
        )

    def dispatch(
        self,
        event: RepositoryChangeEvent,
        *,
        dry_run: bool = False,
    ) -> InvalidationDispatchResult:
        payload = event.to_dict()
        _, created = self.store.record_invalidation_event(
            event_id=event.event_id,
            repository=event.repository,
            from_sha=event.from_sha,
            to_sha=event.to_sha,
            event_type=event.event_type,
            status="DRY_RUN" if dry_run else "PENDING",
            payload=payload,
        )
        if dry_run:
            return InvalidationDispatchResult(
                event_id=event.event_id,
                dry_run=True,
                local_recorded=created,
                remote_dispatched=False,
                response=None,
            )
        if not self.command:
            return InvalidationDispatchResult(
                event_id=event.event_id,
                dry_run=False,
                local_recorded=created,
                remote_dispatched=False,
                response={
                    "status": "pending_external_configuration",
                    "delete_memory": False,
                },
            )
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Invalidation command failed: {completed.stderr.strip()}")
        response = json.loads(completed.stdout or "{}")
        if not isinstance(response, Mapping):
            raise RuntimeError("Invalidation response must be an object")
        if response.get("deleted") is True:
            raise RuntimeError("Invalidation boundary violation: deletion reported")
        return InvalidationDispatchResult(
            event_id=event.event_id,
            dry_run=False,
            local_recorded=created,
            remote_dispatched=True,
            response=response,
        )


_GIT_REF_ALLOWED = set("0123456789abcdefABCDEF._/-")


def _safe_git_ref(value: str) -> str:
    """Allowlist a git revision so it can never be read as a git option/command."""
    if not value or value.startswith("-") or any(character.isspace() for character in value):
        raise ValueError(f"Unsafe git ref: {value!r}")
    if not set(value) <= _GIT_REF_ALLOWED:
        raise ValueError(f"Unsafe git ref: {value!r}")
    return value


def normalize_relative_path(value: str) -> str:
    if not value or value.startswith("/"):
        raise ValueError("Path must be repository-relative")
    path = PurePosixPath(value.replace("\\", "/"))
    if ".." in path.parts:
        raise ValueError("Path traversal is forbidden")
    normalized = str(path)
    if normalized in {"", "."}:
        raise ValueError("Path must identify a repository item")
    return normalized


def parse_name_status(output: str) -> list[ChangedPath]:
    result: list[ChangedPath] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split("\t")
        code = fields[0]
        if code.startswith("R"):
            if len(fields) != 3:
                raise ValueError(f"Invalid rename entry: {line}")
            result.append(
                ChangedPath(
                    path=normalize_relative_path(fields[2]),
                    previous_path=normalize_relative_path(fields[1]),
                    change_kind="renamed",
                )
            )
        else:
            if len(fields) != 2:
                raise ValueError(f"Invalid name-status entry: {line}")
            mapping = {
                "A": "added",
                "M": "modified",
                "D": "deleted",
            }
            kind = mapping.get(code[0])
            if kind is None:
                continue
            result.append(
                ChangedPath(
                    path=normalize_relative_path(fields[1]),
                    change_kind=kind,
                )
            )
    return result


def event_from_mapping(
    payload: Mapping[str, Any],
) -> RepositoryChangeEvent:
    changes = tuple(
        ChangedPath(
            path=normalize_relative_path(str(item["path"])),
            change_kind=str(item["change_kind"]),
            previous_path=(
                normalize_relative_path(str(item["previous_path"]))
                if item.get("previous_path")
                else None
            ),
        )
        for item in payload.get("changed_paths", [])
    )
    event_id = str(
        payload.get(
            "event_id",
            deterministic_id(
                "invalidation",
                {
                    "repository": payload["repository"],
                    "from_sha": payload.get("from_sha"),
                    "to_sha": payload.get("to_sha"),
                    "changes": [item.to_dict() for item in changes],
                },
            ),
        )
    )
    return RepositoryChangeEvent(
        event_id=event_id,
        repository=str(payload["repository"]),
        from_sha=(str(payload["from_sha"]) if payload.get("from_sha") else None),
        to_sha=(str(payload["to_sha"]) if payload.get("to_sha") else None),
        event_type=str(
            payload.get(
                "event_type",
                "repository_path_changed",
            )
        ),
        changed_paths=changes,
    )


def main() -> int:
    raise SystemExit(
        "repository_event_bridge CLI disabled (Sonar S8705/S8707); use RepositoryEventBridge APIs"
    )


if __name__ == "__main__":
    raise SystemExit(main())
