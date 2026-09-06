"""Shared helpers for the memory boundary suite (ops/memory).

A plain module rather than a conftest so tests import it by a name that
cannot collide with the repository's root ``conftest`` under pytest's
rootdir import mode. ``conftest.py`` in this directory re-exports the
fixtures.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.memory.runtime_binding import STATUS_EXACT, RuntimeBinding  # noqa: E402

Handler = Callable[[list[str], str | None], tuple[int, Any, str]]


class FakeMemoryCli:
    """A scripted ``l9-memory``: subcommand -> (exit code, stdout payload, stderr).

    Handlers receive the argv after the executable and the stdin text, so a
    test can assert on exactly what Cursor sent across the boundary.
    """

    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}
        self.calls: list[tuple[list[str], str | None, str | None]] = []
        self.timeout_on: set[str] = set()

    def on(self, command: str, handler: Handler) -> FakeMemoryCli:
        self.handlers[command] = handler
        return self

    def reply(self, command: str, code: int, payload: Any, stderr: str = "") -> FakeMemoryCli:
        return self.on(command, lambda _argv, _stdin: (code, payload, stderr))

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        input_text: str | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del env
        args = list(argv)
        command = args[1] if len(args) > 1 else ""
        if command == "client" and len(args) > 3:
            command = " ".join(args[1:4])
        self.calls.append((args, cwd, input_text))
        if command in self.timeout_on:
            raise subprocess.TimeoutExpired(args, timeout)
        handler = self.handlers.get(command)
        if handler is None:
            return subprocess.CompletedProcess(
                args, 1, "", json.dumps({"error": "KeyError", "message": f"no handler {command}"})
            )
        code, payload, stderr = handler(args[2:], input_text)
        stdout = "" if payload is None else json.dumps(payload, indent=2, default=str)
        return subprocess.CompletedProcess(args, code, stdout, stderr)

    def last(self, command: str) -> list[str]:
        for args, _cwd, _stdin in reversed(self.calls):
            if len(args) > 1 and args[1] == command:
                return args
        raise AssertionError(f"{command} was never invoked")


@pytest.fixture
def fake_cli() -> FakeMemoryCli:
    return FakeMemoryCli()


@pytest.fixture
def bound(tmp_path: Path) -> RuntimeBinding:
    cli = tmp_path / "bin" / "l9-memory"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli.chmod(0o755)
    return RuntimeBinding(
        status=STATUS_EXACT,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="2.2.0",
        expected_contract_version="memory-control-plane/v1",
        manifest_path=str(ROOT / "ops" / "config" / "memory-binding.json"),
        interpreter=str(tmp_path / "bin" / "python"),
        memory_cli=str(cli),
        memory_version="2.2.0",
        contract_version="memory-control-plane/v1",
        module_path=str(tmp_path / "lib" / "l9_graphite_memory" / "__init__.py"),
    )


def error_stderr(name: str, message: str) -> str:
    """The memory CLI's stderr shape: pretty-printed JSON, never a bare line."""

    return json.dumps({"error": name, "message": message}, indent=2)


def hydration_payload(*record_ids: str, status: str = "complete") -> dict[str, Any]:
    sections = (
        [
            {
                "memory_class": "semantic",
                "content": "canonical context",
                "record_ids": list(record_ids),
                "tokens_estimated": 12,
                "highest_score": 0.9,
            }
        ]
        if record_ids
        else []
    )
    return {
        "receipt_id": "11111111-1111-1111-1111-111111111111",
        "status": status,
        "task": "task",
        "sections": sections,
        "token_budget": 1200,
        "tokens_used": 12 if record_ids else 0,
        "search_receipt_id": "22222222-2222-2222-2222-222222222222",
        "result_digest": "a" * 64,
        "warnings": [],
    }


def close_payload(
    *,
    status: str = "complete",
    record_id: str | None = "33333333-3333-3333-3333-333333333333",
    replayed: bool = False,
) -> dict[str, Any]:
    return {
        "receipt_id": "44444444-4444-4444-4444-444444444444",
        "status": status,
        "namespace": "cursor-governance",
        "write_receipt_id": "55555555-5555-5555-5555-555555555555",
        "record_id": record_id,
        "graphiti_accepted": False,
        "replayed": replayed,
        "authorization": {"allowed": status != "failed"},
    }


def health_payload(
    *,
    store_healthy: bool = True,
    projection: str = "none",
    projection_healthy: bool = True,
    status: str | None = None,
) -> dict[str, Any]:
    if status is None:
        if not store_healthy:
            status = "failed"
        elif projection != "none" and not projection_healthy:
            status = "partial"
        else:
            status = "complete"
    return {
        "status": status,
        "package_version": "2.2.0",
        "schema_version": "2.2.0",
        "contract_version": "memory-control-plane/v1",
        "store": {"name": "sqlite", "healthy": store_healthy},
        "projection": {"name": projection, "healthy": projection_healthy},
        "outbox_backlog": 0,
        "degraded_reasons": [] if status == "complete" else ["degraded"],
    }
