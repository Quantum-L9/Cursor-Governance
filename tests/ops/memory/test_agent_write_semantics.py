"""Direct agent-write semantics are locked (ADR-0037, INV-AMW-01..08).

These tests exercise the vendored ``l9-graphite-memory`` MCP dispatcher over a
real ``MemoryService`` with a throwaway sqlite store. Nothing is stubbed: the
principal's namespace grant, request validation, admission and the phase-lock
check all run exactly as they do behind the MCP server. They prove existing
behaviour and add none:

* A — ``memory.write_agent`` admits without ``memory.phase_lock``;
* B — ``memory.write_governed`` still refuses without a held lock;
* C — several independent memories are several sequential writes (no batch);
* D — the structural controls the direct lane already enforces still reject;

plus the contract-level separation of ``memory.phase_lock`` from the
SessionStart prefetch precondition (INV-AMW-06).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from l9_graphite_memory.adapters import build_projection, build_store
from l9_graphite_memory.config import MemorySettings
from l9_graphite_memory.contracts import MemoryPrincipal
from l9_graphite_memory.errors import AuthorizationError
from l9_graphite_memory.mcp_tools import CANONICAL_TOOLS, MCPToolApplication
from l9_graphite_memory.services import MemoryService

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = (
    ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "memory"
    / "memory-enforcement.contract.json"
)

NAMESPACE = "cursor-governance"
TASK_SIGNATURE = "adr-0037-governed-write"
ADMITTED = "admitted"


@pytest.fixture
def service(tmp_path: Path) -> Iterator[MemoryService]:
    settings = MemorySettings(
        data_dir=tmp_path,
        state_dir=tmp_path / "state",
        database_path=tmp_path / "memory.sqlite3",
    )
    svc = MemoryService(
        build_store(settings), build_projection(settings), projection_required=False
    )
    svc.initialize()
    try:
        yield svc
    finally:
        svc.store.close()


@pytest.fixture
def app(service: MemoryService) -> MCPToolApplication:
    return MCPToolApplication(service)


@pytest.fixture
def principal() -> MemoryPrincipal:
    return MemoryPrincipal(
        principal_id="agent:claude-code",
        tenant_id="l9-test",
        agent_id="claude-code",
        read_namespaces=(NAMESPACE,),
        write_namespaces=(NAMESPACE,),
    )


def _write_agent(app: MCPToolApplication, principal: MemoryPrincipal, **args: Any) -> Any:
    payload: dict[str, Any] = {"namespace": NAMESPACE, "tags": ["agent:claude-code"], **args}
    return app.call(principal, "memory.write_agent", payload)


def _status(receipt: Any) -> str:
    return str(getattr(receipt.status, "value", receipt.status))


def _tool(name: str) -> dict[str, Any]:
    return next(item for item in CANONICAL_TOOLS if item["name"] == name)


# ---------------------------------------------------------------------------
# A — ordinary agent write has no phase-lock dependency (INV-AMW-04)
# ---------------------------------------------------------------------------


def test_write_agent_admits_without_phase_lock(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    receipt = _write_agent(
        app,
        principal,
        content="Repository handoffs use the in-scope repository namespace.",
        memory_class="lesson",
    )
    assert _status(receipt) == ADMITTED
    # The ordinary write took no lock: none exists for any task on the namespace.
    verification = app.call(
        principal,
        "memory.verify_phase_lock",
        {"namespace": NAMESPACE, "task_signature": TASK_SIGNATURE},
    )
    assert verification.valid is False


def test_write_agent_tool_declares_no_phase_lock_input() -> None:
    tool = _tool("memory.write_agent")
    assert "No phase-lock required" in tool["description"]
    assert "task_signature" not in tool["inputSchema"]["properties"]
    assert set(tool["inputSchema"]["required"]) == {"namespace", "content"}


# ---------------------------------------------------------------------------
# B — governed write keeps its existing phase-lock requirement (INV-AMW-05)
# ---------------------------------------------------------------------------


def test_write_governed_refuses_without_held_phase_lock(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    with pytest.raises(AuthorizationError, match="requires a held phase-lock"):
        app.call(
            principal,
            "memory.write_governed",
            {"namespace": NAMESPACE, "content": "Governed fact.", "task_signature": TASK_SIGNATURE},
        )


def test_write_governed_admits_under_held_phase_lock(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    lock = app.call(
        principal,
        "memory.phase_lock",
        {"namespace": NAMESPACE, "task_signature": TASK_SIGNATURE},
    )
    assert lock.granted is True
    receipt = app.call(
        principal,
        "memory.write_governed",
        {"namespace": NAMESPACE, "content": "Governed fact.", "task_signature": TASK_SIGNATURE},
    )
    assert _status(receipt) == ADMITTED


def test_write_governed_tool_requires_task_signature() -> None:
    tool = _tool("memory.write_governed")
    assert "task_signature" in tool["inputSchema"]["required"]


# ---------------------------------------------------------------------------
# C — independent memories are independent sequential writes (INV-AMW-01/03)
# ---------------------------------------------------------------------------


def test_independent_memories_are_separate_sequential_writes(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    facts = (
        ("Repository handoffs use the in-scope repository namespace.", "decision"),
        ("Degraded hydration remains usable for session closure.", "insight"),
        ("Direct agent-authored durable memory uses the agent memory write lane.", "decision"),
    )
    receipts = [_write_agent(app, principal, content=c, memory_class=k) for c, k in facts]
    assert [_status(r) for r in receipts] == [ADMITTED] * len(facts)
    record_ids = {r.record_id for r in receipts}
    assert len(record_ids) == len(facts), "each independent memory must be its own record"


def test_write_agent_contract_is_one_record_per_call() -> None:
    """No batch shape exists: ``content`` is a single string, not a list."""
    props = _tool("memory.write_agent")["inputSchema"]["properties"]
    assert props["content"]["type"] == "string"


# ---------------------------------------------------------------------------
# D — existing structural controls on the direct lane still reject
# ---------------------------------------------------------------------------


def test_write_agent_rejects_namespace_outside_grant(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    receipt = app.call(
        principal,
        "memory.write_agent",
        {"namespace": "some-other-repo", "content": "Out-of-grant fact."},
    )
    assert _status(receipt) != ADMITTED


def test_write_agent_rejects_unsupported_memory_class(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    with pytest.raises(ValueError, match="does not allow memory_class"):
        _write_agent(app, principal, content="A fact.", memory_class="procedural")


@pytest.mark.parametrize("content", ["", "x" * 64_001], ids=["empty", "over-bound"])
def test_write_agent_rejects_content_outside_bounds(
    app: MCPToolApplication, principal: MemoryPrincipal, content: str
) -> None:
    with pytest.raises(ValueError, match="invalid memory.write_agent arguments"):
        _write_agent(app, principal, content=content)


def test_write_agent_rejects_oversized_idempotency_key(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    with pytest.raises(ValueError, match="invalid memory.write_agent arguments"):
        _write_agent(app, principal, content="A fact.", idempotency_key="k" * 301)


def test_write_agent_rejects_malformed_payload(
    app: MCPToolApplication, principal: MemoryPrincipal
) -> None:
    with pytest.raises(KeyError):
        app.call(principal, "memory.write_agent", {"namespace": NAMESPACE})


def test_write_agent_input_schema_rejects_unknown_fields_and_bad_tags() -> None:
    schema = _tool("memory.write_agent")["inputSchema"]
    assert schema["additionalProperties"] is False
    validator = jsonschema.Draft202012Validator(schema)
    base = {"namespace": NAMESPACE, "content": "A fact."}
    assert validator.is_valid(base)
    assert not validator.is_valid({**base, "unknown_field": 1})
    assert not validator.is_valid({**base, "tags": "agent:claude-code"})
    assert not validator.is_valid({**base, "tags": [1]})


# ---------------------------------------------------------------------------
# INV-AMW-06 — memory.phase_lock is not the SessionStart prefetch receipt
# ---------------------------------------------------------------------------


def test_phase_lock_is_not_the_session_prefetch_precondition() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    imw = contract["interactive_memory_write"]
    assert imw["cold_write_operation"] == "memory.write_agent"
    assert imw["cold_write_prerequisite"] == "none"
    assert imw["governed_write_prerequisite"] == "memory.phase_lock"

    prefetch = contract["preconditions"]["session_prefetch"]
    assert prefetch["established_by"].endswith("hooks/memory_prefetch.py")
    assert "phase_lock" not in json.dumps(prefetch)
    assert set(contract["preconditions"]) == {"session_prefetch"}
    for rule in contract["governed_writes"]:
        assert "phase_lock" not in rule["requires"], rule["id"]
        tools = rule["match"].get("tools", [])
        assert not any("graphite-memory" in tool for tool in tools), rule["id"]
