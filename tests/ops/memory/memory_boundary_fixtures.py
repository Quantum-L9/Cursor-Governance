"""Shared helpers for the memory boundary suite (ops/memory).

A plain module rather than a conftest so tests import it by a name that
cannot collide with the repository's root ``conftest`` under pytest's
rootdir import mode. ``conftest.py`` in this directory re-exports the
fixtures.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
#: The version the binding manifest pins; the fakes report exactly this.
EXPECTED_VERSION = json.loads(
    (ROOT / "ops" / "config" / "memory-binding.json").read_text(encoding="utf-8")
)["expected_package_version"]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.memory.receipts import CapabilitiesReceipt  # noqa: E402
from ops.memory.runtime_binding import STATUS_EXACT, RuntimeBinding  # noqa: E402
from ops.memory.session_contracts import task_signature_for  # noqa: E402

#: The contract lineage the bound release declares; receipts must agree.
CANONICAL_SCHEMA_VERSION = "2.2.0"

REPOSITORY = "Quantum-L9/Cursor-Governance"
OBJECTIVE = "Realign memory control plane"

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
        #: A real service echoes the query it was handed, so the fake does too.
        #: Turn it off to inject a receipt that answers a *different* search.
        self.echo_search_query = True

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
        if (
            command == "search"
            and self.echo_search_query
            and isinstance(payload, dict)
            and "query" in payload
        ):
            # A real service echoes the query it was handed. The canned payload
            # cannot know it, and a fixed echo would make every search look like
            # a receipt for a different request (MEM-P2-01, consumer half).
            payload = {**payload, "query": args[2] if len(args) > 2 else payload["query"]}
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
        expected_version=EXPECTED_VERSION,
        expected_contract_version="memory-control-plane/v1",
        manifest_path=str(ROOT / "ops" / "config" / "memory-binding.json"),
        interpreter=str(tmp_path / "bin" / "python"),
        memory_cli=str(cli),
        memory_version=EXPECTED_VERSION,
        contract_version="memory-control-plane/v1",
        module_path=str(tmp_path / "lib" / "l9_graphite_memory" / "__init__.py"),
        # The whole suite runs through canonical validation, exactly as the
        # production path does — a receipt no schema accepts fails here too.
        contract_schemas=canonical_schemas(),
        schema_digest=canonical_schema_digest(),
        schema_source=str(tmp_path / "lib" / "l9_graphite_memory" / "contracts.py"),
        capabilities=bound_capabilities(),
    )


def bound_capabilities() -> CapabilitiesReceipt:
    """What the bound release declares about itself — the provenance a receipt
    is checked against (CG-P1-02)."""

    return CapabilitiesReceipt.parse(
        {
            "package": "l9-graphite-memory",
            "package_version": EXPECTED_VERSION,
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "contract_version": "memory-control-plane/v1",
            "transports": [{"transport": "cli", "operations": {"close": "close"}}],
            "exit_codes": {"committed": 0, "dry_run_not_committed": 3},
        }
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
    replay_payload_matched: bool | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    """A CloseReceipt as memory prints it (replay forensics per ADR-082 amendment)."""

    payload: dict[str, Any] = {
        "receipt_id": "44444444-4444-4444-4444-444444444444",
        "status": status,
        "namespace": "cursor-governance",
        "write_receipt_id": "55555555-5555-5555-5555-555555555555",
        "record_id": record_id,
        "graphiti_accepted": False,
        "replayed": replayed,
        "authorization": {"allowed": status != "failed"},
        "warnings": list(warnings),
    }
    if replayed:
        matched = True if replay_payload_matched is None else replay_payload_matched
        payload["replay_payload_matched"] = matched
        payload["stored_digest"] = "d" * 64
        payload["replay_digest"] = "d" * 64 if matched else "e" * 64
    return payload


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
        "package_version": EXPECTED_VERSION,
        "schema_version": "2.2.0",
        "contract_version": "memory-control-plane/v1",
        "store": {"name": "sqlite", "healthy": store_healthy},
        "projection": {"name": projection, "healthy": projection_healthy},
        "outbox_backlog": 0,
        "degraded_reasons": [] if status == "complete" else ["degraded"],
    }


def continuation_record(
    *,
    record_id: str = "66666666-6666-6666-6666-666666666666",
    session_id: str = "session-41",
    repository_state_digest: str = "c" * 40,
    created_at: str = "2026-09-05T00:00:00+00:00",
    next_action: str = "Wire runtime binding",
    objective: str = OBJECTIVE,
    repository_identity: str = REPOSITORY,
    task_signature: str | None = None,
    payload_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A canonical record as `search` returns it, carrying a continuation capsule.

    The capsule's ``task_signature`` defaults to the one the capsule contract
    derives (objective + repository), exactly as a real close writes it.
    """

    capsule = {
        "schema": "cursor.continuation/v2",
        "session_id": session_id,
        "repository_identity": repository_identity,
        "task_signature": task_signature or task_signature_for(objective, repository_identity),
        "objective": objective,
        "next_action": next_action,
        "active_files": ["ops/memory/runtime_binding.py"],
        "blockers": [],
        "decisions": ["CLI is the hook transport"],
        "unfinished_work": ["egress scanner"],
        "repository_state_digest": repository_state_digest,
        "producer": "Cursor-Governance",
        "producer_version": "2.0.0",
        "created_at": created_at,
    }
    if payload_override is not None:
        capsule = payload_override
    return {
        "record_id": record_id,
        "namespace": "cursor-governance",
        "memory_class": "semantic",
        "state": "active",
        "content": f"{objective} | next: {next_action}",
        "tags": ["generated-data", "session_continuation"],
        "metadata": {
            "payload_schema": "cursor.continuation/v2",
            "structured_payload": capsule,
            "producer": "Cursor-Governance",
            "primary_class": "session_continuation",
        },
        "created_at": created_at,
        "temporal": {"recorded_at": created_at, "valid_from": created_at, "valid_to": None},
    }


def search_payload(*records: dict[str, Any], status: str = "complete") -> dict[str, Any]:
    return {
        "receipt_id": "77777777-7777-7777-7777-777777777777",
        "status": status,
        "query": "task",
        "namespaces_authorized": ["cursor-governance"],
        "hits": [
            {"record": record, "score": 0.8, "matched_by": ["canonical-store", "tag"]}
            for record in records
        ],
    }


# ---------------------------------------------------------------------------
# Canonical receipt schemas (CG-P1-02)
#
# In a real environment these are exported from the *bound release* by
# ``runtime_binding._export_contract_schemas`` — the pinned package's own
# pydantic models rendered as JSON Schema. The suite supplies an equivalent
# set so every test in it runs through the same canonical validation the
# production path does, and so the negative cases (missing canonical-required
# field, wrong type, malformed UUID, wrong schema version) have something real
# to fail against.
#
# They are strict about what memory guarantees and permissive about what it
# may add: Cursor narrows the contract, it never rejects a superset.
# ---------------------------------------------------------------------------

_UUID = {"type": "string", "pattern": "^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"}
_STR = {"type": "string"}


def _schema(required: dict[str, Any], **properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "required": sorted(required),
        "properties": {**required, **properties},
    }


def canonical_schemas() -> dict[str, Any]:
    """The canonical receipt contracts, keyed by model name."""

    return {
        "CapabilitiesReceipt": _schema(
            {
                "package": _STR,
                "package_version": _STR,
                "contract_version": _STR,
                "transports": {"type": "array"},
            },
            schema_version=_STR,
            exit_codes={"type": "object"},
        ),
        "HealthReceipt": _schema(
            {
                "status": _STR,
                "package_version": _STR,
                "store": {"type": "object"},
                "projection": {"type": "object"},
            }
        ),
        "ResolveReceipt": _schema({"method": _STR, "readonly": {"type": "boolean"}}),
        "HydrationReceipt": _schema(
            {
                "receipt_id": _UUID,
                "status": _STR,
                "task": _STR,
                "result_digest": _STR,
                "sections": {"type": "array"},
            }
        ),
        "SearchReceipt": _schema(
            {
                "receipt_id": _UUID,
                "status": _STR,
                "query": _STR,
                "namespaces_authorized": {"type": "array", "items": _STR},
            },
            hits={"type": "array"},
            request_digest=_STR,
        ),
        "WriteReceipt": _schema(
            {"receipt_id": _UUID, "status": _STR, "namespace": _STR},
            record_id={"type": ["string", "null"]},
        ),
        "CandidateReceipt": _schema(
            {"status": _STR, "candidate_id": _STR, "namespace": _STR},
            record_id={"type": ["string", "null"]},
            superseded_record_ids={"type": "array", "items": _STR},
        ),
        "CloseReceipt": _schema(
            {
                "receipt_id": _UUID,
                "status": _STR,
                "namespace": _STR,
                "write_receipt_id": {"type": ["string", "null"]},
            },
            record_id={"type": ["string", "null"]},
            replayed={"type": "boolean"},
            replay_payload_matched={"type": ["boolean", "null"]},
            stored_digest={"type": ["string", "null"]},
            replay_digest={"type": ["string", "null"]},
            warnings={"type": "array", "items": _STR},
        ),
        "ConflictsReceipt": _schema(
            {"namespace": _STR, "conflicts": {"type": "array"}, "snapshot_digest": _STR}
        ),
        "PhaseLockReceipt": _schema(
            {
                "lock_id": _STR,
                "namespace": _STR,
                "task_signature": _STR,
                "granted": {"type": "boolean"},
                "expires_at": _STR,
            }
        ),
        "PhaseLockVerificationReceipt": _schema(
            {
                "namespace": _STR,
                "task_signature": _STR,
                "valid": {"type": "boolean"},
                "reasons": {"type": "array", "items": _STR},
            }
        ),
    }


def canonical_schema_digest() -> str:
    encoded = json.dumps(canonical_schemas(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
